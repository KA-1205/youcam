"""A07 merchant catalog tools: CSV/JSON ingest, staging diff, overrides, publish gate."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from contracts.runtime.models import AccessContext, CatalogBatch, CatalogVariant, PublishStage
from services.catalog.demo import to_variant
from services.catalog.errors import InvalidRequestError, NotFoundError, StaleCatalogError
from services.catalog.staging import CatalogStaging
from services.catalog.store import CatalogStore

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
DEMO = 'demo-anchor-fit'


def ctx() -> AccessContext:
    return AccessContext(actorId='merchant-1', tenantId=DEMO, roles=['MERCHANT_ADMIN'],
                         verifiedAccount=True, consentRevision=1)


def make_store() -> CatalogStore:
    payload = json.loads(Path('reference/Anchor-Fit-Final-v3.3/demo-catalog.json')
                         .read_text(encoding='utf-8'))
    variants = [to_variant(row, source_version='fixture-v1', now=T0)
                for row in payload['variants']]
    return CatalogStore(variants, now=lambda: T0)


def staging() -> CatalogStaging:
    return CatalogStaging(make_store())


def batch_row(vid: str, slot: str = 'TOP', *, price: int | None = 52000,
              stock: int | None = 3, brand: str = 'OWN', published: bool = True,
              product: str = 'product-top-9') -> dict:
    return {'tenantId': DEMO, 'productId': product, 'variantId': vid, 'brandKind': brand,
            'brandName': 'Anchor Demo', 'slot': slot, 'priceMinor': price,
            'currency': 'INR', 'stock': stock, 'published': published, 'options': {},
            'attributes': {}, 'imageId': None, 'previewStatus': 'UNVERIFIED_ASSET',
            'isSynthetic': True}


def publish(expected_source_version: str) -> PublishStage:
    return PublishStage.model_validate({'expectedSourceVersion': expected_source_version,
                                        'approvePublication': True})


def make_batch(version: str = 'src-2026-10-30-a', rows: list[dict] | None = None) \
        -> CatalogBatch:
    rows = rows if rows is not None else [batch_row('variant-top-9')]
    return CatalogBatch(sourceId='merchant-feed', sourceVersion=version,
                        variants=[CatalogVariant.model_validate({
                            **row, 'sourceVersion': version, 'checkedAt': T0,
                            'expiresAt': T0 + timedelta(minutes=15)}) for row in rows])


CSV_HEADER = ('tenantId,productId,variantId,brandKind,brandName,slot,priceMinor,currency,'
              'stock,published,options,attributes,imageId,previewStatus')
CSV_OK = (CSV_HEADER + '\n'
          f'{DEMO},product-top-9,variant-top-9,OWN,Anchor Demo,TOP,52000,INR,3,true,,,,'
          'UNVERIFIED_ASSET\n')
CSV_BAD_ROW = (CSV_HEADER + '\n'
               f'{DEMO},product-top-9,variant-top-9,OWN,Anchor Demo,NOT_A_SLOT,52000,INR,3,'
               'true,,,,UNVERIFIED_ASSET\n')


def test_json_ingest_stages_diff_without_touching_the_store():
    store = make_store()
    service = CatalogStaging(store)
    stage = service.ingest_json(make_batch())
    assert stage.errors == []
    assert stage.changedVariantIds == ['variant-top-9']
    assert stage.published is False
    with pytest.raises(NotFoundError):
        store.variant(ctx(), 'variant-top-9')


def test_publish_gate_applies_approved_stage_and_bumps_version():
    service = staging()
    stage = service.ingest_json(make_batch())
    before = service.store.list_variants(ctx(), None, 100).catalogVersion
    service.publish(stage.stageId, publish('src-2026-10-30-a'))
    page = service.store.list_variants(ctx(), None, 100)
    assert 'variant-top-9' in {v.variantId for v in page.items}
    assert page.catalogVersion != before


def test_publish_rejects_wrong_expected_source_version_and_double_publish():
    service = staging()
    stage = service.ingest_json(make_batch())
    with pytest.raises(StaleCatalogError):
        service.publish(stage.stageId, publish('src-2026-10-30-older'))
    service.publish(stage.stageId, publish('src-2026-10-30-a'))
    with pytest.raises(InvalidRequestError):
        service.publish(stage.stageId, publish('src-2026-10-30-a'))


def test_conflicting_duplicates_are_rejected_as_stage_errors():
    service = staging()
    rows = [batch_row('variant-top-9', price=52000),
            batch_row('variant-top-9', price=61000, product='product-other')]
    stage = service.ingest_json(make_batch(rows=rows))
    codes = [error.code for error in stage.errors]
    assert codes == ['DUPLICATE_VARIANT']
    assert stage.changedVariantIds == ['variant-top-9']
    with pytest.raises(InvalidRequestError):
        service.publish(stage.stageId, publish('src-2026-10-30-a'))


def test_brand_kind_changes_on_existing_variants_are_blocked():
    service = staging()
    rows = [batch_row('variant-top-1', brand='SPONSOR', product='product-top-1')]
    stage = service.ingest_json(make_batch(rows=rows))
    assert [error.code for error in stage.errors] == ['BRAND_KIND_CONFLICT']


def test_unknown_price_and_out_of_stock_ingest_as_null_states():
    service = staging()
    rows = [batch_row('variant-top-9', price=None, stock=None)]
    stage = service.ingest_json(make_batch(rows=rows))
    assert stage.errors == []
    service.publish(stage.stageId, publish('src-2026-10-30-a'))
    stored = service.store.variant(ctx(), 'variant-top-9')
    assert stored.priceMinor is None and stored.stock is None  # never fabricated zero


def test_csv_ingest_parses_rows_and_reports_malformed_ones():
    service = staging()
    ok = service.ingest_csv(CSV_OK, source_id='merchant-feed',
                            source_version='csv-1')
    assert ok.errors == [] and ok.changedVariantIds == ['variant-top-9']
    bad = service.ingest_csv(CSV_BAD_ROW, source_id='merchant-feed',
                             source_version='csv-2')
    assert [error.code for error in bad.errors] == ['CSV_ROW_INVALID']
    assert bad.errors[0].details.get('row') == '2'


def test_merchant_overrides_survive_source_updates():
    service = staging()
    service.set_override(DEMO, 'variant-top-1', {'brandName': 'Merchant Label'})
    rows = [batch_row('variant-top-1', price=49000, product='product-top-1')]
    stage = service.ingest_json(make_batch(rows=rows))
    service.publish(stage.stageId, publish('src-2026-10-30-a'))
    stored = service.store.variant(ctx(), 'variant-top-1')
    assert stored.brandName == 'Merchant Label'  # override wins
    assert stored.priceMinor == 49000  # source-owned field updated


def test_override_field_names_are_validated():
    service = staging()
    with pytest.raises(InvalidRequestError):
        service.set_override(DEMO, 'variant-top-1', {'priceMinor': 1})


def test_reingesting_a_seen_source_version_is_a_freshness_error():
    service = staging()
    service.ingest_json(make_batch(version='src-a'))
    with pytest.raises(StaleCatalogError):
        service.ingest_json(make_batch(version='src-a'))
    newer = service.ingest_json(make_batch(version='src-b'))
    assert newer.errors == []
