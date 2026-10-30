"""Recommendation extensions (A05): jewellery sets, inspiration retrieval,
conversation over validated actions and the learnable ranking seam.

Every path here stays inside the permitted catalog, never uses protected
traits (skin tone is never a scoring or filtering input) and gives
sponsorship zero weight in scores.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from contracts.runtime.models import (
    CatalogSnapshot,
    CatalogVariant,
    ClarificationResult,
    ItemRef,
    SessionSnapshot,
    Slot,
)

from .candidates import CandidateSet

JEWELLERY_SLOTS: tuple[Slot, ...] = ('EARRINGS', 'NECKLACE', 'RING', 'BRACELET', 'WATCH')
PROTECTED_KEYS = frozenset({'skinTone', 'skin_tone', 'ethnicity', 'gender'})
INSPIRATION_LIMIT = 12


@dataclass(frozen=True)
class ScoredJewellery:
    variant: CatalogVariant
    score: int
    sponsored: bool


@dataclass(frozen=True)
class ValidatedAction:
    kind: str
    ref: ItemRef | None = None
    slot: Slot | None = None
    budget_minor: int | None = None
    preference_key: str | None = None
    preference_value: str | None = None


def score_jewellery(garment_attributes: dict[str, str], variants: list[CatalogVariant],
                    preferences: dict[str, str]) -> list[ScoredJewellery]:
    """Deterministic jewellery set scoring; missing attributes are neutral."""
    garment = {key: value for key, value in garment_attributes.items()
               if key not in PROTECTED_KEYS}
    scored: list[ScoredJewellery] = []
    for variant in variants:
        if variant.slot not in JEWELLERY_SLOTS or not variant.published:
            continue
        attributes = {key: value for key, value in variant.attributes.items()
                      if key not in PROTECTED_KEYS}
        shared = sum(1 for key, value in garment.items()
                     if attributes.get(key) == value)
        preferences_clean = {key: value for key, value in preferences.items()
                             if key not in PROTECTED_KEYS}
        matched = sum(1 for key, value in preferences_clean.items()
                      if attributes.get(key) == value)
        scored.append(ScoredJewellery(
            variant=variant, score=2 * matched + shared,
            sponsored=variant.brandKind == 'SPONSOR'))
    scored.sort(key=lambda s: (-s.score, s.variant.priceMinor if s.variant.priceMinor
                               is not None else float('inf'), s.variant.variantId))
    return scored


def inspiration_variants(catalog: CatalogSnapshot, query: str) -> list[CatalogVariant]:
    """Retrieve inspiration from permitted catalog images only, deterministically."""
    needle = query.casefold()
    hits: list[tuple[int, CatalogVariant]] = []
    for variant in catalog.variants:
        if not variant.imageId or not variant.published:
            continue  # only catalog-origin permitted images are retrievable
        attributes = {key: value for key, value in variant.attributes.items()
                      if key not in PROTECTED_KEYS}
        values = [value for value in attributes.values() if value is not None]
        haystack = ' '.join([variant.brandName, variant.productId, variant.variantId,
                             *values, *variant.options.values()]).casefold()
        if needle in haystack:
            matches = sum(1 for value in values if needle in value.casefold())
            hits.append((matches, variant))
    hits.sort(key=lambda pair: (-pair[0], pair[1].variantId))
    return [variant for _, variant in hits[:INSPIRATION_LIMIT]]


def validate_conversation_action(action: dict[str, object], session: SessionSnapshot,
                                 candidates: CandidateSet) \
        -> ValidatedAction | ClarificationResult:
    """Map a conversational utterance to a validated action or a clarification.

    Actions may only reference already-validated candidate state; nothing here
    mutates the session (styling-session alone applies changes).
    """
    kind = action.get('kind')
    if kind == 'ADD_ITEM':
        slot, ref_id = action.get('slot'), action.get('refId')
        if not isinstance(slot, str) or not isinstance(ref_id, str):
            return _clarify('Which item should be added?', 'MISSING_REQUIRED_INPUT')
        slot_name = cast(Slot, slot)
        for candidate in candidates.by_slot.get(slot_name, []):
            if candidate.ref.refId == ref_id:
                return ValidatedAction(kind='ADD_ITEM', ref=candidate.ref, slot=slot_name)
        return _clarify('That item is not currently eligible for this session.',
                        'INSUFFICIENT_EVIDENCE')
    if kind == 'REMOVE_SLOT':
        slot = action.get('slot')
        if not isinstance(slot, str):
            return _clarify('Which slot should be cleared?', 'MISSING_REQUIRED_INPUT')
        if slot not in candidates.required:
            return _clarify('That slot is not part of this brief.',
                            'INSUFFICIENT_EVIDENCE')
        return ValidatedAction(kind='REMOVE_SLOT', slot=cast(Slot, slot))
    if kind == 'REGENERATE':
        return ValidatedAction(kind='REGENERATE')
    if kind == 'SET_BUDGET':
        amount = action.get('amount')
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            return _clarify('Please choose a non-negative budget.',
                            'MISSING_REQUIRED_INPUT')
        return ValidatedAction(kind='SET_BUDGET', budget_minor=amount)
    if kind == 'SET_PREFERENCE':
        key, value = action.get('key'), action.get('value')
        if not isinstance(key, str) or not isinstance(value, str) \
                or not key or key in PROTECTED_KEYS or not value:
            return _clarify('Which preference should be recorded?',
                            'MISSING_REQUIRED_INPUT')
        return ValidatedAction(kind='SET_PREFERENCE', preference_key=key,
                               preference_value=value)
    return _clarify('I can add items, clear slots, set budgets or preferences, '
                    'or regenerate looks.', 'INSUFFICIENT_EVIDENCE')


def _clarify(question: str, reason: str) -> ClarificationResult:
    return ClarificationResult.model_validate({'kind': 'NEEDS_CLARIFICATION',
                                               'question': question, 'reason': reason})


@dataclass(frozen=True)
class RankedRef:
    ref_id: str
    features: dict[str, float | int | str | None]


def rank_for_evaluation(candidates: CandidateSet) -> dict[Slot, list[RankedRef]]:
    """Expose the frozen baseline ranking as a learnable evaluation seam."""
    ranking: dict[Slot, list[RankedRef]] = {}
    for slot, items in candidates.by_slot.items():
        ranking[slot] = [
            RankedRef(ref_id=c.ref.refId,
                      features={'preference_matches': c.preference_matches,
                                'missing_optional': c.missing_optional,
                                'new_spend_minor': c.new_spend_minor,
                                'sponsored': c.sponsored,
                                'variant_id': c.ref.refId})
            for c in items]
    return ranking
