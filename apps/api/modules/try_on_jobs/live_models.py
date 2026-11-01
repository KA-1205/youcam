"""Private durable receipts and conservative credit reservations for live calls."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class LiveBase(DeclarativeBase):
    pass


class LiveStep(LiveBase):
    __tablename__ = 'provider_live_steps'
    child_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    reserved_units: Mapped[int] = mapped_column(Integer)
    submit_started: Mapped[bool] = mapped_column(Boolean, default=False)
    next_poll_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class CreditBudget(LiveBase):
    __tablename__ = 'provider_credit_budget'
    budget_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    reserved_units: Mapped[int] = mapped_column(Integer)
