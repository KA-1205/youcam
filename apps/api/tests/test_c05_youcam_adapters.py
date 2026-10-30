"""C05 acceptance: eight adapters with per-API payload builders, fixture parsers,
strict multi-person capture for Clothes V4, schema-validated results and honest
mode gating."""
import httpx
import pytest

from apps.api.errors import ApiError
from apps.api.modules.try_on_jobs.providers.adapters import REGISTRY, adapter_for
from apps.api.modules.try_on_jobs.providers.base import ProviderClient

CAPABILITIES = ['CLOTHES_V4', 'MAKEUP', 'EARRINGS', 'NECKLACE', 'RING', 'BRACELET', 'WATCH',
                'HAIR_COLOR']


def client_for(capability: str, handler=None, items=None) -> ProviderClient:
    def default_handler(request: httpx.Request) -> httpx.Response:
        adapter = adapter_for(capability)
        if request.method == 'GET':
            return httpx.Response(200, json={'status': 'SUCCEEDED',
                                             'result': adapter.fixture_result('f', items or [])})
        return httpx.Response(200, json={'taskId': 'task-123', 'status': 'QUEUED'})

    return ProviderClient(adapter_for(capability), mode='FIXTURE',
                          transport=httpx.MockTransport(handler or default_handler))


def test_all_eight_adapters_registered():
    assert set(REGISTRY) == set(CAPABILITIES)
    for capability in CAPABILITIES:
        assert REGISTRY[capability].task_path.startswith('/s2s/v2.0/task/')


def test_clothes_v4_strict_multi_person_and_area_composition():
    payload = REGISTRY['CLOTHES_V4'].build_payload('file-1', [
        {'area': 'upper_body', 'reference': 'ref-top-1'},
        {'area': 'shoes', 'reference': 'ref-shoes-1'}])
    assert payload['filterMultiPerson'] == 'strict'
    assert len(payload['garments']) == 2
    assert {garment['area'] for garment in payload['garments']} == {'upper_body', 'shoes'}
    with pytest.raises(ApiError):
        REGISTRY['CLOTHES_V4'].build_payload('file-1', [{'area': 'hat', 'reference': 'r'}])
    with pytest.raises(ApiError):
        REGISTRY['CLOTHES_V4'].build_payload('file-1', [])


def test_hair_color_and_makeup_payloads():
    with pytest.raises(ApiError):
        REGISTRY['HAIR_COLOR'].build_payload('file-1', [])
    payload = REGISTRY['HAIR_COLOR'].build_payload('file-1', [{'preset': 'auburn'}])
    assert payload['preset'] == 'auburn'
    payload = REGISTRY['MAKEUP'].build_payload('file-1', [
        {'kind': 'foundation', 'effect': 'fx-1'}, {'kind': 'lip', 'effect': 'fx-2'}])
    assert [effect['kind'] for effect in payload['effects']] == ['foundation', 'lip']


@pytest.mark.parametrize('capability', CAPABILITIES)
def test_fixture_submit_and_validated_parse(capability):
    adapter = REGISTRY[capability]
    items = ([{'area': 'upper_body', 'reference': 'r'}] if capability == 'CLOTHES_V4'
             else ([{'preset': 'auburn'}] if capability == 'HAIR_COLOR'
                   else ([{'kind': 'lip', 'effect': 'fx'}] if capability == 'MAKEUP'
                         else [{'reference': 'r'}])))
    client = client_for(capability, items=items)
    task_id = client.submit(adapter.build_payload('file-1', items))
    assert task_id == 'task-123'
    poll = client.poll(task_id)
    assert poll.status == 'SUCCEEDED'
    urls = adapter.parse_result(poll.result)
    assert urls and all(url.startswith('https://fixture.') for url in urls)


def test_result_schema_validation_rejects_malformed_response():
    adapter = adapter_for('RING')
    with pytest.raises(ApiError) as error:
        adapter.validate_result({'output': {'url': 'not-a-url'}})
    assert error.value.code == 'INVALID_PROVIDER_RESPONSE'


def test_provider_error_normalization_without_inventing_codes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={'error': {'code': 'MULTI_PERSON'}})

    client = ProviderClient(adapter_for('CLOTHES_V4'), mode='FIXTURE',
                            transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as error:
        client.submit({'file': 'f'})
    assert error.value.code == 'MULTI_PERSON'
    assert 'MULTI_PERSON' not in error.value.message  # no invented vendor detail

    def unknown_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={'error': {'code': 'ZZ_UNDOCUMENTED_9'}})

    client = ProviderClient(adapter_for('MAKEUP'), mode='FIXTURE',
                            transport=httpx.MockTransport(unknown_handler))
    with pytest.raises(ApiError) as error:
        client.submit({'file': 'f'})
    assert error.value.code == 'PROVIDER_OUTAGE'  # unknown code maps to generic failure


def test_rate_limit_honours_retry_after():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={'Retry-After': '17'}, json={})

    client = ProviderClient(adapter_for('WATCH'), mode='FIXTURE',
                            transport=httpx.MockTransport(handler))
    poll = client.poll('task-1')
    assert poll.status == 'RUNNING'
    assert poll.retry_after == 17.0
    assert client.next_poll_delay(1, poll.retry_after) == 17.0


def test_poll_backoff_is_exponential_with_jitter_cap():
    client = client_for('RING')
    first = client.next_poll_delay(1)
    assert 10.0 <= first <= 11.0
    capped = client.next_poll_delay(9)
    assert 30.0 <= capped <= 33.0


def test_live_mode_requires_credentials_and_stays_gated():
    with pytest.raises(ApiError) as error:
        ProviderClient(adapter_for('EARRINGS'), mode='LIVE')
    assert error.value.code == 'PROVIDER_UNAVAILABLE'
    with pytest.raises(ApiError) as error:
        ProviderClient(adapter_for('EARRINGS'), mode='LIVE', base_url='https://x.invalid')
    assert error.value.code == 'PROVIDER_UNAVAILABLE'


def test_unknown_capability_rejected():
    with pytest.raises(ApiError):
        adapter_for('TELEPORTATION')
