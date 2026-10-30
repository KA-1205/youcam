"""C07 acceptance: orchestration safeguards — validation, durable intent before
any provider call, staged chains, quotas, supersession and reconciliation."""
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api.modules.storage.models import AssetRow
from apps.api.modules.task_runtime.models import DurableTaskRow
from apps.api.modules.try_on_jobs.orchestration_models import (
    ActiveJobMarker,
    ChildTaskRow,
    PreviewJobRow,
    QuotaCounterRow,
)
from apps.api.tests.test_c02_session_commerce import ANCHORS, BRIEF, login

RENDER_CONTROLS = {'processPhotos': True, 'savePhotosAndRenders': False, 'shareWithStylist': False,
                   'researchUse': False, 'notifications': False, 'saveAddress': False,
                   'savePaymentToken': False}


def setup_ready_client(client):
    login(client, 'previewer@example.com')
    revision = client.get('/api/profile').json()['consent']['consentRevision']
    response = client.put('/api/consents', json={
        'expectedConsentRevision': revision, 'controls': RENDER_CONTROLS, 'processors': ['youcam'],
        'assetIds': [], 'adultAttestation': True})
    assert response.status_code == 200
    session = client.post('/api/sessions', json={'brief': BRIEF, 'anchors': ANCHORS},
                          headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    asset = client.post('/api/assets', json={
        'expectedConsentRevision': revision + 1, 'capability': 'CLOTHES_V4',
        'contentType': 'image/jpeg', 'byteLength': 2048, 'adultAttestation': True},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    engine = create_engine(client.app.state.database.url)
    db = sessionmaker(bind=engine)()
    client.app.state.storage_service.complete_upload(db, str(asset['assetId']), b'jpeg')
    db.commit()
    return session, asset


def enqueue_preview(client, session, asset, capability='CLOTHES_V4', selections=None,
                    settings=None, expect=202):
    body = {'sessionId': session['sessionId'],
            'expectedSessionVersion': session['sessionVersion'],
            'expectedConsentRevision': client.get('/api/profile').json()['consent']
            ['consentRevision'],
            'capability': capability, 'sourceAssetId': asset['assetId'],
            'selections': selections if selections is not None else [
                {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-1'},
                {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
            'effectIds': [], 'settings': settings or {}}
    response = client.post('/api/preview-jobs', json=body,
                           headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == expect, response.text
    return response


def test_enqueue_validates_session_consent_asset_and_catalog(client):
    session, asset = setup_ready_client(client)
    # unknown variant
    rejected = enqueue_preview(client, session, asset, selections=[
        {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-ghost'}], expect=422)
    assert rejected.json()['error']['code'] == 'VALIDATION_ERROR'
    # happy path creates the job with a staged chain
    job = enqueue_preview(client, session, asset).json()
    assert job['status'] in ('CREATED', 'QUEUED')
    assert job['executionMode'] == 'FIXTURE'
    areas = [child['capability'] for child in job['children']]
    assert areas == ['CLOTHES_V4', 'CLOTHES_V4']  # base then shoes; outer omitted


def test_facial_color_tones_requires_explicit_opt_in(client):
    session, asset = setup_ready_client(client)
    denied = enqueue_preview(client, session, asset, capability='FACIAL_COLOR_TONES',
                             selections=[], expect=403)
    assert denied.json()['error']['code'] == 'CONSENT_REQUIRED'
    allowed = enqueue_preview(client, session, asset, capability='FACIAL_COLOR_TONES',
                              selections=[], settings={'facialColorAnalysisOptIn': 'true'})
    assert allowed.status_code == 202


def test_durable_intent_precedes_any_provider_call(client, db_url):
    session, asset = setup_ready_client(client)
    job = enqueue_preview(client, session, asset).json()
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    # before the worker runs, the intent exists and no child has a provider task
    children = db.scalars(select(ChildTaskRow).where(ChildTaskRow.job_id == job['jobId'])).all()
    assert children and all(child.provider_task_id is None for child in children)
    tasks = db.scalars(select(DurableTaskRow)).all()
    assert any(task.operation == 'PREVIEW' and task.resource_id == job['jobId']
               for task in tasks)


def test_worker_runs_chain_and_downloads_results_privately(client, db_url, runtime_factory):
    session, asset = setup_ready_client(client)
    job = enqueue_preview(client, session, asset).json()
    summary = runtime_factory().cycle()
    assert summary['succeeded'] >= 1
    fetched = client.get(f"/api/preview-jobs/{job['jobId']}").json()
    assert fetched['status'] == 'SUCCEEDED'
    assert all(child['status'] == 'SUCCEEDED' and child['resultAssetId']
               for child in fetched['children'])
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    result_row = db.get(AssetRow, fetched['children'][0]['resultAssetId'])
    assert result_row is not None
    assert client.app.state.storage_service._backend.get(result_row.storage_key) is not None \
        # noqa: SLF001


def test_quota_one_active_and_daily_cap(client, db_url):
    session, asset = setup_ready_client(client)
    first = enqueue_preview(client, session, asset)
    assert first.status_code == 202
    second = enqueue_preview(client, session, asset, expect=429)
    assert second.status_code == 429
    assert second.json()['error']['code'] == 'QUOTA_EXCEEDED'

    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    marker = db.get(ActiveJobMarker, client.get('/api/profile').json()['actorId'])
    db.delete(marker)
    counter = db.scalar(select(QuotaCounterRow))
    assert counter is not None
    counter.paid_intents = 10
    db.commit()
    third = enqueue_preview(client, session, asset, expect=429)
    assert third.status_code == 429
    assert '86400' in third.headers.get('retry-after', '')


def test_cancelled_job_frees_active_slot(client, db_url):
    session, asset = setup_ready_client(client)
    job = enqueue_preview(client, session, asset).json()
    cancelled = client.delete(f"/api/preview-jobs/{job['jobId']}")
    assert cancelled.status_code == 200
    assert cancelled.json()['status'] == 'CANCELLED'
    again = enqueue_preview(client, session, asset)
    assert again.status_code == 202


def test_supersession_marks_stale_jobs(client, db_url):
    session, asset = setup_ready_client(client)
    old = enqueue_preview(client, session, asset).json()
    edited = client.put(f"/api/sessions/{session['sessionId']}", json={
        'expectedSessionVersion': session['sessionVersion'], 'brief': BRIEF, 'anchors': ANCHORS,
        'locks': [], 'rejectedIds': [], 'selections': ANCHORS})
    assert edited.status_code == 200
    session['sessionVersion'] = edited.json()['sessionVersion']
    newer = enqueue_preview(client, session, asset)
    assert newer.status_code == 202
    stale = client.get(f"/api/preview-jobs/{old['jobId']}").json()
    assert stale['freshness'] == 'SUPERSEDED'


def test_unknown_outcome_reserves_charge_and_never_resubmits(client, db_url, runtime_factory):

    session, asset = setup_ready_client(client)
    job = enqueue_preview(client, session, asset).json()

    def outage_factory(capability):
        import httpx

        from apps.api.modules.try_on_jobs.providers.adapters import adapter_for
        from apps.api.modules.try_on_jobs.providers.base import ProviderClient

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == 'GET':
                return httpx.Response(500, json={'error': {'code': 'PROVIDER_OUTAGE'}})
            return httpx.Response(200, json={'taskId': 'task-unknown', 'status': 'QUEUED'})

        return ProviderClient(adapter_for(capability), mode='FIXTURE',
                              transport=httpx.MockTransport(handler))

    runtime = runtime_factory(client_factory=outage_factory)
    runtime.cycle()
    fetched = client.get(f"/api/preview-jobs/{job['jobId']}").json()
    assert fetched['status'] == 'TIMED_OUT'
    assert fetched['error']['code'] == 'UNKNOWN_OUTCOME'
    # the submitted child reserves the unknown charge; queued siblings are cancelled
    assert fetched['children'][0]['unknownChargeReserved'] is True
    assert all(child['status'] == 'CANCELLED' for child in fetched['children'][1:])
    db = sessionmaker(bind=create_engine(db_url))()
    row = db.get(PreviewJobRow, job['jobId'])
    assert row is not None and row.status == 'TIMED_OUT'
    db.commit()
    # a rerun must not resubmit the reserved unknown outcome
    summary = runtime.cycle()
    assert summary['succeeded'] == 0


def test_capabilities_report_not_tested_with_live_disabled(client):
    response = client.get('/api/capabilities')
    assert response.status_code == 200
    states = response.json()['items']
    assert len(states) == 10
    assert all(state['state'] == 'NOT_TESTED' and not state['liveEnabled']
               for state in states)
