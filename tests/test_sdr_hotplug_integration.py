"""Real mode routes must wrap final acquisition argv only when opted in."""

from pathlib import Path

import pytest

from tests.fake_process import FakeProcess
from tests.test_mode_lifecycle import _decoders, lifecycle  # noqa: F401


@pytest.mark.parametrize(
    "mode,tool",
    [
        ("sensor", "rtl_433"),
        ("pager", "rtl_fm"),
        ("ais", "AIS-catcher"),
        ("acars", "acarsdec"),
        ("vdl2", "dumpvdl2"),
        ("ook", "rtl_433"),
    ],
)
def test_mode_uses_managed_final_command(client, lifecycle, monkeypatch, mode, tool):  # noqa: F811
    monkeypatch.setenv("INTERCEPT_SDR_HOTPLUG_STATE", "/run/intercept-sdr/status.json")
    spec = lifecycle(mode)
    with _decoders(installed=True):
        response = client.post(spec["start"], json=spec["body"])
        assert response.status_code == 200, response.get_json()
        wrapped = [p.args for p in FakeProcess.instances if isinstance(p.args, list) and "--state" in p.args]
        assert any(Path(command[command.index("--") + 1]).name == tool for command in wrapped)
        client.post(spec["stop"], json={})


def test_timed_scan_stop_during_usb_loss_leaves_no_waiting_receiver(client, lifecycle, monkeypatch):  # noqa: F811
    import subprocess
    import threading

    import routes.listening_post as state
    import routes.listening_post.scanner as scanner

    lifecycle("scanner")
    monkeypatch.setenv("INTERCEPT_SDR_HOTPLUG_STATE", "/run/intercept-sdr/status.json")
    state.scanner_running = True
    state.scanner_paused = False
    with _decoders(installed=True):
        FakeProcess.startup_output = {}

        def source(command, *args, **kwargs):
            proc = FakeProcess(command, *args, **kwargs)
            # USB loss ends a native finite hop; a supervisor retains its pipe.
            if "--state" not in command:
                threading.Timer(0.1, proc.terminate).start()
            return proc

        monkeypatch.setattr(subprocess, "Popen", source)
        worker = threading.Thread(target=scanner.scanner_loop, daemon=True)
        worker.start()
        try:
            from tests.test_mode_lifecycle import _wait_for

            _wait_for(lambda: bool(FakeProcess.instances), "scanner did not start")
            assert client.post("/receiver/scanner/stop", json={}).status_code == 200
            worker.join(timeout=1)
            assert not worker.is_alive(), "Stop left the scanner waiting to restart a receiver"
            assert not any(p.alive for p in FakeProcess.instances)
        finally:
            state.scanner_running = False
            for proc in FakeProcess.instances:
                proc.kill()
            worker.join(timeout=2)
