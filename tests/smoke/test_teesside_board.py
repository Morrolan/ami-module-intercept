"""Airport schedules and received Draken aircraft remain clearly distinct."""
import os

import pytest

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page
DATA = {'available': True, 'stale': False, 'error': None,
        'fetched_at': '2026-11-05T10:00:00+00:00', 'timezone': 'Europe/London',
        'arrivals': [{'date': '2026-11-05', 'flight': 'KL965', 'place': 'Amsterdam',
                      'scheduled': '16:55', 'scheduled_at': '2026-11-05T16:55:00+00:00', 'status': 'On Time', 'remarks': '-'}],
        'departures': [{'date': '2026-11-06', 'flight': 'FR5986', 'place': 'Alicante',
                        'scheduled': '12:50', 'scheduled_at': '2026-11-06T12:50:00+00:00',
                        'expected_at': '2026-11-06T13:10:00+00:00', 'status': 'Delayed', 'remarks': 'Expected 13:10'}]}


@pytest.mark.parametrize('theme,width,height,embedded', [
    ('dark', 1600, 1000, False), ('light', 390, 844, True), ('dark', 720, 450, True),
])
def test_airport_dates_status_and_received_draken(page, theme, width, height, embedded):
    requests = []
    page.route('**/adsb/teesside', lambda route: (requests.append(route.request.url), route.fulfill(json=DATA)))
    page.goto(page.url.split('?')[0] + ('?ami=1' if embedded else ''), wait_until='domcontentloaded')
    page.set_viewport_size({'width': width, 'height': height})
    page.evaluate('theme => document.documentElement.dataset.theme=theme', theme)
    page.evaluate("Date.now = () => new Date('2026-11-05T16:40:00Z').getTime()")
    assert not requests
    page.get_by_role('button', name='Teesside airport board').click(timeout=3000)
    dialog = page.locator('#teessideDialog')
    page.wait_for_function("document.querySelector('#teessideFlights').textContent.includes('KL965')")
    assert 'Amsterdam' in dialog.inner_text()
    assert 'Europe/London' in dialog.inner_text()
    assert '15 min' in dialog.locator('#teessideNext').inner_text()
    assert 'Expected in 20 hr 30 min' in dialog.locator('#teessideNext').inner_text()
    if os.environ.get('INTERCEPT_TEESSIDE_SCREENSHOTS'):
        dialog.screenshot(path=f'/private/tmp/teesside-board-{theme}-{width}.png')
    assert dialog.get_by_role('link', name='Official airport board').get_attribute('href') == 'https://www.teessideinternational.com/arrivals-departures/'
    dialog.get_by_role('button', name='Departures', exact=True).click()
    dialog.get_by_label('Flight date').select_option('2026-11-06')
    assert 'Alicante' in dialog.inner_text() and 'Expected 13:10' in dialog.inner_text()
    page.evaluate("""aircraft={
        '407D80': {icao:'407D80',registration:'G-DKNB',callsign:'PIRATE11',altitude:12000,lastSeen:Date.now()},
        'ABC123': {icao:'ABC123',registration:'G-ABCD',callsign:'FRA99',lastSeen:Date.now()},
        'DEF456': {icao:'DEF456',callsign:'ZODIAC01',lastSeen:Date.now()}
    }""")
    dialog.get_by_role('button', name='Draken — received aircraft', exact=True).click()
    assert 'G-DKNB' in dialog.inner_text() and 'PIRATE11' in dialog.inner_text()
    assert 'G-ABCD' not in dialog.inner_text() and 'ZODIAC01' not in dialog.inner_text()
    assert 'not a flight timetable' in dialog.inner_text()
    box = dialog.bounding_box()
    assert box['x'] >= 15 and box['y'] >= 15
    assert box['x'] + box['width'] <= width and box['y'] + box['height'] <= height
    if os.environ.get('INTERCEPT_TEESSIDE_SCREENSHOTS'):
        dialog.screenshot(path=f'/private/tmp/teesside-{theme}-{width}.png')
    page.keyboard.press('Escape')
    dialog.wait_for(state='hidden')
    assert not page.errors, page.errors


@pytest.mark.parametrize('button,frequency', [('Listen to Tower', 119.8), ('Listen to Approach', 118.85)])
def test_listen_buttons_are_manual_and_use_carrier_frequencies(page, button, frequency):
    page.route('**/adsb/teesside', lambda r: r.fulfill(json=DATA))
    page.evaluate("() => { window.airportTunes=[];window.startAirband=async()=>airportTunes.push(getAirbandFrequency()); }")
    page.get_by_role('button', name='Teesside airport board').click(timeout=3000)
    assert page.evaluate('airportTunes') == []
    page.get_by_role('button', name=button, exact=False).click()
    assert page.evaluate('airportTunes') == [frequency]
    assert page.evaluate('getAirbandFrequency()') == frequency


@pytest.mark.parametrize('status', [200, 503])
def test_listen_waits_for_existing_audio_to_stop(page, status):
    pending = []
    page.route('**/adsb/teesside', lambda r: r.fulfill(json=DATA))
    page.route('**/receiver/audio/stop', lambda r: pending.append(r))
    page.evaluate("() => { isAirbandPlaying=true;window.airportTunes=[];window.startAirband=async()=>airportTunes.push(getAirbandFrequency()); }")
    page.get_by_role('button', name='Teesside airport board').click()
    page.get_by_role('button', name='Listen to Tower', exact=False).click()
    page.wait_for_timeout(100)
    assert pending and page.evaluate('airportTunes') == []
    pending[0].fulfill(status=status, json={'status': 'stopped' if status == 200 else 'error'})
    if status == 200:
        page.wait_for_function('airportTunes.length === 1')
        assert page.evaluate('airportTunes') == [119.8]
    else:
        page.wait_for_function("document.querySelector('#teessideRadioStatus').textContent.includes('Could not stop')")
        assert page.evaluate('airportTunes') == []


def test_airport_stale_failure_and_upstream_text_safety(page):
    data = {**DATA, 'stale': True, 'error': 'Airport unavailable', 'arrivals': [
        {**DATA['arrivals'][0], 'place': '<img src=x onerror=alert(1)>'}]}
    page.route('**/adsb/teesside', lambda r: r.fulfill(json=data))
    page.get_by_role('button', name='Teesside airport board').click(timeout=3000)
    page.wait_for_function("document.querySelector('#teessideFlights').textContent.includes('<img')")
    assert page.locator('#teessideDialog img').count() == 0
    assert 'stale' in page.locator('#teessideFreshness').inner_text().lower()
    data.update(available=False, arrivals=[], departures=[], error='Airport unavailable')
    page.get_by_role('button', name='Refresh airport board').click()
    page.wait_for_function("document.querySelector('#teessideFlights').textContent.includes('unavailable')")
    assert 'No published flights' not in page.locator('#teessideFlights').inner_text()
    assert not page.errors, page.errors
