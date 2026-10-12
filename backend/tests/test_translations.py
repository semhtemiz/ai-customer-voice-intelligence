import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.importer import import_reviews
from backend.app.main import create_app
from backend.app.services import translations


@pytest.fixture
def context(write_csv,tmp_path):
 db=tmp_path/'reviews.db'
 import_reviews(write_csv([
  {'Title':'Lovely fit','Review Text':'Good fit. customer@example.com'},
  {'Title':'','Review Text':'','Rating':'1'},
 ]),db)
 return Settings(db,nvidia_api_key='test-secret')


def translated(items,settings):
 return {'items':[{'review_id':r['review_id'],'title':'Güzel kalıp' if r['title'] else None,'review_text':'Güzel kalıp. [email]' if r['review_text'] else None} for r in items]}


def test_route_translation_cache_source_unchanged_and_nulls(context,monkeypatch):
 calls=[]
 def provider(items,settings):
  calls.append(items)
  assert items[0]['review_text']=='Good fit. [email]'
  return translated(items,settings)
 monkeypatch.setattr(translations,'request_translation',provider)
 with TestClient(create_app(context)) as client:
  first=client.post('/api/reviews/translations',json={'review_ids':[0,1]})
  assert first.status_code==200
  data=first.json();assert data['language']=='tr'
  assert data['items'][0]['title']=='Güzel kalıp'
  assert data['items'][1]['title'] is None and data['items'][1]['review_text'] is None
  assert client.post('/api/reviews/translations',json={'review_ids':[0,1]}).json()==data
  assert len(calls)==1
  source=client.get('/api/reviews').json()['items'][0]
  assert source['title']=='Lovely fit' and source['review_text']=='Good fit. [email]'


@pytest.mark.parametrize('body',[{'review_ids':[]},{'review_ids':[0]*6},{'review_ids':[0,0]},{'review_ids':[-1]},{'review_ids':['0']},{'review_ids':[True]},{'review_ids':[0],'review_text':'arbitrary input'}])
def test_translation_request_is_bounded_ids_only(context,body):
 with TestClient(create_app(context)) as client:
  assert client.post('/api/reviews/translations',json=body).status_code==422


def test_missing_id_and_unconfigured_translation(context):
 with TestClient(create_app(replace(context,nvidia_api_key=None))) as client:
  assert client.post('/api/reviews/translations',json={'review_ids':[999]}).status_code==404
  assert client.post('/api/reviews/translations',json={'review_ids':[0]}).status_code==503
  blank=client.post('/api/reviews/translations',json={'review_ids':[1]})
  assert blank.status_code==200 and blank.json()['items'][0]['review_text'] is None


@pytest.mark.parametrize('output',[
 {'items':[{'review_id':99,'title':'Başlık','review_text':'Metin'}]},
 {'items':[{'review_id':0,'title':None,'review_text':'Metin'}]},
 {'items':[{'review_id':0,'title':'Başlık','review_text':' '}]},
 {'items':[{'review_id':0,'title':'Başlık','review_text':'Metin','rating':5}]},
 {'items':[{'review_id':0,'title':'Başlık','review_text':'Metin'}]*2},
 {'items':[]},
])
def test_bad_output_is_not_cached(context,monkeypatch,output):
 monkeypatch.setattr(translations,'request_translation',lambda *_:output)
 with TestClient(create_app(context)) as client:
  assert client.post('/api/reviews/translations',json={'review_ids':[0]}).status_code==502
  monkeypatch.setattr(translations,'request_translation',translated)
  assert client.post('/api/reviews/translations',json={'review_ids':[0]}).status_code==200


@pytest.mark.parametrize('error,status',[(httpx.ReadTimeout('test-secret'),504),(httpx.ConnectError('test-secret'),502)])
def test_translation_failure_is_safe(context,monkeypatch,error,status):
 def provider(*_):raise error
 monkeypatch.setattr(translations,'request_translation',provider)
 with TestClient(create_app(context)) as client:
  result=client.post('/api/reviews/translations',json={'review_ids':[0]})
  assert result.status_code==status and 'test-secret' not in result.text


def test_cache_bound_to_checksum_model_and_source(context):
 calls=[]
 def provider(items,settings): calls.append(items);return translated(items,settings)
 items=[{'review_id':0,'title':'Lovely fit','review_text':'Good fit.'}]
 for checksum,settings,source in [('a',context,items),('a',context,items),('b',context,items),('a',replace(context,nvidia_translation_model='other'),items),('a',context,[dict(items[0],review_text='Changed text')])]:
  translations.translate_reviews(source,checksum,settings,provider)
 assert len(calls)==4


def test_translation_http_payload(context):
 items=[{'review_id':0,'title':'Lovely fit','review_text':'Good fit. [email]'}]
 def handler(request):
  assert request.url=='https://integrate.api.nvidia.com/v1/chat/completions'
  assert request.headers['authorization']=='Bearer test-secret'
  body=json.loads(request.content);assert body['model']==context.nvidia_translation_model
  assert body['stream'] is False and body['max_tokens']==8192
  assert body['chat_template_kwargs']=={'enable_thinking':False}
  assert json.loads(body['messages'][1]['content'])['items']==items
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(translated(items,context))}}]})
 result=translations.request_translation(items,context,httpx.MockTransport(handler))
 assert result['items'][0]['review_text']=='Güzel kalıp. [email]'


@pytest.mark.parametrize('body',[[],{'choices':[]},{'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},{'choices':[{'finish_reason':'stop','message':{'refusal':'no','content':'{}'}}]}])
def test_translation_incomplete_provider_output(context,body):
 with pytest.raises(ValueError):
  translations.request_translation([],context,httpx.MockTransport(lambda _:httpx.Response(200,json=body)))


def test_summary_model_does_not_invalidate_translation_cache(context):
 calls=[]
 def provider(items,settings):calls.append(items);return translated(items,settings)
 items=[{'review_id':0,'title':'Lovely fit','review_text':'Good fit.'}]
 translations.translate_reviews(items,'same',context,provider)
 translations.translate_reviews(items,'same',replace(context,nvidia_model='different-summary'),provider)
 assert len(calls)==1


def test_translation_version_is_part_of_cache_key(context,monkeypatch):
 calls=[]
 def provider(items,settings):calls.append(items);return translated(items,settings)
 items=[{'review_id':0,'title':'Lovely fit','review_text':'Good fit.'}]
 translations.translate_reviews(items,'same',context,provider)
 monkeypatch.setattr(translations,'TRANSLATION_VERSION','new-prompt')
 translations.translate_reviews(items,'same',context,provider)
 assert len(calls)==2


def test_measurements_restored_without_model_conversions(context):
 items=[{'review_id':0,'title':None,'review_text':'I am just under 5 feet tall, 125 lbs and wear a 0p.'}]
 def handler(request):
  source=json.loads(request.content)['messages'][1]['content']
  text=json.loads(source)['items'][0]['review_text']
  assert '5 feet' not in text and '125 lbs' not in text and '0p' not in text
  tokens=list(__import__('re').findall(r'__MEASURE_\w+__',text))
  output={'items':[{'review_id':0,'title':None,'review_text':f'Boyum {tokens[0]} altında, {tokens[1]} ve {tokens[2]} giyiyorum.'}]}
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(output)}}]})
 result=translations.request_translation(items,context,httpx.MockTransport(handler))
 assert result['items'][0]['review_text']=='Boyum just under 5 feet altında, 125 lbs ve 0p giyiyorum.'


def test_lost_measurement_is_rejected(context):
 items=[{'review_id':0,'title':None,'review_text':'5 feet tall'}]
 with pytest.raises(ValueError,match='Measurement preservation'):
  translations.request_translation(items,context,httpx.MockTransport(lambda _:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'items':[{'review_id':0,'title':None,'review_text':'5 aylık'}]})}}]})))


def test_unexpected_script_falls_back_without_caching(context):
 with pytest.raises(ValueError,match='Unexpected script'):
  translations.translate_reviews([{'review_id':0,'title':None,'review_text':'A dress.'}],'same',context,lambda *_:{'items':[{'review_id':0,'title':None,'review_text':'Türkçe giย์'}]})
