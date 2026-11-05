"""Teesside's public board is parsed defensively and fetched at a bounded rate."""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from utils import teesside_board as board

HTML = '''<table class="flights flights--departures"><tr><th>Flight No.</th></tr>
<tr class="date_row"><td colspan="5">Thursday 5th November</td></tr>
<tr><td>KL966</td><td>Amsterdam</td><td>17:25</td><td>On Time</td><td>-</td></tr></table>
<table class="flights flights--arrivals"><tr class="date_row"><td>Thursday 5th November</td></tr>
<tr><td>FR3374</td><td>M&aacute;laga</td><td>19:00</td><td>Delayed</td><td>Expected 19:20</td></tr></table>'''
NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def test_board_date_direction_status_and_entities():
    data = board.parse_board(HTML, NOW)
    assert data['departures'][0] == {'date': '2026-11-05', 'flight': 'KL966',
        'place': 'Amsterdam', 'scheduled': '17:25', 'scheduled_at': '2026-11-05T17:25:00+00:00',
        'status': 'On Time', 'remarks': '-'}
    assert data['arrivals'][0]['place'] == 'Málaga'
    assert data['arrivals'][0]['remarks'] == 'Expected 19:20'


def test_year_rollover_and_missing_tables():
    html = HTML.replace('Thursday 5th November', 'Friday 1st January')
    assert board.parse_board(html, datetime(2026, 12, 31, tzinfo=timezone.utc))['arrivals'][0]['date'] == '2027-01-01'
    with pytest.raises(ValueError):
        board.parse_board('<html>Maintenance page</html>', NOW)
    with pytest.raises(ValueError):
        board.parse_board(HTML.replace('flights--arrivals', 'other'), NOW)


def test_published_estimate_drives_countdown_including_midnight():
    assert board.parse_board(HTML, NOW)['arrivals'][0]['expected_at'] == '2026-11-05T19:20:00+00:00'
    overnight = HTML.replace('19:00', '23:50').replace('Expected 19:20', 'Expected 00:10')
    assert board.parse_board(overnight, NOW)['arrivals'][0]['expected_at'] == '2026-11-06T00:10:00+00:00'
    summer = HTML.replace('Thursday 5th November', 'Sunday 5th July')
    result = board.parse_board(summer, datetime(2026, 7, 5, tzinfo=timezone.utc))['arrivals'][0]
    assert result['scheduled_at'].endswith('+01:00') and result['expected_at'].endswith('+01:00')
    clock_change = overnight.replace('Thursday 5th November', 'Saturday 24th October').replace('Expected 00:10', 'Expected 03:10')
    result = board.parse_board(clock_change, datetime(2026, 10, 24, tzinfo=timezone.utc))['arrivals'][0]
    assert result['expected_at'] == '2026-10-25T03:10:00+00:00'


def test_bad_rows_do_not_become_flights():
    html = HTML.replace('17:25', 'nonsense').replace('Thursday 5th November', 'bad date')
    with pytest.raises(ValueError):
        board.parse_board(html, NOW)


def response(html=HTML):
    result = Mock(status_code=200, encoding='utf-8')
    result.iter_content.return_value = [html.encode()]
    return result


def test_cache_stale_on_error_and_retry_backoff(monkeypatch):
    cache = board.FlightBoardCache()
    clock = [0]
    monkeypatch.setattr(board.time, 'monotonic', lambda: clock[0])
    fetch = Mock(return_value=response())
    monkeypatch.setattr(board.requests, 'get', fetch)
    first = cache.get(now=NOW)
    assert not first['stale'] and first['available']
    assert cache.get(now=NOW)['fetched_at'] == first['fetched_at']
    assert fetch.call_count == 1
    clock[0] = 301
    fetch.side_effect = TimeoutError('offline')
    stale = cache.get(now=NOW)
    assert stale['stale'] and stale['arrivals'] == first['arrivals']
    assert stale['error'] and fetch.call_count == 2
    clock[0] = 302
    assert cache.get(now=NOW)['stale']
    assert fetch.call_count == 2
    clock[0] = 362
    fetch.side_effect = None
    assert not cache.get(now=NOW)['stale']
    assert fetch.call_count == 3


def test_failed_first_fetch_and_size_bound(monkeypatch):
    monkeypatch.setattr(board.requests, 'get', Mock(side_effect=TimeoutError('secret network detail')))
    missing = board.FlightBoardCache().get(now=NOW)
    assert not missing['available'] and missing['error']
    assert 'secret' not in missing['error']
    huge = response()
    huge.iter_content.return_value = [b'x' * (board.MAX_BYTES + 1)]
    monkeypatch.setattr(board.requests, 'get', Mock(return_value=huge))
    assert not board.FlightBoardCache().get(now=NOW)['available']
    assert huge.close.called


def test_teesside_endpoint_and_auth(client, anon_client, monkeypatch):
    monkeypatch.setattr(board.flight_board, 'get', lambda: {'available': True, 'arrivals': [], 'departures': []})
    assert client.get('/adsb/teesside').json['available']
    assert anon_client.get('/adsb/teesside').status_code in (302, 401)
