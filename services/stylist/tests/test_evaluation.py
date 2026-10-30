"""A08 evaluation: counterfactual harness, regression reports, cost/latency ledger."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from contracts.runtime.models import (
    Brief,
    CatalogSnapshot,
    CatalogVariant,
    ConsentControls,
    ConsentSnapshot,
    ItemRef,
    LooksResult,
    ProfileSnapshot,
    SessionSnapshot,
)
from services.stylist.evaluation import (
    CaseResult,
    CostLedger,
    EvaluationCase,
    compare_reports,
    run_held_out,
)

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'
OWNED_TOP = ItemRef(slot='TOP', refType='OWNED', refId='owned-top-1')


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


def session(preferences: dict[str, str] | None = None) -> SessionSnapshot:
    brief = Brief.model_validate({
        'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
        'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
        'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {},
        'preferences': preferences or {}})
    return SessionSnapshot.model_validate({
        'sessionId': '00000000-0000-4000-8000-000000000001', 'tenantId': DEMO,
        'sessionVersion': 1, 'consentRevision': 1, 'brief': brief, 'anchors': [OWNED_TOP],
        'locks': [OWNED_TOP], 'rejectedIds': [], 'selections': [], 'updatedAt': T0})


def profile() -> ProfileSnapshot:
    controls = ConsentControls.model_validate(dict.fromkeys(ConsentControls.model_fields, False))
    return ProfileSnapshot(actorId='actor-1', tenantId=DEMO, preferences={},
                           consent=ConsentSnapshot(consentRevision=1, controls=controls,
                                                   processors=[], assetIds=[]),
                           ownedItems=[OWNED_TOP])


def case() -> EvaluationCase:
    return EvaluationCase(case_id='case-1', session=session(), catalog=demo_catalog(),
                          profile=profile())


def look_result(bottom: str = 'variant-bottom-1', shoes: str = 'variant-shoes-1',
                total: int | None = 140000, with_lock: bool = True) -> LooksResult:
    items = [
        {'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'},
        {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': bottom},
        {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': shoes}]
    if not with_lock:
        items = items[1:]
    return LooksResult.model_validate({
        'kind': 'LOOKS', 'warnings': [], 'looks': [{
            'lookId': '00000000-0000-4000-8000-000000000004',
            'items': items,
            'reasons': [{'text': 'In stock.', 'evidenceIds': [bottom],
                         'kind': 'CATALOG_FACT'}],
            'warnings': [], 'merchandiseTotalMinor': total, 'currency': 'INR',
            'budgetVerified': True, 'completeness': 'COMPLETE_OUTFIT'}]})


def test_deterministic_policy_scores_zero_violations():
    report = run_held_out([case()], lambda c: look_result(), policy_name='baseline')
    assert report.policy == 'baseline'
    assert report.cases == 1
    assert report.hard_rule_violations == 0
    assert report.determinism_violations == 0
    result = report.results[0]
    assert result.kind == 'LOOKS'
    assert result.evidence_ids == ['variant-bottom-1']


def test_nondeterministic_policy_is_flagged():
    outputs = [look_result(), look_result(bottom='variant-bottom-2')]
    report = run_held_out([case()], lambda c: outputs.pop(0), policy_name='flaky')
    assert report.determinism_violations == 1


def test_budget_and_lock_violations_are_counted():
    over_budget = run_held_out([case()], lambda c: look_result(total=999999),
                               policy_name='over').results[0]
    assert over_budget.budget_violations == 1
    unlocked = run_held_out([case()], lambda c: look_result(with_lock=False),
                            policy_name='unlock').results[0]
    assert unlocked.lock_violations == 1
    cross = run_held_out([case()], lambda c: look_result(bottom='foreign-variant'),
                         policy_name='cross').results[0]
    assert cross.tenant_violations == 1


def test_preference_coverage_uses_explicit_preferences_only():
    preference_case = EvaluationCase(
        case_id='pref', session=session({'color': 'navy'}), catalog=demo_catalog(),
        profile=profile())
    report = run_held_out([preference_case], lambda c: look_result(), policy_name='baseline')
    assert report.results[0].preference_coverage == 0.0  # no navy item in the look


def test_compare_reports_flags_improvement_and_regression():
    base_report = run_held_out([case()], lambda c: look_result(), policy_name='baseline')
    improved = run_held_out([case()], lambda c: look_result(), policy_name='candidate')
    comparison = compare_reports(base_report, improved)
    assert comparison.base_policy == 'baseline'
    assert comparison.candidate_policy == 'candidate'
    assert comparison.metric_delta == 0.0
    assert comparison.regressed is False
    weaker = CaseResult(case_id='case-1', policy='weak', kind='NEEDS_CLARIFICATION',
                        look_count=0, budget_violations=0, lock_violations=0,
                        tenant_violations=0, preference_coverage=0.0, evidence_ids=[])
    from services.stylist.evaluation import EvaluationReport
    weak_report = EvaluationReport(policy='weak', cases=1, results=[weaker],
                                   hard_rule_violations=0, determinism_violations=0)
    regression = compare_reports(base_report, weak_report)
    assert regression.regressed is True


def test_cost_ledger_tracks_latency_fallback_and_unknown_cost():
    ledger = CostLedger()
    ledger.record('job-1', model_calls=1, latency_ms=120.0, fallback_used=False,
                  cost_usd=0.02)
    ledger.record('job-2', model_calls=2, latency_ms=40.0, fallback_used=True,
                  cost_usd=None)
    summary = ledger.summary()
    assert summary['jobs'] == 2
    assert summary['fallback_rate'] == 0.5
    assert summary['latency_p50_ms'] == 40.0
    assert summary['latency_p95_ms'] == 120.0
    assert summary['known_cost_usd'] == 0.02
    assert summary['unknown_cost_jobs'] == 1  # unknown rates stay unknown, never zero
