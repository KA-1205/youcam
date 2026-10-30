"""Commerce authority: quotes, demo checkout, order transitions and outbox events.

Demo market is India (INR paise); shipping and tax are zero and visibly
simulated. Reservations last 15 minutes on server time. Every accepted
transition persists its outbox event in the same transaction; the worker
publishes events to the profile port.
"""
import datetime
import hashlib
import json
from collections.abc import Callable
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import IDEMPOTENCY_CONFLICT, STALE_VERSION, ApiError
from apps.api.modules.commerce.models import (
    CartQuoteRow,
    IdempotencyKeyRow,
    OrderRow,
    OutboxEventRow,
    PaymentAttemptRow,
)
from apps.api.modules.commerce.ports import (
    DemoPaymentPort,
    DemoWarehousePort,
    InsufficientStock,
    UnknownStock,
)
from contracts.runtime.models import (
    AccessContext,
    CartLine,
    CartQuote,
    CartRequest,
    CheckoutConfirm,
    CommerceEvent,
    CommerceLine,
    FulfilmentAction,
    OrderAction,
    OrderSnapshot,
)

QUOTE_TTL = 900  # catalog price/stock and quotes expire after 15 minutes
RESERVATION_TTL = 900
RECONCILE_DELAY = 30  # demo timeout reconciles at +30 seconds
DEMO_PAYMENT_REFERENCES = {
    'demo-pay-success': 'SUCCESS',
    'demo-pay-decline': 'DECLINE',
    'demo-pay-auth': 'AUTH_REQUIRED',
    'demo-pay-timeout': 'TIMEOUT',
}
FULFILMENT_PATH = {'ALLOCATED': 'PICKED', 'PICKED': 'SHIPPED', 'SHIPPED': 'DELIVERED'}
PAID_BEFORE_SHIPMENT = ('PAID', 'ALLOCATED', 'PICKED')

OrderStatus = Literal['CREATED', 'PAYMENT_PENDING', 'PAID', 'ALLOCATED', 'PICKED', 'SHIPPED',
                      'DELIVERED', 'CANCELLED', 'REFUNDED']
EventTypes = Literal['ORDERED', 'DELIVERED', 'CANCELLED', 'REFUNDED', 'RETURN_RECEIVED']


def order_snapshot(row: OrderRow) -> OrderSnapshot:
    return OrderSnapshot(orderId=UUID(row.order_id), tenantId=row.tenant_id,
                         orderVersion=row.order_version, status=cast(OrderStatus, row.status),
                         lines=[CartLine(variantId=line['variantId'], quantity=line['quantity'])
                                for line in row.lines],
                         totalMinor=row.total_minor, currency=row.currency, mode='DEMO',
                         returnStatus=cast(Literal['NONE', 'REQUESTED', 'RECEIVED'],
                                           row.return_status))


SessionGuard = Callable[[Session, AccessContext, UUID, int], None]
TaskEnqueue = Callable[..., object]


class CommerceService:
    """Implements quote/checkout authority with demo payment and warehouse ports.

    Session ownership and version checks are injected at composition so this
    module never imports styling-session persistence internals directly.
    """

    def __init__(self, payment: DemoPaymentPort, catalog,
                 session_guard: SessionGuard | None = None,
                 task_enqueue: TaskEnqueue | None = None) -> None:
        self._payment = payment
        self._catalog = catalog
        self._session_guard = session_guard
        self._task_enqueue = task_enqueue

    def warehouse(self, db: Session, tenant_id: str) -> DemoWarehousePort:
        from apps.api.demo_catalog import FixtureCatalog

        assert isinstance(self._catalog, FixtureCatalog)
        return DemoWarehousePort(db, tenant_id, self._catalog.seed_stock())

    # Quotes -----------------------------------------------------------------

    def quote_cart(self, db: Session, ctx: AccessContext, body: CartRequest) -> CartQuote:
        if self._session_guard is None:
            raise ApiError(501, 'NOT_IMPLEMENTED', 'Session authority is not wired.')
        self._session_guard(db, ctx, body.sessionId, body.expectedSessionVersion)
        total = 0
        currency = 'INR'
        for line in body.lines:
            price, line_currency = self._catalog.price_for(line.variantId)
            if price is None:
                raise ApiError(409, 'PRICE_UNAVAILABLE',
                               'A selected item has no current price and cannot be purchased.')
            if line_currency != currency:
                raise ApiError(422, 'VALIDATION_ERROR', 'Mixed currencies are not supported.')
            total += price * line.quantity
        row = CartQuoteRow(
            quote_id=str(uuid4()), actor_id=ctx.actorId, tenant_id=ctx.tenantId,
            session_id=str(body.sessionId), session_version=body.expectedSessionVersion,
            quote_version=1, lines=[line.model_dump() for line in body.lines],
            merchandise_minor=total, shipping_minor=0, tax_minor=0, total_minor=total,
            currency=currency, mode='DEMO',
            expires_at=clock.now().replace(microsecond=0) + datetime.timedelta(seconds=QUOTE_TTL),
            created_at=clock.now())
        db.add(row)
        db.flush()
        return CartQuote(quoteId=UUID(row.quote_id), quoteVersion=row.quote_version,
                         sessionId=body.sessionId, sessionVersion=row.session_version,
                         lines=body.lines, merchandiseMinor=total, shippingMinor=0, taxMinor=0,
                         totalMinor=total, currency=currency, expiresAt=row.expires_at, mode='DEMO')

    # Checkout ---------------------------------------------------------------

    def confirm_checkout(self, db: Session, ctx: AccessContext, body: CheckoutConfirm,
                         account_id: str) -> OrderSnapshot:
        quote = db.get(CartQuoteRow, str(body.quoteId))
        if quote is None or quote.actor_id != ctx.actorId:
            raise ApiError(404, 'NOT_FOUND', 'Unknown quote.')
        if body.expectedQuoteVersion != quote.quote_version:
            raise ApiError(409, STALE_VERSION, 'Quote changed; request a new one.')
        if clock.as_utc(quote.expires_at) <= clock.now():
            raise ApiError(409, 'QUOTE_EXPIRED', 'The quote expired; request a new one.')
        if body.expectedSessionVersion != quote.session_version:
            raise ApiError(409, STALE_VERSION, 'Session changed; refresh and requote.')
        if body.confirmedTotalMinor != quote.total_minor:
            raise ApiError(409, 'TOTAL_CHANGED', 'The confirmed total does not match the quote.')
        if not body.confirmPurchase:
            raise ApiError(422, 'VALIDATION_ERROR', 'Purchase must be explicitly confirmed.')
        scripted = DEMO_PAYMENT_REFERENCES.get(body.paymentReference)
        if scripted is None:
            raise ApiError(422, 'VALIDATION_ERROR', 'Choose one of the simulated payment options.')

        lines = [CartLine(**line) for line in quote.lines]
        warehouse = self.warehouse(db, quote.tenant_id)
        try:
            reservation = warehouse.reserve(
                lines, clock.now().replace(microsecond=0)
                + datetime.timedelta(seconds=RESERVATION_TTL), intent_id=uuid4())
        except UnknownStock as error:
            raise ApiError(409, 'OUT_OF_STOCK',
                           f'Stock for {error.variant_id} is unknown and cannot be purchased.')
        except InsufficientStock as error:
            raise ApiError(409, 'OUT_OF_STOCK', f'Not enough stock for {error.variant_id}.')

        order = OrderRow(order_id=str(uuid4()), tenant_id=quote.tenant_id, actor_id=ctx.actorId,
                         account_id=account_id, order_version=1, event_sequence=0,
                         status='PAYMENT_PENDING',
                         lines=[{'orderLineId': str(uuid4()), 'variantId': line['variantId'],
                                 'quantity': line['quantity']} for line in quote.lines],
                         total_minor=quote.total_minor, currency=quote.currency, mode='DEMO',
                         return_status='NONE', quote_id=quote.quote_id,
                         reservation_id=str(reservation.reservationId),
                         payment_reference=body.paymentReference,
                         address_reference=body.addressReference, payment_attempt_id=None,
                         stock_restored=False, created_at=clock.now(), updated_at=clock.now())
        db.add(order)
        db.flush()
        self._begin_payment(db, order, scripted)
        return order_snapshot(order)

    def _begin_payment(self, db: Session, order: OrderRow, scripted: str) -> None:
        intent_id = uuid4()
        attempt_id = str(uuid4())
        self._payment.script(intent_id, scripted)
        result = self._payment.initiate(order_snapshot(order), intent_id)
        db.add(PaymentAttemptRow(attempt_id=attempt_id, order_id=order.order_id,
                                 intent_id=str(intent_id), reference=result.reference,
                                 status=result.status, mode='DEMO', scripted_outcome=scripted,
                                 action=result.action, error_json=None, created_at=clock.now(),
                                 updated_at=clock.now()))
        order.payment_attempt_id = attempt_id
        if result.status == 'SUCCEEDED':
            self._mark_paid(db, order)
        elif result.status == 'FAILED':
            self._cancel_order(db, order, 'DECLINED')
        # ACTION_REQUIRED and UNKNOWN keep the order in PAYMENT_PENDING with the
        # reservation retained; scripted approval and timeout reconciliation move it on.
        db.flush()

    def _mark_paid(self, db: Session, order: OrderRow) -> None:
        # Scripted SUCCESS: PAID → ALLOCATED transactionally, consuming the
        # reservation and decrementing available stock exactly once.
        order.order_version += 1
        order.status = 'ALLOCATED'
        warehouse = self.warehouse(db, order.tenant_id)
        assert order.reservation_id is not None
        warehouse.consume(UUID(order.reservation_id))
        self._emit(db, order, 'ORDERED')
        db.flush()

    def approve_demo_authentication(self, db: Session, ctx: AccessContext,
                                    order_id: UUID) -> OrderSnapshot:
        order = self._owned_order(db, ctx, order_id)
        attempt = db.get(PaymentAttemptRow, order.payment_attempt_id)
        if order.status != 'PAYMENT_PENDING' or attempt is None \
                or attempt.status != 'ACTION_REQUIRED':
            raise ApiError(409, 'HTTP_ERROR', 'No simulated authentication is pending.')
        self._mark_paid(db, order)
        return order_snapshot(order)

    def reconcile_timeout(self, db: Session, order: OrderRow, now: datetime.datetime) -> None:
        """Scripted demo timeout reconciles at +30 seconds; the fixture never pays late."""
        attempt = db.get(PaymentAttemptRow, order.payment_attempt_id)
        if attempt is None or attempt.scripted_outcome != 'TIMEOUT' \
                or order.status != 'PAYMENT_PENDING':
            return
        if (now - clock.as_utc(attempt.created_at)).total_seconds() < RECONCILE_DELAY:
            return
        self._cancel_order(db, order, 'SIMULATED_TIMEOUT')

    # Order operations -------------------------------------------------------

    def cancel_order(self, db: Session, ctx: AccessContext, order_id: UUID,
                     body: OrderAction) -> OrderSnapshot:
        order = self._owned_order(db, ctx, order_id)
        if body.expectedOrderVersion != order.order_version:
            raise ApiError(409, STALE_VERSION, 'Order changed; refresh and retry.')
        if order.status in ('SHIPPED', 'DELIVERED'):
            raise ApiError(409, 'HTTP_ERROR', 'Shipped orders use the return flow.')
        if order.status in ('CANCELLED', 'REFUNDED'):
            raise ApiError(409, 'HTTP_ERROR', 'This order is already closed.')
        if order.status in PAID_BEFORE_SHIPMENT:
            self._refund_order(db, order)
        else:
            self._cancel_order(db, order, 'SHOPPER_REQUESTED')
        return order_snapshot(order)

    def request_return(self, db: Session, ctx: AccessContext, order_id: UUID,
                       body: OrderAction) -> OrderSnapshot:
        order = self._owned_order(db, ctx, order_id)
        if body.expectedOrderVersion != order.order_version:
            raise ApiError(409, STALE_VERSION, 'Order changed; refresh and retry.')
        if order.status != 'DELIVERED':
            raise ApiError(409, 'HTTP_ERROR', 'Returns are requested after delivery.')
        order.return_status = 'REQUESTED'
        order.order_version += 1
        order.updated_at = clock.now()
        db.flush()
        return order_snapshot(order)

    def advance_fulfilment(self, db: Session, ctx: AccessContext, order_id: UUID,
                           body: FulfilmentAction) -> OrderSnapshot:
        order = self._operator_order(db, ctx, order_id)
        if body.expectedOrderVersion != order.order_version:
            raise ApiError(409, STALE_VERSION, 'Order changed; refresh and retry.')
        expected = FULFILMENT_PATH.get(order.status)
        if expected is None or body.nextStatus != expected:
            raise ApiError(409, 'HTTP_ERROR',
                           f'Next fulfilment state is {expected or "none"}.')
        order.status = body.nextStatus
        order.order_version += 1
        order.updated_at = clock.now()
        if body.nextStatus == 'DELIVERED':
            self._emit(db, order, 'DELIVERED')
        db.flush()
        return order_snapshot(order)

    def receive_return(self, db: Session, ctx: AccessContext, order_id: UUID,
                       body: OrderAction) -> OrderSnapshot:
        order = self._operator_order(db, ctx, order_id)
        if body.expectedOrderVersion != order.order_version:
            raise ApiError(409, STALE_VERSION, 'Order changed; refresh and retry.')
        if order.status != 'DELIVERED' or order.return_status != 'REQUESTED':
            raise ApiError(409, 'HTTP_ERROR', 'No requested return is pending for this order.')
        order.status = 'REFUNDED'
        order.return_status = 'RECEIVED'
        order.order_version += 1
        order.updated_at = clock.now()
        warehouse = self.warehouse(db, order.tenant_id)
        if order.reservation_id:
            warehouse.restore(UUID(order.reservation_id))
        self._emit(db, order, 'RETURN_RECEIVED')
        db.flush()
        return order_snapshot(order)

    def get_order(self, db: Session, ctx: AccessContext, order_id: UUID) -> OrderSnapshot:
        return order_snapshot(self._owned_order(db, ctx, order_id))

    def pending_timeout_orders(self, db: Session) -> list[OrderRow]:
        return list(db.scalars(select(OrderRow).where(OrderRow.status == 'PAYMENT_PENDING')))

    # Internals --------------------------------------------------------------

    def _refund_order(self, db: Session, order: OrderRow) -> None:
        attempt = db.get(PaymentAttemptRow, order.payment_attempt_id)
        if attempt is None:
            raise ApiError(409, 'HTTP_ERROR', 'No payment attempt exists for this order.')
        self._payment.refund(UUID(order.order_id), order.total_minor, UUID(attempt.intent_id))
        warehouse = self.warehouse(db, order.tenant_id)
        if order.reservation_id and not order.stock_restored:
            warehouse.restore(UUID(order.reservation_id))
            order.stock_restored = True
        order.status = 'REFUNDED'
        order.order_version += 1
        order.updated_at = clock.now()
        self._emit(db, order, 'REFUNDED')
        db.flush()

    def _cancel_order(self, db: Session, order: OrderRow, reason: str) -> None:
        order.status = 'CANCELLED'
        order.order_version += 1
        order.updated_at = clock.now()
        warehouse = self.warehouse(db, order.tenant_id)
        if order.reservation_id:
            warehouse.release(UUID(order.reservation_id), intent_id=uuid4())
        self._emit(db, order, 'CANCELLED', {'reason': reason})
        db.flush()

    def _emit(self, db: Session, order: OrderRow, event_type: EventTypes,
              extra: dict | None = None) -> None:
        order.event_sequence += 1
        event = CommerceEvent(
            eventId=uuid4(), tenantId=order.tenant_id, orderId=UUID(order.order_id),
            orderVersion=order.event_sequence, type=event_type, occurredAt=clock.now(),
            mode='DEMO',
            lines=[CommerceLine(orderLineId=UUID(line['orderLineId']),
                                variantId=line['variantId'], quantity=line['quantity'])
                   for line in order.lines])
        payload = event.model_dump(mode='json')
        if extra:
            payload['extra'] = extra
        db.add(OutboxEventRow(event_id=str(event.eventId), tenant_id=order.tenant_id,
                              order_id=order.order_id, event_sequence=order.event_sequence,
                              payload=payload, status='PENDING', created_at=clock.now(),
                              published_at=None))
        if self._task_enqueue is not None:
            self._task_enqueue(db, order.tenant_id, order.actor_id, 'COMMERCE_EVENT',
                               UUID(str(event.eventId)),
                               hashlib.sha256(json.dumps(payload, sort_keys=True).encode())
                               .hexdigest(), UUID(str(event.eventId)),
                               context={'account_id': order.account_id})
        db.flush()

    def _owned_order(self, db: Session, ctx: AccessContext, order_id: UUID) -> OrderRow:
        row = db.get(OrderRow, str(order_id))
        if row is None or row.tenant_id != ctx.tenantId:
            raise ApiError(404, 'NOT_FOUND', 'Unknown order.')
        if row.actor_id != ctx.actorId:
            raise ApiError(403, 'SCOPE_FORBIDDEN', 'This order belongs to another shopper.')
        return row

    def _operator_order(self, db: Session, ctx: AccessContext, order_id: UUID) -> OrderRow:
        row = db.get(OrderRow, str(order_id))
        if row is None or row.tenant_id != ctx.tenantId:
            raise ApiError(404, 'NOT_FOUND', 'Unknown order.')
        operator_roles = {'WAREHOUSE_OPERATOR', 'PLATFORM_OPERATOR'}
        if not set(ctx.roles) & operator_roles:
            raise ApiError(403, 'SCOPE_FORBIDDEN', 'Warehouse authorization required.')
        return row


# Idempotency helpers --------------------------------------------------------

def request_hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def replay(db: Session, actor_id: str, operation: str, key: UUID, payload) -> dict | None:
    row = db.get(IdempotencyKeyRow, str(key))
    if row is None:
        return None
    if row.actor_id != actor_id or row.operation != operation \
            or row.request_hash != request_hash(payload):
        raise ApiError(409, IDEMPOTENCY_CONFLICT,
                       'This idempotency key was used for a different request.')
    return row.response_json


def store(db: Session, actor_id: str, operation: str, key: UUID, payload,
          response: dict, status_code: int) -> None:
    db.add(IdempotencyKeyRow(idempotency_key=str(key), actor_id=actor_id, operation=operation,
                             request_hash=request_hash(payload), response_json=response,
                             status_code=status_code, created_at=clock.now()))
    db.flush()
