"""Preferences follow real sign-ins across separate browser storage contexts."""

import threading

import pytest
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from utils.database import get_db


@pytest.fixture(autouse=True)
def reset_login_limit():
    import app as runtime

    if hasattr(runtime.limiter, 'reset'):
        runtime.limiter.reset()


@pytest.fixture(scope='module')
def prefs_url(app):
    # Unlike the general smoke fixture, authenticate real accounts here.
    username = 'prefs-browser'
    with get_db() as conn:
        conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                     (username, generate_password_hash('prefs-browser-password'), 'user'))
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    thread.join(timeout=5)
    with get_db() as conn:
        conn.execute('DELETE FROM users WHERE username = ?', (username,))


def sign_in(context, url):
    # Real login route/cookie; then load a lightweight standalone page.
    response = context.request.post(url + '/login', form={
        'username': 'prefs-browser', 'password': 'prefs-browser-password'}, max_redirects=0)
    assert response.status == 302
    page = context.new_page()
    page.goto(url + '/messages', wait_until='domcontentloaded')
    page.wait_for_function('Boolean(window.InterceptPrefs)')
    page.evaluate('() => window.InterceptPrefs.flush()')
    return page


def local_only(context, url):
    context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(url) else route.abort())


def test_account_sync_and_offline(browser, prefs_url):
    first = browser.new_context()
    second = browser.new_context()
    try:
        local_only(first, prefs_url)
        local_only(second, prefs_url)
        page = sign_in(first, prefs_url)
        # Wait for the upload that carries this change: the page's own start-up writes may go first.
        with page.expect_response(lambda r: '/api/me/prefs' in r.url and r.request.method == 'PUT'
                                  and 'interceptTimezone' in (r.request.post_data or '')) as saved:
            page.evaluate("""() => {
                localStorage.setItem('interceptTimezone', 'Europe/London');
                localStorage.setItem('airband.frequencyPresets', '[{"id":"tower","name":"Tower","frequency":119.805}]');
                localStorage.setItem('mainSidebarCollapsed', 'true');
                localStorage.setItem('audioMuted', 'true');
                sessionStorage.setItem('observerLon', 'session-only');
            }""")
        assert saved.value.ok
        fresh = sign_in(second, prefs_url)
        assert fresh.evaluate("localStorage.getItem('interceptTimezone')") == 'Europe/London'
        assert 'Tower' in fresh.evaluate("localStorage.getItem('airband.frequencyPresets')")
        assert fresh.evaluate("localStorage.getItem('mainSidebarCollapsed')") is None
        assert fresh.evaluate("localStorage.getItem('audioMuted')") is None
        assert fresh.evaluate("localStorage.getItem('observerLon')") is None
        # Embedded storage uses the same early bootstrap and account.
        fresh.goto(prefs_url + '/messages?ami=1', wait_until='domcontentloaded')
        assert fresh.evaluate("localStorage.getItem('interceptTimezone')") == 'Europe/London'
        errors = []
        fresh.on('pageerror', lambda err: errors.append(str(err)))
        second.route('**/api/me/prefs*', lambda route: route.abort())
        fresh.evaluate("localStorage.setItem('interceptTimezone', 'UTC')")
        fresh.wait_for_timeout(1000)
        assert fresh.evaluate("localStorage.getItem('interceptTimezone')") == 'UTC'
        fresh.reload(wait_until='domcontentloaded')
        assert fresh.evaluate('Boolean(window.InterceptPrefs)')
        assert fresh.evaluate("localStorage.getItem('interceptTimezone')") == 'UTC'
        assert not errors
    finally:
        first.close()
        second.close()


@pytest.fixture
def shared_feed(prefs_url):
    """One admin-listed ADS-B feed in the real shared receiver list."""
    from utils.remote_sdr_health import monitor

    feed = monitor.save({'name': 'Roof Pi', 'host': '10.10.42.6', 'port': 30003, 'type': 'adsb_sbs'})
    yield feed
    try:
        monitor.remove(feed['id'])
    except KeyError:
        pass


def feed_option(page, feed):
    value = 'remote-sbs:' + feed['id']
    page.wait_for_function(
        "value => Array.from(document.getElementById('adsbDeviceSelect').options).some(o => o.value === value)",
        arg=value, timeout=5000)
    return value


def test_remote_adsb_choice_restores_in_fresh_browser(browser, prefs_url, shared_feed):
    contexts = [browser.new_context(), browser.new_context(viewport={"width": 390, "height": 844})]
    try:
        for context in contexts:
            local_only(context, prefs_url)
            context.add_init_script("""HTMLMediaElement.prototype.play = () => Promise.resolve();
                if (window.speechSynthesis) window.speechSynthesis.speak = () => {};""")
        page = sign_in(contexts[0], prefs_url)
        page.goto(prefs_url + '/adsb/dashboard', wait_until='domcontentloaded')
        value = feed_option(page, shared_feed)
        # A non-admin sees the shared feed, with its health, and nowhere to type a host.
        assert page.locator('#saveRemoteSbs').count() == 0
        assert 'Roof Pi' in page.locator(f'#adsbDeviceSelect option[value="{value}"]').inner_text()
        with page.expect_response(lambda r: r.url.endswith('/api/me/prefs') and r.request.method == 'PUT') as saved:
            page.select_option('#adsbDeviceSelect', value)
        assert saved.value.ok
        assert page.locator('#remoteSbsHealth').is_visible()
        fresh = sign_in(contexts[1], prefs_url)
        fresh.goto(prefs_url + '/adsb/dashboard?ami=1', wait_until='domcontentloaded')
        fresh.wait_for_function("value => document.getElementById('adsbDeviceSelect').value === value", arg=value)
        assert fresh.evaluate("document.getElementById('remoteSbsHost').value") == '10.10.42.6'
        contexts[1].route('**/api/me/prefs', lambda route: route.fulfill(status=503, body='unavailable'))
        fresh.select_option('#adsbDeviceSelect', index=0)
        fresh.wait_for_function("document.getElementById('remoteSbsSaveStatus').textContent.includes('Could not remember')")
    finally:
        for context in contexts:
            context.close()


@pytest.mark.parametrize('viewport,devices,start_mode', [
    ({"width": 1600, "height": 1000}, [{"index": 0, "sdr_type": "rtlsdr", "name": "Local RTL"}], "manual"),
    ({"width": 390, "height": 844}, [], "auto"),
])
def test_saved_remote_is_selectable_and_start_uses_it(browser, prefs_url, viewport, devices, start_mode, shared_feed):
    import json

    context = browser.new_context(viewport=viewport)
    calls = []
    active = {"tracking_active": False}
    try:
        local_only(context, prefs_url)
        context.add_init_script("""HTMLMediaElement.prototype.play = () => Promise.resolve();
            if (window.speechSynthesis) window.speechSynthesis.speak = () => {};""")
        context.route('**/devices', lambda r: r.fulfill(json=devices))
        context.route('**/adsb/session', lambda r: r.fulfill(json=active))

        def start(route):
            calls.append(json.loads(route.request.post_data))
            active.update(tracking_active=True, session={"sdr_type": "remote", "device_index": 0,
                          "remote_host": "10.10.42.6", "remote_port": 30003})
            route.fulfill(json={"status": "started", "session": active["session"]})

        context.route('**/adsb/start', start)
        context.route('**/adsb/stream', lambda r: r.fulfill(content_type='text/event-stream', body=''))
        page = sign_in(context, prefs_url)
        page.goto(prefs_url + '/adsb/dashboard', wait_until='domcontentloaded')
        remote = feed_option(page, shared_feed)
        page.select_option('#adsbDeviceSelect', remote)
        assert page.locator('#adsbDeviceSelect').input_value() == remote
        page.evaluate('() => initDeviceSelectors(true)')
        assert page.locator('#adsbDeviceSelect').input_value() == remote
        if devices:
            page.select_option('#adsbDeviceSelect', 'rtlsdr:0')
            assert not page.evaluate("document.getElementById('useRemoteDump1090').checked")
            page.select_option('#adsbDeviceSelect', remote)
        assert page.evaluate("document.getElementById('useRemoteDump1090').checked")
        page.evaluate("() => { adsbCurrentAgent = '7'; updateSourceIndicator(); }")
        assert page.locator(f'#adsbDeviceSelect option[value="{remote}"]').count() == 0
        assert not page.locator('#adsbGainInput').is_disabled()
        assert not page.locator('#adsbBiasT').is_disabled()
        page.evaluate("() => { adsbCurrentAgent = 'local'; updateSourceIndicator(); }")
        assert page.locator('#adsbDeviceSelect').input_value() == remote
        if start_mode == 'auto':
            page.evaluate('() => tryAutoStartLocal()')
        else:
            page.locator('#startBtn').click()
        page.wait_for_function("document.getElementById('startBtn').textContent === 'STOP'", timeout=2000)
        assert calls == [{"remote_sbs_host": "10.10.42.6", "remote_sbs_port": 30003}]
        assert '10.10.42.6' in page.locator('#stripSource').inner_text()
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function("value => document.getElementById('adsbDeviceSelect').value === value", arg=remote, timeout=5000)
        assert '10.10.42.6' in page.locator('#stripSource').inner_text()
        assert page.locator('#adsbDeviceSelect').is_disabled()
        page.evaluate("() => { const select = document.getElementById('adsbDeviceSelect'); select.value = 'rtlsdr:0'; select.dispatchEvent(new Event('change')); }")
        assert page.evaluate("document.getElementById('useRemoteDump1090').checked")
        assert page.locator('#adsbDeviceSelect').input_value() == remote
        assert '10.10.42.6' in page.locator('#stripSource').inner_text()
    finally:
        context.close()


def test_real_history_disabled_session_restores_remote_over_saved_local(browser, prefs_url, monkeypatch, shared_feed):
    import routes.adsb as adsb

    monkeypatch.setattr(adsb, 'ADSB_HISTORY_ENABLED', False)
    monkeypatch.setattr(adsb, 'adsb_using_service', False)
    monkeypatch.setattr(adsb, '_runtime_session', None)
    monkeypatch.setattr(adsb, 'parse_sbs_stream', lambda *_: None)
    context = browser.new_context()
    try:
        local_only(context, prefs_url)
        context.route('**/devices', lambda r: r.fulfill(json=[{'index': 0, 'sdr_type': 'rtlsdr', 'name': 'Local RTL'}]))
        context.route('**/adsb/stream', lambda r: r.fulfill(content_type='text/event-stream', body=''))
        page = sign_in(context, prefs_url)
        page.evaluate("localStorage.setItem('adsb.remoteReceiver', JSON.stringify({host:'old-host',port:30003,enabled:false}))")
        page.evaluate('() => InterceptPrefs.flush()')
        # Use the real start/status routes: older tests supplied invented complete metadata.
        started = context.request.post(prefs_url + '/adsb/start', data={'remote_sbs_host': '10.10.42.6', 'remote_sbs_port': 30003})
        assert started.ok
        remote = 'remote-sbs:' + shared_feed['id']
        page.goto(prefs_url + '/adsb/dashboard?ami=1', wait_until='domcontentloaded')
        page.wait_for_function("value => document.querySelector('#adsbDeviceSelect').value === value", arg=remote)
        assert '10.10.42.6:30003' in page.locator('#stripSource').inner_text()
        assert page.locator('#adsbDeviceSelect').is_disabled()
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function("value => document.querySelector('#adsbDeviceSelect').value === value", arg=remote)
        page.evaluate('() => initDeviceSelectors(true)')
        assert page.locator('#adsbDeviceSelect').input_value() == remote
    finally:
        context.request.post(prefs_url + '/adsb/stop', data={})
        context.close()
