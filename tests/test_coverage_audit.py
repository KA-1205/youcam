"""I04 coverage audit: manifest completeness and honest route-status evidence."""
import json
from pathlib import Path

from tools.coverage_audit import TICKET_PATHS, audit, load_traceability

MANIFEST = json.loads(Path('policy/traceability.json').read_text(encoding='utf-8'))


def test_manifest_preserves_all_requirements_and_stories():
    report = audit(MANIFEST, surface=None)
    assert report['requirements'] == 97
    assert report['stories'] == 189
    assert report['unmapped'] == []
    assert report['unknownTickets'] == []
    assert report['missingLanePaths'] == []
    assert report['errors'] == []


def test_every_lane_ticket_maps_to_existing_paths():
    covered = {ticket for entry in MANIFEST for ticket in entry['tickets']}
    assert covered == set(TICKET_PATHS)
    for ticket, paths in TICKET_PATHS.items():
        assert all(Path(path).is_dir() for path in paths), ticket


def test_route_surface_reports_foundation_gaps_honestly():
    surface = audit(MANIFEST, surface={
        'listVariants': 'IMPLEMENTED', 'getInsights': 'FOUNDATION_ONLY',
        'deleteAccount': 'FOUNDATION_ONLY'})
    assert surface['implementedOperations'] == 1
    assert surface['foundationOnlyOperations'] == ['deleteAccount', 'getInsights']


def test_audit_flags_incomplete_manifest():
    report = audit(MANIFEST[:-1], surface=None)
    assert report['errors']
