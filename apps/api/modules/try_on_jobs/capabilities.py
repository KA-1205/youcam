"""Capability readiness and the provider activation evidence register.

Every capability starts NOT_TESTED. Live activation requires a recorded
activation entry: account region, console, base URL, auth method, feature
version, tested input requirements, success/error fixture references, cost and
rate limits, retention and deletion behaviour, date and responsible verifier.
Even with a recorded entry, liveEnabled stays false until credentials and cost
guards are verified — this branch never turns live mode on.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from apps.api import clock
from contracts.runtime.models import Capability, CapabilityPage, CapabilityState

CAPABILITY_IDS: list[Capability] = ['CLOTHES_V4', 'MAKEUP', 'EARRINGS', 'NECKLACE', 'RING',
                                    'BRACELET', 'WATCH', 'HAIR_COLOR', 'FACIAL_COLOR_TONES',
                                    'COMBINED']


class ActivationBase(DeclarativeBase):
    pass


class ProviderActivationRow(ActivationBase):
    __tablename__ = 'provider_activations'

    capability: Mapped[str] = mapped_column(String(32), primary_key=True)
    region: Mapped[str] = mapped_column(String(64))
    base_url: Mapped[str] = mapped_column(String(200))
    auth_method: Mapped[str] = mapped_column(String(64))
    feature_version: Mapped[str] = mapped_column(String(64))
    evidence: Mapped[dict] = mapped_column('evidence_json', type_=JSON)
    verified_by: Mapped[str] = mapped_column(String(128))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def capability_page(db: Session | None = None) -> CapabilityPage:
    verified: set[str] = set()
    if db is not None:
        verified = {row.capability for row in db.scalars(select(ProviderActivationRow))}
    return CapabilityPage(items=[
        CapabilityState(capability=capability,
                        state='VERIFIED' if capability in verified else 'NOT_TESTED',
                        liveEnabled=False,  # credentials and cost guards stay unverified here
                        evidenceId=capability if capability in verified else None)
        for capability in CAPABILITY_IDS])


def record_activation(db: Session, capability: Capability, region: str, base_url: str,
                      auth_method: str, feature_version: str, evidence: dict,
                      verified_by: str) -> None:
    row = db.get(ProviderActivationRow, capability)
    now = clock.now()
    if row is None:
        db.add(ProviderActivationRow(capability=capability, region=region, base_url=base_url,
                                     auth_method=auth_method, feature_version=feature_version,
                                     evidence=evidence, verified_by=verified_by, verified_at=now))
    else:
        row.region = region
        row.base_url = base_url
        row.auth_method = auth_method
        row.feature_version = feature_version
        row.evidence = evidence
        row.verified_by = verified_by
        row.verified_at = now
    db.flush()
