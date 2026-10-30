from fastapi.testclient import TestClient

from apps.api.main import app


def test_boot_health_and_unimplemented_route():
    with TestClient(app) as client:
        assert client.get('/healthz').json() == {'status': 'FOUNDATION', 'liveProvidersEnabled': False, 'contractVersion': '1.0.0'}
        response = client.get('/api/catalog/variants')
        assert response.status_code == 501
        assert response.json()['error']['code'] == 'NOT_IMPLEMENTED'
        assert client.get('/api/catalog/variants?limit=101').status_code == 422
        assert client.get('/unknown').json()['error']['code'] == 'NOT_FOUND'
