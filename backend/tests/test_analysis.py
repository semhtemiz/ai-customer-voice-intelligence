import pytest
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.db import connect
from backend.app.importer import import_reviews
from backend.app.main import create_app
from backend.app.services.analysis import run_analysis
from backend.app.services.topics import classify_topics
REVISION='a'*40

def test_actual_job_cache_subset_and_topic_candidates(write_csv,tmp_path):
 db=tmp_path/'job.db';import_reviews(write_csv([
  {'Review Text':'Too small and very itchy. Bad quality.','Rating':'1'},
  {'Review Text':'Absolutely wonderful.','Rating':'5'},
  {'Review Text':'Late delivery; customer service never replied.','Rating':'4'},
  {'Review Text':' ','Rating':'1'},
 ]),db)
 calls=[]
 def predict(texts):
  calls.extend(texts)
  return [('positive' if 'wonderful' in text else 'negative',0.9) for text in texts]
 result=run_analysis(db,'sentiment',predict=predict,model_id='test',revision=REVISION,batch_size=2)
 assert result['eligible_count']==3 and result['processed_count']==3
 assert len(calls)==3
 cached=run_analysis(db,'sentiment',predict=predict,model_id='test',revision=REVISION,batch_size=2)
 assert len(calls)==3 and cached['cached_count']==3
 topics=run_analysis(db,'topics')
 assert topics['eligible_count']==2 and topics['processed_count']==2
 with TestClient(create_app(Settings(db))) as client:
  sentiments=client.get('/api/sentiments').json()['data']
  assert {r['sentiment']:r['reviews'] for r in sentiments['distribution']}=={'negative':2,'positive':1,'neutral':0,'unknown':1}
  data=client.get('/api/topics').json()['data']
  assert data['candidate_count']==data['topic_processed_count']==2
  assert data['topic_failed_count']==data['topic_pending_count']==0
  assert sum(row['mentions'] for row in data['distribution'])==4
  assert sum(row['rate_pct'] for row in data['distribution'])==200
  evidence=client.get('/api/topics/sizing/examples').json()
  assert [r['review_id'] for r in evidence['data']]==[0]
  assert evidence['meta']['matched_review_count']==4
  assert client.get('/api/topics/shipping/examples',params={'rating':1}).json()['data']==[]
  assert client.get('/api/topics/nonexistent/examples').status_code==404
  empty=client.get('/api/topics',params={'sentiment':'neutral'}).json()['data']
  assert empty['candidate_count']==0 and all(r['rate_pct'] is None for r in empty['distribution'])
 # Selecting a new sentiment run must invalidate the selected topic run.
 run_analysis(db,'sentiment',predict=predict,model_id='new-test',revision=REVISION,limit=1)
 with connect(db,readonly=True) as c:
  assert c.execute('SELECT selected_topic_run_id FROM import_state').fetchone()[0] is None
 with TestClient(create_app(Settings(db))) as client:
  result=client.get('/api/topics').json()['data']
  assert result['topic_processed_count']==0 and result['topic_pending_count']==result['candidate_count']


def test_failed_model_preserves_old_selected_run_and_resume_uses_cache(write_csv,tmp_path):
 db=tmp_path/'job.db';import_reviews(write_csv([{},{}]),db)
 run_analysis(db,'sentiment',predict=lambda texts:[('positive',0.8)]*len(texts),model_id='old',revision=REVISION)
 with connect(db,readonly=True) as c: old=c.execute('SELECT selected_sentiment_run_id FROM import_state').fetchone()[0]
 count=0
 def fail(texts):
  nonlocal count
  count+=1
  if count==2: raise RuntimeError('model unavailable')
  return [('negative',0.8)]*len(texts)
 with pytest.raises(RuntimeError): run_analysis(db,'sentiment',predict=fail,model_id='new',revision=REVISION,batch_size=1)
 with connect(db,readonly=True) as c:
  assert c.execute('SELECT selected_sentiment_run_id FROM import_state').fetchone()[0]==old
 resumed=run_analysis(db,'sentiment',predict=lambda texts:[('negative',0.8)]*len(texts),model_id='new',revision=REVISION,batch_size=1)
 assert resumed['cached_count']==1


def test_dataset_change_during_job_cannot_promote_stale_run(write_csv,tmp_path):
 db=tmp_path/'job.db';source=write_csv([{}]);import_reviews(source,db)
 def mutate(texts):
  import_reviews(write_csv([{'Rating':'1'}]),db)
  return [('negative',0.8)]*len(texts)
 with pytest.raises(ValueError,match='Dataset changed'):
  run_analysis(db,'sentiment',predict=mutate,model_id='test',revision=REVISION)
 with connect(db,readonly=True) as c:
  assert c.execute('SELECT selected_sentiment_run_id FROM import_state').fetchone()[0] is None


@pytest.mark.parametrize('text,expected',[
 ('Too tight and the fabric is sheer.',['sizing','fabric_quality']),
 ('The package was late.',['shipping']),
 ('It arrived yesterday and fits true to size.',['other']),
 ('Not itchy and not too small.',['other']),
 ('The print was ugly.',['color_appearance']),
 ('Customer service never replied.',['customer_service']),
])
def test_conservative_topic_phrases(text,expected): assert classify_topics(text)==expected


def test_evidence_limit_masking_historical_and_failed_exclusion(write_csv,tmp_path):
 db=tmp_path/'job.db';import_reviews(write_csv([{'Rating':'1','Review Text':'Too small. email test@example.com'} for _ in range(25)]),db)
 run_analysis(db,'topics')
 with TestClient(create_app(Settings(db))) as client:
  evidence=client.get('/api/topics/sizing/examples').json()['data']
  assert len(evidence)==20 and [r['review_id'] for r in evidence]==list(range(20))
  assert all('test@example.com' not in r['review_text'] for r in evidence)
 with connect(db) as c:
  selected=c.execute('SELECT selected_topic_run_id FROM import_state').fetchone()[0]
  c.execute("UPDATE review_topic_results SET status='failed' WHERE review_id=0 AND run_id=?",(selected,));c.commit()
 with TestClient(create_app(Settings(db))) as client:
  data=client.get('/api/topics').json()['data']
  assert data['topic_processed_count']==24 and data['topic_failed_count']==1
  assert next(row for row in data['distribution'] if row['topic']=='sizing')['mentions']==24
  assert client.get('/api/topics/sizing/examples').json()['data'][0]['review_id']==1


@pytest.mark.parametrize('kind',['sentiment','topics'])
def test_reusing_completed_cache_never_hides_selected_results(write_csv,tmp_path,monkeypatch,kind):
 from backend.app.services import analysis
 from backend.app.analytics import Analytics
 from backend.app.schemas import Filters
 db=tmp_path/'reuse.db';import_reviews(write_csv([{'Rating':'1','Review Text':'Too small and itchy'},{'Rating':'2','Review Text':'Too tight'}]),db)
 kwargs={'predict':lambda texts:[('negative',0.8)]*len(texts),'model_id':'test','revision':REVISION}
 run_analysis(db,'sentiment',**kwargs)
 if kind=='topics':run_analysis(db,'topics')
 with connect(db,readonly=True) as c:
  identifier=c.execute(f'SELECT selected_{"sentiment" if kind=="sentiment" else "topic"}_run_id FROM import_state').fetchone()[0]
  completed_at=c.execute('SELECT completed_at FROM analysis_runs WHERE run_id=?',(identifier,)).fetchone()[0]
 observed=[];original_now=analysis.now
 def observe():
  with connect(db,readonly=True) as c:
   service=Analytics(c,c.execute('SELECT * FROM import_state').fetchone(),Filters())
   observed.append(service.meta()['sentiment_classified_count'] if kind=='sentiment' else service.topics()['topic_processed_count'])
  return original_now()
 monkeypatch.setattr(analysis,'now',observe)
 result=run_analysis(db,kind,**(kwargs if kind=='sentiment' else {}))
 assert observed and all(count==2 for count in observed)
 assert result['cached_count']==2
 with connect(db,readonly=True) as c:
  row=c.execute('SELECT status,completed_at FROM analysis_runs WHERE run_id=?',(identifier,)).fetchone()
  assert row['status']=='completed' and row['completed_at']==completed_at
