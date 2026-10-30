"""Stylist proposals (A06): scoped advice with explicit exception approvals.

Proposals are advice only: styling-session alone applies them through its
atomic version check. Every lock/constraint exception needs its own approval;
application validation rechecks the current catalog and session versions so a
stale proposal can never be applied as current advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID, uuid4

from contracts.runtime.models import (
    AccessContext,
    Ack,
    CatalogSnapshot,
    ItemRef,
    ProposalApply,
    ProposalCreate,
    ProposalRefresh,
    ProposalSnapshot,
    SessionSnapshot,
)

from .errors import InvalidRequestError, NotFoundError, PermissionDenied, StaleSessionError


class SharedSessionCheck(Protocol):
    """Lane C owns share state; the proposal service queries it through this seam."""

    def is_shared_with(self, session_id: UUID, tenant_id: str, actor_id: str) -> bool: ...


@dataclass
class _Record:
    proposal: ProposalSnapshot
    tenant_id: str
    outcome: str | None = None  # ACCEPTED | REJECTED once styling-session applies it
    refresh_requested: bool = False
    audit: list[str] = field(default_factory=list)


class ProposalService:
    def __init__(self, shared: SharedSessionCheck) -> None:
        self._shared = shared
        self._records: dict[UUID, _Record] = {}

    # -- creation and reads --------------------------------------------------
    def create(self, ctx: AccessContext, create: ProposalCreate, session: SessionSnapshot,
               catalog: CatalogSnapshot) -> ProposalSnapshot:
        self._authorize(ctx, create.sessionId, session)
        if create.baseSessionVersion > session.sessionVersion:
            raise StaleSessionError('The proposal targets a session version that does not '
                                    'exist yet.')
        self._validate_selections(create, session, catalog)
        replaced = {ref.refId for ref in session.locks if ref not in create.selections}
        claimed = {e.target for e in create.exceptions if e.kind == 'LOCK_REPLACEMENT'}
        if replaced - claimed:
            raise InvalidRequestError('A locked item is replaced without a lock-replacement '
                                      'exception.')
        status = 'PROPOSAL_READY' if create.baseSessionVersion == session.sessionVersion \
            else 'OUTDATED'
        proposal = ProposalSnapshot.model_validate({
            **create.model_dump(mode='json'),
            'proposalId': str(uuid4()), 'status': status})
        self._records[proposal.proposalId] = _Record(proposal=proposal,
                                                     tenant_id=ctx.tenantId)
        return proposal

    def get(self, ctx: AccessContext, proposal_id: UUID, session: SessionSnapshot) \
            -> ProposalSnapshot:
        record = self._records.get(proposal_id)
        if record is None or record.tenant_id != ctx.tenantId:
            raise NotFoundError()
        return self._with_status(record, session)

    # -- application validation (called by styling-session before its CAS) ----
    def validate_application(self, proposal: ProposalSnapshot, session: SessionSnapshot,
                             apply: ProposalApply, catalog: CatalogSnapshot) -> list[ItemRef]:
        record = self._records.get(proposal.proposalId)
        if record is None or record.tenant_id != session.tenantId:
            raise NotFoundError()
        if record.outcome is not None:
            raise InvalidRequestError('This proposal was already applied or rejected.')
        status = self._with_status(record, session).status
        if status == 'OUTDATED':
            raise StaleSessionError('The proposal is outdated; request a refresh.')
        if apply.expectedSessionVersion != session.sessionVersion:
            raise StaleSessionError()
        approved = set(apply.approvedExceptionIds)
        missing = [e for e in proposal.exceptions if e.exceptionId not in approved]
        if missing:
            raise InvalidRequestError(
                f'{len(missing)} exception(s) lack individual approval.')
        self._validate_selections(proposal, session, catalog)
        replaced_locks = {ref.refId for ref in session.locks
                          if ref not in proposal.selections}
        claimed = {e.target for e in proposal.exceptions if e.kind == 'LOCK_REPLACEMENT'}
        unclaimed = replaced_locks - claimed
        if unclaimed:
            raise InvalidRequestError('A locked item is replaced without a lock-replacement '
                                      'exception.')
        return list(proposal.selections)

    def record_outcome(self, proposal_id: UUID, *, accepted: bool) -> None:
        record = self._records.get(proposal_id)
        if record is None:
            raise NotFoundError()
        record.outcome = 'ACCEPTED' if accepted else 'REJECTED'

    # -- refresh -------------------------------------------------------------
    def refresh(self, ctx: AccessContext, proposal_id: UUID, refresh: ProposalRefresh,
                session: SessionSnapshot) -> Ack:
        record = self._records.get(proposal_id)
        if record is None or session.tenantId != ctx.tenantId:
            raise NotFoundError()
        if refresh.expectedSessionVersion != session.sessionVersion \
                or refresh.expectedConsentRevision != session.consentRevision:
            raise StaleSessionError()
        record.refresh_requested = True
        record.audit.append(f'refresh requested for session version '
                            f'{session.sessionVersion}')
        return Ack(requestId=uuid4(), status='ACCEPTED')

    # -- internals -----------------------------------------------------------
    def _authorize(self, ctx: AccessContext, session_id: UUID, session: SessionSnapshot) -> None:
        if 'STORE_STYLIST' not in ctx.roles:
            raise PermissionDenied()
        if session.tenantId != ctx.tenantId:
            raise NotFoundError()
        if not self._shared.is_shared_with(session_id, ctx.tenantId, ctx.actorId):
            raise NotFoundError()

    def _with_status(self, record: _Record, session: SessionSnapshot) -> ProposalSnapshot:
        if record.outcome is not None:
            return record.proposal.model_copy(update={'status': record.outcome})
        status = 'PROPOSAL_READY' \
            if record.proposal.baseSessionVersion == session.sessionVersion else 'OUTDATED'
        return record.proposal.model_copy(update={'status': status})

    @staticmethod
    def _validate_selections(proposal: ProposalCreate, session: SessionSnapshot,
                             catalog: CatalogSnapshot) -> None:
        variants = {v.variantId: v for v in catalog.variants
                    if v.published and v.tenantId == session.tenantId}
        for ref in proposal.selections:
            if ref.refType == 'OWNED':
                continue
            if ref.refId not in variants:
                raise InvalidRequestError('A proposed item is not in the published catalog.')
            if variants[ref.refId].slot != ref.slot:
                raise InvalidRequestError('A proposed item does not match its slot.')
        covered = {ref.slot for ref in proposal.selections}
        for slot in proposal.brief.requestedSlots:
            if slot not in covered:
                raise InvalidRequestError(f'The proposal leaves requested {slot} uncovered.')
