"""Opt-in streaming receiver supervision, without real SDR hardware."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from utils.sdr import hotplug


def state(path, generation="a", available=True, stamp=None):
    doc = {
        "version": 1,
        "available": available,
        "node": "/dev/bus/usb/001/032" if available else None,
        "generation": generation,
        "updatedAt": time.time() if stamp is None else stamp,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(doc))
    temporary.replace(path)


def wait_for(test, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if test():
            return
        time.sleep(0.02)
    raise AssertionError("condition not reached")


def test_command_is_opt_in_and_only_wraps_local_continuous_sources(monkeypatch):
    cmd = ["rtl_fm", "-d", "0", "-f", "137M", "-"]
    monkeypatch.delenv("INTERCEPT_SDR_HOTPLUG_STATE", raising=False)
    assert hotplug.managed_command(cmd) == cmd
    monkeypatch.setenv("INTERCEPT_SDR_HOTPLUG_STATE", "/run/intercept-sdr/status.json")
    wrapped = hotplug.managed_command(cmd)
    assert wrapped[0] == sys.executable and wrapped[-len(cmd) :] == cmd
    for other in [
        ["rtl_fm", "-d", "rtl_tcp:home:1234", "-"],
        ["rtl_sdr", "-n", "100", "capture.raw"],
        ["rtl_sdr", "-f", "100M", "capture.raw"],
        ["satdump", "pipeline", "baseband"],
        ["dump1090", "--net-only"],
        ["acarsdec", "--soapysdr", "driver=lime"],
        ["rtl_fm", "-d", "1", "-"],
        ["dump1090", "--device-type", "airspy", "--device-index", "0"],
    ]:
        assert hotplug.managed_command(other) == other
    for local in [
        ["dump1090", "--device-index", "0", "--net"],
        ["rtl_433", "-d", "0:biast=1", "-F", "json"],
        ["rtl_tcp", "-d", "0"],
        ["AIS-catcher", "-d:0", "-S", "10110"],
        ["acarsdec", "-r", "0", "131.725"],
        ["dumpvdl2", "--rtlsdr", "0", "136975000"],
        ["rtl_sdr", "-d", "0", "-f", "100000000", "-"],
    ]:
        assert hotplug.managed_command(local) != local


def test_status_rejects_stale_malformed_or_future_state(tmp_path):
    path = tmp_path / "status.json"
    for contents in ["garbled", "{}", "[]"]:
        path.write_text(contents)
        assert not hotplug.read_state(path)["available"]
    state(path, stamp=time.time() - 20)
    assert not hotplug.read_state(path)["available"]
    state(path, stamp=time.time() + 20)
    assert not hotplug.read_state(path)["available"]
    state(path)
    assert hotplug.read_state(path)["available"]


def run_supervisor(tmp_path, command, available=True):
    path = tmp_path / "status.json"
    state(path, available=available)
    process = subprocess.Popen(
        [sys.executable, str(Path(hotplug.__file__)), "--state", str(path), "--", *command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    return process, path


def test_reconnect_keeps_stream_and_reuses_arguments(tmp_path):
    marker = tmp_path / "starts"
    code = "import sys,time; from pathlib import Path; p=Path(sys.argv[1]); p.open('ab').write(b'S'); sys.stdout.buffer.write(b'\\x00\\xffDATA'); sys.stdout.buffer.flush(); time.sleep(30)"
    process, path = run_supervisor(tmp_path, [sys.executable, "-c", code, str(marker)])
    try:
        wait_for(lambda: marker.exists() and marker.read_bytes() == b"S")
        state(path, "b", False)
        time.sleep(0.2)
        assert process.poll() is None
        state(path, "c", True)
        wait_for(lambda: marker.read_bytes() == b"SS")
        process.terminate()
        out, err = process.communicate(timeout=3)
        assert out == b"\x00\xffDATA\x00\xffDATA"
        assert process.returncode == 0
        assert b"waiting" in err.lower()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def test_stop_while_waiting_never_starts_after_return(tmp_path):
    marker = tmp_path / "starts"
    process, path = run_supervisor(
        tmp_path, [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"], available=False
    )
    assert b"waiting" in process.stderr.readline()
    process.terminate()
    process.communicate(timeout=3)
    state(path, "new", True)
    time.sleep(0.15)
    assert not marker.exists()


def test_ordinary_decoder_failure_is_not_an_infinite_restart(tmp_path):
    process, _ = run_supervisor(tmp_path, [sys.executable, "-c", "raise SystemExit(7)"])
    process.communicate(timeout=3)
    assert process.returncode == 7


def test_passive_ami_status_shows_waiting_without_private_device_fields(tmp_path, monkeypatch):
    from utils import ami

    path = tmp_path / "status.json"
    state(path, available=False)
    monkeypatch.setenv(hotplug.STATE_ENV, str(path))
    result = ami.status()
    assert result["data"]["hotplug"] == {"enabled": True, "available": False}
    panel = ami.panel()
    tiles = [t for section in panel["sections"] for t in section.get("tiles", [])]
    assert any(t["label"] == "SDR USB" and t["value"] == "Waiting for receiver" for t in tiles)
    body = json.dumps(result)
    assert "/dev/bus/usb" not in body and "generation" not in body


def test_stop_kills_a_child_which_ignores_sigterm(tmp_path):
    marker = tmp_path / "ready"
    code = f"import signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path({str(marker)!r}).touch(); time.sleep(30)"
    process, _ = run_supervisor(tmp_path, [sys.executable, "-c", code])
    try:
        wait_for(marker.exists)
        process.terminate()
        process.communicate(timeout=3)
        assert process.returncode == 0
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux parent-death signal contract")
def test_worker_death_stops_supervisor_and_receiver(tmp_path):
    marker = tmp_path / "child-pid"
    path = tmp_path / "status.json"
    state(path)
    child_code = (
        f"import os,time; from pathlib import Path; Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)"
    )
    args = [sys.executable, str(Path(hotplug.__file__)), "--state", str(path)]
    launch_code = f"import subprocess,os,time; subprocess.Popen({args!r}+['--parent',str(os.getpid()),'--',{sys.executable!r},'-c',{child_code!r}]); time.sleep(30)"
    launcher = subprocess.Popen(
        [sys.executable, "-c", launch_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    )
    try:
        wait_for(marker.exists)
        child_pid = int(marker.read_text())
        launcher.kill()
        launcher.wait(timeout=2)

        def exited():
            try:
                return Path(f"/proc/{child_pid}/stat").read_text().split()[2] == "Z"
            except FileNotFoundError:
                return True

        wait_for(exited, timeout=3)
    finally:
        try:
            os.killpg(launcher.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        launcher.communicate(timeout=3)


def test_early_usb_exit_waits_for_the_publishers_next_poll(tmp_path):
    marker = tmp_path / "starts"
    code = "import sys,time; from pathlib import Path; Path(sys.argv[1]).open('ab').write(b'S'); time.sleep(.05); raise SystemExit(7)"
    process, path = run_supervisor(tmp_path, [sys.executable, "-c", code, str(marker)])
    try:
        wait_for(marker.exists)
        time.sleep(0.16)
        state(path, "removed", False)
        time.sleep(0.2)
        assert process.poll() is None, "wrapper exited before the publisher could observe USB loss"
        state(path, "returned", True)
        wait_for(lambda: marker.read_bytes() == b"SS")
        process.terminate()
        process.communicate(timeout=3)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def test_startup_delay_covers_managed_exit_grace_only(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setenv(hotplug.STATE_ENV, "/run/intercept-sdr/status.json")
    proc = SimpleNamespace(args=hotplug.managed_command(["rtl_433", "-d", "0"]))
    assert hotplug.startup_delay(proc, 0.3) >= 1
    assert hotplug.startup_delay(SimpleNamespace(args=["rtl_433", "-d", "0"]), 0.3) == 0.3
