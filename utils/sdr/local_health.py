"""Health of the local RTL-SDR, from the host watcher's heartbeat only.

The host watcher matches the receiver by its exact VID, PID and serial and
publishes whether it is present. This never probes or opens the radio, and it
exposes no serial, USB path or generation.

States:
  online        the watcher sees the receiver
  missing       the watcher is running and the receiver is not there
  not_reporting no fresh heartbeat, so its state is unknown
  not_set_up    INTERCEPT_SDR_HOTPLUG_STATE is not configured
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone

from utils.sdr import hotplug

# With the watcher set up, the container sees only the watched receiver, and
# supervision only covers RTL-SDR index 0 (see hotplug._continuous_rtl).
WATCHED_INDEX = 0


def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat() if epoch is not None else None


class LocalSdrHealth:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_seen = None
        self.missing_since = None

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        path = os.environ.get(hotplug.STATE_ENV)
        if not path:
            return {"enabled": False, "state": "not_set_up", "last_seen": None, "missing_since": None}
        heartbeat = hotplug.read_state(path)
        with self.lock:
            if not heartbeat["reporting"]:
                state = "not_reporting"
            elif heartbeat["available"]:
                state = "online"
                self.last_seen = now
                self.missing_since = None
            else:
                state = "missing"
                if self.missing_since is None:
                    self.missing_since = now
            return {"enabled": True, "state": state, "last_seen": _iso(self.last_seen),
                    "missing_since": _iso(self.missing_since) if state == "missing" else None}


health = LocalSdrHealth()
