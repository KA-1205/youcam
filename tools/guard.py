"""Read-only source, ownership and commit checks; run the trusted base copy in CI."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], text=True).strip()


def read_policy(path: str, base: str | None) -> dict:
    return json.loads(git('show', f'{base}:{path}') if base else Path(path).read_text())


def source_errors(manifest: dict, root: Path = ROOT) -> list[str]:
    errors = []
    expected = manifest['files']
    actual = {str(p.relative_to(root)) for p in (root / 'reference').rglob('*') if p.is_file()}
    if actual != set(expected):
        errors.append('Protected source inventory changed')
    for path, digest in expected.items():
        file = root / path
        if file.is_symlink() or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            errors.append(f'Protected source changed: {path}')
    return errors


def path_errors(paths: list[str], branch: str, ownership: dict) -> list[str]:
    errors = []
    lane = ownership['branches'].get(branch)
    integration = branch == 'main' or branch.startswith(ownership['integrationBranchPrefix'])
    if lane is None and not integration:
        errors.append(f'Unrecognized code branch: {branch}')
    for path in paths:
        if path.startswith(tuple(ownership['protectedPrefixes'])) or path in ownership['protectedNames']:
            errors.append(f'Protected path touched: {path}')
        elif lane is not None and not path.startswith(tuple(lane)):
            errors.append(f'Outside {branch} ownership: {path}')
    return errors


def message_errors(message: str) -> list[str]:
    text = message.rstrip('\n')
    if '\n' in text or not 1 <= len(text) <= 50:
        return ['Commit must have only a subject of 1–50 characters']
    if not 2 <= len(text.split()) <= 6:
        return ['Commit subject must contain 2–6 words']
    if re.search(r'(?i)co-authored|generated.by|\b(ai|codex|claude|chatgpt|copilot)\b|\b[A-Z][A-Z0-9]*-\d+\b|\b[ABC]\d{2}\b', text):
        return ['Commit subject contains attribution or ticket tags']
    if any(ord(c) > 127 for c in text):
        return ['Use plain subject text without emoji']
    return []


def commit_message_errors(message: str, branch: str, parent_count: int) -> list[str]:
    """Permit only genuine GitHub PR merge envelopes on main."""
    if branch == 'main' and parent_count == 2:
        match = re.fullmatch(
            r'Merge pull request #[1-9][0-9]* from [A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+'
            r'\\n\\n([^\\n]{1,100})\\n*',
            message,
        )
        if match and not re.search(r'(?i)co-authored|generated.by', match.group(1)):
            return []
    return message_errors(message)


def secret_errors(paths: list[str]) -> list[str]:
    errors = []
    for path in paths:
        p = Path(path)
        if (p.name.startswith('.env') and p.name != '.env.example') or p.suffix in {'.pem', '.key'}:
            errors.append(f'Secret file is tracked: {path}')
        if not p.is_file() or p.is_symlink() or p.stat().st_size > 2_000_000:
            continue
        text = p.read_text(errors='replace')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            errors.append(f'Private key detected: {path}')
        if re.search(r'\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AIza[A-Za-z0-9_-]{35})\b', text):
            errors.append(f'Credential pattern detected: {path}')
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--branch', default='main')
    args = parser.parse_args()
    manifest = read_policy('policy/protected-sources.json', args.base)
    ownership = read_policy('policy/ownership.json', args.base)
    errors = source_errors(manifest)
    tracked = git('ls-files').splitlines()
    errors += secret_errors(tracked)
    if args.base:
        paths = git('diff', '--name-only', '--no-renames', args.base, args.head).splitlines()
        errors += path_errors(paths, args.branch, ownership)
        for sha in git('rev-list', f'{args.base}..{args.head}').splitlines():
            parents = len(git('show', '-s', '--format=%P', sha).split())
            errors += [f'{sha}: {e}' for e in commit_message_errors(
                git('show', '-s', '--format=%B', sha), args.branch, parents)]
    if errors:
        raise SystemExit('\n'.join(errors))
    print('PASS: source hashes, inventory, scope, commit subjects and tracked secret checks')


if __name__ == '__main__':
    main()
