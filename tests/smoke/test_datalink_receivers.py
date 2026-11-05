"""Datalink receivers name their hardware and host without a second source list."""
import os
from pathlib import Path

import pytest

from .test_adsb_mixed_sources import page as mixed_source_page

page = mixed_source_page


def test_receiver_picker_and_europe_default(page):
    assert page.locator('#acarsSourceSelect, #vdl2SourceSelect').count() == 0
    page.wait_for_function("document.querySelector('#vdl2DeviceSelect').textContent.includes('Agent RTL')")
    for panel in ('acars', 'vdl2'):
        labels = page.locator('#'+panel+'DeviceSelect').inner_text()
        assert 'This server' in labels
        assert 'Local RTL A' in labels
        assert 'Local RTL B' in labels
        assert 'Pi Agent' in labels
        assert 'Agent RTL' in labels
    assert page.input_value('#vdl2DeviceSelect') == 'local|rtlsdr:0'
    assert page.input_value('#vdl2RegionDashSelect') == 'eu'
    assert '136.675' in page.locator('#vdl2FreqSelector').inner_text()
    assert '136.100' not in page.locator('#vdl2FreqSelector').inner_text()
    if os.environ.get('INTERCEPT_DATALINK_SCREENSHOTS'):
        folder = Path(os.environ['INTERCEPT_DATALINK_SCREENSHOTS'])
        folder.mkdir(parents=True, exist_ok=True)
        page.click('#vdl2CollapseBtn')
        page.wait_for_function("document.querySelector('#vdl2Sidebar').getBoundingClientRect().width>250 && document.querySelector('#acarsSidebar').getBoundingClientRect().width<60")
        page.screenshot(path=str(folder / 'vdl2-receiver.png'), full_page=True)
        page.click('#acarsCollapseBtn')
        page.wait_for_function("document.querySelector('#acarsSidebar').getBoundingClientRect().width>250 && document.querySelector('#vdl2Sidebar').getBoundingClientRect().width<60")
        page.screenshot(path=str(folder / 'acars-receiver.png'), full_page=True)



@pytest.mark.parametrize('panel', ['acars', 'vdl2'])
@pytest.mark.parametrize('source', ['local', '7'])
def test_receiver_choice_routes_decoder_and_stays_locked(page, panel, source):
    device = '1' if source == 'local' else '0'
    value = source+'|rtlsdr:'+device
    page.wait_for_function("document.querySelector('#vdl2DeviceSelect').textContent.includes('Agent RTL')")
    if panel == 'vdl2':
        page.click('#vdl2CollapseBtn')
    page.select_option('#'+panel+'DeviceSelect', value)
    page.click('#'+panel+'ToggleBtn')
    page.wait_for_function('panel=>panel==="acars"?isAcarsRunning:isVdl2Running', arg=panel)
    endpoint = '/'+panel+'/start' if source == 'local' else '/controller/agents/7/'+panel+'/start'
    assert 'POST '+endpoint in page.calls
    assert next(body for path, body in page.posts if path == endpoint)['device'] == device
    assert page.is_disabled('#'+panel+'DeviceSelect')
    page.evaluate('DatalinkReceivers.refresh()')
    assert page.input_value('#'+panel+'DeviceSelect') == value
    page.click('#'+panel+'ToggleBtn')
    page.wait_for_function('panel=>panel==="acars"?!isAcarsRunning:!isVdl2Running', arg=panel)
    assert not page.is_disabled('#'+panel+'DeviceSelect')
    assert not page.errors, page.errors


def test_adsb_agent_changes_do_not_change_datalink_receiver(page):
    page.wait_for_function("document.querySelector('#vdl2DeviceSelect').textContent.includes('Agent RTL')")
    page.click('#vdl2CollapseBtn')
    page.select_option('#vdl2DeviceSelect', 'local|rtlsdr:1')
    page.select_option('#agentSelect', '7')
    page.wait_for_function("adsbCurrentAgent === '7'")
    page.evaluate('DatalinkReceivers.refresh()')
    assert page.input_value('#vdl2DeviceSelect') == 'local|rtlsdr:1'
    page.click('#vdl2ToggleBtn')
    page.wait_for_function('isVdl2Running')
    assert 'POST /vdl2/start' in page.calls
    assert 'POST /controller/agents/7/vdl2/start' not in page.calls


def test_disappearing_agent_does_not_fall_back_to_local_receiver(page):
    page.wait_for_function("document.querySelector('#vdl2DeviceSelect').textContent.includes('Agent RTL')")
    page.click('#vdl2CollapseBtn')
    page.select_option('#vdl2DeviceSelect', '7|rtlsdr:0')
    page.route('**/controller/agents/7?refresh=true', lambda r: r.fulfill(status=503, json={'error': 'offline'}))
    page.evaluate('DatalinkReceivers.refresh()')
    assert page.input_value('#vdl2DeviceSelect') == '7|rtlsdr:0'
    page.click('#vdl2ToggleBtn')
    assert 'POST /vdl2/start' not in page.calls
    assert 'POST /controller/agents/7/vdl2/start' not in page.calls
    assert not page.evaluate('isVdl2Running')


def test_reopened_vdl2_selects_actual_running_receiver(page):
    page.route('**/vdl2/status', lambda route: route.fulfill(json={
        'running': True, 'active_device': 1, 'sdr_type': 'rtlsdr', 'message_count': 0,
    }))
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function("document.querySelector('#vdl2DeviceSelect').value==='local|rtlsdr:1'")
    assert page.is_disabled('#vdl2DeviceSelect')
    assert 'STOP VDL2' in page.locator('#vdl2ToggleBtn').inner_text()
    page.evaluate('DatalinkReceivers.refresh()')
    assert page.input_value('#vdl2DeviceSelect') == 'local|rtlsdr:1'
    assert not page.errors, page.errors
