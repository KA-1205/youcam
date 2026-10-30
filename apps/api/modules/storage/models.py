"""Asset persistence and audited retention for the privacy lifecycle."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class StorageBase(DeclarativeBase):
    pass


class AssetRow(StorageBase):
    __tablename__ = 'assets'

    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[str | None] = mapped_column(String(64))
    capability: Mapped[str] = mapped_column(String(32))
    content_type: Mapped[str] = mapped_column(String(64))
    byte_length: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default='PENDING_UPLOAD')
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    last_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RetentionEventRow(StorageBase):
    """Append-only retention audit; never stores photo content or signed URLs."""

    __tablename__ = 'retention_events'

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column('details_json', type_=JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
