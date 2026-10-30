"""Cached provider feature costs; missing or stale costs stop paid submission."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtilityBase(DeclarativeBase):
    pass


class FeatureCostRow(UtilityBase):
    __tablename__ = 'provider_feature_costs'

    capability: Mapped[str] = mapped_column(String(32), primary_key=True)
    cost_units: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str] = mapped_column(String(64))
