"""Write-acknowledgement ordering: responses must not be sent before commit.

FastAPI closes yield-dependencies after the response is transmitted, so the
unit-of-work commit has to move into request middleware. A follow-up request
over real HTTP must never observe the acknowledged-but-uncommitted state.
"""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

ROOT = Path.cwd().resolve()


class CommitVisibilityProbe:
    """ASGI middleware: record whether an acknowledged write is committed."""

    def __init__(self, app, database_url: str) -> None:
        self.app = app
        self.database_url = database_url
        self.visible_at_transmission: dict[str, bool] = {}

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_when_checked(message):
            if message['type'] == 'http.response.start' \
                    and scope['path'] == '/api/sessions' \
                    and scope['method'] == 'POST':
                self.visible_at_transmission['session'] = self._row_committed()
            await send(message)

        await self.app(scope, receive, send_when_checked)

    def _row_committed(self) -> bool:
        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        try:
            with engine.connect() as connection:
                count = connection.execute(text(
                    'SELECT COUNT(*) FROM styling_sessions')).scalar()
            return bool(count)
        finally:
            engine.dispose()


@pytest.fixture()
def probed_client(tmp_path):
    url = f'sqlite:///{tmp_path / "commit-order.db"}'
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = url
    command.upgrade(Config(str(ROOT / 'infra' / 'migrations' / 'alembic.ini')), 'head')
    from apps.api.main import create_app

    app = create_app(database_url=url)
    probe = CommitVisibilityProbe(app, url)
    from fastapi.testclient import TestClient

    yield TestClient(probe, base_url='https://testserver'), probe
    if previous is None:
        os.environ.pop('DATABASE_URL', None)
    else:
        os.environ['DATABASE_URL'] = previous


def test_acknowledged_session_is_committed_when_response_starts(probed_client):
    client, probe = probed_client
    client.post('/api/auth/demo-login', json={'email': 'order@example.com'})
    response = client.post('/api/sessions', json={
        'brief': {'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
                  'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
                  'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {},
                  'preferences': {}},
        'anchors': [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'}]},
        headers={'Idempotency-Key': '00000000-0000-4000-8000-00000000c0de'})
    assert response.status_code == 201, response.text
    assert probe.visible_at_transmission.get('session') is True
