"""Demo payment and warehouse adapters behind the frozen ports.

These are labelled DEMO simulations: scripted outcomes are stored server-side and
public shoppers cannot forge SUCCESS. A live adapter may report unsupported
operations explicitly; it can never emulate success. No adapter mutates wardrobe.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.modules.commerce.models import ReservationRow, WarehouseStockRow
from contracts.runtime.models import CartLine, OrderSnapshot, PaymentResult, Reservation, StockItem

RESERVATION_TTL = 900  # demo reservation lasts 15 minutes using server time

PaymentStatus = Literal['PENDING', 'ACTION_REQUIRED', 'SUCCEEDED', 'FAILED', 'UNKNOWN',
                        'CANCELLED', 'REFUNDED']


class DemoPaymentPort:
    """Scripted demo processor; the scripted outcome is decided before initiate."""

    def __init__(self, scripted: dict[str, str] | None = None) -> None:
        self._scripted = scripted or {}

    def script(self, intent_id: UUID, outcome: str) -> None:
        self._scripted[str(intent_id)] = outcome

    def outcome(self, intent_id: UUID) -> str:
        return self._scripted.get(str(intent_id), 'SUCCESS')

    def initiate(self, order: OrderSnapshot, intent_id: UUID) -> PaymentResult:
        return self._result(self.outcome(intent_id), f'demo-attempt-{intent_id.hex[:12]}')

    def get_status(self, attempt_id: str) -> PaymentResult:
        return self._result('SUCCESS', attempt_id)

    def cancel(self, attempt_id: str, intent_id: UUID) -> PaymentResult:
        return PaymentResult(mode='DEMO', reference=attempt_id, status='CANCELLED', action=None,
                             error=None)

    def refund(self, order_id: UUID, amount_minor: int, intent_id: UUID) -> PaymentResult:
        return PaymentResult(mode='DEMO', reference=f'demo-refund-{order_id.hex[:12]}',
                             status='REFUNDED', action=None, error=None)

    def _result(self, outcome: str, reference: str) -> PaymentResult:
        mapping: dict[str, tuple[PaymentStatus, str | None]] = {
            'SUCCESS': ('SUCCEEDED', None),
            'DECLINE': ('FAILED', None),
            'AUTH_REQUIRED': ('ACTION_REQUIRED', 'Approve the simulated authentication.'),
            'TIMEOUT': ('UNKNOWN', None),
        }
        status, action = mapping[outcome]
        return PaymentResult(mode='DEMO', reference=reference, status=status, action=action,
                             error=None)


class DemoWarehousePort:
    """Demo stock ledger; the first read seeds availability from the fixture catalog."""

    def __init__(self, db: Session, tenant_id: str, seed_stock: dict[str, int | None]) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._seed = seed_stock

    def get_stock(self, variant_ids: list[str]) -> list[StockItem]:
        return [StockItem(variantId=variant_id, available=self._available(variant_id),
                          checkedAt=clock.now(), sourceVersion='demo-warehouse-1')
                for variant_id in variant_ids]

    def _available(self, variant_id: str) -> int | None:
        row = self._db.get(WarehouseStockRow, variant_id)
        if row is None:
            available = self._seed.get(variant_id)
            row = WarehouseStockRow(variant_id=variant_id, tenant_id=self._tenant_id,
                                    available=available, checked_at=clock.now(),
                                    source_version='demo-warehouse-1')
            self._db.add(row)
            self._db.flush()
        return row.available

    def reserve(self, lines: list[CartLine], expires_at: datetime, intent_id: UUID) -> Reservation:
        for line in lines:
            available = self._available(line.variantId)
            if available is None:
                raise UnknownStock(line.variantId)
            if available < line.quantity:
                raise InsufficientStock(line.variantId)
        reservation_id = str(uuid4())
        self._db.add(ReservationRow(reservation_id=reservation_id,
                                    tenant_id=self._tenant_id,
                                    lines=[line.model_dump() for line in lines],
                                    expires_at=expires_at, mode='DEMO',
                                    created_at=clock.now()))
        self._db.flush()
        return Reservation(reservationId=UUID(reservation_id), lines=lines, expiresAt=expires_at,
                           mode='DEMO')

    def release(self, reservation_id: UUID, intent_id: UUID) -> None:
        row = self._db.get(ReservationRow, str(reservation_id))
        if row is not None:
            row.released = True

    def consume(self, reservation_id: UUID) -> None:
        """Atomic decrement: consumes the reservation and decrements stock once."""
        row = self._db.get(ReservationRow, str(reservation_id))
        if row is None or row.consumed or row.released:
            raise ApiConflict('Reservation is no longer active.')
        for line in row.lines:
            stock = self._db.get(WarehouseStockRow, line['variantId'])
            if stock is None or stock.available is None:
                raise ApiConflict('Reserved stock became unknown.')
            stock.available -= line['quantity']
        row.consumed = True
        self._db.flush()

    def restore(self, reservation_id: UUID) -> None:
        """Restore stock exactly once for refunds or return receipts."""
        row = self._db.get(ReservationRow, str(reservation_id))
        if row is None or row.restored:
            return
        for line in row.lines:
            stock = self._db.get(WarehouseStockRow, line['variantId'])
            if stock is not None and stock.available is not None:
                stock.available += line['quantity']
        row.restored = True
        self._db.flush()

    def submit_order(self, order: OrderSnapshot, reservation_id: UUID, intent_id: UUID) -> str:
        return f'demo-warehouse-{order.orderId.hex[:12]}'

    def get_fulfilment(self, order_id: UUID) -> OrderSnapshot:
        raise NotImplementedError('fulfilment state lives in the order row')


class UnknownStock(Exception):
    def __init__(self, variant_id: str) -> None:
        super().__init__(variant_id)
        self.variant_id = variant_id


class InsufficientStock(Exception):
    def __init__(self, variant_id: str) -> None:
        super().__init__(variant_id)
        self.variant_id = variant_id


class ApiConflict(Exception):
    pass
