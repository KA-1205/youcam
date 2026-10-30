"""Disabled API surface. Test fixture routes are a separate app, never auto-enabled."""
import inspect
import re
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .models import ErrorDetail, ErrorEnvelope, Health
from .routes import ROUTES, Route

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
}


def error(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorEnvelope(error=ErrorDetail(code=code, message=message), requestId=uuid4())
    return JSONResponse(body.model_dump(mode='json'), status_code=status, headers=SECURITY_HEADERS)


def endpoint(route: Route):
    async def disabled(**kwargs: Any) -> JSONResponse:
        return error(501, 'NOT_IMPLEMENTED', 'This operation is not implemented in the foundation.')

    params = []
    for name in re.findall(r'\{(\w+)\}', route.path):
        params.append(inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY,
                      annotation=str if name == 'variantId' else UUID))
    if route.request:
        params.append(inspect.Parameter('body', inspect.Parameter.KEYWORD_ONLY,
                                        annotation=route.request))
    if route.idempotent:
        params.append(inspect.Parameter('idempotency_key', inspect.Parameter.KEYWORD_ONLY,
                                        annotation=UUID, default=Header(alias='Idempotency-Key')))
    if route.paginated:
        params.extend([
            inspect.Parameter('cursor', inspect.Parameter.KEYWORD_ONLY, annotation=str | None,
                              default=Query(default=None)),
            inspect.Parameter('limit', inspect.Parameter.KEYWORD_ONLY, annotation=int,
                              default=Query(default=30, ge=1, le=100)),
        ])
    disabled.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    return disabled


def create_app() -> FastAPI:
    app = FastAPI(title='Anchor Fit frozen API', version='1.0.0', docs_url=None, redoc_url=None,
                  description='Foundation only. Product routes return 501. Fixture transport is separate.')

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return error(500, 'INTERNAL_ERROR', 'The request could not be completed.')

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(422, 'VALIDATION_ERROR', 'Request does not match the frozen contract.')

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error(exc.status_code, 'NOT_FOUND' if exc.status_code == 404 else 'HTTP_ERROR',
                     'The request could not be completed.')

    @app.get('/healthz', response_model=Health, operation_id='health')
    def health() -> Health:
        return Health()

    for route in ROUTES:
        responses: dict[int | str, dict[str, Any]] = {
            code: {'model': ErrorEnvelope, 'description': description}
            for code, description in [(401, 'Authentication required'), (403, 'Known scope revoked'),
                (404, 'Unknown or non-owned resource'), (409, 'Version or idempotency conflict'),
                (422, 'Invalid request'), (429, 'Quota; Retry-After header'),
                (500, 'Sanitized internal error'), (501, 'Foundation operation unavailable')]
        }
        responses[429]['headers'] = {'Retry-After': {'schema': {'type': 'integer', 'minimum': 1}}}
        if route.operation == 'createStylistJob':
            from .models import StylistJob
            responses[200] = {'model': StylistJob, 'description': 'Replay of terminal job'}
        app.add_api_route(route.path, endpoint(route), methods=[route.method],
                          operation_id=route.operation, response_model=route.response,
                          status_code=route.status, responses=responses,
                          tags=[route.owner], openapi_extra={
                              'security': [{'sessionCookie': []}],
                              'x-domain-owner': route.owner, 'x-http-owner': 'C',
                              'x-required-scope': route.scope,
                              'x-idempotency-required': route.idempotent,
                              'x-implementation-status': 'FOUNDATION_ONLY',
                          })
    original = app.openapi

    def schema() -> dict[str, Any]:
        document = original()
        document['components']['securitySchemes'] = {
            'sessionCookie': {'type': 'apiKey', 'in': 'cookie', 'name': 'anchor_session'}}
        return document

    app.openapi = schema  # type: ignore[method-assign]
    return app
