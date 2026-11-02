"""Security, contract, freshness and resumable-event checks for the AMI adapter."""
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from utils import ami

TOKEN = "test-only-service-secret-with-at-least-32-characters"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("AMI_URL", "https://ami.example.test")
    monkeypatch.setenv("INTERCEPT_AMI_TOKEN_SHA256", hashlib.sha256(TOKEN.encode()).hexdigest())
    monkeypatch.setattr(ami, "_journal", ami.EventJournal(tmp_path / "events.sqlite"))


def rpc(client, method, params=None, headers=None):
    return client.post("/api/module/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method,
                                               "params": params or {}}, headers=AUTH if headers is None else headers)


def test_opt_in_and_public_metadata(anon_client, monkeypatch):
    manifest = anon_client.get("/.well-known/ami-module.json").get_json()
    assert manifest["auth"] == {"type": "token", "roles": ["admin"]}
    assert manifest["ui"]["entry"] == "/?ami=1"
    assert manifest["ui"]["deepLinks"] == {"aircraft": "/adsb/dashboard?ami=1", "vessels": "/ais/dashboard?ami=1"}
    health = anon_client.get(manifest["health"]).get_json()
    assert set(health) == {"status", "module", "version", "checkedAt", "detail"}
    assert health["status"] == "ok"
    for value in ("", "https://ami.example.test/path", "https://user@ami.example.test", "https://evil.test;script-src", "https://evil.test:99999"):
        monkeypatch.setenv("AMI_URL", value)
        assert anon_client.get("/.well-known/ami-module.json").status_code == 404
        assert rpc(anon_client, "tools/list").status_code == 404


def test_session_cannot_authorize_module(client, anon_client, monkeypatch):
    for c in (client, anon_client):
        assert rpc(c, "tools/list", headers={}).status_code == 401
        assert rpc(c, "tools/list", headers={"Authorization": "Bearer invalid"}).status_code == 401
        assert c.get("/api/module/events").status_code == 401
    monkeypatch.setenv("INTERCEPT_DISABLE_AUTH", "1")
    assert rpc(anon_client, "tools/list", headers={}).status_code == 401
    monkeypatch.delenv("INTERCEPT_AMI_TOKEN_SHA256")
    assert rpc(anon_client, "tools/list").status_code == 401


def test_read_only_tools_and_json_rpc(anon_client, monkeypatch):
    from routes import space_weather as sw
    monkeypatch.setattr(sw, "_fetch_json", lambda *a, **kw: None)
    assert rpc(anon_client, "initialize").get_json()["result"]["protocolVersion"] == "2025-06-18"
    tools = rpc(anon_client, "tools/list").get_json()["result"]["tools"]
    assert {t["name"] for t in tools} == {"get_status", "list_receivers", "get_contacts", "get_recent_events", "get_panel", "get_overview", "get_space_weather"}
    for tool in tools:
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["_meta"]["ami/risk"] == "read"
        assert tool["_meta"]["ami/scopes"] == ["intercept.read"]
        assert "structuredContent" in rpc(anon_client, "tools/call", {"name": tool["name"]}).get_json()["result"]
    for name, args in (("start_capture", {}), ("get_status", {"extra": 1}), ("get_contacts", {"limit": True}),
                       ("get_contacts", {"limit": 51}), ("get_contacts", {"kind": "pager"}),
                       ("get_recent_events", {"after": -1}), ("get_recent_events", {"after": 2**64})):
        assert rpc(anon_client, "tools/call", {"name": name, "arguments": args}).get_json()["error"]["code"] == -32602
    assert rpc(anon_client, "unknown").get_json()["error"]["code"] == -32601
    assert anon_client.post("/api/module/mcp", json=[], headers=AUTH).get_json()["error"]["code"] == -32600
    assert anon_client.post("/api/module/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=AUTH).status_code == 202
    assert anon_client.post("/api/module/mcp", data="x" * 17000, headers=AUTH).status_code == 413


def test_receiver_cache_never_probes(anon_client, monkeypatch):
    from utils.sdr import detection
    monkeypatch.setattr(detection, "detect_all_devices", Mock(side_effect=AssertionError("must not probe")))
    monkeypatch.setattr(detection, "_all_devices_cache_ts", 0)
    result = ami.receivers()
    assert result["stale"] and result["asOf"] is None and result["data"] == []
    device = Mock(index=0, is_network=True, serial="private", rtl_tcp_host="private")
    device.sdr_type.value = "rtlsdr"
    monkeypatch.setattr(detection, "get_cached_devices", lambda: [device])
    monkeypatch.setattr(detection, "_all_devices_cache_ts", time.time() - 120)
    result = ami.receivers()
    assert result["stale"] and set(result["data"][0]) == {"index", "type", "network"}
    assert "private" not in json.dumps(result)


def test_contacts_allowlist_and_observation_age(monkeypatch):
    import app as runtime
    from utils.cleanup import DataStore
    store = DataStore(max_age_seconds=60)
    store.set("abc", {"icao": "abc", "callsign": "TEST", "raw": "private-message", "mac": "private-mac", "lat": float("nan")})
    monkeypatch.setattr(runtime, "adsb_aircraft", store)
    result = ami.contacts("aircraft", 10)
    assert not result["stale"] and result["asOf"]
    assert result["data"]["contacts"][0]["icao"] == "abc"
    assert "private" not in json.dumps(result) and "NaN" not in json.dumps(result)
    store.timestamps["abc"] -= 120
    assert ami.contacts("aircraft", 10)["stale"]
    assert ami.contacts("aircraft", 10)["data"]["contacts"][0]["stale"]


def test_durable_debounced_fault_recovery_and_retention(tmp_path):
    path = tmp_path / "journal.sqlite"
    journal = ami.EventJournal(path)
    start = time.time()
    journal.sample({"adsb": "running", "ais": "idle"}, start)
    journal.sample({"adsb": "stopped", "ais": "idle"}, start + 1)
    journal.sample({"adsb": "stopped", "ais": "idle"}, start + 60)
    assert journal.recent() == []
    journal.sample({"adsb": "stopped", "ais": "idle"}, start + 61)
    # Reopening also keeps the debounce state: no duplicate fault.
    journal = ami.EventJournal(path)
    journal.sample({"adsb": "stopped", "ais": "idle"}, start + 100)
    fault = journal.recent()[0][1]
    assert fault["kind"] == "decoder-health" and fault["severity"] == "critical"
    journal.sample({"adsb": "running", "ais": "idle"}, start + 101)
    assert len(journal.recent()) == 2
    resolved = journal.recent(after=1)[0][1]
    assert resolved["clears"] == fault["dedupeKey"]
    journal.sample({}, start + 24 * 3600 + 102)
    assert len(journal.recent()) == 2
    journal.sample({}, start + 48 * 3600 + 102)
    assert journal.recent() == []
    assert journal.latest() == 2  # Retention must not invalidate the last delivered cursor.


def test_sse_replay_and_cursor(anon_client):
    history = ami.journal()
    now = time.time()
    history.sample({"adsb": "stopped"}, now - 65)
    history.sample({"adsb": "stopped"}, now)
    history.sample({"adsb": "running"}, now + 1)
    response = anon_client.get("/api/module/events", headers={**AUTH, "Last-Event-ID": "intercept:1"}, buffered=False)
    first = next(iter(response.response)).decode()
    assert "id: intercept:2" in first and "event: ami-event" in first and '"clears": "decoder:adsb:critical"' in first
    response.close()
    for cursor in ("invalid", "intercept:-1", "intercept:9999"):
        assert anon_client.get("/api/module/events", headers={**AUTH, "Last-Event-ID": cursor}).status_code == 400


def test_frame_allowlist_and_embed_redirect(anon_client, monkeypatch):
    response = anon_client.get("/login?ami=1")
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'self' https://ami.example.test"
    assert "X-Frame-Options" not in response.headers
    assert b'ami-theme.css' in response.data and b'ami-bridge.js' in response.data
    assert anon_client.get("/?ami=1").headers["Location"] == "/login?ami=1"
    monkeypatch.delenv("AMI_URL")
    response = anon_client.get("/login")
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'self'"



def test_embed_redirect_keeps_other_query_parameters(app):
    from flask import redirect

    import app as app_module

    with app.test_request_context("/somewhere?ami=1"):
        response = app_module.add_security_headers(redirect("/login?next=%2Fadsb&tag=a&tag=b&empty=&ami=0#top"))
    assert response.headers["Location"] == "/login?next=%2Fadsb&tag=a&tag=b&empty=&ami=1#top"
    with app.test_request_context("/somewhere?ami=1"):
        external = app_module.add_security_headers(redirect("https://elsewhere.example/x?a=1"))
    assert external.headers["Location"] == "https://elsewhere.example/x?a=1"

def test_every_document_loads_theme_once():
    templates = Path(__file__).resolve().parents[1] / "templates"
    for file in templates.rglob("*.html"):
        body = file.read_text()
        if "</head>" in body:
            assert body.count("include 'partials/ami_head.html'") == 1, file
