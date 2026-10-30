"""Commerce persistence: quotes, orders, payment attempts, warehouse, outbox, idempotency."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class CommerceBase(DeclarativeBase):
    pass


class CartQuoteRow(CommerceBase):
    __tablename__ = 'cart_quotes'

    quote_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str] = mapped_column(String(64))
    session_version: Mapped[int] = mapped_column(Integer)
    quote_version: Mapped[int] = mapped_column(Integer)
    lines: Mapped[list] = mapped_column('lines_json', type_=JSON)
    merchandise_minor: Mapped[int] = mapped_column(Integer)
    shipping_minor: Mapped[int] = mapped_column(Integer)
    tax_minor: Mapped[int] = mapped_column(Integer)
    total_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8))
    mode: Mapped[str] = mapped_column(String(8))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrderRow(CommerceBase):
    __tablename__ = 'orders'

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    order_version: Mapped[int] = mapped_column(Integer)
    event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24))
    lines: Mapped[list] = mapped_column('lines_json', type_=JSON)
    total_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8))
    mode: Mapped[str] = mapped_column(String(8))
    return_status: Mapped[str] = mapped_column(String(16), default='NONE')
    quote_id: Mapped[str] = mapped_column(String(64))
    reservation_id: Mapped[str | None] = mapped_column(String(64))
    payment_reference: Mapped[str] = mapped_column(String(128))
    address_reference: Mapped[str] = mapped_column(String(128))
    payment_attempt_id: Mapped[str | None] = mapped_column(String(64))
    stock_restored: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PaymentAttemptRow(CommerceBase):
    __tablename__ = 'payment_attempts'

    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    intent_id: Mapped[str] = mapped_column(String(64))
    reference: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24))
    mode: Mapped[str] = mapped_column(String(8))
    scripted_outcome: Mapped[str] = mapped_column(String(24))
    action: Mapped[str | None] = mapped_column('action_text', type_=String, nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WarehouseStockRow(CommerceBase):
    __tablename__ = 'warehouse_stock'

    variant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    available: Mapped[int | None] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str] = mapped_column(String(64))


class ReservationRow(CommerceBase):
    __tablename__ = 'warehouse_reservations'

    reservation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    lines: Mapped[list] = mapped_column('lines_json', type_=JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(8))
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    released: Mapped[bool] = mapped_column(Boolean, default=False)
    restored: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutboxEventRow(CommerceBase):
    __tablename__ = 'outbox_events'

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    event_sequence: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column('payload_json', type_=JSON)
    status: Mapped[str] = mapped_column(String(16), default='PENDING')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyKeyRow(CommerceBase):
    __tablename__ = 'idempotency_keys'

    idempotency_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(64))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[dict] = mapped_column('response_json', type_=JSON)
    status_code: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
