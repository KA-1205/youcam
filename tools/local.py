"""Load local configuration and prepare persistence before starting a service."""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    load_dotenv(root / '.env')
    os.environ.setdefault('DATABASE_URL', f'sqlite:///{root / ".anchor-fit-demo.db"}')
    os.environ.setdefault('DEMO_MODE', 'true')
    os.environ.setdefault('NEXT_PUBLIC_TRANSPORT', 'live')
    os.environ.setdefault('NEXT_PUBLIC_API_BASE_URL', 'http://127.0.0.1:8000')
    mode = sys.argv[1]
    if mode in ('api', 'worker'):
        subprocess.run([sys.executable, '-m', 'alembic', '-c',
                        'infra/migrations/alembic.ini', 'upgrade', 'head'], check=True)
    commands = {
        'api': [sys.executable, '-m', 'uvicorn', 'apps.api.main:app',
                '--host', '127.0.0.1', '--port', '8000'],
        'worker': [sys.executable, '-m', 'apps.worker.main', '--loop'],
        'web': ['npm', 'run', 'dev'],
    }
    os.execvp(commands[mode][0], commands[mode])


if __name__ == '__main__':
    main()
