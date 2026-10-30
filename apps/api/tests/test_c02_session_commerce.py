"""C02 acceptance: session CAS authority, demo commerce transitions and outbox events."""
import json
import uuid

from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.orm import sessionmaker

BRIEF: dict[str, object] = {'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES', 'requestedSlots': ['TOP', 'BOTTOM',
                                                                             'SHOES'],
         'occasion': None, 'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {},
         'preferences': {}}
ANCHORS = [{'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-1'}]


def login(client, email='shopper@example.com', role='SHOPPER'):
    response = client.post('/api/auth/demo-login', json={'email': email, 'role': role})
    assert response.status_code == 200
    return response.json()


def create_session(client, **overrides):
    body = {'brief': BRIEF, 'anchors': overrides.get('anchors', ANCHORS)}
    response = client.post('/api/sessions', json=body,
                           headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


def _outbox(db_url):
    engine = create_engine(db_url)
    rows = sessionmaker(bind=engine)().execute(
        sql_text('SELECT payload_json FROM outbox_events ORDER BY event_sequence')).fetchall()
    return [json.loads(row[0]) for row in rows]


def test_unknown_variant_anchor_rejected(client):
    login(client)
    response = client.post('/api/sessions', json={
        'brief': BRIEF,
        'anchors': [{'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-ghost'}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 422


def test_session_create_get_edit_cas(client):
    login(client)
    session = create_session(client)
    assert session['sessionVersion'] == 1
    fetched = client.get(f"/api/sessions/{session['sessionId']}")
    assert fetched.status_code == 200
    assert fetched.json()['anchors'] == ANCHORS

    edited = client.put(f"/api/sessions/{session['sessionId']}", json={
        'expectedSessionVersion': 1, 'brief': BRIEF, 'anchors': ANCHORS,
        'locks': ANCHORS, 'rejectedIds': [], 'selections': ANCHORS})
    assert edited.status_code == 200
    assert edited.json()['sessionVersion'] == 2
    assert edited.json()['locks'] == ANCHORS

    stale = client.put(f"/api/sessions/{session['sessionId']}", json={
        'expectedSessionVersion': 1, 'brief': BRIEF, 'anchors': ANCHORS,
        'locks': [], 'rejectedIds': [], 'selections': ANCHORS})
    assert stale.status_code == 409
    assert stale.json()['error']['code'] == 'STALE_VERSION'


def test_session_idempotent_creation_replays(client):
    login(client)
    key = str(uuid.uuid4())
    body = {'brief': BRIEF, 'anchors': ANCHORS}
    first = client.post('/api/sessions', json=body, headers={'Idempotency-Key': key})
    second = client.post('/api/sessions', json=body, headers={'Idempotency-Key': key})
    assert first.json()['sessionId'] == second.json()['sessionId']
    conflict = client.post('/api/sessions', json={'brief': BRIEF, 'anchors': [
        {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-2'}]},
        headers={'Idempotency-Key': key})
    assert conflict.status_code == 409
    assert conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'


def test_claim_requires_verified_account_and_ownership(client, db_url):
    from apps.api.tests.conftest import make_client
    with make_client(db_url) as guest:
        guest_session = create_session(guest)
        guest_claim = guest.post('/api/session-claims', json={
            'sessionId': guest_session['sessionId'], 'expectedSessionVersion': 1,
            'keepGuestSession': True}, headers={'Idempotency-Key': str(uuid.uuid4())})
        assert guest_claim.status_code == 403

    session = create_session(client)  # same cookie: guest now, owner after login
    login(client, 'owner@example.com')  # upgrades this cookie's actor to the account
    claimed = client.post('/api/session-claims', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': 1,
        'keepGuestSession': True}, headers={'Idempotency-Key': str(uuid.uuid4())})
    assert claimed.status_code == 200
    assert claimed.json()['sessionVersion'] == 2

    with make_client(db_url) as intruder:
        login(intruder, 'intruder@example.com')
        hijack = intruder.post('/api/session-claims', json={
            'sessionId': session['sessionId'], 'expectedSessionVersion': 2,
            'keepGuestSession': True}, headers={'Idempotency-Key': str(uuid.uuid4())})
        assert hijack.status_code == 403


def _checkout(client, email='buyer@example.com'):
    login(client, email)
    session = create_session(client)
    quoted = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 1},
                  {'variantId': 'variant-shoes-1', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert quoted.status_code == 201, quoted.text
    quote = quoted.json()
    confirmed = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'], 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-success'},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert confirmed.status_code == 201, confirmed.text
    return session, quote, confirmed.json()


def test_quote_totals_and_simulated_labels(client):
    login(client, 'quoting@example.com')
    session = create_session(client)
    quoted = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 2}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert quoted.status_code == 201
    quote = quoted.json()
    assert quote['merchandiseMinor'] == 100000
    assert quote['shippingMinor'] == 0 and quote['taxMinor'] == 0
    assert quote['mode'] == 'DEMO'


def test_unknown_price_item_cannot_be_purchased(client):
    login(client, 'unknownprice@example.com')
    session = create_session(client)
    response = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-3', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code in (409, 422)


def test_successful_checkout_allocates_and_emits_ordered_event(client, db_url):
    _, quote, order = _checkout(client)
    assert order['status'] == 'ALLOCATED'
    assert order['mode'] == 'DEMO'
    events = _outbox(db_url)
    assert [event['type'] for event in events] == ['ORDERED']
    assert events[0]['orderVersion'] == 1
    assert events[0]['lines'][0]['variantId'] == 'variant-top-1'


def test_forged_total_rejected(client):
    login(client, 'forger@example.com')
    session = create_session(client)
    quoted = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    quote = quoted.json()
    response = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'] - 1, 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-success'},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'TOTAL_CHANGED'


def test_declined_payment_cancels_and_releases(client, db_url):
    login(client, 'declined@example.com')
    session = create_session(client)
    quoted = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    quote = quoted.json()
    declined = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'], 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-decline'},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert declined.json()['status'] == 'CANCELLED'
    events = _outbox(db_url)
    assert [event['type'] for event in events] == ['CANCELLED']


def test_out_of_stock_rejected_atomically(client, db_url):
    login(client, 'stocked@example.com')
    session = create_session(client)
    response = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-4', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    quote = response.json()
    rejected = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'], 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-success'},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert rejected.status_code == 409
    assert rejected.json()['error']['code'] == 'OUT_OF_STOCK'
    engine = create_engine(db_url)
    orders = sessionmaker(bind=engine)().execute(sql_text('SELECT COUNT(*) FROM orders')).scalar()
    assert orders == 0


def test_paid_cancellation_refunds_and_restores_stock_once(client, db_url):
    _, _, order = _checkout(client, 'cancelling@example.com')
    cancelled = client.post(f"/api/orders/{order['orderId']}/cancellations", json={
        'expectedOrderVersion': order['orderVersion']},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert cancelled.status_code == 200
    assert cancelled.json()['status'] == 'REFUNDED'
    events = _outbox(db_url)
    assert [event['type'] for event in events] == ['ORDERED', 'REFUNDED']
    engine = create_engine(db_url)
    session = sessionmaker(bind=engine)()
    stock = session.execute(sql_text(
        "SELECT available FROM warehouse_stock WHERE variant_id = 'variant-top-1'")).scalar()
    assert stock == 10
    restored_flags = session.execute(sql_text(
        'SELECT restored FROM warehouse_reservations')).fetchall()
    assert all(flag[0] for flag in restored_flags)

    replayed = client.post(f"/api/orders/{order['orderId']}/cancellations", json={
        'expectedOrderVersion': cancelled.json()['orderVersion']},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    assert replayed.status_code == 409


def test_fulfilment_advances_and_delivery_converts_ownership_event(client, db_url):
    _, _, order = _checkout(client, 'delivering@example.com')
    operator = client
    # separate operator account with warehouse role
    from apps.api.tests.conftest import make_client
    with make_client(db_url) as warehouse_client:
        login(warehouse_client, 'warehouse@example.com', role='WAREHOUSE_OPERATOR')
        picked = operator.post(f"/api/orders/{order['orderId']}/fulfilments", json={
            'expectedOrderVersion': order['orderVersion'], 'nextStatus': 'PICKED'},
            headers={'Idempotency-Key': str(uuid.uuid4())})
        assert picked.status_code == 403  # shopper cannot advance fulfilment
        for version, status in ((order['orderVersion'], 'PICKED'),
                                (order['orderVersion'] + 1, 'SHIPPED'),
                                (order['orderVersion'] + 2, 'DELIVERED')):
            response = warehouse_client.post(f"/api/orders/{order['orderId']}/fulfilments", json={
                'expectedOrderVersion': version, 'nextStatus': status},
                headers={'Idempotency-Key': str(uuid.uuid4())})
            assert response.status_code == 200, response.text
        events = _outbox(db_url)
        assert [event['type'] for event in events] == ['ORDERED', 'DELIVERED']

        current = 5  # v1 created, v2 paid→allocated, v3–v5 fulfilment transitions
        wrong_return = warehouse_client.post(f"/api/orders/{order['orderId']}/return-receipts",
                                             json={'expectedOrderVersion': current},
                                             headers={'Idempotency-Key': str(uuid.uuid4())})
        assert wrong_return.status_code == 409  # return must be requested first
        requested = operator.post(f"/api/orders/{order['orderId']}/returns", json={
            'expectedOrderVersion': current}, headers={'Idempotency-Key': str(uuid.uuid4())})
        assert requested.status_code == 200
        assert requested.json()['returnStatus'] == 'REQUESTED'
        received = warehouse_client.post(f"/api/orders/{order['orderId']}/return-receipts", json={
            'expectedOrderVersion': 6}, headers={'Idempotency-Key': str(uuid.uuid4())})
        assert received.status_code == 200
        assert received.json()['status'] == 'REFUNDED'
        assert received.json()['returnStatus'] == 'RECEIVED'
        events = _outbox(db_url)
        assert [event['type'] for event in events][-1] == 'RETURN_RECEIVED'


def test_timeout_payment_reconciles_to_cancelled(client, db_url, monkeypatch):
    import datetime

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    import apps.api.clock as clock_module
    from apps.api.modules.commerce.models import CommerceBase, OrderRow

    login(client, 'timing@example.com')
    session = create_session(client)
    quoted = client.post('/api/cart-quotes', json={
        'sessionId': session['sessionId'], 'expectedSessionVersion': session['sessionVersion'],
        'lines': [{'variantId': 'variant-top-1', 'quantity': 1}]},
        headers={'Idempotency-Key': str(uuid.uuid4())})
    quote = quoted.json()
    order = client.post('/api/orders', json={
        'quoteId': quote['quoteId'], 'expectedQuoteVersion': quote['quoteVersion'],
        'expectedSessionVersion': session['sessionVersion'],
        'confirmedTotalMinor': quote['totalMinor'], 'confirmPurchase': True,
        'addressReference': 'demo-address-1', 'paymentReference': 'demo-pay-timeout'},
        headers={'Idempotency-Key': str(uuid.uuid4())}).json()
    assert order['status'] == 'PAYMENT_PENDING'

    engine = create_engine(db_url)
    CommerceBase.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    commerce = client.app.state.commerce_service
    # before the 30 second delay the demo keeps the reservation and shows "checking"
    commerce.reconcile_timeout(db, db.get(OrderRow, order['orderId']),
                               clock_module.now())
    db.rollback()
    assert client.get(f"/api/orders/{order['orderId']}").json()['status'] == 'PAYMENT_PENDING'

    real_now = clock_module.now
    monkeypatch.setattr(clock_module, 'now', lambda: datetime.datetime.now(
        datetime.timezone.utc) + datetime.timedelta(seconds=31))
    rows = db.scalars(select(OrderRow)).all()
    for row in rows:
        commerce.reconcile_timeout(db, row, clock_module.now())
    db.commit()
    monkeypatch.setattr(clock_module, 'now', real_now)
    assert client.get(f"/api/orders/{order['orderId']}").json()['status'] == 'CANCELLED'
    events = _outbox(db_url)
    assert [event['type'] for event in events] == ['CANCELLED']


def test_cross_tenant_session_is_invisible(client, db_url):
    login(client, 'tenant-a@example.com')
    session = create_session(client)
    import os

    from apps.api.tests.conftest import make_client
    os.environ['ANCHOR_TENANT_ID'] = 'other-storefront'
    try:
        with make_client(db_url) as other_tenant:
            other_tenant.post('/api/auth/demo-login', json={'email': 'tenant-b@example.com'})
            response = other_tenant.get(f"/api/sessions/{session['sessionId']}")
            assert response.status_code == 404
    finally:
        os.environ['ANCHOR_TENANT_ID'] = 'demo-anchor-fit'
