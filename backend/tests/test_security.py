import pytest
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_app

@pytest.fixture
def client(tmp_path):
 with TestClient(create_app(Settings(tmp_path/'missing.db'))) as client:yield client

def test_untrusted_host_and_proxy_host(client):
 assert client.get('/health',headers={'Host':'attacker.example'}).status_code==400
 assert client.get('/health',headers={'X-Forwarded-Host':'attacker.example'}).status_code==400
 assert client.get('/health',headers={'X-Forwarded-Host':'localhost:3000'}).status_code==503

@pytest.mark.parametrize('path',['/api/insights','/api/reviews/translations'])
def test_external_origin_and_content_type_blocked(client,path):
 assert client.post(path,json={},headers={'Origin':'https://attacker.example'}).status_code==403
 assert client.post(path,content='{}',headers={'Content-Type':'text/plain'}).status_code==415
 assert client.post(path,json={},headers={'Origin':'http://localhost:3000'}).status_code==503

def test_body_size_including_chunked_requests(client):
 assert client.post('/api/insights',content='x'*32769,headers={'Content-Type':'application/json'}).status_code==413
 def chunks():
  yield b'x'*16000
  yield b'x'*18000
 assert client.post('/api/insights',content=chunks(),headers={'Content-Type':'application/json'}).status_code==413

def test_post_rate_limit_ignores_spoofed_ip(client):
 for _ in range(30):assert client.post('/api/insights',json={}).status_code==503
 assert client.post('/api/insights',json={},headers={'X-Forwarded-For':'203.0.113.55'}).status_code==429

def test_response_security_headers(client):
 response=client.get('/health')
 assert response.headers['x-content-type-options']=='nosniff'
 assert response.headers['x-frame-options']=='DENY'
 assert response.headers['cache-control']=='no-store'


def test_public_scanner_rejects_quoted_credentials_and_private_paths(tmp_path):
 from scripts.check_public_security import scan
 source=tmp_path/'README.md'
 for value in ['NVIDIA_API_KEY="'+'a'*24+'"','/Users/'+'private-user/project']:
  source.write_text(value)
  assert scan([source],root=tmp_path)
 source.write_text('NVIDIA_API_KEY=\nNVIDIA_MODEL=nvidia/model\n')
 assert scan([source],root=tmp_path)==[]


def test_public_inventory_excludes_private_inputs():
 from scripts.public_source import ROOT,files
 paths=[path.relative_to(ROOT).as_posix() for path in files()]
 assert 'screenshots/overview.png' in paths
 assert sum(path.startswith('screenshots/') for path in paths)==1
 assert not any('/.git/' in p or p.endswith(('.db','.csv','.parquet')) for p in paths)
 assert not any(p.startswith(('backend/data/','backend/reports/','skills/')) for p in paths)
 assert not any(p.endswith('/.env') or 'FULL_PLAN' in p for p in paths)
