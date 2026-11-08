"""Opt-in TCP reachability checks, independent of receiver/decoder state."""
from __future__ import annotations

import ipaddress
import re
import socket
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

from utils.database import get_setting, set_setting
from utils.validation import validate_rtl_tcp_port

SETTING = 'remote_sdr_health'
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
    return {'name': name.strip(), 'host': host, 'port': validate_rtl_tcp_port(port)}


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

    def entries(self):
        with self.lock:
            return [{**r, **self.results.get(r['id'], {
                'state': 'unknown', 'last_seen': None, 'checked_at': None,
            })} for r in self._saved()]

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
        config = {k: entry[k] for k in ('id', 'name', 'host', 'port')}
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
