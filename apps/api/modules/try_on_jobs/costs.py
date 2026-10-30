"""Cost cache seam: verified per-feature costs must be fresh before paid submission."""
import hashlib
from datetime import timedelta

from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import PROVIDER_UNAVAILABLE, ApiError
from apps.api.modules.try_on_jobs.models import FeatureCostRow, UtilityBase
from apps.api.modules.try_on_jobs.providers.utility import UtilityClient

COST_STALENESS = timedelta(hours=24)


class CostService:
    def __init__(self, client: UtilityClient) -> None:
        self._client = client

    def cost_for(self, db: Session, capability: str, refresh: bool = False) -> int:
        row = db.get(FeatureCostRow, capability)
        if row is not None and not refresh:
            return row.cost_units
        cost = self._client.feature_cost(f'feature_{capability.lower()}')
        if cost is None:
            raise ApiError(503, PROVIDER_UNAVAILABLE,
                           'No verified cost is available for this feature.')
        now = clock.now()
        if row is None:
            db.add(FeatureCostRow(capability=capability, cost_units=cost, fetched_at=now,
                                  source_version=_version(capability, cost)))
        else:
            row.cost_units = cost
            row.fetched_at = now
            row.source_version = _version(capability, cost)
        db.flush()
        return cost

    def verified_cost(self, db: Session, capability: str) -> int:
        """Cost only when fetched within the last 24 hours; otherwise refuse paid submission."""
        row = db.get(FeatureCostRow, capability)
        if row is None or clock.now() - clock.as_utc(row.fetched_at) > COST_STALENESS:
            raise ApiError(503, 'COST_UNAVAILABLE',
                           'A fresh verified provider cost is required before paid submission.')
        return row.cost_units


def _version(capability: str, cost: int) -> str:
    return hashlib.sha256(f'{capability}:{cost}'.encode()).hexdigest()[:16]


__all__ = ['COST_STALENESS', 'CostService', 'UtilityBase']
