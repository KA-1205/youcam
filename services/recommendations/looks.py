"""Deterministic look generation with bounded search and honest infeasibility.

Baseline order is the ranked candidate order per slot. Canonical identity is
the sorted set of slot plus product ID (owned ID for owned items), so a
different size of the same product is never a distinct look. Truncated search
reports NEEDS_CLARIFICATION/SEARCH_LIMIT; NO_ELIGIBLE_COMBINATION requires an
empty required slot, a constraint proof or a completed exhaustive search.
"""
from __future__ import annotations

import itertools
import time
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from contracts.runtime.models import (
    CatalogSnapshot,
    ClarificationResult,
    Evidence,
    ItemRef,
    Look,
    LooksResult,
    NoCombinationResult,
    Slot,
    StylistResult,
)

from .candidates import Candidate, CandidateSet

MAX_COMBINATIONS = 10_000
MAX_LOOKS = 3
SEARCH_DEADLINE_SECONDS = 2.0
_LOOK_NAMESPACE = uuid5(NAMESPACE_URL, 'anchor-fit:stylist-v1:looks')


def generate_looks(candidates: CandidateSet, catalog: CatalogSnapshot, *,
                   session_id: str = '', max_combinations: int = MAX_COMBINATIONS,
                   deadline_seconds: float | None = SEARCH_DEADLINE_SECONDS) -> StylistResult:
    brief = candidates.brief
    if brief is None:  # pragma: no cover - builder always supplies the brief
        raise ValueError('CandidateSet is missing the brief')
    started = time.monotonic() if deadline_seconds is not None else None

    if candidates.contradictions:
        return NoCombinationResult(
            kind='NO_ELIGIBLE_COMBINATION',
            proofCode='CONSTRAINT_PROOF', affectedSlots=_contradiction_slots(brief),
            evaluatedCatalogVersion=catalog.catalogVersion,
            constraintEvidence=[f'brief:{brief.lookMode}', *candidates.contradictions])
    if candidates.incompatible_locks:
        locked = ', '.join(sorted({ref.slot for ref in candidates.incompatible_locks}))
        return ClarificationResult(
            kind='NEEDS_CLARIFICATION',
            question=f'The locked {locked} item cannot be part of the requested '
                     'outfit form. Unlock it or choose a different form.',
            reason='MISSING_REQUIRED_INPUT')

    form_slots = set(brief.requestedSlots)
    if brief.lookMode == 'OUTFIT':
        form_slots |= {'TOP', 'BOTTOM', 'SHOES'} if brief.outfitForm == 'SEPARATES' \
            else {'ONE_PIECE', 'SHOES'}

    empty = sorted(slot for slot in candidates.required
                   if not candidates.by_slot.get(slot)
                   and slot not in {ref.slot for ref in candidates.fixed})
    if empty:
        return NoCombinationResult(
            kind='NO_ELIGIBLE_COMBINATION',
            proofCode='EMPTY_REQUIRED_SLOT', affectedSlots=empty,
            evaluatedCatalogVersion=catalog.catalogVersion,
            constraintEvidence=[f'catalog:{catalog.catalogVersion}', *empty])

    fixed_price = sum(candidates.fixed_variants[ref.refId].priceMinor or 0
                      for ref in candidates.fixed if ref.refType == 'VARIANT')
    if brief.budgetMinor is not None:
        positive = {slot: min(c.new_spend_minor or 0 for c in candidates.by_slot[slot])
                    for slot in candidates.required
                    if slot not in {ref.slot for ref in candidates.fixed}
                    and candidates.by_slot.get(slot)}
        minimum = fixed_price + sum(positive.values())
        if minimum > brief.budgetMinor:
            return NoCombinationResult(
                kind='NO_ELIGIBLE_COMBINATION',
                proofCode='CONSTRAINT_PROOF',
                affectedSlots=sorted(slot for slot, price in positive.items() if price > 0),
                evaluatedCatalogVersion=catalog.catalogVersion,
                constraintEvidence=[f'catalog:{catalog.catalogVersion}',
                                    f'minimum:{minimum}'])

    slot_order = [slot for slot in brief.requestedSlots if slot in candidates.by_slot]
    slot_order += sorted(slot for slot in candidates.by_slot if slot not in slot_order)
    locked_slots = {ref.slot for ref in candidates.fixed}
    slot_order = [slot for slot in slot_order if slot not in locked_slots]

    per_slot: list[list[tuple[Candidate, str]]] = []
    for slot in slot_order:
        seen_products: set[str] = set()
        options: list[tuple[Candidate, str]] = []
        for candidate in candidates.by_slot[slot]:
            if candidate.variant.productId in seen_products:
                continue  # another size of the same product is not a new option
            seen_products.add(candidate.variant.productId)
            options.append((candidate, candidate.variant.productId))
        per_slot.append(options)

    looks: list[Look] = []
    identities: set[tuple[tuple[str, str], ...]] = set()
    evaluated = 0
    exhausted = True
    combos = itertools.product(*per_slot) if per_slot else ((),)  # all-fixed is one combo
    for combo in combos:
        evaluated += 1
        if max_combinations is not None and evaluated > max_combinations:
            exhausted = False
            break
        if started is not None and deadline_seconds is not None \
                and time.monotonic() - started > deadline_seconds:
            exhausted = False
            break
        items = [*candidates.fixed, *(c.ref for c, _ in combo)]
        identity = _identity(items, combo)
        if identity in identities:
            continue
        total, _warned = _total(candidates, combo)
        if brief.budgetMinor is not None and (total is None or total > brief.budgetMinor):
            continue
        identities.add(identity)
        looks.append(_build_look(candidates, catalog, session_id, identity, items, combo,
                                 total, form_slots))
        if len(looks) >= MAX_LOOKS:
            break

    if looks:
        return LooksResult(kind='LOOKS', looks=looks, warnings=[])
    if exhausted:
        return NoCombinationResult(
            kind='NO_ELIGIBLE_COMBINATION',
            proofCode='EXHAUSTIVE_SEARCH', affectedSlots=sorted(slot_order),
            evaluatedCatalogVersion=catalog.catalogVersion,
            constraintEvidence=[f'catalog:{catalog.catalogVersion}'])
    return ClarificationResult(
        kind='NEEDS_CLARIFICATION',
        question='The bounded combination search stopped before finding a valid look. '
                 'Narrow the requirements or raise the budget.',
        reason='SEARCH_LIMIT')


def _contradiction_slots(brief) -> list[Slot]:
    requested = set(brief.requestedSlots)
    involved = requested & ({'ONE_PIECE', 'TOP', 'BOTTOM'})
    if brief.lookMode == 'OUTFIT':
        involved |= {'TOP', 'BOTTOM', 'SHOES'} if brief.outfitForm == 'SEPARATES' \
            else {'ONE_PIECE', 'SHOES'}
    return sorted(involved)


def _identity(items: list[ItemRef], combo) -> tuple[tuple[str, str], ...]:
    product_by_ref = {c.ref.refId: product for c, product in combo}
    parts = []
    for ref in items:
        key = product_by_ref.get(ref.refId, ref.refId)
        parts.append((ref.slot, key))
    return tuple(sorted(parts))


def _total(candidates: CandidateSet, combo) -> tuple[int | None, bool]:
    total = sum(candidates.fixed_variants[ref.refId].priceMinor or 0
                for ref in candidates.fixed if ref.refType == 'VARIANT')
    unknown = any(c.new_spend_minor is None for c, _ in combo)
    total += sum(c.new_spend_minor or 0 for c, _ in combo)
    return (None if unknown else total), unknown


def _build_look(candidates: CandidateSet, catalog: CatalogSnapshot, session_id: str,
                identity, items: list[ItemRef], combo, total: int | None,
                form_slots: set[Slot]) -> Look:
    brief = candidates.brief
    assert brief is not None
    warnings: list[str] = []
    reasons: list[Evidence] = []
    for candidate, _ in combo:
        variant = candidate.variant
        if candidate.sponsored:
            warnings.append(f'{variant.variantId} is a sponsored placement from a '
                            f'{variant.brandKind} brand; organic ranking ignores sponsorship.')
        if variant.priceMinor is None:
            warnings.append(f'{variant.variantId} has an unknown price; the look total '
                            'cannot be verified.')
        price = ('unknown price' if variant.priceMinor is None
                 else f'{variant.priceMinor} minor units')
        reasons.append(Evidence(
            text=f'{variant.brandName} {variant.slot} offered at {price}.',
            evidenceIds=[variant.variantId], kind='CATALOG_FACT'))
        for key in brief.preferences:
            values = {**variant.attributes, **variant.options}
            observed = values.get(key)
            if observed is not None and observed.casefold() == brief.preferences[key].casefold():
                reasons.append(Evidence(
                    text=f'Matches your stated {key} preference.',
                    evidenceIds=[f'preference:{key}'], kind='EXPLICIT_PREFERENCE'))
    for ref in candidates.fixed:
        if ref.refType == 'OWNED':
            reasons.append(Evidence(
                text=f'Confirmed owned {ref.slot} item contributes zero new spend.',
                evidenceIds=[ref.refId], kind='CATALOG_FACT'))
        else:
            variant = candidates.fixed_variants[ref.refId]
            reasons.append(Evidence(
                text=f'Locked {ref.slot} selection retained.',
                evidenceIds=[ref.refId], kind='CATALOG_FACT'))
        if len(reasons) >= 8:
            break
    if total is None:
        warnings.append('The look total is unknown because a selected item has no price.')
    covered = {ref.slot for ref in items}
    completeness: Literal['COMPLETE_OUTFIT', 'CATEGORY_SET'] = \
        'COMPLETE_OUTFIT' if brief.lookMode == 'OUTFIT' and form_slots <= covered \
        else 'CATEGORY_SET'
    return Look(
        lookId=uuid5(_LOOK_NAMESPACE, f'{session_id}:{identity}'),
        items=items[:13],
        reasons=reasons[:8],
        warnings=warnings[:8],
        merchandiseTotalMinor=total,
        currency=brief.currency,
        budgetVerified=brief.budgetMinor is not None and total is not None
        and total <= brief.budgetMinor,
        completeness=completeness,
    )
