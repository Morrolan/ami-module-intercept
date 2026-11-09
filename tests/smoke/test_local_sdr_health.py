"""The local RTL-SDR's state shows in Settings and beside it in device menus."""

from __future__ import annotations

import json
import time

import pytest

pytest.importorskip("playwright.sync_api")


@pytest.fixture
def unplugged(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"version": 1, "available": False, "node": None,
                                "generation": "g1", "updatedAt": time.time()}))
    monkeypatch.setenv("INTERCEPT_SDR_HOTPLUG_STATE", str(path))
    return path


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    context.add_init_script("try { localStorage.setItem('disclaimerAccepted','true');"
                            " localStorage.setItem('intercept.setup.complete.v1','true'); } catch (e) {}")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda err: page.errors.append(str(err)))
    yield page
    context.close()


def test_adsb_menu_shows_local_receiver_state(page, base_url, unplugged):
    devices = [{"index": 0, "sdr_type": "rtlsdr", "name": "Roof RTL", "health": "missing"}]
    page.route("**/devices", lambda route: route.fulfill(json=devices))
    page.goto(base_url + "/adsb/dashboard", wait_until="domcontentloaded")
    page.wait_for_function("[...document.querySelector('#adsbDeviceSelect').options]"
                           ".some(o => o.textContent === 'SDR 0: Roof RTL — Unplugged')")
    assert not page.errors, page.errors


def test_settings_shows_local_receiver_state(page, base_url, unplugged):
    page.goto(base_url + "/?mode=pager", wait_until="domcontentloaded")
    page.evaluate("showSettings(); switchSettingsTab('sdr')")
    page.wait_for_function("document.getElementById('localSdrHealthState').textContent === 'Unplugged'")
    assert "Decoders using it wait" in page.locator("#localSdrHealthDetail").inner_text()
    assert page.locator("#localSdrHealthPanel").is_visible()
    assert not page.errors, page.errors
