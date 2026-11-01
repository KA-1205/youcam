from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_unmigrated_database_is_not_ready(tmp_path):
    app = create_app(f'sqlite:///{tmp_path / "empty.db"}')
    with TestClient(app) as client:
        assert client.get('/readyz').json()['ready'] is False


def test_local_browser_preflight():
    with TestClient(create_app()) as client:
        response = client.options('/api/sessions', headers={
            'Origin': 'http://127.0.0.1:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,idempotency-key'})
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == 'http://127.0.0.1:3000'
        assert response.headers['access-control-allow-credentials'] == 'true'
