"""Lane integration acceptance: A services served through the C HTTP surface.

Fixture mode end to end: the A-lane catalog, recommendations and stylist run
behind the frozen contracts; the labelled rule-based fallback stands in for the
unavailable AI model and every response stays honest about that.
"""
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

ROOT = Path.cwd().resolve()

BRIEF: dict[str, object] = {'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
                            'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
                            'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {},
                            'preferences': {}}
OWNED_ANCHOR = [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'}]
FALLBACK_LABEL = 'Rule-based suggestions — AI stylist unavailable.'


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


@pytest.fixture()
def studio(tmp_path):
    """App factory: several live clients share one app, like separate browsers."""
    url = f'sqlite:///{tmp_path / "anchor-fit.db"}'
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = url
    config = Config(str(ROOT / 'infra' / 'migrations' / 'alembic.ini'))
    command.upgrade(config, 'head')
    from apps.api.main import create_app

    app = create_app(database_url=url)
    yield lambda: TestClient(app, base_url='https://testserver')
    if previous is None:
        os.environ.pop('DATABASE_URL', None)
    else:
        os.environ['DATABASE_URL'] = previous


def login(client, email='shopper@example.com', role='SHOPPER'):
    response = client.post('/api/auth/demo-login', json={'email': email, 'role': role})
    assert response.status_code == 200, response.text
    return response.json()


def new_session(client, anchors=None):
    body = {'brief': BRIEF, 'anchors': anchors if anchors is not None else []}
    response = client.post('/api/sessions', json=body,
                           headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


# -- lane A catalog through the API ------------------------------------------

def test_catalog_listing_served_by_lane_a(client):
    login(client)
    page = client.get('/api/catalog/variants', params={'limit': 5})
    assert page.status_code == 200, page.text
    body = page.json()
    assert len(body['items']) == 5
    assert body['catalogVersion'].startswith('catalog-v')
    assert body['nextCursor']
    assert all(item['isSynthetic'] for item in body['items'])

    following = client.get('/api/catalog/variants',
                           params={'limit': 5, 'cursor': body['nextCursor']})
    assert following.status_code == 200
    assert following.json()['items'][0]['variantId'] != body['items'][0]['variantId']

    search = client.get('/api/catalog/variants', params={'search': 'variant-shoes'})
    assert search.status_code == 200
    assert search.json()['items']
    assert {item['slot'] for item in search.json()['items']} == {'SHOES'}


def test_catalog_stale_cursor_fails_closed(client):
    login(client)
    stale = client.get('/api/catalog/variants', params={'cursor': 'v999:5'})
    assert stale.status_code == 409
    assert stale.json()['error']['code'] == 'STALE_VERSION'


def test_variant_detail_and_missing_variant(client):
    login(client)
    found = client.get('/api/catalog/variants/variant-top-1')
    assert found.status_code == 200
    assert found.json()['variantId'] == 'variant-top-1'
    missing = client.get('/api/catalog/variants/variant-ghost')
    assert missing.status_code == 404
    assert missing.json()['error']['code'] == 'NOT_FOUND'


# -- lane A stylist jobs with labelled fallback -------------------------------

def run_stylist_job(client, session):
    accepted = client.post('/api/stylist-jobs',
                           json={'sessionId': session['sessionId'],
                                 'expectedSessionVersion': session['sessionVersion'],
                                 'mode': 'PROPOSE', 'lookId': None},
                           headers={'Idempotency-Key': str(uuid.uuid4())})
    assert accepted.status_code == 202, accepted.text
    return accepted


def test_stylist_job_serves_labelled_rule_based_looks(client):
    login(client)
    session = new_session(client, OWNED_ANCHOR)
    accepted = run_stylist_job(client, session)
    body = accepted.json()
    assert body['status'] == 'QUEUED'
    assert body['statusUrl'] == f"/api/stylist-jobs/{body['jobId']}"

    job = client.get(body['statusUrl'])
    assert job.status_code == 200, job.text
    payload = job.json()
    assert payload['status'] == 'SUCCEEDED'
    assert payload['source'] == 'RULE_BASED'
    assert payload['freshness'] == 'CURRENT'
    assert payload['result']['kind'] == 'LOOKS'
    looks = payload['result']['looks']
    assert 1 <= len(looks) <= 3
    for look in looks:
        assert look['completeness'] == 'COMPLETE_OUTFIT'
        assert look['budgetVerified'] is True
        assert look['merchandiseTotalMinor'] <= BRIEF['budgetMinor']
        assert FALLBACK_LABEL in look['warnings']


def test_stylist_job_idempotent_replay_and_conflict(client):
    login(client)
    session = new_session(client, OWNED_ANCHOR)
    key = str(uuid.uuid4())
    body = {'sessionId': session['sessionId'],
            'expectedSessionVersion': session['sessionVersion'],
            'mode': 'PROPOSE', 'lookId': None}
    first = client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': key})
    second = client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': key})
    assert first.json()['jobId'] == second.json()['jobId']

    stale = client.post('/api/stylist-jobs', json={**body, 'expectedSessionVersion': 2},
                        headers={'Idempotency-Key': key})
    assert stale.status_code == 409
    assert stale.json()['error']['code'] == 'STALE_VERSION'

    job = client.get(first.json()['statusUrl']).json()
    look_id = job['result']['looks'][0]['lookId']
    conflict = client.post('/api/stylist-jobs',
                           json={'sessionId': session['sessionId'],
                                 'expectedSessionVersion': session['sessionVersion'],
                                 'mode': 'REVIEW', 'lookId': str(look_id)},
                           headers={'Idempotency-Key': key})
    assert conflict.status_code == 409
    assert conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'


def test_apply_generated_look_updates_session(client):
    login(client)
    session = new_session(client, OWNED_ANCHOR)
    accepted = run_stylist_job(client, session)
    job = client.get(accepted.json()['statusUrl']).json()
    look = job['result']['looks'][0]

    applied = client.post(f"/api/sessions/{session['sessionId']}/look-applications",
                          json={'expectedSessionVersion': session['sessionVersion'],
                                'jobId': job['jobId'], 'lookId': look['lookId']})
    assert applied.status_code == 200, applied.text
    updated = applied.json()
    assert updated['sessionVersion'] == session['sessionVersion'] + 1
    assert [item['refId'] for item in updated['selections']] == \
        [item['refId'] for item in look['items']]

    stale = client.post(f"/api/sessions/{session['sessionId']}/look-applications",
                        json={'expectedSessionVersion': session['sessionVersion'],
                              'jobId': job['jobId'], 'lookId': look['lookId']})
    assert stale.status_code == 409
    assert stale.json()['error']['code'] == 'STALE_VERSION'


def test_cancelled_stylist_job_reports_terminal_state(client):
    login(client)
    session = new_session(client, OWNED_ANCHOR)
    accepted = run_stylist_job(client, session)
    cancelled = client.delete(accepted.json()['statusUrl'])
    assert cancelled.status_code == 200
    assert cancelled.json()['status'] == 'SUCCEEDED'


# -- shares and lane A proposals ----------------------------------------------

def share_session(client, session, recipient_account_id):
    response = client.post('/api/shares',
                           json={'sessionId': session['sessionId'],
                                 'expectedSessionVersion': session['sessionVersion'],
                                 'recipientAccountId': recipient_account_id,
                                 'includedAssetIds': [],
                                 'expectedConsentRevision': session['consentRevision']},
                           headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


def test_share_and_proposal_round_trip(studio):
    shopper = studio()
    stylist = studio()
    stylist_account = login(stylist, 'stylist@example.com', role='STORE_STYLIST')
    login(shopper, 'shopper@example.com')
    session = new_session(shopper, OWNED_ANCHOR)
    share = share_session(shopper, session, stylist_account['accountId'])
    assert share['revoked'] is False
    assert share['sessionId'] == session['sessionId']

    proposal = stylist.post('/api/proposals', json={
        'sessionId': session['sessionId'], 'baseSessionVersion': session['sessionVersion'],
        'selections': [{'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-2'},
                       {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': 'variant-bottom-1'},
                       {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
        'brief': BRIEF, 'notes': 'Try a darker top with the wide trousers.',
        'exceptions': []}, headers={'Idempotency-Key': str(uuid.uuid4())})
    assert proposal.status_code == 201, proposal.text
    assert proposal.json()['status'] == 'PROPOSAL_READY'

    applied = shopper.post(f"/api/proposals/{proposal.json()['proposalId']}/applications",
                           json={'expectedSessionVersion': session['sessionVersion'],
                                 'approvedExceptionIds': [], 'accept': True},
                           headers={'Idempotency-Key': str(uuid.uuid4())})
    assert applied.status_code == 200, applied.text
    assert applied.json()['sessionVersion'] == session['sessionVersion'] + 1

    seen = stylist.get(f"/api/proposals/{proposal.json()['proposalId']}")
    assert seen.status_code == 200
    assert seen.json()['status'] == 'ACCEPTED'
    assert stylist_account['accountId']


def test_proposal_requires_explicit_share(client):
    login(client, 'shopper@example.com')
    session = new_session(client, OWNED_ANCHOR)
    login(client, 'stylist@example.com', role='STORE_STYLIST')
    proposal = client.post('/api/proposals', json={
        'sessionId': session['sessionId'], 'baseSessionVersion': 1,
        'selections': [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'},
                       {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': 'variant-bottom-1'},
                       {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
        'brief': BRIEF, 'notes': 'Unshared access attempt.', 'exceptions': []},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert proposal.status_code == 404


def test_share_revocation_blocks_stylist(client):
    stylist = login(client, 'stylist@example.com', role='STORE_STYLIST')
    login(client, 'shopper@example.com')
    session = new_session(client, OWNED_ANCHOR)
    share = share_session(client, session, stylist['accountId'])

    revoked = client.delete(f"/api/shares/{share['shareId']}")
    assert revoked.status_code == 200
    assert revoked.json()['revoked'] is True

    login(client, 'stylist@example.com', role='STORE_STYLIST')

    blocked = client.post('/api/proposals', json={
        'sessionId': session['sessionId'], 'baseSessionVersion': 1,
        'selections': [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'},
                       {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': 'variant-bottom-1'},
                       {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
        'brief': BRIEF, 'notes': 'Post-revocation attempt.', 'exceptions': []},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert blocked.status_code == 404


def test_outdated_proposal_refresh_round_trip(studio):
    shopper = studio()
    stylist = studio()
    stylist_account = login(stylist, 'stylist@example.com', role='STORE_STYLIST')
    login(shopper, 'shopper@example.com')
    session = new_session(shopper, OWNED_ANCHOR)
    share_session(shopper, session, stylist_account['accountId'])

    proposal = stylist.post('/api/proposals', json={
        'sessionId': session['sessionId'], 'baseSessionVersion': session['sessionVersion'],
        'selections': [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'},
                       {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': 'variant-bottom-1'},
                       {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
        'brief': BRIEF, 'notes': 'Swap the bottom only.', 'exceptions': []},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert proposal.status_code == 201
    proposal_id = proposal.json()['proposalId']

    edited = shopper.put(f"/api/sessions/{session['sessionId']}", json={
        'expectedSessionVersion': session['sessionVersion'], 'brief': BRIEF,
        'anchors': OWNED_ANCHOR, 'locks': [], 'rejectedIds': [], 'selections': []})
    assert edited.status_code == 200
    assert stylist.get(f'/api/proposals/{proposal_id}').json()['status'] == 'OUTDATED'

    refreshed = shopper.post(f'/api/proposals/{proposal_id}/refresh-requests', json={
        'expectedSessionVersion': session['sessionVersion'] + 1,
        'expectedConsentRevision': session['consentRevision'],
        'requestAdviceOnly': True}, headers={'Idempotency-Key': str(uuid.uuid4())})
    assert refreshed.status_code == 202, refreshed.text
    assert refreshed.json()['status'] == 'ACCEPTED'


# -- lane A merchant staging ---------------------------------------------------

def test_staging_and_publication_flow(client):
    login(client, 'merchant@example.com', role='MERCHANT_ADMIN')
    listing = client.get('/api/catalog/variants/variant-top-1').json()
    batch = {**listing, 'priceMinor': 52000}
    response = client.post('/api/catalog/stages', json={
        'sourceId': 'merchant-sync-1', 'sourceVersion': 'sync-v1',
        'variants': [batch]}, headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    stage = response.json()
    assert stage['changedVariantIds'] == ['variant-top-1']
    assert stage['published'] is False
    assert stage['errors'] == []

    published = client.post(f"/api/catalog/stages/{stage['stageId']}/publications",
                            json={'expectedSourceVersion': 'sync-v1',
                                  'approvePublication': True},
                            headers={'Idempotency-Key': str(uuid.uuid4())})
    assert published.status_code == 200, published.text

    updated = client.get('/api/catalog/variants/variant-top-1').json()
    assert updated['priceMinor'] == 52000


# -- honest foundation gaps ----------------------------------------------------

def test_unimplemented_c_surface_stays_labelled(client):
    login(client)
    insights = client.get('/api/merchant/insights')
    assert insights.status_code == 501
    assert insights.json()['error']['code'] == 'NOT_IMPLEMENTED'
    deleted = client.delete('/api/account')
    assert deleted.status_code == 501
