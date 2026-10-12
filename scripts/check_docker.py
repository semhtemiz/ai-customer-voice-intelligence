"""Check local Docker API/proxy without sending data to any LLM provider."""
import json
from urllib.request import urlopen


def fetch(url):
    with urlopen(url,timeout=10) as response:
        if response.status!=200:raise RuntimeError(f'Unexpected HTTP status for {url}')
        return json.load(response)


def main():
    assert fetch('http://localhost:8000/health')['database_ready']
    for endpoint in ('overview','ratings','sentiments','topics','data-quality','reviews','priorities'):
        path=f'/api/{endpoint}?department=Tops&rating=1'
        direct=fetch('http://localhost:8000'+path)
        proxied=fetch('http://localhost:3000'+path)
        assert direct==proxied,f'Proxy mismatch: {endpoint}'
        print(f'PASS: {endpoint} shared-filter response matches API and frontend proxy')
    result=fetch('http://localhost:3000/api/overview')
    print('Review count:',result['data']['total_reviews'])
    print('Sentiment coverage:',result['meta']['sentiment_processed_count'],'/',result['meta']['text_review_count'])


if __name__=='__main__':main()
