import httpx
import pytest

from apps.api.errors import ApiError
from apps.api.modules.try_on_jobs.live_gateway import LiveGateway, payload_for


def test_real_nested_response_and_signed_upload_do_not_leak_key():
    calls = []
    def respond(request):
        calls.append(request)
        if request.url.host == 'media.s3.amazonaws.com':
            assert 'authorization' not in request.headers
            return httpx.Response(200)
        assert request.headers['authorization'] == 'Bearer test-key'
        if request.url.path.endswith('/file'):
            return httpx.Response(200, json={'status': 200, 'data': {'files': [{
                'file_id': 'file-1', 'requests': [{'method': 'PUT',
                'url': 'https://media.s3.amazonaws.com/input', 'headers': {}}]}]}})
        if request.method == 'POST':
            return httpx.Response(200, json={'status': 200, 'data': {'task_id': 'task-1'}})
        return httpx.Response(200, json={'status': 200, 'data': {
            'task_status': 'running', 'results': None}})
    gateway = LiveGateway('test-key', httpx.MockTransport(respond))
    assert gateway.upload(b'jpeg', 'image/jpeg') == 'file-1'
    assert gateway.submit('HAIR_COLOR', {'src_file_id': 'file-1', 'preset': 'Burgundy'}) == 'task-1'
    assert gateway.poll('HAIR_COLOR', 'task-1')['task_status'] == 'running'


def test_clothes_payload_is_one_real_garment_step():
    result = payload_for('CLOTHES_V4', 'src', ['ref'], {'area': 'upper_body'})
    assert result == {'src_file_id': 'src', 'ref_file_id': 'ref',
                      'garment_category': 'upper_body', 'filter_multi_person': 'strict'}


def test_reject_unsupported_combined_before_billing():
    with pytest.raises(ApiError):
        payload_for('COMBINED', 'src', [], {})


@pytest.mark.parametrize('capability', ['EARRINGS', 'NECKLACE', 'RING', 'BRACELET', 'WATCH'])
def test_jewellery_requests_link_source_and_reference_file_ids(capability):
    value = payload_for(capability, 'src', ['product'], {})
    assert value['src_file_id'] == value['source_info']['name'] == 'src'
    assert value['ref_file_ids'] == ['product']
    assert value['object_infos'] == [{'name': 'product'}]


@pytest.mark.parametrize('category', ['lip_color', 'foundation', 'blush'])
def test_makeup_choices_preserve_zero_skin_smoothing(category):
    value = payload_for('MAKEUP', 'src', [], {'makeupCategory': category, 'color': '#ab3456'})
    assert value['effects'][0]['skinSmoothStrength'] == 0
    assert value['effects'][1]['category'] == category
    assert value['effects'][1]['palettes'][0]['color'] == '#ab3456'


def test_untrusted_signed_media_urls_are_rejected():
    for url in ['http://example.com/x', 'https://127.0.0.1/x',
                'https://amazonaws.com.evil.invalid/x', 'https://user:pass@media.s3.amazonaws.com/x']:
        with pytest.raises(ApiError):
            LiveGateway.validate_media_url(url)
