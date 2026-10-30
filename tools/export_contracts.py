"""Generate only derived contracts; never write protected specifications."""
import argparse
import json
from pathlib import Path

from contracts.runtime.transport import create_app

TARGET = Path('contracts/runtime/openapi.json')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = json.dumps(create_app().openapi(), sort_keys=True, indent=2) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != result:
            raise SystemExit('Frozen OpenAPI drift; integration owner must review changes')
    else:
        TARGET.write_text(result)


if __name__ == '__main__':
    main()
