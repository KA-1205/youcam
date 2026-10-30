"""C04 acceptance: consent-gated uploads, short-lived access, revocation and expiry."""
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api import clock
from apps.api.db import Database
from apps.api.modules.storage.models import AssetRow, RetentionEventRow
from apps.api.tests.test_c02_session_commerce import login

PHOTO_CONTROLS = {'processPhotos': True, 'savePhotosAndRenders': False, 'shareWithStylist': False,
                  'researchUse': False, 'notifications': False, 'saveAddress': False,
                  'savePaymentToken': False}
ALL_OFF = {key: False for key in PHOTO_CONTROLS}


def prepare_consent(client, process=True, save=False):
    current = client.get('/api/profile').json()['consent']['consentRevision']
    controls = dict(ALL_OFF)
    controls['processPhotos'] = process
    controls['savePhotosAndRenders'] = save
    response = client.put('/api/consents', json={
        'expectedConsentRevision': current, 'controls': controls, 'processors': ['youcam'],
        'assetIds': [], 'adultAttestation': True})
    assert response.status_code == 200


def prepare_asset(client, capability='CLOTHES_V4'):
    response = client.post('/api/assets', json={
        'expectedConsentRevision': 2, 'capability': capability, 'contentType': 'image/jpeg',
        'byteLength': 2048, 'adultAttestation': True},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_requires_processing_consent(client):
    login(client, 'no-consent@example.com')
    response = client.post('/api/assets', json={
        'expectedConsentRevision': 1, 'capability': 'CLOTHES_V4', 'contentType': 'image/jpeg',
        'byteLength': 2048, 'adultAttestation': True},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'CONSENT_REQUIRED'


def test_prepare_upload_is_pending_then_available(client, db_url):
    prepare_consent(client)
    descriptor = prepare_asset(client)
    assert descriptor['status'] == 'PENDING_UPLOAD'
    assert descriptor['accessPath'] == ''
    assert descriptor['saved'] is False

    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    app_storage = client.app.state.storage_service
    app_storage.complete_upload(db, str(descriptor['assetId']), b'fake-jpeg-bytes')
    db.commit()

    fetched = client.get(f"/api/assets/{descriptor['assetId']}").json()
    assert fetched['status'] == 'AVAILABLE'
    assert '/api/assets/' in fetched['accessPath']
    # five-minute signed access, not a direct object URL
    assert 'object' not in fetched['accessPath']


def test_other_actor_cannot_read_or_delete_asset(client, db_url):
    prepare_consent(client)
    descriptor = prepare_asset(client)
    from apps.api.tests.conftest import make_client
    with make_client(db_url) as stranger:
        login(stranger, 'stranger@example.com')
        assert stranger.get(f"/api/assets/{descriptor['assetId']}").status_code == 404
        deleted = stranger.delete(f"/api/assets/{descriptor['assetId']}")
        assert deleted.status_code == 404


def test_save_requires_saving_consent_and_extends_retention(client, db_url):
    prepare_consent(client, process=True, save=False)
    descriptor = prepare_asset(client)
    denied = client.post(f"/api/assets/{descriptor['assetId']}/saves", json={
        'expectedConsentRevision': 2, 'saveOrRenew': True},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert denied.status_code == 403

    prepare_consent(client, process=True, save=True)
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    client.app.state.storage_service.complete_upload(db, str(descriptor['assetId']),
                                                     b'bytes')
    db.commit()
    saved = client.post(f"/api/assets/{descriptor['assetId']}/saves", json={
        'expectedConsentRevision': 3, 'saveOrRenew': True},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert saved.status_code == 200
    assert saved.json()['saved'] is True


def test_delete_revokes_immediately_and_audits(client, db_url):
    prepare_consent(client)
    descriptor = prepare_asset(client)
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    client.app.state.storage_service.complete_upload(db, str(descriptor['assetId']), b'bytes')
    db.commit()
    deleted = client.delete(f"/api/assets/{descriptor['assetId']}")
    assert deleted.status_code == 202
    fetched = client.get(f"/api/assets/{descriptor['assetId']}").json()
    assert fetched['status'] == 'REVOKED'
    assert fetched['accessPath'] == ''
    events = sessionmaker(bind=engine)().scalars(
        select(RetentionEventRow).where(RetentionEventRow.asset_id == str(descriptor['assetId']))
    ).all()
    assert [event.event_type for event in events][-2:] == ['REVOKED', 'DELETED']
    # storage bytes are gone
    storage = client.app.state.storage_service
    db = sessionmaker(bind=engine)()
    row = db.get(AssetRow, str(descriptor['assetId']))
    assert row is not None
    assert storage._backend.get(row.storage_key) is None  # noqa: SLF001


def test_expiry_sweep_expires_unsaved_and_saved(client, db_url):
    prepare_consent(client, process=True, save=True)
    unsaved = prepare_asset(client)
    saved = prepare_asset(client)
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    storage = client.app.state.storage_service
    storage.complete_upload(db, str(unsaved['assetId']), b'a')
    storage.complete_upload(db, str(saved['assetId']), b'b')
    db.commit()
    saved_response = client.post(f"/api/assets/{saved['assetId']}/saves", json={
        'expectedConsentRevision': 3, 'saveOrRenew': True},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert saved_response.status_code == 200

    db = sessionmaker(bind=engine)()
    # 25 hours later the unsaved asset expires; the saved one lives 90 days
    from datetime import timedelta

    expired = storage.sweep_expired(db, clock.now() + timedelta(hours=25))
    assert expired == 1
    row = db.get(AssetRow, str(unsaved['assetId']))
    assert row is not None and row.status == 'EXPIRED'
    kept = db.get(AssetRow, str(saved['assetId']))
    assert kept is not None and kept.status == 'AVAILABLE'

    far_future = clock.now() + timedelta(days=91)
    expired = storage.sweep_expired(db, far_future)
    assert expired == 1
    row = db.get(AssetRow, str(saved['assetId']))
    assert row is not None and row.status == 'EXPIRED'


def test_worker_purges_asset_delete_tasks(client, db_url):
    from apps.worker.runtime import build_runtime

    prepare_consent(client)
    descriptor = prepare_asset(client)
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    storage = client.app.state.storage_service
    storage.complete_upload(db, str(descriptor['assetId']), b'bytes')
    db.commit()

    from apps.api import clock as api_clock
    from apps.api.modules.task_runtime.models import DurableTaskRow

    db = sessionmaker(bind=engine)()
    now = api_clock.now()
    db.add(DurableTaskRow(task_id=str(uuid.uuid4()), tenant_id='demo-anchor-fit',
                          actor_id='actor:test', operation='ASSET_DELETE',
                          resource_id=str(descriptor['assetId']), request_hash='a' * 64,
                          idempotency_key=str(uuid.uuid4()), status='PENDING', attempt=0,
                          max_attempts=3, lease_worker_id=None, lease_expires_at=None,
                          available_at=now, last_error_code=None, context_json={},
                          created_at=now, updated_at=now))
    db.commit()
    summary = build_runtime(Database(db_url)).cycle()
    assert summary['succeeded'] >= 1
    fetched = client.get(f"/api/assets/{descriptor['assetId']}").json()
    assert fetched['status'] == 'REVOKED'
