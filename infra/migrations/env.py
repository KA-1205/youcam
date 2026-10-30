"""Migration runner only; domain tables belong to C01 onward.

Concurrent deployers serialize on a PostgreSQL advisory lock; SQLite (local
tests) needs no lock. The lock id is fixed for this migration series.
"""
import os

from alembic import context
from sqlalchemy import create_engine, pool, text

url = os.environ['DATABASE_URL']
ADVISORY_LOCK_KEY = 727449


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=url, target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        if engine.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_lock(:key)'), {'key': ADVISORY_LOCK_KEY})
        try:
            _run_migrations(connection)
        finally:
            if engine.dialect.name == 'postgresql':
                connection.execute(text('SELECT pg_advisory_unlock(:key)'),
                                   {'key': ADVISORY_LOCK_KEY})
