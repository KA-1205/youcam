"""Traceability audit: 97 requirements and 189 stories against lane evidence.

Structural evidence only — it proves the manifest is complete, every entry maps
to a known ticket and every mapped lane path exists, and reports the honest
implementation status of the frozen HTTP surface. Behavior is proven by the
test suites, never by this script.
"""
import argparse
import json
import sys
from pathlib import Path

TRACEABILITY_PATH = Path('policy/traceability.json')
REQUIREMENT_COUNT = 97
STORY_COUNT = 189
LANE_TICKETS = {f'{lane}{number:02d}' for lane in 'ABC' for number in range(1, 9)}

TICKET_PATHS: dict[str, tuple[str, ...]] = {
    'A01': ('services/catalog',), 'A02': ('services/recommendations',),
    'A03': ('services/recommendations',), 'A04': ('services/stylist',),
    'A05': ('services/recommendations',), 'A06': ('services/stylist',),
    'A07': ('services/catalog',), 'A08': ('services/stylist',),
    'B01': ('apps/web/src',), 'B02': ('apps/web/src',), 'B03': ('apps/web/src',),
    'B04': ('apps/web/src',), 'B05': ('apps/web/src',), 'B06': ('apps/web/src',),
    'B07': ('apps/web/src',), 'B08': ('apps/web/src',),
    'C01': ('apps/api/modules/tenant_access', 'apps/api/modules/shopper_profile',
            'infra/migrations'),
    'C02': ('apps/api/modules/styling_session', 'apps/api/modules/commerce'),
    'C03': ('apps/api/modules/task_runtime', 'apps/worker'),
    'C04': ('apps/api/modules/storage',),
    'C05': ('apps/api/modules/try_on_jobs',),
    'C06': ('apps/api/modules/try_on_jobs',),
    'C07': ('apps/api/modules/try_on_jobs',),
    'C08': ('apps/worker', 'infra'),
}


def load_traceability(path: Path = TRACEABILITY_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def route_surface() -> dict[str, str]:
    """operation -> x-implementation-status, from the composed app itself."""
    from apps.api.main import create_app

    app = create_app()
    surface: dict[str, str] = {}
    for route in app.routes:
        extra = getattr(route, 'openapi_extra', None) or {}
        operation = extra.get('x-implementation-status')
        if operation is not None:
            surface[route.operation_id] = extra['x-implementation-status']  # type: ignore[attr-defined]
    return surface


def audit(entries: list[dict], surface: dict[str, str] | None = None,
          root: Path = Path.cwd()) -> dict:
    requirements = [entry for entry in entries if entry['id'].startswith('FR-')]
    stories = [entry for entry in entries if entry['id'].startswith('US-')]
    errors: list[str] = []
    if len(requirements) != REQUIREMENT_COUNT:
        errors.append(f'Expected {REQUIREMENT_COUNT} requirements, found {len(requirements)}')
    if len(stories) != STORY_COUNT:
        errors.append(f'Expected {STORY_COUNT} stories, found {len(stories)}')
    unmapped = [entry['id'] for entry in entries if not entry.get('tickets')]
    if unmapped:
        errors.append(f'{len(unmapped)} entries without tickets: {unmapped[:5]}')
    unknown = sorted({ticket for entry in entries for ticket in entry.get('tickets', [])
                      if ticket not in LANE_TICKETS})
    if unknown:
        errors.append(f'Unknown ticket references: {unknown}')
    missing_paths = sorted({ticket for entry in entries for ticket in entry.get('tickets', [])
                            if any(not (root / path).is_dir()
                                   for path in TICKET_PATHS.get(ticket, ('',)))})
    if missing_paths:
        errors.append(f'Tickets whose lane paths are missing: {missing_paths}')
    foundation_only = sorted(operation for operation, status in (surface or {}).items()
                             if status == 'FOUNDATION_ONLY')
    return {'requirements': len(requirements), 'stories': len(stories),
            'unmapped': unmapped, 'unknownTickets': unknown, 'missingLanePaths': missing_paths,
            'implementedOperations': sum(1 for status in (surface or {}).values()
                                         if status == 'IMPLEMENTED'),
            'foundationOnlyOperations': foundation_only, 'errors': errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true', help='print the machine report')
    args = parser.parse_args()
    report = audit(load_traceability(), route_surface())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"requirements={report['requirements']} stories={report['stories']} "
              f"implementedOperations={report['implementedOperations']} "
              f"foundationOnly={report['foundationOnlyOperations']}")
    if report['errors']:
        print('\n'.join(report['errors']), file=sys.stderr)
        raise SystemExit(1)
    print('PASS: traceability manifest complete; lane paths and ticket map verified')


if __name__ == '__main__':
    main()
