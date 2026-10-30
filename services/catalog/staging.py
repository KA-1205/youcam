"""Merchant catalog tools (A07): CSV/JSON ingest, staging diff, publish gate.

Staging never mutates the read store. Duplicate conflicts and brand-kind
changes fail as stage errors; a failed sync retains the prior snapshot and
freshness timestamp. Merchant overrides survive source updates, and
publication requires the exact expected source version.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from contracts.runtime.models import (
    Ack,
    CatalogBatch,
    CatalogStage,
    CatalogVariant,
    ErrorDetail,
    PublishStage,
)

from .errors import InvalidRequestError, NotFoundError, StaleCatalogError
from .store import CatalogStore

CSV_COLUMNS = ('tenantId', 'productId', 'variantId', 'brandKind', 'brandName', 'slot',
               'priceMinor', 'currency', 'stock', 'published', 'options', 'attributes',
               'imageId', 'previewStatus')


@dataclass
class _Stage:
    stage_id: UUID
    source_id: str
    source_version: str
    variants: list[CatalogVariant]
    changed: list[str]
    errors: list[ErrorDetail]
    applied: bool = False
    audit: list[str] = field(default_factory=list)


class CatalogStaging:
    def __init__(self, store: CatalogStore) -> None:
        self.store = store
        self._stages: dict[UUID, _Stage] = {}
        self._seen_versions: dict[str, set[str]] = {}
        self._csv_source_version: str = '' 

    # -- ingest --------------------------------------------------------------
    def ingest_json(self, batch: CatalogBatch) -> CatalogStage:
        seen = self._seen_versions.setdefault(batch.sourceId, set())
        if batch.sourceVersion in seen:
            raise StaleCatalogError('This source version was already ingested.')
        kept: dict[str, CatalogVariant] = {}
        errors: list[ErrorDetail] = []
        for variant in batch.variants:
            existing = kept.get(variant.variantId)
            if existing is not None:
                if existing.model_dump() != variant.model_dump():
                    errors.append(ErrorDetail(
                        code='DUPLICATE_VARIANT',
                        message='Conflicting duplicate variant in the same batch.',
                        details={'variantId': variant.variantId}))
                continue
            stored = self.store.find(variant.tenantId, variant.variantId)
            if stored is not None and stored.brandKind != variant.brandKind:
                errors.append(ErrorDetail(
                    code='BRAND_KIND_CONFLICT',
                    message='Sponsor placement changes require a separate operation.',
                    details={'variantId': variant.variantId}))
                continue
            kept[variant.variantId] = variant
        variants = list(kept.values())
        changed = [v.variantId for v in variants
                   if self._changed(self.store.find(v.tenantId, v.variantId), v)]
        stage = _Stage(stage_id=uuid4(), source_id=batch.sourceId,
                       source_version=batch.sourceVersion, variants=variants,
                       changed=changed, errors=errors)
        self._stages[stage.stage_id] = stage
        if not errors:
            seen.add(batch.sourceVersion)
        return self._envelope(stage)

    def ingest_csv(self, text: str, *, source_id: str, source_version: str) -> CatalogStage:
        self._csv_source_version = source_version
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None or not set(CSV_COLUMNS) <= set(reader.fieldnames):
            raise InvalidRequestError('CSV header is missing required columns.',
                                      code='CSV_HEADER_INVALID')
        checked_at, expires_at = self.store.observation()
        rows: list[CatalogVariant] = []
        errors: list[ErrorDetail] = []
        for number, raw in enumerate(reader, start=2):
            try:
                parsed = self._csv_row(raw)
                rows.append(CatalogVariant.model_validate({
                    **parsed, 'sourceVersion': source_version, 'checkedAt': checked_at,
                    'expiresAt': expires_at, 'isSynthetic': False}))
            except (ValueError, KeyError):
                errors.append(ErrorDetail(
                    code='CSV_ROW_INVALID', message='A CSV row did not parse or validate.',
                    details={'row': str(number)}))
        if errors:
            stage = _Stage(stage_id=uuid4(), source_id=source_id,
                           source_version=source_version, variants=[], changed=[],
                           errors=errors)
            self._stages[stage.stage_id] = stage
            return self._envelope(stage)
        return self.ingest_json(CatalogBatch(sourceId=source_id,
                                             sourceVersion=source_version,
                                             variants=rows))

    def publish(self, stage_id: UUID, publish: PublishStage) -> Ack:
        stage = self._stages.get(stage_id)
        if stage is None:
            raise NotFoundError('Unknown staging batch.')
        if stage.applied:
            raise InvalidRequestError('This staging batch was already published.')
        if stage.errors:
            raise InvalidRequestError('Staging errors must be resolved before publication.',
                                      code='STAGE_HAS_ERRORS')
        if publish.expectedSourceVersion != stage.source_version \
                or stage.source_version not in self._seen_versions.get(stage.source_id,
                                                                       set()):
            raise StaleCatalogError('The source moved on; restage before publishing.')
        self.store.apply_variants(stage.variants)
        stage.applied = True
        stage.audit.append(f'published source {stage.source_version}')
        return Ack(requestId=uuid4(), status='ACCEPTED')

    def set_override(self, tenant_id: str, variant_id: str, fields: dict[str, Any]) -> None:
        self.store.set_override(tenant_id, variant_id, fields)

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _changed(stored: CatalogVariant | None, incoming: CatalogVariant) -> bool:
        if stored is None:
            return True
        return stored.model_dump() != incoming.model_dump()

    @staticmethod
    def _csv_row(raw: dict[str, str]) -> dict[str, Any]:
        def number(field: str) -> int | None:
            value = (raw.get(field) or '').strip()
            return int(value) if value else None

        def pairs(field: str) -> dict[str, str]:
            value = (raw.get(field) or '').strip()
            if not value:
                return {}
            result: dict[str, str] = {}
            for chunk in value.split(';'):
                key, _, item = chunk.partition('=')
                if not key or not item:
                    raise ValueError('malformed pair')
                result[key] = item
            return result

        published = (raw.get('published') or '').strip().casefold()
        return {
            'tenantId': raw['tenantId'], 'productId': raw['productId'],
            'variantId': raw['variantId'], 'brandKind': raw['brandKind'],
            'brandName': raw['brandName'], 'slot': raw['slot'],
            'priceMinor': number('priceMinor'), 'currency': raw.get('currency') or 'INR',
            'stock': number('stock'), 'published': published == 'true',
            'options': pairs('options'), 'attributes': pairs('attributes'),
            'imageId': (raw.get('imageId') or '').strip() or None,
            'previewStatus': raw.get('previewStatus') or 'UNVERIFIED_ASSET',
        }

    @staticmethod
    def _envelope(stage: _Stage) -> CatalogStage:
        return CatalogStage(stageId=stage.stage_id, sourceVersion=stage.source_version,
                            changedVariantIds=list(stage.changed),
                            errors=list(stage.errors))
