"""A real cross-origin frame: login, navigation and the AMI bridge, without radios."""
from __future__ import annotations

import threading

import pytest
from flask import Flask, request
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

pytest.importorskip("playwright.sync_api")


@pytest.fixture
def embedded_servers(app, monkeypatch):
    from utils.database import get_db
    from utils.sdr import SDRFactory

    monkeypatch.delenv("INTERCEPT_DISABLE_AUTH", raising=False)
    monkeypatch.setattr(SDRFactory, "detect_devices", lambda *a, **kw: [])
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO users (username,password_hash,role,must_change_password) VALUES (?,?,?,0)",
                   ("ami-smoke", generate_password_hash("fixture-password"), "admin"))
    child = make_server("127.0.0.1", 0, app, threaded=True)
    child_url = f"http://127.0.0.1:{child.server_port}"
    parent_app = Flask("ami-frame-fixture")

    @parent_app.get("/")
    def parent_page():
        # Like AMI, optionally answer each ami-ready with the user's theme.
        theme = request.args.get("theme") if request.args.get("theme") in ("light", "dark") else ""
        return f"""<!doctype html><html><head><style>body{{margin:0;background:#020408}}iframe{{width:100vw;height:100vh;border:0}}</style></head><body><iframe title="Intercept" src="{child_url}/?ami=1"></iframe>
        <script>window.bridgeMessages=[];window.addEventListener('message',e=>{{
          if(e.origin!=='{child_url}')return;
          window.bridgeMessages.push(e.data);
          if(e.data.type==='ami-speak')e.source.postMessage({{type:'ami-speech',id:e.data.id,state:'idle'}},e.origin);
          if(e.data.type==='ami-ready'&&'{theme}')e.source.postMessage({{type:'ami-theme',theme:'{theme}'}},e.origin);
        }});</script>
        </body></html>"""

    parent = make_server("127.0.0.1", 0, parent_app, threaded=True)
    parent_url = f"http://127.0.0.1:{parent.server_port}"
    monkeypatch.setenv("AMI_URL", parent_url)
    for server in (child, parent):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    yield parent_url, child_url
    for server in (child, parent):
        server.shutdown()
        server.server_close()
    with get_db() as db:
        db.execute("DELETE FROM users WHERE username='ami-smoke'")


def test_embedded_login_navigation_and_origin_checks(browser, embedded_servers):
    parent_url, child_url = embedded_servers
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    context.add_init_script("localStorage.setItem('disclaimerAccepted','true');localStorage.setItem('intercept.setup.complete.v1','true');")
    context.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://127.0.0.1:") else route.abort())
    page = context.new_page()
    page.goto(parent_url, wait_until="domcontentloaded")
    frame = page.frame_locator("iframe")
    frame.locator('html.ami-embedded').wait_for()
    assert frame.locator('input[name=password]').evaluate('(node) => getComputedStyle(node).borderRadius') == '0px'
    frame.locator('input[name=username]').fill('ami-smoke')
    frame.locator('input[name=password]').fill('fixture-password')
    frame.locator('button[type=submit]').click()
    frame.locator('#mainSidebar').wait_for()
    child = next(f for f in page.frames if f.url.startswith(child_url))
    assert 'ami=1' in child.url
    child.locator('html.ami-embedded').wait_for()
    assert child.locator('header .logo').is_hidden()
    assert child.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim()") == '#64f0c8'
    page.wait_for_function("window.bridgeMessages.some(m=>m.type==='ami-ready')")
    # Automatic speech follows AMI, and spoofed settings cannot enable it.
    child.evaluate("""() => {
      window.nativeSpeechCount=0;
      window.speechSynthesis.speak=()=>window.nativeSpeechCount++;
      window.dispatchEvent(new MessageEvent('message',{
        origin:document.querySelector('meta[name=ami-origin]').content,source:window,
        data:{type:'ami-settings',autoplay:true}}));
      VoiceAlerts.speak('Must stay silent');
    }""")
    page.wait_for_timeout(100)
    assert page.evaluate("window.bridgeMessages.filter(m=>m.type==='ami-speak').length") == 0
    assert child.evaluate('window.InterceptAMI.autoplay') is False
    page.evaluate("(origin)=>document.querySelector('iframe').contentWindow.postMessage({type:'ami-settings',autoplay:true},origin)", child_url)
    child.wait_for_function('window.InterceptAMI.autoplay === true')
    child.evaluate("VoiceAlerts.speak('First AMI alert'); VoiceAlerts.speak('Second AMI alert');")
    page.wait_for_function("window.bridgeMessages.filter(m=>m.type==='ami-speak').length === 2")
    assert page.evaluate("window.bridgeMessages.filter(m=>m.type==='ami-speak').map(m=>m.text)") == ['First AMI alert', 'Second AMI alert']
    page.evaluate("(origin)=>document.querySelector('iframe').contentWindow.postMessage({type:'ami-settings',autoplay:false},origin)", child_url)
    child.wait_for_function('window.InterceptAMI.autoplay === false')
    child.evaluate("VoiceAlerts.testVoice('Manual AMI preview')")
    page.wait_for_function("window.bridgeMessages.some(m=>m.type==='ami-speak' && m.text==='Manual AMI preview')")
    assert child.evaluate('window.nativeSpeechCount') == 0
    assert child.locator('[data-ami-voice-settings]').evaluate_all("nodes=>nodes.length===3 && nodes.every(n=>getComputedStyle(n).display==='none')")
    child.evaluate("""() => {
      const a=document.createElement('a');a.id='ami-nav-test';a.href='/ais/dashboard';a.textContent='Vessels';document.body.append(a);
      a.click();
    }""")
    child.wait_for_url('**/ais/dashboard?ami=1')
    frame.locator('html.ami-embedded').wait_for()
    child = next(f for f in page.frames if '/ais/dashboard' in f.url)
    child.locator('.panel-header').first.wait_for()
    assert 'ami=1' in child.url
    # A forged event (even with the trusted origin) from a different window cannot focus the frame.
    child.evaluate("""() => {
      window.focusCalls=0;
      const node=document.querySelector('main, .main-content, .dashboard-container');
      if(node) node.focus=()=>window.focusCalls++;
      window.dispatchEvent(new MessageEvent('message',{origin:document.querySelector('meta[name=ami-origin]').content,
        source:window,data:{type:'ami-focus'}}));
    }""")
    assert child.evaluate('window.focusCalls') == 0
    # Existing programmatic navigation does not carry a query; restore embed mode per frame/tab.
    child.evaluate("window.location.href = '/?mode=pager'")
    child.wait_for_url('**/?mode=pager*')
    frame.locator('html.ami-embedded').wait_for()
    assert 'ami=1' in child.url
    frame.locator('#mainSidebar').wait_for()
    page.screenshot(path='/tmp/intercept-ami-embedded.png', full_page=True)
    standalone = context.new_page()
    standalone.goto(child_url, wait_until="domcontentloaded")
    assert standalone.locator('html.ami-embedded').count() == 0
    assert standalone.evaluate('window.InterceptAMI === undefined')
    standalone.wait_for_function('window.VoiceAlerts')
    standalone.evaluate("window.nativeSpeechCount=0; speechSynthesis.speak=()=>window.nativeSpeechCount++; VoiceAlerts.testVoice('Standalone preview');")
    assert standalone.evaluate('window.nativeSpeechCount') == 1
    standalone.close()
    context.close()


def test_embedded_theme_follows_ami_and_standalone_toggle_is_local(browser, embedded_servers):
    parent_url, child_url = embedded_servers
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    context.add_init_script("if(!localStorage.getItem('intercept-theme'))localStorage.setItem('intercept-theme','dark');"
                            "localStorage.setItem('disclaimerAccepted','true');localStorage.setItem('intercept.setup.complete.v1','true');")
    context.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://127.0.0.1:") else route.abort())
    page = context.new_page()
    page.goto(parent_url + "/?theme=light", wait_until="domcontentloaded")
    frame = page.frame_locator("iframe")
    frame.locator("html.ami-embedded[data-theme=light]").wait_for()
    frame.locator("input[name=username]").fill("ami-smoke")
    frame.locator("input[name=password]").fill("fixture-password")
    frame.locator("button[type=submit]").click()
    frame.locator("#mainSidebar").wait_for()
    child = next(f for f in page.frames if f.url.startswith(child_url))
    # AMI answers ami-ready on every page; the page's own start-up (loadTheme) must not undo it.
    child.wait_for_load_state("load")
    page.wait_for_timeout(300)
    assert child.evaluate("document.documentElement.dataset.theme") == "light"
    assert child.evaluate("getComputedStyle(document.documentElement).colorScheme") == "light"
    assert child.evaluate("localStorage.getItem('intercept-theme')") == "dark"
    assert not any(m.get("type") == "ami-theme" for m in page.evaluate("window.bridgeMessages"))
    # A live change from AMI applies straight away.
    page.evaluate("(origin)=>document.querySelector('iframe').contentWindow.postMessage({type:'ami-theme',theme:'dark'},origin)", child_url)
    child.wait_for_function("document.documentElement.dataset.theme === 'dark'")
    page.evaluate("(origin)=>document.querySelector('iframe').contentWindow.postMessage({type:'ami-theme',theme:'light'},origin)", child_url)
    child.wait_for_function("document.documentElement.dataset.theme === 'light'")
    # A forged message from the frame itself, even claiming AMI's origin, is ignored.
    child.evaluate("""() => window.dispatchEvent(new MessageEvent('message',{
      origin:document.querySelector('meta[name=ami-origin]').content,source:window,data:{type:'ami-theme',theme:'dark'}}))""")
    assert child.evaluate("document.documentElement.dataset.theme") == "light"
    # Navigating inside the frame keeps AMI's theme on the next page.
    child.evaluate("window.location.href = '/ais/dashboard'")
    child.wait_for_url("**/ais/dashboard?ami=1")
    child = next(f for f in page.frames if "/ais/dashboard" in f.url)
    child.wait_for_load_state("load")
    child.wait_for_function("document.documentElement.dataset.theme === 'light'")
    page.wait_for_timeout(300)
    assert child.evaluate("document.documentElement.dataset.theme") == "light"
    assert child.evaluate("localStorage.getItem('intercept-theme')") == "dark"
    # Standalone, the stored local choice applies and the toggle still flips and saves it.
    standalone = context.new_page()
    standalone.goto(child_url, wait_until="load")
    standalone.locator("#mainSidebar").wait_for()
    assert standalone.locator("html.ami-embedded").count() == 0
    assert standalone.evaluate("document.documentElement.dataset.theme") == "dark"
    standalone.evaluate("toggleTheme()")
    assert standalone.evaluate("[document.documentElement.dataset.theme, localStorage.getItem('intercept-theme')]") == ["light", "light"]
    standalone.evaluate("toggleTheme()")
    assert standalone.evaluate("[document.documentElement.dataset.theme, localStorage.getItem('intercept-theme')]") == ["dark", "dark"]
    standalone.close()
    context.close()
