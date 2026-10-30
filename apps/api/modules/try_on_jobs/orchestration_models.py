"""Preview orchestration tables: jobs, provider child tasks and visitor quotas."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PreviewBase(DeclarativeBase):
    pass


class PreviewJobRow(PreviewBase):
    __tablename__ = 'preview_jobs'

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64))
    session_version: Mapped[int] = mapped_column(Integer)
    consent_revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default='CREATED', index=True)
    freshness: Mapped[str] = mapped_column(String(16), default='CURRENT')
    execution_mode: Mapped[str] = mapped_column(String(8), default='FIXTURE')
    capability: Mapped[str] = mapped_column(String(32))
    source_asset_id: Mapped[str] = mapped_column(String(64))
    selections: Mapped[list] = mapped_column('selections_json', type_=JSON)
    effect_ids: Mapped[list] = mapped_column('effect_ids_json', type_=JSON)
    settings: Mapped[dict] = mapped_column('settings_json', type_=JSON)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChildTaskRow(PreviewBase):
    __tablename__ = 'preview_child_tasks'

    child_task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    capability: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default='CREATED')
    source_asset_id: Mapped[str] = mapped_column(String(64))
    result_asset_id: Mapped[str | None] = mapped_column(String(64))
    applied_items: Mapped[list] = mapped_column('applied_items_json', type_=JSON)
    unknown_charge_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_task_id: Mapped[str | None] = mapped_column(String(64))
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QuotaCounterRow(PreviewBase):
    __tablename__ = 'preview_quota_counters'
    __table_args__ = (UniqueConstraint('actor_id', 'day', name='uq_quota_actor_day'),)

    counter_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10))
    paid_intents: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActiveJobMarker(PreviewBase):
    __tablename__ = 'preview_active_jobs'

    actor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
