"""SessionPort implementation: versioned CAS edits, guest claims and look application.

The session is the final atomic application authority; it rechecks catalog facts
for anchors and applies selections only under an expected-version check.
"""
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import STALE_VERSION, ApiError
from apps.api.modules.styling_session.models import SessionBase, StylingSessionRow
from contracts.runtime.models import (
    AccessContext,
    ApplyLook,
    Brief,
    ClaimSession,
    ItemRef,
    SessionCreate,
    SessionEdit,
    SessionSnapshot,
)
from contracts.runtime.ports import CatalogPort


def _snapshot(row: StylingSessionRow, ctx: AccessContext) -> SessionSnapshot:
    return SessionSnapshot(
        brief=Brief(**row.brief), anchors=[ItemRef(**anchor) for anchor in row.anchors],
        sessionId=UUID(row.session_id), tenantId=row.tenant_id,
        sessionVersion=row.session_version, consentRevision=ctx.consentRevision,
        locks=[ItemRef(**lock) for lock in row.locks], rejectedIds=list(row.rejected_ids),
        selections=[ItemRef(**selection) for selection in row.selections],
        updatedAt=row.updated_at)


class SessionService:
    """Implements the frozen SessionPort; ownership is actor-based, never client-supplied."""

    def __init__(self, catalog: CatalogPort) -> None:
        self._catalog = catalog

    def create(self, db: Session, ctx: AccessContext, body: SessionCreate) -> SessionSnapshot:
        self._validate_refs(ctx, body.anchors)
        row = StylingSessionRow(session_id=str(uuid4()), tenant_id=ctx.tenantId,
                                owner_actor_id=ctx.actorId, session_version=1,
                                brief=body.brief.model_dump(), anchors=self._dump(body.anchors),
                                locks=[], rejected_ids=[], selections=self._dump(body.anchors),
                                claimed_by_account=None, created_at=clock.now(),
                                updated_at=clock.now())
        db.add(row)
        db.flush()
        return _snapshot(row, ctx)

    def snapshot(self, db: Session, ctx: AccessContext, session_id: UUID) -> SessionSnapshot:
        return _snapshot(self._owned_row(db, ctx, session_id), ctx)

    def edit(self, db: Session, ctx: AccessContext, session_id: UUID, body: SessionEdit,
             approved_brief: Brief | None = None) -> SessionSnapshot:
        row = self._owned_row(db, ctx, session_id)
        if body.expectedSessionVersion != row.session_version:
            raise ApiError(409, STALE_VERSION, 'Session changed; refresh and reapply.')
        self._validate_refs(ctx, body.anchors)
        brief = approved_brief or body.brief
        row.brief = brief.model_dump()
        row.anchors = self._dump(body.anchors)
        row.locks = self._dump(body.locks)
        row.rejected_ids = list(body.rejectedIds)
        row.selections = self._dump(body.selections)
        row.session_version += 1
        row.updated_at = clock.now()
        db.flush()
        return _snapshot(row, ctx)

    def assert_editable(self, db: Session, ctx: AccessContext, session_id: UUID,
                        expected_version: int) -> None:
        """Ownership/tenant/version guard injected into dependent lanes via composition."""
        row = self._owned_row(db, ctx, session_id)
        if expected_version != row.session_version:
            raise ApiError(409, STALE_VERSION, 'Session changed; refresh and reapply.')

    def claim(self, db: Session, ctx: AccessContext, body: ClaimSession,
              account_id: str) -> SessionSnapshot:
        row = self._owned_row(db, ctx, body.sessionId)
        if body.expectedSessionVersion != row.session_version:
            raise ApiError(409, STALE_VERSION, 'Session changed; refresh and reapply.')
        row.claimed_by_account = account_id
        row.session_version += 1
        row.updated_at = clock.now()
        db.flush()
        return _snapshot(row, ctx)

    def apply(self, db: Session, ctx: AccessContext, session_id: UUID, expected_version: int,
              selections: list[ItemRef], approved_exception_ids: list[UUID],
              approved_brief: Brief | None = None) -> SessionSnapshot:
        """Atomic selection application; the only writer of final session state."""
        row = self._owned_row(db, ctx, session_id)
        if expected_version != row.session_version:
            raise ApiError(409, STALE_VERSION, 'Session changed; refresh and reapply.')
        self._validate_refs(ctx, selections)
        row.selections = self._dump(selections)
        if approved_brief is not None:
            row.brief = approved_brief.model_dump()
        del approved_exception_ids  # exception effects are validated by the proposal owner
        row.session_version += 1
        row.updated_at = clock.now()
        db.flush()
        return _snapshot(row, ctx)

    def apply_look(self, db: Session, ctx: AccessContext, session_id: UUID,
                   body: ApplyLook) -> SessionSnapshot:
        raise ApiError(501, 'NOT_IMPLEMENTED',
                       'Look application requires the stylist lane integration.')

    def _owned_row(self, db: Session, ctx: AccessContext, session_id: UUID) -> StylingSessionRow:
        row = db.get(StylingSessionRow, str(session_id))
        if row is None or row.tenant_id != ctx.tenantId:
            raise ApiError(404, 'NOT_FOUND', 'Unknown session.')
        if row.owner_actor_id != ctx.actorId:
            raise ApiError(403, 'SCOPE_FORBIDDEN', 'This session belongs to another shopper.')
        return row

    def _validate_refs(self, ctx: AccessContext, refs: list[ItemRef]) -> None:
        variant_ids = [ref.refId for ref in refs if ref.refType == 'VARIANT']
        if not variant_ids:
            return
        found = {variant.variantId for variant in
                 self._catalog.snapshot(ctx, variant_ids).variants}
        missing = sorted(set(variant_ids) - found)
        if missing:
            raise ApiError(422, 'VALIDATION_ERROR',
                           f'Unknown catalog references: {", ".join(missing)}.')

    @staticmethod
    def _dump(refs: list[ItemRef]) -> list[dict]:
        return [ref.model_dump() for ref in refs]


__all__ = ['SessionBase', 'SessionService']
