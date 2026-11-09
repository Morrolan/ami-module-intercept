"""Opt-in local RTL streaming supervision; no device discovery or decoder control API."""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import re
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

STATE_ENV = "INTERCEPT_SDR_HOTPLUG_STATE"
MAX_STATE_AGE = 3.0


def read_state(path):
    """Only the small, root-published heartbeat; never probe a receiver."""
    # reporting: the watcher's heartbeat is present and fresh (else we cannot tell).
    absent = {"available": False, "generation": None, "reporting": False}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "r") as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o022
                or info.st_size > 4096
                or info.st_uid not in (0, os.geteuid())
            ):
                return absent
            data = json.loads(source.read(4097))
        if not isinstance(data, dict) or data.get("version") != 1:
            return absent
        stamp = data.get("updatedAt")
        generation = data.get("generation")
        if (
            type(stamp) not in (int, float)
            or not math.isfinite(stamp)
            or not -2 <= time.time() - stamp <= MAX_STATE_AGE
        ):
            return absent
        if not isinstance(generation, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", generation):
            return absent
        if type(data.get("available")) is not bool:
            return absent
        if data["available"] and not re.fullmatch(r"/dev/bus/usb/001/[0-9]{3}", str(data.get("node", ""))):
            return absent
        return {"available": data["available"], "generation": generation, "reporting": True}
    except (OSError, ValueError, TypeError):
        return absent


def status():
    """Sanitized passive availability; no identity, path, generation or probing."""
    path = os.environ.get(STATE_ENV)
    return {"enabled": bool(path), "available": read_state(path)["available"] if path else None}


def _arg(command, flag, default=None):
    try:
        return command[command.index(flag) + 1]
    except (ValueError, IndexError):
        return default


def _continuous_rtl(command):
    if not command or not all(isinstance(arg, str) for arg in command):
        return False
    name = Path(command[0]).name
    if any("rtl_tcp:" in arg for arg in command) or "--soapysdr" in command:
        return False
    if name in ("rtl_fm", "rtl_433", "rtl_tcp", "rtl_sdr"):
        device = _arg(command, "-d", "0").split(":", 1)[0]
        if device != "0":
            return False
        if name == "rtl_sdr":
            return command[-1] == "-" and "-n" not in command
        if name == "rtl_fm":
            return command[-1] == "-"
        if name == "rtl_433":
            return not any(flag in command for flag in ("-r", "-T", "-w", "-W"))
        return True
    if name in ("dump1090", "dump1090-fa", "readsb"):
        return (
            _arg(command, "--device-index", "0") == "0"
            and _arg(command, "--device-type", "rtlsdr") in ("rtlsdr", "rtl-sdr")
            and not any(flag in command for flag in ("--net-only", "--ifile"))
        )
    if name == "AIS-catcher":
        return "-d:0" in command and "-r" not in command
    if name == "acarsdec":
        return _arg(command, "--rtlsdr", _arg(command, "-r")) == "0"
    if name == "dumpvdl2":
        return _arg(command, "--rtlsdr") == "0"
    return False


def managed_command(command):
    """Wrap only known continuous local RTL commands, after all argv edits."""
    state = os.environ.get(STATE_ENV)
    if not state or not _continuous_rtl(command):
        return command
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--state",
        state,
        "--parent",
        str(os.getpid()),
        "--",
        *command,
    ]


def startup_delay(process, seconds):
    """Readiness checks must outlast the supervised USB-state grace period."""
    args = getattr(process, "args", None)
    wrapped = isinstance(args, (list, tuple)) and len(args) > 1 and args[1] == str(Path(__file__).resolve())
    return max(seconds, 1.1) if wrapped else seconds


def _parent_death(sig, expected_parent):
    if sys.platform == "linux":
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, sig, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "Unable to arm parent-death cleanup")
    return os.getppid() == expected_parent


def supervise(command, state_path, parent):
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    if not _parent_death(signal.SIGTERM, parent):
        return 0
    child = None
    generation = None
    waiting = False

    def halt():
        nonlocal child
        if child is None:
            return True
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=0.4)
            except subprocess.TimeoutExpired:
                child.kill()
                try:
                    child.wait(timeout=0.4)
                except subprocess.TimeoutExpired:
                    return False
        child = None
        return True

    try:
        while not stopping and os.getppid() == parent:
            current = read_state(state_path)
            if not current["available"]:
                if not halt():
                    return 1
                if not waiting:
                    print("[SDR hotplug] Receiver unavailable; waiting for its return.", file=sys.stderr, flush=True)
                    waiting = True
            elif child is not None and current["generation"] != generation:
                if not halt():
                    return 1
            elif child is not None and child.poll() is not None:
                code = child.returncode
                # A running tool can exit slightly before the host watcher sees
                # the removal. Only a USB state/generation change permits retry.
                deadline = time.monotonic() + 0.75
                while not stopping and time.monotonic() < deadline:
                    latest = read_state(state_path)
                    if not latest["available"] or latest["generation"] != generation:
                        break
                    time.sleep(0.025)
                else:
                    return 0 if stopping or os.getppid() != parent else code if code >= 0 else 128 - code
                child = None
            elif child is None:
                if waiting:
                    print("[SDR hotplug] Receiver returned; resuming reception.", file=sys.stderr, flush=True)
                waiting = False
                generation = current["generation"]
                expected = os.getpid()

                def child_setup():
                    if not _parent_death(signal.SIGKILL, expected):
                        os._exit(1)

                child = subprocess.Popen(command, preexec_fn=child_setup if sys.platform == "linux" else None)
            time.sleep(0.05)
        return 0
    finally:
        halt()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--parent", type=int, default=os.getppid())
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Command is required")
    try:
        return supervise(command, args.state, args.parent)
    except OSError as error:
        print(f"[SDR hotplug] Cannot run receiver: {error.strerror}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
