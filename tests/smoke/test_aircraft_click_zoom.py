"""Aircraft selection can leave the map fixed, with a device-local preference."""
import pytest

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page


@pytest.mark.parametrize('embedded,width,theme', [
    (False, 1600, 'dark'), (False, 390, 'light'),
    (True, 1600, 'light'), (True, 390, 'dark'),
])
def test_click_zoom_keeps_map_fixed_and_remembers_choice(page, embedded, width, theme):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(page.url.split('?')[0] + ('?ami=1' if embedded else ''))
    page.evaluate('theme => document.documentElement.dataset.theme = theme', theme)
    button = page.get_by_role('button', name='Click zoom: ON', exact=True)
    button.click(timeout=3000)
    assert page.locator('#clickZoomBtn').get_attribute('aria-pressed') == 'false'
    page.reload()
    button = page.get_by_role('button', name='Click zoom: OFF', exact=True)
    assert button.get_attribute('aria-pressed') == 'false'
    page.evaluate("updateAircraft({icao:'ABCDEF',callsign:'TEST123',lat:52,lon:1,altitude:12000})")
    page.wait_for_timeout(700)  # Let initial map sizing and the aircraft list settle.
    result = page.evaluate("""() => {
        radarMap.stop(); radarMap.setView([54, -1], 7, {animate:false});
        const before = {center:radarMap.getCenter(), zoom:radarMap.getZoom()};
        updateMarkerImmediate('ABCDEF');
        for (const source of ['map','panel','message']) selectAircraft('ABCDEF', source);
        return {before, after:{center:radarMap.getCenter(),zoom:radarMap.getZoom()},
                selected:selectedIcao, icon:markers.ABCDEF.getElement().innerHTML};
    }""")
    page.wait_for_timeout(2200)  # Also catch a delayed second zoom stage.
    assert result['before'] == result['after']
    assert page.evaluate('({center:radarMap.getCenter(),zoom:radarMap.getZoom()})') == result['before']
    assert result['selected'] == 'ABCDEF'
    assert 'tracking-ring' in result['icon']
    assert 'TEST123' in page.locator('.selected-callsign').inner_text()
    button.click()
    page.evaluate("selectAircraft('ABCDEF', 'map')")
    page.wait_for_function('radarMap.getZoom() > 7')
    # Disabling during the first stage must cancel any queued second stage.
    page.get_by_role('button', name='Click zoom: ON', exact=True).click()
    page.wait_for_timeout(350)  # Allow Leaflet's current CSS transition to settle.
    stopped = page.evaluate('({center:radarMap.getCenter(),zoom:radarMap.getZoom()})')
    page.wait_for_timeout(2200)
    assert page.evaluate('({center:radarMap.getCenter(),zoom:radarMap.getZoom()})') == stopped
    assert not page.errors, page.errors
