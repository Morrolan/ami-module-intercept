"""Selected-only callsign enrichment must fail safely and avoid repeated requests."""
import json
from unittest.mock import Mock

import pytest

from utils import aircraft_routes as routes


def response(body, status=200):
    result = Mock(status_code=status)
    result.iter_content.return_value = [json.dumps(body).encode()]
    return result


def test_callsign_route_whitelist_cache_and_missing(monkeypatch):
    raw = {'response': {'flightroute': {'callsign_icao': 'KLM965',
        'origin': {'iata_code': 'AMS', 'icao_code': 'EHAM', 'name': 'Schiphol', 'private_extra': 'ignore',
                   'country_name': 'Netherlands', 'country_iso_name': 'NL', 'municipality': 'Amsterdam',
                   'elevation': -11, 'latitude': 52.3086, 'longitude': 4.76389},
        'destination': {'iata_code': 'MME', 'icao_code': 'EGNV', 'name': 'Teesside',
                        'country_iso_name': '<b>', 'elevation': True, 'latitude': 400, 'longitude': '1'}}}}
    get = Mock(return_value=response(raw))
    monkeypatch.setattr(routes.requests, 'get', get)
    cache = routes.RouteCache()
    result = cache.get('KLM965')
    assert result['available'] and result['origin'] == {
        'iata': 'AMS', 'icao': 'EHAM', 'name': 'Schiphol', 'municipality': 'Amsterdam', 'country': 'Netherlands',
        'country_code': 'NL', 'elevation_ft': -11, 'lat': 52.3086, 'lon': 4.76389}
    destination = result['destination']
    assert destination['iata'] == 'MME' and destination['country_code'] == '' and destination['country'] == ''
    assert destination['elevation_ft'] is None and destination['lat'] is None and destination['lon'] is None
    assert cache.get('KLM965') == result and get.call_count == 1
    get.return_value = response({'response': 'unknown callsign'}, status=404)
    assert not cache.get('KLM999')['available']
    assert not cache.get('KLM999')['available']
    assert get.call_count == 2
    with pytest.raises(ValueError):
        cache.get('../unknown')
    assert get.call_count == 2


def test_route_failures_are_unknown_and_bounded(monkeypatch):
    get = Mock(side_effect=TimeoutError('sensitive details'))
    monkeypatch.setattr(routes.requests, 'get', get)
    result = routes.RouteCache().get('KLM965')
    assert not result['available'] and result['origin'] is None
    assert 'sensitive' not in result['message']
    oversized = response({})
    oversized.iter_content.return_value = [b'x' * 65537]
    get.side_effect = None
    get.return_value = oversized
    assert not routes.RouteCache().get('KLM965')['available']
    assert oversized.close.called


def test_aircraft_route_endpoint(client, anon_client, monkeypatch):
    monkeypatch.setattr(routes.route_cache, 'get', lambda call: {'callsign': call, 'available': False})
    assert client.get('/adsb/route/KLM965').json['callsign'] == 'KLM965'
    assert anon_client.get('/adsb/route/KLM965').status_code in (302, 401)
