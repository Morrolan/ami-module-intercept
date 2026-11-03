"""Feed silence must produce durable, privacy-safe AMI transitions."""
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

from utils import ami


def daytime():
    return datetime(2026, 11, 3, 12).timestamp()


@pytest.mark.parametrize('mode,window', [('adsb', 3600), ('ais', 7200), ('acars', 3600), ('vdl2', 3600)])
def test_gap_opens_once_survives_restart_and_data_clears_once(tmp_path, mode, window):
    path = tmp_path / 'events.sqlite'
    journal = ami.EventJournal(path)
    start = daytime()
    states = {mode: 'running'}
    journal.sample_feeds(states, {}, start)
    journal.sample_feeds(states, {}, start + window - 1)
    assert journal.recent() == []
    journal.sample_feeds(states, {}, start + window)
    journal = ami.EventJournal(path)
    journal.sample_feeds(states, {}, start + window + 15)
    events = [e for _, e in journal.recent()]
    assert len(events) == 1
    assert events[0]['dedupeKey'] == f'feed-gap:{mode}'
    assert events[0]['severity'] == 'warning'
    assert events[0]['clears'] is None
    journal.sample_feeds(states, {mode: start + window + 20}, start + window + 21)
    journal.sample_feeds(states, {mode: start + window + 20}, start + window + 30)
    events = [e for _, e in journal.recent()]
    assert len(events) == 2
    assert events[1]['clears'] == f'feed-gap:{mode}'
    assert events[1]['severity'] == 'info'


@pytest.mark.parametrize('state', ['idle', 'stopped'])
def test_inactive_modes_do_not_raise_and_restart_gets_full_window(tmp_path, state):
    journal = ami.EventJournal(tmp_path / 'events.sqlite')
    start = daytime()
    journal.sample_feeds({'acars': state}, {}, start)
    journal.sample_feeds({'acars': state}, {}, start + 8000)
    journal.sample_feeds({'acars': 'running'}, {}, start + 8001)
    journal.sample_feeds({'acars': 'running'}, {}, start + 11600)
    assert journal.recent() == []


def test_adsb_night_suppresses_warning(tmp_path):
    journal = ami.EventJournal(tmp_path / 'events.sqlite')
    start = datetime(2026, 11, 3, 1).timestamp()
    journal.sample_feeds({'adsb': 'running'}, {}, start)
    journal.sample_feeds({'adsb': 'running'}, {}, start + 3600)
    assert journal.recent() == []


def test_data_resets_quiet_window_and_stop_clears_gap(tmp_path):
    journal = ami.EventJournal(tmp_path / 'events.sqlite')
    start = daytime()
    journal.sample_feeds({'acars': 'running'}, {}, start)
    journal.sample_feeds({'acars': 'running'}, {'acars': start + 3500}, start + 3500)
    journal.sample_feeds({'acars': 'running'}, {}, start + 3600)
    assert journal.recent() == []
    journal.sample_feeds({'acars': 'running'}, {}, start + 7100)
    journal.sample_feeds({'acars': 'idle'}, {}, start + 7101)
    assert [e['clears'] for _, e in journal.recent()] == [None, 'feed-gap:acars']


def test_passive_snapshot_includes_service_receivers(monkeypatch):
    monkeypatch.setattr(ami, 'process_states', lambda: {'adsb': 'idle', 'ais': 'idle', 'acars': 'stopped'})
    monkeypatch.setitem(sys.modules, 'routes.adsb', SimpleNamespace(adsb_using_service=True, adsb_last_message_time=123))
    monkeypatch.setitem(sys.modules, 'routes.ais', SimpleNamespace(ais_running=True, ais_last_message_time=456))
    states, times = ami.feed_snapshot()
    assert states == {'adsb': 'running', 'ais': 'running', 'acars': 'stopped'}
    assert times['adsb'] == 123
    assert times['ais'] == 456


def test_stopped_process_is_not_overridden_by_route_flag(monkeypatch):
    monkeypatch.setattr(ami, 'process_states', lambda: {'adsb': 'stopped', 'ais': 'stopped'})
    monkeypatch.setitem(sys.modules, 'routes.adsb', SimpleNamespace(adsb_using_service=True))
    monkeypatch.setitem(sys.modules, 'routes.ais', SimpleNamespace(ais_running=True))
    states, _ = ami.feed_snapshot()
    assert states == {'adsb': 'stopped', 'ais': 'stopped'}


@pytest.mark.parametrize('observed', [None, -1, float('nan'), float('inf'), 'secret payload', True])
def test_invalid_timestamps_do_not_clear_open_gap(tmp_path, observed):
    journal = ami.EventJournal(tmp_path / 'events.sqlite')
    start = daytime()
    journal.sample_feeds({'vdl2': 'running'}, {}, start)
    journal.sample_feeds({'vdl2': 'running'}, {}, start + 3600)
    journal.sample_feeds({'vdl2': 'running'}, {'vdl2': observed}, start + 3610)
    assert len(journal.recent()) == 1


def test_stale_and_future_timestamps_do_not_clear_gap(tmp_path):
    journal = ami.EventJournal(tmp_path / 'events.sqlite')
    start = daytime()
    journal.sample_feeds({'vdl2': 'running'}, {'vdl2': start - 7200}, start)
    journal.sample_feeds({'vdl2': 'running'}, {}, start + 3600)
    journal.sample_feeds({'vdl2': 'running'}, {'vdl2': start - 7200}, start + 3610)
    journal.sample_feeds({'vdl2': 'running'}, {'vdl2': start + 9999}, start + 3620)
    assert len(journal.recent()) == 1


def test_monitor_publishes_feed_gap_in_existing_journal(tmp_path, monkeypatch):
    journal = ami.EventJournal(tmp_path / 'events.sqlite')
    start = daytime()
    journal.sample_feeds({'adsb': 'running'}, {}, start)
    monkeypatch.setattr(ami, '_journal', journal)
    monkeypatch.setattr(ami, 'process_states', lambda: {'adsb': 'running'})
    monkeypatch.setattr(ami, 'feed_snapshot', lambda: ({'adsb': 'running'}, {}))
    monkeypatch.setattr(ami.time, 'time', lambda: start + 4500)

    def end_loop(_):
        raise InterruptedError

    monkeypatch.setattr(ami.time, 'sleep', end_loop)
    with pytest.raises(InterruptedError):
        ami._monitor()
    events = [e for _, e in journal.recent()]
    assert len(events) == 1
    assert events[0]['title'] == 'ADS-B has heard nothing for 75 minutes'
    assert events[0]['dedupeKey'] == 'feed-gap:adsb'
    assert set(events[0]) == {'module', 'kind', 'severity', 'title', 'body', 'eventTime',
                              'observedAt', 'users', 'dedupeKey', 'clears', 'id'}
