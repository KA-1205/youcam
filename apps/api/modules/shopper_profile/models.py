"""Profile persistence: consent revisions, preferences and wardrobe provenance.

Consent revisions are append-only; the latest revision is authoritative and every
write compares against the expected revision. Wardrobe stores independent saved
flags and manual ownership; ordered contributions arrive via commerce events.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ProfileBase(DeclarativeBase):
    pass


class ConsentRevision(ProfileBase):
    __tablename__ = 'consent_revisions'
    __table_args__ = (UniqueConstraint('actor_id', 'revision', name='uq_consent_revision'),)

    actor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    controls: Mapped[dict] = mapped_column('controls_json', type_=JSON)
    processors: Mapped[list] = mapped_column('processors_json', type_=JSON)
    asset_ids: Mapped[list] = mapped_column('asset_ids_json', type_=JSON)
    adult_attestation: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WardrobeItem(ProfileBase):
    __tablename__ = 'wardrobe_items'
    __table_args__ = (UniqueConstraint('account_id', 'ref_type', 'ref_id',
                                       name='uq_wardrobe_reference'),)

    wardrobe_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    ref_type: Mapped[str] = mapped_column(String(16))
    ref_id: Mapped[str] = mapped_column(String(128))
    slot: Mapped[str] = mapped_column(String(16))
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_owned_quantity: Mapped[int] = mapped_column(Integer, default=0)
    attributes_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    provenance: Mapped[list] = mapped_column('provenance_json', type_=JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrderLineContribution(ProfileBase):
    """Per-order-line quantity contributions; owned conversion happens on delivery events."""

    __tablename__ = 'wardrobe_contributions'

    order_line_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    ref_type: Mapped[str] = mapped_column(String(16))
    ref_id: Mapped[str] = mapped_column(String(128))
    slot: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16))  # ORDERED or OWNED
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CommerceEventRecord(ProfileBase):
    """Deduplicated event log; conflicting duplicate content raises an integrity error."""

    __tablename__ = 'commerce_events'

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    order_version: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(32))
    fingerprint: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrderProgressRecord(ProfileBase):
    """Tracks the highest applied order version so out-of-order events wait for predecessors."""

    __tablename__ = 'order_progress'

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    applied_version: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
