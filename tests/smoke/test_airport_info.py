"""Clicking a selected aircraft's origin or destination opens that airport's details."""

import os

import pytest

from .test_adsb_mixed_sources import page as mixed_source_page
from .test_aircraft_routes import route, select

page = mixed_source_page


def open_route(page, data):
    page.route("**/adsb/route/KLM965", lambda r: r.fulfill(json=data))
    select(page, "ABCDEF", "KLM965")
    page.wait_for_selector("#selectedOrigin .airport-link")


@pytest.mark.parametrize(
    "theme,width,height,embedded",
    [
        ("dark", 1600, 1000, False),
        ("light", 390, 844, True),
    ],
)
def test_origin_opens_bundled_airport_details(page, theme, width, height, embedded):
    if embedded:
        page.goto(page.url.split("?")[0] + "?ami=1", wait_until="domcontentloaded")
    page.set_viewport_size({"width": width, "height": height})
    page.evaluate("theme => document.documentElement.dataset.theme=theme", theme)
    data = route()
    data["origin"]["name"] = "Amsterdam Airport Schiphol"
    data["destination"]["name"] = "Teesside International Airport"
    open_route(page, data)
    dialog = page.locator("#airportInfoDialog")
    assert not dialog.is_visible()
    page.locator("#selectedDestination").get_by_role("button").click()
    page.wait_for_function("document.querySelector('#airportInfoFacts').textContent.includes('Medium airport')")
    text = dialog.inner_text()
    assert page.locator("#airportInfoTitle").text_content() == "Teesside International Airport"
    assert "Destination of KLM965" in text and "ICAO EGNV" in text
    assert "United Kingdom (GB)" in text and "England" in text and "From your location" in text
    assert "05/23" in dialog.locator("#airportInfoRunways").inner_text()
    assert "TWR" in dialog.locator("#airportInfoFreqs").inner_text()
    assert (
        dialog.get_by_role("link", name="OurAirports page").get_attribute("href")
        == "https://ourairports.com/airports/EGNV/"
    )
    assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    if os.environ.get("INTERCEPT_TEESSIDE_SCREENSHOTS"):
        dialog.screenshot(path=f"/private/tmp/airport-info-{theme}-{width}.png")
    page.keyboard.press("Escape")
    assert not dialog.is_visible()
    page.locator("#selectedOrigin").get_by_role("button").click()
    page.wait_for_function("document.querySelector('#airportInfoFacts').textContent.includes('Large airport')")
    assert page.locator("#airportInfoTitle").text_content() == "Amsterdam Airport Schiphol"
    dialog.get_by_role("button", name="Close airport details").click()
    assert not dialog.is_visible()
    assert not page.errors, page.errors


def test_unbundled_airport_falls_back_and_names_stay_text(page):
    data = route()
    data["origin"].update(
        icao="ZZZZ",
        iata="",
        name="<img src=x onerror=alert(1)>",
        country="Nowhere",
        country_code="NW",
        municipality="<b>Town</b>",
        elevation_ft=100,
        lat=1.5,
        lon=2.5,
    )
    page.route("**/adsb/airport/ZZZZ", lambda r: r.fulfill(status=404, json={"error": "not found"}))
    open_route(page, data)
    page.locator("#selectedOrigin").get_by_role("button").click()
    dialog = page.locator("#airportInfoDialog")
    page.wait_for_function("document.querySelector('#airportInfoStatus').textContent.includes('bundled')")
    text = dialog.inner_text()
    assert page.locator("#airportInfoTitle").text_content() == "<img src=x onerror=alert(1)>"
    assert "<b>Town</b>" in text and "Nowhere (NW)" in text
    assert "100 ft (30 m)" in text and "Size" not in text
    assert dialog.locator("img, b").count() == 0
    assert not dialog.locator("#airportInfoRunwaysSection").is_visible()
    assert not dialog.locator("#airportInfoFreqSection").is_visible()
    assert not page.errors, page.errors


def test_slow_airport_lookup_cannot_overwrite_newer_airport(page):
    pending = []
    page.route("**/adsb/airport/EHAM", lambda r: pending.append(r))
    open_route(page, route())
    page.locator("#selectedOrigin").get_by_role("button").click()
    page.wait_for_timeout(150)
    assert pending
    page.keyboard.press("Escape")
    page.locator("#selectedDestination").get_by_role("button").click()
    page.wait_for_function("document.querySelector('#airportInfoFacts').textContent.includes('Medium airport')")
    pending[0].fulfill(json={"available": True, "icao": "EHAM", "name": "Wrong airport", "type": "large"})
    page.wait_for_timeout(150)
    assert page.locator("#airportInfoTitle").text_content() == "Teesside International Airport"


def test_listen_is_manual_and_tunes_the_airport_frequency(page):
    page.evaluate(
        "() => { window.airportTunes=[];window.startAirband=async()=>airportTunes.push(getAirbandFrequency()); }"
    )
    open_route(page, route())
    page.locator("#selectedDestination").get_by_role("button").click()
    dialog = page.locator("#airportInfoDialog")
    listen = dialog.get_by_role("button", name="Listen to TWR · 119.800 MHz")
    listen.wait_for()
    assert page.evaluate("airportTunes") == []
    listen.click()
    page.wait_for_function("airportTunes.length === 1")
    assert page.evaluate("airportTunes") == [119.8]
    assert not dialog.is_visible()
