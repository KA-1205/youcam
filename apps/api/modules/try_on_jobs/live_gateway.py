"""Documented YouCam wire protocol. No credentials accompany signed media requests.

Sources: docs.perfectcorp.com/_bundle/reference/{file,ai_clothes,ai_hair_color,
makeup_vto,ai_earrings,ai_necklace,ring_vto,ai_bracelet,ai_watch}.json
"""
import math
import os
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from apps.api.errors import ApiError

HOST = 'https://yce-api-01.makeupar.com'
PATHS = {'CLOTHES_V4': 'cloth-v4', 'MAKEUP': 'makeup-vto', 'HAIR_COLOR': 'hair-color',
         'EARRINGS': '2d-vto/earring', 'NECKLACE': '2d-vto/necklace',
         'RING': '2d-vto/ring', 'BRACELET': '2d-vto/bracelet', 'WATCH': '2d-vto/watch'}
PRESETS = ['Jet Black', 'Chocolate Brown', 'Honey Blonde', 'Platinum Blonde', 'Ash Gray',
           'Rose Gold', 'Burgundy', 'Copper Red', 'Lavender', 'Teal Blue']
MAX_MEDIA_BYTES = 10 * 1024 * 1024


def enabled_capabilities() -> set[str]:
    if os.getenv('LIVE_PROVIDERS_ENABLED', 'false').lower() != 'true':
        return set()
    if not os.getenv('YOUCAM_API_KEY'):
        raise ValueError('YOUCAM_API_KEY is required for live previews.')
    if (os.getenv('YOUCAM_BASE_URL') or HOST).rstrip('/') != HOST:
        raise ValueError('Only the verified YouCam API server is supported.')
    if int(os.getenv('YOUCAM_CREDIT_LIMIT', '0')) <= 0:
        raise ValueError('An explicit positive YOUCAM_CREDIT_LIMIT is required.')
    requested = set(filter(None, os.getenv('YOUCAM_LIVE_CAPABILITIES', 'HAIR_COLOR').split(',')))
    if not requested <= PATHS.keys():
        raise ValueError('An unsupported live capability was configured.')
    return requested


def payload_for(capability: str, source: str, references: list[str], settings: dict) -> dict:
    payload: dict[str, Any] = {'src_file_id': source}
    if capability == 'HAIR_COLOR':
        preset = settings.get('preset')
        if preset not in PRESETS:
            raise ApiError(422, 'VALIDATION_ERROR', 'Choose a supported hair colour preset.')
        return {**payload, 'preset': preset}
    if capability == 'MAKEUP':
        # Presets are explicit exploration choices, never inferred product matches.
        shade = settings.get('color', '#9b3850')
        import re
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', shade):
            raise ApiError(422, 'VALIDATION_ERROR', 'Choose a valid makeup colour.')
        effect = settings.get('makeupCategory', 'lip_color')
        if effect not in ('lip_color', 'foundation', 'blush'):
            raise ApiError(422, 'VALIDATION_ERROR', 'Unsupported makeup category.')
        chosen: dict[str, Any]
        if effect == 'foundation':
            chosen = {'category': 'foundation', 'palettes': [{'color': shade,
                      'colorIntensity': 50, 'glowIntensity': 0, 'coverageIntensity': 50}]}
        elif effect == 'blush':
            chosen = {'category': 'blush', 'pattern': {'name': '1color1'},
                      'palettes': [{'color': shade, 'texture': 'matte', 'colorIntensity': 50}]}
        else:
            chosen = {'category': 'lip_color', 'shape': {'name': 'original'},
                      'style': {'type': 'full'},
                      'palettes': [{'color': shade, 'texture': 'matte', 'colorIntensity': 50}]}
        return {**payload, 'effects': [
            {'category': 'skin_smooth', 'skinSmoothStrength': 0, 'skinSmoothColorIntensity': 0},
            chosen]}
    if capability == 'CLOTHES_V4':
        if len(references) != 1:
            raise ApiError(422, 'VALIDATION_ERROR', 'Each clothing step needs one product photo.')
        return {**payload, 'ref_file_id': references[0],
                'garment_category': settings.get('area', 'auto'), 'filter_multi_person': 'strict'}
    if capability in ('EARRINGS', 'NECKLACE', 'RING', 'BRACELET', 'WATCH'):
        if not references:
            raise ApiError(422, 'VALIDATION_ERROR', 'A product reference photo is required.')
        return {**payload, 'ref_file_ids': references, 'source_info': {'name': source},
                'object_infos': [{'name': ref} for ref in references]}
    raise ApiError(503, 'PROVIDER_UNAVAILABLE', 'This capability is not activated.')


class LiveGateway:
    def __init__(self, key: str, transport: httpx.BaseTransport | None = None) -> None:
        self.key = key
        self.http = httpx.Client(transport=transport, timeout=35,
                                 proxy=None if transport else os.getenv('HTTPS_PROXY'),
                                 trust_env=transport is None)
        self.media = httpx.Client(transport=transport, timeout=40,
                                  proxy=None if transport else os.getenv('HTTPS_PROXY'),
                                  trust_env=transport is None)

    def close(self) -> None:
        self.http.close()
        self.media.close()

    def api(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self.http.request(method, HOST + path,
                                         headers={'Authorization': f'Bearer {self.key}'}, **kwargs)
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except httpx.HTTPStatusError as exc:
            code = 'QUOTA_EXCEEDED' if exc.response.status_code == 429 else 'PROVIDER_REJECTED'
            raise ApiError(502, code, 'YouCam rejected the request.',
                           headers={'Retry-After': exc.response.headers.get('Retry-After', '30')}) from None
        except (httpx.HTTPError, ValueError):
            raise ApiError(503, 'PROVIDER_OUTAGE', 'YouCam response was unavailable.') from None

    def upload(self, data: bytes, content_type: str, ring: bool = False) -> str:
        path = '/s2s/v2.0/file/2d-vto/ring' if ring else '/s2s/v2.0/file'
        response = self.api('POST', path, json={'files': [{'content_type': content_type,
                            'file_name': 'preview.jpg', 'file_size': len(data)}]})
        try:
            file = response['data']['files'][0]
            for target in file['requests']:
                self.validate_media_url(target['url'])
                # Deliberately uses a different client without an API-key default.
                uploaded = self.media.request(target['method'], target['url'], content=data,
                    headers={k: str(v) for k, v in target['headers'].items()})
                uploaded.raise_for_status()
            return str(file['file_id'])
        except (KeyError, IndexError, httpx.HTTPError):
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'YouCam upload failed.') from None

    def submit(self, capability: str, payload: dict) -> str:
        response = self.api('POST', '/s2s/v2.0/task/' + PATHS[capability], json=payload)
        try:
            return str(response['data']['task_id'])
        except (KeyError, TypeError):
            raise ApiError(502, 'UNKNOWN_OUTCOME', 'Submission requires reconciliation.') from None

    def poll(self, capability: str, task_id: str) -> dict:
        response = self.api('GET', '/s2s/v2.0/task/' + PATHS[capability] + '/' + quote(task_id, safe=''))
        data = response.get('data')
        if not isinstance(data, dict) or data.get('task_status') not in ('running', 'success', 'error'):
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'Invalid YouCam task status.')
        return data

    def cost(self, capability: str) -> int:
        token = None
        costs = []
        for _ in range(20):
            params = {'page_size': 20}
            if token:
                params['starting_token'] = token
            result = self.api('GET', '/s2s/v2.0/credit/feature-cost', params=params)['result']
            for sku in result['skus']:
                if sku['run_task_url'] == HOST + '/s2s/v2.0/task/' + PATHS[capability]:
                    costs.append(math.ceil(float(sku['amount']) / int(sku['proc_unit'])))
            token = result.get('next_token')
            if not token:
                break
        if not costs or token:
            raise ApiError(503, 'COST_UNAVAILABLE', 'A verified cost is required.')
        return max(costs)  # Reserve the highest possible cost for this endpoint.

    @staticmethod
    def validate_media_url(url: str) -> None:
        parsed = urlsplit(url)
        host = parsed.hostname or ''
        allowed = ('amazonaws.com', 'cloudfront.net', 'makeupar.com', 'perfectcorp.com')
        if (parsed.scheme != 'https' or parsed.username or parsed.password
                or parsed.port not in (None, 443)
                or not any(host == domain or host.endswith('.' + domain) for domain in allowed)):
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'Untrusted provider media host.')

    def download(self, url: str) -> bytes:
        self.validate_media_url(url)
        try:
            with self.media.stream('GET', url) as response:
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_MEDIA_BYTES:
                        raise ValueError()
            if not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n')):
                raise ValueError()
            return bytes(data)
        except httpx.HTTPError:
            raise ApiError(503, 'PROVIDER_OUTAGE', 'Result download is temporarily unavailable.') from None
        except ValueError:
            raise ApiError(502, 'INVALID_PROVIDER_RESPONSE', 'Invalid result image.') from None

    def delete(self, task_id: str) -> None:
        self.api('POST', '/s2s/v2.0/task/delete', json={'task_id': task_id})
