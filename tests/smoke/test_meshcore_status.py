"""Queued MeshCore status events must not override the current connection."""
from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.fixture
def connected_page(browser):
    page = browser.new_page()
    try:
        page.set_content('''<span id="meshcoreStatusDot"></span>
            <span id="meshcoreStatusText"></span>
            <button id="meshcoreConnectBtn"></button>
            <button id="meshcoreDisconnectBtn"></button>
            <div id="meshcoreMessageFeed"></div><span id="meshcoreMsgCount"></span>
            <input id="meshcoreComposeInput">
            <select id="meshcoreRecipientSelect"><option value="BROADCAST">Broadcast</option></select>''')
        page.evaluate('''() => {
            window.serverStatus = {state: 'connected'};
            window.sources = [];
            window.alerts = [];
            window.alert = message => alerts.push(message);
            window.fetch = async () => ({json: async () => window.serverStatus});
            window.EventSource = class {
                constructor() { this.closed = false; window.sources.push(this); }
                close() { this.closed = true; }
            };
        }''')
        script = Path(__file__).resolve().parents[2] / 'static/js/modes/meshcore.js'
        page.add_script_tag(path=str(script.parents[1] / 'core/content-layout.js'))
        page.add_script_tag(path=str(script))
        page.evaluate('MeshCore.init()')
        expect(page.locator('#meshcoreStatusText')).to_have_text('Connected')
        yield page
    finally:
        page.close()


@pytest.mark.parametrize('queued_state', ['connecting', 'error'])
def test_queued_status_rechecks_current_connection(connected_page, queued_state):
    page = connected_page
    page.evaluate('''state => sources[0].onmessage({data: JSON.stringify({
        type: 'status', data: {state,
            message: state === 'error' ? 'Device disconnected unexpectedly' : undefined}
    })})''', queued_state)
    expect(page.locator('#meshcoreStatusText')).to_have_text('Connected')
    assert page.evaluate('sources[0].closed') is False
    # A real current backend error must still be displayed.
    page.evaluate('''() => {
        serverStatus = {state: 'error', message: 'Device disconnected unexpectedly'};
        sources[0].onmessage({data: JSON.stringify({type: 'status', data: serverStatus})});
    }''')
    expect(page.locator('#meshcoreStatusText')).to_have_text('Device disconnected unexpectedly')
    assert page.evaluate('sources[0].closed') is True


def test_delayed_older_status_response_cannot_restore_error(connected_page):
    page = connected_page
    page.evaluate('''() => {
        window.pending = [];
        window.fetch = () => new Promise(resolve => pending.push(resolve));
        const event = {data: JSON.stringify({type: 'status', data: {state: 'error'}})};
        sources[0].onmessage(event);
        sources[0].onmessage(event);
    }''')
    assert page.evaluate('pending.length') == 2
    page.evaluate('''async () => {
        pending[1]({json: async () => ({state: 'connected'})});
        await new Promise(resolve => setTimeout(resolve, 0));
        pending[0]({json: async () => ({state: 'error', message: 'Device disconnected unexpectedly'})});
        await new Promise(resolve => setTimeout(resolve, 0));
    }''')
    expect(page.locator('#meshcoreStatusText')).to_have_text('Connected')
    assert page.evaluate('sources[0].closed') is False



def test_message_is_accepted_only_after_radio_confirmation(connected_page):
    page = connected_page
    page.evaluate("fetch = async () => ({ok: true, json: async () => ({status: 'accepted'})})")
    page.locator('#meshcoreComposeInput').fill('synthetic')
    page.evaluate('MeshCore.sendMessage()')
    expect(page.locator('.meshcore-message.pending')).to_have_count(0)
    expect(page.locator('.meshcore-message-header')).to_contain_text('Accepted by radio')
    assert page.evaluate('alerts') == []


@pytest.mark.parametrize('code,message', [(502, 'Radio did not accept the message'),
                                         (504, 'Radio confirmation timed out; delivery is unknown')])
def test_message_failure_is_shown_and_text_is_preserved(connected_page, code, message):
    page = connected_page
    page.evaluate("d => { fetch = async () => ({ok: false, status: d.code, json: async () => ({status: 'error', message: d.message})}); }",
                  {'code': code, 'message': message})
    page.locator('#meshcoreComposeInput').fill('synthetic')
    page.evaluate('MeshCore.sendMessage()')
    expect(page.locator('.meshcore-message')).to_have_count(0)
    expect(page.locator('#meshcoreComposeInput')).to_have_value('synthetic')
    assert page.evaluate('alerts') == [message]
