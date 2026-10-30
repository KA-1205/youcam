"""Only these stable interfaces cross module boundaries; use dependency injection.

No module imports another module's database models or mutable internals.
Authorization context is resolved server-side, never from request JSON.
"""
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .models import (
    AccessContext,
    Brief,
    CartLine,
    CatalogPage,
    CatalogQuery,
    CatalogSnapshot,
    CommerceEvent,
    DurableTask,
    ItemRef,
    OrderSnapshot,
    PaymentResult,
    PreviewRequest,
    ProfileSnapshot,
    Reservation,
    SessionSnapshot,
    StockItem,
    StylistRequest,
    StylistResult,
)


class CatalogPort(Protocol):
    def list_variants(self, ctx: AccessContext, cursor: str | None, limit: int, query: CatalogQuery | None = None) -> CatalogPage: ...
    def snapshot(self, ctx: AccessContext, variant_ids: list[str]) -> CatalogSnapshot: ...


class ProfilePort(Protocol):
    def snapshot(self, ctx: AccessContext) -> ProfileSnapshot: ...
    def consume_commerce_event(self, ctx: AccessContext, event: CommerceEvent) -> None: ...


class SessionPort(Protocol):
    def snapshot(self, ctx: AccessContext, session_id: UUID) -> SessionSnapshot: ...
    def apply(self, ctx: AccessContext, session_id: UUID, expected_version: int,
              selections: list[ItemRef], approved_exception_ids: list[UUID],
              approved_brief: Brief | None = None) -> SessionSnapshot: ...


class RecommendationPort(Protocol):
    def propose(self, ctx: AccessContext, request: StylistRequest,
                session: SessionSnapshot, catalog: CatalogSnapshot,
                profile: ProfileSnapshot) -> StylistResult: ...


class PaymentPort(Protocol):
    def initiate(self, order: OrderSnapshot, intent_id: UUID) -> PaymentResult: ...
    def get_status(self, attempt_id: str) -> PaymentResult: ...
    def cancel(self, attempt_id: str, intent_id: UUID) -> PaymentResult: ...
    def refund(self, order_id: UUID, amount_minor: int, intent_id: UUID) -> PaymentResult: ...


class WarehousePort(Protocol):
    def get_stock(self, variant_ids: list[str]) -> list[StockItem]: ...
    def reserve(self, lines: list[CartLine], expires_at: datetime, intent_id: UUID) -> Reservation: ...
    def release(self, reservation_id: UUID, intent_id: UUID) -> None: ...
    def submit_order(self, order: OrderSnapshot, reservation_id: UUID, intent_id: UUID) -> str: ...
    def get_fulfilment(self, order_id: UUID) -> OrderSnapshot: ...


class TaskPort(Protocol):
    """Durable intent before dispatch; UNKNOWN never authorizes resubmission."""
    def enqueue(self, ctx: AccessContext, task: DurableTask) -> UUID: ...
    def claim(self, worker_id: str, now: datetime) -> DurableTask | None: ...
    def reconcile(self, task_id: UUID) -> None: ...


class PreviewPort(Protocol):
    def enqueue(self, ctx: AccessContext, request: PreviewRequest, intent_id: UUID) -> UUID: ...
