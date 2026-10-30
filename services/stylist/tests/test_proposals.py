"""A06 stylist proposals: scoped creation, per-exception approval, refresh."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from contracts.runtime.models import (
    AccessContext,
    Brief,
    CatalogSnapshot,
    CatalogVariant,
    ItemRef,
    ProposalApply,
    ProposalCreate,
    ProposalRefresh,
    ProposalSnapshot,
    SessionSnapshot,
)
from services.stylist.errors import (
    InvalidRequestError,
    NotFoundError,
    PermissionDenied,
    StaleSessionError,
)
from services.stylist.proposals import ProposalService

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'
SESSION_ID = UUID('00000000-0000-4000-8000-000000000001')
LOCK_ID = UUID('00000000-0000-4000-8000-000000000010')


def ctx(role: str = 'STORE_STYLIST', tenant: str = DEMO) -> AccessContext:
    return AccessContext(actorId='stylist-1', tenantId=tenant,
                         roles=[role],  # type: ignore[list-item]
                         verifiedAccount=True, consentRevision=1)


class Shared:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    def is_shared_with(self, session_id: UUID, tenant_id: str, actor_id: str) -> bool:
        return self.allowed


def demo_catalog() -> CatalogSnapshot:
    payload = json.loads(Path('reference/Anchor-Fit-Final-v3.3/demo-catalog.json')
                         .read_text(encoding='utf-8'))
    variants = [CatalogVariant.model_validate({
        'tenantId': row['tenantId'], 'productId': row['productId'],
        'variantId': row['variantId'], 'brandKind': row['brandKind'],
        'brandName': row['brandName'], 'slot': row['slot'],
        'priceMinor': row.get('priceMinor'), 'currency': row.get('currency', 'INR'),
        'stock': row.get('stock'), 'published': row.get('published', True),
        'options': dict(row.get('options', {})), 'attributes': dict(row.get('attributes', {})),
        'imageId': row.get('imageId'),
        'previewStatus': row.get('previewStatus', 'UNVERIFIED_ASSET'),
        'sourceVersion': 'fixture-v1', 'checkedAt': T0,
        'expiresAt': T0 + timedelta(minutes=15), 'isSynthetic': row.get('isSynthetic', True)})
        for row in payload['variants']]
    return CatalogSnapshot(tenantId=DEMO, catalogVersion='catalog-v1', variants=variants,
                           evidence={v.variantId: f'listing {v.variantId}' for v in variants})


def demo_session(version: int = 1, consent_revision: int = 1) -> SessionSnapshot:
    brief = Brief.model_validate({
        'lookMode': 'OUTFIT', 'outfitForm': 'SEPARATES',
        'requestedSlots': ['TOP', 'BOTTOM', 'SHOES'], 'occasion': None,
        'budgetMinor': 200000, 'currency': 'INR', 'hardRequirements': {}, 'preferences': {}})
    anchor = ItemRef(slot='TOP', refType='OWNED', refId='owned-top-1')
    return SessionSnapshot.model_validate({
        'sessionId': str(SESSION_ID), 'tenantId': DEMO, 'sessionVersion': version,
        'consentRevision': consent_revision, 'brief': brief, 'anchors': [anchor],
        'locks': [anchor], 'rejectedIds': [], 'selections': [], 'updatedAt': T0})


def make_create(base_version: int = 1, exceptions: list | None = None,
                catalog_top: bool = False) -> ProposalCreate:
    top = ({'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'variant-top-1'}
           if catalog_top else {'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top-1'})
    return ProposalCreate.model_validate({
        'sessionId': str(SESSION_ID), 'baseSessionVersion': base_version,
        'selections': [
            top,
            {'slot': 'BOTTOM', 'refType': 'VARIANT', 'refId': 'variant-bottom-1'},
            {'slot': 'SHOES', 'refType': 'VARIANT', 'refId': 'variant-shoes-1'}],
        'brief': demo_session().brief.model_dump(),
        'notes': 'Swap in warmer shoes for the rainy week.',
        'exceptions': exceptions or []})


def service(allowed: bool = True) -> ProposalService:
    return ProposalService(Shared(allowed))


def test_create_returns_ready_proposal_for_shared_session():
    proposal = service().create(ctx(), make_create(), demo_session(), demo_catalog())
    assert isinstance(proposal, ProposalSnapshot)
    assert proposal.status == 'PROPOSAL_READY'
    assert proposal.proposalId == proposal.proposalId
    assert proposal.notes.startswith('Swap')


def test_create_requires_stylist_role_and_shared_scope():
    with pytest.raises(PermissionDenied):
        service().create(ctx('SHOPPER'), make_create(), demo_session(), demo_catalog())
    with pytest.raises(NotFoundError):
        service(allowed=False).create(ctx(), make_create(), demo_session(), demo_catalog())
    with pytest.raises(NotFoundError):
        service().create(ctx(tenant='other'), make_create(), demo_session(), demo_catalog())


def test_create_rejects_unknown_variants():
    create = make_create()
    selections = [ItemRef(slot='BOTTOM', refType='VARIANT', refId='variant-missing')
                  if ref.slot == 'BOTTOM' else ref for ref in create.selections]
    create = create.model_copy(update={'selections': selections})
    with pytest.raises(InvalidRequestError):
        service().create(ctx(), create, demo_session(), demo_catalog())


def test_replacing_a_lock_requires_a_lock_replacement_exception():
    with pytest.raises(InvalidRequestError):
        service().create(ctx(), make_create(catalog_top=True), demo_session(), demo_catalog())
    create = make_create(catalog_top=True, exceptions=[{
        'exceptionId': str(LOCK_ID), 'kind': 'LOCK_REPLACEMENT', 'target': 'owned-top-1',
        'description': 'Shopper approved trying a catalog top instead.'}])
    proposal = service().create(ctx(), create, demo_session(), demo_catalog())
    assert proposal.exceptions[0].kind == 'LOCK_REPLACEMENT'


def test_session_advance_marks_proposal_outdated():
    broker_service = service()
    proposal = broker_service.create(ctx(), make_create(), demo_session(), demo_catalog())
    current = demo_session(version=2)
    assert broker_service.get(ctx(), proposal.proposalId, current).status == 'OUTDATED'
    assert broker_service.get(ctx(), proposal.proposalId,
                              demo_session()).status == 'PROPOSAL_READY'


def test_application_needs_every_exception_approved_and_current_versions():
    create = make_create(catalog_top=True, exceptions=[{
        'exceptionId': str(LOCK_ID), 'kind': 'LOCK_REPLACEMENT', 'target': 'owned-top-1',
        'description': 'Approved swap.'}])
    proposal_service = service()
    proposal = proposal_service.create(ctx(), create, demo_session(), demo_catalog())
    partial = ProposalApply.model_validate({'expectedSessionVersion': 1,
                                            'approvedExceptionIds': [], 'accept': True})
    with pytest.raises(InvalidRequestError):
        proposal_service.validate_application(proposal, demo_session(), partial,
                                              demo_catalog())
    approved = ProposalApply.model_validate({
        'expectedSessionVersion': 1, 'approvedExceptionIds': [str(LOCK_ID)], 'accept': True})
    applied = proposal_service.validate_application(proposal, demo_session(), approved,
                                                    demo_catalog())
    assert [ref.refId for ref in applied] == ['variant-top-1', 'variant-bottom-1',
                                              'variant-shoes-1']
    stale = ProposalApply.model_validate({'expectedSessionVersion': 7,
                                          'approvedExceptionIds': [str(LOCK_ID)],
                                          'accept': True})
    with pytest.raises(StaleSessionError):
        proposal_service.validate_application(proposal, demo_session(), stale,
                                              demo_catalog())


def test_application_revalidates_references_against_current_catalog():
    proposal_service = service()
    proposal = proposal_service.create(ctx(), make_create(), demo_session(), demo_catalog())
    withdrawn = [v.model_copy(update={'published': False})
                 if v.variantId == 'variant-shoes-1' else v
                 for v in demo_catalog().variants]
    apply = ProposalApply.model_validate({'expectedSessionVersion': 1,
                                          'approvedExceptionIds': [], 'accept': True})
    with pytest.raises(InvalidRequestError):
        proposal_service.validate_application(proposal, demo_session(), apply,
                                              demo_catalog().model_copy(
                                                  update={'variants': withdrawn}))


def test_refresh_is_separate_from_apply_and_revalidates():
    proposal_service = service()
    proposal = proposal_service.create(ctx(), make_create(), demo_session(), demo_catalog())
    refresh = ProposalRefresh.model_validate({'expectedSessionVersion': 1,
                                              'expectedConsentRevision': 1,
                                              'requestAdviceOnly': True})
    ack = proposal_service.refresh(ctx(), proposal.proposalId, refresh, demo_session())
    assert ack.status == 'ACCEPTED'
    stale = ProposalRefresh.model_validate({'expectedSessionVersion': 5,
                                            'expectedConsentRevision': 1,
                                            'requestAdviceOnly': True})
    with pytest.raises(StaleSessionError):
        proposal_service.refresh(ctx(), proposal.proposalId, stale, demo_session())
    wrong_consent = ProposalRefresh.model_validate({'expectedSessionVersion': 1,
                                                    'expectedConsentRevision': 9,
                                                    'requestAdviceOnly': True})
    with pytest.raises(StaleSessionError):
        proposal_service.refresh(ctx(), proposal.proposalId, wrong_consent, demo_session())


def test_recorded_outcome_is_sticky():
    proposal_service = service()
    proposal = proposal_service.create(ctx(), make_create(), demo_session(), demo_catalog())
    proposal_service.record_outcome(proposal.proposalId, accepted=True)
    assert proposal_service.get(ctx(), proposal.proposalId,
                                demo_session()).status == 'ACCEPTED'
