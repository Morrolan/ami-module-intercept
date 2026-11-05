"""Small, cached reader for Teesside's public passenger-flight board."""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import requests

SOURCE_URL = 'https://www.teessideinternational.com/arrivals-departures/'
MAX_BYTES = 1024 * 1024
CACHE_SECONDS = 300
RETRY_SECONDS = 60
LOCAL_TIMEZONE = ZoneInfo('Europe/London')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


def _expected(scheduled, status, remarks):
    match = re.search(r'\b(?:expected|estimated|due)(?:\s+at)?\s+((?:\d{4}-\d{2}-\d{2}T)?\d{2}:\d{2}(?::\d{2})?)',
                      status + ' ' + remarks, re.IGNORECASE)
    if not match:
        return None
    try:
        base = datetime.fromisoformat(scheduled).astimezone(LOCAL_TIMEZONE)
        value = match[1]
        if 'T' in value:
            estimate = datetime.fromisoformat(value).replace(tzinfo=LOCAL_TIMEZONE)
        else:
            hour, minute = map(int, value.split(':')[:2])
            estimate = base.replace(hour=hour, minute=minute)
            if estimate - base < timedelta(hours=-12):
                estimate += timedelta(days=1)
        return estimate.isoformat() if abs(estimate - base) <= timedelta(days=2) else None
    except ValueError:
        return None


def _date(text, reference):
    match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(MONTHS) + r')\b', text)
    if not match:
        return None
    day, month = int(match[1]), MONTHS.index(match[2]) + 1
    candidates = []
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(reference.replace(year=year, month=month, day=day))
        except ValueError:
            pass
    if not candidates:
        return None
    nearest = min(candidates, key=lambda value: abs((value - reference).days))
    return nearest.isoformat() if -2 <= (nearest - reference).days <= 14 else None


class _BoardParser(HTMLParser):
    def __init__(self, now):
        super().__init__(convert_charrefs=True)
        self.reference = now.astimezone(LOCAL_TIMEZONE).date()
        self.tables = []
        self.seen = set()
        self.rows = {'arrivals': [], 'departures': []}
        self.day = None
        self.cells = None
        self.text = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            classes = dict(attrs).get('class', '').split()
            direction = next((value for value in self.rows if 'flights--' + value in classes), None)
            self.tables.append(direction)
            if direction:
                self.seen.add(direction)
                self.day = None
        if not self.tables or not self.tables[-1]:
            return
        if tag == 'tr':
            self.cells = []
        if tag == 'td' and self.cells is not None:
            self.text = []

    def handle_data(self, data):
        if self.text is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'td' and self.text is not None:
            if self.cells is not None:
                self.cells.append(' '.join(' '.join(self.text).split())[:500])
            self.text = None
        if tag == 'tr' and self.cells is not None and self.tables and self.tables[-1]:
            if len(self.cells) == 1:
                self.day = _date(self.cells[0], self.reference)
            elif len(self.cells) >= 4 and self.day:
                flight, place, scheduled, status = self.cells[:4]
                if re.fullmatch(r'[A-Z0-9]{2,12}', flight) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', scheduled):
                    row = {
                        'date': self.day, 'flight': flight, 'place': place,
                        'scheduled': scheduled, 'status': status,
                        'scheduled_at': datetime.fromisoformat(self.day + 'T' + scheduled).replace(tzinfo=LOCAL_TIMEZONE).isoformat(),
                        'remarks': self.cells[4] if len(self.cells) > 4 else '',
                    }
                    estimate = _expected(row['scheduled_at'], row['status'], row['remarks'])
                    if estimate:
                        row['expected_at'] = estimate
                    self.rows[self.tables[-1]].append(row)
                    if sum(map(len, self.rows.values())) > 300:
                        raise ValueError('Unexpected flight-board size')
            self.cells = None
        if tag == 'table' and self.tables:
            self.tables.pop()


def parse_board(html, now):
    parser = _BoardParser(now)
    parser.feed(html)
    if parser.seen != {'arrivals', 'departures'} or not any(parser.rows.values()):
        raise ValueError('No usable Teesside flight tables')
    return parser.rows


class FlightBoardCache:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = None
        self.fetched_at = None
        self.next_refresh = 0
        self.error = None

    def get(self, now=None):
        now = now or datetime.now(timezone.utc)
        with self.lock:
            if time.monotonic() >= self.next_refresh:
                response = None
                try:
                    response = requests.get(SOURCE_URL, timeout=(3, 8), stream=True,
                                            allow_redirects=False,
                                            headers={'User-Agent': 'Intercept airport board (personal dashboard)'})
                    if response.status_code != 200:
                        raise ValueError('Upstream flight board unavailable')
                    chunks, size = [], 0
                    for chunk in response.iter_content(chunk_size=8192):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ValueError('Flight board exceeds size limit')
                        chunks.append(chunk)
                    data = parse_board(b''.join(chunks).decode('utf-8', errors='replace'), now)
                    self.data = data
                    self.fetched_at = now.isoformat()
                    self.error = None
                    self.next_refresh = time.monotonic() + CACHE_SECONDS
                except Exception:
                    self.error = 'The airport flight board is temporarily unavailable. Please try again later.'
                    self.next_refresh = time.monotonic() + RETRY_SECONDS
                finally:
                    if response is not None:
                        response.close()
            return {
                'airport': 'Teesside International', 'iata': 'MME', 'icao': 'EGNV',
                'source_url': SOURCE_URL, 'timezone': 'Europe/London',
                'available': self.data is not None, 'stale': self.error is not None and self.data is not None,
                'fetched_at': self.fetched_at, 'error': self.error,
                **(self.data or {'arrivals': [], 'departures': []}),
            }


flight_board = FlightBoardCache()
