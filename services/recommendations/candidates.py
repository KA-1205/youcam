"""Eligible candidate construction (Behavior Contract §§2–3).

Slot coverage follows the brief form; unknown stock or stale freshness blocks
new purchase recommendations while fixed references survive; unknown prices
are excluded only against a hard budget. Ranking is the frozen baseline:
explicit preference matches descending, missing optional attributes ascending,
new-spend price ascending, variant ID ascending — sponsorship has zero weight.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from contracts.runtime.models import (
    Brief,
    CatalogSnapshot,
    CatalogVariant,
    ItemRef,
    ProfileSnapshot,
    SessionSnapshot,
    Slot,
)

from .errors import NotFoundError

MAX_CANDIDATES = 40

ONE_PIECE_FORM_SLOTS: tuple[Slot, ...] = ('ONE_PIECE', 'SHOES')
SEPARATES_FORM_SLOTS: tuple[Slot, ...] = ('TOP', 'BOTTOM', 'SHOES')


@dataclass(frozen=True)
class Candidate:
    slot: Slot
    ref: ItemRef
    variant: CatalogVariant
    new_spend_minor: int | None
    preference_matches: int
    missing_optional: int

    @property
    def sponsored(self) -> bool:
        return self.variant.brandKind == 'SPONSOR'


@dataclass(frozen=True)
class CandidateSet:
    required: list[Slot]
    by_slot: dict[Slot, list[Candidate]]
    fixed: list[ItemRef]
    fixed_variants: dict[str, CatalogVariant] = field(default_factory=dict)
    incompatible_locks: list[ItemRef] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    catalog_version: str = ''
    brief: Brief | None = None


def build_candidates(catalog: CatalogSnapshot, session: SessionSnapshot,
                     profile: ProfileSnapshot, *, now: datetime) -> CandidateSet:
    if catalog.tenantId != session.tenantId:
        raise NotFoundError('Catalog does not belong to the session tenant.')
    brief = session.brief
    contradictions = _contradictions(brief)
    fixed, incompatible = _fixed_items(session, catalog)
    required = _required_slots(brief, session.locks)
    fixed_slots = {ref.slot for ref in fixed}
    by_variant = {v.variantId: v for v in catalog.variants}
    rejected = set(session.rejectedIds)

    by_slot: dict[Slot, list[Candidate]] = {}
    for slot in required:
        if slot in fixed_slots:
            by_slot[slot] = []
            continue
        eligible = [
            Candidate(slot=slot, ref=ItemRef(slot=slot, refType='VARIANT', refId=v.variantId),
                      variant=v, new_spend_minor=v.priceMinor,
                      preference_matches=_preference_matches(v, brief.preferences),
                      missing_optional=_missing_optional(v, brief.preferences))
            for v in catalog.variants
            if v.slot == slot and v.published and v.variantId not in rejected
            and _purchasable(v, brief, now)]
        by_slot[slot] = sorted(eligible, key=lambda c: (
            -c.preference_matches, c.missing_optional,
            c.new_spend_minor if c.new_spend_minor is not None else float('inf'),
            c.ref.refId))
    order = [slot for slot in brief.requestedSlots if slot in by_slot]
    order += sorted(slot for slot in by_slot if slot not in brief.requestedSlots)
    return CandidateSet(required=sorted(required), by_slot=allocate(by_slot, order), fixed=fixed,
                        fixed_variants={r.refId: by_variant[r.refId] for r in fixed
                                        if r.refType == 'VARIANT' and r.refId in by_variant},
                        incompatible_locks=incompatible, contradictions=contradictions,
                        catalog_version=catalog.catalogVersion, brief=brief,
                        )


def required_and_optional(brief: Brief, locks: list[ItemRef]) -> set[Slot]:
    """Slots a look must cover: form mandates, explicit requests and locks."""
    if brief.lookMode == 'OUTFIT':
        slots = set(SEPARATES_FORM_SLOTS if brief.outfitForm == 'SEPARATES'
                    else ONE_PIECE_FORM_SLOTS)
    else:
        slots = set(brief.requestedSlots)
    slots |= set(brief.requestedSlots)
    slots |= {lock.slot for lock in locks}
    return slots


def _required_slots(brief: Brief, locks: list[ItemRef]) -> set[Slot]:
    return required_and_optional(brief, locks)


def _contradictions(brief: Brief) -> list[str]:
    requested = set(brief.requestedSlots)
    issues: list[str] = []
    if brief.lookMode == 'OUTFIT':
        if brief.outfitForm == 'SEPARATES' and 'ONE_PIECE' in requested:
            issues.append('ONE_PIECE cannot coexist with a SEPARATES outfit form')
        if brief.outfitForm == 'ONE_PIECE' and requested & {'TOP', 'BOTTOM'}:
            issues.append('TOP/BOTTOM cannot coexist with a ONE_PIECE outfit form')
    elif 'ONE_PIECE' in requested and requested & {'TOP', 'BOTTOM'}:
        issues.append('ONE_PIECE cannot coexist with TOP/BOTTOM in a category set')
    return issues


def _fixed_items(session: SessionSnapshot, catalog: CatalogSnapshot) \
        -> tuple[list[ItemRef], list[ItemRef]]:
    seen: list[ItemRef] = []
    for ref in [*session.anchors, *session.locks]:
        if ref not in seen:
            seen.append(ref)
    known_variants = {v.variantId for v in catalog.variants}
    form = session.brief.outfitForm
    incompatible: list[ItemRef] = []
    if session.brief.lookMode == 'OUTFIT' and form is not None:
        form_slots = set(SEPARATES_FORM_SLOTS if form == 'SEPARATES' else ONE_PIECE_FORM_SLOTS)
        incompatible = [ref for ref in seen if ref.slot not in form_slots]
    unknown = [ref for ref in seen
               if ref.refType == 'VARIANT' and ref.refId not in known_variants]
    if unknown:
        raise NotFoundError('A fixed reference is not in this catalog.')
    return seen, incompatible


def _purchasable(variant: CatalogVariant, brief: Brief, now: datetime) -> bool:
    if variant.stock is None or variant.stock <= 0:
        return False  # unknown stock blocks new purchase recommendations
    if variant.expiresAt <= now:
        return False  # stale price/stock observation is not purchasable evidence
    if variant.priceMinor is None and brief.budgetMinor is not None:
        return False  # new hard-budget candidates with unknown price are excluded
    return True


def _preference_matches(variant: CatalogVariant, preferences: dict[str, str]) -> int:
    values = {**variant.attributes, **variant.options}
    matches = 0
    for key, value in preferences.items():
        observed = values.get(key)
        if observed is not None and observed.casefold() == value.casefold():
            matches += 1
    return matches


def _missing_optional(variant: CatalogVariant, preferences: dict[str, str]) -> int:
    values = {**variant.attributes, **variant.options}
    return sum(1 for key in preferences if not values.get(key))


def allocate(candidates: dict[Slot, list[Candidate]], requested: list[Slot]) \
        -> dict[Slot, list[Candidate]]:
    """One candidate per requested slot first, then round-robin remaining capacity."""
    order = [slot for slot in requested if slot in candidates]
    order += sorted(slot for slot in candidates if slot not in requested)
    picked: dict[Slot, list[Candidate]] = {slot: [] for slot in candidates}
    total = 0
    for slot in order:  # first pass: one per requested slot
        if candidates[slot] and total < MAX_CANDIDATES:
            picked[slot].append(candidates[slot][0])
            total += 1
    depth = 1
    while total < MAX_CANDIDATES:
        progressed = False
        for slot in order:
            if depth < len(candidates[slot]) and total < MAX_CANDIDATES:
                picked[slot].append(candidates[slot][depth])
                total += 1
                progressed = True
        if not progressed:
            break
        depth += 1
    return picked
