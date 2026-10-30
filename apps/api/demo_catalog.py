"""Fixture catalog adapter implementing the frozen CatalogPort.

Synthetic seed data from the protected demo-catalog fixture; explicitly labelled
FIXTURE mode, never presented as live provider or live warehouse behavior. The
fixture is read-only; stock freshness is simulated on read.
"""
import json
from pathlib import Path

from apps.api import clock
from contracts.runtime.models import (
    AccessContext,
    CatalogPage,
    CatalogQuery,
    CatalogSnapshot,
    CatalogVariant,
)

FRESHNESS_WINDOW = 900  # catalog price/stock expires after 15 minutes without refresh
CATALOG_VERSION = 'demo-catalog-fixture-1'


class FixtureCatalog:
    def __init__(self, seed_path: str | None = None) -> None:
        path = seed_path or Path('reference/Anchor-Fit-Final-v3.3/demo-catalog.json')
        seed = json.loads(Path(path).read_text())
        self._variants = {variant['variantId']: variant for variant in seed['variants']}
        self._owned = seed.get('ownedItems', [])

    def _to_dto(self, tenant_id: str, variant: dict) -> CatalogVariant:
        checked_at = clock.now().replace(microsecond=0)
        age = int(variant.get('stockAgeSeconds') or 0)
        import datetime

        checked_at = checked_at - datetime.timedelta(seconds=age)
        return CatalogVariant(
            tenantId=tenant_id, productId=variant['productId'], variantId=variant['variantId'],
            brandKind=variant['brandKind'], brandName=variant['brandName'], slot=variant['slot'],
            priceMinor=variant.get('priceMinor'), currency=variant.get('currency', 'INR'),
            stock=variant.get('stock'), published=variant['published'],
            options=dict(variant.get('options') or {}),
            attributes={key: value for key, value in (variant.get('attributes') or {}).items()},
            imageId=variant.get('imageId'), previewStatus=variant.get('previewStatus',
                                                                       'UNVERIFIED_ASSET'),
            sourceVersion=CATALOG_VERSION, checkedAt=checked_at,
            expiresAt=checked_at.replace(microsecond=0) + datetime.timedelta(
                seconds=FRESHNESS_WINDOW),
            isSynthetic=variant.get('isSynthetic', True))

    def list_variants(self, ctx: AccessContext, cursor: str | None, limit: int,
                      query: CatalogQuery | None = None) -> CatalogPage:
        items = [self._to_dto(ctx.tenantId, variant)
                 for variant in self._variants.values() if variant['tenantId'] == ctx.tenantId]
        if query is not None:
            if query.search:
                needle = query.search.lower()
                items = [item for item in items
                         if needle in item.productId.lower() or needle in item.brandName.lower()]
            if query.slot is not None:
                items = [item for item in items if item.slot == query.slot]
            if query.brandKind is not None:
                items = [item for item in items if item.brandKind == query.brandKind]
            if query.inStock is not None:
                items = [item for item in items
                         if (item.stock is not None and item.stock > 0) == query.inStock]
        items.sort(key=lambda item: item.variantId)
        start = int(cursor) if cursor else 0
        page = items[start:start + limit]
        next_cursor = str(start + limit) if start + limit < len(items) else None
        return CatalogPage(items=page, nextCursor=next_cursor, catalogVersion=CATALOG_VERSION)

    def snapshot(self, ctx: AccessContext, variant_ids: list[str]) -> CatalogSnapshot:
        variants = []
        for variant_id in variant_ids:
            variant = self._variants.get(variant_id)
            if variant is not None and variant['tenantId'] == ctx.tenantId:
                variants.append(self._to_dto(ctx.tenantId, variant))
        return CatalogSnapshot(tenantId=ctx.tenantId, catalogVersion=CATALOG_VERSION,
                               variants=variants, evidence={'mode': 'FIXTURE'})

    def slot_for(self, variant_id: str) -> str | None:
        variant = self._variants.get(variant_id)
        return variant['slot'] if variant else None

    def seed_stock(self) -> dict[str, int | None]:
        return {variant_id: variant.get('stock')
                for variant_id, variant in self._variants.items()}

    def price_for(self, variant_id: str) -> tuple[int | None, str]:
        variant = self._variants.get(variant_id)
        if variant is None:
            return None, 'INR'
        return variant.get('priceMinor'), variant.get('currency', 'INR')
