import json
import subprocess
import sys


def test_worker_check_reports_ready_without_dispatch():
    result = subprocess.run([sys.executable, '-m', 'apps.worker.main', '--check'],
                            text=True, capture_output=True, check=True)
    payload = json.loads(result.stdout)
    assert payload['status'] == 'READY'
    # Without a configured database the worker must not claim real dispatch duty.
    assert payload['dispatchEnabled'] is (bool(__import__('os').environ.get('DATABASE_URL')))


def test_worker_requires_one_run_mode():
    result = subprocess.run([sys.executable, '-m', 'apps.worker.main'],
                            text=True, capture_output=True)
    assert result.returncode != 0
