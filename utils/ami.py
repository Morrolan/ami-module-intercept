"""Read-only AMI adapter. No decoder control or hardware probing lives here."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from config import VERSION

log = logging.getLogger(__name__)
PROCESSES = {
    "pager": "current_process", "sensor": "sensor_process", "adsb": "adsb_process",
    "ais": "ais_process", "acars": "acars_process", "vdl2": "vdl2_process",
    "aprs": "aprs_process", "radiosonde": "radiosonde_process", "morse": "morse_process",
    "meteor": "meteor_process", "ook": "ook_process", "dsc": "dsc_process",
}


def iso(epoch=None):
    return datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc).isoformat()


def ami_origin():
    """Only an explicit HTTP(S) origin can opt in to embedding and service access."""
    value = os.environ.get("AMI_URL", "").rstrip("/")
    try:
        url = urlsplit(value)
        if (not re.fullmatch(r"https?://(?:[A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9a-fA-F:]+\])(?::[0-9]{1,5})?", value)
                or url.scheme not in ("https", "http") or not url.hostname or url.username or url.password
                or url.path or url.query or url.fragment or any(c.isspace() for c in value)):
            return None
        _ = url.port
        return value
    except ValueError:
        return None


def token_valid(header):
    if not ami_origin() or not header.startswith("Bearer "):
        return False
    token = header[7:]
    if not 32 <= len(token) <= 256:
        return False
    # The environment contains a digest, never the bearer secret itself.
    expected = os.environ.get("INTERCEPT_AMI_TOKEN_SHA256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        return False
    return hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), expected)


def envelope(data, source, as_of=None, stale=False):
    return {"data": data, "asOf": as_of, "sources": [{"name": source, "health": "stale" if stale else "ok"}], "stale": stale}


def process_states():
    import app as runtime
    states = {}
    for name, attr in PROCESSES.items():
        proc = getattr(runtime, attr, None)
        states[name] = "idle" if proc is None else "running" if proc.poll() is None else "stopped"
    return states


def receivers():
    from utils.sdr import detection
    devices = detection.get_cached_devices()
    observed = detection._all_devices_cache_ts  # Cache's observation time, not request time.
    rows = [{"index": d.index, "type": d.sdr_type.value, "network": d.is_network} for d in devices or []]
    return envelope(rows, "Intercept receiver discovery cache", iso(observed) if observed else None,
                    not observed or time.time() - observed > 60)


def contacts(kind, limit):
    import app as runtime
    store = runtime.adsb_aircraft if kind == "aircraft" else runtime.ais_vessels
    fields = ("icao", "callsign", "registration", "altitude", "speed", "heading", "lat", "lon") if kind == "aircraft" else (
        "mmsi", "name", "ship_type", "speed", "course", "lat", "lon")
    # One atomic snapshot, including the actual last-observed timestamps.
    with store._lock:
        entries = [(dict(row), store.timestamps.get(key)) for key, row in store.data.items() if isinstance(row, dict)]
    now = time.time()
    fresh = sum(observed is not None and now - observed <= store.max_age for _, observed in entries)
    entries.sort(key=lambda pair: pair[1] or 0, reverse=True)
    result = []
    for row, observed in entries[:limit]:
        clean = {k: v[:80] if isinstance(v, str) else v for k, v in row.items()
                 if k in fields and isinstance(v, (str, int, float)) and not isinstance(v, bool)
                 and (not isinstance(v, float) or math.isfinite(v))}
        clean.update(asOf=iso(observed) if observed else None,
                     stale=observed is None or now - observed > store.max_age)
        result.append(clean)
    latest = entries[0][1] if entries else None
    data = {"contacts": result, "total": len(entries), "fresh": fresh, "stale": len(entries) - fresh,
            "lastMessageAt": iso(latest) if latest is not None else None}
    return envelope(data, f"Intercept {kind} decoder cache", data["lastMessageAt"],
                    latest is None or now - latest > store.max_age)


class EventJournal:
    """Durable, bounded health transitions. Never stores decoded messages or device identities."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, value TEXT NOT NULL, since REAL NOT NULL, alerted INTEGER NOT NULL DEFAULT 0);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def sample(self, states, now=None):
        now = time.time() if now is None else now
        with self.lock, self.connect() as db:
            for name, value in states.items():
                old = db.execute("SELECT value,since,alerted FROM state WHERE name=?", (name,)).fetchone()
                if old is None:
                    db.execute("INSERT INTO state VALUES (?,?,?,0)", (name, value, now))
                    continue
                previous, since, alerted = old
                if previous != value:
                    # An absent process is a normal user stop. Only an exited process remaining
                    # attached for a minute is considered a fault; no notifications for idle modes.
                    if alerted:
                        self._append(db, name, False, now)
                    db.execute("UPDATE state SET value=?,since=?,alerted=0 WHERE name=?", (value, now, name))
                elif value == "stopped" and not alerted and now - since >= 60:
                    self._append(db, name, True, now)
                    db.execute("UPDATE state SET alerted=1 WHERE name=?", (name,))
            db.execute("DELETE FROM events WHERE created < ?", (now - 48 * 3600,))

    @staticmethod
    def _append(db, name, failed, now):
        key = f"decoder:{name}:critical"
        event = {"module": "intercept", "kind": "decoder-health", "severity": "critical" if failed else "info",
                 "title": f"{name.upper()} decoder exited" if failed else f"Resolved: {name.upper()} decoder",
                 "body": "The decoder process has remained stopped for at least one minute." if failed else "The decoder is running again or has been released.",
                 "eventTime": iso(now), "observedAt": iso(now), "users": None,
                 "dedupeKey": key if failed else f"{key}:resolved:{now}", "clears": None if failed else key}
        cur = db.execute("INSERT INTO events(created,body) VALUES (?,?)", (now, json.dumps(event)))
        event["id"] = f"intercept:{cur.lastrowid}"
        db.execute("UPDATE events SET body=? WHERE seq=?", (json.dumps(event), cur.lastrowid))

    def recent(self, after=0, limit=50):
        with self.connect() as db:
            return [(seq, json.loads(body)) for seq, body in db.execute(
                "SELECT seq,body FROM events WHERE seq>? ORDER BY seq LIMIT ?", (after, limit))]

    def latest(self):
        with self.connect() as db:
            return db.execute("SELECT COALESCE((SELECT seq FROM sqlite_sequence WHERE name='events'),0)").fetchone()[0]


_journal = None
_monitor_lock = threading.Lock()


def journal():
    global _journal
    with _monitor_lock:
        if _journal is None:
            from utils.database import DB_DIR
            _journal = EventJournal(DB_DIR / "ami-events.sqlite")
            # A single worker owns decoder state in Intercept (as in its existing WSGI config).
            if os.environ.get("INTERCEPT_SKIP_DEFERRED_INIT") != "1":
                threading.Thread(target=_monitor, daemon=True, name="ami-health").start()
    return _journal


def _monitor():
    while True:
        try:
            _journal.sample(process_states())
        except Exception:
            log.exception("AMI health sample failed")
        time.sleep(15)


def status():
    cached = receivers()
    return envelope({"version": VERSION, "decoders": process_states(),
                     "receivers": cached}, "Intercept process state", iso(), cached["stale"])


def panel():
    states = process_states()
    receiver_data = receivers()
    return {"title": "Intercept", "updatedAt": iso(), "sections": [
        {"id": "receivers", "title": "Signal intelligence", "tiles": [
            {"label": "Active decoders", "value": str(sum(v == "running" for v in states.values())), "level": "ok"},
            {"label": "Cached receivers", "value": str(len(receiver_data["data"])),
             "sub": "Discovery cache is stale" if receiver_data["stale"] else "Last discovery snapshot",
             "level": "warn" if receiver_data["stale"] else "ok"}]},
        {"id": "decoders", "title": "Decoders", "items": [
            {"label": name.upper(), "value": state, "status": {"running": "ok", "idle": "off", "stopped": "bad"}[state]}
            for name, state in states.items()]}]}


def tool(name, description, properties=None, panel_tool=False):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties or {}, "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
            "_meta": {"ami/risk": "read", "ami/scopes": ["intercept.read"], "ami/timeoutMs": 5000,
                      **({"ami/panel": True} if panel_tool else {})}}


TOOLS = [tool("get_status", "Read decoder process status. Idle does not imply a receiver fault."),
         tool("list_receivers", "Read cached receiver types without probing hardware. Stale or empty is not proof of absence."),
         tool("get_contacts", "Read aircraft or vessel contacts. Counts are exact; contacts is only the most recent N. Fresh means within the store TTL; total includes stale retained contacts. No WiFi, Bluetooth or pager payloads.", {
             "kind": {"type": "string", "enum": ["aircraft", "vessels"]},
             "limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
         tool("get_recent_events", "Read recent decoder-health events, oldest first.", {
             "after": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
         tool("get_panel", "Read the AMI Overview panel.", panel_tool=True)]


def call_tool(name, args):
    allowed = next((t["inputSchema"]["properties"] for t in TOOLS if t["name"] == name), None)
    if allowed is None or not isinstance(args, dict) or set(args) - set(allowed):
        raise ValueError("Unknown tool or arguments")
    for key, value in args.items():
        prop = allowed[key]
        if prop["type"] == "integer" and (type(value) is not int or value < prop.get("minimum", 0) or value > prop.get("maximum", 2**63 - 1)):
            raise ValueError("Invalid integer argument")
        if "enum" in prop and value not in prop["enum"]:
            raise ValueError("Invalid kind")
    if name == "get_status":
        return status()
    if name == "list_receivers":
        return receivers()
    if name == "get_contacts":
        return contacts(args.get("kind", "aircraft"), args.get("limit", 20))
    if name == "get_panel":
        return panel()
    events = [ev for _, ev in journal().recent(args.get("after", 0), args.get("limit", 20))]
    return envelope(events, "Intercept decoder-health journal", iso(), False)
