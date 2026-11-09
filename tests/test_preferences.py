"""Account preference security, migration and bootstrap contract."""

import json
import re
from pathlib import Path

import pytest

from utils.database import get_db
from utils.preferences import PER_DEVICE_KEYS, PER_DEVICE_PREFIXES, SYNCED_KEYS, user_id

URL = '/api/me/prefs'


@pytest.fixture(autouse=True)
def clean_preferences():
    with get_db() as conn:
        conn.execute('DELETE FROM user_prefs')
    yield
    with get_db() as conn:
        conn.execute('DELETE FROM user_prefs')


def headers(username='admin'):
    return {'X-Intercept-Prefs': '1', 'X-Intercept-Prefs-Owner': str(user_id(username))}


def put(client, data, **kwargs):
    return client.put(URL, json=data, headers=headers(), **kwargs)


@pytest.mark.parametrize('method', ['get', 'put'])
def test_auth_required(anon_client, method):
    assert getattr(anon_client, method)(URL).status_code == 401


def test_signed_in_without_real_account_is_rejected(client):
    with client.session_transaction() as sess:
        sess['username'] = 'no-such-user'
    assert client.get(URL).status_code == 401


def test_allowed_values_and_removal(client):
    assert put(client, {'observerLat': '51.5', 'adsb_watchlist': '["ABCDEF"]'}).status_code == 200
    assert client.get(URL).json['prefs']['observerLat'] == '51.5'
    assert put(client, {'observerLat': None}).status_code == 200
    assert client.get(URL).json['prefs']['observerLat'] is None
    # A stale browser's first import cannot resurrect deleted preferences.
    assert client.put(URL + '?import=1', json={'observerLat': 'old', 'observerLon': '-1'},
                      headers=headers()).status_code == 200
    assert client.get(URL).json['prefs'] == {
        'observerLat': None, 'observerLon': '-1', 'adsb_watchlist': '["ABCDEF"]'}


@pytest.mark.parametrize('data', [
    {'unknown': 'x'}, {'mainSidebarCollapsed': 'true'}, {'intercept.sidebar.open.pager': '[]'},
    {'observerLat': 51}, {'observerLat': {}}, [], None,
])
def test_reject_invalid_atomically(client, data):
    response = client.put(URL, data=json.dumps(data), content_type='application/json', headers=headers())
    assert response.status_code == 400
    assert client.get(URL).json['prefs'] == {}


def test_size_caps_are_bytes_and_atomic(client):
    assert put(client, {'pagerPresets': 'x' * 65536}).status_code == 200
    assert put(client, {'pagerPresets': 'é' * 32769}).status_code == 400
    assert put(client, dict.fromkeys(sorted(SYNCED_KEYS)[:9], 'x' * 65536)).status_code == 400
    assert client.get(URL).json['prefs'] == {'pagerPresets': 'x' * 65536}


@pytest.mark.parametrize('extra', [
    {'Origin': 'https://foreign.example'}, {'Sec-Fetch-Site': 'cross-site'},
    {'X-Intercept-Prefs': ''}, {'X-Intercept-Prefs-Owner': 'other-account'},
])
def test_same_origin_protection(client, extra):
    assert client.put(URL, json={'observerLat': '1'}, headers={**headers(), **extra}).status_code == 403


def test_json_required(client):
    assert client.put(URL, data='observerLat=1', headers=headers()).status_code == 403


def test_per_user_isolation(app, client):
    with get_db() as conn:
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('prefs-other', 'unused', 'user')")
    try:
        assert put(client, {'observerLat': '1'}).status_code == 200
        other = app.test_client()
        with other.session_transaction() as sess:
            sess.update(logged_in=True, username='prefs-other')
        assert other.get(URL).json['prefs'] == {}
        assert other.put(URL, json={'observerLat': '2'}, headers=headers('prefs-other')).status_code == 200
        assert client.get(URL).json['prefs']['observerLat'] == '1'
        # Client supplied identity headers cannot choose an account.
        assert client.get(URL, headers={'X-User-ID': str(user_id('prefs-other'))}).json['prefs']['observerLat'] == '1'
    finally:
        with get_db() as conn:
            conn.execute("DELETE FROM users WHERE username = 'prefs-other'")


def test_bootstrap_is_safe_first_and_private(client, anon_client):
    value = '</script><script>window.breakout=true</script>\u2028&'
    assert put(client, {'pagerPresets': value}).status_code == 200
    response = client.get('/messages')
    html = response.get_data(as_text=True)
    payload = re.search(r'id="intercept-account-prefs" type="application/json">(.*?)</script>', html, re.S)[1]
    assert json.loads(payload)['prefs']['pagerPresets'] == value
    assert '</script>' not in payload
    assert html.index('js/core/preferences.js') < html.index("localStorage.getItem")
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'Cookie' in response.vary
    assert 'intercept-account-prefs' not in anon_client.get('/login').get_data(as_text=True)


def test_registry_covers_literal_storage_keys_and_layout():
    root = Path(__file__).resolve().parents[1]
    classified = SYNCED_KEYS | set(PER_DEVICE_KEYS)
    for folder in ['static/js', 'templates']:
        for path in (root / folder).rglob('*'):
            if path.suffix not in ('.html', '.js'):
                continue
            literals = re.findall(r'localStorage\??\.(?:getItem|setItem|removeItem)\(\s*[\'\"]([^\'\"]+)', path.read_text())
            assert all(k in classified or k.startswith(PER_DEVICE_PREFIXES) for k in literals), (path, literals)
    source = (root / 'static/js/core/settings-manager.js').read_text()
    layout = re.search(r'const LAYOUT_KEYS = \[(.*?)\];', source, re.S)[1]
    assert set(re.findall(r"'([^']+)'", layout)) <= set(PER_DEVICE_KEYS)
    assert not SYNCED_KEYS.intersection(PER_DEVICE_KEYS)


def test_all_document_heads_bootstrap_first():
    root = Path(__file__).resolve().parents[1] / 'templates'
    for path in root.rglob('*.html'):
        source = path.read_text()
        if re.search(r'^\s*<head>', source, re.M):
            assert re.search(r"<head>\s*{% include 'partials/preferences_head.html' %}", source), path


def test_remote_adsb_receiver_is_persisted_and_bootstrapped(client):
    value = json.dumps({"id": "a" * 32, "host": "10.10.42.10", "port": 30003, "enabled": True})
    assert put(client, {"adsb.remoteReceiver": value}).status_code == 200
    assert client.get(URL).json["prefs"]["adsb.remoteReceiver"] == value
    html = client.get("/adsb/dashboard").get_data(as_text=True)
    payload = re.search(r'id="intercept-account-prefs" type="application/json">(.*?)</script>', html, re.S)[1]
    assert json.loads(payload)["prefs"]["adsb.remoteReceiver"] == value
    # Feeds come from the shared list; the old free-text Save control is gone.
    assert 'id="saveRemoteSbs"' not in html
    assert 'id="remoteSbsHealth"' in html
