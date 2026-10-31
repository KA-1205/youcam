"""Asset lifecycle: consent-gated upload, five-minute proxy access, revocation,
expiry (24h unsaved / 90d saved), immediate revocation on delete and an
append-only retention audit.
"""
import hashlib
import os
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import CONSENT_REQUIRED, ApiError
from apps.api.modules.storage.backend import StorageBackend
from apps.api.modules.storage.models import AssetRow, RetentionEventRow, StorageBase
from contracts.runtime.models import (
    AccessContext,
    Ack,
    AssetDescriptor,
    AssetUploadRequest,
    ConsentSnapshot,
    SaveAsset,
)

UNSAVED_TTL = timedelta(hours=24)
SAVED_TTL = timedelta(days=90)
SIGNATURE_TTL = timedelta(minutes=5)
MAX_BYTES = 10 * 1024 * 1024

AssetStatus = Literal['PENDING_UPLOAD', 'AVAILABLE', 'EXPIRED', 'REVOKED']


class StorageService:
    def __init__(self, backend: StorageBackend,
                 consent_lookup: Callable[[Session, str], object] | None = None) -> None:
        self._backend = backend
        self._consent_lookup = consent_lookup

    def prepare_upload(self, db: Session, ctx: AccessContext, body: AssetUploadRequest,
                       bytes_digest: str | None = None) -> AssetDescriptor:
        self._require_consent(db, ctx.actorId, 'processPhotos')
        if body.byteLength > MAX_BYTES:
            raise ApiError(422, 'VALIDATION_ERROR', 'Photo exceeds the supported size.')
        asset_id = str(uuid4())
        storage_key = f'{ctx.tenantId}/{asset_id}'
        now = clock.now()
        db.add(AssetRow(asset_id=asset_id, tenant_id=ctx.tenantId, actor_id=ctx.actorId,
                        account_id=None, capability=body.capability,
                        content_type=body.contentType, byte_length=body.byteLength,
                        digest=bytes_digest or hashlib.sha256(asset_id.encode()).hexdigest(),
                        storage_key=storage_key, status='PENDING_UPLOAD', saved=False,
                        last_saved_at=None, expires_at=now + UNSAVED_TTL, deleted_at=None,
                        created_at=now, updated_at=now))
        self._audit(db, asset_id, ctx.actorId, 'UPLOAD_PREPARED',
                    {'capability': body.capability, 'mode': self._backend.mode})
        db.flush()
        return self._descriptor(db, asset_id, issue_access=False)

    def complete_upload(self, db: Session, asset_id: str, data: bytes) -> None:
        """Fixture-mode upload completion; live transfers go directly to the backend."""
        row = db.get(AssetRow, asset_id)
        if row is None or row.status != 'PENDING_UPLOAD':
            raise ApiError(409, 'HTTP_ERROR', 'No pending upload exists for this asset.')
        self._backend.put(row.storage_key, data)
        row.digest = hashlib.sha256(data).hexdigest()
        row.byte_length = len(data)
        row.status = 'AVAILABLE'
        row.updated_at = clock.now()
        self._audit(db, asset_id, row.actor_id, 'UPLOADED', {'mode': self._backend.mode})
        db.flush()

    def get_asset(self, db: Session, ctx: AccessContext, asset_id: str) -> AssetDescriptor:
        row = self._owned_asset(db, ctx, asset_id)
        return self._descriptor(db, row.asset_id, issue_access=row.status == 'AVAILABLE')

    def asset_available(self, db: Session, ctx: AccessContext, asset_id: str) -> bool:
        """Injected into preview orchestration so it never imports storage internals."""
        row = db.get(AssetRow, asset_id)
        return bool(row is not None and row.tenant_id == ctx.tenantId
                    and row.actor_id == ctx.actorId and row.status == 'AVAILABLE')

    def save_asset(self, db: Session, ctx: AccessContext, asset_id: str,
                   body: SaveAsset) -> AssetDescriptor:
        self._require_consent(db, ctx.actorId, 'savePhotosAndRenders')
        row = self._owned_asset(db, ctx, asset_id, include_terminal=False)
        row.saved = True
        row.last_saved_at = clock.now()
        row.expires_at = row.last_saved_at + SAVED_TTL
        row.updated_at = clock.now()
        self._audit(db, asset_id, ctx.actorId, 'SAVED', {'retentionDays': SAVED_TTL.days})
        db.flush()
        return self._descriptor(db, asset_id, issue_access=row.status == 'AVAILABLE')

    def delete_asset(self, db: Session, ctx: AccessContext, asset_id: str) -> Ack:
        row = self._owned_asset(db, ctx, asset_id, include_terminal=False)
        # Revocation blocks new access immediately; stored bytes are removed now.
        self._backend.delete(row.storage_key)
        row.status = 'REVOKED'
        row.deleted_at = clock.now()
        row.updated_at = clock.now()
        self._audit(db, asset_id, ctx.actorId, 'REVOKED', {'reason': 'SHOPPER_REQUESTED'})
        self._audit(db, asset_id, ctx.actorId, 'DELETED', {'mode': self._backend.mode})
        db.flush()
        return Ack(requestId=uuid4(), status='ACCEPTED')

    def revoke_for_actors(self, db: Session, actor_ids: list[str]) -> int:
        """Account deletion: revoke access immediately and drop stored bytes now."""
        if not actor_ids:
            return 0
        now = clock.now()
        revoked = 0
        for row in db.scalars(select(AssetRow)
                              .where(AssetRow.actor_id.in_(actor_ids),
                                     AssetRow.status.in_(('PENDING_UPLOAD', 'AVAILABLE')))).all():
            self._backend.delete(row.storage_key)
            row.status = 'REVOKED'
            row.deleted_at = now
            row.updated_at = now
            self._audit(db, row.asset_id, row.actor_id, 'REVOKED',
                        {'reason': 'ACCOUNT_DELETED', 'mode': self._backend.mode})
            revoked += 1
        db.flush()
        return revoked

    def store_render_result(self, db: Session, tenant_id: str, actor_id: str,
                            capability: str, data: bytes = b'fixture-render-bytes') -> str:
        """Persist a provider result into private storage as a fresh unsaved asset.

        A provider URL is never the durable saved artifact; bytes are captured
        while consent remains valid and expire on the unsaved 24h clock.
        """
        asset_id = str(uuid4())
        storage_key = f'{tenant_id}/{asset_id}'
        self._backend.put(storage_key, data)
        now = clock.now()
        db.add(AssetRow(asset_id=asset_id, tenant_id=tenant_id, actor_id=actor_id,
                        account_id=None, capability=capability, content_type='image/png',
                        byte_length=len(data), digest=hashlib.sha256(data).hexdigest(),
                        storage_key=storage_key, status='AVAILABLE', saved=False,
                        last_saved_at=None, expires_at=now + UNSAVED_TTL, deleted_at=None,
                        created_at=now, updated_at=now))
        self._audit(db, asset_id, actor_id, 'UPLOADED', {'mode': self._backend.mode,
                                                         'origin': 'PREVIEW_RESULT'})
        db.flush()
        return asset_id

    def sweep_expired(self, db: Session, now: datetime | None = None) -> int:
        """Expire unsaved assets after 24h and saved assets 90d after the last save."""
        now = now or clock.now()
        rows = db.scalars(select(AssetRow).where(AssetRow.status == 'AVAILABLE')).all()
        expired = 0
        for row in rows:
            if clock.as_utc(row.expires_at) > now:
                continue
            row.status = 'EXPIRED'
            row.updated_at = now
            self._backend.delete(row.storage_key)
            self._audit(db, row.asset_id, row.actor_id, 'EXPIRED',
                        {'saved': row.saved, 'mode': self._backend.mode})
            expired += 1
        db.flush()
        return expired

    def _descriptor(self, db: Session, asset_id: str, issue_access: bool = True) -> AssetDescriptor:
        row = db.get(AssetRow, asset_id)
        assert row is not None
        access_path = ''
        expires_at = clock.now()
        if issue_access and row.status == 'AVAILABLE':
            access_path = f'/api/assets/{asset_id}/content?token={self._sign(asset_id)}'
            expires_at = clock.now() + SIGNATURE_TTL
        return AssetDescriptor(assetId=UUID(asset_id), accessPath=access_path, expiresAt=expires_at,
                               saved=row.saved, status=cast(AssetStatus, row.status))

    def _sign(self, asset_id: str) -> str:
        secret = os.environ.get('ANCHOR_URL_SECRET', 'demo-signing-secret')
        return hashlib.sha256(f'{asset_id}:{secret}'.encode()).hexdigest()[:32]

    def _owned_asset(self, db: Session, ctx: AccessContext, asset_id: str,
                     include_terminal: bool = True) -> AssetRow:
        row = db.get(AssetRow, asset_id)
        if row is None or row.tenant_id != ctx.tenantId or row.actor_id != ctx.actorId:
            # Unknown and non-owned assets are indistinguishable to the caller.
            raise ApiError(404, 'NOT_FOUND', 'Unknown asset.')
        if not include_terminal and row.status in ('REVOKED', 'EXPIRED'):
            raise ApiError(410, 'HTTP_ERROR', f'This asset is {row.status.lower()}.')
        return row

    def _require_consent(self, db: Session, actor_id: str, control: str) -> None:
        if self._consent_lookup is None:
            raise ApiError(501, 'NOT_IMPLEMENTED', 'Consent authority is not wired.')
        snapshot = cast(ConsentSnapshot, self._consent_lookup(db, actor_id))
        if not getattr(snapshot.controls, control):
            raise ApiError(403, CONSENT_REQUIRED,
                           f'The {control} consent control must be enabled.')

    def _audit(self, db: Session, asset_id: str, actor_id: str, event_type: str,
               details: dict) -> None:
        db.add(RetentionEventRow(event_id=str(uuid4()), asset_id=asset_id, actor_id=actor_id,
                                 event_type=event_type, details=details, created_at=clock.now()))


__all__ = ['SAVED_TTL', 'SIGNATURE_TTL', 'StorageBase', 'StorageService', 'UNSAVED_TTL']
