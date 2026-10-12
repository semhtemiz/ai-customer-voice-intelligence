import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.analytics import Analytics
from backend.app.config import Settings
from backend.app.db import connect
from backend.app.importer import import_reviews
from backend.app.main import create_app
from backend.app.schemas import Filters
from backend.app.services.insights import build_catalog,generate_insights,request_llm
from backend.app.services.analysis import run_analysis

@pytest.fixture
def insight_context(write_csv,tmp_path):
 db=tmp_path/'insights.db'
 import_reviews(write_csv([
  {'Rating':'1','Recommended IND':'0','Review Text':'Too small. Fabric is very itchy. email customer@example.com'},
  {'Rating':'5','Recommended IND':'1','Review Text':'Love this product.'},
  {'Rating':'2','Recommended IND':'0','Review Text':'Terrible quality. Phone +1 (212) 555-0199'},
  {'Rating':'5','Recommended IND':'1','Review Text':'','Department Name':'Dresses','Class Name':'Dresses'},
 ]),db)
 run_analysis(db,'sentiment',predict=lambda texts:[('negative' if 'Love' not in text else 'positive',0.8) for text in texts],model_id='test',revision='a'*40)
 run_analysis(db,'topics')
 with connect(db,readonly=True) as c:
  catalog=build_catalog(Analytics(c,c.execute('SELECT * FROM import_state').fetchone(),Filters()))
 return db,catalog


def verify_evidence(result):
 ids={item['id'] for item in result['evidence']}
 for statement in result['key_findings']+result['recommended_actions']:
  assert statement['evidence_ids'] and set(statement['evidence_ids'])<=ids


def test_rules_recompute_filtered_evidence_and_empty(insight_context):
 db,catalog=insight_context
 with TestClient(create_app(Settings(db))) as client:
  result=client.post('/api/insights',json={}).json()
  assert result['data']['source']=='rules' and result['data']['fallback_reason']=='not_configured'
  verify_evidence(result['data'])
  assert result['meta']['matched_review_count']==4
  evidence={row['metric']:row for row in result['data']['evidence']}
  assert evidence['total_reviews']['value']==4
  assert evidence['low_rating_count']['value']==2
  assert evidence['low_rating_rate_pct']['value']==50
  assert evidence['topic_sizing']['value']==1
  filtered=client.post('/api/insights',json={'department':'Dresses'}).json()
  assert filtered['meta']['matched_review_count']==1
  assert not any(item['metric'].startswith('topic_') for item in filtered['data']['evidence'])
  assert not any(item['metric']=='low_rating_count' for item in filtered['data']['evidence']) or next(item['value'] for item in filtered['data']['evidence'] if item['metric']=='low_rating_count')==0
  empty=client.post('/api/insights',json={'search':'does-not-exist'}).json()
  assert empty['data']['source']=='empty' and empty['data']['fallback_reason'] is None
  assert empty['data']['key_findings']==empty['data']['recommended_actions']==empty['data']['evidence']==[]
  for body in ({'rating':9},{'search':'x'*201},{'metrics':{'total_reviews':9999}},{'api_key':'secret'}):
   assert client.post('/api/insights',json=body).status_code==422


def test_approved_llm_selection_can_only_reorder_backend_clauses(insight_context):
 db,catalog=insight_context
 def select(catalog,settings): return {'headline_id':'scope','finding_ids':['scope','topic_sizing'],'action_ids':['topic_sizing']}
 result=generate_insights(catalog,Settings(db,openai_api_key='test-secret'),select)
 assert result['source']=='llm' and result['fallback_reason'] is None
 assert result['key_findings'][1]==catalog['findings']['topic_sizing']
 verify_evidence(result)


@pytest.mark.parametrize('output',[
 {'headline_id':'scope','finding_ids':['scope','fabricated_99999'],'action_ids':[]},
 {'headline_id':'scope','finding_ids':['scope'],'action_ids':['shipping']},
 {'headline_id':'scope','finding_ids':['scope'],'action_ids':[],'text':'Revenue is 99999'},
 {'headline_id':'scope','finding_ids':['topic_sizing'],'action_ids':[]},
 {'headline_id':'fabricated','finding_ids':['scope'],'action_ids':[]},
 {'headline_id':'scope','finding_ids':['scope','scope'],'action_ids':[]},
 {'headline_id':'scope','finding_ids':[],'action_ids':[]},
 {'headline_id':'scope','finding_ids':['scope'],'action_ids':[],'evidence':[{'metric':'shipping','value':99999}]},
])
def test_untrusted_or_unreferenced_llm_claims_fall_back(insight_context,output):
 db,catalog=insight_context
 result=generate_insights(catalog,Settings(db,openai_api_key='test-secret'),lambda *_:output)
 assert result['source']=='rules' and result['fallback_reason']=='invalid_output'
 assert '99999' not in json.dumps(result)
 verify_evidence(result)


@pytest.mark.parametrize('error,reason',[(httpx.ReadTimeout('private-secret'), 'timeout'),(httpx.ConnectError('private-secret'),'provider_error')])
def test_provider_failure_keeps_rules_usable_without_leaking_errors(insight_context,error,reason):
 db,catalog=insight_context
 def fail(*_): raise error
 result=generate_insights(catalog,Settings(db,openai_api_key='private-secret'),fail)
 assert result['source']=='rules' and result['fallback_reason']==reason
 assert 'private-secret' not in json.dumps(result)


def test_provider_request_is_bounded_masked_and_strict(insight_context):
 db,catalog=insight_context
 def handler(request):
  assert request.url=='https://api.openai.com/v1/responses'
  body=json.loads(request.content)
  assert body['store'] is False and body['text']['format']['strict'] is True
  data=json.loads(body['input']);assert len(data['samples'])<=20
  assert data['samples']
  assert all(set(row)=={'review_id','review_text'} for row in data['samples'])
  assert 'customer@example.com' not in body['input'] and '555-0199' not in body['input']
  assert request.headers['authorization']=='Bearer test-secret'
  assert '[email]' in body['input'] and '[phone]' in body['input']
  selection={'headline_id':'scope','finding_ids':['scope'],'action_ids':[]}
  return httpx.Response(200,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(selection)}]}]})
 output=request_llm(catalog,Settings(db,openai_api_key='test-secret'),httpx.MockTransport(handler))
 assert output['finding_ids']==['scope']
 assert 'test-secret' not in repr(Settings(db,openai_api_key='test-secret'))


@pytest.mark.parametrize('envelope',[[],{'status':'incomplete'},{'status':'completed','output':[]},{'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]}])
def test_invalid_provider_envelope_is_rejected(insight_context,envelope):
 db,catalog=insight_context
 with pytest.raises(ValueError):
  request_llm(catalog,Settings(db,openai_api_key='test'),httpx.MockTransport(lambda _:httpx.Response(200,json=envelope)))


def test_empty_context_never_calls_provider(write_csv,tmp_path):
 db=tmp_path/'empty.db';import_reviews(write_csv([]),db)
 with connect(db,readonly=True) as c: catalog=build_catalog(Analytics(c,c.execute('SELECT * FROM import_state').fetchone(),Filters()))
 def forbidden(*_): raise AssertionError('Provider must not be called')
 assert generate_insights(catalog,Settings(db,openai_api_key='test'),forbidden)['source']=='empty'


def test_missing_database_insights_returns_safe_503(tmp_path):
 with TestClient(create_app(Settings(tmp_path/'missing.db'))) as client:
  response=client.post('/api/insights',json={})
  assert response.status_code==503 and response.json()=={'detail':'Database is not ready'}


def test_nvidia_request_and_evidence_selection(insight_context):
 db,catalog=insight_context
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='nvidia-test-secret',nvidia_model='meta/llama-3.1-8b-instruct')
 selection={'headline_id':'scope','finding_ids':['scope','topic_sizing'],'action_ids':['topic_sizing']}
 def handler(request):
  assert request.url=='https://integrate.api.nvidia.com/v1/chat/completions'
  assert request.headers['authorization']=='Bearer nvidia-test-secret'
  body=json.loads(request.content)
  assert body['model']=='meta/llama-3.1-8b-instruct'
  assert body['stream'] is False and body['max_tokens']==600 and body['temperature']==0
  assert 'response_format' not in body
  assert body['messages'][0]['role']=='system'
  data=json.loads(body['messages'][1]['content'])
  assert len(data['samples'])<=20
  assert all(set(sample)=={'review_id','review_text'} for sample in data['samples'])
  assert 'customer@example.com' not in json.dumps(data) and '555-0199' not in json.dumps(data)
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(selection)}}]})
 result=generate_insights(catalog,settings,lambda c,s:request_llm(c,s,httpx.MockTransport(handler)))
 assert result['source']=='llm' and result['key_findings'][1]==catalog['findings']['topic_sizing']
 verify_evidence(result)
 assert 'nvidia-test-secret' not in repr(settings) and 'nvidia-test-secret' not in json.dumps(result)


@pytest.mark.parametrize('envelope',[
 [],{}, {'choices':[]}, {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},
 {'choices':[{'finish_reason':'stop','message':{'refusal':'no','content':'{}'}}]},
 {'choices':[{'finish_reason':'stop','message':{'content':None}}]},
 {'choices':[{'finish_reason':'stop','message':{'content':'```json\n{}\n```'}}]},
 {'choices':[{'finish_reason':'stop','message':{'content':'{"headline_id":"scope","finding_ids":["scope","fake"],"action_ids":[]}'}}]},
 {'choices':[{'finish_reason':'stop','message':{'tool_calls':[{}],'content':'{}'}}]},
])
def test_nvidia_invalid_output_uses_rules(insight_context,envelope):
 db,catalog=insight_context
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret')
 result=generate_insights(catalog,settings,lambda c,s:request_llm(c,s,httpx.MockTransport(lambda _:httpx.Response(200,json=envelope))))
 assert result['source']=='rules' and result['fallback_reason']=='invalid_output'
 verify_evidence(result)


@pytest.mark.parametrize('status',[401,429,500])
def test_nvidia_provider_errors_do_not_leak_secrets(insight_context,status):
 db,catalog=insight_context
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret')
 result=generate_insights(catalog,settings,lambda c,s:request_llm(c,s,httpx.MockTransport(lambda _:httpx.Response(status,json={'detail':'test-secret'}))))
 assert result['source']=='rules' and result['fallback_reason']=='provider_error'
 assert 'test-secret' not in json.dumps(result)


def test_nvidia_timeout_and_missing_configuration(insight_context):
 db,catalog=insight_context
 def timeout(request): raise httpx.ReadTimeout('test-secret')
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret')
 result=generate_insights(catalog,settings,lambda c,s:request_llm(c,s,httpx.MockTransport(timeout)))
 assert result['source']=='rules' and result['fallback_reason']=='timeout'
 def forbidden(*_): raise AssertionError('Wrong or unconfigured provider must not be called')
 for settings in [Settings(db,llm_provider='nvidia',openai_api_key='test-secret'),Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret',nvidia_model='')]:
  assert generate_insights(catalog,settings,forbidden)['fallback_reason']=='not_configured'


def test_nvidia_env_configuration(monkeypatch):
 monkeypatch.setenv('LLM_PROVIDER','NVIDIA')
 monkeypatch.setenv('NVIDIA_API_KEY','test-secret')
 monkeypatch.setenv('NVIDIA_MODEL',' meta/llama-3.2-11b-vision-instruct ')
 settings=Settings.from_env()
 assert settings.llm_provider=='nvidia' and settings.llm_configured
 assert settings.nvidia_model=='meta/llama-3.2-11b-vision-instruct'
 assert 'test-secret' not in repr(settings)
 monkeypatch.setenv('LLM_PROVIDER','unsupported')
 with pytest.raises(ValueError,match='LLM_PROVIDER'): Settings.from_env()


def test_nvidia_11b_uses_shared_route_with_text_only_input(insight_context):
 db,catalog=insight_context
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret',nvidia_model='meta/llama-3.2-11b-vision-instruct')
 selection={'headline_id':'scope','finding_ids':['scope','topic_sizing'],'action_ids':['topic_sizing']}
 def handler(request):
  assert request.url=='https://integrate.api.nvidia.com/v1/chat/completions'
  assert request.headers['authorization']=='Bearer test-secret'
  body=json.loads(request.content)
  assert body['model']=='meta/llama-3.2-11b-vision-instruct'
  assert body['stream'] is False and body['max_tokens']==600
  assert len(body['messages'])==2 and body['messages'][0]['role']=='system'
  assert body['messages'][1]['role']=='user'
  assert 'MUST include' in body['messages'][0]['content']
  content=body['messages'][1]['content']
  assert isinstance(content,str)
  data=json.loads(content)
  assert len(data['samples'])<=20 and 'customer@example.com' not in content
  assert '555-0199' not in content and 'image_url' not in body
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(selection)}}]})
 result=generate_insights(catalog,settings,lambda c,s:request_llm(c,s,httpx.MockTransport(handler)))
 assert result['source']=='llm' and result['fallback_reason'] is None
 verify_evidence(result)


def test_lightning_selection_disables_thinking_and_validates_evidence(insight_context):
 db,catalog=insight_context
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret')
 def handler(request):
  body=json.loads(request.content)
  assert body['model']=='nvidia/nemotron-3.5-lightning-30b-a3b'
  assert body['chat_template_kwargs']=={'enable_thinking':False}
  selection={'headline_id':'scope','finding_ids':['scope','topic_sizing'],'action_ids':['topic_sizing']}
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(selection)}}]})
 result=generate_insights(catalog,settings,lambda c,s:request_llm(c,s,httpx.MockTransport(handler)))
 assert result['source']=='llm'
 verify_evidence(result)


def test_lightning_is_default_but_legacy_models_keep_compatible_payload():
 from backend.app.services.nvidia import LIGHTNING_MODEL,chat_options
 assert Settings.__dataclass_fields__['nvidia_model'].default==LIGHTNING_MODEL
 assert chat_options('meta/llama-3.2-11b-vision-instruct')=={}


def test_nvidia_offered_catalog_fits_selection_limits(insight_context):
 db,catalog=insight_context
 catalog['findings'].update({f'extra_{i}':{'text':'Synthetic','evidence_ids':[]} for i in range(20)})
 catalog['actions'].update({f'extra_{i}':{'text':'Synthetic','evidence_ids':[]} for i in range(20)})
 def handler(request):
  data=json.loads(json.loads(request.content)['messages'][1]['content'])
  assert len(data['findings'])==8 and len(data['actions'])==5
  assert 'scope' in data['findings']
  content=json.dumps({'headline_id':'scope','finding_ids':list(data['findings']),'action_ids':list(data['actions'])})
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':content}}]})
 from backend.app.services.insights import request_nvidia,Selection
 settings=Settings(db,llm_provider='nvidia',nvidia_api_key='test-secret')
 Selection.model_validate(request_nvidia(catalog,settings,httpx.MockTransport(handler)))
