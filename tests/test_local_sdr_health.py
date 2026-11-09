"""Local RTL-SDR health: watcher heartbeat only, menus, Settings data and the AMI warning."""
import json
import time

import pytest

from utils import ami
from utils.sdr import hotplug
from utils.sdr.local_health import LocalSdrHealth

START = 1_800_000_000


def heartbeat(path, available=True, stamp=None):
    doc = {"version": 1, "available": available, "node": "/dev/bus/usb/001/032" if available else None,
           "generation": "g1", "updatedAt": time.time() if stamp is None else stamp}
    path.write_text(json.dumps(doc))


@pytest.fixture
def watcher(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    monkeypatch.setenv(hotplug.STATE_ENV, str(path))
    return path


def test_read_state_tells_not_reporting_from_unplugged(tmp_path):
    path = tmp_path / "status.json"
    assert hotplug.read_state(path)["reporting"] is False
    heartbeat(path, available=False)
    assert hotplug.read_state(path) == {"available": False, "generation": "g1", "reporting": True}
    heartbeat(path, stamp=time.time() - 20)
    assert hotplug.read_state(path)["reporting"] is False


def test_states_and_times(watcher, monkeypatch):
    health = LocalSdrHealth()
    assert health.snapshot()["state"] == "not_reporting"
    heartbeat(watcher)
    online = health.snapshot(now=START)
    assert online["enabled"] and online["state"] == "online" and online["missing_since"] is None
    heartbeat(watcher, available=False)
    missing = health.snapshot(now=START + 30)
    assert missing["state"] == "missing"
    assert missing["last_seen"] == online["last_seen"]
    assert missing["missing_since"].startswith("2027-01-15")
    assert health.snapshot(now=START + 90)["missing_since"] == missing["missing_since"]
    heartbeat(watcher)
    assert health.snapshot(now=START + 95)["missing_since"] is None
    monkeypatch.delenv(hotplug.STATE_ENV)
    assert health.snapshot() == {"enabled": False, "state": "not_set_up", "last_seen": None, "missing_since": None}


def test_snapshot_never_exposes_identity(watcher):
    heartbeat(watcher)
    snapshot = LocalSdrHealth().snapshot()
    assert set(snapshot) == {"enabled", "state", "last_seen", "missing_since"}
    assert "001/032" not in json.dumps(snapshot) and "g1" not in json.dumps(snapshot)


def events(journal):
    return [e for _, e in journal.recent()]


def test_warning_after_two_minutes_once_and_survives_restart(tmp_path):
    path = tmp_path / "events.sqlite"
    journal = ami.EventJournal(path)
    journal.sample_usb("online", START)
    journal.sample_usb("missing", START + 10)
    journal.sample_usb("missing", START + 129)
    assert events(journal) == []
    journal = ami.EventJournal(path)  # restart keeps when it went missing
    journal.sample_usb("missing", START + 130)
    journal.sample_usb("missing", START + 400)
    [warning] = events(journal)
    assert warning["kind"] == "sdr-usb" and warning["severity"] == "warning"
    assert warning["dedupeKey"] == "sdr-usb:local:warning" and warning["clears"] is None
    assert warning["title"] == "Local RTL-SDR missing for 2 minutes"
    journal.sample_usb("online", START + 410)
    journal.sample_usb("online", START + 420)
    cleared = events(journal)[1:]
    assert len(cleared) == 1
    assert cleared[0]["clears"] == "sdr-usb:local:warning" and cleared[0]["severity"] == "info"


def test_brief_unplug_does_not_alert(tmp_path):
    journal = ami.EventJournal(tmp_path / "events.sqlite")
    journal.sample_usb("missing", START)
    journal.sample_usb("online", START + 60)
    journal.sample_usb("missing", START + 75)
    journal.sample_usb("missing", START + 190)
    assert events(journal) == []


def test_not_reporting_neither_opens_nor_clears(tmp_path):
    journal = ami.EventJournal(tmp_path / "events.sqlite")
    journal.sample_usb("not_reporting", START)
    journal.sample_usb("not_reporting", START + 600)
    assert events(journal) == []
    journal.sample_usb("missing", START + 600)
    journal.sample_usb("not_reporting", START + 650)
    journal.sample_usb("missing", START + 720)
    assert len(events(journal)) == 1  # the missing period continued through the silence
    journal.sample_usb("not_reporting", START + 800)
    assert len(events(journal)) == 1


def test_switching_monitoring_off_clears(tmp_path):
    journal = ami.EventJournal(tmp_path / "events.sqlite")
    journal.sample_usb("missing", START)
    journal.sample_usb("missing", START + 120)
    journal.sample_usb("not_set_up", START + 130)
    assert events(journal)[-1]["clears"] == "sdr-usb:local:warning"


def test_devices_marks_only_the_watched_rtlsdr(client, watcher, monkeypatch):
    import app as runtime
    devices = [{"index": 0, "sdr_type": "rtlsdr", "name": "RTL"}, {"index": 1, "sdr_type": "rtlsdr", "name": "B"},
               {"index": 0, "sdr_type": "hackrf", "name": "H"}]
    monkeypatch.setattr(runtime, "describe_devices", lambda found: [dict(d) for d in devices])
    monkeypatch.setattr(runtime.SDRFactory, "detect_devices", staticmethod(lambda: []))
    heartbeat(watcher, available=False)
    listed = client.get("/devices").get_json()
    assert [d.get("health") for d in listed] == ["missing", None, None]
    assert client.get("/devices/local-health").get_json()["state"] == "missing"
    monkeypatch.delenv(hotplug.STATE_ENV)
    assert all("health" not in d for d in client.get("/devices").get_json())


def test_local_health_requires_sign_in(anon_client):
    assert anon_client.get("/devices/local-health").status_code != 200


def test_panel_tile_uses_live_state(watcher):
    heartbeat(watcher, available=False)
    tiles = ami.panel()["sections"][0]["tiles"]
    assert tiles[0] == {"label": "SDR USB", "value": "Waiting for receiver", "level": "warn"}
