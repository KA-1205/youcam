"""Tenant-aware catalog read models behind the frozen CatalogPort.

Listing and snapshots are deterministic: one immutable ordering, one cursor
alphabet. Price/stock entries expire after FRESHNESS and refresh on read the
way the demo simulator does; refreshes bump the catalog version so stale
cursors fail closed instead of silently paginating mixed generations.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone

from contracts.runtime.models import (
    AccessContext,
    CatalogPage,
    CatalogQuery,
    CatalogSnapshot,
    CatalogVariant,
)

from .errors import InvalidRequestError, NotFoundError, StaleCatalogError

FRESHNESS = timedelta(minutes=15)
OVERRIDABLE_FIELDS = frozenset({'brandName', 'options', 'attributes', 'imageId',
                                'previewStatus'})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CatalogStore:
    """In-memory catalog for one deployment; lane C persists this in its own schema."""

    def __init__(self, variants: Iterable[CatalogVariant], *,
                 now: Callable[[], datetime] | None = None) -> None:
        self._now = now or _utcnow
        self._variants: dict[tuple[str, str], CatalogVariant] = {}
        for variant in variants:
            self._variants[(variant.tenantId, variant.variantId)] = variant
        self._overrides: dict[tuple[str, str], dict[str, object]] = {}
        self._version = 1
        self._refresh_expired()

    # -- reads ---------------------------------------------------------------
    def list_variants(self, ctx: AccessContext, cursor: str | None, limit: int,
                      query: CatalogQuery | None = None) -> CatalogPage:
        self._refresh_expired()
        rows = sorted(self._published(ctx.tenantId), key=lambda v: (v.slot, v.variantId))
        rows = [v for v in rows if _matches(v, query)]
        offset = self._offset(cursor)
        window = rows[offset:offset + limit]
        following = offset + limit
        next_cursor = f'v{self._version}:{following}' if following < len(rows) else None
        return CatalogPage(items=window, nextCursor=next_cursor,
                           catalogVersion=f'catalog-v{self._version}')

    def variant(self, ctx: AccessContext, variant_id: str) -> CatalogVariant:
        self._refresh_expired()
        found = self._variants.get((ctx.tenantId, variant_id))
        if found is None or not found.published:
            raise NotFoundError()
        return found

    def find(self, tenant_id: str, variant_id: str) -> CatalogVariant | None:
        """Return a variant in any publication state, without freshness refresh."""
        return self._variants.get((tenant_id, variant_id))

    def observation(self) -> tuple[datetime, datetime]:
        """Current observation window (checkedAt, expiresAt) for incoming data."""
        now = self._now()
        return now, now + FRESHNESS

    def snapshot(self, ctx: AccessContext, variant_ids: list[str]) -> CatalogSnapshot:
        self._refresh_expired()
        unique: list[str] = []
        for variant_id in variant_ids:
            if variant_id not in unique:
                unique.append(variant_id)
        variants = [self.variant(ctx, variant_id) for variant_id in unique]
        return CatalogSnapshot(
            tenantId=ctx.tenantId,
            catalogVersion=f'catalog-v{self._version}',
            variants=variants,
            evidence={v.variantId: _evidence(v) for v in variants},
        )

    @property
    def version(self) -> int:
        return self._version

    # -- merchant overrides and publication ----------------------------------
    def set_override(self, tenant_id: str, variant_id: str, fields: dict[str, object]) -> None:
        """Record merchant-owned fields; source syncs may never overwrite them."""
        unknown = set(fields) - OVERRIDABLE_FIELDS
        if unknown:
            raise InvalidRequestError(
                f'Fields cannot be overridden: {", ".join(sorted(unknown))}.')
        key = (tenant_id, variant_id)
        merged = {**self._overrides.get(key, {}), **fields}
        self._overrides[key] = merged

    def apply_variants(self, variants: list[CatalogVariant]) -> None:
        """Apply an approved publication; overrides take precedence over source data."""
        for variant in variants:
            overrides = self._overrides.get((variant.tenantId, variant.variantId), {})
            if overrides:
                variant = variant.model_copy(update=dict(overrides))
            self._variants[(variant.tenantId, variant.variantId)] = variant
        self._version += 1

    # -- freshness -----------------------------------------------------------
    def _refresh_expired(self) -> None:
        now = self._now()
        stale = [(key, v) for key, v in self._variants.items() if v.expiresAt <= now]
        if not stale:
            return
        for key, variant in stale:
            # Demo simulator refresh: same source values, new observation time.
            self._variants[key] = variant.model_copy(
                update={'checkedAt': now, 'expiresAt': now + FRESHNESS})
        self._version += 1

    def _published(self, tenant_id: str) -> list[CatalogVariant]:
        return [v for v in self._variants.values() if v.tenantId == tenant_id and v.published]

    def _offset(self, cursor: str | None) -> int:
        if cursor is None:
            return 0
        prefix = f'v{self._version}:'
        if not cursor.startswith(prefix):
            raise StaleCatalogError()
        tail = cursor[len(prefix):]
        if not tail.isdigit():
            raise InvalidRequestError('Malformed pagination cursor.')
        return int(tail)


def _matches(variant: CatalogVariant, query: CatalogQuery | None) -> bool:
    if query is None:
        return True
    if query.slot is not None and variant.slot != query.slot:
        return False
    if query.brandKind is not None and variant.brandKind != query.brandKind:
        return False
    if query.inStock is True and not (variant.stock is not None and variant.stock > 0):
        return False
    if query.inStock is False and variant.stock != 0:
        return False
    if query.search is not None:
        needle = query.search.casefold()
        haystack = ' '.join([variant.brandName, variant.productId, variant.variantId,
                             *variant.options.values(),
                             *(a for a in variant.attributes.values() if a)])
        if needle not in haystack.casefold():
            return False
    return True


def _evidence(variant: CatalogVariant) -> str:
    price = 'unknown price' if variant.priceMinor is None else f'{variant.priceMinor} minor units'
    stock = 'unknown stock' if variant.stock is None else f'stock {variant.stock}'
    checked = variant.checkedAt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return f'Published listing; {price}, {stock} as of {checked}'
