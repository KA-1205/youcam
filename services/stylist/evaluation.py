"""Merchant and model evaluation (A08): counterfactual harness, regressions, ledger.

The harness runs each held-out case twice per policy to prove determinism,
counts hard-rule violations (budget, lock, tenant) from backend data rather
than trusting policy self-reports, and records stylist cost/latency where
unknown costs stay explicitly unknown instead of being fabricated as zero.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from contracts.runtime.models import (
    CatalogSnapshot,
    ProfileSnapshot,
    SessionSnapshot,
    StylistResult,
)

USEFUL_SHORTLIST_THRESHOLD = 0.05


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    session: SessionSnapshot
    catalog: CatalogSnapshot
    profile: ProfileSnapshot
    held_out: bool = True


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    policy: str
    kind: str
    look_count: int
    budget_violations: int
    lock_violations: int
    tenant_violations: int
    preference_coverage: float
    evidence_ids: list[str]


@dataclass(frozen=True)
class EvaluationReport:
    policy: str
    cases: int
    results: list[CaseResult]
    hard_rule_violations: int
    determinism_violations: int

    @property
    def useful_shortlist_rate(self) -> float:
        if not self.results:
            return 0.0
        useful = sum(1 for result in self.results
                     if result.kind == 'LOOKS' and result.look_count >= 1)
        return useful / len(self.results)

    @property
    def mean_preference_coverage(self) -> float:
        if not self.results:
            return 0.0
        return sum(result.preference_coverage for result in self.results) / len(self.results)


@dataclass(frozen=True)
class ComparisonReport:
    base_policy: str
    candidate_policy: str
    metric: str
    base_value: float
    candidate_value: float
    metric_delta: float
    regressed: bool


PolicyFn = Callable[[EvaluationCase], StylistResult]


def run_held_out(cases: list[EvaluationCase], policy: PolicyFn, *,
                 policy_name: str, runs: int = 2) -> EvaluationReport:
    results: list[CaseResult] = []
    determinism_violations = 0
    hard_violations = 0
    for case in cases:
        outputs = [policy(case) for _ in range(max(1, runs))]
        first = outputs[0]
        if any(output != first for output in outputs[1:]):
            determinism_violations += 1
        result = _score(case, first, policy_name)
        hard_violations += (result.budget_violations + result.lock_violations
                            + result.tenant_violations)
        results.append(result)
    return EvaluationReport(policy=policy_name, cases=len(cases), results=results,
                            hard_rule_violations=hard_violations,
                            determinism_violations=determinism_violations)


def compare_reports(base: EvaluationReport, candidate: EvaluationReport, *,
                    metric: str = 'useful_shortlist_rate',
                    min_uplift: float = USEFUL_SHORTLIST_THRESHOLD) -> ComparisonReport:
    base_value = getattr(base, metric)
    candidate_value = getattr(candidate, metric)
    delta = candidate_value - base_value
    return ComparisonReport(
        base_policy=base.policy, candidate_policy=candidate.policy, metric=metric,
        base_value=base_value, candidate_value=candidate_value, metric_delta=delta,
        regressed=delta < -min_uplift)


def _score(case: EvaluationCase, outcome: StylistResult, policy: str) -> CaseResult:
    kind = str(outcome.kind)
    budget_violations = lock_violations = tenant_violations = 0
    look_count = 0
    coverage: list[float] = []
    evidence_ids: list[str] = []
    looks = getattr(outcome, 'looks', None) or []
    if outcome.__class__.__name__ == 'LooksResult':
        look_count = len(looks)
        variants = {v.variantId: v for v in case.catalog.variants}
        brief = case.session.brief
        for look in looks:
            item_ids = {ref.refId for ref in look.items}
            if brief.budgetMinor is not None and look.merchandiseTotalMinor is not None \
                    and look.merchandiseTotalMinor > brief.budgetMinor:
                budget_violations += 1
            for lock in case.session.locks:
                if lock.refId not in item_ids:
                    lock_violations += 1
                    break
            for ref in look.items:
                variant = variants.get(ref.refId)
                if ref.refType == 'VARIANT' and (variant is None
                                                 or variant.tenantId != case.session.tenantId):
                    tenant_violations += 1
                    break
            covered = _preference_covered(look, variants, brief.preferences)
            coverage.append(1.0 if covered else 0.0)
            for reason in look.reasons:
                evidence_ids.extend(reason.evidenceIds)
    return CaseResult(case_id=case.case_id, policy=policy, kind=kind, look_count=look_count,
                      budget_violations=budget_violations, lock_violations=lock_violations,
                      tenant_violations=tenant_violations,
                      preference_coverage=(sum(coverage) / len(coverage)) if coverage else 0.0,
                      evidence_ids=evidence_ids)


def _preference_covered(look: Any, variants: dict[str, Any],
                        preferences: dict[str, str]) -> bool:
    for ref in look.items:
        variant = variants.get(ref.refId)
        if variant is None:
            continue
        values = {**variant.attributes, **variant.options}
        for key, value in preferences.items():
            observed = values.get(key)
            if observed is not None and observed.casefold() == value.casefold():
                return True
    return False


@dataclass
class _CostEntry:
    job_id: str
    model_calls: int
    latency_ms: float
    fallback_used: bool
    cost_usd: float | None


@dataclass
class CostLedger:
    """Stylist cost and latency tracking; unknown costs are never invented."""

    entries: list[_CostEntry] = field(default_factory=list)

    def record(self, job_id: str, *, model_calls: int, latency_ms: float,
               fallback_used: bool, cost_usd: float | None) -> None:
        self.entries.append(_CostEntry(job_id=job_id, model_calls=model_calls,
                                       latency_ms=latency_ms, fallback_used=fallback_used,
                                       cost_usd=cost_usd))

    def summary(self) -> dict[str, Any]:
        if not self.entries:
            return {'jobs': 0, 'fallback_rate': 0.0, 'latency_p50_ms': 0.0,
                    'latency_p95_ms': 0.0, 'known_cost_usd': 0.0, 'unknown_cost_jobs': 0}
        latencies = sorted(entry.latency_ms for entry in self.entries)

        def percentile(fraction: float) -> float:
            index = min(len(latencies) - 1, int(round(fraction * (len(latencies) - 1))))
            return latencies[index]

        known_costs = [entry.cost_usd for entry in self.entries if entry.cost_usd is not None]
        return {
            'jobs': len(self.entries),
            'fallback_rate': (sum(1 for entry in self.entries if entry.fallback_used)
                              / len(self.entries)),
            'latency_p50_ms': percentile(0.50),
            'latency_p95_ms': percentile(0.95),
            'known_cost_usd': sum(known_costs),
            'unknown_cost_jobs': sum(1 for entry in self.entries
                                     if entry.cost_usd is None),
        }
