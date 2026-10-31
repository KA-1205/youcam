from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]


def test_boot_health_and_unimplemented_route(tmp_path, monkeypatch):
    url = f'sqlite:///{tmp_path / "boot.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    command.upgrade(Config(str(ROOT / 'infra' / 'migrations' / 'alembic.ini')), 'head')
    from apps.api.main import create_app

    with TestClient(create_app(database_url=url), base_url='https://testserver') as client:
        assert client.get('/healthz').json() == {'status': 'FOUNDATION', 'liveProvidersEnabled': False, 'contractVersion': '1.0.0'}
        response = client.get('/api/catalog/variants')
        assert response.status_code == 200
        assert response.json()['items']
        assert client.get('/api/catalog/variants?limit=101').status_code == 422
        assert client.get('/unknown').json()['error']['code'] == 'NOT_FOUND'
        assert client.delete('/api/account').json()['error']['code'] == 'SCOPE_FORBIDDEN'
