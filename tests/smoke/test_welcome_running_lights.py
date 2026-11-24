"""Main-menu tiles light while anything in their context runs, on any SDR or remote feed."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")


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


def _health(processes, sources=None, claims=None):
    return {
        "status": "healthy", "uptime_seconds": 60, "sdr_devices": 2,
        "processes": processes, "sources": sources or {}, "sdr_claims": claims or {},
        "lifecycle": {}, "data": {},
    }


def _tile(page, selector):
    return page.locator(f"#welcomePage {selector}")


def test_tiles_light_for_feeds_and_every_sdr(page, base_url):
    health = _health(
        {"adsb": True, "acars": True, "ais": False, "dsc": True, "pager": False},
        sources={"adsb": "remote"},
        claims={"rtlsdr:1": "acars", "rtlsdr:0": "dsc", "rtlsdr:2": "waterfall"},
    )
    page.route("**/health", lambda route: route.fulfill(json=health))
    page.goto(base_url + "/", wait_until="domcontentloaded")

    aircraft = _tile(page, "a.mode-card[href='/adsb/dashboard']")
    page.wait_for_function("document.querySelector(\"#welcomePage a.mode-card[href='/adsb/dashboard']\")"
                           ".classList.contains('is-running')")
    assert aircraft.locator(".wl-doing").inner_text() == "ADS-B remote feed · ACARS SDR 1"

    vessels = _tile(page, "a.mode-card[href='/ais/dashboard']")
    assert "is-running" in vessels.get_attribute("class")  # DSC alone lights Vessels
    assert vessels.locator(".wl-doing").inner_text() == "DSC SDR 0"

    waterfall = _tile(page, ".mode-card[onclick=\"selectMode('waterfall')\"]")
    assert "is-running" in waterfall.get_attribute("class")  # no process, but it holds an SDR
    assert waterfall.locator(".wl-doing").inner_text() == "SDR 2"

    pager = _tile(page, ".mode-card[onclick=\"selectMode('pager')\"]")
    assert "is-running" not in pager.get_attribute("class")
    assert pager.locator(".wl-doing").count() == 0
    assert not page.errors, page.errors


def test_tile_light_goes_out_when_the_feed_stops(page, base_url):
    state = {"health": _health({"adsb": True}, sources={"adsb": "external"})}
    page.route("**/health", lambda route: route.fulfill(json=state["health"]))
    page.goto(base_url + "/", wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector(\"#welcomePage a.mode-card[href='/adsb/dashboard'] .wl-doing\")"
                           "?.textContent === 'ADS-B local dump1090'")

    state["health"] = _health({"adsb": False})
    page.evaluate("RunState.refresh()")
    page.wait_for_function("!document.querySelector(\"#welcomePage a.mode-card[href='/adsb/dashboard']\")"
                           ".classList.contains('is-running')")
    assert _tile(page, "a.mode-card[href='/adsb/dashboard'] .wl-doing").count() == 0
    assert not page.errors, page.errors
