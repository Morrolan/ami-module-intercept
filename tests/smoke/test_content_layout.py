"""Information panels reflow with their contents rather than clipping data."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from .test_pages_load import DASHBOARDS, INIT_SCRIPT

# No external requests or RF operations: content is synthetic, rendering is real.
GEOMETRY = """el => {
 const s = getComputedStyle(el), r = el.getBoundingClientRect();
 return {height:r.height, scroll:el.scrollHeight, client:el.clientHeight,
 overflow:s.overflowY, max:s.maxHeight, display:s.display};
}"""


def route_layout_request(route, base_url):
    url = route.request.url
    if url.endswith("/system/stream"):
        metrics = {"cpu": {"percent": 12, "cores": 2, "per_core": [10, 14]}, "memory": {"percent": 25}}
        route.fulfill(content_type="text/event-stream", body="retry: 60000\ndata: " + json.dumps(metrics) + "\n\n")
    elif "/system/" in url and "/static/" not in url:
        route.fulfill(json={"source": "none", "devices": []})
    elif url.startswith(base_url):
        route.continue_()
    else:
        route.abort()


@pytest.fixture(
    params=[
        ("dark", 1440, 900, False),
        ("light", 1366, 768, True),
        ("dark", 390, 844, False),
        ("light", 720, 450, True),
    ]
)
def layout_page(request, browser, base_url):
    theme, width, height, embedded = request.param
    context = browser.new_context(viewport={"width": width, "height": height})
    context.add_init_script(INIT_SCRIPT % theme)
    if embedded:
        context.add_init_script("document.documentElement.classList.add('ami-embedded')")
    context.route("**/*", lambda route: route_layout_request(route, base_url))
    page = context.new_page()
    page.set_default_timeout(5000)
    yield page
    context.close()


def test_layout_inventory(layout_page, base_url):
    """Opt-in rendering audit, including every registered mode and dashboard."""
    if not os.environ.get("INTERCEPT_LAYOUT_AUDIT"):
        pytest.skip("Set INTERCEPT_LAYOUT_AUDIT=1 to collect diagnostic inventory")
    page = layout_page
    page.goto(base_url + "/", wait_until="domcontentloaded")
    page.wait_for_function("window.INTERCEPT_MODES && window.switchMode")
    modes = page.evaluate("Object.keys(INTERCEPT_MODES)")
    rows = []
    for mode in modes:
        page.evaluate("(mode)=>switchMode(mode)", mode)
        page.wait_for_timeout(150)
        rows.append(
            {
                "mode": mode,
                "panes": page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e=>{
 const s=getComputedStyle(e);return e.getBoundingClientRect().height>0 && e.children.length &&
 (s.overflowY==='auto'||s.overflowY==='scroll'||s.overflowY==='hidden') &&
 !e.closest('.leaflet-container,.maplibregl-map,svg') && !e.matches('script,style');
 }).map(e=>({selector:e.id?'#'+e.id:'.'+[...e.classList].join('.'),height:e.clientHeight,scroll:e.scrollHeight,overflow:getComputedStyle(e).overflowY})).filter(e=>e.selector!=='.')"""),
            }
        )
    for path in DASHBOARDS:
        page.goto(base_url + path, wait_until="domcontentloaded")
        page.wait_for_timeout(200)
        rows.append(
            {
                "page": path,
                "panes": page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e=>{
 const s=getComputedStyle(e);return e.getBoundingClientRect().height>0 && e.children.length &&
 ['auto','scroll','hidden'].includes(s.overflowY) && !e.closest('.leaflet-container,.maplibregl-map,svg');
 }).map(e=>({selector:e.id?'#'+e.id:'.'+[...e.classList].join('.'),height:e.clientHeight,scroll:e.scrollHeight,overflow:getComputedStyle(e).overflowY})).filter(e=>e.selector!=='.')"""),
            }
        )
    Path(os.environ["INTERCEPT_LAYOUT_AUDIT"]).write_text(json.dumps(rows, indent=2))


def assert_information_grows(page, selector):
    # Use the DOM directly for the large workspace root; Playwright's shadow-
    # piercing parent selector can time out on the populated System document.
    page.evaluate(
        """selector=>{
      const el=document.querySelector(selector);if(!el)throw Error('Missing information container: '+selector);
      const content=document.createElement('section');content.id='layoutFixture';
      for(let i=0;i<25;i++){const row=document.createElement('p');row.textContent='Synthetic detail row '+i;row.style.padding='8px';content.append(row);}
      const action=document.createElement('button');action.textContent='Final detail action';action.id='layoutFinalAction';content.append(action);el.append(content);
    }""",
        selector,
    )
    # Match the exact fixture node without Playwright walking every shadow root
    # in the populated System dashboard before starting the actionability check.
    action = page.evaluate_handle("document.getElementById('layoutFinalAction')").as_element()
    assert action is not None
    hidden = action.evaluate("""el=>{
      const hidden=[];for(let e=el.parentElement;e&&e!==document.body;e=e.parentElement){
        const s=getComputedStyle(e);if(['hidden','auto','scroll','clip'].includes(s.overflowY)&&e.scrollHeight>e.clientHeight+2)hidden.push(e.id||e.className||e.tagName);
      }return hidden;
    }""")
    assert not hidden, {"selector": selector, "constrained_ancestors": hidden}
    action.scroll_into_view_if_needed()
    action.click(trial=True)
    assert page.evaluate("!['hidden','clip'].includes(getComputedStyle(document.body).overflowY)")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.locator("#layoutFixture").evaluate("el=>el.remove()")


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize(
    "width,height,theme", [(1440, 900, "dark"), (1366, 768, "light"), (390, 844, "dark"), (720, 450, "light")]
)
def test_every_mode_information_flows(browser, base_url, embedded, width, height, theme):
    context = browser.new_context(viewport={"width": width, "height": height})
    context.add_init_script(INIT_SCRIPT % theme)
    context.route("**/*", lambda route: route_layout_request(route, base_url))
    page = context.new_page()
    page.set_default_timeout(5000)
    try:
        page.goto(base_url + "/?mode=pager" + ("&ami=1" if embedded else ""), wait_until="domcontentloaded")
        page.wait_for_function("window.INTERCEPT_MODES && window.switchMode")
        for mode in page.evaluate("Object.keys(INTERCEPT_MODES)"):
            page.evaluate("async mode=>{await switchMode(mode);await new Promise(requestAnimationFrame);}", mode)
            try:
                assert_information_grows(page, ".output-panel")
            except Exception as error:
                state = page.evaluate(
                    "()=>({url:location.href,body:document.body.dataset.mode,output:!!document.querySelector('.output-panel')})"
                )
                raise AssertionError(f"{mode}: {state}: {error}") from error
    finally:
        context.close()


DETAIL_CASES = [
    ("/ais/dashboard", "#selectedInfo"),
    ("/satellite/dashboard", ".telemetry-panel .panel-content"),
    ("/satellite/dashboard", "#passList"),
    ("/satellite/iss", ".iss-side"),
    ("/aprs/dashboard", "#aprsStationList"),
    ("/meshtastic/dashboard", ".mesh-tabpane.active"),
    ("/meshcore/dashboard", "#meshcoreSidePanel"),
    ("/adsb/history", ".panel-body"),
    ("/messages", "#detailBody"),
    ("/controller/monitor", ".panel-body"),
    ("/?mode=bluetooth", ".bt-detail-body"),
    ("/?mode=weathersat", ".wxsat-passes-panel"),
    ("/?mode=sstv", ".sstv-countdown-panel"),
    ("/?mode=wefax", ".wefax-schedule-panel"),
    ("/?mode=tscm", "#tscmWifiList"),
    ("/?mode=wifi", ".wifi-networks-table-wrapper"),
    ("/?mode=gps", "#gpsVisuals"),
    ("/?mode=radiosonde", "#radiosondeCardContainer"),
    ("/?mode=spaceweather", ".sw-alerts-panel"),
    ("/?mode=meteor", ".ms-events-scroll"),
    ("/?mode=drone", ".drone-contact-panel"),
    ("/?mode=spystations", "#spyStationsVisuals"),
    ("/?mode=ook", "#ookOutput"),
    ("/?mode=system", "#systemVisuals"),
    ("/?mode=activity", ".activity-list"),
    ("/?mode=tscmsurvey", "#tscmSurveyVisuals"),
    ("/?mode=morse", ".morse-decoded-panel"),
    ("/?mode=morse", ".morse-raw-text"),
    ("/?mode=morse", "#morseDiagLog"),
    ("/?mode=weathersat", ".wxsat-console-log"),
    ("/?mode=subghz", ".subghz-console-log"),
]


@pytest.mark.parametrize("path,selector", DETAIL_CASES)
def test_dashboard_and_mode_details_grow(layout_page, base_url, path, selector):
    page = layout_page
    page.goto(base_url + path, wait_until="domcontentloaded")
    page.wait_for_timeout(250)
    if path.startswith("/?"):
        mode = path.split("=")[1]
        page.evaluate("(mode)=>switchMode(mode)", mode)
        page.wait_for_timeout(150)
    if selector == ".wxsat-console-log":
        page.locator("#wxsatSignalConsole").evaluate("el=>el.classList.add('active')")
    if selector == ".subghz-console-log":
        page.locator("#subghzConsole").evaluate("el=>el.style.display=''")
    if selector in (".wxsat-console-log", ".subghz-console-log"):
        page.locator(selector).locator("..").evaluate("el=>el.classList.remove('collapsed')")
    if selector == "#morseDiagLog":
        page.locator(selector).evaluate("el=>el.style.display='block'")
    assert_information_grows(page, selector)
    if selector in (".wxsat-console-log", ".subghz-console-log"):
        body = page.locator(selector).locator("..")
        body.evaluate("el=>el.classList.add('collapsed')")
        page.wait_for_timeout(350)
        assert body.evaluate("el=>el.getBoundingClientRect().height") <= 1


def test_live_scroll_uses_page_without_stealing_offscreen_position(layout_page, base_url):
    page = layout_page
    page.goto(base_url + "/?mode=pager", wait_until="domcontentloaded")
    page.evaluate("""()=>{
      const feed=document.createElement('div');feed.id='layoutFeed';
      for(let i=0;i<80;i++){const row=document.createElement('p');row.textContent='Synthetic log '+i;row.style.padding='8px';feed.append(row);}
      document.body.append(feed);
      feed.scrollIntoView({block:'start'});
    }""")
    page.evaluate("InterceptLayout.scrollToEdge(document.querySelector('#layoutFeed'),'end')")
    assert page.locator("#layoutFeed").evaluate("el=>el.getBoundingClientRect().bottom<=innerHeight+1")
    page.evaluate("InterceptLayout.scrollToEdge(document.querySelector('#layoutFeed'),'start')")
    assert page.locator("#layoutFeed").evaluate("el=>el.getBoundingClientRect().top>=-1")
    page.evaluate("scrollTo(0,0)")
    page.evaluate("InterceptLayout.scrollToEdge(document.querySelector('#layoutFeed'),'end')")
    assert page.evaluate("scrollY") == 0
    page.locator("#layoutFeed").evaluate("el=>el.remove()")


def test_settings_long_tab_has_one_reachable_scroll_area(layout_page, base_url):
    page = layout_page
    page.goto(base_url + "/?mode=pager", wait_until="domcontentloaded")
    page.evaluate("showSettings()")
    page.locator("#settingsModal").wait_for(state="visible")
    panel = page.locator(".settings-section.active").first
    panel.evaluate("""el=>{
      const rows=document.createElement('div');
      for(let i=0;i<40;i++){const p=document.createElement('p');p.textContent='Synthetic setting '+i;p.style.padding='10px';rows.append(p);}
      const b=document.createElement('button');b.id='layoutSettingsAction';b.textContent='Last setting';rows.append(b);el.append(rows);
    }""")
    page.locator("#layoutSettingsAction").click(trial=True, timeout=4000)
    page.locator(".settings-close").click(timeout=4000)
    assert not page.locator("#settingsModal").is_visible()


@pytest.mark.parametrize(
    "path,selector",
    [("/aprs/dashboard", "#aprsMap"), ("/satellite/iss", "#issMap"), ("/meshtastic/dashboard", "#meshMap")],
)
def test_map_remains_usable_beside_growing_information(layout_page, base_url, path, selector):
    page = layout_page
    page.goto(base_url + path, wait_until="domcontentloaded")
    page.locator(selector).wait_for(state="attached")
    box = page.locator(selector).bounding_box()
    assert box and box["width"] >= 250 and box["height"] >= 250, {"map": selector, "box": box}


def test_short_local_scroller_does_not_move_page(layout_page, base_url):
    page = layout_page
    page.set_content('<!doctype html><html><body style="margin:0"><div style="height:1000px"></div></body></html>')
    page.add_script_tag(path=str(Path(__file__).resolve().parents[2] / "static/js/core/content-layout.js"))
    page.evaluate("""()=>{
      const panel=document.createElement('div');panel.id='shortScroller';
      panel.style.cssText='height:120px;overflow:auto';panel.textContent='One line';
      document.body.append(panel);
      const tail=document.createElement('div');tail.style.height='1000px';document.body.append(tail);
      panel.scrollIntoView({block:'start'});window.scrollBy(0,-100);
    }""")
    before = page.evaluate("scrollY")
    page.evaluate("InterceptLayout.scrollToEdge(document.querySelector('#shortScroller'),'end')")
    assert page.evaluate("scrollY") == before


def test_mobile_drawer_retains_background_lock(browser, base_url):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(INIT_SCRIPT % "dark")
    context.route("**/*", lambda route: route_layout_request(route, base_url))
    page = context.new_page()
    try:
        page.goto(base_url + "/?mode=pager", wait_until="domcontentloaded")
        page.wait_for_function("typeof toggleMobileDrawer==='function'")
        page.locator("#hamburgerBtn").click()
        assert page.evaluate("getComputedStyle(document.body).overflowY") == "hidden"
        assert page.evaluate("getComputedStyle(document.documentElement).overflowY") == "hidden"
        drawer = page.locator("#mainSidebar")
        assert drawer.evaluate("el=>getComputedStyle(el).overflowY") == "auto"
        page.evaluate("closeMobileDrawer()")
        assert page.evaluate("getComputedStyle(document.body).overflowY") == "auto"
    finally:
        context.close()
