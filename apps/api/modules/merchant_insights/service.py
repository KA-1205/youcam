"""Merchant insights (FR-079/FR-080): first-party aggregates only.

The composition root supplies windowed counts from first-party tables through
one injected source; this module owns the metric definitions: denominator
relationships, the fixed trailing window, cohort suppression and the DEMO flag
so demo orders are never readable as revenue. Product clicks have no first-party
source yet, so they are honestly absent rather than reported as zero.
"""
from collections.abc import Callable
from datetime import datetime, timedelta

from apps.api import clock
from contracts.runtime.models import InsightMetric, Insights

MIN_COHORT = 5
WINDOW = timedelta(days=7)

# name -> denominator metric name (None = base count defines its own cohort)
DENOMINATORS: dict[str, str | None] = {
    'qualifiedSessions': None,
    'stylistRequests': 'qualifiedSessions',
    'generatedLooks': 'stylistRequests',
    'wardrobeSaves': 'qualifiedSessions',
    'orders': 'qualifiedSessions',
    'previewJobs': None,
}

Counts = dict[str, tuple[int, int]]


class InsightsService:
    def __init__(self, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or clock.now

    def page(self, counts: Callable[[datetime, datetime], Counts]) -> Insights:
        end = self._now()
        start = end - WINDOW
        raw = counts(start, end)
        metrics = [InsightMetric(
            name=name,
            numerator=None if suppressed else raw.get(name, (0, 0))[0],
            denominator=None if suppressed or base is None
            else raw.get(base, (0, 0))[0],
            distinctShoppers=None if suppressed else raw.get(name, (0, 0))[1],
            suppressed=suppressed,
            windowStart=start, windowEnd=end, mode='DEMO')
            for name, base in DENOMINATORS.items()
            for suppressed in [raw.get(name, (0, 0))[1] < MIN_COHORT]]
        return Insights(metrics=metrics, nextCursor=None)
