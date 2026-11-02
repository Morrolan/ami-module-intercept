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
        assert set(f['tools']) <= {'get_overview', 'get_contacts', 'get_space_weather'}
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
