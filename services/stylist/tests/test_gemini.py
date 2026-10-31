import httpx
import pytest

from services.stylist.broker import ModelUnavailable
from services.stylist.gemini import GeminiAdapter


def test_gemini_extracts_json_without_trusting_it():
    def respond(request):
        assert request.headers['x-goog-api-key'] == 'test-key'
        assert request.url.path.endswith('/gemini-test:generateContent')
        return httpx.Response(200, json={'candidates': [{'content': {
            'parts': [{'text': '{"kind":"LOOKS"}'}]}}]})
    adapter = GeminiAdapter('test-key', 'gemini-test', httpx.MockTransport(respond))
    assert adapter.complete('policy', {}, timeout_seconds=1) == {'kind': 'LOOKS'}


def test_gemini_outage_uses_broker_fallback_signal():
    adapter = GeminiAdapter('test-key', 'gemini-test', httpx.MockTransport(
        lambda request: httpx.Response(503)))
    with pytest.raises(ModelUnavailable):
        adapter.complete('policy', {}, timeout_seconds=1)
