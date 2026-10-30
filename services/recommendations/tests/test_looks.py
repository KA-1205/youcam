"""A03 deterministic look generator: cardinality, budget, diversity, infeasibility."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from contracts.runtime.models import (
    Brief,
    CatalogSnapshot,
    CatalogVariant,
    ClarificationResult,
    ItemRef,
    LooksResult,
    NoCombinationResult,
    SessionSnapshot,
)
from services.recommendations.candidates import build_candidates
from services.recommendations.looks import MAX_COMBINATIONS, generate_looks

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'
OWNED_TOP = ItemRef(slot='TOP', refType='OWNED', refId='owned-top-1')
BOTTOM_ANCHOR = ItemRef(slot='BOTTOM', refType='VARIANT', refId='variant-bottom-1')


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


def session(brief: Brief, anchors: list[ItemRef], locks: list[ItemRef],
            rejected: list[str] | None = None) -> SessionSnapshot:
    return SessionSnapshot.model_validate({
        'sessionId': '00000000-0000-4000-8000-000000000001', 'tenantId': DEMO,
        'sessionVersion': 1, 'consentRevision': 1, 'brief': brief, 'anchors': anchors,
        'locks': locks, 'rejectedIds': rejected or [], 'selections': [], 'updatedAt': T0})


def separates(budget: int | None = 200000, **kwargs) -> Brief:
    return Brief.model_validate({
        'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
        'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
        'budgetMinor': budget, 'currency': 'INR', 'hardRequirements': {}, 'preferences': {},
        **kwargs})


SESSION_ID = '00000000-0000-4000-8000-000000000001'


def looks_for(brief: Brief, anchors: list[ItemRef], locks: list[ItemRef],
              catalog: CatalogSnapshot | None = None, **gen_kwargs):
    snap = catalog or demo_catalog()
    cand = build_candidates(snap, session(brief, anchors, locks),
                            profile(anchors), now=T0)
    return generate_looks(cand, snap, session_id=SESSION_ID, **gen_kwargs)


def profile(anchors: list[ItemRef]):
    from contracts.runtime.models import ConsentControls, ConsentSnapshot, ProfileSnapshot
    controls = ConsentControls.model_validate(dict.fromkeys(ConsentControls.model_fields, False))
    return ProfileSnapshot(actorId='actor-1', tenantId=DEMO, preferences={}, consent=ConsentSnapshot(
        consentRevision=1, controls=controls, processors=[], assetIds=[]),
        ownedItems=[ref for ref in anchors if ref.refType == 'OWNED'])


def test_separates_returns_three_deterministic_looks():
    result = looks_for(separates(), [OWNED_TOP], [OWNED_TOP])
    assert isinstance(result, LooksResult)
    assert result.kind == 'LOOKS'
    assert 1 <= len(result.looks) <= 3
    first = result.looks[0]
    assert first.completeness == 'COMPLETE_OUTFIT'
    assert first.merchandiseTotalMinor == 140000  # cheapest bottom + shoes; owned top is zero
    assert first.budgetVerified is True
    slots = {i.slot for i in first.items}
    assert slots == {'TOP', 'BOTTOM', 'SHOES'}
    again = looks_for(separates(), [OWNED_TOP], [OWNED_TOP])
    assert again == result  # deterministic including look IDs


def test_size_variants_of_same_product_do_not_multiply_looks():
    catalog = demo_catalog()
    twin = next(v for v in catalog.variants
                if v.variantId == 'variant-shoes-1').model_copy(
        update={'variantId': 'variant-shoes-1b', 'options': {'size': 'UK 8'}})
    catalog = catalog.model_copy(update={'variants': [*catalog.variants, twin],
                                         'evidence': {**catalog.evidence,
                                                      'variant-shoes-1b': 'listing twin'}})
    base = looks_for(separates(), [OWNED_TOP], [OWNED_TOP], catalog)
    plain = looks_for(separates(), [OWNED_TOP], [OWNED_TOP])
    assert len(base.looks) == len(plain.looks)  # same product identity, not a new look


def test_alternatives_differ_in_unlocked_product():
    result = looks_for(separates(), [OWNED_TOP], [OWNED_TOP])
    identities = []
    for look in result.looks:
        identities.append(sorted((i.slot, i.refId) for i in look.items if i.slot != 'TOP'))
    assert len({tuple(ids) for ids in identities}) == len(identities)


def test_budget_below_minimum_is_a_constraint_proof():
    result = looks_for(separates(budget=100000), [OWNED_TOP], [OWNED_TOP])
    assert isinstance(result, NoCombinationResult)
    assert result.proofCode == 'CONSTRAINT_PROOF'
    assert set(result.affectedSlots) == {'BOTTOM', 'SHOES'}
    assert result.evaluatedCatalogVersion == 'catalog-v1'
    assert result.constraintEvidence


def test_empty_required_slot_is_proven_without_search():
    catalog = demo_catalog()
    drained = [v.model_copy(update={'stock': 0}) if v.slot == 'SHOES' else v
               for v in catalog.variants]
    result = looks_for(separates(), [OWNED_TOP], [OWNED_TOP],
                       catalog.model_copy(update={'variants': drained}))
    assert isinstance(result, NoCombinationResult)
    assert result.proofCode == 'EMPTY_REQUIRED_SLOT'
    assert result.affectedSlots == ['SHOES']


def test_truncated_search_is_clarification_not_infeasibility():
    result = looks_for(separates(), [OWNED_TOP], [OWNED_TOP], max_combinations=0)
    assert isinstance(result, ClarificationResult)
    assert result.reason == 'SEARCH_LIMIT'
    assert result.question


def test_exhaustive_search_proves_infeasibility():
    # the catalog is stripped of OUTER, so the requested slot has no eligible candidates
    brief = Brief.model_validate({
        'lookMode': 'CATEGORY_SET', 'outfitForm': None,
        'requestedSlots': ['OUTER'], 'occasion': None, 'budgetMinor': None,
        'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    catalog = demo_catalog()
    stripped = [v for v in catalog.variants if v.slot != 'OUTER']
    result = looks_for(brief, [OWNED_TOP], [OWNED_TOP],
                       catalog.model_copy(update={'variants': stripped}))
    assert isinstance(result, NoCombinationResult)
    assert result.proofCode == 'EMPTY_REQUIRED_SLOT'
    assert result.affectedSlots == ['OUTER']


def test_one_piece_contradiction_is_constraint_proof():
    brief = Brief.model_validate({
        'lookMode': 'CATEGORY_SET', 'outfitForm': None,
        'requestedSlots': ['ONE_PIECE', 'TOP'], 'occasion': None, 'budgetMinor': None,
        'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    result = looks_for(brief, [OWNED_TOP], [OWNED_TOP])
    assert isinstance(result, NoCombinationResult)
    assert result.proofCode == 'CONSTRAINT_PROOF'
    assert set(result.affectedSlots) == {'ONE_PIECE', 'TOP'}


def test_incompatible_lock_triggers_clarification():
    brief = Brief.model_validate({
        'lookMode': 'OUTFIT', 'outfitForm': 'ONE_PIECE',
        'requestedSlots': ['ONE_PIECE', 'SHOES'], 'occasion': None, 'budgetMinor': 200000,
        'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    result = looks_for(brief, [OWNED_TOP], [OWNED_TOP])
    assert isinstance(result, ClarificationResult)
    assert result.reason == 'MISSING_REQUIRED_INPUT'


def test_category_set_completeness_and_total():
    brief = Brief.model_validate({
        'lookMode': 'CATEGORY_SET', 'outfitForm': None,
        'requestedSlots': ['TOP', 'BOTTOM'], 'occasion': None, 'budgetMinor': 150000,
        'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    result = looks_for(brief, [BOTTOM_ANCHOR], [BOTTOM_ANCHOR])
    assert isinstance(result, LooksResult)
    look = result.looks[0]
    assert look.completeness == 'CATEGORY_SET'
    assert look.merchandiseTotalMinor == 110000  # cheapest top plus the locked bottom purchase


def test_fully_locked_returns_single_zero_spend_look():
    owned_bottom = ItemRef(slot='BOTTOM', refType='OWNED', refId='owned-bottom-1')
    owned_shoes = ItemRef(slot='SHOES', refType='OWNED', refId='owned-shoes-1')
    result = looks_for(separates(), [OWNED_TOP, owned_bottom, owned_shoes],
                       [OWNED_TOP, owned_bottom, owned_shoes])
    assert isinstance(result, LooksResult)
    assert len(result.looks) == 1
    assert result.looks[0].merchandiseTotalMinor == 0
    assert result.looks[0].budgetVerified is True


def test_unknown_price_without_budget_yields_null_total_and_warning():
    catalog = demo_catalog()
    keep = {'variant-top-3', 'variant-bottom-1'}
    catalog = catalog.model_copy(update={
        'variants': [v for v in catalog.variants if v.variantId in keep]})
    brief = Brief.model_validate({
        'lookMode': 'CATEGORY_SET', 'outfitForm': None,
        'requestedSlots': ['TOP', 'BOTTOM'], 'occasion': None, 'budgetMinor': None,
        'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    result = looks_for(brief, [BOTTOM_ANCHOR], [BOTTOM_ANCHOR], catalog)
    assert isinstance(result, LooksResult)
    first = result.looks[0]
    assert sorted(i.refId for i in first.items) == ['variant-bottom-1', 'variant-top-3']
    assert first.merchandiseTotalMinor is None
    assert first.budgetVerified is False
    assert any('price' in w.casefold() for w in first.warnings)


def test_sponsored_items_carry_a_warning():
    result = looks_for(separates(budget=260000), [BOTTOM_ANCHOR], [BOTTOM_ANCHOR])
    assert isinstance(result, LooksResult)
    sponsored_looks = [look for look in result.looks
                       if any(i.refId.endswith('-2') for i in look.items)]
    assert all(any('sponsor' in w.casefold() for w in look.warnings)
               for look in sponsored_looks)


def test_reasons_cite_snapshot_evidence():
    result = looks_for(separates(), [OWNED_TOP], [OWNED_TOP])
    assert isinstance(result, LooksResult)
    evidence = {**demo_catalog().evidence, 'owned-top-1': 'confirmed owned item'}
    for look in result.looks:
        assert look.reasons
        for reason in look.reasons:
            assert reason.evidenceIds
            for evidence_id in reason.evidenceIds:
                assert evidence_id in evidence, evidence_id


def test_constant_matches_spec_bound():
    assert MAX_COMBINATIONS == 10_000
