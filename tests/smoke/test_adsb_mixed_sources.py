"""ADS-B dashboard: ACARS on one source while ADS-B runs on another (#264).

ADS-B, ACARS and VDL2 used to share the header's agent choice, which locks
while ADS-B tracks, so a local-SDR mode and an agent-hosted one couldn't run
from the same page. The agent and the decoders are mocked at the HTTP layer;
what's checked is which endpoint each start/stop goes to and that the panels
keep their state.

Skipped when Playwright is not installed, like the rest of tests/smoke.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("playwright.sync_api")

AGENT = {"id": 7, "name": "Pi Agent", "healthy": True, "base_url": "http://192.0.2.7:8020"}
LOCAL_SDRS = [
    {"index": 0, "sdr_type": "rtlsdr", "name": "Local RTL A"},
    {"index": 1, "sdr_type": "rtlsdr", "name": "Local RTL B"},
]
AGENT_SDRS = [{"index": 0, "sdr_type": "rtlsdr", "name": "Agent RTL"}]

RESPONSES = {
    ("GET", "/controller/agents"): {"agents": [AGENT]},
    ("GET", "/controller/agents/7"): {"agent": {**AGENT, "interfaces": {"sdr_devices": AGENT_SDRS}}},
    ("GET", "/controller/agents/7/status"): {"status": "success", "agent_status": {"running_modes": []}},
    ("POST", "/controller/agents/7/adsb/start"): {"status": "started"},
    ("POST", "/controller/agents/7/acars/start"): {"status": "success", "result": {"status": "started"}},
    ("POST", "/controller/agents/7/acars/stop"): {"status": "success", "result": {"status": "stopped"}},
    ("GET", "/devices"): LOCAL_SDRS,
    ("GET", "/devices/status"): [],
    ("POST", "/adsb/start"): {"status": "started"},
    ("POST", "/acars/start"): {"status": "started"},
    ("POST", "/acars/stop"): {"status": "stopped"},
    ("POST", "/vdl2/start"): {"status": "started"},
    ("POST", "/vdl2/stop"): {"status": "stopped"},
}


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    context.add_init_script(
        "try { localStorage.setItem('disclaimerAccepted', 'true');"
        " localStorage.setItem('intercept.setup.complete.v1', 'true');"
        " localStorage.setItem('acarsSidebarCollapsed', 'false'); } catch (e) {}"
    )
    page = context.new_page()
    page.calls = []
    page.errors = []

    def handle(route):
        request = route.request
        if not request.url.startswith(base_url):
            return route.abort()
        path = request.url[len(base_url) :].split("?")[0]
        body = RESPONSES.get((request.method, path))
        if body is None:
            return route.continue_()
        page.calls.append(f"{request.method} {path}")
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    context.route("**/*", handle)
    page.on("pageerror", lambda err: page.errors.append(str(err)))
    page.goto(base_url + "/adsb/dashboard", wait_until="domcontentloaded")
    page.wait_for_function("typeof agents !== 'undefined' && agents.length === 1")
    yield page
    context.close()


def _choose(page, select_id, value):
    page.focus(f"#{select_id}")  # the panel source list is filled on focus
    page.select_option(f"#{select_id}", value)


def test_acars_on_agent_while_adsb_tracks_locally(page):
    page.click("#startBtn")
    page.wait_for_function("isTracking === true")
    assert page.is_disabled("#agentSelect")  # header locked to Local while ADS-B tracks

    _choose(page, "acarsSourceSelect", "7")
    page.wait_for_function("document.getElementById('acarsDeviceSelect').textContent.includes('Agent RTL')")
    page.click("#acarsToggleBtn")
    page.wait_for_function("isAcarsRunning === true")

    assert "POST /controller/agents/7/acars/start" in page.calls
    assert "POST /acars/start" not in page.calls
    assert page.is_disabled("#acarsSourceSelect")
    assert page.evaluate("isTracking && adsbTrackingSource === 'local'")

    page.click("#acarsToggleBtn")
    page.wait_for_function("isAcarsRunning === false")
    assert "POST /controller/agents/7/acars/stop" in page.calls
    assert not page.errors, page.errors


def test_local_acars_survives_switching_header_to_agent(page):
    page.click("#acarsToggleBtn")
    page.wait_for_function("isAcarsRunning === true")
    assert "POST /acars/start" in page.calls

    # The agent isn't running ACARS; that must not mark the local ACARS stopped
    page.select_option("#agentSelect", "7")
    page.wait_for_function("adsbCurrentAgent === '7'")
    page.wait_for_timeout(500)
    assert "GET /controller/agents/7/status" in page.calls
    assert page.evaluate("isAcarsRunning && acarsCurrentAgent === null")
    assert "STOP ACARS" in page.inner_text("#acarsToggleBtn")

    page.click("#startBtn")
    page.wait_for_function("isTracking === true")
    assert "POST /controller/agents/7/adsb/start" in page.calls

    page.click("#acarsToggleBtn")
    page.wait_for_function("isAcarsRunning === false")
    assert "POST /acars/stop" in page.calls
    assert "POST /controller/agents/7/acars/stop" not in page.calls
    assert not page.errors, page.errors


@pytest.mark.parametrize("mode", ["acars", "vdl2"])
@pytest.mark.parametrize("remote", [True, False])
def test_datalink_only_conflicts_with_actual_local_adsb_device(page, mode, remote):
    page.evaluate("""() => {
      window.receiverConflicts=[];
      AppFeedback.confirmAction=async details=>{receiverConflicts.push(details);return false;};
    }""")
    if remote:
        page.check('#useRemoteDump1090')
        page.fill('#remoteSbsHost', '10.10.42.6')
    page.click('#startBtn')
    page.wait_for_function('isTracking === true')
    if mode == 'vdl2':
        page.click('#vdl2CollapseBtn')
    _choose(page, mode+'SourceSelect', 'local')
    page.select_option('#'+mode+'DeviceSelect', 'rtlsdr:0')
    page.click('#'+mode+'ToggleBtn')
    if remote:
        page.wait_for_function('mode=>mode==="acars"?isAcarsRunning:isVdl2Running', arg=mode, timeout=2000)
        assert 'POST /'+mode+'/start' in page.calls
        assert page.evaluate('receiverConflicts') == []
        assert page.evaluate('adsbActiveDevice') is None
    else:
        assert len(page.evaluate('receiverConflicts')) == 1
        assert 'POST /'+mode+'/start' not in page.calls
    assert page.evaluate('isTracking')
    assert not page.errors, page.errors


def test_remote_session_clears_stale_local_receiver_ownership(page):
    page.route('**/adsb/session', lambda route: route.fulfill(json={
        'tracking_active': True,
        'session': {'sdr_type': 'remote', 'device_index': 0, 'remote_host': '10.10.42.6', 'remote_port': 30003},
    }))
    page.evaluate('async () => { adsbActiveDevice=0; await syncTrackingStatus(); }')
    assert page.evaluate('isTracking')
    assert page.evaluate('adsbActiveDevice') is None
    assert not page.errors, page.errors


@pytest.mark.parametrize('actual_remote', [False, True])
def test_existing_session_ownership_overrides_requested_receiver(page, actual_remote):
    session = {'sdr_type': 'remote' if actual_remote else 'rtlsdr', 'device_index': 0,
               'remote_host': '10.10.42.6', 'remote_port': 30003}
    page.route('**/adsb/start', lambda route: route.fulfill(status=409, json={
        'status': 'already_running', 'session': session,
    }))
    page.evaluate("""() => {
      window.receiverConflicts=[];
      AppFeedback.confirmAction=async details=>{receiverConflicts.push(details);return false;};
    }""")
    if not actual_remote:
        page.check('#useRemoteDump1090')
        page.fill('#remoteSbsHost', '10.10.42.6')
    page.click('#startBtn')
    page.wait_for_function('isTracking === true')
    page.click('#vdl2CollapseBtn')
    _choose(page, 'vdl2SourceSelect', 'local')
    page.select_option('#vdl2DeviceSelect', 'rtlsdr:0')
    page.click('#vdl2ToggleBtn')
    if actual_remote:
        page.wait_for_function('isVdl2Running', timeout=2000)
        assert page.evaluate('adsbActiveDevice') is None
        assert page.evaluate('receiverConflicts') == []
        assert 'POST /vdl2/start' in page.calls
    else:
        assert page.evaluate('adsbActiveDevice') == 0
        assert len(page.evaluate('receiverConflicts')) == 1
        assert 'POST /vdl2/start' not in page.calls
    assert not page.errors, page.errors
