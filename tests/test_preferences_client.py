"""Exercise the actual browser synchronizer without a browser/network dependency."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize('script', ['preferences.test.cjs', 'adsb-remote.test.cjs'])
def test_client_preferences(script):
    if not shutil.which('node'):
        pytest.skip('Node is needed for isolated JavaScript checks')
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['node', 'tests/js/' + script], cwd=root, check=True, timeout=15)
