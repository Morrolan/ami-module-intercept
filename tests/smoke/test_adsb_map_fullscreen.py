"""The ADS-B map has a full screen toggle, native or window-filling fallback."""
import pytest

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page


def _map_box(page):
    return page.evaluate("""() => {
        const r = document.getElementById('radarMap').getBoundingClientRect();
        return {w: Math.round(r.width), h: Math.round(r.height),
                leaflet: radarMap.getSize().x, vw: innerWidth, vh: innerHeight};
    }""")


def _center_shift_px(page, center):
    return page.evaluate("""c => radarMap.project(radarMap.getCenter())
        .distanceTo(radarMap.project(L.latLng(c.lat, c.lng)))""", center)


@pytest.mark.parametrize('embedded,width', [(False, 1600), (True, 390)])
@pytest.mark.parametrize('native', [True, False])
def test_map_fullscreen_toggle(page, embedded, width, native):
    page.set_viewport_size({'width': width, 'height': 900})
    if not native:
        page.add_init_script("Object.defineProperty(Document.prototype, 'fullscreenEnabled', {get: () => false})")
    page.goto(page.url.split('?')[0] + ('?ami=1' if embedded else ''))
    page.wait_for_function('window.radarMap')
    page.wait_for_timeout(700)  # Let initial map sizing settle.
    before = _map_box(page)
    center = page.evaluate('radarMap.getCenter()')

    page.get_by_role('button', name='Full screen map', exact=True).click(timeout=3000)
    exit_button = page.get_by_role('button', name='Exit full screen', exact=True)
    assert exit_button.get_attribute('aria-pressed') == 'true'
    if native:
        page.wait_for_function("document.fullscreenElement?.classList.contains('display-container')")
    else:
        assert page.evaluate("document.querySelector('.display-container').classList.contains('map-fullscreen')")
    page.wait_for_function('radarMap.getSize().x === innerWidth')
    full = _map_box(page)
    assert (full['w'], full['h']) == (full['vw'], full['vh'])
    assert full['h'] > before['h']
    assert _center_shift_px(page, center) < 1.5

    if native:
        exit_button.click()
    else:
        page.keyboard.press('Escape')
    page.get_by_role('button', name='Full screen map', exact=True).wait_for(timeout=3000)
    page.wait_for_function(f"radarMap.getSize().y === {before['h']}")
    assert _map_box(page)['h'] == before['h']
    assert _center_shift_px(page, center) < 1.5
    assert not page.errors, page.errors
