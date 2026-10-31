"""Anchor Fit API: C-owned HTTP delivery with real access/profile behavior.

A-owned operations (catalog, stylist, proposals) are served by lane A services
composed in apps.api.integration behind the frozen contracts. C-owned
operations activate per ticket. Frozen contracts in contracts.runtime are never
modified here.
"""
import os
from collections.abc import Iterator
from typing import Any, Literal
from uuid import UUID, uuid4

import sqlalchemy
from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from apps.api import clock
from apps.api.db import Database
from apps.api.errors import (
    SCOPE_FORBIDDEN,
    STALE_VERSION,
    ApiError,
)
from apps.api.integration import (
    IntegratedCatalog,
    ShareRegistry,
    build_broker,
    lane_api_error,
    require_consent_revision,
)
from apps.api.modules.commerce.models import OrderRow
from apps.api.modules.commerce.ports import DemoPaymentPort
from apps.api.modules.commerce.service import CommerceService, replay, store
from apps.api.modules.merchant_insights.service import InsightsService
from apps.api.modules.shopper_profile.models import WardrobeItem
from apps.api.modules.shopper_profile.service import ProfileService
from apps.api.modules.storage.backend import create_backend
from apps.api.modules.storage.service import StorageService
from apps.api.modules.styling_session.models import StylingSessionRow
from apps.api.modules.styling_session.service import SessionService
from apps.api.modules.task_runtime.models import DurableTaskRow
from apps.api.modules.task_runtime.service import TaskService
from apps.api.modules.tenant_access.models import Account as AccessAccount
from apps.api.modules.tenant_access.models import Actor
from apps.api.modules.tenant_access.service import (
    COOKIE_NAME,
    AccessService,
    Identity,
    demo_mode_enabled,
)
from apps.api.modules.try_on_jobs.orchestration import PreviewService
from apps.api.ratelimit import RateLimiter
from contracts.runtime import models as m
from contracts.runtime.routes import ROUTES
from contracts.runtime.transport import SECURITY_HEADERS, error
from services.catalog.errors import CatalogError
from services.recommendations.errors import RecommendationError
from services.stylist.errors import StylistError
from services.stylist.proposals import ProposalService

LANE_ERRORS = (CatalogError, RecommendationError, StylistError)


class DevLoginRequest(BaseModel):
    """Development login request; never used outside explicitly labelled demo deployments."""

    model_config = ConfigDict(extra='forbid', frozen=True)
    email: str = Field(min_length=5, max_length=320, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    role: str = Field(default='SHOPPER', pattern=r'^(SHOPPER|WAREHOUSE_OPERATOR|MERCHANT_ADMIN|'
                                                r'PLATFORM_OPERATOR|STORE_STYLIST|PARTNER_EDITOR)$')


def create_app(database_url: str | None = None) -> FastAPI:
    database = Database(database_url)
    catalog = IntegratedCatalog()
    access_service = AccessService()
    profile_service = ProfileService(resolve_slot=catalog.slot_for)
    session_service = SessionService(catalog)
    task_service = TaskService()
    payment_port = DemoPaymentPort()
    commerce_service = CommerceService(payment_port, catalog, session_service.assert_editable,
                                       task_service.enqueue_direct)
    storage_service = StorageService(create_backend(), profile_service.consent_snapshot)
    preview_service = PreviewService(session_service.assert_editable, catalog,
                                     profile_service.consent_snapshot,
                                     storage_service.store_render_result, task_service,
                                     storage_service.asset_available)
    broker = build_broker()

    def actor_account(actor_id: str) -> str | None:
        with database.unit_of_work() as session:
            actor = session.get(Actor, actor_id)
            return actor.account_id if actor else None

    shares = ShareRegistry(actor_account)
    proposals = ProposalService(shared=shares)
    proposal_sessions: dict[UUID, UUID] = {}
    # In-process demo evidence for the insights dashboard (mode DEMO, single process).
    stylist_ledger: list[dict[str, Any]] = []
    insights_service = InsightsService()

    def ctx_of(db: Session, identity: Identity) -> m.AccessContext:
        revision = profile_service.latest_revision(db, identity.actor_id)
        return identity.access_context(revision)
    app = FastAPI(title='Anchor Fit API', version='1.0.0', docs_url=None, redoc_url=None,
                  description='C-owned HTTP delivery; live providers stay disabled until '
                              'verified activation.')

    def get_db() -> Iterator[Session]:
        with database.unit_of_work() as session:
            yield session

    def get_identity(request: Request, response: Response,
                     db: Session = Depends(get_db)) -> Identity:
        identity = access_service.resolve(db, request.cookies.get(COOKIE_NAME))
        if identity.set_cookie:
            response.set_cookie(COOKIE_NAME, identity.set_cookie, max_age=86400, path='/',
                                httponly=True, secure=True, samesite='lax')
        profile_service.ensure_actor_consent(db, identity.actor_id)
        return identity

    def account_email(db: Session, identity: Identity) -> tuple[str | None, dict[str, str]]:
        if identity.account_id is None:
            return None, {}
        account = db.get(AccessAccount, identity.account_id)
        if account is None:
            return None, {}
        return account.email, dict(account.preferences or {})

    def get_profile(identity: Identity = Depends(get_identity),
                    db: Session = Depends(get_db)) -> m.ProfileSnapshot:
        _, preferences = account_email(db, identity)
        return profile_service.snapshot(db, identity.actor_id, identity.tenant_id, preferences,
                                        identity.account_id)

    def update_consent(body: m.ConsentUpdate,
                       identity: Identity = Depends(get_identity),
                       db: Session = Depends(get_db)) -> m.ConsentSnapshot:
        return profile_service.update_consent(
            db, identity.actor_id, body.expectedConsentRevision, body.controls.model_dump(),
            list(body.processors), [str(value) for value in body.assetIds], body.adultAttestation)

    def list_wardrobe(cursor: str | None = Query(default=None),
                      limit: int = Query(default=30, ge=1, le=100),
                      identity: Identity = Depends(get_identity),
                      db: Session = Depends(get_db)) -> m.WardrobePage:
        account_id = profile_service.require_account(identity.account_id)
        return profile_service.list_wardrobe(db, account_id, cursor, limit)

    def save_wardrobe(body: m.WardrobeSave,
                      identity: Identity = Depends(get_identity),
                      db: Session = Depends(get_db)) -> m.WardrobeItem:
        account_id = profile_service.require_account(identity.account_id)
        return profile_service.save_wardrobe(db, account_id, body.reference, body.saved,
                                             body.manualOwnedQuantity, body.attributesConfirmed)

    def demo_login(body: DevLoginRequest, response: Response, request: Request,
                   db: Session = Depends(get_db)) -> dict[str, Any]:
        if not demo_mode_enabled():
            raise HTTPException(404)
        identity = access_service.demo_login(db, request.cookies.get(COOKIE_NAME), body.email,
                                             roles=(body.role,))
        if identity.set_cookie:
            response.set_cookie(COOKIE_NAME, identity.set_cookie, max_age=86400, path='/',
                                httponly=True, secure=True, samesite='lax')
        return {'accountId': identity.account_id, 'verified': identity.verified,
                'mode': 'DEMO', 'roles': identity.roles}

    def logout(db: Session = Depends(get_db)) -> dict[str, str]:
        access_service.logout(db, None)
        return {'status': 'ok'}

    def _idempotent(db: Session, identity: Identity, operation: str, key: UUID, body: Any,
                    produce) -> Any:
        cached = replay(db, identity.actor_id, operation, key, body.model_dump())
        if cached is not None:
            return cached
        produced = produce()
        store(db, identity.actor_id, operation, key, body.model_dump(),
              produced.model_dump(mode='json'), 0)
        return produced

    def create_session(body: m.SessionCreate, idempotency_key: UUID = Header(alias='Idempotency-Key'),
                       identity: Identity = Depends(get_identity),
                       db: Session = Depends(get_db)) -> m.SessionSnapshot:
        return _idempotent(db, identity, 'createSession', idempotency_key, body,
                           lambda: session_service.create(db, ctx_of(db, identity), body))

    def get_session(sessionId: UUID, identity: Identity = Depends(get_identity),
                    db: Session = Depends(get_db)) -> m.SessionSnapshot:
        return session_service.snapshot(db, ctx_of(db, identity), sessionId)

    def edit_session(sessionId: UUID, body: m.SessionEdit,
                     identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.SessionSnapshot:
        return session_service.edit(db, ctx_of(db, identity), sessionId, body)

    def claim_session(body: m.ClaimSession,
                      idempotency_key: UUID = Header(alias='Idempotency-Key'),
                      identity: Identity = Depends(get_identity),
                      db: Session = Depends(get_db)) -> m.SessionSnapshot:
        if not identity.verified:
            raise ApiError(403, 'SCOPE_FORBIDDEN', 'Session claims require a verified account.')
        assert identity.account_id is not None
        return session_service.claim(db, ctx_of(db, identity), body, identity.account_id)

    def quote_cart(body: m.CartRequest, idempotency_key: UUID = Header(alias='Idempotency-Key'),
                   identity: Identity = Depends(get_identity),
                   db: Session = Depends(get_db)) -> m.CartQuote:
        if not identity.verified:
            raise ApiError(403, 'SCOPE_FORBIDDEN', 'Cart quotes require a verified account.')
        return _idempotent(db, identity, 'quoteCart', idempotency_key, body,
                           lambda: commerce_service.quote_cart(db, ctx_of(db, identity), body))

    def confirm_checkout(body: m.CheckoutConfirm,
                         idempotency_key: UUID = Header(alias='Idempotency-Key'),
                         identity: Identity = Depends(get_identity),
                         db: Session = Depends(get_db)) -> m.OrderSnapshot:
        if not identity.verified:
            raise ApiError(403, 'SCOPE_FORBIDDEN', 'Checkout requires a verified account.')
        assert identity.account_id is not None
        return _idempotent(db, identity, 'confirmCheckout', idempotency_key, body,
                           lambda: commerce_service.confirm_checkout(db, ctx_of(db, identity), body,
                                                                     identity.account_id or ''))

    def get_order(orderId: UUID, identity: Identity = Depends(get_identity),
                  db: Session = Depends(get_db)) -> m.OrderSnapshot:
        return commerce_service.get_order(db, ctx_of(db, identity), orderId)

    def cancel_order(orderId: UUID, body: m.OrderAction,
                     idempotency_key: UUID = Header(alias='Idempotency-Key'),
                     identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.OrderSnapshot:
        return _idempotent(db, identity, 'cancelOrder', idempotency_key, body,
                           lambda: commerce_service.cancel_order(db, ctx_of(db, identity), orderId,
                                                                 body))

    def request_return(orderId: UUID, body: m.OrderAction,
                       idempotency_key: UUID = Header(alias='Idempotency-Key'),
                       identity: Identity = Depends(get_identity),
                       db: Session = Depends(get_db)) -> m.OrderSnapshot:
        return _idempotent(db, identity, 'requestReturn', idempotency_key, body,
                           lambda: commerce_service.request_return(db, ctx_of(db, identity),
                                                                   orderId, body))

    def advance_fulfilment(orderId: UUID, body: m.FulfilmentAction,
                           idempotency_key: UUID = Header(alias='Idempotency-Key'),
                           identity: Identity = Depends(get_identity),
                           db: Session = Depends(get_db)) -> m.OrderSnapshot:
        return _idempotent(db, identity, 'advanceFulfilment', idempotency_key, body,
                           lambda: commerce_service.advance_fulfilment(db, ctx_of(db, identity),
                                                                       orderId, body))

    def receive_return(orderId: UUID, body: m.OrderAction,
                       idempotency_key: UUID = Header(alias='Idempotency-Key'),
                       identity: Identity = Depends(get_identity),
                       db: Session = Depends(get_db)) -> m.OrderSnapshot:
        return _idempotent(db, identity, 'receiveReturn', idempotency_key, body,
                           lambda: commerce_service.receive_return(db, ctx_of(db, identity),
                                                                   orderId, body))

    def prepare_asset_upload(body: m.AssetUploadRequest,
                             idempotency_key: UUID = Header(alias='Idempotency-Key'),
                             identity: Identity = Depends(get_identity),
                             db: Session = Depends(get_db)) -> m.AssetDescriptor:
        return _idempotent(db, identity, 'prepareAssetUpload', idempotency_key, body,
                           lambda: storage_service.prepare_upload(db, ctx_of(db, identity), body))

    def get_asset(assetId: UUID, identity: Identity = Depends(get_identity),
                  db: Session = Depends(get_db)) -> m.AssetDescriptor:
        return storage_service.get_asset(db, ctx_of(db, identity), str(assetId))

    def delete_asset(assetId: UUID, identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.Ack:
        return storage_service.delete_asset(db, ctx_of(db, identity), str(assetId))

    def save_asset(assetId: UUID, body: m.SaveAsset,
                   idempotency_key: UUID = Header(alias='Idempotency-Key'),
                   identity: Identity = Depends(get_identity),
                   db: Session = Depends(get_db)) -> m.AssetDescriptor:
        return _idempotent(db, identity, 'saveAsset', idempotency_key, body,
                           lambda: storage_service.save_asset(db, ctx_of(db, identity),
                                                              str(assetId), body))

    def list_capabilities(db: Session = Depends(get_db)) -> m.CapabilityPage:
        from apps.api.modules.try_on_jobs.capabilities import capability_page

        return capability_page(db)

    def create_preview_job(body: m.PreviewRequest,
                           idempotency_key: UUID = Header(alias='Idempotency-Key'),
                           identity: Identity = Depends(get_identity),
                           db: Session = Depends(get_db)) -> m.PreviewJob:
        job_id = preview_service.enqueue(db, ctx_of(db, identity), body,
                                         profile_service.consent_snapshot(db, identity.actor_id),
                                         idempotency_key)
        return preview_service.get(db, ctx_of(db, identity), job_id)

    def get_preview_job(jobId: UUID, identity: Identity = Depends(get_identity),
                        db: Session = Depends(get_db)) -> m.PreviewJob:
        return preview_service.get(db, ctx_of(db, identity), jobId)

    def cancel_preview_job(jobId: UUID, identity: Identity = Depends(get_identity),
                           db: Session = Depends(get_db)) -> m.PreviewJob:
        return preview_service.cancel(db, ctx_of(db, identity), jobId)

    # -- lane A surface: catalog, stylist jobs, proposals, staging ------------

    def list_catalog_variants(cursor: str | None = Query(default=None),
                              limit: int = Query(default=30, ge=1, le=100),
                              search: str | None = Query(default=None, min_length=1,
                                                         max_length=200),
                              slot: m.Slot | None = Query(default=None),
                              brandKind: Literal['OWN', 'SPONSOR'] | None = Query(default=None),
                              inStock: bool | None = Query(default=None),
                              identity: Identity = Depends(get_identity),
                              db: Session = Depends(get_db)) -> m.CatalogPage:
        ctx = ctx_of(db, identity)
        query = m.CatalogQuery(search=search, slot=slot, brandKind=brandKind, inStock=inStock)
        try:
            return catalog.list_variants(ctx, cursor, limit, query)
        except LANE_ERRORS as exc:
            raise lane_api_error(exc) from None

    def get_catalog_variant(variantId: str, identity: Identity = Depends(get_identity),
                            db: Session = Depends(get_db)) -> m.CatalogVariant:
        ctx = ctx_of(db, identity)
        try:
            return catalog.variant(ctx, variantId)
        except LANE_ERRORS as exc:
            raise lane_api_error(exc) from None

    def create_stylist_job(body: m.StylistRequest,
                           idempotency_key: UUID = Header(alias='Idempotency-Key'),
                           identity: Identity = Depends(get_identity),
                           db: Session = Depends(get_db)) -> m.JobAccepted:
        ctx = ctx_of(db, identity)
        try:
            session = session_service.snapshot(db, ctx, body.sessionId)
            profile = get_profile(identity, db)
            accepted = broker.submit(ctx, body, session, catalog.full_snapshot(ctx), profile,
                                     idempotency_key=idempotency_key, now=clock.now())
        except LANE_ERRORS as exc:
            raise lane_api_error(exc) from None
        if isinstance(accepted, m.JobAccepted):
            # Fixture mode runs the queued job inline; live deployments drive it
            # from the durable worker instead.
            broker.run(accepted.jobId, now=clock.now())
            job = broker.get(accepted.jobId, ctx)
            stylist_ledger.append({
                'at': clock.now(), 'actorId': ctx.actorId,
                'looks': len(job.result.looks)
                if isinstance(job.result, m.LooksResult) else 0})
        return m.JobAccepted(jobId=accepted.jobId,
                             statusUrl=f'/api/stylist-jobs/{accepted.jobId}',
                             status='QUEUED', sessionVersion=body.expectedSessionVersion)

    def get_stylist_job(jobId: UUID, identity: Identity = Depends(get_identity),
                        db: Session = Depends(get_db)) -> m.StylistJob:
        ctx = ctx_of(db, identity)
        try:
            job = broker.get(jobId, ctx)
        except StylistError as exc:
            raise lane_api_error(exc) from None
        try:
            session = session_service.snapshot(db, ctx, job.sessionId)
        except ApiError:
            return job
        return broker.get(jobId, ctx, current_session_version=session.sessionVersion)

    def cancel_stylist_job(jobId: UUID, identity: Identity = Depends(get_identity),
                           db: Session = Depends(get_db)) -> m.StylistJob:
        try:
            return broker.cancel(jobId, ctx_of(db, identity))
        except StylistError as exc:
            raise lane_api_error(exc) from None

    def apply_look(sessionId: UUID, body: m.ApplyLook,
                   identity: Identity = Depends(get_identity),
                   db: Session = Depends(get_db)) -> m.SessionSnapshot:
        ctx = ctx_of(db, identity)
        try:
            job = broker.get(body.jobId, ctx)
        except StylistError as exc:
            raise lane_api_error(exc) from None
        if job.sessionId != sessionId or job.status != 'SUCCEEDED' \
                or not isinstance(job.result, m.LooksResult):
            raise ApiError(404, 'NOT_FOUND', 'No completed look exists for this job.')
        look = next((item for item in job.result.looks if item.lookId == body.lookId), None)
        if look is None:
            raise ApiError(404, 'NOT_FOUND', 'Unknown look for this job.')
        return session_service.apply(db, ctx, sessionId, body.expectedSessionVersion,
                                     list(look.items), [], None)

    def create_share(body: m.ShareCreate,
                     idempotency_key: UUID = Header(alias='Idempotency-Key'),
                     identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.ShareSnapshot:
        if not identity.verified:
            raise ApiError(403, SCOPE_FORBIDDEN, 'Sharing requires a verified account.')
        ctx = ctx_of(db, identity)
        session = session_service.snapshot(db, ctx, body.sessionId)
        if body.expectedSessionVersion != session.sessionVersion:
            raise ApiError(409, STALE_VERSION, 'Session changed; refresh and retry.')
        require_consent_revision(session, body.expectedConsentRevision)
        if db.get(AccessAccount, body.recipientAccountId) is None:
            raise ApiError(404, 'NOT_FOUND', 'Unknown recipient account.')
        return shares.create(ctx, body, session)

    def revoke_share(shareId: UUID, identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.ShareSnapshot:
        return shares.revoke(ctx_of(db, identity), shareId)

    def create_proposal(body: m.ProposalCreate,
                        idempotency_key: UUID = Header(alias='Idempotency-Key'),
                        identity: Identity = Depends(get_identity),
                        db: Session = Depends(get_db)) -> m.ProposalSnapshot:
        ctx = ctx_of(db, identity)
        try:
            session = session_service.read_shared(db, ctx, body.sessionId)
            proposal = proposals.create(ctx, body, session, catalog.full_snapshot(ctx))
        except LANE_ERRORS as exc:
            raise lane_api_error(exc) from None
        proposal_sessions[proposal.proposalId] = body.sessionId
        return proposal

    def get_proposal(proposalId: UUID, identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.ProposalSnapshot:
        ctx = ctx_of(db, identity)
        session_id = proposal_sessions.get(proposalId)
        if session_id is None:
            raise ApiError(404, 'NOT_FOUND', 'Unknown or non-owned resource.')
        try:
            session = session_service.read_shared(db, ctx, session_id)
            return proposals.get(ctx, proposalId, session)
        except StylistError as exc:
            raise lane_api_error(exc) from None

    def apply_proposal(proposalId: UUID, body: m.ProposalApply,
                       idempotency_key: UUID = Header(alias='Idempotency-Key'),
                       identity: Identity = Depends(get_identity),
                       db: Session = Depends(get_db)) -> m.SessionSnapshot:
        ctx = ctx_of(db, identity)
        session_id = proposal_sessions.get(proposalId)
        if session_id is None:
            raise ApiError(404, 'NOT_FOUND', 'Unknown or non-owned resource.')
        try:
            session = session_service.snapshot(db, ctx, session_id)
            proposal = proposals.get(ctx, proposalId, session)
            selections = proposals.validate_application(proposal, session, body,
                                                        catalog.full_snapshot(ctx))
            updated = session_service.apply(db, ctx, session_id, body.expectedSessionVersion,
                                            selections, list(body.approvedExceptionIds),
                                            proposal.brief)
        except LANE_ERRORS as exc:
            raise lane_api_error(exc) from None
        proposals.record_outcome(proposalId, accepted=True)
        return updated

    def request_proposal_refresh(proposalId: UUID, body: m.ProposalRefresh,
                                 idempotency_key: UUID = Header(alias='Idempotency-Key'),
                                 identity: Identity = Depends(get_identity),
                                 db: Session = Depends(get_db)) -> m.Ack:
        ctx = ctx_of(db, identity)
        session_id = proposal_sessions.get(proposalId)
        if session_id is None:
            raise ApiError(404, 'NOT_FOUND', 'Unknown or non-owned resource.')
        try:
            session = session_service.snapshot(db, ctx, session_id)
            return proposals.refresh(ctx, proposalId, body, session)
        except StylistError as exc:
            raise lane_api_error(exc) from None

    def require_role(ctx: m.AccessContext, *roles: str) -> None:
        if not set(roles) & set(ctx.roles):
            raise ApiError(403, SCOPE_FORBIDDEN, 'This action needs merchant scope.')

    def stage_catalog(body: m.CatalogBatch,
                      idempotency_key: UUID = Header(alias='Idempotency-Key'),
                      identity: Identity = Depends(get_identity),
                      db: Session = Depends(get_db)) -> m.CatalogStage:
        ctx = ctx_of(db, identity)
        require_role(ctx, 'MERCHANT_ADMIN', 'PLATFORM_OPERATOR')
        if any(variant.tenantId != ctx.tenantId for variant in body.variants):
            raise ApiError(422, 'VALIDATION_ERROR',
                           'Staged variants must belong to the merchant tenant.')
        return catalog.stage(ctx, body)

    def publish_catalog(stageId: UUID, body: m.PublishStage,
                        idempotency_key: UUID = Header(alias='Idempotency-Key'),
                        identity: Identity = Depends(get_identity),
                        db: Session = Depends(get_db)) -> m.Ack:
        ctx = ctx_of(db, identity)
        require_role(ctx, 'MERCHANT_ADMIN', 'PLATFORM_OPERATOR')
        return catalog.publish(ctx, stageId, body)

    def get_insights(cursor: str | None = Query(default=None),
                     limit: int = Query(default=100, ge=1, le=100),
                     identity: Identity = Depends(get_identity),
                     db: Session = Depends(get_db)) -> m.Insights:
        ctx = ctx_of(db, identity)
        require_role(ctx, 'MERCHANT_ADMIN', 'PLATFORM_OPERATOR')

        def counts(start, end):
            def windowed(rows, at_index, actor_index):
                current = [(clock.as_utc(row[at_index]), row[actor_index]) for row in rows]
                inside = [(at, actor) for at, actor in current if start <= at <= end]
                return (len(inside), len({actor for _, actor in inside}))

            sessions = db.execute(select(StylingSessionRow.created_at,
                                         StylingSessionRow.owner_actor_id)).all()
            saves = db.execute(select(WardrobeItem.updated_at, WardrobeItem.account_id)
                               .where(WardrobeItem.saved.is_(True))).all()
            orders = db.execute(select(OrderRow.created_at, OrderRow.account_id)).all()
            previews = db.execute(select(DurableTaskRow.created_at, DurableTaskRow.actor_id)
                                  .where(DurableTaskRow.operation == 'PREVIEW')).all()
            requests = [entry for entry in stylist_ledger if start <= clock.as_utc(entry['at']) <= end]
            looks = sum(entry['looks'] for entry in requests)
            look_actors = {entry['actorId'] for entry in requests if entry['looks']}
            return {
                'qualifiedSessions': windowed(sessions, 0, 1),
                'wardrobeSaves': windowed(saves, 0, 1),
                'orders': windowed(orders, 0, 1),
                'previewJobs': windowed(previews, 0, 1),
                'stylistRequests': (len(requests), len({entry['actorId'] for entry in requests})),
                'generatedLooks': (looks, len(look_actors)),
            }

        return insights_service.page(counts)

    def delete_account(identity: Identity = Depends(get_identity),
                       db: Session = Depends(get_db)) -> m.Ack:
        if not identity.verified or identity.account_id is None:
            raise ApiError(403, SCOPE_FORBIDDEN,
                           'Account deletion requires a verified account.')
        try:
            actor_ids = access_service.delete_account(db, identity.account_id)
        except LookupError:
            raise ApiError(404, 'NOT_FOUND', 'Unknown or non-owned resource.') from None
        now = clock.now()
        task_service.cancel_for_actors(db, actor_ids, now)
        storage_service.revoke_for_actors(db, actor_ids)
        session_ids = [UUID(row) for row in db.scalars(select(StylingSessionRow.session_id)
                                                       .where(StylingSessionRow.owner_actor_id
                                                              .in_(actor_ids)))]
        shares.revoke_all_for(identity.account_id, session_ids)
        return m.Ack(requestId=uuid4(), status='ACCEPTED')

    HANDLERS: dict[str, Any] = {
        'getProfile': get_profile,
        'updateConsent': update_consent,
        'listWardrobe': list_wardrobe,
        'saveWardrobeItem': save_wardrobe,
        'createSession': create_session,
        'getSession': get_session,
        'editSession': edit_session,
        'claimSession': claim_session,
        'applyLook': apply_look,
        'createStylistJob': create_stylist_job,
        'getStylistJob': get_stylist_job,
        'cancelStylistJob': cancel_stylist_job,
        'listVariants': list_catalog_variants,
        'getVariant': get_catalog_variant,
        'stageCatalog': stage_catalog,
        'publishCatalog': publish_catalog,
        'getInsights': get_insights,
        'deleteAccount': delete_account,
        'createShare': create_share,
        'revokeShare': revoke_share,
        'createProposal': create_proposal,
        'getProposal': get_proposal,
        'applyProposal': apply_proposal,
        'requestProposalRefresh': request_proposal_refresh,
        'quoteCart': quote_cart,
        'confirmCheckout': confirm_checkout,
        'getOrder': get_order,
        'cancelOrder': cancel_order,
        'requestReturn': request_return,
        'advanceFulfilment': advance_fulfilment,
        'receiveReturn': receive_return,
        'prepareAssetUpload': prepare_asset_upload,
        'getAsset': get_asset,
        'deleteAsset': delete_asset,
        'saveAsset': save_asset,
        'createPreviewJob': create_preview_job,
        'getPreviewJob': get_preview_job,
        'cancelPreviewJob': cancel_preview_job,
        'listCapabilities': list_capabilities,
    }

    limiter = RateLimiter()

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    @app.middleware('http')
    async def rate_limit(request: Request, call_next):
        # Pre-auth endpoints have no stable cookie, so limit them by client host.
        pre_auth = request.url.path.endswith('/auth/demo-login')
        fingerprint = (request.client.host if request.client else 'anonymous') if pre_auth \
            else (request.cookies.get(COOKIE_NAME)
                  or (request.client.host if request.client else 'anonymous'))
        if request.method in ('POST', 'PUT', 'DELETE'):
            try:
                limiter.check(fingerprint, request.url.path)
            except ApiError as error:
                # Middleware sits outside the exception handlers; return the envelope here.
                body = m.ErrorEnvelope(error=m.ErrorDetail(code=error.code, message=error.message),
                                       requestId=uuid4())
                return JSONResponse(body.model_dump(mode='json'), status_code=error.status,
                                    headers={**SECURITY_HEADERS, **(error.headers or {})})
        return await call_next(request)

    @app.get('/readyz', operation_id='ready')
    def ready() -> dict[str, object]:
        connected = True
        try:
            with database.unit_of_work() as db:
                db.execute(sqlalchemy.text('SELECT 1'))
        except Exception:
            connected = False
        return {'ready': connected, 'database': connected, 'liveProvidersEnabled': False}

    @app.exception_handler(ApiError)
    async def domain_error(request: Request, exc: ApiError) -> JSONResponse:
        body = m.ErrorEnvelope(error=m.ErrorDetail(code=exc.code, message=exc.message),
                               requestId=uuid4())
        headers = {**SECURITY_HEADERS, **(exc.headers or {})}
        return JSONResponse(body.model_dump(mode='json'), status_code=exc.status, headers=headers)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> Any:
        return error(500, 'INTERNAL_ERROR', 'The request could not be completed.')

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> Any:
        return error(422, 'VALIDATION_ERROR', 'Request does not match the frozen contract.')

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> Any:
        return error(exc.status_code, 'NOT_FOUND' if exc.status_code == 404 else 'HTTP_ERROR',
                     'The request could not be completed.')

    @app.get('/healthz', response_model=m.Health, operation_id='health')
    def health() -> m.Health:
        return m.Health()

    for route in ROUTES:
        responses: dict[int | str, dict[str, Any]] = {
            code: {'model': m.ErrorEnvelope, 'description': description}
            for code, description in [(401, 'Authentication required'), (403, 'Known scope revoked'),
                (404, 'Unknown or non-owned resource'), (409, 'Version or idempotency conflict'),
                (422, 'Invalid request'), (429, 'Quota; Retry-After header'),
                (500, 'Sanitized internal error'), (501, 'Operation not yet implemented')]
        }
        responses[429]['headers'] = {'Retry-After': {'schema': {'type': 'integer', 'minimum': 1}}}
        handler = HANDLERS.get(route.operation)
        if handler is None:
            from contracts.runtime.transport import endpoint as disabled_endpoint

            handler = disabled_endpoint(route)
        app.add_api_route(route.path, handler, methods=[route.method],
                          operation_id=route.operation, response_model=route.response,
                          status_code=route.status, responses=responses,
                          tags=[route.owner], openapi_extra={
                              'security': [{'sessionCookie': []}],
                              'x-domain-owner': route.owner, 'x-http-owner': 'C',
                              'x-required-scope': route.scope,
                              'x-idempotency-required': route.idempotent,
                              'x-implementation-status':
                                  'IMPLEMENTED' if route.operation in HANDLERS else 'FOUNDATION_ONLY',
                          })

    app.add_api_route('/api/auth/demo-login', demo_login, methods=['POST'], operation_id='demoLogin',
                      status_code=200, tags=['C'], include_in_schema=bool(demo_mode_enabled()),
                      response_model=None, openapi_extra={
                          'x-domain-owner': 'C', 'x-implementation-status': 'DEMO_ONLY',
                          'summary': 'Labelled development login for isolated demo deployments'})
    app.state.database = database
    app.state.commerce_service = commerce_service
    app.state.session_service = session_service
    app.state.profile_service = profile_service
    app.state.task_service = task_service
    app.state.storage_service = storage_service
    app.state.preview_service = preview_service
    app.state.catalog = catalog
    app.state.stylist_broker = broker
    app.state.shares = shares
    app.state.proposals = proposals
    return app


if os.getenv('LIVE_PROVIDERS_ENABLED', 'false').lower() != 'false':
    raise RuntimeError('Live providers cannot be enabled without verified activation evidence.')

app = create_app()
