import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.db import connect
from backend.app.importer import import_reviews
from backend.app.main import create_app


@pytest.fixture
def api(write_csv, tmp_path):
    source = write_csv([
        {'': '10', 'Rating': '1', 'Recommended IND': '0', 'Review Text': 'Bad fit 100%_\\', 'Title': 'Issue'},
        {'': '20', 'Rating': '5', 'Recommended IND': '1', 'Review Text': 'Wonderful fit'},
        {'': '30', 'Rating': 'bad', 'Recommended IND': '', 'Age': '0', 'Review Text': ' ', 'Title': '',
         'Department Name': '', 'Class Name': '', 'Division Name': ''},
        {'': '40', 'Rating': '4', 'Recommended IND': '1', 'Department Name': 'Dresses', 'Class Name': 'Dresses',
         'Review Text': 'Email test@example.com or +1 (212) 555-0199'},
    ])
    db = tmp_path / 'reviews.db'
    import_reviews(source, db)
    with TestClient(create_app(Settings(db))) as client:
        yield client, db


def test_kpi_denominators_and_unknown_predictions(api):
    client, _ = api
    result = client.get('/api/overview').json()
    assert result['data'] == {'total_reviews': 4, 'valid_rating_count': 3, 'valid_recommendation_count': 3,
                              'avg_rating': 3.33, 'recommendation_rate_pct': 66.67, 'low_rating_rate_pct': 33.33}
    assert result['meta']['text_review_count'] == 3
    assert result['meta']['sentiment_classified_count'] == 0
    assert result['meta']['sentiment_method'] is None
    assert result['meta']['sentiment_run_id'] is None
    assert result['meta']['topic_run_id'] is None
    items = client.get('/api/reviews').json()['items']
    assert all(row['sentiment'] == 'unknown' and row['sentiment_score'] is None for row in items)
    assert all(row['complaint_topics'] == [] for row in items)


def test_concurrent_dashboard_requests_use_independent_connections(api):
    client, _ = api
    endpoints = ['overview','ratings','categories','filter-options'] * 4
    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda endpoint: client.get('/api/'+endpoint), endpoints))
    assert all(response.status_code == 200 for response in responses)


@pytest.mark.parametrize('params,expected', [
    ({'department':'Tops'}, [10,20]), ({'class_name':'Dresses'}, [40]),
    ({'rating':1}, [10]), ({'department':'Unknown','class_name':'Unknown'}, [30]),
    ({'search':'WONDERFUL'}, [20]), ({'search':'issue'}, [10]),
    ({'search':'100%_\\'}, [10]), ({'search':"' OR 1=1 --"}, []),
    ({'department':'Tops','rating':5,'search':'fit','sentiment':'unknown'}, [20]),
    ({'sentiment':'negative'}, []), ({'department':'  Tops  '}, [10,20]),
])
def test_shared_filters_across_all_analytics(api, params, expected):
    client, _ = api
    reviews = client.get('/api/reviews', params=params)
    assert reviews.status_code == 200
    assert [row['review_id'] for row in reviews.json()['items']] == expected
    for endpoint in ('overview','ratings','categories','data-quality'):
        response = client.get('/api/'+endpoint, params=params)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['meta']['matched_review_count'] == len(expected)
        assert result['meta'] == reviews.json()['meta']
        if endpoint == 'overview':
            assert result['data']['total_reviews'] == len(expected)
        elif endpoint == 'categories':
            assert sum(row['reviews'] for row in result['data']) == len(expected)
        elif endpoint == 'ratings':
            assert sum(row['reviews'] for row in result['data']['distribution']) + result['data']['invalid_or_missing_rating_count'] == len(expected)
        else:
            assert result['data']['filtered_quality']['review_count'] == len(expected)


def test_like_wildcards_are_literal(api):
    client, _ = api
    for search in ('%', '_', '\\'):
        assert [row['review_id'] for row in client.get('/api/reviews',params={'search':search}).json()['items']] == [10]


def test_empty_results_preserve_null_and_zero(api):
    client, _ = api
    params = {'department':'No match'}
    overview = client.get('/api/overview',params=params).json()['data']
    assert overview['total_reviews'] == 0
    assert overview['valid_rating_count'] == overview['valid_recommendation_count'] == 0
    assert overview['avg_rating'] is overview['recommendation_rate_pct'] is overview['low_rating_rate_pct'] is None
    assert client.get('/api/categories',params=params).json()['data'] == []
    ratings = client.get('/api/ratings',params=params).json()['data']
    assert [row['reviews'] for row in ratings['distribution']] == [0]*5
    reviews = client.get('/api/reviews',params=params).json()
    assert reviews['items'] == [] and reviews['total_pages'] == 0


def test_pagination_is_stable_and_bounded(api):
    client, _ = api
    first = client.get('/api/reviews',params={'page':1,'page_size':2}).json()
    second = client.get('/api/reviews',params={'page':2,'page_size':2}).json()
    assert [row['review_id'] for row in first['items'] + second['items']] == [10,20,30,40]
    assert first['total'] == 4 and first['total_pages'] == 2
    for page in (3, 10**30):
        response = client.get('/api/reviews',params={'page':page,'page_size':2})
        assert response.status_code == 200
        assert response.json()['items'] == []
    assert client.get('/api/reviews',params={'page_size':100}).status_code == 200


@pytest.mark.parametrize('endpoint,params', [
    ('reviews',{'page':0}), ('reviews',{'page_size':101}), ('reviews',{'page_size':0}),
    ('reviews',{'page':'abc'}), ('overview',{'rating':0}), ('ratings',{'rating':6}),
    ('categories',{'sentiment':'made-up'}), ('data-quality',{'search':'a'*201}),
    ('overview',{'department':'a'*101}), ('reviews',{'unexpected':'bad'}),
    ('filter-options',{'rating':1}),
])
def test_invalid_queries_return_422(api, endpoint, params):
    client, _ = api
    assert client.get('/api/'+endpoint,params=params).status_code == 422


def test_import_quality_and_filtered_quality_have_distinct_scopes(api):
    client, _ = api
    result = client.get('/api/data-quality',params={'department':'Tops'}).json()['data']
    assert result['import_report']['row_count'] == 4
    assert result['import_report']['invalid_rating_count'] == 1
    assert result['import_report']['file'] == 'reviews.csv'
    assert result['filtered_quality']['review_count'] == 2
    assert result['filtered_quality']['missing_text_count'] == 0
    missing = client.get('/api/data-quality',params={'department':'Unknown'}).json()['data']['filtered_quality']
    assert all(missing[key] == 1 for key in missing)


def test_filter_options_use_global_departments_and_scoped_classes(api):
    client, _ = api
    options = client.get('/api/filter-options',params={'department':'Tops'}).json()['data']
    assert options['departments'] == ['Dresses','Tops','Unknown']
    assert options['classes'] == ['Blouses']
    assert options['ratings'] == [1,2,3,4,5]
    assert options['sentiments'] == ['positive','neutral','negative','unknown']
    assert client.get('/api/filter-options',params={'department':'Unknown'}).json()['data']['classes'] == ['Unknown']
    assert client.get('/api/filter-options',params={'department':'missing'}).json()['data']['classes'] == []


def test_review_text_is_masked_but_source_is_preserved(api):
    client, db = api
    item = client.get('/api/reviews',params={'department':'Dresses'}).json()['items'][0]
    assert 'test@example.com' not in item['review_text'] and '555-0199' not in item['review_text']
    assert '[email]' in item['review_text'] and '[phone]' in item['review_text']
    assert 'age' not in item
    with connect(db,readonly=True) as connection:
        assert 'test@example.com' in connection.execute('SELECT review_text FROM reviews WHERE review_id=40').fetchone()[0]


def test_only_selected_compatible_completed_run_is_used(api):
    client, db = api
    with connect(db) as connection:
        checksum = connection.execute('SELECT dataset_sha256 FROM import_state').fetchone()[0]
        for run, status, sha in [('selected','completed',checksum),('historical','completed',checksum),
                                 ('failed','failed',checksum),('stale','completed','old-checksum')]:
            connection.execute('''INSERT INTO analysis_runs
                (run_id,kind,method,dataset_sha256,started_at,status,eligible_count,processed_count)
                VALUES (?,'sentiment','test-model',?,'test',?,3,1)''',(run,sha,status))
            connection.execute('INSERT INTO review_predictions VALUES (10,?, ?,0.8)',
                               (run,'negative' if run=='selected' else 'positive'))
        connection.execute("UPDATE import_state SET selected_sentiment_run_id='selected'")
        connection.commit()
    result = client.get('/api/overview',params={'sentiment':'negative'}).json()
    assert result['data']['total_reviews'] == 1 and result['meta']['sentiment_classified_count'] == 1
    assert result['meta']['sentiment_run_id'] == 'selected'
    assert client.get('/api/reviews',params={'sentiment':'positive'}).json()['total'] == 0
    assert client.get('/api/reviews',params={'sentiment':'unknown'}).json()['total'] == 3
    for invalid in ('failed','stale','historical'):
        with connect(db) as connection:
            connection.execute('UPDATE import_state SET selected_sentiment_run_id=?',(invalid,))
            connection.commit()
        result = client.get('/api/overview').json()
        if invalid != 'historical':
            assert result['meta']['sentiment_run_id'] is None
            assert result['meta']['sentiment_classified_count'] == 0
        else:
            assert result['meta']['sentiment_run_id'] == 'historical'


def test_multi_topic_rows_do_not_multiply_reviews_and_incompatible_topics_are_hidden(api):
    client, db = api
    with connect(db) as connection:
        checksum = connection.execute('SELECT dataset_sha256 FROM import_state').fetchone()[0]
        connection.execute('''INSERT INTO analysis_runs
            (run_id,kind,method,dataset_sha256,started_at,status,eligible_count,processed_count)
            VALUES ('s','sentiment','rating_heuristic',?,'test','completed',3,1)''',(checksum,))
        connection.execute('''INSERT INTO analysis_runs
            (run_id,kind,method,dataset_sha256,source_sentiment_run_id,started_at,status,eligible_count,processed_count)
            VALUES ('t','topics','keywords',?,'s','test','completed',1,1)''',(checksum,))
        connection.execute("INSERT INTO review_predictions VALUES (10,'s','negative',NULL)")
        # A prediction attached to a blank comment must still be unknown/excluded.
        connection.execute("INSERT INTO review_predictions VALUES (30,'s','positive',NULL)")
        connection.execute("INSERT INTO review_topic_results VALUES (10,'t','completed')")
        for topic in ('sizing','fabric_quality'):
            connection.execute("INSERT INTO review_topics VALUES (10,'t',?)",(topic,))
        connection.execute("UPDATE import_state SET selected_sentiment_run_id='s',selected_topic_run_id='t'")
        connection.commit()
    result = client.get('/api/reviews').json()
    assert result['total'] == 4 and len(result['items']) == 4
    assert result['items'][0]['complaint_topics'] == ['fabric_quality','sizing']
    assert result['meta']['topic_run_id'] == 't'
    assert result['meta']['sentiment_classified_count'] == 1
    assert any('heuristic' in text for text in result['meta']['limitations'])
    assert client.get('/api/reviews',params={'sentiment':'positive'}).json()['total'] == 0
    with connect(db) as connection:
        connection.execute("UPDATE analysis_runs SET source_sentiment_run_id=NULL WHERE run_id='t'")
        connection.commit()
    result = client.get('/api/reviews').json()
    assert result['meta']['topic_run_id'] is None
    assert result['items'][0]['complaint_topics'] == []


def test_blank_title_quality_and_null_category_metric(api):
    client, db = api
    with connect(db) as connection:
        connection.execute("UPDATE reviews SET title=' \t\n ' WHERE review_id=30")
        connection.commit()
    quality = client.get('/api/data-quality',params={'department':'Unknown'}).json()['data']['filtered_quality']
    assert quality['missing_title_count'] == 1
    category = client.get('/api/categories',params={'department':'Unknown'}).json()['data'][0]
    assert category['reviews'] == 1 and category['valid_rating_count'] == 0
    assert category['avg_rating'] is None and category['low_rating_rate_pct'] is None


@pytest.mark.parametrize('endpoint',['overview','ratings','categories','reviews','data-quality','filter-options'])
def test_unready_database_returns_safe_503(tmp_path, endpoint):
    with TestClient(create_app(Settings(tmp_path/'missing.db'))) as client:
        result = client.get('/api/'+endpoint)
        assert result.status_code == 503
        assert result.json() == {'detail':'Database is not ready'}


def test_real_dataset_sql_and_api_match_independent_profile(tmp_path):
    source = PROJECT_ROOT/'dataset/Womens Clothing E-Commerce Reviews.csv'
    if not source.exists():
        pytest.skip('Local raw dataset is not distributed with the repository')
    db = tmp_path/'real.db'
    import_reviews(source,db)
    profile = json.loads((PROJECT_ROOT/'dataset/profile.json').read_text())
    with TestClient(create_app(Settings(db))) as client:
        result = client.get('/api/overview')
        assert result.status_code == 200
        for key,value in result.json()['data'].items():
            assert value == profile['kpis'][key]
        ratings = client.get('/api/ratings').json()['data']['distribution']
        assert {str(row['rating']):row['reviews'] for row in ratings} == profile['rating_counts']
        categories = client.get('/api/categories').json()['data']
        assert {row['department']:row['reviews'] for row in categories} == profile['department_counts']
        schema = client.get('/openapi.json').json()
        for endpoint in ('overview','ratings','categories','reviews','data-quality','filter-options'):
            assert 'application/json' in schema['paths']['/api/'+endpoint]['get']['responses']['200']['content']
        assert schema['components']['schemas']['Overview']['examples'][0]['total_reviews'] == 0
