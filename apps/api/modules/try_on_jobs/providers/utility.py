"""Utility adapters: file management, task deletion and the unit/credit system.

The credit history endpoint is documented on a different version and
authentication than the other unit operations, so this client carries a separate
optional history key and never assumes one credential works everywhere. Exact
provider contracts beyond the documented paths are unverified for this account;
fixture responses are synthetic and live calls stay gated.
"""
import base64
from typing import Any

import httpx

from apps.api.errors import ApiError
from apps.api.modules.try_on_jobs.providers.base import _safe_json, normalize_error

FILE_PATH = '/s2s/v2.0/file'
TASK_DELETE_PATH = '/s2s/v2.0/task/delete'
FEATURE_COST_PATH = '/s2s/v2.0/credit/feature-cost'
BALANCE_PATH = '/s2s/v2.0/credit/balance'
HISTORY_PATH = '/s2s/v1.0/client/credit/history'  # different version and authentication


class UtilityClient:
    """Shared transport for documented utility operations (FIXTURE or LIVE)."""

    def __init__(self, mode: str = 'FIXTURE', base_url: str | None = None,
                 api_key: str | None = None, history_key: str | None = None,
                 transport: httpx.BaseTransport | None = None) -> None:
        self.mode = mode
        self.api_key = api_key
        self.history_key = history_key
        if mode == 'LIVE':
            if not api_key or not base_url:
                raise ApiError(503, 'PROVIDER_UNAVAILABLE',
                               'Utility operations are not activated for this account.')
            self._http = httpx.Client(base_url=base_url, headers={'X-API-KEY': api_key},
                                      timeout=20.0)
        else:
            self._http = httpx.Client(
                base_url=base_url or 'https://yce-api-01.makeupar.com',
                transport=transport or httpx.MockTransport(self._fixture_transport), timeout=20.0)

    def _fixture_transport(self, request: httpx.Request) -> httpx.Response:
        if request.method == 'POST' and request.url.path == FILE_PATH:
            return httpx.Response(200, json={
                'fileId': 'fixture-file-1', 'uploadUrl': 'https://fixture.anchor-fit.invalid/up'})
        if request.method == 'GET' and request.url.path == FEATURE_COST_PATH:
            feature = request.url.params.get('featureName', 'unknown')
            return httpx.Response(200, json={'featureName': feature, 'cost': 2})
        if request.method == 'GET' and request.url.path == BALANCE_PATH:
            return httpx.Response(200, json={'balance': 500})
        if request.method == 'GET' and request.url.path == HISTORY_PATH:
            return httpx.Response(200, json={'entries': []})
        return httpx.Response(200, json={'ok': True})

    def create_file(self, data: bytes, content_type: str) -> str:
        response = self._request('POST', FILE_PATH, json={'contentType': content_type})
        file_id = response.get('fileId') or response.get('file_id')
        upload_url = response.get('uploadUrl')
        if not file_id or not upload_url:
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE',
                           'File creation did not return an upload target.')
        upload = self._http.put(str(upload_url), content=data,
                                headers={'Content-Type': content_type})
        if upload.status_code >= 400:
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'File upload was rejected.')
        return str(file_id)

    def delete_task(self, task_id: str) -> None:
        # Documented for finished tasks; never claimed to stop in-flight billing.
        self._request('POST', TASK_DELETE_PATH, json={'taskId': task_id})

    def feature_cost(self, feature: str) -> int | None:
        response = self._request('GET', FEATURE_COST_PATH, params={'featureName': feature})
        cost = response.get('cost')
        return int(cost) if cost is not None else None

    def balance(self) -> int | None:
        response = self._request('GET', BALANCE_PATH)
        balance = response.get('balance')
        return int(balance) if balance is not None else None

    def credit_history(self) -> list[dict[str, Any]]:
        """Requires the separate history credential; a missing key is reported honestly."""
        if self.mode == 'LIVE' and not self.history_key:
            raise ApiError(503, 'PROVIDER_UNAVAILABLE',
                           'Credit history requires its own documented credential.')
        headers = {'X-API-KEY': self.history_key or 'fixture-history-key'}
        try:
            response = self._http.get(HISTORY_PATH, headers=headers)
        except httpx.HTTPError:
            raise ApiError(503, 'PROVIDER_OUTAGE', 'The provider is unreachable.')
        if response.status_code >= 400:
            raise normalize_error(response.status_code, _safe_json(response))
        return list(_safe_json(response).get('entries', []))

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise ApiError(503, 'PROVIDER_OUTAGE', 'The provider is unreachable.')
        if response.status_code >= 400:
            raise normalize_error(response.status_code, _safe_json(response))
        return _safe_json(response)


class FacialColorTonesAdapter:
    """Optional image-estimated colour evidence for AnchorMatch.

    The guide names `task/skin-tone-analysis`; the exact versioned contract is
    unverified, so this adapter is built and gated NOT_TESTED. It is opt-in for
    the shopper and never restricts clothing or jewellery by skin tone.
    """

    capability = 'FACIAL_COLOR_TONES'
    task_path = '/s2s/v2.0/task/skin-tone-analysis'
    result_schema = {
        'type': 'object',
        'required': ['tones'],
        'properties': {'tones': {'type': 'array', 'minItems': 1,
                                 'items': {'type': 'object', 'required': ['hex'],
                                           'properties': {'hex': {'type': 'string',
                                                                  'pattern': '^#[0-9A-Fa-f]{6}$'}}}}},
    }

    def build_payload(self, file_id: str) -> dict[str, Any]:
        return {'file': file_id}

    def fixture_result(self, file_id: str) -> dict[str, Any]:
        palette = ['#F1C9A5', '#E0AC8B']
        return {'tones': [{'hex': tone} for tone in palette]}

    def parse_result(self, result: dict[str, Any]) -> list[str]:
        return [tone['hex'] for tone in result['tones']]

    def validate_result(self, result: dict[str, Any]) -> None:
        from jsonschema import ValidationError, validate

        try:
            validate(instance=result, schema=self.result_schema)
        except ValidationError as error:
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE',
                           'Colour analysis response does not match the expected schema.') \
                from error


def encode_reference(reference: str) -> str:
    return base64.urlsafe_b64encode(reference.encode()).decode()
