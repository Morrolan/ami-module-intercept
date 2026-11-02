"""Passive mode snapshots. Never call lazy getters, status routes or discovery."""
from __future__ import annotations

import sqlite3
import sys
import time
from contextlib import closing
from datetime import datetime, timezone

from utils.ami import contacts, envelope, iso, process_states
from utils.ami_features import features

# Read only already-loaded modules and existing instances. Some getters construct
# decoders and discover tools, so they are deliberately not used here.
_INSTANCES = {
    'meshtastic': ('utils.meshtastic', '_client', 'is_running'),
    'sstv': ('utils.sstv.sstv_decoder', '_decoder', 'is_running'),
    'sstv-general': ('utils.sstv.sstv_decoder', '_general_decoder', 'is_running'),
    'weathersat': ('utils.weather_sat', '_decoder', 'is_running'),
    'wefax': ('utils.wefax', '_decoder', 'is_running'),
    'gps': ('utils.gps', '_gps_client', 'is_running'),
    'bt-locate': ('utils.bt_locate', '_session', 'active'),
}


def _existing(module, attr):
    return getattr(sys.modules.get(module), attr, None)


def _epoch(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).timestamp()
    if type(value) in (float, int):
        import math
        return value if math.isfinite(value) and value > 0 else None
    return None


def _store_summary(store):
    with store._lock:
        count = len(store.data)
        latest = max((_epoch(t) or 0 for t in store.timestamps.values()), default=0)
    return count, iso(latest) if latest else None


def _message_summary(times, now):
    valid = [t for value in times if (t := _epoch(value)) is not None and t <= now]
    return {'count': sum(now - 3600 <= t for t in valid),
            'countScope': 'retained messages in the last hour',
            'lastMessageAt': iso(max(valid)) if valid else None}


def _meshtastic_summary(now):
    """Aggregate stored messages without creating a database or reading payloads."""
    from utils.database import DB_PATH
    try:
        with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + '?mode=ro', uri=True, timeout=0.2)) as db:
            row = db.execute('SELECT COUNT(CASE WHEN received_at >= ? THEN 1 END), MAX(received_at) '
                             'FROM meshtastic_messages WHERE received_at <= ?', (now-3600, now)).fetchone()
        return {'count': row[0], 'countScope': 'stored messages in the last hour',
                'lastMessageAt': iso(row[1]) if row[1] is not None else None}
    except sqlite3.Error:
        return {}  # Unavailable is not a zero-message observation.


def overview():
    import app as runtime
    now = time.time()
    states = {key.replace('_', '-'): value for key, value in process_states().items()}
    meter = getattr(runtime, 'rtlamr_process', None)
    states['rtlamr'] = 'idle' if meter is None else 'running' if meter.poll() is None else 'stopped'
    states.update({name: 'running' if bool(getattr(_existing(mod, obj), attr, False)) else 'idle'
                   for name, (mod, obj, attr) in _INSTANCES.items()})
    for name, mod, flag in (('adsb', 'routes.adsb', 'adsb_using_service'),
                             ('ais', 'routes.ais', 'ais_running'),
                             ('tscm', 'routes.tscm', '_sweep_running'),
                             ('drone', 'routes.drone', '_drone_running')):
        if _existing(mod, flag):
            states[name] = 'running'
        else:
            states.setdefault(name, 'idle')
    for name, module, attr in (('wifi', 'utils.wifi.scanner', 'wifi_process'),
                                ('bluetooth', 'utils.bluetooth.scanner', 'bt_process')):
        proc = getattr(runtime, attr, None)
        scanner = _existing(module, '_scanner_instance')
        states[name] = 'running' if (proc is not None and proc.poll() is None) or (
            scanner is not None and scanner.is_scanning) else 'idle'
    manager = _existing('utils.subghz', '_manager')
    states['subghz'] = 'running' if manager is not None and manager.active_mode != 'idle' else 'idle'
    client = _existing('utils.meshcore', '_client')
    states['meshcore'] = 'running' if client is not None and client.get_state()[0].value == 'connected' else 'idle'
    shared = _existing('routes.waterfall_websocket', '_shared_state') or {}
    states['waterfall'] = 'running' if shared.get('running') else 'idle'
    flipper = _existing('routes.sensor', 'flipper_receiver')
    if flipper is not None and flipper.snapshot()['running']:
        states['sensor'] = 'running'

    metrics = {}
    for mode, kind in (('adsb', 'aircraft'), ('ais', 'vessels')):
        summary = contacts(kind, 1)['data']
        metrics[mode] = {'count': summary['fresh'], 'countScope': 'fresh contacts within store TTL',
                         **{k: summary[k] for k in ('total', 'fresh', 'stale', 'lastMessageAt')}}
        last = _epoch(_existing(f'routes.{mode}', f'{mode}_last_message_time'))
        if last:
            metrics[mode]['lastMessageAt'] = iso(last)
    for mode, store in (('wifi', runtime.wifi_networks), ('bluetooth', runtime.bt_devices)):
        count, last = _store_summary(store)
        scanner = _existing(f'utils.{mode}.scanner', '_scanner_instance')
        if scanner is not None:
            if mode == 'wifi':
                count = max(count, len(scanner.access_points))
            else:
                count = max(count, scanner.device_count)
        metrics[mode] = {'count': count, 'countScope': 'retained presence entries', 'lastMessageAt': last}
    correlator = _existing('utils.flight_correlator', '_correlator')
    if correlator is not None:
        for mode in ('acars', 'vdl2'):
            messages = list(getattr(correlator, f'_{mode}_messages'))
            metrics[mode] = _message_summary([m.get('_corr_time') for m in messages], now)
    if client is not None:
        with client._lock:
            times = [m.timestamp for m in client._messages]
        metrics['meshcore'] = _message_summary(times, now)
    metrics['meshtastic'] = _meshtastic_summary(now)
    rows = [{'id': f['id'], 'name': f['name'], 'state': states.get(f['id'], 'idle'),
             'monitored': f['id'] in states, 'count': None, 'countScope': None,
             'lastMessageAt': None, **metrics.get(f['id'], {})} for f in features()]
    return envelope(rows, 'Intercept passive runtime snapshot', iso(now))
