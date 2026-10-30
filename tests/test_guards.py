import hashlib
import json
from pathlib import Path

import pytest

from tools.boundaries import violations
from tools.guard import commit_message_errors, message_errors, path_errors, source_errors

POLICY = json.loads(Path('policy/ownership.json').read_text())


@pytest.mark.parametrize('branch,path', [
    ('feature/catalog-stylist', 'services/catalog/catalog.py'),
    ('feature/web-studio', 'apps/web/src/app/page.tsx'),
    ('feature/platform-integrations', 'infra/migrations/versions/new.py'),
    ('integration/contract-update', 'contracts/runtime/models.py'),
])
def test_owned_paths_allowed(branch, path):
    assert path_errors([path], branch, POLICY) == []


@pytest.mark.parametrize('path', ['package.json', 'package-lock.json', 'AGENTS.md',
                                  'contracts/runtime/models.py', 'apps/api/main.py',
                                  'reference/Anchor-Fit-Final-v3.3/README.md', '.github/workflows/ci.yml'])
def test_cross_lane_and_shared_edits_rejected(path):
    assert path_errors([path], 'feature/web-studio', POLICY)


def test_integration_owner_cannot_edit_original_docs():
    assert path_errors(['reference/Anchor-Fit-Final-v3.3/README.md'], 'integration/fix', POLICY)
    assert path_errors(['docs/new.md'], 'main', POLICY)
    assert path_errors(['README.md'], 'main', POLICY)


@pytest.mark.parametrize('message', ['Add shared foundation', 'Fix contract validation'])
def test_valid_commit_subject(message):
    assert not message_errors(message)


@pytest.mark.parametrize('message', ['Fix', 'Add contract\n\nDetails', 'Add AI foundation',
                                     'Add feature A01-123', 'Add foundation 🚀', 'x' * 51,
                                     'Add foundation\nCo-authored-by: person'])
def test_invalid_commit_subject(message):
    assert message_errors(message)


def test_github_merge_commit_on_main_allowed():
    message = ('Merge pull request #2 from KA-1205/integration/contract-remediation\n\n'
               'Extend catalog and session contracts')
    assert not commit_message_errors(message, 'main', 2)


@pytest.mark.parametrize('branch,parents,message', [
    ('feature/catalog-stylist', 2, 'Merge pull request #2 from KA-1205/feature/a\n\nFix'),
    ('main', 1, 'Merge pull request #2 from KA-1205/feature/a\n\nFix'),
    ('main', 2, 'Merge pull request #2 from KA-1205/feature/a\n\nFix\nCo-authored-by: X'),
    ('main', 2, 'Merge pull request #2 from KA-1205/feature/a\n\nFix\nMore text'),
    ('main', 2, 'Merge something unsafe\n\nFix'),
])
def test_nonstandard_merge_commit_still_rejected(branch, parents, message):
    assert commit_message_errors(message, branch, parents)


def test_modified_deleted_added_sources_fail(tmp_path):
    source = tmp_path / 'reference/spec.md'
    source.parent.mkdir()
    source.write_text('original\n')
    manifest = {'files': {'reference/spec.md': hashlib.sha256(source.read_bytes()).hexdigest()}}
    assert not source_errors(manifest, tmp_path)
    source.write_text('changed\n')
    assert source_errors(manifest, tmp_path)
    source.unlink()
    assert source_errors(manifest, tmp_path)
    source.write_text('original\n')
    (source.parent / 'extra.md').write_text('extra')
    assert source_errors(manifest, tmp_path)


def test_cross_module_imports_fail():
    assert violations('from apps.api.modules.commerce import database', 'apps/api/modules/shopper_profile')
    assert violations('from services.catalog.internal import Table', 'services/recommendations')
    assert violations('from ..commerce import Table', 'apps/api/modules/shopper_profile')
    assert not violations('from contracts.runtime.ports import CatalogPort', 'services/recommendations')
