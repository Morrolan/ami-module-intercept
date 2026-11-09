"""The shared remote receiver list: admin-managed, typed, with TCP reachability checks.

Health checks are independent of receiver/decoder state. Modes offer the
entries of their type (ADS-B offers ``adsb_sbs`` feeds).
"""
from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

from utils.database import get_db, get_setting, set_setting
from utils.validation import validate_rtl_tcp_port

logger = logging.getLogger('intercept.remote_receivers')

SETTING = 'remote_sdr_health'
IMPORTED = 'remote_sdr_health.adsb_prefs_imported'
ADSB_PREF = 'adsb.remoteReceiver'
# Entries saved before types existed have none; they stay generic, never ADS-B.
TYPES = {
    'adsb_sbs': {'label': 'ADS-B feed (dump1090, port 30003)', 'port': 30003},
    'other': {'label': 'Other TCP service', 'port': None},
}
DEFAULT_TYPE = 'other'
INTERVAL = 60
TIMEOUT = 3
MAX_ENTRIES = 32


def validate_entry(data):
    if not isinstance(data, dict):
        raise ValueError('An SDR name, host and port are required')
    name, host, port = data.get('name'), data.get('host'), data.get('port')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError('Name must contain 1–80 characters')
    if not isinstance(host, str) or not host.strip() or len(host.strip()) > 253:
        raise ValueError('Enter a hostname or IP address without a URL or port')
    host = host.strip()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if (re.fullmatch(r'[0-9.]+', host) or not all(
            re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
            for label in host.split('.')
        )):
            raise ValueError('Enter a valid hostname or IP address') from None
    if isinstance(port, bool) or not isinstance(port, (str, int)):
        raise ValueError('Port must be a whole number from 1 to 65535')
    kind = data.get('type')
    if kind is None:
        kind = DEFAULT_TYPE
    if kind not in TYPES:
        raise ValueError('Choose a receiver type')
    return {'name': name.strip(), 'host': host, 'port': validate_rtl_tcp_port(port), 'type': kind}


def _import_candidate(raw):
    """Old per-account ADS-B preference -> (host, port), or None if unusable."""
    try:
        value = json.loads(raw) if isinstance(raw, str) else None
        if not isinstance(value, dict):
            return None
        host, port = value.get('host'), value.get('port')
        clean = validate_entry({'name': 'ADS-B feed', 'host': host, 'port': port, 'type': 'adsb_sbs'})
        return clean['host'], clean['port']
    except (ValueError, TypeError):
        return None


class RemoteSDRHealth:
    def __init__(self):
        self.lock = threading.RLock()
        self.results = {}
        self.pending = {}
        self.due = {}
        self.slots = threading.BoundedSemaphore(MAX_ENTRIES)
        self.started = False
        self.stop_event = threading.Event()

    def _saved(self):
        # Validate at the boundary even if an older generic settings client wrote it.
        saved = get_setting(SETTING, [], strict=True)
        if not isinstance(saved, list):
            return []
        entries = []
        for item in saved[:MAX_ENTRIES]:
            try:
                clean = validate_entry(item)
                identifier = item.get('id')
                if isinstance(identifier, str) and re.fullmatch(r'[a-f0-9]{32}', identifier):
                    entries.append({'id': identifier, **clean})
            except ValueError:
                continue
        return entries

    def entries(self, kind=None):
        with self.lock:
            return [{**r, **self.results.get(r['id'], {
                'state': 'unknown', 'last_seen': None, 'checked_at': None,
            })} for r in self._saved() if kind is None or r['type'] == kind]

    def find(self, kind, host, port):
        """The saved entry of this type for host:port, or None."""
        host = host.strip().lower() if isinstance(host, str) else host
        for entry in self.entries(kind):
            if entry['host'].lower() == host and entry['port'] == port:
                return entry
        return None

    def import_adsb_preferences(self):
        """Copy receivers saved in account preferences into the shared list, once.

        Runs in one write transaction with the done flag, so a restart or a
        second process cannot import twice. Returns the number of entries added.
        """
        with self.lock, get_db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM settings WHERE key = ?', (IMPORTED,)).fetchone():
                return 0
            row = conn.execute('SELECT value FROM settings WHERE key = ?', (SETTING,)).fetchone()
            try:
                saved = json.loads(row['value']) if row else []
            except ValueError:
                saved = None
            if not isinstance(saved, list):
                # Never overwrite a list we cannot read; try again next start.
                logger.warning('Remote receiver list unreadable; skipping preference import')
                conn.rollback()
                return 0
            have = set()
            for item in saved:
                try:
                    clean = validate_entry(item)
                except ValueError:
                    continue
                if clean['type'] == 'adsb_sbs':
                    have.add((clean['host'].lower(), clean['port']))
            added = 0
            rows = conn.execute(
                'SELECT u.username, p.value FROM user_prefs p JOIN users u ON u.id = p.user_id '
                'WHERE p.key = ? ORDER BY u.username', (ADSB_PREF,)
            ).fetchall()
            for pref in rows:
                candidate = _import_candidate(pref['value'])
                if candidate is None:
                    logger.warning('Skipped saved ADS-B receiver for %s: not a valid host and port',
                                   pref['username'])
                    continue
                host, port = candidate
                if (host.lower(), port) in have:
                    continue
                if len(saved) >= MAX_ENTRIES:
                    logger.warning('Skipped saved ADS-B receiver %s:%s for %s: list is full',
                                   host, port, pref['username'])
                    continue
                saved.append({'id': uuid4().hex, 'name': f'ADS-B feed {host}:{port}',
                              'host': host, 'port': port, 'type': 'adsb_sbs'})
                have.add((host.lower(), port))
                added += 1
            upsert = ('INSERT INTO settings (key, value, value_type, updated_at) '
                      'VALUES (?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET '
                      'value=excluded.value, value_type=excluded.value_type, updated_at=CURRENT_TIMESTAMP')
            if added:
                conn.execute(upsert, (SETTING, json.dumps(saved), 'json'))
            conn.execute(upsert, (IMPORTED, 'true', 'bool'))
            if added:
                logger.info('Copied %d saved ADS-B receiver(s) into the shared list', added)
            return added

    def save(self, data, identifier=None):
        clean = validate_entry(data)
        with self.lock:
            saved = self._saved()
            if identifier is not None:
                old = next((r for r in saved if r['id'] == identifier), None)
                if old is None:
                    raise KeyError(identifier)
                saved.remove(old)
            elif len(saved) >= MAX_ENTRIES:
                raise ValueError(f'At most {MAX_ENTRIES} remote SDRs can be saved')
            identifier = identifier or uuid4().hex
            saved.append({'id': identifier, **clean})
            set_setting(SETTING, saved)
            self.results.pop(identifier, None)
            self.due.pop(identifier, None)
            return next(r for r in self.entries() if r['id'] == identifier)

    def remove(self, identifier):
        with self.lock:
            saved = self._saved()
            remaining = [r for r in saved if r['id'] != identifier]
            if len(saved) == len(remaining):
                raise KeyError(identifier)
            set_setting(SETTING, remaining)
            self.results.pop(identifier, None)
            self.due.pop(identifier, None)

    def _current(self, entry):
        config = {k: entry[k] for k in ('id', 'name', 'host', 'port', 'type')}
        return config in self._saved()

    def _result(self, entry, online):
        if not self._current(entry):
            return
        now = datetime.now(timezone.utc).isoformat()
        previous = self.results.get(entry['id'], {})
        self.results[entry['id']] = {
            'state': 'online' if online else 'offline', 'checked_at': now,
            'last_seen': now if online else previous.get('last_seen'),
        }

    def check(self, entry):
        """Worker only; discard results for endpoints edited/removed in flight."""
        with self.lock:
            if not self._current(entry):
                return
        started = time.monotonic()
        try:
            with socket.create_connection((entry['host'], entry['port']), timeout=TIMEOUT):
                online = True
        except OSError:
            online = False
        with self.lock:
            # DNS can outlast socket's connect timeout. The scheduler marks it
            # offline at the deadline; a late connection cannot turn it online.
            self._result(entry, online and time.monotonic() - started < TIMEOUT)

    def _worker(self, entry):
        try:
            self.check(entry)
        finally:
            self.slots.release()

    def tick(self):
        """Schedule at most one worker per entry; requests never call check()."""
        now = time.monotonic()
        with self.lock:
            saved = self._saved()
            for entry in saved:
                identifier = entry['id']
                pending = self.pending.get(identifier)
                if pending:
                    thread, started, snapshot = pending
                    if thread.is_alive():
                        if now - started >= TIMEOUT:
                            self._result(snapshot, False)
                        continue
                    del self.pending[identifier]
                if now < self.due.get(identifier, 0):
                    continue
                if not self.slots.acquire(blocking=False):
                    continue
                thread = threading.Thread(target=self._worker, args=(entry,), daemon=True)
                self.pending[identifier] = (thread, now, entry)
                self.due[identifier] = now + INTERVAL
                thread.start()
            # Keep completed removed workers from accumulating bookkeeping.
            ids = {r['id'] for r in saved}
            for identifier in list(self.pending):
                if identifier not in ids and not self.pending[identifier][0].is_alive():
                    del self.pending[identifier]

    def start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
        try:
            self.import_adsb_preferences()
        except Exception:
            logger.warning('Could not copy saved ADS-B receivers; will retry on next start', exc_info=True)
        threading.Thread(target=self._run, name='remote-sdr-health', daemon=True).start()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception:
                # A temporarily unavailable settings DB must not kill the monitor.
                pass
            self.stop_event.wait(1)


monitor = RemoteSDRHealth()
