"""One durable provider step per worker cycle; polling never resubmits a task."""
import os
from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import ApiError
from apps.api.modules.try_on_jobs.live_gateway import LiveGateway, payload_for
from apps.api.modules.try_on_jobs.live_models import CreditBudget, LiveStep
from apps.api.modules.try_on_jobs.models import FeatureCostRow
from apps.api.modules.try_on_jobs.orchestration_models import ChildTaskRow, PreviewJobRow
from contracts.runtime.models import AccessContext


def gateway_factory() -> LiveGateway:
    return LiveGateway(os.environ['YOUCAM_API_KEY'])


class LiveRunner:
    def __init__(self, read_asset: Callable, store_result: Callable) -> None:
        self.read_asset = read_asset
        self.store_result = store_result

    def run(self, db: Session, job: PreviewJobRow, child: ChildTaskRow,
            ctx: AccessContext, revalidate: Callable) -> str:
        gateway = gateway_factory()
        try:
            return self._run(db, job, child, ctx, revalidate, gateway)
        finally:
            gateway.close()

    def _run(self, db: Session, job: PreviewJobRow, child: ChildTaskRow,
             ctx: AccessContext, revalidate: Callable, gateway: LiveGateway) -> str:
        receipt = db.get(LiveStep, child.child_task_id)
        if receipt is None:
            settings = dict(job.settings)
            source = child.source_asset_id
            previous = db.scalar(select(ChildTaskRow).where(
                ChildTaskRow.job_id == job.job_id, ChildTaskRow.sequence == child.sequence - 1))
            if previous is not None and previous.result_asset_id:
                source = previous.result_asset_id
            data, mime = self.read_asset(db, ctx, source)
            if mime not in ('image/jpeg', 'image/png'):
                raise ApiError(422, 'VALIDATION_ERROR', 'Live previews require JPEG or PNG photos.')
            refs = []
            if child.capability not in ('HAIR_COLOR', 'MAKEUP'):
                for item in child.applied_items:
                    asset_id = settings.get('reference:' + item['reference'])
                    if not asset_id:
                        raise ApiError(422, 'REFERENCE_REQUIRED',
                                       'Upload a permitted product photo for each selected item.')
                    # Read through storage authorization before any external transfer.
                    try:
                        reference_id = str(UUID(asset_id))
                    except ValueError:
                        raise ApiError(422, 'VALIDATION_ERROR', 'Invalid reference asset.') from None
                    ref_data, ref_mime = self.read_asset(db, ctx, reference_id)
                    if ref_mime not in ('image/jpeg', 'image/png'):
                        raise ApiError(422, 'VALIDATION_ERROR', 'Product photos require JPEG or PNG.')
                    refs.append((ref_data, ref_mime))
                if child.capability == 'CLOTHES_V4':
                    settings['area'] = child.applied_items[0]['area']
            # Validate settings before uploads or reservations.
            payload_for(child.capability, 'source', ['ref'] * len(refs), settings)
            cached = db.get(FeatureCostRow, child.capability)
            if (cached is not None and cached.source_version.startswith('live:')
                    and clock.now() - clock.as_utc(cached.fetched_at) < timedelta(hours=24)):
                cost = cached.cost_units
            else:
                cost = gateway.cost(child.capability)
                if cached is None:
                    db.add(FeatureCostRow(capability=child.capability, cost_units=cost,
                                          fetched_at=clock.now(), source_version='live:feature-cost'))
                else:
                    cached.cost_units = cost
                    cached.fetched_at = clock.now()
                    cached.source_version = 'live:feature-cost'

            limit = int(os.getenv('YOUCAM_CREDIT_LIMIT', '0'))
            budget = db.get(CreditBudget, 'youcam')
            if budget is None or budget.reserved_units + cost > limit:
                raise ApiError(429, 'CREDIT_LIMIT', 'The configured provider credit limit is reached.')
            file_id = gateway.upload(data, mime)
            reference_ids = [gateway.upload(b, m, ring=child.capability == 'RING') for b, m in refs]
            receipt = LiveStep(child_id=child.child_task_id,
                               payload=payload_for(child.capability, file_id, reference_ids, settings),
                               reserved_units=cost, submit_started=False,
                               next_poll_at=clock.now(), deleted=False)
            changed = db.execute(update(CreditBudget).where(
                CreditBudget.budget_id == 'youcam',
                CreditBudget.reserved_units + cost <= limit).values(
                    reserved_units=CreditBudget.reserved_units + cost).returning(
                        CreditBudget.budget_id))
            if changed.scalar_one_or_none() is None:
                raise ApiError(429, 'CREDIT_LIMIT', 'The configured provider credit limit is reached.')
            db.add(receipt)
            db.commit()  # Reservation and request payload survive a process crash.
        if not child.provider_task_id:
            if receipt.submit_started:
                child.unknown_charge_reserved = True
                job.status = 'TIMED_OUT'
                job.error_json = {'code': 'UNKNOWN_OUTCOME', 'message':
                                  'Submission needs reconciliation; it will not be repeated.'}
                db.commit()
                return 'FAILED'
            revalidate()
            receipt.submit_started = True
            child.status = 'SUBMITTED'
            child.unknown_charge_reserved = True
            db.commit()  # Persist before the only potentially billable POST.
            try:
                child.provider_task_id = gateway.submit(child.capability, receipt.payload)
            except ApiError as exc:
                # Even a response parse failure can mean a paid request was accepted.
                job.status = 'TIMED_OUT'
                job.error_json = {'code': 'UNKNOWN_OUTCOME', 'message':
                                  'Provider submission needs reconciliation.'}
                child.error_code = exc.code
                db.commit()
                return 'FAILED'
            child.unknown_charge_reserved = False
            child.status = 'RUNNING'
            receipt.next_poll_at = clock.now() + timedelta(seconds=10)
            db.commit()
            return 'RUNNING'
        if clock.now() < clock.as_utc(receipt.next_poll_at):
            return 'RUNNING'
        if clock.now() - clock.as_utc(job.created_at) > timedelta(minutes=10):
            job.status = 'TIMED_OUT'
            child.unknown_charge_reserved = True
            job.error_json = {'code': 'UNKNOWN_OUTCOME', 'message':
                              'Provider outcome needs reconciliation; no resubmission is allowed.'}
            db.commit()
            return 'FAILED'
        try:
            state = gateway.poll(child.capability, child.provider_task_id)
        except ApiError as exc:
            try:
                delay = max(30, int((exc.headers or {}).get('Retry-After', '30')))
            except ValueError:
                delay = 30
            receipt.next_poll_at = clock.now() + timedelta(seconds=delay)
            db.commit()
            return 'RUNNING'
        if state['task_status'] == 'running':
            receipt.next_poll_at = clock.now() + timedelta(seconds=15)
            db.commit()
            return 'RUNNING'
        if state['task_status'] == 'error':
            child.status = 'FAILED'
            child.error_code = 'PROVIDER_REJECTED'
            job.error_json = {'code': 'PROVIDER_REJECTED', 'message':
                              'YouCam could not process this photo. Check the capture guidance.'}
            db.commit()
            self.cleanup(db, gateway, child, receipt)
            return 'FAILED'
        results = state.get('results', {})
        if isinstance(results, list) and results:
            results = results[0]
        url = results.get('url') if isinstance(results, dict) else None
        if not isinstance(url, str):
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'YouCam returned no result image.')
        try:
            data = gateway.download(url)
        except ApiError as exc:
            if exc.code != 'PROVIDER_OUTAGE':
                raise
            receipt.next_poll_at = clock.now() + timedelta(seconds=30)
            db.commit()
            return 'RUNNING'
        revalidate()  # Consent, cancellation and session may have changed during I/O.
        child.result_asset_id = self.store_result(db, job.tenant_id, job.actor_id,
                                                  child.capability, data)
        child.status = 'SUCCEEDED'
        db.commit()
        self.cleanup(db, gateway, child, receipt)
        return 'SUCCEEDED'

    def sweep_deletions(self, db: Session) -> int:
        rows = db.execute(select(LiveStep, ChildTaskRow).join(
            ChildTaskRow, ChildTaskRow.child_task_id == LiveStep.child_id).where(
                LiveStep.deleted.is_(False), ChildTaskRow.provider_task_id.is_not(None),
                ChildTaskRow.status.in_(('SUCCEEDED', 'FAILED', 'CANCELLED')))).all()
        if not rows:
            return 0
        gateway = gateway_factory()
        deleted = 0
        try:
            for receipt, child in rows:
                self.cleanup(db, gateway, child, receipt)
                deleted += int(receipt.deleted)
        finally:
            gateway.close()
        return deleted

    @staticmethod
    def cleanup(db: Session, gateway: LiveGateway, child: ChildTaskRow, receipt: LiveStep) -> None:
        if child.provider_task_id and not receipt.deleted:
            try:
                gateway.delete(child.provider_task_id)
                receipt.deleted = True
                db.commit()
            except ApiError:
                pass  # Receipt persists; the worker sweeps unacknowledged deletions.
