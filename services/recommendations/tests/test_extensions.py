"""A05 recommendation extensions: jewellery scoring, inspiration, conversation, seam."""
from datetime import datetime, timedelta, timezone

from contracts.runtime.models import (
    Brief,
    CatalogSnapshot,
    CatalogVariant,
    ItemRef,
    ProfileSnapshot,
    SessionSnapshot,
    Slot,
)
from services.recommendations.candidates import CandidateSet, build_candidates
from services.recommendations.extensions import (
    ValidatedAction,
    inspiration_variants,
    rank_for_evaluation,
    score_jewellery,
    validate_conversation_action,
)

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'


def variant(vid: str, slot: Slot, *, price: int = 50000, attrs: dict | None = None,
            brand: str = 'OWN', image: str | None = None, product: str | None = None) \
        -> CatalogVariant:
    return CatalogVariant.model_validate({
        'tenantId': DEMO, 'productId': product or f'p-{vid}', 'variantId': vid,
        'brandKind': brand, 'brandName': 'B', 'slot': slot, 'priceMinor': price,
        'currency': 'INR', 'stock': 5, 'published': True, 'options': {},
        'attributes': attrs or {}, 'imageId': image, 'previewStatus': 'UNVERIFIED_ASSET',
        'sourceVersion': 'v1', 'checkedAt': T0,
        'expiresAt': T0 + timedelta(minutes=15), 'isSynthetic': True})


def garment_catalog() -> CatalogSnapshot:
    garments = [variant('variant-top-1', 'TOP', price=40000, attrs={'occasion': 'work'})]
    jewellery = [
        variant('variant-earrings-a', 'EARRINGS', price=90000, attrs={'occasion': 'work'}),
        variant('variant-earrings-b', 'EARRINGS', price=80000, attrs={'occasion': 'party'}),
        variant('variant-earrings-c', 'EARRINGS', price=70000, attrs={}),
        variant('variant-necklace-a', 'NECKLACE', price=100000, attrs={'occasion': 'work'},
                brand='SPONSOR'),
    ]
    variants = garments + jewellery
    return CatalogSnapshot(tenantId=DEMO, catalogVersion='catalog-v1', variants=variants,
                           evidence={v.variantId: f'listing {v.variantId}' for v in variants})


def test_jewellery_scores_attribute_cooccurrence_first():
    scored = score_jewellery({'occasion': 'work'}, garment_catalog().variants, {})
    ids = [s.variant.variantId for s in scored]
    assert ids[0] == 'variant-earrings-a'  # occasion match beats lower price
    assert all(s.score >= 0 for s in scored)
    assert {s.variant.variantId for s in scored} >= {
        'variant-earrings-a', 'variant-earrings-b', 'variant-earrings-c'}


def test_jewellery_preferences_beat_price_and_missing_is_neutral():
    scored = score_jewellery({}, garment_catalog().variants, {'occasion': 'work'})
    ids = [s.variant.variantId for s in scored]
    assert ids == ['variant-earrings-a', 'variant-necklace-a', 'variant-earrings-c',
                   'variant-earrings-b']


def test_jewellery_sponsorship_has_zero_score_weight():
    own_match = variant('variant-ring-own', 'RING', price=100000, attrs={'occasion': 'work'})
    sponsor_match = variant('variant-ring-sponsor', 'RING', price=100000,
                            attrs={'occasion': 'work'}, brand='SPONSOR')
    scored = score_jewellery({'occasion': 'work'}, [own_match, sponsor_match], {})
    scores = {s.variant.variantId: s.score for s in scored}
    assert scores['variant-ring-own'] == scores['variant-ring-sponsor']
    flags = {s.variant.variantId: s.sponsored for s in scored}
    assert flags == {'variant-ring-own': False, 'variant-ring-sponsor': True}


def test_jewellery_never_scores_or_filters_on_skin_tone():
    light = variant('variant-bracelet-light', 'BRACELET', price=50000,
                    attrs={'skinTone': 'light'})
    dark = variant('variant-bracelet-dark', 'BRACELET', price=50000,
                   attrs={'skinTone': 'dark'})
    scored = score_jewellery({'skinTone': 'dark'}, [light, dark], {'skinTone': 'dark'})
    assert all(s.score == 0 for s in scored)  # tone is never a scoring input
    assert {s.variant.variantId for s in scored} == {'variant-bracelet-light',
                                                     'variant-bracelet-dark'}


def test_inspiration_retrieval_uses_only_permitted_catalog_images():
    catalog = garment_catalog()
    pictured = catalog.variants[0].model_copy(update={'imageId': 'img-top-1'})
    catalog = catalog.model_copy(update={'variants': [pictured, *catalog.variants[1:]]})
    hits = inspiration_variants(catalog, 'work')
    assert [h.variantId for h in hits] == ['variant-top-1']  # jewellery lacks permitted images
    assert all(h.imageId for h in hits)
    assert inspiration_variants(catalog, 'nonexistent-thing') == []


def test_inspiration_is_deterministic_and_capped():
    pictured = [variant(f'variant-top-{i}', 'TOP', attrs={'style': 'floral'},
                        image=f'img-{i}') for i in range(20)]
    catalog = CatalogSnapshot(tenantId=DEMO, catalogVersion='v', variants=pictured,
                              evidence={})
    hits = inspiration_variants(catalog, 'floral')
    assert len(hits) == 12
    assert hits == sorted(hits, key=lambda v: v.variantId)
    assert inspiration_variants(catalog, 'floral') == hits


def make_session(rejected: list[str] | None = None) -> SessionSnapshot:
    brief = Brief.model_validate({
        'lookMode': 'CATEGORY_SET', 'outfitForm': None,
        'requestedSlots': ['TOP', 'EARRINGS'], 'occasion': None, 'budgetMinor': None,
        'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    anchor = ItemRef(slot='TOP', refType='VARIANT', refId='variant-top-1')
    return SessionSnapshot.model_validate({
        'sessionId': '00000000-0000-4000-8000-000000000001', 'tenantId': DEMO,
        'sessionVersion': 1, 'consentRevision': 1, 'brief': brief, 'anchors': [anchor],
        'locks': [anchor], 'rejectedIds': rejected or [], 'selections': [],
        'updatedAt': T0})


def candidates_for(session: SessionSnapshot) -> CandidateSet:
    from contracts.runtime.models import ConsentControls, ConsentSnapshot
    controls = ConsentControls.model_validate(dict.fromkeys(ConsentControls.model_fields, False))
    consent = ConsentSnapshot(consentRevision=1, controls=controls, processors=[], assetIds=[])
    profile = ProfileSnapshot(actorId='a', tenantId=DEMO, preferences={}, consent=consent,
                              ownedItems=[])
    return build_candidates(garment_catalog(), session, profile, now=T0)


def test_conversation_validates_add_item_against_candidates():
    session = make_session()
    action = validate_conversation_action(
        {'kind': 'ADD_ITEM', 'slot': 'EARRINGS', 'refId': 'variant-earrings-a'},
        session, candidates_for(session))
    assert isinstance(action, ValidatedAction)
    assert action.kind == 'ADD_ITEM'
    assert action.ref is not None and action.ref.refId == 'variant-earrings-a'


def test_conversation_rejects_unknown_or_rejected_items_as_clarification():
    session = make_session(rejected=['variant-earrings-a'])
    candidates = candidates_for(session)
    rejected = validate_conversation_action(
        {'kind': 'ADD_ITEM', 'slot': 'EARRINGS', 'refId': 'variant-earrings-a'},
        session, candidates)
    assert not isinstance(rejected, ValidatedAction)
    unknown = validate_conversation_action(
        {'kind': 'ADD_ITEM', 'slot': 'EARRINGS', 'refId': 'variant-earrings-z'},
        session, candidates)
    assert not isinstance(unknown, ValidatedAction)


def test_conversation_clarifies_malformed_actions():
    session = make_session()
    candidates = candidates_for(session)
    assert not isinstance(validate_conversation_action({'kind': 'DANCE'}, session,
                                                       candidates), ValidatedAction)
    assert not isinstance(validate_conversation_action({'kind': 'ADD_ITEM'}, session,
                                                       candidates), ValidatedAction)
    bad_budget = validate_conversation_action({'kind': 'SET_BUDGET', 'amount': -1},
                                              session, candidates)
    assert not isinstance(bad_budget, ValidatedAction)
    budget = validate_conversation_action({'kind': 'SET_BUDGET', 'amount': 150000},
                                          session, candidates)
    assert isinstance(budget, ValidatedAction) and budget.budget_minor == 150000


def test_rank_seam_exposes_frozen_features_deterministically():
    session = make_session()
    candidates = candidates_for(session)
    ranking = rank_for_evaluation(candidates)
    earrings = ranking['EARRINGS']
    assert [r.ref_id for r in earrings] == ['variant-earrings-c', 'variant-earrings-b',
                                            'variant-earrings-a']  # price ascending baseline
    again = rank_for_evaluation(candidates)
    assert again == ranking
    last = earrings[-1]
    assert last.features['preference_matches'] == 0
    assert last.features['new_spend_minor'] == 90000
    assert last.ref_id == 'variant-earrings-a'
