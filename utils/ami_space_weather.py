"""Small allowlisted NOAA summary using the SPACE WX page's existing caches."""
from __future__ import annotations

import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from utils.ami import envelope, iso


def _number(value, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        value = float(value)
        if not math.isfinite(value) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            return None
        return value
    except ValueError:
        return None


def _time(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).timestamp()
    except (ValueError, OverflowError):
        return None


def _points(table, columns, minimum=None, maximum=None):
    if not isinstance(table, list) or not table:
        return []
    if isinstance(table[0], list):
        header = table[0]
        if not all(isinstance(h, str) for h in header):
            return []
        rows = [dict(zip(header, row)) for row in table[1:] if isinstance(row, list)]
    else:
        rows = [row for row in table if isinstance(row, dict)]
    points = []
    for row in rows:
        stamp = _time(row.get('time_tag'))
        value = next((_number(row.get(k), minimum, maximum) for k in columns if row.get(k) is not None), None)
        if stamp is not None and value is not None:
            points.append({'time': iso(stamp), 'value': value})
    return sorted(points, key=lambda p: p['time'])


def _notice_time(value):
    match = re.fullmatch(r'(\d{4}) ([A-Za-z]{3}) (\d{1,2}) (\d{2})(\d{2}) UTC', value.strip())
    if not match:
        return None
    try:
        year, month, day, hour, minute = match.groups()
        month_number = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].index(month.lower()) + 1
        return datetime(int(year), month_number, int(day), int(hour), int(minute), tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _alerts(raw, now):
    """Read only a headline and validity lines; never return the notice body."""
    if not isinstance(raw, list):
        return [], [], False
    notices = []
    valid = True
    for notice in raw:
        if not isinstance(notice, dict):
            valid = False
            continue
        stamp = _time(notice.get('issue_datetime'))
        product = notice.get('product_id')
        if stamp is None or not isinstance(product, str) or not product.strip():
            valid = False
            continue
        body = notice.get('message') or notice.get('product_text') or ''
        body = body[:8192] if isinstance(body, str) else ''
        headline = re.search(r'^(?:(?:EXTENDED|CONTINUED) )?(?:CANCEL[^:]*|WARNING|WATCH|ALERT):?[^\r\n]*', body, re.M | re.I)
        title = notice.get('title') or (headline.group() if headline else product)
        if not isinstance(title, str):
            valid = False
            continue
        notices.append((stamp, product, title, body))
    active, recent, seen = [], [], set()
    for stamp, product, title, body in sorted(notices, reverse=True):
        if stamp > now or product in seen:
            continue
        seen.add(product)  # A cancellation supersedes older valid warnings too.
        if re.search(r'\bCANCEL', title, re.I):
            continue
        end = re.search(r'^(?:Now Valid Until|Valid To|Valid Until):[ \t]*([^\r\n]+)', body, re.M | re.I)
        start = re.search(r'^Valid From:[ \t]*([^\r\n]+)', body, re.M | re.I)
        expires = _notice_time(end.group(1)) if end else None
        begins = _notice_time(start.group(1)) if start else None
        if (end and expires is None) or (start and begins is None):
            valid = False
            continue
        if (expires is not None and expires < now) or (begins is not None and begins > now):
            continue
        row = {'title': ' '.join(title.split())[:160], 'issuedAt': iso(stamp)}
        (active if expires is not None else recent).append(row)
    return active, recent, valid


def space_weather():
    from routes import space_weather as sw
    now = time.time()
    sources = {
        'kp': ('kp_index', sw._fetch_kp_index, sw.TTL_REALTIME),
        'kpForecast': ('kp_forecast', sw._fetch_kp_forecast, sw.TTL_FORECAST),
        'scales': ('scales', sw._fetch_scales, sw.TTL_REALTIME),
        'flux': ('flux', sw._fetch_flux, sw.TTL_DAILY),
        'alerts': ('alerts', sw._fetch_alerts, sw.TTL_REALTIME),
        'speed': ('sw_plasma', sw._fetch_solar_wind_plasma, sw.TTL_REALTIME),
        'bz': ('sw_mag', sw._fetch_solar_wind_mag, sw.TTL_REALTIME),
    }

    def read(item):
        key, fetch, ttl = item
        try:
            raw = fetch()  # Same fetcher/URL/TTL as the page, no independent cache.
        except Exception:
            raw = None
        cached = dict(sw._cache.get(key) or {})
        failed = raw is None
        if failed:
            raw = cached.get('data')  # A failed refresh may still have an older snapshot.
        fetched = cached.get('fetchedAt', cached.get('expires', now) - ttl)
        return raw, fetched if cached else None, failed or cached.get('expires', 0) <= now

    # Existing fetchers can each wait 15s. Parallel reads fit the tool's 20s
    # budget without introducing new HTTP helpers or changing cache TTLs.
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        snapshots = dict(zip(sources, executor.map(read, sources.values())))
    raw = {key: value[0] for key, value in snapshots.items()}
    kp = [p for p in _points(raw['kp'], ('Kp', 'kp'), 0, 9) if _time(p['time']) <= now]
    forecast = [p for p in _points(raw['kpForecast'], ('kp', 'Kp'), 0, 9)
                if now < _time(p['time']) <= now + 72*3600]
    flux = [p for p in _points(raw['flux'], ('flux',), 0) if _time(p['time']) <= now]
    speed = [p for p in _points(raw['speed'], ('proton_speed', 'speed'), 0) if _time(p['time']) <= now]
    bz = [p for p in _points(raw['bz'], ('bz_gsm',)) if _time(p['time']) <= now]
    current = raw['scales'].get('0', {}) if isinstance(raw['scales'], dict) else {}
    if not isinstance(current, dict):
        current = {}
    scales = {key: _number(current.get(key, {}).get('Scale'), 0, 5)
              if isinstance(current.get(key), dict) else None for key in ('R', 'S', 'G')}
    alerts, recent_alerts, alerts_valid = _alerts(raw['alerts'], now)
    scales_time = _time(f"{current.get('DateStamp', '')}T{current.get('TimeStamp', '')}")
    values = {'kp': kp[-1] if kp else None, 'kpForecast': forecast, 'scales': scales,
              'flux': flux[-1] if flux else None, 'alerts': alerts[:50],
              'speed': speed[-1] if speed else None, 'bz': bz[-1] if bz else None}
    available = {key: bool(value) for key, value in values.items()}
    available['alerts'] = alerts_valid
    available['scales'] = all(v is not None for v in scales.values())
    missing = [key for key in sources if not available[key]]
    stale_fields = [key for key in sources if snapshots[key][2] or not available[key]]
    # A newly fetched but frozen feed is still an old observation. Product
    # cadences differ: Kp is three-hourly, flux daily, wind one-minute.
    for key, max_age in (('kp', 6*3600), ('flux', 72*3600), ('speed', 20*60), ('bz', 20*60)):
        point = values[key]
        if point and now - _time(point['time']) > max_age and key not in stale_fields:
            stale_fields.append(key)
    if (scales_time is None or not 0 <= now - scales_time <= 20*60) and 'scales' not in stale_fields:
        stale_fields.append('scales')
    times = [stamp for _, stamp, _ in snapshots.values() if stamp is not None]
    data = {'kp': values['kp'], 'kpForecast': forecast, 'scales': scales, 'flux': values['flux'],
            'alerts': values['alerts'], 'recentAlerts': recent_alerts[:50],
            'alertsScope': 'alerts have explicit current validity; recentAlerts lack a validity end. Cancelled, expired and superseded notices are excluded.',
            'scalesAsOf': iso(scales_time) if scales_time is not None else None,
            'solarWind': {'speed': values['speed'], 'speedUnit': 'km/s', 'bz': values['bz'], 'bzUnit': 'nT'},
            'fluxUnit': 'sfu', 'missing': missing, 'staleFields': stale_fields}
    return envelope(data, 'NOAA SWPC', iso(min(times)) if times else None, bool(stale_fields))
