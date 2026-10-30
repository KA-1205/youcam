"""C06 acceptance: file upload, task deletion, credit ops with distinct auth,
facial color tones gating and 24h cost freshness."""
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.errors import ApiError
from apps.api.modules.try_on_jobs.costs import COST_STALENESS, CostService
from apps.api.modules.try_on_jobs.providers.utility import FacialColorTonesAdapter, UtilityClient


def captured_requests():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == 'POST' and request.url.path == '/s2s/v2.0/file':
            return httpx.Response(200, json={'fileId': 'file-9',
                                             'uploadUrl': 'https://fixture.anchor-fit.invalid/up'})
        if request.method == 'GET' and request.url.path == '/s2s/v2.0/credit/feature-cost':
            return httpx.Response(200, json={'featureName': request.url.params['featureName'],
                                             'cost': 3})
        if request.method == 'GET' and request.url.path == '/s2s/v2.0/credit/balance':
            return httpx.Response(200, json={'balance': 4242})
        if request.method == 'GET' and request.url.path == '/s2s/v1.0/client/credit/history':
            return httpx.Response(200, json={'entries': [{'taskId': 't', 'units': 2}]})
        return httpx.Response(200, json={'ok': True})

    return UtilityClient(mode='FIXTURE', transport=httpx.MockTransport(handler)), requests


def test_file_upload_two_step_flow():
    client, requests = captured_requests()
    file_id = client.create_file(b'image-bytes', 'image/jpeg')
    assert file_id == 'file-9'
    methods = [request.method for request in requests]
    assert methods == ['POST', 'PUT']
    assert requests[1].read() == b'image-bytes'
    assert requests[1].headers['content-type'] == 'image/jpeg'


def test_task_deletion_is_documented_for_finished_tasks():
    client, requests = captured_requests()
    client.delete_task('task-1')
    assert requests[0].url.path == '/s2s/v2.0/task/delete'
    assert requests[0].read() == b'{"taskId": "task-1"}'.replace(b' ', b'')


def test_cost_fetch_balance_and_history_with_distinct_auth():
    client, requests = captured_requests()
    assert client.feature_cost('feature_clothes_v4') == 3
    assert client.balance() == 4242
    entries = client.credit_history()
    assert entries == [{'taskId': 't', 'units': 2}]
    history_request = [request for request in requests
                       if request.url.path == '/s2s/v1.0/client/credit/history'][0]
    assert history_request.headers['x-api-key'] == 'fixture-history-key'


def test_credit_history_requires_its_own_credential_in_live_mode():
    client = UtilityClient(mode='LIVE', base_url='https://x.invalid', api_key='k')
    with pytest.raises(ApiError) as error:
        client.credit_history()
    assert error.value.code == 'PROVIDER_UNAVAILABLE'


def test_facial_color_tones_payload_and_parse():
    adapter = FacialColorTonesAdapter()
    assert adapter.build_payload('file-1') == {'file': 'file-1'}
    result = adapter.fixture_result('file-1')
    adapter.validate_result(result)
    tones = adapter.parse_result(result)
    assert tones == ['#F1C9A5', '#E0AC8B']
    with pytest.raises(ApiError):
        adapter.validate_result({'tones': [{'hex': 'red'}]})


def test_cost_cache_freshness_gates_paid_submission(db_url):
    import datetime

    from sqlalchemy import select

    import apps.api.clock as clock_module
    from apps.api.modules.try_on_jobs.models import FeatureCostRow

    client, _ = captured_requests()
    service = CostService(client)
    engine = create_engine(db_url)
    db = sessionmaker(bind=engine)()
    cost = service.cost_for(db, 'CLOTHES_V4')
    assert cost == 3
    # fresh cache allows paid submission
    assert service.verified_cost(db, 'CLOTHES_V4') == 3

    stale_at = clock_module.now() - datetime.timedelta(hours=25)
    row = db.scalar(select(FeatureCostRow).where(FeatureCostRow.capability == 'CLOTHES_V4'))
    assert row is not None
    row.fetched_at = stale_at
    db.commit()
    with pytest.raises(ApiError) as error:
        service.verified_cost(db, 'CLOTHES_V4')
    assert error.value.code == 'COST_UNAVAILABLE'
    db.rollback()

    # refresh overwrites the stale cache
    assert service.cost_for(db, 'CLOTHES_V4', refresh=True) == 3
    row = db.scalar(select(FeatureCostRow).where(FeatureCostRow.capability == 'CLOTHES_V4'))
    assert row is not None
    assert clock_module.now() - clock_module.as_utc(row.fetched_at) < COST_STALENESS
