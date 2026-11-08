"""Saved remote endpoints only; no real sockets/listeners."""
import socket
from unittest.mock import MagicMock

import pytest

from utils.remote_sdr_health import RemoteSDRHealth, validate_entry


@pytest.mark.parametrize('host', ['', 'http://radio', 'radio/path', 'a b', '-bad', '999.1.1.1', 'bad..host'])
def test_invalid_hosts(host):
    with pytest.raises(ValueError):
        validate_entry({'name': 'Radio', 'host': host, 'port': 1234})


@pytest.mark.parametrize('port', [0, 65536, True, 1.5, '1.5', None])
def test_invalid_ports(port):
    with pytest.raises(ValueError):
        validate_entry({'name': 'Radio', 'host': 'radio.local', 'port': port})


@pytest.fixture
def monitor(monkeypatch):
    import utils.remote_sdr_health as module
    store = {}
    monkeypatch.setattr(module, 'get_setting', lambda key, default=None, **kwargs: store.get(key, default))
    monkeypatch.setattr(module, 'set_setting', lambda key, value: store.__setitem__(key, value))
    return RemoteSDRHealth()


def entry():
    return {'name': 'Roof', 'host': 'radio.local', 'port': 30003}


def test_crud(monitor):
    first = monitor.save(entry())
    second = monitor.save({**entry(), 'name': 'Second'})
    assert len(monitor.entries()) == 2
    assert first['state'] == 'unknown' and first['last_seen'] is None
    changed = monitor.save({**entry(), 'host': 'other.local'}, first['id'])
    assert changed['id'] == first['id']
    assert changed['host'] == 'other.local'
    monitor.remove(first['id'])
    assert [r['id'] for r in monitor.entries()] == [second['id']]
    with pytest.raises(KeyError):
        monitor.save(entry(), first['id'])


def test_check_states_timeout_and_stale_result(monitor, monkeypatch):
    import utils.remote_sdr_health as module
    saved = monitor.save(entry())
    connect = MagicMock()
    monkeypatch.setattr(module.socket, 'create_connection', connect)
    monitor.check(saved)
    online = monitor.entries()[0]
    assert online['state'] == 'online' and online['last_seen']
    connect.assert_called_once_with(('radio.local', 30003), timeout=3)
    connect.side_effect = socket.timeout()
    monitor.check(saved)
    offline = monitor.entries()[0]
    assert offline['state'] == 'offline'
    assert offline['last_seen'] == online['last_seen']
    monitor.save({**entry(), 'host': 'changed.local'}, saved['id'])
    connect.reset_mock()
    monitor.check(saved)
    connect.assert_not_called()
    assert monitor.entries()[0]['state'] == 'unknown'
    monitor.remove(saved['id'])
    monitor.check(saved)
    connect.assert_not_called()


def test_routes(client, anon_client, monitor, monkeypatch):
    import utils.remote_sdr_health as module
    monkeypatch.setattr(module, 'monitor', monitor)
    response = client.post('/settings/remote-sdrs', json=entry())
    assert response.status_code == 200
    saved = response.json['entry']
    assert client.get('/settings/remote-sdrs').json['entries'][0]['id'] == saved['id']
    assert client.put('/settings/remote-sdrs/' + saved['id'], json={**entry(), 'name': 'Edited'}).json['entry']['name'] == 'Edited'
    assert client.post('/settings/remote-sdrs', json={**entry(), 'port': 0}).status_code == 400
    assert client.delete('/settings/remote-sdrs/' + saved['id']).status_code == 200
    assert client.delete('/settings/remote-sdrs/' + saved['id']).status_code == 404
    with client.session_transaction() as session:
        session['role'] = 'user'
        session['username'] = 'not-admin'
    assert client.post('/settings/remote-sdrs', json=entry()).status_code == 403
    assert anon_client.get('/settings/remote-sdrs').status_code != 200


@pytest.mark.parametrize('host', ['10.10.42.6', 'radio.local', '::1', '2001:db8::1'])
def test_valid_hosts(host):
    assert validate_entry({**entry(), 'host': host, 'port': '30003'})['host'] == host


@pytest.mark.parametrize('data', [None, [], {}, {**entry(), 'name': ' '}, {**entry(), 'name': 'a' * 81}])
def test_invalid_entries(data):
    with pytest.raises(ValueError):
        validate_entry(data)


def test_scheduler_cadence_deadline_and_no_overlap(monitor, monkeypatch):
    import utils.remote_sdr_health as module
    clock = [100.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    thread = MagicMock()
    thread.is_alive.return_value = True
    factory = MagicMock(return_value=thread)
    monkeypatch.setattr(module.threading, 'Thread', factory)
    monitor.save(entry())
    monitor.tick()
    factory.assert_called_once()
    assert monitor.entries()[0]['state'] == 'unknown'
    clock[0] += 4
    monitor.tick()
    assert monitor.entries()[0]['state'] == 'offline'
    factory.assert_called_once()
    thread.is_alive.return_value = False
    monitor.tick()
    factory.assert_called_once()  # not due again until 60 seconds
    clock[0] = 160
    monitor.tick()
    assert factory.call_count == 2


def test_inflight_edit_discards_result(monitor, monkeypatch):
    import utils.remote_sdr_health as module
    saved = monitor.save(entry())
    def connect(*args, **kwargs):
        monitor.save({**entry(), 'host': 'different.local'}, saved['id'])
        return MagicMock()
    monkeypatch.setattr(module.socket, 'create_connection', connect)
    monitor.check(saved)
    assert monitor.entries()[0]['state'] == 'unknown'


def test_only_valid_saved_entries_are_scheduled(monitor, monkeypatch):
    import utils.remote_sdr_health as module
    monkeypatch.setattr(module, 'get_setting', lambda *args, **kwargs: [
        {'id': 'a' * 32, **entry(), 'host': 'http://invalid'}, None, 'radio'
    ])
    thread = MagicMock()
    monkeypatch.setattr(module.threading, 'Thread', thread)
    monitor.tick()
    assert monitor.entries() == []
    thread.assert_not_called()


def test_real_settings_persistence(tmp_path, monkeypatch):
    import utils.database as database
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'settings.db')
    database.init_db()
    first = RemoteSDRHealth()
    saved = first.save(entry())
    second = RemoteSDRHealth()
    assert second.entries()[0]['id'] == saved['id']
    second.remove(saved['id'])
    assert first.entries() == []


def test_requests_do_not_probe_and_generic_writes_cannot_bypass(client, monitor, monkeypatch):
    import utils.remote_sdr_health as module
    monkeypatch.setattr(module, 'monitor', monitor)
    probe = MagicMock()
    monkeypatch.setattr(module.socket, 'create_connection', probe)
    client.post('/settings/remote-sdrs', json=entry())
    client.get('/settings/remote-sdrs')
    for method, path, data in [
        ('post', '/settings', {'remote_sdr_health': []}),
        ('put', '/settings/remote_sdr_health', {'value': []}),
        ('delete', '/settings/remote_sdr_health', None),
    ]:
        assert getattr(client, method)(path, json=data).status_code == 400
    probe.assert_not_called()


def test_settings_read_error_is_not_an_empty_list(monkeypatch):
    import sqlite3

    import utils.database as database
    failed = MagicMock(side_effect=sqlite3.OperationalError('unavailable'))
    monkeypatch.setattr(database, 'get_db', failed)
    with pytest.raises(sqlite3.OperationalError):
        database.get_setting('remote_sdr_health', [], strict=True)


def test_unavailable_storage_returns_503_without_writing(client, monitor, monkeypatch):
    import sqlite3

    import utils.remote_sdr_health as module
    monkeypatch.setattr(module, 'monitor', monitor)
    monkeypatch.setattr(module, 'get_setting', MagicMock(side_effect=sqlite3.OperationalError('busy')))
    write = MagicMock()
    monkeypatch.setattr(module, 'set_setting', write)
    assert client.post('/settings/remote-sdrs', json=entry()).status_code == 503
    assert client.get('/settings/remote-sdrs').status_code == 503
    write.assert_not_called()


def test_database_fallback_unchanged_for_other_callers(monkeypatch):
    import sqlite3

    import utils.database as database
    monkeypatch.setattr(database, 'get_db', MagicMock(side_effect=sqlite3.OperationalError('busy')))
    assert database.get_setting('unrelated', 'default') == 'default'
