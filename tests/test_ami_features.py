"""AMI feature discovery, exact counts and passive runtime summaries."""
import json
import re
from pathlib import Path

import pytest

from utils import ami
from utils.cleanup import DataStore


def test_manifest_features_match_contract_and_modes(anon_client, monkeypatch):
    monkeypatch.setenv('AMI_URL', 'https://ami.example.test')
    features = anon_client.get('/.well-known/ami-module.json').get_json()['features']
    assert 30 <= len(features) <= 40
    ids = {f['id'] for f in features}
    assert len(ids) == len(features)
    registry = (Path(__file__).resolve().parents[1] / 'static/js/mode-registry.js').read_text()
    modes = set(re.findall(r'^    (\w+): \{', registry, re.M))
    assert {m.replace('_', '-') for m in modes} <= ids
    for f in features:
        assert re.fullmatch(r'[a-z0-9-]{1,40}', f['id'])
        assert 0 < len(f['name']) <= 60
        assert 0 < len(f['summary']) <= 200
        assert 0 < len(f['where']) <= 80
        assert len(f['aliases']) <= 10 and all(0 < len(a) <= 40 for a in f['aliases'])
        assert len(f['tools']) <= 5
        assert set(f['tools']) <= {tool['name'] for tool in ami.TOOLS}
    by_id = {f['id']: f for f in features}
    assert by_id['spaceweather']['name'] == 'SPACE WX'
    assert {'space weather', 'aurora', 'Kp', 'solar flares', 'geomagnetic storm'} <= set(by_id['spaceweather']['aliases'])
    assert {'ADS-B', 'ADSB', 'planes', 'aircraft', 'flights'} <= set(by_id['adsb']['aliases'])
    assert {'ships', 'vessels', 'boats'} <= set(by_id['ais']['aliases'])
    assert {'acars', 'vdl2', 'meshtastic', 'meshcore', 'iss'} <= ids
    for name in ('wifi', 'bluetooth'):
        assert 'identities' in by_id[name]['summary']


@pytest.mark.parametrize('kind,attr', [('aircraft', 'adsb_aircraft'), ('vessels', 'ais_vessels')])
def test_contact_counts_are_exact_independent_of_sample(monkeypatch, kind, attr):
    import app as runtime
    now = 1800000000
    monkeypatch.setattr(ami.time, 'time', lambda: now)
    store = DataStore(max_age_seconds=60)
    for i in range(75):
        store.set(str(i), {'icao': str(i), 'mmsi': str(i), 'raw': 'private'})
    store.timestamps.update({'0': now - 61, '1': now - 60})
    store.timestamps.pop('2')
    monkeypatch.setattr(runtime, attr, store)
    result = ami.contacts(kind, 2)
    data = result['data']
    assert data['total'] == 75 and data['fresh'] == 73 and data['stale'] == 2
    assert len(data['contacts']) == 2
    assert data['lastMessageAt'] == ami.iso(now)
    assert result['asOf'] == ami.iso(now) and result['stale'] is False
    assert 'private' not in json.dumps(result)
    assert ami.contacts(kind, 50)['data']['total'] == 75


def test_contact_counts_empty_and_stale(monkeypatch):
    import app as runtime
    store = DataStore(max_age_seconds=60)
    monkeypatch.setattr(runtime, 'adsb_aircraft', store)
    empty = ami.contacts('aircraft', 1)
    assert empty['data'] == {'contacts': [], 'total': 0, 'fresh': 0, 'stale': 0, 'lastMessageAt': None}
    assert empty['stale'] and empty['asOf'] is None
    store.set('a', {'icao': 'a'})
    store.timestamps['a'] -= 61
    stale = ami.contacts('aircraft', 1)
    assert stale['data']['fresh'] == 0 and stale['data']['stale'] == 1
    assert stale['data']['contacts'][0]['stale'] and stale['stale']


def test_overview_reports_remote_activity_and_privacy(monkeypatch):
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock

    import app as runtime
    from routes import adsb, ais
    from utils.ami_features import features

    monkeypatch.setattr(adsb, 'adsb_using_service', True)
    monkeypatch.setattr(ais, 'ais_running', True)
    monkeypatch.setattr(runtime, 'adsb_process', None)
    monkeypatch.setattr(runtime, 'ais_process', None)
    store = DataStore(max_age_seconds=60)
    store.set('a', {'icao': 'a', 'raw': 'secret-payload'})
    monkeypatch.setattr(runtime, 'adsb_aircraft', store)
    monkeypatch.setattr(runtime, 'wifi_networks', store)
    # Reads must not construct clients, even when a getter would do so.
    forbidden = Mock(side_effect=AssertionError('must not construct or probe'))
    monkeypatch.setitem(sys.modules, 'utils.weather_sat', SimpleNamespace(_decoder=None, get_weather_sat_decoder=forbidden))
    monkeypatch.setitem(sys.modules, 'utils.meshcore', SimpleNamespace(
        _client=SimpleNamespace(get_state=lambda: (SimpleNamespace(value='connected'), 'secret-address'),
                                _lock=__import__('threading').Lock(), _messages=[]),
        get_meshcore_client=forbidden))
    result = ami.call_tool('get_overview', {})
    rows = {r['id']: r for r in result['data']}
    assert set(rows) == {f['id'] for f in features()}
    assert rows['adsb']['state'] == rows['ais']['state'] == rows['meshcore']['state'] == 'running'
    assert rows['adsb']['count'] == 1 and rows['adsb']['lastMessageAt'] == ami.contacts('aircraft', 1)['data']['lastMessageAt']
    assert rows['weathersat']['state'] == 'idle'
    assert rows['spaceweather']['monitored'] is False
    assert rows['wifi']['count'] >= 1
    assert 'secret' not in json.dumps(result) and 'icao' not in json.dumps(result)
    forbidden.assert_not_called()


def test_overview_message_window_is_not_lifetime_count(monkeypatch):
    import sys
    from collections import deque
    from types import SimpleNamespace
    now = 1800000000
    monkeypatch.setattr(ami.time, 'time', lambda: now)
    monkeypatch.setitem(sys.modules, 'utils.flight_correlator', SimpleNamespace(_correlator=SimpleNamespace(
        _acars_messages=deque([{'_corr_time': now-3601, 'text': 'secret'}, {'_corr_time': now-5, 'text': 'secret'}]),
        _vdl2_messages=deque())))
    rows = {r['id']: r for r in ami.call_tool('get_overview', {})['data']}
    assert rows['acars']['count'] == 1
    assert rows['acars']['countScope'] == 'retained messages in the last hour'
    assert rows['acars']['lastMessageAt'] == ami.iso(now-5)
    assert rows['vdl2']['count'] == 0
    assert 'secret' not in json.dumps(rows)


def test_invalid_contact_timestamps_are_stale(monkeypatch):
    import app as runtime
    store = DataStore(max_age_seconds=60)
    for key, stamp in [('a', float('nan')), ('b', float('inf')), ('c', 'invalid')]:
        store.set(key, {'icao': key})
        store.timestamps[key] = stamp
    monkeypatch.setattr(runtime, 'adsb_aircraft', store)
    result = ami.contacts('aircraft', 3)
    assert result['data']['total'] == 3 and result['data']['stale'] == 3
    assert result['data']['lastMessageAt'] is None and result['stale']


def test_overview_mesh_message_sql_uses_only_counts(monkeypatch, tmp_path):
    import sqlite3

    from utils import database
    now = 1800000000
    monkeypatch.setattr(ami.time, 'time', lambda: now)
    path = tmp_path / 'messages.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE meshtastic_messages (received_at REAL, message TEXT)')
        db.executemany('INSERT INTO meshtastic_messages VALUES (?, ?)', [(now-1, 'secret'), (now-3601, 'secret')])
    monkeypatch.setattr(database, 'DB_PATH', path)
    rows = {r['id']: r for r in ami.call_tool('get_overview', {})['data']}
    assert rows['meshtastic']['count'] == 1
    assert rows['meshtastic']['countScope'] == 'stored messages in the last hour'
    assert rows['meshtastic']['lastMessageAt'] == ami.iso(now-1)
    assert 'secret' not in json.dumps(rows)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'missing.db')
    rows = {r['id']: r for r in ami.call_tool('get_overview', {})['data']}
    assert rows['meshtastic']['count'] is None
    assert not (tmp_path / 'missing.db').exists()


def test_overview_reports_running_utility_meter_decoder(monkeypatch):
    from unittest.mock import Mock

    import app as runtime
    monkeypatch.setattr(runtime, 'rtlamr_process', Mock(poll=lambda: None))
    rows = {r['id']: r for r in ami.call_tool('get_overview', {})['data']}
    assert rows['rtlamr']['state'] == 'running' and rows['rtlamr']['monitored']
