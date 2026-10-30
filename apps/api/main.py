"""Anchor Fit API: C-owned HTTP delivery with real access/profile behavior.

A-owned operations (catalog, stylist, proposals) remain foundation 501s until
lane A is integrated; C-owned operations activate per ticket. Frozen contracts
in contracts.runtime are never modified here.
"""
import os
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from apps.api.db import Database
from apps.api.demo_catalog import FixtureCatalog
from apps.api.errors import ApiError
from apps.api.modules.commerce.ports import DemoPaymentPort
from apps.api.modules.commerce.service import CommerceService, replay, store
from apps.api.modules.shopper_profile.service import ProfileService
from apps.api.modules.styling_session.service import SessionService
from apps.api.modules.task_runtime.service import TaskService
from apps.api.modules.tenant_access.models import Account as AccessAccount
from apps.api.modules.tenant_access.service import (
    COOKIE_NAME,
    AccessService,
    Identity,
    demo_mode_enabled,
)
from contracts.runtime import models as m
from contracts.runtime.routes import ROUTES
from contracts.runtime.transport import SECURITY_HEADERS, error


class DevLoginRequest(BaseModel):
    """Development login request; never used outside explicitly labelled demo deployments."""

    model_config = ConfigDict(extra='forbid', frozen=True)
    email: str = Field(min_length=5, max_length=320, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    role: str = Field(default='SHOPPER', pattern=r'^(SHOPPER|WAREHOUSE_OPERATOR|MERCHANT_ADMIN|'
                                                r'PLATFORM_OPERATOR|STORE_STYLIST|PARTNER_EDITOR)$')


def create_app(database_url: str | None = None) -> FastAPI:
    database = Database(database_url)
    catalog = FixtureCatalog()
    access_service = AccessService()
    profile_service = ProfileService(resolve_slot=catalog.slot_for)
    session_service = SessionService(catalog)
    task_service = TaskService()
    payment_port = DemoPaymentPort()
    commerce_service = CommerceService(payment_port, catalog, session_service.assert_editable,
                                       task_service.enqueue_direct)

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

    HANDLERS: dict[str, Any] = {
        'getProfile': get_profile,
        'updateConsent': update_consent,
        'listWardrobe': list_wardrobe,
        'saveWardrobeItem': save_wardrobe,
        'createSession': create_session,
        'getSession': get_session,
        'editSession': edit_session,
        'claimSession': claim_session,
        'quoteCart': quote_cart,
        'confirmCheckout': confirm_checkout,
        'getOrder': get_order,
        'cancelOrder': cancel_order,
        'requestReturn': request_return,
        'advanceFulfilment': advance_fulfilment,
        'receiveReturn': receive_return,
    }

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

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
    return app


if os.getenv('LIVE_PROVIDERS_ENABLED', 'false').lower() != 'false':
    raise RuntimeError('Live providers cannot be enabled without verified activation evidence.')

app = create_app()
