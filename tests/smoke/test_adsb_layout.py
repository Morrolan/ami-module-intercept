"""Selected aircraft details stay in document flow, including delayed content."""
from __future__ import annotations

import pytest
from .test_pages_load import INIT_SCRIPT

VIEWPORTS = [(1440,900),(1366,768),(390,844),(720,450)]

@pytest.mark.parametrize('width,height', VIEWPORTS)
@pytest.mark.parametrize('theme', ['dark','light'])
@pytest.mark.parametrize('embedded', [False,True])
def test_selected_aircraft_pushes_list_down(browser, base_url, width, height, theme, embedded):
    context=browser.new_context(viewport={'width':width,'height':height})
    context.add_init_script(INIT_SCRIPT % theme)
    context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base_url) else r.abort())
    page=context.new_page()
    try:
        page.goto(base_url+'/adsb/dashboard'+('?ami=1' if embedded else ''),wait_until='domcontentloaded')
        page.wait_for_function("typeof showAircraftDetails === 'function'")
        page.evaluate("""() => {
          aircraft['ABCDEF']={icao:'ABCDEF',callsign:'TEST123',lat:54.5,lon:-1.5,
            altitude:33000,speed:420,heading:90,squawk:'7000',vertical_rate:100,
            registration:'G-TEST',type_code:'A320',type_desc:'Synthetic aircraft with a long descriptive name'};
          showAircraftDetails('ABCDEF');
        }""")
        before=page.locator('.aircraft-list').bounding_box()['y']
        # Simulate late photo/extra flight detail arrival without contacting an external service.
        page.locator('#selectedInfo').evaluate("""el => {
          const extra=document.createElement('section');extra.id='lateFlightDetails';
          for(let i=0;i<20;i++){const row=document.createElement('p');row.textContent='Additional flight detail '+i;row.style.padding='8px';extra.append(row);}
          const button=document.createElement('button');button.textContent='Last aircraft action';button.id='lastAircraftAction';extra.append(button);el.append(extra);
        }""")
        geometry=page.evaluate("""() => {
          const detail=document.querySelector('.selected-aircraft'),list=document.querySelector('.aircraft-list');
          const hidden=[];for(let e=document.querySelector('#lastAircraftAction');e&&e!==document.documentElement;e=e.parentElement){
            const s=getComputedStyle(e);if(['hidden','auto','scroll','clip'].includes(s.overflowY)&&e.scrollHeight>e.clientHeight+2)hidden.push(e.id||e.className);
          }
          return {detailBottom:detail.getBoundingClientRect().bottom,listTop:list.getBoundingClientRect().top,hidden};
        }""")
        assert geometry['listTop']>before+100,geometry
        assert geometry['listTop']>=geometry['detailBottom']-1,geometry
        assert not geometry['hidden'],geometry
        page.locator('#lastAircraftAction').scroll_into_view_if_needed()
        assert page.locator('#lastAircraftAction').is_visible()
        page.locator('#lastAircraftAction').focus()
        assert page.locator('#lastAircraftAction').evaluate('el=>el===document.activeElement')
        page.locator('#lateFlightDetails').evaluate('el=>el.remove()')
        assert page.locator('.aircraft-list').bounding_box()['y']<geometry['listTop']-100
        # Removing/changing the selection also releases its height.
        page.evaluate("showAircraftDetails('not-present')")
        assert page.locator('#selectedInfo').inner_text().strip().endswith('Select an aircraft')
    finally:context.close()
