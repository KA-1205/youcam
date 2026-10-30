"""Reject cross-module implementation imports; contracts are the only shared seam."""
import ast
from pathlib import Path

ROOTS = ['services/catalog', 'services/recommendations', 'services/stylist',
         'apps/api/modules/tenant_access', 'apps/api/modules/shopper_profile',
         'apps/api/modules/styling_session', 'apps/api/modules/commerce',
         'apps/api/modules/try_on_jobs', 'apps/api/modules/merchant_insights',
         'apps/api/modules/storage']


def violations(source: str, own: str) -> list[str]:
    errors = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level > 1:
                errors.append('Cross-module relative imports are forbidden; use ports')
            names = [node.module or '']
        for name in names:
            for root in ROOTS:
                module = root.replace('/', '.')
                if root != own and (name == module or name.startswith(module + '.')):
                    errors.append(f'{own} imports {name}; use contracts.runtime ports')
            if name.startswith('apps.web') or (own.startswith('services/') and name.startswith('apps.')):
                errors.append(f'{own} imports application implementation {name}')
    return errors


def main() -> None:
    errors = []
    for root in ROOTS:
        for p in Path(root).rglob('*.py'):
            errors += [f'{p}: {e}' for e in violations(p.read_text(), root)]
    if errors:
        raise SystemExit('\n'.join(errors))
    print('PASS: module import boundaries')


if __name__ == '__main__':
    main()
