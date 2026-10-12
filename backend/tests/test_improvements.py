import pytest
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.db import connect, initialize_schema, SCHEMA_PATH
from backend.app.importer import import_reviews
from backend.app.main import create_app
from backend.app.services.analysis import run_analysis
from backend.app.services.topics import classify_topics

@pytest.mark.parametrize('text,labels',[
 ('A huge tag, but the shirt fits well.', ['other']),
 ('Customer service was wonderful.', ['other']),
 ('Looks like it shrunk in the wash.', ['other']),
 ('The fabric is stiffer than expected.', ['fabric_quality']),
 ('It is not overpriced and not itchy.', ['other']),
 ('The color is different from the photo and it is overpriced.', ['color_appearance','value_price']),
 ('The design was ugly.', ['style_design']),
 ('The top is enormous.', ['sizing']),
 ('Love the stretch fabric.', ['other']),
 ('The color was not ugly.', ['other']),
 ('I avoid expensive shipping costs.', ['other']),
])
def test_topic_context(text,labels):
 assert classify_topics(text)==labels


def test_positive_local_complaint_and_priorities_share_filters(write_csv,tmp_path):
 db=tmp_path/'reviews.db'
 rows=[{'Clothing ID':'77','Department Name':'Tops','Rating':'5','Review Text':'Love it but the fabric is itchy.'} for _ in range(10)]
 rows += [{'Clothing ID':'77','Department Name':'Tops','Rating':'1','Review Text':'Wonderful overall.'},
          {'Clothing ID':'88','Department Name':'Dresses','Rating':'1','Review Text':'Too small'}]
 import_reviews(write_csv(rows),db)
 run_analysis(db,'sentiment',predict=lambda texts:[('positive',.9)]*len(texts),model_id='test',revision='a'*40)
 run_analysis(db,'topics')
 with TestClient(create_app(Settings(db))) as client:
  topic=client.get('/api/topics',params={'department':'Tops','rating':5}).json()
  assert topic['data']['candidate_count']==topic['data']['topic_processed_count']==10
  assert next(t['mentions'] for t in topic['data']['distribution'] if t['topic']=='fabric_quality')==10
  data=client.get('/api/priorities',params={'department':'Tops'}).json()['data']
  assert len(data['products'])==1 and data['products'][0]['clothing_id']==77
  assert data['products'][0]['valid_rating_count']==11
  assert data['products'][0]['low_rating_count']==1
  assert data['products'][0]['topics']==[{'topic':'fabric_quality','mentions':10},{'topic':'other','mentions':1}]
  assert data['disagreement_count']==1 and data['compared_count']==11
  assert [r['review_id'] for r in data['disagreement_examples']]==[10]
  empty=client.get('/api/priorities',params={'search':'No such review 987654'}).json()['data']
  assert empty['products']==[] and empty['disagreement_count']==empty['compared_count']==0
  assert client.get('/api/evaluation/form').status_code==404
  assert client.post('/api/evaluation/labels',json={}).status_code==404


def test_v1_migration_preserves_predictions_topics_and_selected_runs(write_csv,tmp_path):
 db=tmp_path/'legacy.db';source=write_csv([{'Rating':'1','Review Text':'Too small'}])
 # Create the old schema, including its restrictive topic CHECK.
 legacy=SCHEMA_PATH.read_text().replace("'color_appearance', 'style_design', 'value_price', ",'')
 with connect(db) as c:
  c.executescript(legacy);c.execute('PRAGMA user_version=1');c.commit()
 import_reviews(source,db)
 run_analysis(db,'sentiment',predict=lambda texts:[('negative',.9)]*len(texts),model_id='test',revision='a'*40)
 run_analysis(db,'topics')
 with connect(db) as c:
  before=[tuple(row) for row in c.execute('SELECT * FROM review_topics')]
  chosen=tuple(c.execute('SELECT selected_sentiment_run_id,selected_topic_run_id FROM import_state').fetchone())
  c.execute('PRAGMA user_version=1');c.commit()
 assert import_reviews(source,db)['status']=='unchanged'
 with connect(db) as c:
  assert c.execute('PRAGMA user_version').fetchone()[0]==2
  assert [tuple(row) for row in c.execute('SELECT * FROM review_topics')]==before
  assert tuple(c.execute('SELECT selected_sentiment_run_id,selected_topic_run_id FROM import_state').fetchone())==chosen
  c.execute('INSERT INTO review_topics VALUES (?,?,?)',(before[0][0],before[0][1],'color_appearance'))
  assert c.execute('PRAGMA foreign_key_check').fetchone() is None
