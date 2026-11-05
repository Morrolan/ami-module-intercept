"""A reopened receiver picker must reflect the actual running radio."""
import importlib
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize('mode', ['acars', 'vdl2'])
@pytest.mark.parametrize('running', [True, False])
def test_datalink_status_reports_actual_receiver(client, monkeypatch, mode, running):
    import app as runtime
    route = importlib.import_module('routes.'+mode)
    process = Mock()
    process.poll.return_value = None if running else 1
    monkeypatch.setattr(runtime, mode+'_process', process)
    monkeypatch.setattr(route, mode+'_active_device', 1)
    monkeypatch.setattr(route, mode+'_active_sdr_type', 'rtlsdr')
    response = client.get('/'+mode+'/status')
    assert response.status_code == 200
    assert response.json['running'] is running
    assert response.json['active_device'] == (1 if running else None)
    assert response.json['sdr_type'] == ('rtlsdr' if running else None)
