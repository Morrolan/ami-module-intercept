"""Current receiver identity must not depend on optional flight history."""
from threading import Event
from threading import Thread as RealThread
from unittest.mock import Mock

import pytest

import routes.adsb as adsb


@pytest.fixture(autouse=True)
def clean_session(monkeypatch):
    monkeypatch.setattr(adsb, 'ADSB_HISTORY_ENABLED', False)
    monkeypatch.setattr(adsb, 'adsb_using_service', False)
    monkeypatch.setattr(adsb, 'adsb_active_device', None)
    monkeypatch.setattr(adsb, '_runtime_session', None, raising=False)
    monkeypatch.setattr(adsb.threading, 'Thread', Mock())


def test_remote_receiver_survives_status_reload_without_history(client):
    response = client.post('/adsb/start', json={'remote_sbs_host': '10.10.42.6', 'remote_sbs_port': 30003})
    assert response.status_code == 200
    session = response.json['session']
    assert session and session['sdr_type'] == 'remote'
    assert session['remote_host'] == '10.10.42.6'
    status = client.get('/adsb/session').json
    assert status['tracking_active']
    assert status['session'] == session
    assert status['uptime_seconds'] is not None
    assert client.post('/adsb/start', json={'device': 0}).json['session'] == session
    assert client.post('/adsb/stop', json={}).status_code == 200
    stopped = client.get('/adsb/session').json
    assert not stopped['tracking_active']
    assert stopped['session'] is None


def test_history_failure_does_not_lose_current_receiver(client, monkeypatch):
    monkeypatch.setattr(adsb, 'ADSB_HISTORY_ENABLED', True)
    monkeypatch.setattr(adsb, 'PSYCOPG2_AVAILABLE', True)
    monkeypatch.setattr(adsb, '_ensure_history_schema', Mock())
    monkeypatch.setattr(adsb, '_get_history_connection', Mock(side_effect=RuntimeError('unavailable')))
    response = client.post('/adsb/start', json={'remote_sbs_host': '10.10.42.6'})
    assert response.status_code == 200
    assert client.get('/adsb/session').json['session']['remote_host'] == '10.10.42.6'


def test_local_session_replaces_previous_remote_identity():
    adsb._record_session_start(device_index=0, sdr_type='remote', remote_host='10.10.42.6',
                               remote_port=30003, start_source=None, started_by=None)
    adsb._record_session_stop(stop_source=None, stopped_by=None)
    adsb._record_session_start(device_index=1, sdr_type='rtlsdr', remote_host=None,
                               remote_port=None, start_source=None, started_by=None)
    assert adsb._get_active_session()['sdr_type'] == 'rtlsdr'
    assert adsb._get_active_session()['device_index'] == 1
    assert adsb._get_active_session()['remote_host'] is None


def test_overlapping_stop_start_preserves_new_receiver(client, monkeypatch):
    client.post('/adsb/start', json={'remote_sbs_host': 'old-host'})
    entered, release, start_finished = Event(), Event(), Event()
    original_stop = adsb._record_session_stop

    def delayed_stop(**kwargs):
        entered.set()
        assert release.wait(3)
        return original_stop(**kwargs)

    monkeypatch.setattr(adsb, '_record_session_stop', delayed_stop)
    results = []
    stop = RealThread(target=lambda: results.append(client.post('/adsb/stop', json={}).status_code))

    def start_again():
        results.append(client.post('/adsb/start', json={'remote_sbs_host': 'new-host'}).status_code)
        start_finished.set()

    start = RealThread(target=start_again)
    try:
        stop.start()
        assert entered.wait(2)
        start.start()
        # The later START may complete only after the previous STOP is finished.
        assert not start_finished.wait(.15)
    finally:
        release.set()
        stop.join(3)
        start.join(3)
    assert sorted(results) == [200, 200]
    assert client.get('/adsb/session').json['session']['remote_host'] == 'new-host'


def test_status_during_start_waits_for_complete_receiver_identity(client, monkeypatch):
    entered, release, status_finished = Event(), Event(), Event()
    original = adsb._record_session_start

    def delayed_start(**kwargs):
        entered.set()
        assert release.wait(3)
        return original(**kwargs)

    monkeypatch.setattr(adsb, '_record_session_start', delayed_start)
    status = []
    start = RealThread(target=lambda: client.post('/adsb/start', json={'remote_sbs_host': 'new-host'}))

    def read_status():
        status.append(client.get('/adsb/session').json)
        status_finished.set()

    reader = RealThread(target=read_status)
    try:
        start.start()
        assert entered.wait(2)
        reader.start()
        assert not status_finished.wait(.15)
    finally:
        release.set()
        start.join(3)
        reader.join(3)
    assert status[0]['tracking_active']
    assert status[0]['session']['remote_host'] == 'new-host'
