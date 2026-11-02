"""NOAA tool uses existing fetchers/caches and emits only its allowlist."""
import json

import pytest

from routes import space_weather as sw
from utils import ami

NOW = 1793620800  # 2026-11-02 12:00 UTC


@pytest.fixture
def noaa(monkeypatch):
    monkeypatch.setattr(ami.time, 'time', lambda: NOW)
    monkeypatch.setattr(sw, '_cache', {})
    payloads = {
        'kp_index': [['time_tag', 'Kp'], ['2026-11-02 09:00:00', '3.33'], ['2026-11-02 06:00:00', '2']],
        'kp_forecast': [['time_tag', 'kp', 'observed', 'noaa_scale'],
                        ['2026-11-02 09:00:00', '3', 'observed', 'G0'],
                        ['2026-11-02 15:00:00', '5', 'predicted', 'G1'],
                        ['2026-11-06 15:00:00', '4', 'predicted', 'G0']],
        'scales': {'0': {'DateStamp': '2026-11-02', 'TimeStamp': '12:00:00', 'R': {'Scale': '1', 'Text': 'private'}, 'S': {'Scale': '0'}, 'G': {'Scale': '2'}}},
        'flux': [['time_tag', 'flux'], ['2026-11-01 20:00:00', '145.2']],
        'alerts': [{'product_id': 'WARK05', 'issue_datetime': '2026-11-02 10:00:00', 'title': 'Geomagnetic warning', 'message': 'WARNING: Geomagnetic warning\nValid To: 2026 Nov 02 1800 UTC\nFULL BODY MUST NOT LEAK'}],
        'sw_plasma': [['time_tag', 'proton_speed'], ['2026-11-02 11:59:00', '450']],
        'sw_mag': [['time_tag', 'bz_gsm'], ['2026-11-02 11:58:00', '-4.2']],
    }
    fetch_names = {'kp_index': '_fetch_kp_index', 'kp_forecast': '_fetch_kp_forecast', 'scales': '_fetch_scales',
                   'flux': '_fetch_flux', 'alerts': '_fetch_alerts', 'sw_plasma': '_fetch_solar_wind_plasma',
                   'sw_mag': '_fetch_solar_wind_mag'}
    for key, name in fetch_names.items():
        def fetch(key=key):
            sw._cache_set(key, payloads[key], 300)
            return payloads[key]
        monkeypatch.setattr(sw, name, fetch)
    return payloads


def test_space_weather_sanitized_latest_and_forecast(noaa):
    result = ami.call_tool('get_space_weather', {})
    data = result['data']
    assert data['kp']['value'] == 3.33
    assert data['kp']['time'] == '2026-11-02T09:00:00+00:00'
    assert len(data['kpForecast']) == 1 and data['kpForecast'][0]['value'] == 5
    assert data['scales'] == {'R': 1, 'S': 0, 'G': 2}
    assert data['flux']['value'] == 145.2
    assert data['solarWind']['speed']['value'] == 450
    assert data['solarWind']['bz']['value'] == -4.2
    assert data['alerts'] == [{'title': 'Geomagnetic warning', 'issuedAt': '2026-11-02T10:00:00+00:00'}]
    assert result['sources'] == [{'name': 'NOAA SWPC', 'health': 'ok'}]
    assert result['asOf'] == ami.iso(NOW) and result['stale'] is False
    assert 'FULL BODY' not in json.dumps(result) and 'private' not in json.dumps(result)


def test_space_weather_partial_failure_and_expired_cache(noaa, monkeypatch):
    sw._cache['sw_mag'] = {'data': noaa['sw_mag'], 'expires': NOW-1, 'fetchedAt': NOW-301}
    monkeypatch.setattr(sw, '_fetch_solar_wind_mag', lambda: None)
    monkeypatch.setattr(sw, '_fetch_flux', lambda: None)
    result = ami.call_tool('get_space_weather', {})
    assert result['stale'] and result['asOf'] == ami.iso(NOW-301)
    assert result['data']['solarWind']['bz']['value'] == -4.2
    assert {'bz', 'flux'} <= set(result['data']['staleFields'])
    assert 'flux' in result['data']['missing'] and result['data']['flux'] is None


def test_space_weather_malformed_values_never_become_zero(noaa):
    noaa['kp_index'] = [['time_tag', 'Kp'], ['bad time', '3'], ['2026-11-02 09:00:00', 'nan']]
    noaa['sw_plasma'] = {'unexpected': 'secret'}
    noaa['scales'] = {'0': {'R': {'Scale': 'bad'}, 'G': {'Scale': '99'}}}
    noaa['alerts'] = [None, {'message': 'secret'}]
    result = ami.call_tool('get_space_weather', {})
    assert result['stale']
    assert result['data']['kp'] is None
    assert result['data']['solarWind']['speed'] is None
    assert result['data']['scales'] == {'R': None, 'S': None, 'G': None}
    assert result['data']['alerts'] == []
    assert 'NaN' not in json.dumps(result) and 'secret' not in json.dumps(result)


def test_existing_fresh_cache_makes_no_network_calls(monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setattr(sw, '_cache', {})
    forbidden = Mock(side_effect=AssertionError('fresh cache must not fetch'))
    monkeypatch.setattr(sw, '_fetch_json', forbidden)
    # An empty response is still cached, rather than repeatedly downloaded.
    for key in ('kp_index', 'kp_forecast', 'scales', 'flux', 'alerts', 'sw_plasma', 'sw_mag'):
        sw._cache_set(key, [] if key != 'scales' else {}, 300)
    result = ami.call_tool('get_space_weather', {})
    assert result['stale']  # Missing readings, despite a fresh HTTP snapshot.
    forbidden.assert_not_called()


def test_space_weather_old_observations_and_malformed_scales(noaa):
    noaa['kp_index'] = [['time_tag', 'Kp'], ['2026-10-30 09:00:00', '3']]
    noaa['scales'] = {'0': ['not a scale object']}
    result = ami.call_tool('get_space_weather', {})
    assert result['stale']
    assert {'kp', 'scales'} <= set(result['data']['staleFields'])


def test_alerts_only_current_validity_latest_product_and_headlines(noaa):
    noaa['alerts'] = [
        {'product_id': 'W1', 'issue_datetime': '2026-11-02 11:00:00',
         'message': 'Space Weather Message Code: WARK05\n\nWARNING: Geomagnetic K-index of 5 expected\nValid From: 2026 Nov 02 1000 UTC\nValid To: 2026 Nov 02 1800 UTC\nFULL BODY MUST NOT LEAK'},
        {'product_id': 'W2', 'issue_datetime': '2026-11-01 11:00:00',
         'message': 'WARNING: Expired warning\nValid To: 2026 Nov 01 1800 UTC'},
        {'product_id': 'W3', 'issue_datetime': '2026-11-02 11:00:00',
         'message': 'CANCEL WARNING: Cancelled warning'},
        {'product_id': 'W3', 'issue_datetime': '2026-11-02 10:00:00',
         'message': 'WARNING: Superseded warning\nValid To: 2026 Nov 02 1800 UTC'},
        {'product_id': 'A1', 'issue_datetime': '2026-11-02 11:00:00',
         'message': 'ALERT: Threshold reached\nNo expiry supplied'},
    ]
    result = ami.call_tool('get_space_weather', {})
    assert result['data']['alerts'] == [{'title': 'WARNING: Geomagnetic K-index of 5 expected',
                                         'issuedAt': '2026-11-02T11:00:00+00:00'}]
    assert result['data']['recentAlerts'] == [{'title': 'ALERT: Threshold reached',
                                               'issuedAt': '2026-11-02T11:00:00+00:00'}]
    assert 'FULL BODY' not in json.dumps(result)


def test_malformed_alert_list_is_not_a_fresh_empty_result(noaa):
    noaa['alerts'] = [None, {'message': 'secret'}]
    result = ami.call_tool('get_space_weather', {})
    assert result['stale']
    assert 'alerts' in result['data']['missing']


@pytest.mark.parametrize('date,time', [('2020-01-01', '00:00:00'), ('bad', 'bad'), (None, None)])
def test_scales_observation_time_is_not_cache_fetch_time(noaa, date, time):
    noaa['scales']['0'].update(DateStamp=date, TimeStamp=time)
    result = ami.call_tool('get_space_weather', {})
    assert result['stale'] and 'scales' in result['data']['staleFields']
    assert result['data']['scalesAsOf'] != ami.iso(NOW)
