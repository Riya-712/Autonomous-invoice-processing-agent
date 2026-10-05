from fastapi.testclient import TestClient
from simulated_ap.main import app

def test_health():
    with TestClient(app) as client:
        r=client.get('/api/health')
        assert r.status_code==200 and r.json()['status']=='ok'
