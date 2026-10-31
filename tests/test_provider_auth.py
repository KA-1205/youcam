import httpx

from apps.api.modules.try_on_jobs.providers.adapters import ClothesV4Adapter
from apps.api.modules.try_on_jobs.providers.base import ProviderClient
from apps.api.modules.try_on_jobs.providers.utility import UtilityClient


def test_live_clients_send_documented_bearer_authentication():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={'task_id': 'task-1'})

    transport = httpx.MockTransport(respond)
    provider = ProviderClient(ClothesV4Adapter(), mode='LIVE',
                              base_url='https://provider.invalid', api_key='test-key',
                              transport=transport)
    provider.submit({})
    utility = UtilityClient(mode='LIVE', base_url='https://provider.invalid',
                            api_key='test-key', transport=transport)
    utility._request('GET', '/s2s/v2.0/credit/feature-cost')
    assert len(seen) == 2
    for request in seen:
        assert request.headers.get('Authorization') == 'Bearer test-key'
        assert 'X-API-KEY' not in request.headers
