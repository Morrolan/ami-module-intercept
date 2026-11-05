"""Selected aircraft details stay in document flow, including delayed content."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from .test_pages_load import INIT_SCRIPT

VIEWPORTS = [(3008, 1692), (1440, 900), (1366, 768), (390, 844), (720, 450)]


@pytest.mark.parametrize("width,height", VIEWPORTS)
@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("embedded", [False, True])
def test_selected_aircraft_pushes_list_down(browser, base_url, width, height, theme, embedded):
    context = browser.new_context(viewport={"width": width, "height": height})
    context.add_init_script(INIT_SCRIPT % theme)
    context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base_url) else r.abort())
    context.route("**/adsb/aircraft-photo/**", lambda r: r.fulfill(json={"photos": []}))
    page = context.new_page()
    try:
        page.goto(base_url + "/adsb/dashboard" + ("?ami=1" if embedded else ""), wait_until="domcontentloaded")
        page.wait_for_function("typeof showAircraftDetails === 'function'")
        page.evaluate("""() => {
          aircraft['ABCDEF']={icao:'ABCDEF',callsign:'TEST123',lat:54.5,lon:-1.5,
            altitude:33000,speed:420,heading:90,squawk:'7000',vertical_rate:100,
            registration:'G-TEST',type_code:'A320',type_desc:'Synthetic aircraft with a long descriptive name'};
          showAircraftDetails('ABCDEF');
        }""")
        before = page.locator(".aircraft-list").bounding_box()["y"]
        # Simulate late photo/extra flight detail arrival without contacting an external service.
        page.locator("#selectedInfo").evaluate("""el => {
          const photo = document.querySelector('#aircraftPhoto');
          photo.src = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300"><rect width="800" height="300" fill="#234"/></svg>');
          document.querySelector('#aircraftPhotoContainer').style.display = 'block';
          const extra=document.createElement('section');extra.id='lateFlightDetails';
          for(let i=0;i<20;i++){const row=document.createElement('p');row.textContent='Additional flight detail '+i;row.style.padding='8px';extra.append(row);}
          const button=document.createElement('button');button.textContent='Last aircraft action';button.id='lastAircraftAction';extra.append(button);el.append(extra);
        }""")
        shots = os.environ.get("INTERCEPT_LAYOUT_SCREENSHOTS")
        if shots and not embedded and theme == "dark" and width in (1440, 390):
            folder = Path(shots)
            folder.mkdir(parents=True, exist_ok=True)
            sheet = page.locator('link[href*="content-layout.css"]')
            sheet.evaluate("el=>el.disabled=true")
            page.screenshot(path=str(folder / f"adsb-{width}-before.png"), full_page=True)
            sheet.evaluate("el=>el.disabled=false")
            page.screenshot(path=str(folder / f"adsb-{width}-after.png"), full_page=True)
        geometry = page.evaluate("""() => {
          const detail=document.querySelector('.selected-aircraft'),list=document.querySelector('.aircraft-list');
          const hidden=[];for(let e=document.querySelector('#lastAircraftAction');e&&e!==document.documentElement;e=e.parentElement){
            const s=getComputedStyle(e);if(['hidden','auto','scroll','clip'].includes(s.overflowY)&&e.scrollHeight>e.clientHeight+2)hidden.push(`${e.tagName}#${e.id}.${e.className}:${s.overflowY}`);
          }
          return {detailBottom:detail.getBoundingClientRect().bottom,listTop:list.getBoundingClientRect().top,hidden};
        }""")
        assert geometry["listTop"] > before + 100, geometry
        assert geometry["listTop"] >= geometry["detailBottom"] - 1, geometry
        assert not geometry["hidden"], geometry
        page.locator("#lastAircraftAction").scroll_into_view_if_needed()
        assert page.locator("#lastAircraftAction").is_visible()
        page.locator("#lastAircraftAction").focus()
        assert page.locator("#lastAircraftAction").evaluate("el=>el===document.activeElement")
        page.locator("#lateFlightDetails").evaluate("el=>el.remove()")
        assert page.locator(".aircraft-list").bounding_box()["y"] < geometry["listTop"] - 100
        # Removing/changing the selection also releases its height.
        page.evaluate("showAircraftDetails('not-present')")
        assert page.locator("#selectedInfo").inner_text().strip().endswith("Select an aircraft")
    finally:
        context.close()


@pytest.mark.parametrize("embedded", [False, True])
def test_aircraft_uses_full_desktop_height(browser, base_url, embedded, monkeypatch):
    """A tall desktop must not leave an empty half-screen below the map."""
    context = browser.new_context(viewport={"width": 3008, "height": 1692})
    context.add_init_script(INIT_SCRIPT % "dark")
    context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base_url) else r.abort())
    monkeypatch.setenv("AMI_URL", base_url)
    page = context.new_page()
    try:
        if embedded:
            context.route(base_url + "/layout-parent", lambda r: r.fulfill(content_type="text/html", body=
                '<style>html,body{height:100%;margin:0}body{display:flex;flex-direction:column}'
                'header{height:96px;flex:none;background:#071a18;color:#75ead5}iframe{flex:1;border:0;width:100%;min-height:0}</style>'
                '<header>AMI — embedded aircraft layout check</header><iframe src="/adsb/dashboard?ami=1"></iframe>'))
            page.goto(base_url + "/layout-parent", wait_until="domcontentloaded")
            view = page.frames[1]
            view.wait_for_load_state("domcontentloaded")
            view.wait_for_function("typeof showAircraftDetails === 'function'")
            assert view.evaluate("document.documentElement.classList.contains('ami-embedded')")
        else:
            page.goto(base_url + "/adsb/dashboard", wait_until="domcontentloaded")
            page.wait_for_function("typeof showAircraftDetails === 'function'")
            view = page
        for width, height in [(3008, 1692), (1920, 1080), (1366, 768)]:
            page.set_viewport_size({"width": width, "height": height})
            view.wait_for_function("""() => {
              const map=document.querySelector('.main-display').getBoundingClientRect();
              const controls=document.querySelector('.controls-bar').getBoundingClientRect();
              return Math.abs(controls.bottom-Math.max(innerHeight,map.top+320+controls.height))<=2;
            }""")
            geometry = view.evaluate("""() => {
              const map=document.querySelector('.main-display').getBoundingClientRect();
              const controls=document.querySelector('.controls-bar').getBoundingClientRect();
              return {mapTop:map.top,mapBottom:map.bottom,controlsBottom:controls.bottom,
                controlsHeight:controls.height,viewport:innerHeight};
            }""")
            assert geometry['mapBottom'] >= geometry['viewport'] - geometry['controlsHeight'] - 2, geometry
            assert geometry['controlsBottom'] >= geometry['viewport'] - 2, geometry
            if height >= 1080:
                assert abs(geometry['controlsBottom'] - geometry['viewport']) <= 2, geometry
            shots = os.environ.get("INTERCEPT_LAYOUT_SCREENSHOTS")
            if shots and width == 3008:
                folder = Path(shots)
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"adsb-full-height-{'embedded' if embedded else 'standalone'}.png"))
    finally:
        context.close()


def test_aircraft_map_tracks_content_resizing(browser, base_url):
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    context.add_init_script(INIT_SCRIPT % "dark")
    context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base_url) else r.abort())
    page = context.new_page()
    try:
        page.goto(base_url + "/adsb/dashboard", wait_until="domcontentloaded")
        page.wait_for_function("window.radarMap && typeof window.radarMap.getSize === 'function'")
        # Outlive the dashboard's existing 200/500ms one-shot init corrections;
        # they must not mask the missing handling of subsequent content changes.
        page.wait_for_timeout(650)
        before = page.locator('#radarMap').evaluate('el=>el.clientHeight')
        page.locator('#selectedInfo').evaluate("""el=>{
          const detail=document.createElement('div');detail.id='largeAircraftDetail';
          detail.style.height='2000px';detail.textContent='Additional aircraft details';el.append(detail);
        }""")
        assert page.locator('#radarMap').evaluate('el=>el.clientHeight') <= before + 1
        assert page.locator('.sidebar').evaluate('el=>el.getBoundingClientRect().height') > 2000
        matches = "radarMap.getSize().y === document.getElementById('radarMap').clientHeight && radarMap.getSize().x === document.getElementById('radarMap').clientWidth"
        page.wait_for_function(matches, timeout=2000)
        page.locator('#largeAircraftDetail').evaluate('el=>el.remove()')
        page.wait_for_function("old=>document.getElementById('radarMap').clientHeight<=old", arg=before)
        page.wait_for_function(matches, timeout=2000)
    finally:
        context.close()


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_many_aircraft_do_not_push_map_controls_away(browser, base_url, embedded, theme, monkeypatch):
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    context.add_init_script(INIT_SCRIPT % theme)
    context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base_url) else r.abort())
    context.route("**/adsb/aircraft-photo/**", lambda r: r.fulfill(json={"photos": []}))
    monkeypatch.setenv("AMI_URL", base_url)
    page = context.new_page()
    try:
        if embedded:
            context.route(base_url + "/layout-parent", lambda r: r.fulfill(content_type="text/html", body=
                '<style>html,body{height:100%;margin:0}body{display:flex;flex-direction:column}'
                'header{height:96px;flex:none}iframe{flex:1;border:0;width:100%;min-height:0}</style>'
                '<header>AMI layout check</header><iframe src="/adsb/dashboard?ami=1"></iframe>'))
            page.goto(base_url + "/layout-parent", wait_until="domcontentloaded")
            view = page.frames[1]
        else:
            page.goto(base_url + "/adsb/dashboard", wait_until="domcontentloaded")
            view = page
        view.wait_for_function("typeof renderAircraftList === 'function'")
        view.evaluate("""() => {
          for(let i=0;i<50;i++) {
            const icao=(0xA00000+i).toString(16).toUpperCase();
            aircraft[icao]={icao,callsign:'TEST'+i,altitude:30000-i,lastSeen:Date.now()};
          }
          renderAircraftList();showAircraftDetails('A00000');
          const detail=document.createElement('p');detail.style.height='2000px';
          detail.textContent='Delayed selected aircraft details';document.querySelector('#selectedInfo').append(detail);
        }""")
        for width, height in [(3008,1692), (1600,1000), (1366,768), (390,844)]:
            page.set_viewport_size({"width":width,"height":height})
            if width >= 1024:
                view.wait_for_function("""() => {
                  const map=document.querySelector('.main-display').getBoundingClientRect();
                  const controls=document.querySelector('.controls-bar').getBoundingClientRect();
                  return Math.abs(controls.bottom-Math.max(innerHeight,map.top+320+controls.height))<=2;
                }""")
            geometry=view.evaluate("""() => {
              const rect=s=>document.querySelector(s).getBoundingClientRect().toJSON();
              return {map:rect('.main-display'),controls:rect('.controls-bar'),
                sidebar:rect('.sidebar'),list:rect('.aircraft-list'),viewport:innerHeight};
            }""")
            assert abs(geometry['controls']['top']-geometry['map']['bottom']) <= 2, geometry
            if width >= 1024:
                assert geometry['controls']['bottom'] <= geometry['viewport']+2, geometry
                assert geometry['controls']['right'] <= geometry['sidebar']['left']+2, geometry
                assert geometry['list']['bottom'] > geometry['viewport']+1000, geometry
            else:
                assert geometry['sidebar']['top'] >= geometry['controls']['bottom']-2, geometry
            shots = os.environ.get("INTERCEPT_LAYOUT_SCREENSHOTS")
            if shots and theme == "dark" and width in (1600,390):
                folder = Path(shots)
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"map-controls-{width}-{'embedded' if embedded else 'standalone'}.png"))
            last=view.locator('#aircraftList .aircraft-item').last
            last.scroll_into_view_if_needed()
            last.click()
            assert view.locator('#selectedInfo').inner_text().find('TEST49') >= 0
            view.evaluate("window.scrollTo(0,0);showAircraftDetails('A00000')")
    finally:
        context.close()
