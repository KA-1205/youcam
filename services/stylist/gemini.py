"""Gemini generateContent adapter; output still passes broker validation.

Wire contract: https://ai.google.dev/api/generate-content
"""
import json
import re
from typing import Any

import httpx

from services.stylist.broker import ModelTimeout, ModelUnavailable


class GeminiAdapter:
    def __init__(self, api_key: str, model: str,
                 transport: httpx.BaseTransport | None = None) -> None:
        if not re.fullmatch(r'[a-zA-Z0-9._-]+', model):
            raise ValueError('Invalid stylist model identifier.')
        self.model = model
        self.api_key = api_key
        self.transport = transport

    def complete(self, system: str, payload: dict[str, Any], *,
                 timeout_seconds: float) -> dict[str, Any]:
        try:
            with httpx.Client(transport=self.transport, timeout=timeout_seconds) as client:
                response = client.post(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}'
                    ':generateContent', headers={'x-goog-api-key': self.api_key}, json={
                        'systemInstruction': {'parts': [{'text': system}]},
                        'contents': [{'role': 'user', 'parts': [{'text': json.dumps(payload)}]}],
                        'generationConfig': {'responseMimeType': 'application/json'},
                    })
                response.raise_for_status()
                parts = response.json()['candidates'][0]['content']['parts']
                result = json.loads(''.join(part.get('text', '') for part in parts))
                if not isinstance(result, dict):
                    raise ModelUnavailable()
                return result
        except httpx.TimeoutException:
            raise ModelTimeout() from None
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise ModelUnavailable() from None
