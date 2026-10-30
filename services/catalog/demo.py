"""Read-only demo catalog loader; original fixtures are never modified."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from contracts.runtime.models import CatalogVariant

from .store import FRESHNESS


def load_demo_catalog(payload: dict[str, Any], *, now: datetime) \
        -> tuple[list[CatalogVariant], list[dict[str, Any]]]:
    """Map the supplied demo-catalog.json structure onto frozen v1 DTOs.

    Fixture keys outside the DTO (notes, stockAgeSeconds) are informational only.
    checkedAt/expiresAt come from the injected clock; the source version tracks
    the fixture version so freshness can be reasoned about deterministically.
    """
    source_version = f"fixture-v{payload.get('fixtureVersion', 1)}"
    variants = [to_variant(row, source_version=source_version, now=now)
                for row in payload.get('variants', [])]
    owned = [dict(item) for item in payload.get('ownedItems', [])]
    return variants, owned


def to_variant(row: dict[str, Any], *, source_version: str, now: datetime) -> CatalogVariant:
    return CatalogVariant(
        tenantId=row['tenantId'],
        productId=row['productId'],
        variantId=row['variantId'],
        brandKind=row['brandKind'],
        brandName=row['brandName'],
        slot=row['slot'],
        priceMinor=row.get('priceMinor'),
        currency=row.get('currency', 'INR'),
        stock=row.get('stock'),
        published=row.get('published', True),
        options=dict(row.get('options', {})),
        attributes=dict(row.get('attributes', {})),
        imageId=row.get('imageId'),
        previewStatus=row.get('previewStatus', 'UNVERIFIED_ASSET'),
        sourceVersion=source_version,
        checkedAt=now,
        expiresAt=now + FRESHNESS,
        isSynthetic=bool(row.get('isSynthetic', True)),
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
