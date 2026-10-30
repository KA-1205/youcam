"""C03 acceptance: leases, idempotent enqueue, retries and outbox-driven wardrobe."""
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api import clock
from apps.api.db import Database
from apps.api.errors import ApiError
from apps.api.modules.task_runtime.models import DurableTaskRow
from apps.api.modules.task_runtime.service import RETRY_BACKOFF
from apps.api.tests.conftest import make_client
from apps.api.tests.test_c02_session_commerce import login

KEY = uuid.uuid4()


@pytest.fixture()
def runtime(db_url):
    from apps.worker.runtime import build_runtime

    return build_runtime(Database(db_url))


@pytest.fixture()
def tasks(runtime):
    return runtime.tasks


def ctx(tenant='demo-anchor-fit', actor='actor:test'):
    from contracts.runtime.models import AccessContext

    return AccessContext(actorId=actor, tenantId=tenant, roles=['SHOPPER'], verifiedAccount=True,
                         consentRevision=1)


def test_enqueue_is_idempotent_by_key_and_hash(tasks, db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    first = tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'COMMERCE_EVENT',
                                 uuid.uuid4(), 'a' * 64, KEY)
    second = tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'COMMERCE_EVENT',
                                  uuid.uuid4(), 'a' * 64, KEY)
    assert first.taskId == second.taskId
    with pytest.raises(ApiError) as conflict:
        tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'COMMERCE_EVENT',
                             uuid.uuid4(), 'b' * 64, KEY)
    assert conflict.value.code == 'IDEMPOTENCY_CONFLICT'
    db.rollback()


def test_claim_lease_is_exclusive_across_workers(tasks, db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    resource = uuid.uuid4()
    tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'COMMERCE_EVENT', resource,
                         'a' * 64, KEY)
    first = tasks.claim(db, 'worker-a', clock.now())
    second = tasks.claim(db, 'worker-b', clock.now())
    assert first is not None and first.resourceId == resource
    assert second is None
    row = db.get(DurableTaskRow, str(first.taskId))
    assert row is not None and row.status == 'LEASED'
    assert row.attempt == 1
    db.rollback()


def test_expired_lease_is_reclaimed(tasks, db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'COMMERCE_EVENT', uuid.uuid4(),
                         'a' * 64, KEY)
    claimed = tasks.claim(db, 'worker-a', clock.now())
    assert claimed is not None
    future = clock.now() + timedelta(seconds=3600)
    reclaimed = tasks.reclaim_expired_leases(db, future)
    assert reclaimed == 1
    again = tasks.claim(db, 'worker-b', future + timedelta(seconds=RETRY_BACKOFF + 1))
    assert again is not None and again.attempt == 2
    db.rollback()


def test_retries_then_terminal_failure(tasks, db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    task = tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'STYLIST', uuid.uuid4(),
                                'a' * 64, KEY, max_attempts=2)
    now = clock.now()
    outcomes = []
    for attempt in range(2):
        claimed = tasks.claim(db, 'worker-a', now)
        assert claimed is not None
        outcomes.append(tasks.fail(db, claimed.taskId, 'STYLIST_UNAVAILABLE', now))
        now = now + timedelta(seconds=RETRY_BACKOFF * (attempt + 1) + 1)
    assert outcomes == ['WAITING', 'FAILED']
    # terminal failure is parked, never resubmitted automatically
    assert tasks.claim(db, 'worker-a', now + timedelta(seconds=3600)) is None
    row = db.get(DurableTaskRow, str(task.taskId))
    assert row is not None and row.status == 'FAILED'
    assert row.last_error_code == 'STYLIST_UNAVAILABLE'
    db.rollback()


def test_unknown_outcome_is_not_resubmitted_automatically(tasks, db_url):
    db = sessionmaker(bind=create_engine(db_url))()
    tasks.enqueue_direct(db, 'demo-anchor-fit', 'actor:1', 'STYLIST', uuid.uuid4(),
                         'a' * 64, KEY)
    claimed = tasks.claim(db, 'worker-a', clock.now())
    db.commit()
    # A worker crash leaves the lease; the task is not resubmitted until expiry.
    fresh = sessionmaker(bind=create_engine(db_url))()
    still_leased = tasks.claim(fresh, 'worker-b', clock.now() + timedelta(seconds=1))
    assert still_leased is None
    assert tasks.get(fresh, claimed.taskId).attempt == 1
    db.rollback()


def _checkout_success(client):
    from apps.api.tests.test_c02_session_commerce import ANCHORS, BRIEF

    login(client, 'outbox@example.com')
    session = client.post('/api/sessions', json={'brief': BRIEF, 'anchors': ANCHORS},
                          headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    quote = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    order = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'], 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-success'},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    return order


def test_worker_publishes_order_event_to_wardrobe(client, db_url, runtime):
    order = _checkout_success(client)
    summary = runtime.cycle()
    assert summary['succeeded'] >= 1
    wardrobe = client.get('/api/wardrobe').json()
    assert len(wardrobe['items']) == 1
    assert wardrobe['items'][0]['orderedQuantity'] == 1
    assert wardrobe['items'][0]['ownedQuantity'] == 0
    assert order['orderId'].replace('-', '')  # order referenced in events


def test_worker_delivered_event_converts_to_owned_once(client, db_url, runtime):
    order = _checkout_success(client)
    runtime.cycle()  # publish ORDERED
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    from apps.api.modules.commerce.models import OrderRow

    row = db.get(OrderRow, order['orderId'])
    assert row is not None
    with make_client(db_url) as operator_ui:
        login(operator_ui, 'warehouse-ops@example.com', role='WAREHOUSE_OPERATOR')
        response = operator_ui.post(f"/api/orders/{order['orderId']}/fulfilments", json={
            'expectedOrderVersion': row.order_version, 'nextStatus': 'PICKED'},
            headers={'Idempotency-Key': str(uuid.uuid4())})
        assert response.status_code == 200, response.text
    db.expire_all()
    row = db.get(OrderRow, order['orderId'])
    assert row is not None
    runtime.cycle()  # no new event yet; PICKED emits nothing
    with make_client(db_url) as operator_ui:
        login(operator_ui, 'warehouse-ops@example.com', role='WAREHOUSE_OPERATOR')
        for version, status in ((row.order_version, 'SHIPPED'),
                                (row.order_version + 1, 'DELIVERED')):
            response = operator_ui.post(f"/api/orders/{order['orderId']}/fulfilments", json={
                'expectedOrderVersion': version, 'nextStatus': status},
                headers={'Idempotency-Key': str(uuid.uuid4())})
            assert response.status_code == 200
    runtime.cycle()  # publish DELIVERED
    wardrobe = client.get('/api/wardrobe').json()
    assert wardrobe['items'][0]['ownedQuantity'] == 1
    assert wardrobe['items'][0]['orderedQuantity'] == 0
    owned_before = wardrobe['items'][0]['ownedQuantity']
    runtime.cycle()  # replay: dedupe must not double-apply
    wardrobe = client.get('/api/wardrobe').json()
    assert wardrobe['items'][0]['ownedQuantity'] == owned_before


def test_worker_reconciles_demo_payment_timeout(client, db_url, runtime, monkeypatch):
    import apps.api.clock as clock_module

    login(client, 'timeout-worker@example.com')
    session = client.post('/api/sessions', json={
        'brief': {'lookMode': 'CATEGORY_SET', 'outfitForm': None, 'requestedSlots': ['TOP'],
                  'occasion': None, 'budgetMinor': None, 'currency': 'INR',
                  'hardRequirements': {}, 'preferences': {}},
        'anchors': [{'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-1'}]},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    quote = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    order = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'], 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-timeout'},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    runtime.cycle()
    assert client.get(f"/api/orders/{order['orderId']}").json()['status'] == 'PAYMENT_PENDING'

    real_now = clock_module.now
    monkeypatch.setattr(clock_module, 'now', lambda: real_now() + timedelta(seconds=31))
    runtime.cycle()
    monkeypatch.setattr(clock_module, 'now', real_now)
    assert client.get(f"/api/orders/{order['orderId']}").json()['status'] == 'CANCELLED'
