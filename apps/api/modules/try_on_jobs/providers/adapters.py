"""The eight required YouCam adapters.

Each adapter carries its own documented task path, request payload builder and
result schema. Makeup documentation shows differing example result shapes, so
parsing follows per-adapter fixtures rather than an assumed universal
`results.url` field. Clothes V4 deliberately uses filter_multi_person=strict for
predictable single-person capture, and one logical clothing job may compose
several provider tasks (upper/lower/full-body/outer/shoes) rather than a fixed
number of calls.
"""
from abc import ABC
from typing import Any

from apps.api.errors import ApiError
from apps.api.modules.try_on_jobs.providers.base import ProviderAdapter

CLOTHES_AREAS = ('full_body', 'lower_body', 'upper_body', 'shoes', 'outer', 'auto')
URL_SHAPE = {
    'type': 'object',
    'required': ['urls'],
    'properties': {'urls': {'type': 'array', 'items': {'type': 'string',
                                                       'pattern': '^https?://'}}},
}
RESULT_SHAPE_SINGULAR = {
    'type': 'object',
    'required': ['output'],
    'properties': {'output': {'type': 'object', 'required': ['url'],
                              'properties': {'url': {'type': 'string',
                                                     'pattern': '^https?://'}}}},
}


class _ListAdapter(ProviderAdapter, ABC):
    """Common shape: results arrive as a `urls` array under `results`."""

    result_schema = {
        'type': 'object',
        'required': ['results'],
        'properties': {'results': {'type': 'array', 'minItems': 1, 'items': URL_SHAPE}},
    }

    def parse_result(self, result: dict[str, Any]) -> list[str]:
        return [entry['urls'][0] for entry in result['results']]

    def fixture_result(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'results': [{'urls': [f'https://fixture.anchor-fit.invalid/render/'
                                      f'{self.capability.lower()}-{file_id}.png']}]}


class _OutputAdapter(ProviderAdapter, ABC):
    """Shape with a single `output.url` (documented for some feature examples)."""

    result_schema = RESULT_SHAPE_SINGULAR

    def parse_result(self, result: dict[str, Any]) -> list[str]:
        return [result['output']['url']]

    def fixture_result(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'output': {'url': f'https://fixture.anchor-fit.invalid/render/'
                                  f'{self.capability.lower()}-{file_id}.png'}}


class ClothesV4Adapter(ProviderAdapter):
    """AI Clothes Virtual Try-On V4: composes one provider task per selected area."""

    capability = 'CLOTHES_V4'
    task_path = '/s2s/v2.0/task/cloth-v4'
    result_schema = _ListAdapter.result_schema

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        areas = []
        for item in items:
            area = item.get('area', 'auto')
            if area not in CLOTHES_AREAS:
                raise ApiError(422, 'VALIDATION_ERROR', f'Unsupported V4 area: {area}.')
            areas.append({'area': area, 'reference': item['reference']})
        if not areas:
            raise ApiError(422, 'VALIDATION_ERROR', 'V4 requires at least one garment area.')
        return {'file': file_id, 'filterMultiPerson': 'strict', 'garments': areas}

    def parse_result(self, result: dict[str, Any]) -> list[str]:
        return [entry for entry in (item['urls'][0] for item in result['results'])]

    def fixture_result(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'results': [{'urls': [f'https://fixture.anchor-fit.invalid/render/'
                                      f'cloth-v4-{area["area"]}-{file_id}.png']}
                            for area in items]}


class MakeupAdapter(_ListAdapter):
    capability = 'MAKEUP'
    task_path = '/s2s/v2.0/task/makeup-vto'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        if not items:
            raise ApiError(422, 'VALIDATION_ERROR', 'Makeup requires at least one effect.')
        return {'file': file_id, 'effects': [{'kind': item['kind'], 'effect': item['effect']}
                                             for item in items]}


class EarringsAdapter(_ListAdapter):
    capability = 'EARRINGS'
    task_path = '/s2s/v2.0/task/2d-vto/earring'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'file': file_id, 'product': items[0]['reference']}


class NecklaceAdapter(_ListAdapter):
    capability = 'NECKLACE'
    task_path = '/s2s/v2.0/task/2d-vto/necklace'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'file': file_id, 'product': items[0]['reference']}


class RingAdapter(_OutputAdapter):
    """Ring VTO documents a single-output example shape; parse follows that fixture."""

    capability = 'RING'
    task_path = '/s2s/v2.0/task/2d-vto/ring'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'file': file_id, 'product': items[0]['reference']}


class BraceletAdapter(_OutputAdapter):
    capability = 'BRACELET'
    task_path = '/s2s/v2.0/task/2d-vto/bracelet'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'file': file_id, 'product': items[0]['reference']}


class WatchAdapter(_ListAdapter):
    capability = 'WATCH'
    task_path = '/s2s/v2.0/task/2d-vto/watch'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        return {'file': file_id, 'product': items[0]['reference']}


class HairColorAdapter(_OutputAdapter):
    """Hair colour presets are exploration, not catalog SKUs; no buy action is derived."""

    capability = 'HAIR_COLOR'
    task_path = '/s2s/v2.0/task/hair-color'

    def build_payload(self, file_id: str, items: list[dict[str, str]]) -> dict[str, Any]:
        preset = items[0].get('preset') if items else None
        if not preset:
            raise ApiError(422, 'VALIDATION_ERROR', 'Hair color requires a preset.')
        return {'file': file_id, 'preset': preset}


REGISTRY: dict[str, ProviderAdapter] = {adapter.capability: adapter for adapter in (
    ClothesV4Adapter(), MakeupAdapter(), EarringsAdapter(), NecklaceAdapter(), RingAdapter(),
    BraceletAdapter(), WatchAdapter(), HairColorAdapter())}


def adapter_for(capability: str) -> ProviderAdapter:
    adapter = REGISTRY.get(capability)
    if adapter is None:
        raise ApiError(422, 'VALIDATION_ERROR', f'Unsupported capability: {capability}.')
    return adapter
