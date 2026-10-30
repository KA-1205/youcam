"""Lane test fixtures: real migrations on a disposable SQLite database."""
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.db import Database
from apps.api.main import create_app

ROOT = os.getcwd()


@pytest.fixture()
def db_url(tmp_path):
    url = f'sqlite:///{tmp_path / "anchor-fit.db"}'
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = url
    config = Config(os.path.join(ROOT, 'infra', 'migrations', 'alembic.ini'))
    try:
        command.upgrade(config, 'head')
    except Exception:
        os.environ['DATABASE_URL'] = previous or ''
        raise
    yield url
    if previous is None:
        os.environ.pop('DATABASE_URL', None)
    else:
        os.environ['DATABASE_URL'] = previous


@pytest.fixture()
def client(db_url):
    # Secure cookies require an https base URL for httpx to store and resend them.
    app = create_app(database_url=db_url)
    with TestClient(app, base_url='https://testserver') as test_client:
        yield test_client


def make_client(db_url):
    app = create_app(database_url=db_url)
    return TestClient(app, base_url='https://testserver')


@pytest.fixture()
def runtime_factory(db_url):
    def make(client_factory=None):
        from apps.worker.runtime import build_runtime

        return build_runtime(Database(db_url), client_factory=client_factory)

    return make


def migration_round_trip(db_url_value):
    config = Config(os.path.join(ROOT, 'infra', 'migrations', 'alembic.ini'))
    command.downgrade(config, 'base')
    command.upgrade(config, 'head')
    command.downgrade(config, 'base')
    command.upgrade(config, 'head')
