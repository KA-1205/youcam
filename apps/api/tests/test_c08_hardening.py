"""C08 acceptance: rate-limit safety, readiness, migration locking and the
provider activation evidence register."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api.db import Database
from apps.api.modules.try_on_jobs.capabilities import (
    ProviderActivationRow,
    capability_page,
    record_activation,
)
from apps.api.ratelimit import RateLimiter


def test_rate_limiter_blocks_excess_and_reports_retry_after():
    limiter = RateLimiter()
    for _ in range(10):
        limiter.check('actor-1', '/api/auth/demo-login')
    try:
        limiter.check('actor-1', '/api/auth/demo-login')
        raise AssertionError('expected rate limit')
    except Exception as error:
        assert getattr(error, 'code', '') == 'QUOTA_EXCEEDED'
        assert int(error.headers['Retry-After']) >= 1  # type: ignore[attr-defined]
    limiter.check('actor-2', '/api/auth/demo-login')  # other actors unaffected
    limiter.check('actor-1', '/api/preview-jobs')  # other paths unaffected


def test_demo_login_is_rate_limited_end_to_end(client, db_url):
    from apps.api.tests.conftest import make_client
    with make_client(db_url) as fresh:
        for attempt in range(11):
            response = fresh.post('/api/auth/demo-login', json={'email': f'r{attempt}@x.test'})
            if attempt < 10:
                assert response.status_code == 200
        assert fresh.post('/api/auth/demo-login',
                          json={'email': 'overflow@x.test'}).status_code == 429


def test_readyz_reports_database_and_live_state(client):
    response = client.get('/readyz')
    assert response.status_code == 200
    assert response.json() == {'ready': True, 'database': True, 'liveProvidersEnabled': False}


def test_capabilities_reflect_recorded_activation_but_stay_live_disabled(client, db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    record_activation(db, 'MAKEUP', region='undocumented', base_url='https://yce-api-01.invalid',
                      auth_method='X-API-KEY', feature_version='makeup-vto',
                      evidence={'successFixture': 'fixture', 'errorFixture': 'fixture',
                                'costUnits': 2, 'retention': 'unverified'},
                      verified_by='operator')
    db.commit()
    states = {state.capability: state for state in capability_page(db).items}
    assert states['MAKEUP'].state == 'VERIFIED'
    assert states['MAKEUP'].evidenceId == 'MAKEUP'
    assert states['CLOTHES_V4'].state == 'NOT_TESTED'
    # Live mode stays disabled on this branch even with recorded evidence.
    assert all(not state.liveEnabled for state in states.values())


def test_activation_row_persists_evidence(db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    record_activation(db, 'RING', region='r', base_url='https://x.invalid', auth_method='key',
                      feature_version='ring-vto', evidence={'fixture': 'ok'},
                      verified_by='operator')
    db.commit()
    row = db.scalar(select(ProviderActivationRow).where(
        ProviderActivationRow.capability == 'RING'))
    assert row is not None
    assert row.evidence == {'fixture': 'ok'}
    assert row.verified_by == 'operator'


def test_rate_limit_middleware_covers_state_changing_routes(client, db_url):
    from apps.api.tests.conftest import make_client
    with make_client(db_url) as fresh:
        setup = fresh.post('/api/auth/demo-login', json={'email': 'burst@x.test'})
        assert setup.status_code == 200
        # The default per-path budget is generous; hammer one path to the limit.
        for _ in range(int(__import__('os').environ.get('ANCHOR_RATE_DEFAULT', '240'))):
            fresh.put('/api/consents', json={'expectedConsentRevision': 1, 'controls': {
                'processPhotos': False, 'savePhotosAndRenders': False, 'shareWithStylist': False,
                'researchUse': False, 'notifications': False, 'saveAddress': False,
                'savePaymentToken': False}, 'processors': [], 'assetIds': [],
                'adultAttestation': False})
        flooded = fresh.put('/api/consents', json={'expectedConsentRevision': 1, 'controls': {
            'processPhotos': False, 'savePhotosAndRenders': False, 'shareWithStylist': False,
            'researchUse': False, 'notifications': False, 'saveAddress': False,
            'savePaymentToken': False}, 'processors': [], 'assetIds': [],
            'adultAttestation': False})
        assert flooded.status_code == 429


def test_worker_cycle_runs_clean_on_migrated_database(db_url):
    from apps.worker.runtime import build_runtime

    summary = build_runtime(Database(db_url)).cycle()
    assert summary['reclaimedLeases'] == 0
    assert summary['succeeded'] == 0
