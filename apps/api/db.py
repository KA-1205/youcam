"""Database engine and session factory for the C-owned persistence layer.

Engine creation is deferred to first use so the app can boot (health, disabled
routes) wherever no database is configured.
"""
import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url(explicit: str | None = None) -> str:
    return explicit or os.environ.get(
        'DATABASE_URL', 'sqlite:///.anchor-fit-demo.db')


def create_database_engine(url: str) -> Engine:
    if url.startswith('sqlite'):
        return create_engine(url, connect_args={'check_same_thread': False})
    return create_engine(url, pool_pre_ping=True)


class Database:
    def __init__(self, url: str | None = None) -> None:
        self._url = url
        self._engine: Engine | None = None
        self._sessions: sessionmaker | None = None

    @property
    def url(self) -> str:
        if self._url is None:
            self._url = database_url()
        return self._url

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_database_engine(self.url)
        return self._engine

    @property
    def sessions(self) -> sessionmaker:
        if self._sessions is None:
            self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._sessions

    @contextmanager
    def unit_of_work(self) -> Iterator[Session]:
        session = self.sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
