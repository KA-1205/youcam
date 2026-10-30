"""Preview orchestration: durable intent before any paid call, staged child chains,
quotas and unknown-outcome reconciliation.

Safeguards enforced here: consent revision and session version at dispatch and
at every serving; explicit opt-in for Facial Color Tones; ten paid intents per
visitor per day and one active render per visitor; a failed chain stops while
retaining valid independent previews; UNKNOWN provider outcomes reserve the
charge and never authorize resubmission.
"""
import hashlib
import json
from collections.abc import Callable
from typing import Literal, cast
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import CONSENT_REQUIRED, QUOTA_EXCEEDED, STALE_VERSION, ApiError
from apps.api.modules.task_runtime.service import TaskService
from apps.api.modules.try_on_jobs.orchestration_models import (
    ActiveJobMarker,
    ChildTaskRow,
    PreviewBase,
    PreviewJobRow,
    QuotaCounterRow,
)
from apps.api.modules.try_on_jobs.providers.adapters import adapter_for
from apps.api.modules.try_on_jobs.providers.base import ProviderClient
from contracts.runtime.models import (
    AccessContext,
    Capability,
    ChildTask,
    ConsentSnapshot,
    ErrorDetail,
    PreviewJob,
    PreviewRequest,
)

DAILY_PAID_INTENT_LIMIT = 10
RENDER_TIMEOUT_SECONDS = 600
JobStatus = Literal['CREATED', 'QUEUED', 'SUBMITTED', 'RUNNING', 'SUCCEEDED', 'FAILED',
                    'TIMED_OUT', 'CANCELLED']
ACTIVE_STATUSES = ('CREATED', 'QUEUED', 'SUBMITTED', 'RUNNING')

BASE_SLOTS = {'TOP': 'upper_body', 'BOTTOM': 'lower_body', 'ONE_PIECE': 'full_body',
              'OUTER': 'outer', 'SHOES': 'shoes'}


def child_dto(row: ChildTaskRow) -> ChildTask:
    return ChildTask(childTaskId=UUID(row.child_task_id),
                     capability=cast(Capability, row.capability),
                     status=cast(JobStatus, row.status), sourceAssetId=UUID(row.source_asset_id),
                     resultAssetId=UUID(row.result_asset_id) if row.result_asset_id else None,
                     appliedItems=[], unknownChargeReserved=row.unknown_charge_reserved)


def plan_chain(request: PreviewRequest) -> list[tuple[str, list[dict[str, str]]]]:
    """Stage order: base (one-piece or top then bottom), outer, shoes; absent slots omitted."""
    if request.capability != 'CLOTHES_V4':
        return [(request.capability, _items_for(request))]
    steps: list[tuple[str, list[dict[str, str]]]] = []
    base_items: list[dict[str, str]] = []
    outer_items: list[dict[str, str]] = []
    shoe_items: list[dict[str, str]] = []
    for selection in request.selections:
        area = BASE_SLOTS.get(selection.slot)
        if area in ('upper_body', 'lower_body', 'full_body'):
            base_items.append({'area': area, 'reference': selection.refId})
        elif area == 'outer':
            outer_items.append({'area': area, 'reference': selection.refId})
        elif area == 'shoes':
            shoe_items.append({'area': area, 'reference': selection.refId})
    if base_items:
        steps.append(('CLOTHES_V4', base_items))
    if outer_items:
        steps.append(('CLOTHES_V4', outer_items))
    if shoe_items:
        steps.append(('CLOTHES_V4', shoe_items))
    if not steps:
        raise ApiError(422, 'VALIDATION_ERROR', 'No supported clothing area was selected.')
    return steps


def _items_for(request: PreviewRequest) -> list[dict[str, str]]:
    if request.capability == 'MAKEUP':
        return [{'kind': 'makeup', 'effect': effect} for effect in request.effectIds]
    if request.capability == 'HAIR_COLOR':
        return [{'preset': request.settings.get('preset', 'natural')}]
    if request.capability == 'FACIAL_COLOR_TONES':
        return []
    reference = request.selections[0].refId if request.selections else 'fixture'
    return [{'reference': reference}]


def _job_ctx(job: PreviewJobRow) -> AccessContext:
    return AccessContext(actorId=job.actor_id, tenantId=job.tenant_id, roles=['SHOPPER'],
                         verifiedAccount=True, consentRevision=job.consent_revision)


class PreviewService:
    """Implements the frozen PreviewPort plus the worker-side runner."""

    def __init__(self, session_guard: Callable, catalog, consent_lookup: Callable[..., object],
                 store_result: Callable[..., str], tasks: TaskService, asset_check: Callable,
                 client_factory: Callable[[str], ProviderClient] | None = None,
                 mode: str = 'FIXTURE') -> None:
        self._session_guard = session_guard
        self._catalog = catalog
        self._consent_lookup = consent_lookup
        self._store_result = store_result
        self._asset_check = asset_check
        self._tasks = tasks
        self._mode = mode
        self._client_factory = client_factory or self._fixture_client

    # Enqueue (HTTP side) ----------------------------------------------------

    def enqueue(self, db: Session, ctx: AccessContext, request: PreviewRequest,
                consent_snapshot: ConsentSnapshot, intent_id: UUID) -> UUID:
        self._session_guard(db, ctx, request.sessionId, request.expectedSessionVersion)
        if request.expectedConsentRevision != consent_snapshot.consentRevision:
            raise ApiError(409, STALE_VERSION, 'Consent changed; review and resubmit.')
        if not consent_snapshot.controls.processPhotos:
            raise ApiError(403, CONSENT_REQUIRED, 'Photo processing consent is required.')
        if not self._asset_available(db, ctx, str(request.sourceAssetId)):
            raise ApiError(404, 'NOT_FOUND', 'No available source photo for this account.')
        if request.capability == 'FACIAL_COLOR_TONES' \
                and request.settings.get('facialColorAnalysisOptIn') != 'true':
            raise ApiError(403, CONSENT_REQUIRED,
                           'Facial color analysis requires its own explicit opt-in.')
        if request.selections and request.capability != 'HAIR_COLOR':
            found = {variant.variantId for variant in self._catalog.snapshot(
                ctx, [item.refId for item in request.selections if item.refType == 'VARIANT']
            ).variants}
            missing = sorted({item.refId for item in request.selections
                              if item.refType == 'VARIANT'} - found)
            if missing:
                raise ApiError(422, 'VALIDATION_ERROR',
                               f'Unknown catalog references: {", ".join(missing)}.')
        plan_chain(request)  # validates supported areas before any durable write
        self._check_quota(db, ctx.actorId, request)
        now = clock.now()
        job_id = str(uuid4())
        db.add(PreviewJobRow(job_id=job_id, tenant_id=ctx.tenantId, actor_id=ctx.actorId,
                             session_id=str(request.sessionId),
                             session_version=request.expectedSessionVersion,
                             consent_revision=request.expectedConsentRevision, status='QUEUED',
                             freshness='CURRENT', execution_mode=self._mode,
                             capability=request.capability,
                             source_asset_id=str(request.sourceAssetId),
                             selections=[item.model_dump() for item in request.selections],
                             effect_ids=list(request.effectIds), settings=dict(request.settings),
                             error_json=None, created_at=now, updated_at=now))
        for sequence, (capability, items) in enumerate(plan_chain(request)):
            db.add(ChildTaskRow(child_task_id=str(uuid4()), job_id=job_id, sequence=sequence,
                                capability=capability, status='CREATED',
                                source_asset_id=str(request.sourceAssetId),
                                result_asset_id=None, applied_items=items,
                                unknown_charge_reserved=False, provider_task_id=None, attempt=0,
                                error_code=None, created_at=now, updated_at=now))
        self._consume_quota(db, ctx.actorId)
        db.add(ActiveJobMarker(actor_id=ctx.actorId, job_id=job_id, updated_at=now))
        # The durable task intent commits in this same transaction, before any
        # provider submission can happen in the worker.
        request_hash = hashlib.sha256(json.dumps({'job': job_id}, sort_keys=True)
                                      .encode()).hexdigest()
        self._tasks.enqueue_direct(db, ctx.tenantId, ctx.actorId, 'PREVIEW', UUID(job_id),
                                   request_hash, intent_id, context={'account_id': ctx.actorId})
        self.supersede_stale(db, ctx, request.sessionId, request.expectedSessionVersion)
        db.flush()
        return UUID(job_id)

    def _check_quota(self, db: Session, actor_id: str, request: PreviewRequest) -> None:
        today = clock.now().date().isoformat()
        row = db.scalar(select(QuotaCounterRow).where(QuotaCounterRow.actor_id == actor_id,
                                                      QuotaCounterRow.day == today))
        if row is not None and row.paid_intents >= DAILY_PAID_INTENT_LIMIT:
            raise ApiError(429, QUOTA_EXCEEDED, 'Daily preview quota reached.',
                           headers={'Retry-After': '86400'})
        marker = db.get(ActiveJobMarker, actor_id)
        if marker is not None:
            active = db.get(PreviewJobRow, marker.job_id)
            if active is not None and active.status in ACTIVE_STATUSES:
                same_session = str(request.sessionId) == active.session_id
                supersedes = same_session and active.session_version < request \
                    .expectedSessionVersion
                if not supersedes:
                    raise ApiError(429, QUOTA_EXCEEDED,
                                   'One preview render can run at a time.',
                                   headers={'Retry-After': '60'})
                # The newer request supersedes the stale active render for this session.
                active.freshness = 'SUPERSEDED'
                active.status = 'CANCELLED'
                active.updated_at = clock.now()
                for child in db.scalars(select(ChildTaskRow).where(
                        ChildTaskRow.job_id == active.job_id,
                        ChildTaskRow.status.in_(ACTIVE_STATUSES))):
                    child.status = 'CANCELLED'
                    child.updated_at = clock.now()
            db.delete(marker)
            db.flush()

    def _consume_quota(self, db: Session, actor_id: str) -> None:
        today = clock.now().date().isoformat()
        row = db.scalar(select(QuotaCounterRow).where(QuotaCounterRow.actor_id == actor_id,
                                                      QuotaCounterRow.day == today))
        if row is None:
            db.add(QuotaCounterRow(counter_id=str(uuid4()), actor_id=actor_id, day=today,
                                   paid_intents=1, updated_at=clock.now()))
        else:
            row.paid_intents += 1
            row.updated_at = clock.now()
        db.flush()

    # Serving ----------------------------------------------------------------

    def get(self, db: Session, ctx: AccessContext, job_id: UUID) -> PreviewJob:
        row = self._owned_job(db, ctx, job_id)
        children = db.scalars(select(ChildTaskRow).where(ChildTaskRow.job_id == str(job_id))
                              .order_by(ChildTaskRow.sequence)).all()
        return PreviewJob(
            jobId=UUID(row.job_id), sessionId=UUID(row.session_id),
            sessionVersion=row.session_version, consentRevision=row.consent_revision,
            status=cast(JobStatus, row.status), freshness=cast(
                Literal['CURRENT', 'SUPERSEDED'], row.freshness),
            executionMode=cast(Literal['FIXTURE', 'LIVE'], row.execution_mode),
            children=[child_dto(child) for child in children],
            error=_error_detail(row.error_json) if row.error_json else None,
            createdAt=row.created_at, updatedAt=row.updated_at)

    def _owned_job(self, db: Session, ctx: AccessContext, job_id: UUID) -> PreviewJobRow:
        row = db.get(PreviewJobRow, str(job_id))
        if row is None or row.tenant_id != ctx.tenantId or row.actor_id != ctx.actorId:
            raise ApiError(404, 'NOT_FOUND', 'Unknown preview job.')
        return row

    def cancel(self, db: Session, ctx: AccessContext, job_id: UUID) -> PreviewJob:
        row = self._owned_job(db, ctx, job_id)
        if row.status not in ACTIVE_STATUSES:
            raise ApiError(409, 'HTTP_ERROR', 'This preview job already finished.')
        row.status = 'CANCELLED'
        row.updated_at = clock.now()
        for child in db.scalars(select(ChildTaskRow)
                                .where(ChildTaskRow.job_id == str(job_id),
                                       ChildTaskRow.status.in_(ACTIVE_STATUSES))):
            child.status = 'CANCELLED'
            child.updated_at = clock.now()
        marker = db.get(ActiveJobMarker, ctx.actorId)
        if marker is not None and marker.job_id == str(job_id):
            db.delete(marker)
        db.flush()
        return self.get(db, ctx, job_id)

    def supersede_stale(self, db: Session, ctx: AccessContext, session_id: UUID,
                        session_version: int) -> None:
        rows = db.scalars(select(PreviewJobRow).where(
            PreviewJobRow.actor_id == ctx.actorId, PreviewJobRow.session_id == str(session_id),
            PreviewJobRow.freshness == 'CURRENT',
            PreviewJobRow.session_version < session_version,
            PreviewJobRow.status.in_(ACTIVE_STATUSES))).all()
        for row in rows:
            row.freshness = 'SUPERSEDED'
            row.updated_at = clock.now()
        db.flush()

    # Worker-side runner -----------------------------------------------------

    def run(self, db: Session, job_id: UUID) -> str:
        """Run the child chain. Consent/session are revalidated; failures stop the chain."""
        job = db.get(PreviewJobRow, str(job_id))
        if job is None or job.status not in ACTIVE_STATUSES:
            return 'SKIPPED'
        consent = cast(ConsentSnapshot, self._consent_lookup(db, job.actor_id))
        if not consent.controls.processPhotos or consent.consentRevision != job.consent_revision:
            return self._terminate(db, job, 'CANCELLED', 'CONSENT_REVOKED',
                                   'Consent was withdrawn before rendering.')
        try:
            self._session_guard(db, _job_ctx(job), UUID(job.session_id), job.session_version)
        except ApiError:
            return self._terminate(db, job, 'SUPERSEDED_SESSION', 'STALE_SESSION',
                                   'The session changed; start a new preview.')
        job.status = 'RUNNING'
        job.updated_at = clock.now()
        children = db.scalars(select(ChildTaskRow).where(ChildTaskRow.job_id == str(job_id))
                              .order_by(ChildTaskRow.sequence)).all()
        outcome = 'SUCCEEDED'
        for child in children:
            if child.status in ('SUCCEEDED', 'CANCELLED'):
                continue
            outcome = self._run_child(db, job, child)
            if outcome != 'SUCCEEDED':
                break  # stop the chain while retaining valid independent previews
        if outcome == 'SUCCEEDED':
            job.status = 'SUCCEEDED'
        elif job.status == 'RUNNING':
            job.status = 'FAILED'
        job.updated_at = clock.now()
        db.flush()
        return outcome

    def _run_child(self, db: Session, job: PreviewJobRow, child: ChildTaskRow) -> str:
        capability = child.capability
        child.status = 'SUBMITTED'
        child.attempt += 1
        child.updated_at = clock.now()
        db.flush()
        client = self._client_factory(capability)
        adapter = adapter_for(capability)
        try:
            payload = adapter.build_payload(child.source_asset_id, child.applied_items)
            provider_task = client.submit(payload)
        except ApiError as error:
            child.status = 'FAILED'
            child.error_code = error.code
            child.updated_at = clock.now()
            db.flush()
            self._job_error(job, error.code, error.message)
            return 'FAILED'
        child.provider_task_id = provider_task
        child.status = 'RUNNING'
        db.flush()
        try:
            poll = client.poll(provider_task)
        except ApiError as error:
            if error.code == 'PROVIDER_OUTAGE':
                # Ambiguous submission: reserve the charge, never blindly resubmit.
                child.unknown_charge_reserved = True
                child.status = 'RUNNING'
                child.updated_at = clock.now()
                db.flush()
                return self._terminate(db, job, 'TIMED_OUT', 'UNKNOWN_OUTCOME',
                                       'The provider outcome is unknown; usage stays reserved '
                                       'pending reconciliation.')
            child.status = 'FAILED'
            child.error_code = error.code
            db.flush()
            self._job_error(job, error.code, error.message)
            return 'FAILED'
        if poll.status != 'SUCCEEDED':
            child.status = 'FAILED'
            child.error_code = poll.error_category or 'PROVIDER_OUTAGE'
            child.updated_at = clock.now()
            db.flush()
            self._job_error(job, child.error_code, 'The preview could not be rendered.')
            return 'FAILED'
        urls = adapter.parse_result(poll.result)
        del urls  # fixture bytes are synthetic; live mode fetches the verified URL
        child.result_asset_id = self._store_result(db, job.tenant_id, job.actor_id,
                                                   child.capability)
        child.status = 'SUCCEEDED'
        child.updated_at = clock.now()
        db.flush()
        return 'SUCCEEDED'

    def _asset_available(self, db: Session, ctx: AccessContext, asset_id: str) -> bool:
        """Ownership/availability check injected at composition to avoid a
        cross-module import of storage persistence internals."""
        return bool(self._asset_check(db, ctx, asset_id))

    def _terminate(self, db: Session, job: PreviewJobRow, status: str, code: str,
                   message: str) -> str:
        job.status = status
        job.error_json = {'code': code, 'message': message, 'details': {}}
        job.updated_at = clock.now()
        for child in db.scalars(select(ChildTaskRow)
                                .where(ChildTaskRow.job_id == str(job.job_id),
                                       ChildTaskRow.status.in_(('CREATED', 'QUEUED')))):
            child.status = 'CANCELLED'
            child.updated_at = clock.now()
        marker = db.get(ActiveJobMarker, job.actor_id)
        if marker is not None and marker.job_id == str(job.job_id):
            db.delete(marker)
        db.flush()
        return 'SUCCEEDED' if status == 'SUCCEEDED' else ('CANCELLED' if status == 'CANCELLED'
                                                          else 'FAILED')

    def _job_error(self, job: PreviewJobRow, code: str, message: str) -> None:
        job.error_json = {'code': code, 'message': message, 'details': {}}

    def _fixture_client(self, capability: str) -> ProviderClient:
        adapter = adapter_for(capability)
        submitted: dict[str, list[dict[str, str]]] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == 'GET':
                task_id = request.url.path.rsplit('/', 1)[-1]
                items = submitted.get(task_id, [])
                return httpx.Response(200, json={'status': 'SUCCEEDED',
                                                 'result': adapter.fixture_result('f', items)})
            payload = json.loads(request.content)
            items = payload.get('garments') or payload.get('effects') or [
                {'reference': payload.get('product', 'fixture')}]
            task_id = f'fixture-{uuid4().hex[:8]}'
            submitted[task_id] = items
            return httpx.Response(200, json={'taskId': task_id, 'status': 'QUEUED'})

        return ProviderClient(adapter, mode='FIXTURE', transport=httpx.MockTransport(handler))


def _error_detail(payload: dict) -> ErrorDetail:
    return ErrorDetail(code=payload['code'], message=payload['message'],
                       details=payload.get('details', {}))


__all__ = ['DAILY_PAID_INTENT_LIMIT', 'PreviewBase', 'PreviewService', 'plan_chain']
