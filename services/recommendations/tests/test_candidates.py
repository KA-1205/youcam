"""A02 eligible candidate construction: coverage, eligibility, locks, budget."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from contracts.runtime.models import (
    AccessContext,
    Brief,
    CatalogSnapshot,
    CatalogVariant,
    ConsentControls,
    ConsentSnapshot,
    ItemRef,
    ProfileSnapshot,
    SessionSnapshot,
)
from services.recommendations.candidates import CandidateSet, build_candidates
from services.recommendations.errors import NotFoundError

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'
OWNED_TOP = ItemRef(slot='TOP', refType='OWNED', refId='owned-top-1')
TOP_ANCHOR = ItemRef(slot='TOP', refType='VARIANT', refId='variant-top-1')
BOTTOM_ANCHOR = ItemRef(slot='BOTTOM', refType='VARIANT', refId='variant-bottom-1')


def ctx(tenant: str = DEMO) -> AccessContext:
    return AccessContext(actorId='actor-1', tenantId=tenant, roles=['SHOPPER'],
                         verifiedAccount=False, consentRevision=1)


def demo_catalog() -> CatalogSnapshot:
    payload = json.loads(Path('reference/Anchor-Fit-Final-v3.3/demo-catalog.json')
                         .read_text(encoding='utf-8'))
    variants = [CatalogVariant.model_validate({
        'tenantId': row['tenantId'], 'productId': row['productId'],
        'variantId': row['variantId'], 'brandKind': row['brandKind'],
        'brandName': row['brandName'], 'slot': row['slot'],
        'priceMinor': row.get('priceMinor'), 'currency': row.get('currency', 'INR'),
        'stock': row.get('stock'), 'published': row.get('published', True),
        'options': dict(row.get('options', {})), 'attributes': dict(row.get('attributes', {})),
        'imageId': row.get('imageId'),
        'previewStatus': row.get('previewStatus', 'UNVERIFIED_ASSET'),
        'sourceVersion': 'fixture-v1', 'checkedAt': T0,
        'expiresAt': T0 + timedelta(minutes=15), 'isSynthetic': row.get('isSynthetic', True)})
        for row in payload['variants']]
    return CatalogSnapshot(tenantId=DEMO, catalogVersion='catalog-v1', variants=variants,
                           evidence={v.variantId: f'listing {v.variantId}' for v in variants})


def consent() -> ConsentSnapshot:
    controls = ConsentControls.model_validate(dict.fromkeys(
        ConsentControls.model_fields, False))
    return ConsentSnapshot(consentRevision=1, controls=controls, processors=[], assetIds=[])


def demo_profile(owned: list[ItemRef] | None = None) -> ProfileSnapshot:
    return ProfileSnapshot(actorId='actor-1', tenantId=DEMO, preferences={},
                           consent=consent(),
                           ownedItems=[OWNED_TOP] if owned is None else owned)


def demo_session(**overrides) -> SessionSnapshot:
    brief = Brief.model_validate({
        'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
        'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
        'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {}, 'preferences': {},
    })
    fields: dict = {
        'sessionId': '00000000-0000-4000-8000-000000000001', 'tenantId': DEMO,
        'sessionVersion': 1, 'consentRevision': 1, 'brief': brief, 'anchors': [OWNED_TOP],
        'locks': [OWNED_TOP], 'rejectedIds': [], 'selections': [], 'updatedAt': T0,
    }
    fields.update(overrides)
    return SessionSnapshot.model_validate(fields)


def build(catalog=None, session=None, profile=None, now=T0) -> CandidateSet:
    return build_candidates(catalog or demo_catalog(), session or demo_session(),
                            profile or demo_profile(), now=now)


def test_separates_coverage_with_owned_anchor():
    cand = build()
    assert set(cand.required) == {'TOP', 'BOTTOM', 'SHOES'}
    assert cand.fixed == [OWNED_TOP]
    assert {c.ref.refId for c in cand.by_slot['BOTTOM']} == {'variant-bottom-1',
                                                             'variant-bottom-2'}
    assert {c.ref.refId for c in cand.by_slot['SHOES']} == {'variant-shoes-1', 'variant-shoes-2'}
    assert cand.by_slot['TOP'] == []  # the anchor is fixed, not a purchasable candidate


def test_out_of_stock_and_unknown_stock_block_purchase():
    snapshot = demo_catalog()
    out_of_stock = next(v for v in snapshot.variants
                        if v.variantId == 'variant-bottom-2').model_copy(update={'stock': 0})
    mutated = snapshot.model_copy(update={'variants': [
        out_of_stock if v.variantId == 'variant-bottom-2' else v for v in snapshot.variants]})
    session = demo_session(anchors=[BOTTOM_ANCHOR], locks=[BOTTOM_ANCHOR])
    cand = build(mutated, session, demo_profile(owned=[]))
    assert 'variant-bottom-2' not in {c.ref.refId for c in cand.by_slot['BOTTOM']}
    unknown_stock = out_of_stock.model_copy(update={'stock': None})
    mutated = mutated.model_copy(update={'variants': [
        unknown_stock if v.variantId == 'variant-bottom-2' else v for v in mutated.variants]})
    cand = build(mutated, session, demo_profile(owned=[]))
    assert 'variant-bottom-2' not in {c.ref.refId for c in cand.by_slot['BOTTOM']}


def test_unknown_price_excluded_only_against_hard_budget():
    snapshot = demo_catalog()
    session = demo_session(anchors=[BOTTOM_ANCHOR], locks=[BOTTOM_ANCHOR])
    cand = build(snapshot, session, demo_profile(owned=[]))
    assert 'variant-top-3' not in {c.ref.refId for c in cand.by_slot['TOP']}
    brief = demo_session().brief.model_copy(update={'budgetMinor': None})
    session = demo_session(anchors=[BOTTOM_ANCHOR], locks=[BOTTOM_ANCHOR], brief=brief)
    cand = build(snapshot, session, demo_profile(owned=[]))
    assert 'variant-top-3' in {c.ref.refId for c in cand.by_slot['TOP']}


def test_rejected_ids_are_excluded():
    cand = build(session=demo_session(anchors=[TOP_ANCHOR], locks=[TOP_ANCHOR], rejectedIds=['variant-bottom-1']),
                 profile=demo_profile(owned=[]))
    assert 'variant-bottom-1' not in {c.ref.refId for c in cand.by_slot['BOTTOM']}


def test_locked_variant_is_fixed_not_candidate():
    lock = ItemRef(slot='BOTTOM', refType='VARIANT', refId='variant-bottom-2')
    cand = build(session=demo_session(anchors=[TOP_ANCHOR], locks=[TOP_ANCHOR, lock]),
                 profile=demo_profile(owned=[]))
    assert lock in cand.fixed
    assert 'variant-bottom-1' not in {c.ref.refId for c in cand.by_slot['BOTTOM']}


def test_ranking_prefers_preference_then_price_then_id():
    brief = demo_session().brief.model_copy(update={'preferences': {'color': 'navy'}})
    base = {'tenantId': DEMO, 'productId': 'p-a', 'variantId': 'variant-b-a', 'brandKind': 'OWN',
            'brandName': 'B', 'slot': 'BOTTOM', 'priceMinor': 50000, 'currency': 'INR',
            'stock': 5, 'published': True, 'options': {}, 'attributes': {'color': 'red'},
            'imageId': None, 'previewStatus': 'UNVERIFIED_ASSET', 'sourceVersion': 'v1',
            'checkedAt': T0, 'expiresAt': T0 + timedelta(minutes=15), 'isSynthetic': True}
    a = CatalogVariant.model_validate(base)
    b = a.model_copy(update={'variantId': 'variant-b-b', 'priceMinor': 70000,
                             'attributes': {'color': 'navy'}})
    c = b.model_copy(update={'variantId': 'variant-b-c'})
    snapshot = demo_catalog().model_copy(update={'variants': demo_catalog().variants + [a, b, c]})
    cand = build(snapshot, demo_session(anchors=[TOP_ANCHOR], locks=[TOP_ANCHOR], brief=brief),
                 demo_profile(owned=[]))
    ranked = [item.ref.refId for item in cand.by_slot['BOTTOM']]
    assert ranked
    # preference match outranks lower price; equal preference resolved by price then id
    assert ranked[:2] == ['variant-b-b', 'variant-b-c']
    assert ranked.index('variant-b-a') > ranked.index('variant-b-c')


def test_candidate_cap_forty_spreads_across_requested_slots():
    extra = [CatalogVariant.model_validate({
        'tenantId': DEMO, 'productId': f'p-{i}', 'variantId': f'variant-top-x{i}',
        'brandKind': 'OWN', 'brandName': 'B', 'slot': 'TOP', 'priceMinor': 10000 + i,
        'currency': 'INR', 'stock': 5, 'published': True, 'options': {}, 'attributes': {},
        'imageId': None, 'previewStatus': 'UNVERIFIED_ASSET', 'sourceVersion': 'v1',
        'checkedAt': T0, 'expiresAt': T0 + timedelta(minutes=15), 'isSynthetic': True})
        for i in range(60)]
    snapshot = demo_catalog().model_copy(update={'variants': demo_catalog().variants + extra})
    cand = build(snapshot, demo_session(anchors=[BOTTOM_ANCHOR], locks=[BOTTOM_ANCHOR]),
                 demo_profile(owned=[]))
    assert sum(len(v) for v in cand.by_slot.values()) <= 40
    for slot in cand.required:
        if slot == 'BOTTOM':  # covered by the fixed anchor
            continue
        assert len(cand.by_slot[slot]) >= 1


def test_cross_tenant_snapshot_rejected():
    snapshot = demo_catalog().model_copy(update={'tenantId': 'foreign'})
    with pytest.raises(NotFoundError):
        build(snapshot)


def test_incompatible_lock_is_reported_not_deleted():
    brief = Brief.model_validate({
        'lookMode': 'OUTFIT', 'outfitForm': 'ONE_PIECE',
        'requestedSlots': ['ONE_PIECE', 'SHOES'], 'occasion': None,
        'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    session = demo_session(brief=brief, anchors=[OWNED_TOP], locks=[OWNED_TOP])
    cand = build(session=session)
    assert OWNED_TOP in cand.incompatible_locks


def test_stale_purchase_candidates_excluded():
    snapshot = demo_catalog()
    stale_at = T0 - timedelta(minutes=1)
    snapshot = snapshot.model_copy(update={'variants': [
        v.model_copy(update={'checkedAt': stale_at, 'expiresAt': stale_at})
        if v.variantId == 'variant-shoes-1' else v for v in snapshot.variants]})
    cand = build(snapshot)
    assert 'variant-shoes-1' not in {c.ref.refId for c in cand.by_slot['SHOES']}
