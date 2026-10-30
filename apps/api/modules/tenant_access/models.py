"""Tenant access persistence: tenants, accounts, actors, roles, cookie sessions."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AccessBase(DeclarativeBase):
    pass


class Tenant(AccessBase):
    __tablename__ = 'tenants'

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Account(AccessBase):
    __tablename__ = 'accounts'
    __table_args__ = (UniqueConstraint('tenant_id', 'email', name='uq_account_email'),)

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.tenant_id'), index=True)
    email: Mapped[str] = mapped_column(String(320))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preferences: Mapped[dict] = mapped_column('preferences_json', type_=JSON, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AccountRole(AccessBase):
    __tablename__ = 'account_roles'

    account_id: Mapped[str] = mapped_column(
        ForeignKey('accounts.account_id', ondelete='CASCADE'), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), primary_key=True)


class Actor(AccessBase):
    """Server-issued identity behind one cookie: a guest, or an account after login."""

    __tablename__ = 'actors'

    actor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.tenant_id'), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # GUEST or ACCOUNT
    account_id: Mapped[str | None] = mapped_column(
        ForeignKey('accounts.account_id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSession(AccessBase):
    __tablename__ = 'auth_sessions'

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.tenant_id'), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('actors.actor_id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
