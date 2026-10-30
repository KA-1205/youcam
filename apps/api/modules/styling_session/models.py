"""Styling-session persistence. Styling-session alone applies selections."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class SessionBase(DeclarativeBase):
    pass


class StylingSessionRow(SessionBase):
    __tablename__ = 'styling_sessions'

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_actor_id: Mapped[str] = mapped_column(String(64), index=True)
    session_version: Mapped[int] = mapped_column(Integer)
    brief: Mapped[dict] = mapped_column('brief_json', type_=JSON)
    anchors: Mapped[list] = mapped_column('anchors_json', type_=JSON)
    locks: Mapped[list] = mapped_column('locks_json', type_=JSON)
    rejected_ids: Mapped[list] = mapped_column('rejected_ids_json', type_=JSON)
    selections: Mapped[list] = mapped_column('selections_json', type_=JSON)
    claimed_by_account: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
