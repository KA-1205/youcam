"""A01 catalog read models: tenant-aware listing, filters, pagination, freshness."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from contracts.runtime.models import CatalogPage, CatalogQuery, CatalogSnapshot, CatalogVariant
from services.catalog.demo import load_demo_catalog
from services.catalog.errors import NotFoundError, StaleCatalogError
from services.catalog.store import FRESHNESS, CatalogStore

FIXTURE = Path('reference/Anchor-Fit-Final-v3.3/demo-catalog.json')
T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'


def ctx(tenant: str = DEMO):
    from contracts.runtime.models import AccessContext
    return AccessContext(actorId='actor-1', tenantId=tenant, roles=['SHOPPER'],
                         verifiedAccount=False, consentRevision=1)


@pytest.fixture
def store() -> CatalogStore:
    payload = json.loads(FIXTURE.read_text(encoding='utf-8'))
    variants, _ = load_demo_catalog(payload, now=T0)
    return CatalogStore(variants, now=lambda: T0)


def test_demo_loader_maps_thirty_variants():
    payload = json.loads(FIXTURE.read_text(encoding='utf-8'))
    variants, owned = load_demo_catalog(payload, now=T0)
    assert len(variants) == 30 and len(owned) == 1
    for variant in variants:
        assert isinstance(variant, CatalogVariant)
        assert variant.checkedAt == T0
        assert variant.expiresAt == T0 + FRESHNESS
        assert variant.sourceVersion == 'fixture-v1'
    unknown = {v.variantId: v for v in variants}['variant-top-3']
    assert unknown.priceMinor is None  # unknown is null, never zero


def test_list_returns_published_tenant_variants_sorted(store):
    page = store.list_variants(ctx(), cursor=None, limit=100)
    assert isinstance(page, CatalogPage)
    assert len(page.items) == 30
    keys = [(v.slot, v.variantId) for v in page.items]
    assert keys == sorted(keys)
    assert {v.variantId for v in page.items} <= {v.variantId for v in page.items}


def test_cross_tenant_sees_nothing_and_explicit_ids_404(store):
    assert store.list_variants(ctx('other-tenant'), None, 100).items == []
    with pytest.raises(NotFoundError):
        store.variant(ctx('other-tenant'), 'variant-top-1')
    with pytest.raises(NotFoundError):
        store.variant(ctx(), 'missing-variant')


def test_query_filters_slot_brand_and_stock(store):
    tops = store.list_variants(ctx(), None, 100, CatalogQuery(slot='TOP')).items
    assert [v.variantId for v in tops] == [f'variant-top-{i}' for i in range(1, 7)]
    sponsors = store.list_variants(ctx(), None, 100, CatalogQuery(brandKind='SPONSOR')).items
    assert all(v.brandKind == 'SPONSOR' for v in sponsors) and len(sponsors) == 15
    in_stock = store.list_variants(ctx(), None, 100, CatalogQuery(inStock=True)).items
    assert 'variant-top-4' not in {v.variantId for v in in_stock}
    assert all(v.stock is not None and v.stock > 0 for v in in_stock)
    out = store.list_variants(ctx(), None, 100, CatalogQuery(inStock=False)).items
    assert [v.variantId for v in out] == ['variant-top-4']


def test_search_matches_brand_and_ids_case_insensitively(store):
    hits = store.list_variants(ctx(), None, 100, CatalogQuery(search='anchor demo')).items
    assert len(hits) == 15  # only the OWN brand carries that name
    assert all(v.brandKind == 'OWN' for v in hits)
    hits = store.list_variants(ctx(), None, 100, CatalogQuery(search='VARIANT-TOP-3')).items
    assert [v.variantId for v in hits] == ['variant-top-3']
    assert store.list_variants(ctx(), None, 100, CatalogQuery(search='no-such-product')).items == []


def test_pagination_is_stable_and_exhaustive(store):
    seen: list[str] = []
    cursor = None
    while True:
        page = store.list_variants(ctx(), cursor, 7)
        seen += [v.variantId for v in page.items]
        if page.nextCursor is None:
            break
        cursor = page.nextCursor
    assert len(seen) == 30 and len(set(seen)) == 30


def test_snapshot_is_tenant_scoped_and_deduplicates(store):
    ids = ['variant-top-1', 'variant-top-1', 'variant-shoes-1']
    snap = store.snapshot(ctx(), ids)
    assert isinstance(snap, CatalogSnapshot)
    assert [v.variantId for v in snap.variants] == ['variant-top-1', 'variant-shoes-1']
    assert all(snap.evidence[v.variantId] for v in snap.variants)
    with pytest.raises(NotFoundError):
        store.snapshot(ctx(), ['variant-top-1', 'variant-bottom-9'])


def test_stale_entries_refresh_on_read_and_invalidate_cursors(store):
    payload = json.loads(FIXTURE.read_text(encoding='utf-8'))
    variants, _ = load_demo_catalog(payload, now=T0)
    expired = variants[0].model_copy(update={
        'checkedAt': T0 - FRESHNESS, 'expiresAt': T0 - timedelta(minutes=1)})
    now = [T0]
    store = CatalogStore([expired, *variants[1:]], now=lambda: now[0])
    page = store.list_variants(ctx(), None, 100)
    refreshed = next(v for v in page.items if v.variantId == variants[0].variantId)
    assert refreshed.checkedAt == T0 and refreshed.expiresAt == T0 + FRESHNESS
    first = store.list_variants(ctx(), None, 5)
    now[0] = T0 + timedelta(hours=1)
    with pytest.raises(StaleCatalogError):
        store.list_variants(ctx(), first.nextCursor, 5)
