"""TaskPort implementation: durable intent before dispatch; UNKNOWN never authorizes resubmission.

Enqueue is idempotent by (idempotency_key, request_hash). Claims lease one task
atomically (FOR UPDATE SKIP LOCKED where the dialect supports it); expired leases
are reclaimed with a retry backoff, and terminal failure preserves a sanitized
error code for reconciliation review.
"""
from datetime import datetime, timedelta
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import IDEMPOTENCY_CONFLICT, ApiError
from apps.api.modules.task_runtime.models import DurableTaskRow, TaskBase
from contracts.runtime.models import AccessContext, DurableTask

LEASE_TTL = 120  # seconds; short leases keep reconciliation prompt
RETRY_BACKOFF = 5  # seconds between attempts; grows linearly with the attempt count

DurableTaskOperation = Literal['STYLIST', 'PREVIEW', 'COMMERCE_EVENT', 'ASSET_DELETE']


def to_dto(row: DurableTaskRow) -> DurableTask:
    return DurableTask(taskId=UUID(row.task_id), tenantId=row.tenant_id, actorId=row.actor_id,
                       operation=cast(DurableTaskOperation, row.operation),
                       resourceId=UUID(row.resource_id), requestHash=row.request_hash,
                       idempotencyKey=UUID(row.idempotency_key), attempt=row.attempt,
                       expectedSessionVersion=row.context_json.get('expectedSessionVersion'),
                       expectedConsentRevision=row.context_json.get('expectedConsentRevision'),
                       leaseExpiresAt=row.lease_expires_at)


class TaskService:
    """Implements the frozen TaskPort."""

    def enqueue(self, db: Session, ctx: AccessContext, task: DurableTask,
                request_hash: str) -> DurableTask:
        """Frozen TaskPort shape: enqueue a durable intent with its request hash."""
        return self.enqueue_direct(db, ctx.tenantId, ctx.actorId, task.operation, task.resourceId,
                                   request_hash, task.idempotencyKey)

    def enqueue_direct(self, db: Session, tenant_id: str, actor_id: str, operation: str,
                       resource_id: UUID, request_hash: str, idempotency_key: UUID,
                       max_attempts: int = 3, context: dict | None = None) -> DurableTask:
        row = db.scalar(select(DurableTaskRow)
                        .where(DurableTaskRow.idempotency_key == str(idempotency_key)))
        if row is not None:
            if row.request_hash != request_hash or row.operation != operation:
                raise ApiError(409, IDEMPOTENCY_CONFLICT,
                               'This idempotency key was used for a different request.')
            return to_dto(row)
        now = clock.now()
        row = DurableTaskRow(task_id=str(uuid4()), tenant_id=tenant_id, actor_id=actor_id,
                             operation=operation, resource_id=str(resource_id),
                             request_hash=request_hash, idempotency_key=str(idempotency_key),
                             status='PENDING', attempt=0, max_attempts=max_attempts,
                             lease_worker_id=None, lease_expires_at=None, available_at=now,
                             last_error_code=None, context_json=context or {},
                             created_at=now, updated_at=now)
        db.add(row)
        db.flush()
        return to_dto(row)

    def claim(self, db: Session, worker_id: str, now: datetime) -> DurableTask | None:
        row = db.scalar(
            select(DurableTaskRow)
            .where(DurableTaskRow.status.in_(('PENDING', 'WAITING')),
                   DurableTaskRow.available_at <= now)
            .order_by(DurableTaskRow.created_at).limit(1)
            .with_for_update(skip_locked=True))
        if row is None:
            return None
        row.status = 'LEASED'
        row.attempt += 1
        row.lease_worker_id = worker_id
        row.lease_expires_at = now + timedelta(seconds=LEASE_TTL)
        row.updated_at = now
        db.flush()
        return to_dto(row)

    def complete(self, db: Session, task_id: UUID, now: datetime) -> None:
        row = db.get(DurableTaskRow, str(task_id))
        if row is not None:
            row.status = 'SUCCEEDED'
            row.lease_worker_id = None
            row.lease_expires_at = None
            row.updated_at = now
            db.flush()

    def fail(self, db: Session, task_id: UUID, error_code: str, now: datetime) -> str:
        """Record a failure: retry with backoff, or park as FAILED after the attempt budget."""
        row = db.get(DurableTaskRow, str(task_id))
        if row is None:
            return 'GONE'
        row.last_error_code = error_code
        row.updated_at = now
        if row.attempt >= row.max_attempts:
            row.status = 'FAILED'
            row.lease_worker_id = None
            row.lease_expires_at = None
            db.flush()
            return 'FAILED'
        row.status = 'WAITING'
        row.available_at = now + timedelta(seconds=RETRY_BACKOFF * max(row.attempt, 1))
        row.lease_worker_id = None
        row.lease_expires_at = None
        db.flush()
        return 'WAITING'

    def reclaim_expired_leases(self, db: Session, now: datetime) -> int:
        rows = db.scalars(select(DurableTaskRow)
                          .where(DurableTaskRow.status == 'LEASED',
                                 DurableTaskRow.lease_expires_at <= now)).all()
        for row in rows:
            row.status = 'WAITING'
            row.available_at = now + timedelta(seconds=RETRY_BACKOFF)
            row.lease_worker_id = None
            row.lease_expires_at = None
            row.updated_at = now
        db.flush()
        return len(rows)

    def get(self, db: Session, task_id: UUID) -> DurableTask | None:
        row = db.get(DurableTaskRow, str(task_id))
        return to_dto(row) if row is not None else None

    def cancel_for_actors(self, db: Session, actor_ids: list[str], now: datetime) -> int:
        """Stop queued or leased work for deleted accounts; the claim loop skips these."""
        if not actor_ids:
            return 0
        rows = db.scalars(select(DurableTaskRow)
                          .where(DurableTaskRow.actor_id.in_(actor_ids),
                                 DurableTaskRow.status.in_(('PENDING', 'WAITING', 'LEASED')))).all()
        for row in rows:
            row.status = 'CANCELLED'
            row.lease_worker_id = None
            row.lease_expires_at = None
            row.updated_at = now
        db.flush()
        return len(rows)


__all__ = ['TaskBase', 'TaskService', 'LEASE_TTL', 'RETRY_BACKOFF']
