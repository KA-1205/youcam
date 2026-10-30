"""ProfilePort implementation: consent CAS, wardrobe provenance and event application.

Wardrobe display aggregates three independent sources: per-order-line contributions
(ORDERED until DELIVERED, OWNED afterwards), manual ownership and the saved flag.
Order-version progression is enforced so out-of-order events wait for predecessors.
"""
import base64
import hashlib
import json
from collections.abc import Callable
from typing import Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api import clock
from apps.api.errors import SCOPE_FORBIDDEN, STALE_VERSION, ApiError
from apps.api.modules.shopper_profile.models import (
    CommerceEventRecord,
    ConsentRevision,
    OrderLineContribution,
    OrderProgressRecord,
    WardrobeItem,
)
from contracts.runtime.models import (
    CommerceEvent,
    ConsentControls,
    ConsentSnapshot,
    ItemRef,
    ProfileSnapshot,
    Slot,
    WardrobePage,
)
from contracts.runtime.models import WardrobeItem as WardrobeItemDTO

RefType = Literal['VARIANT', 'OWNED']

CONTROL_KEYS = ('processPhotos', 'savePhotosAndRenders', 'shareWithStylist', 'researchUse',
                'notifications', 'saveAddress', 'savePaymentToken')


def default_controls() -> dict[str, bool]:
    return {key: False for key in CONTROL_KEYS}


def _item_row(row: WardrobeItem, ordered: int, owned: int) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        wardrobeId=UUID(row.wardrobe_id),
        reference=ItemRef(slot=cast(Slot, row.slot), refType=cast(RefType, row.ref_type),
                          refId=row.ref_id),
        saved=row.saved, orderedQuantity=ordered, ownedQuantity=owned,
        manualOwnedQuantity=row.manual_owned_quantity, provenance=row.provenance)


class ProfileService:
    """Implements the frozen ProfilePort; wardrobe requires a verified account.

    Commerce events carry variant IDs only, so a catalog-backed slot resolver is
    injected at composition; events are rejected (retried by the worker) if the
    variant is unknown rather than recorded with a guessed slot.
    """

    def __init__(self, resolve_slot: Callable[[str], str] | None = None) -> None:
        self._resolve_slot = resolve_slot

    def ensure_actor_consent(self, db: Session, actor_id: str) -> None:
        if db.get(ConsentRevision, (actor_id, 1)) is None:
            db.add(ConsentRevision(actor_id=actor_id, revision=1, controls=default_controls(),
                                   processors=[], asset_ids=[], adult_attestation=False,
                                   created_at=clock.now()))
            db.flush()

    def latest_revision(self, db: Session, actor_id: str) -> int:
        row = db.scalar(select(ConsentRevision.revision)
                        .where(ConsentRevision.actor_id == actor_id)
                        .order_by(ConsentRevision.revision.desc()).limit(1))
        return int(row) if row is not None else 0

    def consent_snapshot(self, db: Session, actor_id: str) -> ConsentSnapshot:
        row = db.scalar(select(ConsentRevision)
                        .where(ConsentRevision.actor_id == actor_id)
                        .order_by(ConsentRevision.revision.desc()).limit(1))
        if row is None:
            raise ApiError(404, 'NOT_FOUND', 'No consent recorded for this actor.')
        return ConsentSnapshot(consentRevision=row.revision,
                               controls=ConsentControls(**row.controls),
                               processors=row.processors,
                               assetIds=[UUID(value) for value in row.asset_ids])

    def update_consent(self, db: Session, actor_id: str, expected_revision: int,
                       controls: dict[str, bool], processors: list[str], asset_ids: list[str],
                       adult_attestation: bool) -> ConsentSnapshot:
        current = self.latest_revision(db, actor_id)
        if expected_revision != current:
            raise ApiError(409, STALE_VERSION, 'Consent changed; review the current controls.')
        if (controls.get('processPhotos') or processors) and not adult_attestation:
            raise ApiError(422, 'VALIDATION_ERROR',
                           'Photo processing requires adult attestation.')
        next_revision = current + 1
        db.add(ConsentRevision(actor_id=actor_id, revision=next_revision, controls=dict(controls),
                               processors=list(processors), asset_ids=list(asset_ids),
                               adult_attestation=adult_attestation, created_at=clock.now()))
        db.flush()
        return ConsentSnapshot(consentRevision=next_revision, controls=ConsentControls(**controls),
                               processors=list(processors),
                               assetIds=[UUID(value) for value in asset_ids])

    def snapshot(self, db: Session, actor_id: str, tenant_id: str, preferences: dict[str, str],
                 account_id: str | None) -> ProfileSnapshot:
        owned = self._owned_items(db, account_id) if account_id else []
        return ProfileSnapshot(actorId=actor_id, tenantId=tenant_id, preferences=preferences,
                               consent=self.consent_snapshot(db, actor_id), ownedItems=owned)

    def _owned_items(self, db: Session, account_id: str) -> list[ItemRef]:
        rows = db.scalars(select(OrderLineContribution)
                          .where(OrderLineContribution.account_id == account_id,
                                 OrderLineContribution.state == 'OWNED'))
        return [ItemRef(slot=cast(Slot, row.slot), refType=cast(RefType, row.ref_type),
                        refId=row.ref_id) for row in rows]

    def require_account(self, account_id: str | None) -> str:
        if account_id is None:
            raise ApiError(403, SCOPE_FORBIDDEN, 'Wardrobe persistence requires a verified account.')
        return account_id

    def save_wardrobe(self, db: Session, account_id: str, reference: ItemRef, saved: bool,
                      manual_owned_quantity: int, attributes_confirmed: bool) -> WardrobeItemDTO:
        row = db.scalar(select(WardrobeItem).where(
            WardrobeItem.account_id == account_id, WardrobeItem.ref_type == reference.refType,
            WardrobeItem.ref_id == reference.refId))
        if row is None:
            row = WardrobeItem(wardrobe_id=str(uuid4()), account_id=account_id,
                               ref_type=reference.refType, ref_id=reference.refId,
                               slot=reference.slot, saved=saved,
                               manual_owned_quantity=manual_owned_quantity,
                               attributes_confirmed=attributes_confirmed,
                               provenance=['MANUAL'] if manual_owned_quantity else [],
                               created_at=clock.now(), updated_at=clock.now())
            db.add(row)
        else:
            row.saved = saved
            row.manual_owned_quantity = manual_owned_quantity
            row.attributes_confirmed = attributes_confirmed
            if manual_owned_quantity and 'MANUAL' not in row.provenance:
                row.provenance = [*row.provenance, 'MANUAL']
            row.updated_at = clock.now()
        db.flush()
        ordered, owned = self._contribution_totals(db, account_id, reference)
        return _item_row(row, ordered, owned)

    def list_wardrobe(self, db: Session, account_id: str, cursor: str | None,
                      limit: int) -> WardrobePage:
        rows = db.scalars(select(WardrobeItem).where(WardrobeItem.account_id == account_id)
                          .order_by(WardrobeItem.wardrobe_id)).all()
        by_reference = {(row.ref_type, row.ref_id): row for row in rows}
        contributions = db.scalars(select(OrderLineContribution)
                                   .where(OrderLineContribution.account_id == account_id)
                                   .order_by(OrderLineContribution.order_line_id)).all()
        for contribution in contributions:
            key = (contribution.ref_type, contribution.ref_id)
            if key not in by_reference:
                by_reference[key] = WardrobeItem(
                    wardrobe_id=str(uuid5(NAMESPACE_URL, f'wc:{contribution.order_line_id}')),
                    account_id=account_id,
                    ref_type=contribution.ref_type, ref_id=contribution.ref_id,
                    slot=contribution.slot, saved=False, manual_owned_quantity=0,
                    attributes_confirmed=False, provenance=[contribution.order_id],
                    created_at=contribution.updated_at, updated_at=contribution.updated_at)
        ordered_all: dict[tuple[str, str], int] = {}
        owned_all: dict[tuple[str, str], int] = {}
        for contribution in contributions:
            key = (contribution.ref_type, contribution.ref_id)
            if contribution.state == 'ORDERED':
                ordered_all[key] = ordered_all.get(key, 0) + contribution.quantity
            elif contribution.state == 'OWNED':
                owned_all[key] = owned_all.get(key, 0) + contribution.quantity
                if contribution.order_id not in by_reference[key].provenance:
                    by_reference[key].provenance = [*by_reference[key].provenance,
                                                    contribution.order_id]
        entries = [_item_row(row, ordered_all.get((row.ref_type, row.ref_id), 0),
                             owned_all.get((row.ref_type, row.ref_id), 0))
                   for row in sorted(by_reference.values(),
                                     key=lambda item: (item.created_at, item.wardrobe_id))
                   if _visible(row, ordered_all, owned_all)]
        if cursor:
            after_position = _decode_cursor(cursor)
            entries = entries[after_position:]
        page = entries[:limit]
        next_cursor = _encode_cursor(limit) if len(entries) > limit else None
        return WardrobePage(items=page, nextCursor=next_cursor)

    def _contribution_totals(self, db: Session, account_id: str, reference: ItemRef) -> tuple[int, int]:
        rows = db.scalars(select(OrderLineContribution).where(
            OrderLineContribution.account_id == account_id,
            OrderLineContribution.ref_type == reference.refType,
            OrderLineContribution.ref_id == reference.refId))
        ordered = sum(row.quantity for row in rows if row.state == 'ORDERED')
        owned = sum(row.quantity for row in rows if row.state == 'OWNED')
        return ordered, owned

    def consume_commerce_event(self, db: Session, account_id: str, event: CommerceEvent) -> None:
        """Deduplicate by eventId; conflicting duplicate content is an integrity error."""
        fingerprint = hashlib.sha256(json.dumps(
            {'order': str(event.orderId), 'version': event.orderVersion, 'type': event.type,
             'mode': event.mode,
             'lines': [[line.orderLineId, line.variantId, line.quantity] for line in event.lines]},
            sort_keys=True).encode()).hexdigest()
        existing = db.get(CommerceEventRecord, str(event.eventId))
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise ApiError(409, 'EVENT_CONFLICT',
                               'Duplicate event content differs; refusing ambiguous application.')
            return
        progress = db.get(OrderProgressRecord, str(event.orderId))
        applied = progress.applied_version if progress is not None else 0
        if event.orderVersion != applied + 1:
            raise ApiError(409, 'EVENT_OUT_OF_ORDER',
                           'Waiting for missing order version predecessors.')
        for line in event.lines:
            if event.type == 'ORDERED':
                db.add(OrderLineContribution(
                    order_line_id=str(line.orderLineId), account_id=account_id,
                    order_id=str(event.orderId), ref_type='VARIANT', ref_id=line.variantId,
                    slot=self._slot_for(line.variantId), quantity=line.quantity, state='ORDERED',
                    updated_at=clock.now()))
            elif event.type == 'DELIVERED':
                contribution = db.get(OrderLineContribution, str(line.orderLineId))
                if contribution is not None:
                    contribution.state = 'OWNED'
                    contribution.updated_at = clock.now()
            elif event.type in ('CANCELLED', 'RETURN_RECEIVED'):
                contribution = db.get(OrderLineContribution, str(line.orderLineId))
                if contribution is not None:
                    db.delete(contribution)
            elif event.type == 'REFUNDED':
                contribution = db.get(OrderLineContribution, str(line.orderLineId))
                if contribution is not None and contribution.state == 'ORDERED':
                    db.delete(contribution)
        db.add(CommerceEventRecord(event_id=str(event.eventId), account_id=account_id,
                                   order_id=str(event.orderId), order_version=event.orderVersion,
                                   event_type=event.type, fingerprint=fingerprint,
                                   received_at=clock.now()))
        if progress is None:
            db.add(OrderProgressRecord(order_id=str(event.orderId), account_id=account_id,
                                       applied_version=event.orderVersion, updated_at=clock.now()))
        else:
            progress.applied_version = event.orderVersion
            progress.updated_at = clock.now()
        db.flush()


    def _slot_for(self, variant_id: str) -> str:
        if self._resolve_slot is None:
            raise ApiError(409, 'EVENT_OUT_OF_ORDER',
                           'Catalog slot resolution is not wired for commerce events.')
        return self._resolve_slot(variant_id)


def _visible(row: WardrobeItem, ordered: dict, owned: dict) -> bool:
    key = (row.ref_type, row.ref_id)
    # Hide empty unsaved records; keep anything with a contribution, saved flag or manual count.
    return bool(row.saved or row.manual_owned_quantity or ordered.get(key) or owned.get(key))


def _encode_cursor(position: int) -> str:
    return base64.urlsafe_b64encode(str(position).encode()).decode()


def _decode_cursor(cursor: str) -> int:
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        raise ApiError(422, 'VALIDATION_ERROR', 'Malformed pagination cursor.')
