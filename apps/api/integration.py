"""Integration composition: lane A services behind the frozen contracts.

Assembly point only — no domain logic lives here. The catalog store is seeded
from the read-only demo fixture (every row synthetic); the stylist runs through
lane A's rule-based engine because no AI model is configured in this
deployment, and share state is in-process per the seven-day share contract.
"""
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from apps.api import clock
from apps.api.errors import (
    CONSENT_REQUIRED,
    IDEMPOTENCY_CONFLICT,
    SCOPE_FORBIDDEN,
    STALE_VERSION,
    ApiError,
)
from contracts.runtime import models as m
from contracts.runtime.models import AccessContext, CatalogPage, CatalogSnapshot
from services.catalog.demo import load_demo_catalog
from services.catalog.errors import CatalogError
from services.catalog.staging import CatalogStaging
from services.catalog.store import CatalogStore
from services.recommendations.candidates import build_candidates
from services.recommendations.looks import generate_looks
from services.stylist.broker import ModelUnavailable, StylistBroker

SEED_PATH = Path('reference/Anchor-Fit-Final-v3.3/demo-catalog.json')
SHARE_TTL = timedelta(days=7)

_LANE_ERROR_MAP: dict[str, tuple[int, str]] = {
    'NOT_FOUND': (404, 'NOT_FOUND'),
    'STALE_VERSION': (409, STALE_VERSION),
    'STALE_SESSION': (409, STALE_VERSION),
    'PERMISSION_DENIED': (403, SCOPE_FORBIDDEN),
    'IDEMPOTENCY_CONFLICT': (409, IDEMPOTENCY_CONFLICT),
}


def lane_api_error(exc: Exception) -> ApiError:
    """Map a lane A error carrying a stable code onto the frozen envelope codes."""
    code = getattr(exc, 'code', None)
    message = getattr(exc, 'message', None) or 'The request could not be completed.'
    status, envelope_code = _LANE_ERROR_MAP.get(str(code), (422, 'VALIDATION_ERROR'))
    return ApiError(status, envelope_code, message)


class IntegratedCatalog:
    """CatalogStore (lane A) behind the seams the API composition consumes.

    Port reads go through the store; the commerce/profile seams keep the seed
    values so demo pricing stays deterministic. Publication bumps the store
    version, which fails stale cursors closed.
    """

    def __init__(self, seed_path: Path | None = None) -> None:
        payload = json.loads((seed_path or SEED_PATH).read_text(encoding='utf-8'))
        variants, self._owned = load_demo_catalog(payload, now=clock.now())
        self._seed = {row['variantId']: row for row in payload.get('variants', [])}
        self._tenants = sorted({variant.tenantId for variant in variants})
        self.store = CatalogStore(variants, now=clock.now)
        self.staging = CatalogStaging(self.store)

    def list_variants(self, ctx: AccessContext, cursor: str | None, limit: int,
                      query: m.CatalogQuery | None = None) -> CatalogPage:
        return self.store.list_variants(ctx, cursor, limit, query)

    def variant(self, ctx: AccessContext, variant_id: str) -> m.CatalogVariant:
        return self.store.variant(ctx, variant_id)

    def snapshot(self, ctx: AccessContext, variant_ids: list[str]) -> CatalogSnapshot:
        present = [variant_id for variant_id in dict.fromkeys(variant_ids)
                   if (found := self.store.find(ctx.tenantId, variant_id)) is not None
                   and found.published]
        return self.store.snapshot(ctx, present)

    def full_snapshot(self, ctx: AccessContext) -> CatalogSnapshot:
        page = self.store.list_variants(ctx, None, 10_000)
        return self.snapshot(ctx, [variant.variantId for variant in page.items])

    def slot_for(self, variant_id: str) -> str | None:
        for tenant_id in self._tenants:
            found = self.store.find(tenant_id, variant_id)
            if found is not None:
                return found.slot
        return None

    def seed_stock(self) -> dict[str, int | None]:
        return {variant_id: row.get('stock') for variant_id, row in self._seed.items()}

    def price_for(self, variant_id: str) -> tuple[int | None, str]:
        row = self._seed.get(variant_id)
        if row is None:
            return None, 'INR'
        return row.get('priceMinor'), row.get('currency', 'INR')

    def stage(self, ctx: AccessContext, batch: m.CatalogBatch) -> m.CatalogStage:
        try:
            return self.staging.ingest_json(batch)
        except CatalogError as exc:
            raise lane_api_error(exc) from None

    def publish(self, ctx: AccessContext, stage_id: UUID, body: m.PublishStage) -> m.Ack:
        try:
            return self.staging.publish(stage_id, body)
        except CatalogError as exc:
            raise lane_api_error(exc) from None


class UnavailableModelAdapter:
    """No AI model is configured; the broker must use its labelled fallback."""

    def complete(self, system: str, payload: dict[str, Any], *,
                 timeout_seconds: float) -> dict[str, Any]:
        raise ModelUnavailable()


class RecommendationFallback:
    """Lane A's deterministic rule-based look engine as the labelled fallback."""

    def propose(self, ctx: AccessContext, request: m.StylistRequest,
                session: m.SessionSnapshot, catalog: CatalogSnapshot,
                profile: m.ProfileSnapshot) -> m.StylistResult:
        candidates = build_candidates(catalog, session, profile, now=clock.now())
        return generate_looks(candidates, catalog, session_id=str(session.sessionId))


def build_broker() -> StylistBroker:
    return StylistBroker(adapter=UnavailableModelAdapter(), fallback=RecommendationFallback())


class ShareRegistry:
    """In-process share state for the seven-day named-recipient share contract.

    Shares are created by the session owner, revocable immediately, and gate
    the stylist's shared-session reads and proposal writes.
    """

    def __init__(self, actor_account: Callable[[str], str | None]) -> None:
        self._shares: dict[UUID, dict[str, Any]] = {}
        self._actor_account = actor_account

    def create(self, ctx: AccessContext, body: m.ShareCreate,
               session: m.SessionSnapshot) -> m.ShareSnapshot:
        share_id = uuid4()
        self._shares[share_id] = {
            'sessionId': body.sessionId, 'tenantId': session.tenantId,
            'recipientAccountId': body.recipientAccountId,
            'includedAssetIds': list(body.includedAssetIds),
            'expiresAt': clock.now() + SHARE_TTL, 'revoked': False,
        }
        return m.ShareSnapshot(shareId=share_id, sessionId=body.sessionId,
                               recipientAccountId=body.recipientAccountId,
                               expiresAt=self._shares[share_id]['expiresAt'],
                               revoked=False,
                               includedAssetIds=list(body.includedAssetIds))

    def revoke(self, ctx: AccessContext, share_id: UUID) -> m.ShareSnapshot:
        record = self._shares.get(share_id)
        if record is None or record['tenantId'] != ctx.tenantId:
            raise ApiError(404, 'NOT_FOUND', 'Unknown or non-owned resource.')
        record['revoked'] = True
        return m.ShareSnapshot(shareId=share_id, sessionId=record['sessionId'],
                               recipientAccountId=record['recipientAccountId'],
                               expiresAt=record['expiresAt'], revoked=True,
                               includedAssetIds=list(record['includedAssetIds']))

    def is_shared_with(self, session_id: UUID, tenant_id: str, actor_id: str) -> bool:
        account_id = self._actor_account(actor_id)
        if account_id is None:
            return False
        now = clock.now()
        return any(record['sessionId'] == session_id and record['tenantId'] == tenant_id
                   and record['recipientAccountId'] == account_id
                   and not record['revoked'] and record['expiresAt'] > now
                   for record in self._shares.values())


def require_consent_revision(session: m.SessionSnapshot, expected: int) -> None:
    if expected != session.consentRevision:
        raise ApiError(409, CONSENT_REQUIRED,
                       'Consent changed; review the current controls and retry.')
