"""Worker composition: same backend services, separate process, leased dispatch."""
import hashlib
import json
import os
import socket
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.db import Database
from apps.api.demo_catalog import FixtureCatalog
from apps.api.errors import ApiError
from apps.api.modules.commerce.models import OrderRow, OutboxEventRow
from apps.api.modules.commerce.ports import DemoPaymentPort
from apps.api.modules.commerce.service import CommerceService
from apps.api.modules.shopper_profile.service import ProfileService
from apps.api.modules.styling_session.service import SessionService
from apps.api.modules.task_runtime.models import DurableTaskRow
from apps.api.modules.task_runtime.service import TaskService
from apps.api.modules.tenant_access.service import AccessService
from contracts.runtime.models import CommerceEvent

OUTBOX_TTL_MARK = 'PUBLISHED'


@dataclass
class Runtime:
    database: Database
    catalog: FixtureCatalog
    access: AccessService
    profile: ProfileService
    sessions: SessionService
    tasks: TaskService
    payment: DemoPaymentPort
    commerce: CommerceService
    worker_id: str

    def cycle(self, max_tasks: int = 10) -> dict:
        """One worker cycle: reclaim expired leases, reconcile timeouts, run due tasks."""
        summary = {'reclaimedLeases': 0, 'reconciledTimeouts': 0, 'succeeded': 0,
                   'retried': 0, 'failed': 0}
        with self.database.unit_of_work() as db:
            summary['reclaimedLeases'] = self.tasks.reclaim_expired_leases(db, _now())
            summary['reconciledTimeouts'] = self._reconcile_timeouts(db)
        for _ in range(max_tasks):
            outcome = self._run_one()
            if outcome is None:
                break
            summary[outcome] += 1
        return summary

    def _run_one(self) -> str | None:
        with self.database.unit_of_work() as db:
            task = self.tasks.claim(db, self.worker_id, _now())
            if task is None:
                return None
        with self.database.unit_of_work() as db:
            row = db.get(DurableTaskRow, str(task.taskId))
            assert row is not None
            try:
                self._dispatch(db, row.operation, row.resource_id, row.context_json)
                self.tasks.complete(db, task.taskId, _now())
                return 'succeeded'
            except ApiError as error:
                db.rollback()
                return self._record_failure(task.taskId, error.code)

    def _record_failure(self, task_id, error_code: str) -> str:
        with self.database.unit_of_work() as db:
            outcome = self.tasks.fail(db, task_id, error_code, _now())
        return {'WAITING': 'retried', 'FAILED': 'failed'}.get(outcome, 'retried')

    def _dispatch(self, db: Session, operation: str, resource_id: str, context: dict) -> None:
        if operation == 'COMMERCE_EVENT':
            self._publish_commerce_event(db, resource_id, context)
        elif operation == 'STYLIST':
            raise ApiError(503, 'STYLIST_UNAVAILABLE',
                           'The stylist lane is not integrated on this branch.')
        else:
            raise ApiError(503, 'HANDLER_UNAVAILABLE',
                           f'No worker handler is wired for {operation} yet.')

    def _publish_commerce_event(self, db: Session, event_id: str, context: dict) -> None:
        row = db.get(OutboxEventRow, event_id)
        if row is None:
            return  # nothing to publish; the enqueue was replayed
        payload = dict(row.payload)
        payload.pop('extra', None)
        event = CommerceEvent(**payload)
        order = db.get(OrderRow, str(event.orderId))
        account_id = order.account_id if order is not None else context.get('account_id')
        if not account_id:
            raise ApiError(409, 'EVENT_TARGET_MISSING',
                           'No account is attributable for this commerce event.')
        self.profile.consume_commerce_event(db, account_id, event)
        row.status = OUTBOX_TTL_MARK
        row.published_at = _now()

    def _reconcile_timeouts(self, db: Session) -> int:
        rows = db.scalars(select(OrderRow).where(OrderRow.status == 'PAYMENT_PENDING')).all()
        reconciled = 0
        for order in rows:
            before = order.status
            self.commerce.reconcile_timeout(db, order, _now())
            if order.status != before:
                reconciled += 1
        return reconciled

    def enqueue_outbox_backlog(self) -> int:
        """Safety net: enqueue tasks for any pending outbox event missing its task."""
        with self.database.unit_of_work() as db:
            pending = db.scalars(select(OutboxEventRow)
                                 .where(OutboxEventRow.status == 'PENDING')).all()
            enqueued = 0
            for row in pending:
                payload = dict(row.payload)
                payload.pop('extra', None)
                from uuid import UUID

                self.tasks.enqueue_direct(
                    db, row.tenant_id, '', 'COMMERCE_EVENT', UUID(row.event_id),
                    hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                    UUID(row.event_id))
                enqueued += 1
            return enqueued


def build_runtime(database: Database) -> Runtime:
    catalog = FixtureCatalog()
    profile = ProfileService(resolve_slot=catalog.slot_for)
    sessions = SessionService(catalog)
    tasks = TaskService()
    payment = DemoPaymentPort()
    commerce = CommerceService(payment, catalog, sessions.assert_editable, tasks.enqueue_direct)
    return Runtime(database=database, catalog=catalog, access=AccessService(), profile=profile,
                   sessions=sessions, tasks=tasks, payment=payment, commerce=commerce,
                   worker_id=os.getenv('WORKER_ID', f'worker-{socket.gethostname()}'))


def _now():
    from apps.api import clock

    return clock.now()
