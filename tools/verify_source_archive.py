"""Verify exact archived paths and bytes against pinned docs without changing docs."""
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

policy = json.loads(Path('policy/protected-sources.json').read_text())
sha = policy['docsCommit']
# CI checkout may not have docs locally. Fetch the specific reviewed source commit.
exists = subprocess.run(['git', 'cat-file', '-e', f'{sha}^{{commit}}'], capture_output=True)
if exists.returncode:
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', sha], check=True)
archive = subprocess.check_output(['git', 'show', f'{sha}:Anchor-Fit-v3.3-Specifications.zip'])
assert hashlib.sha256(archive).hexdigest() == policy['sourceZipSha256'], 'Original ZIP mismatch'
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    names = {f'reference/{name}' for name in z.namelist() if not name.endswith('/')}
    assert names == set(policy['files']), 'Reference inventory differs from original archive'
    for name in z.namelist():
        if not name.endswith('/'):
            p = Path('reference') / name
            assert p.read_bytes() == z.read(name), f'Changed original: {name}'
print('PASS: all 15 original files match the pinned ZIP byte for byte')
