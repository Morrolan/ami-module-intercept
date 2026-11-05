"""The aircraft key explains real map markers and works without a selection."""
import os

import pytest

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page


@pytest.mark.parametrize('embedded,theme,width,height', [
    (False, 'dark', 1600, 1000), (True, 'dark', 390, 844),
    (False, 'light', 720, 450), (True, 'light', 1600, 1000),
])
def test_key_matches_markers_and_remains_accessible(page, embedded, theme, width, height):
    page.set_viewport_size({'width': width, 'height': height})
    page.goto(page.url.split('?')[0] + ('?ami=1' if embedded else ''), wait_until='domcontentloaded')
    page.evaluate('theme => document.documentElement.dataset.theme = theme', theme)
    button = page.get_by_role('button', name='Aircraft colour key', exact=True)
    button.click(timeout=3000)
    # The hover explanation also has role=dialog and the same short title.
    dialog = page.locator('#aircraftKeyDialog')
    assert dialog.is_visible()
    assert dialog.get_attribute('aria-labelledby') == 'aircraftKeyTitle'
    assert page.evaluate('selectedIcao') is None
    for altitude in (0, 5000, 15000, 30000, 40000):
        row = dialog.locator(f'[data-altitude="{altitude}"]')
        expected = page.evaluate('alt => getAltitudeColor(alt)', altitude)
        assert expected.lower() in row.locator('svg').get_attribute('style').lower()
    assert '35,000' in dialog.inner_text()
    assert dialog.locator('[data-key="military"] .aircraft-military').count() == 1
    assert dialog.locator('[data-key="ground"] .ti-ground').count() == 1
    assert dialog.locator('[data-key="emergency"] .ti-alert').count() == 1
    assert dialog.locator('[data-key="selected"] .tracking-ring').count() == 1
    assert dialog.locator('.aircraft-key-shapes .ti-shape').count() == 8
    box = dialog.bounding_box()
    assert box['x'] >= 15 and box['y'] >= 15, box
    assert box['x'] + box['width'] <= width and box['y'] + box['height'] <= height, box
    # The final section can be scrolled into view rather than clipped away.
    last = dialog.locator('.aircraft-key-shapes li').last
    last.scroll_into_view_if_needed()
    last_box = last.bounding_box()
    assert last_box['y'] >= box['y'] and last_box['y'] + last_box['height'] <= box['y'] + box['height']
    if os.environ.get('INTERCEPT_KEY_SCREENSHOTS'):
        dialog.screenshot(path=f'/private/tmp/aircraft-key-{theme}-{width}.png')
    page.keyboard.press('Escape')
    dialog.wait_for(state='hidden', timeout=3000)
    assert button.evaluate('element => element === document.activeElement')
    button.click()
    dialog.get_by_role('button', name='Close aircraft key').click()
    assert not dialog.is_visible()
    button.click()
    page.mouse.click(2, 2)
    dialog.wait_for(state='hidden', timeout=3000)
    assert not page.errors, page.errors
