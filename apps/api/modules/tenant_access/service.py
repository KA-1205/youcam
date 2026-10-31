"""Access context resolution and demo login. Tenant and identity are server-side truth.

Email one-time-link authentication is the production default; this lane ships the
explicitly labelled development login for isolated demo deployments only, guarded
by ANCHOR_DEMO_MODE. Guest cookies are opaque, server-issued and 24-hour bound.
"""
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.modules.tenant_access.models import (
    AccessBase,
    Account,
    AccountRole,
    Actor,
    AuthSession,
    Tenant,
)

COOKIE_NAME = 'anchor_session'
GUEST_TTL = timedelta(hours=24)
DEMO_TENANT = 'demo-anchor-fit'


@dataclass
class Identity:
    actor_id: str
    tenant_id: str
    roles: list[str]
    verified: bool
    account_id: str | None
    set_cookie: str | None = None

    def access_context(self, consent_revision: int):
        from typing import cast

        from contracts.runtime.models import AccessContext, Role

        return AccessContext(actorId=self.actor_id, tenantId=self.tenant_id,
                             roles=cast(list[Role], self.roles),
                             verifiedAccount=self.verified, consentRevision=consent_revision)


def demo_mode_enabled() -> bool:
    return os.getenv('ANCHOR_DEMO_MODE', 'true').lower() in ('1', 'true', 'yes')


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_tenant(db: Session, tenant_id: str) -> None:
    if db.get(Tenant, tenant_id) is None:
        db.add(Tenant(tenant_id=tenant_id, display_name='Anchor Fit — simulated store',
                      created_at=clock.now()))
        db.flush()


class AccessService:
    """Resolves the cookie to an actor; creates a bound guest when absent or stale."""

    def resolve(self, db: Session, cookie_token: str | None) -> Identity:
        if cookie_token:
            identity = self._load(db, cookie_token)
            if identity is not None:
                return identity
        return self._create_guest(db)

    def _load(self, db: Session, token: str) -> Identity | None:
        row = db.get(AuthSession, token_hash(token))
        if row is None or row.revoked_at is not None or clock.as_utc(row.expires_at) <= clock.now():
            return None
        actor = db.get(Actor, row.actor_id)
        if actor is None:
            return None
        account = db.get(Account, actor.account_id) if actor.account_id else None
        if account is not None and account.deleted_at is not None:
            return None
        roles = ['SHOPPER']
        if account is not None:
            roles = cast(list[str], list(db.scalars(select(AccountRole.role)
                                                 .where(AccountRole.account_id
                                                        == account.account_id))))
        return Identity(actor_id=actor.actor_id, tenant_id=actor.tenant_id, roles=roles,
                        verified=actor.kind == 'ACCOUNT' and account is not None
                        and account.verified_at is not None,
                        account_id=actor.account_id)

    def _create_guest(self, db: Session) -> Identity:
        tenant_id = os.getenv('ANCHOR_TENANT_ID', DEMO_TENANT)
        ensure_tenant(db, tenant_id)
        actor = Actor(actor_id=f'actor:{uuid4().hex}', tenant_id=tenant_id, kind='GUEST',
                      account_id=None, created_at=clock.now())
        db.add(actor)
        return self._issue_cookie(db, actor, roles=['SHOPPER'], verified=False, account_id=None)

    def _issue_cookie(self, db: Session, actor: Actor, roles: list[str], verified: bool,
                      account_id: str | None) -> Identity:
        token = secrets.token_urlsafe(32)
        db.add(AuthSession(token_hash=token_hash(token), tenant_id=actor.tenant_id,
                           actor_id=actor.actor_id, created_at=clock.now(),
                           expires_at=clock.now() + GUEST_TTL, revoked_at=None))
        return Identity(actor_id=actor.actor_id, tenant_id=actor.tenant_id, roles=roles,
                        verified=verified, account_id=account_id, set_cookie=token)

    def demo_login(self, db: Session, cookie_token: str | None, email: str,
                   roles: tuple[str, ...] = ('SHOPPER',)) -> Identity:
        """Labelled development login: upgrades the current cookie's actor to an account."""
        if not demo_mode_enabled():
            raise LookupError('demo login unavailable')
        tenant_id = os.getenv('ANCHOR_TENANT_ID', DEMO_TENANT)
        ensure_tenant(db, tenant_id)
        canonical = email.strip().lower()
        account = db.scalar(select(Account).where(Account.tenant_id == tenant_id,
                                                  Account.email == canonical,
                                                  Account.deleted_at.is_(None)))
        if account is None:
            account = Account(account_id=f'acct:{uuid4().hex}', tenant_id=tenant_id,
                              email=canonical, verified_at=clock.now(), preferences={},
                              deleted_at=None, created_at=clock.now())
            db.add(account)
            for role in roles:
                db.add(AccountRole(account_id=account.account_id, role=role))
        db.flush()
        current = self._load(db, cookie_token) if cookie_token else None
        if current is not None and current.verified and current.account_id == account.account_id:
            return current
        if current is not None and current.account_id is None:
            actor_id = current.actor_id  # upgrade the guest actor in place, keeping its sessions
        else:
            actor_id = f'actor:{uuid4().hex}'
        actor = db.get(Actor, actor_id)
        if actor is None:
            actor = Actor(actor_id=actor_id, tenant_id=tenant_id, kind='ACCOUNT',
                          account_id=account.account_id, created_at=clock.now())
            db.add(actor)
        else:
            actor.kind = 'ACCOUNT'
            actor.account_id = account.account_id
        db.flush()
        return self._issue_cookie(db, actor, roles=['SHOPPER'], verified=True,
                                  account_id=account.account_id)

    def logout(self, db: Session, cookie_token: str | None) -> None:
        if not cookie_token:
            return
        row = db.get(AuthSession, token_hash(cookie_token))
        if row is not None:
            row.revoked_at = clock.now()

    def delete_account(self, db: Session, account_id: str) -> list[str]:
        """Tombstone the account: every session it issued stops resolving now.

        The tombstone also denies re-login through the same row. Returns the
        actor ids that belonged to the account so composition can cancel its
        queued work, revoke its assets and close its shares in the same
        transaction. First-party rows are purged later by the worker sweep.
        """
        account = db.get(Account, account_id)
        if account is None or account.deleted_at is not None:
            raise LookupError('Unknown or non-owned resource.')
        now = clock.now()
        account.deleted_at = now
        # Free the unique email immediately so the identity can re-register
        # fresh; the tombstone row keeps the ledger reference until the purge.
        account.email = f'deleted:{account.account_id}@invalid'
        actors = list(db.scalars(select(Actor).where(Actor.account_id == account_id)))
        for actor in actors:
            for row in db.scalars(select(AuthSession).where(AuthSession.actor_id
                                                            == actor.actor_id)):
                row.revoked_at = row.revoked_at or now
        return [actor.actor_id for actor in actors]


__all__ = ['COOKIE_NAME', 'AccessBase', 'AccessService', 'GUEST_TTL', 'Identity', 'demo_mode_enabled',
           'token_hash']
