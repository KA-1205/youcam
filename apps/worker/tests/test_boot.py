import json
import subprocess
import sys


def test_worker_check_cannot_dispatch():
    result = subprocess.run([sys.executable, '-m', 'apps.worker.main', '--check'],
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == {'status': 'FOUNDATION', 'dispatchEnabled': False}
