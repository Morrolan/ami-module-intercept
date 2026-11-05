"""Named airband presets survive reloads without starting or retuning a radio."""
import json
import os

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page


def test_add_rename_reload_and_remove_named_frequency(page):
    audio_requests = []
    page.on('request', lambda request: audio_requests.append(request.url)
            if request.method == 'POST' and '/receiver/audio/' in request.url else None)
    page.click('#airbandChip')
    page.select_option('#airbandFreqSelect', 'custom')
    page.fill('#airbandCustomFreq', '119.805')
    page.fill('#airbandPresetName', 'Local approach')
    page.click('#airbandPresetSave')
    option = page.locator('#airbandFreqSelect option:checked')
    assert option.inner_text() == 'Local approach · 119.805 MHz'
    assert page.evaluate('getAirbandFrequency()') == 119.805
    assert 'Local approach' in page.locator('#airbandChipFreq').inner_text()
    for width, height in ((1600, 1000), (390, 844), (720, 450)):
        page.set_viewport_size({'width': width, 'height': height})
        page.evaluate('positionAirbandPanel()')
        box = page.locator('#airbandPanel').bounding_box()
        assert box['x'] >= 0 and box['y'] >= 0, box
        assert box['x'] + box['width'] <= width and box['y'] + box['height'] <= height, box
        if os.environ.get('INTERCEPT_AIRBAND_SCREENSHOTS'):
            page.screenshot(path=f'/private/tmp/airband-presets-{width}.png', full_page=True)
    page.set_viewport_size({'width': 1600, 'height': 1000})
    saved = page.input_value('#airbandFreqSelect')
    page.reload(wait_until='domcontentloaded')
    page.click('#airbandChip')
    page.select_option('#airbandFreqSelect', saved)
    assert page.evaluate('getAirbandFrequency()') == 119.805
    assert page.input_value('#airbandPresetName') == 'Local approach'
    page.fill('#airbandPresetName', 'Approach west')
    page.click('#airbandPresetSave')
    assert 'Approach west' in page.locator('#airbandFreqSelect option:checked').inner_text()
    assert len(json.loads(page.evaluate("localStorage.getItem('airband.frequencyPresets')"))) == 1
    page.click('#airbandPresetRemove')
    assert page.input_value('#airbandFreqSelect') == 'custom'
    assert page.evaluate('getAirbandFrequency()') == 119.805
    assert json.loads(page.evaluate("localStorage.getItem('airband.frequencyPresets')")) == []
    assert not audio_requests
    assert not page.errors, page.errors


def test_invalid_frequency_and_empty_name_are_not_saved(page):
    page.click('#airbandChip')
    page.select_option('#airbandFreqSelect', 'custom')
    page.fill('#airbandCustomFreq', '433.92')
    page.fill('#airbandPresetName', 'Outside airband')
    page.click('#airbandPresetSave')
    assert '118' in page.locator('#airbandPresetStatus').inner_text()
    page.fill('#airbandCustomFreq', '121.5')
    page.fill('#airbandPresetName', '   ')
    page.click('#airbandPresetSave')
    assert 'name' in page.locator('#airbandPresetStatus').inner_text().lower()
    assert page.evaluate("localStorage.getItem('airband.frequencyPresets')") is None


def test_preset_names_are_text_and_bad_storage_is_ignored(page):
    page.evaluate("localStorage.setItem('airband.frequencyPresets', '{invalid json')")
    page.reload(wait_until='domcontentloaded')
    page.click('#airbandChip')
    page.fill('#airbandPresetName', '<img src=x onerror=alert(1)>')
    page.click('#airbandPresetSave')
    assert '<img' in page.locator('#airbandFreqSelect option:checked').inner_text()
    assert page.locator('#airbandPanel img').count() == 0
    assert not page.errors, page.errors
