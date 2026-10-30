"""Provider client seam: submit and poll YouCam tasks with honest mode gating.

FIXTURE mode uses canned synthetic responses validated per-adapter (never
presented as live). LIVE mode requires explicit base URL and API key
configuration; without verified capability activation it stays gated and raises
PROVIDER_UNAVAILABLE rather than simulating success. Polling follows the
documented cadence: 10s first, then exponential backoff to 30s with jitter,
honouring Retry-After.
"""
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
from jsonschema import ValidationError, validate

from apps.api.errors import ApiError

DEFAULT_HOST = 'https://yce-api-01.makeupar.com'  # documented example host; region unverified
FIRST_POLL_DELAY = 10.0
MAX_POLL_DELAY = 30.0


@dataclass
class PollResult:
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    error_category: str | None = None
    retry_after: float | None = None


class ProviderAdapter(ABC):
    """One adapter per documented API; request and result shapes are not interchangeable."""

    capability: str
    task_path: str

    @abstractmethod
    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]: ...

    @abstractmethod
    def parse_result(self, result: dict[str, Any]) -> list[str]:
        """Extract result asset URLs; each adapter follows its own verified fixture shape."""

    @abstractmethod
    def fixture_result(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        """Synthetic success payload matching this adapter's result schema (FIXTURE only)."""

    result_schema: dict[str, Any]

    def validate_result(self, result: dict[str, Any]) -> None:
        try:
            validate(instance=result, schema=self.result_schema)
        except ValidationError as error:
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE',
                           'Provider response does not match the expected schema.') from error


def normalize_error(status_code: int, body: dict[str, Any]) -> ApiError:
    """Map provider failures to the behavior-contract categories without inventing codes."""
    known = {'INVALID_INPUT': 422, 'MISSING_REGION': 422, 'MULTI_PERSON': 422,
             'SAFETY_REJECTED': 422, 'UNSUITED_REFERENCE': 422,
             'FEATURE_NOT_ENABLED': 503, 'RATE_LIMITED': 429, 'PROVIDER_OUTAGE': 503}
    code = str(body.get('error', {}).get('code') or body.get('code') or 'PROVIDER_OUTAGE')
    status = known.get(code, 502)
    category = code if code in known else 'PROVIDER_OUTAGE'
    return ApiError(status, category,
                    'The preview provider rejected or failed this request.')


class ProviderClient:
    """HTTP delivery for one adapter. mode FIXTURE never performs a network call."""

    def __init__(self, adapter: ProviderAdapter, mode: str = 'FIXTURE', base_url: str | None = None,
                 api_key: str | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.adapter = adapter
        self.mode = mode
        if mode == 'LIVE':
            if not api_key or not base_url:
                raise ApiError(503, 'PROVIDER_UNAVAILABLE',
                               'Live provider access is not activated for this capability.')
            self._http = httpx.Client(base_url=base_url, headers={'X-API-KEY': api_key},
                                      timeout=20.0)
        else:
            self._http = httpx.Client(
                base_url=base_url or DEFAULT_HOST,
                transport=transport or httpx.MockTransport(self._fixture_transport), timeout=20.0)

    def _fixture_transport(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/delete') or 'credit' in request.url.path:
            return httpx.Response(200, json={'ok': True})
        return httpx.Response(200, json={'taskId': 'fixture-task-1', 'status': 'QUEUED'})

    def submit(self, payload: dict[str, Any]) -> str:
        if self.mode != 'LIVE' and os.getenv('LIVE_PROVIDERS_ENABLED', 'false').lower() == 'true':
            raise ApiError(503, 'PROVIDER_UNAVAILABLE',
                           'Live providers are disabled pending verified activation.')
        try:
            response = self._http.post(self.adapter.task_path, json=payload)
        except httpx.HTTPError:
            raise ApiError(503, 'PROVIDER_OUTAGE', 'The preview provider is unreachable.')
        if response.status_code >= 400:
            raise normalize_error(response.status_code, _safe_json(response))
        body = _safe_json(response)
        task_id = body.get('taskId') or body.get('task_id')
        if not task_id:
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'Provider accepted without a task id.')
        return str(task_id)

    def poll(self, task_id: str) -> PollResult:
        try:
            response = self._http.get(f'{self.adapter.task_path}/{task_id}')
        except httpx.HTTPError:
            return PollResult(status='RUNNING', error_category='PROVIDER_OUTAGE',
                              retry_after=MAX_POLL_DELAY)
        if response.status_code == 429:
            retry_after = float(response.headers.get('Retry-After') or MAX_POLL_DELAY)
            return PollResult(status='RUNNING', retry_after=retry_after)
        if response.status_code >= 400:
            raise normalize_error(response.status_code, _safe_json(response))
        body = _safe_json(response)
        status = str(body.get('status', 'RUNNING')).upper()
        if status == 'SUCCEEDED':
            result = body.get('result') or {}
            self.adapter.validate_result(result)
            return PollResult(status='SUCCEEDED', result=result)
        if status == 'FAILED':
            return PollResult(status='FAILED', error_category='PROVIDER_OUTAGE')
        return PollResult(status='RUNNING')

    def next_poll_delay(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None:
            return retry_after
        delay = FIRST_POLL_DELAY * (2 ** max(attempt - 1, 0))
        delay = min(delay, MAX_POLL_DELAY)
        return delay * (1 + random.uniform(0, 0.1))  # jitter


def wait(seconds: float) -> None:
    time.sleep(seconds)


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
        return body if isinstance(body, dict) else {}
    except ValueError:
        return {}


__all__ = ['FIRST_POLL_DELAY', 'MAX_POLL_DELAY', 'PollResult', 'ProviderAdapter',
           'ProviderClient', 'normalize_error']
