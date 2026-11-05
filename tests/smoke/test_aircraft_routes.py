"""Route enrichment stays attached to the selected aircraft and is not guessed."""
import os

import pytest

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page


def route(origin='AMS', destination='MME'):
    return {'available': True, 'origin': {'iata': origin, 'icao': 'EHAM', 'name': 'Schiphol'},
            'destination': {'iata': destination, 'icao': 'EGNV', 'name': 'Teesside'}, 'message': 'Callsign route'}


def select(page, icao, callsign, registration=''):
    page.evaluate("""args => { aircraft[args.icao]={icao:args.icao,callsign:args.callsign,
      registration:args.registration,altitude:12000};selectedIcao=args.icao;showAircraftDetails(args.icao); }""",
                  {'icao': icao, 'callsign': callsign, 'registration': registration})


def test_selected_route_cache_and_unknown_draken(page):
    calls = []
    page.route('**/adsb/route/*', lambda r: (calls.append(r.request.url), r.fulfill(json=route())))
    select(page, 'ABCDEF', 'KLM965')
    page.wait_for_function("document.querySelector('#selectedOrigin').textContent.includes('AMS')")
    assert 'MME' in page.locator('#selectedDestination').inner_text()
    assert 'adsbdb' in page.locator('#selectedRouteSource').inner_text()
    page.evaluate("() => { for(let i=0;i<5;i++)showAircraftDetails('ABCDEF'); }")
    assert len(calls) == 1
    select(page, '407D80', 'FRA52', 'G-DKNB')
    assert page.locator('#selectedOrigin').inner_text() == 'Unknown'
    assert page.locator('#selectedDestination').inner_text() == 'Unknown'
    assert len(calls) == 1
    select(page, '123ABC', '')
    assert page.locator('#selectedOrigin').inner_text() == 'Unknown'
    assert len(calls) == 1
    assert not page.errors, page.errors


def test_late_route_cannot_overwrite_new_selection(page):
    pending = []
    page.route('**/adsb/route/KLM965', lambda r: pending.append(r))
    page.route('**/adsb/route/BAW123', lambda r: r.fulfill(json=route('LHR', 'JFK')))
    select(page, 'ABCDEF', 'KLM965')
    page.wait_for_timeout(150)
    assert pending
    select(page, 'FEDCBA', 'BAW123')
    page.wait_for_function("document.querySelector('#selectedOrigin').textContent.includes('LHR')")
    pending[0].fulfill(json=route())
    assert 'LHR' in page.locator('#selectedOrigin').inner_text()
    assert 'JFK' in page.locator('#selectedDestination').inner_text()


def test_lookup_failure_and_untrusted_names(page):
    data = route()
    data['origin']['name'] = '<img src=x onerror=alert(1)>'
    page.route('**/adsb/route/KLM965', lambda r: r.fulfill(json=data))
    select(page, 'ABCDEF', 'KLM965')
    page.wait_for_function("document.querySelector('#selectedOrigin').textContent.includes('<img')")
    assert page.locator('#selectedOrigin img').count() == 0
    page.route('**/adsb/route/BAW123', lambda r: r.fulfill(status=503, json={}))
    select(page, 'FEDCBA', 'BAW123')
    page.wait_for_function("document.querySelector('#selectedOrigin').textContent === 'Unknown'")
    assert 'unavailable' in page.locator('#selectedRouteSource').inner_text().lower()


@pytest.mark.parametrize('width,height', [(1600, 1000), (390, 844)])
def test_long_airport_names_remain_visible(page, width, height):
    page.set_viewport_size({'width': width, 'height': height})
    data = route()
    data['origin']['name'] = 'Amsterdam Airport Schiphol'
    data['destination']['name'] = 'Teesside International Airport'
    page.route('**/adsb/route/KLM965', lambda r: r.fulfill(json=data))
    select(page, 'ABCDEF', 'KLM965')
    page.wait_for_function("document.querySelector('#selectedOrigin').textContent.includes('Schiphol')")
    for name in ('selectedOrigin', 'selectedDestination'):
        assert page.locator('#'+name).evaluate('el=>el.scrollWidth<=el.clientWidth+1')
    pane = page.locator('#selectedInfo')
    assert pane.evaluate('el=>el.scrollHeight<=el.clientHeight+1')
    if os.environ.get('INTERCEPT_TEESSIDE_SCREENSHOTS'):
        pane.screenshot(path=f'/private/tmp/selected-route-{width}.png')
