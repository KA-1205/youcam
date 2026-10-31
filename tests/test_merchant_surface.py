"""Merchant surface acceptance: insights aggregates (FR-079/FR-080) and real
account deletion (FR-092/US-074): immediate revocation, queued removal and the
seven-day first-party purge."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.modules.merchant_insights.service import InsightsService

ROOT = Path.cwd().resolve()

BRIEF: dict[str, object] = {'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
                            'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
                            'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {},
                            'preferences': {}}


@pytest.fixture()
def client(tmp_path):
    url = f'sqlite:///{tmp_path / "anchor-fit.db"}'
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = url
    config = Config(str(ROOT / 'infra' / 'migrations' / 'alembic.ini'))
    command.upgrade(config, 'head')
    from apps.api.main import create_app

    app = create_app(database_url=url)
    yield TestClient(app, base_url='https://testserver')
    if previous is None:
        os.environ.pop('DATABASE_URL', None)
    else:
        os.environ['DATABASE_URL'] = previous


def login(client, email='shopper@example.com', role='SHOPPER'):
    response = client.post('/api/auth/demo-login', json={'email': email, 'role': role})
    assert response.status_code == 200, response.text
    return response.json()


def new_session(client):
    response = client.post('/api/sessions', json={'brief': BRIEF, 'anchors': [
        {'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


# -- insights service (pure) ---------------------------------------------------

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def test_insights_define_window_denominators_and_demo_flag():
    service = InsightsService(now=lambda: NOW)
    page = service.page(lambda start, end: {
        'qualifiedSessions': (12, 6), 'stylistRequests': (8, 6),
        'generatedLooks': (8, 4), 'wardrobeSaves': (3, 2), 'orders': (2, 2),
        'previewJobs': (5, 5)})
    by_name = {metric.name: metric for metric in page.metrics}
    assert by_name['qualifiedSessions'].numerator == 12
    assert by_name['qualifiedSessions'].denominator is None
    assert by_name['stylistRequests'].denominator == 12
    assert by_name['stylistRequests'].numerator == 8
    assert by_name['generatedLooks'].suppressed is True
    assert by_name['wardrobeSaves'].suppressed is True
    assert by_name['orders'].mode == 'DEMO'
    assert by_name['previewJobs'].numerator == 5
    assert all(metric.windowEnd == NOW for metric in page.metrics)
    assert all((metric.windowEnd - metric.windowStart).days == 7 for metric in page.metrics)
    assert page.nextCursor is None


def test_insights_suppress_cohorts_below_documented_threshold():
    service = InsightsService(now=lambda: NOW)
    page = service.page(lambda start, end: {
        'qualifiedSessions': (3, 3), 'orders': (0, 0)})
    by_name = {metric.name: metric for metric in page.metrics}
    assert by_name['qualifiedSessions'].suppressed is True
    assert by_name['qualifiedSessions'].numerator is None
    assert by_name['orders'].suppressed is True
    assert by_name['stylistRequests'].suppressed is True  # absent source counts as empty


# -- insights over the API ------------------------------------------------------

def test_insights_require_merchant_role(client):
    login(client)
    forbidden = client.get('/api/merchant/insights')
    assert forbidden.status_code == 403
    login(client, 'merchant@example.com', role='MERCHANT_ADMIN')
    assert client.get('/api/merchant/insights').status_code == 200


def test_insights_aggregate_first_party_activity(client):
    for number in range(5):
        login(client, f'shopper-{number}@example.com')
        new_session(client)
        client.post('/api/wardrobe', json={
            'reference': {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-1'},
            'saved': True, 'manualOwnedQuantity': 0, 'attributesConfirmed': True},
            headers={'Idempotency-Key': str(uuid.uuid4())})
    login(client, 'merchant@example.com', role='MERCHANT_ADMIN')
    page = client.get('/api/merchant/insights', params={'limit': 100})
    assert page.status_code == 200, page.text
    by_name = {metric['name']: metric for metric in page.json()['metrics']}
    assert by_name['qualifiedSessions']['numerator'] == 5
    assert by_name['qualifiedSessions']['distinctShoppers'] == 5
    assert by_name['wardrobeSaves']['numerator'] == 5
    assert by_name['orders']['suppressed'] is True  # no orders: empty cohort suppressed


# -- account deletion ------------------------------------------------------------

def test_delete_account_requires_verified_account(client):
    guest = client.delete('/api/account')
    assert guest.status_code == 403


def test_delete_account_revokes_access_and_shares_immediately(client):
    stylist = login(client, 'stylist@example.com', role='STORE_STYLIST')
    shopper_client = client
    account = login(shopper_client, 'shopper@example.com')
    actor_before = shopper_client.get('/api/profile').json()['actorId']
    session = new_session(shopper_client)
    share = shopper_client.post('/api/shares', json={
        'sessionId': session['sessionId'],
        'expectedSessionVersion': session['sessionVersion'],
        'recipientAccountId': stylist['accountId'], 'includedAssetIds': [],
        'expectedConsentRevision': session['consentRevision']},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert share.status_code == 201

    deleted = shopper_client.delete('/api/account')
    assert deleted.status_code == 202, deleted.text
    assert deleted.json()['status'] == 'ACCEPTED'

    # The old cookie no longer resolves to the account; the next call is a guest.
    after = shopper_client.get('/api/profile')
    assert after.status_code == 200
    assert after.json()['actorId'] != actor_before

    # Same email gets a fresh account, never the deleted one.
    rejoined = login(client, 'shopper@example.com')
    assert rejoined['accountId'] != account['accountId']

    # Shares granted to or from the deleted account are dead.
    login(client, 'stylist@example.com', role='STORE_STYLIST')
    blocked = client.post('/api/proposals', json={
        'sessionId': session['sessionId'], 'baseSessionVersion': session['sessionVersion'],
        'selections': [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'},
                       {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': 'variant-bottom-1'},
                       {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
        'brief': BRIEF, 'notes': 'Access must be revoked.', 'exceptions': []},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert blocked.status_code == 404


def test_seven_day_purge_removes_first_party_personal_data(tmp_path):
    url = f'sqlite:///{tmp_path / "purge.db"}'
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = url
    command.upgrade(Config(str(ROOT / 'infra' / 'migrations' / 'alembic.ini')), 'head')
    from apps.api.main import create_app

    app = create_app(database_url=url)
    client = TestClient(app, base_url='https://testserver')
    account = login(client, 'purge-me@example.com')
    session = new_session(client)
    client.post('/api/wardrobe', json={
        'reference': {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-1'},
        'saved': True, 'manualOwnedQuantity': 0, 'attributesConfirmed': True},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    deleted = client.delete('/api/account')
    assert deleted.status_code == 202

    from sqlalchemy import create_engine, text

    from apps.api.db import Database
    from apps.worker.runtime import purge_deleted_accounts

    database = Database(url)
    engine = create_engine(url)

    def account_row():
        with engine.connect() as connection:
            return connection.execute(text(
                'SELECT email, preferences_json, deleted_at FROM accounts '
                'WHERE account_id = :id'), {'id': account['accountId']}).fetchone()

    # Younger than seven days: tombstoned, email already freed, rows still present.
    summary = purge_deleted_accounts(database, datetime.now(timezone.utc))
    assert summary['purgedAccounts'] == 0
    row = account_row()
    assert 'purge-me@example.com' not in row[0]
    with engine.connect() as connection:
        early_wardrobe = connection.execute(text(
            'SELECT COUNT(*) FROM wardrobe_items WHERE account_id = :id'),
            {'id': account['accountId']}).scalar()
    assert early_wardrobe == 1

    # Past the seven-day promise: personal data is gone, ledger tombstone stays.
    summary = purge_deleted_accounts(database, datetime.now(timezone.utc) + timedelta(days=8))
    assert summary['purgedAccounts'] == 1
    row = account_row()
    assert 'purge-me@example.com' not in row[0]
    assert row[1] in (None, '{}', '')
    with engine.connect() as connection:
        sessions = connection.execute(text(
            'SELECT COUNT(*) FROM styling_sessions WHERE session_id = :id'),
            {'id': session['sessionId']}).scalar()
        wardrobe = connection.execute(text(
            'SELECT COUNT(*) FROM wardrobe_items WHERE account_id = :id'),
            {'id': account['accountId']}).scalar()
    assert sessions == 0
    assert wardrobe == 0
    if previous is None:
        os.environ.pop('DATABASE_URL', None)
    else:
        os.environ['DATABASE_URL'] = previous
