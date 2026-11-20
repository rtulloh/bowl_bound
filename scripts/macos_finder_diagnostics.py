"""Retain failed hosted macOS launch facts; never substitute a successful launch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir


def _retained_output(label: str, value: str | bytes | None, limit: int) -> dict:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    value = value or ""
    truncated = len(value) > limit
    head = value[: limit // 2] if truncated else value
    tail = value[-limit // 2 :] if truncated else ""
    return {
        label: head,
        f"{label}_tail": tail,
        f"{label}_original_chars": len(value),
        f"{label}_truncated": truncated,
        f"{label}_retained_range": [0, len(head)],
        f"{label}_tail_retained_range": [len(value) - len(tail), len(value)],
        f"{label}_omitted_chars": len(value) - len(head) - len(tail),
    }


def capture_command(command: tuple[str, ...]) -> dict:
    """Bound each read-only command and preserve incomplete timeout evidence."""
    result: dict = {
        "command": list(command),
        "qualified": False,
        "incomplete": True,
        "timed_out": False,
    }
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, errors="replace", timeout=10, check=False
        )
        result.update(returncode=completed.returncode, incomplete=False)
        result.update(_retained_output("stdout", completed.stdout, 1_048_576))
        result.update(_retained_output("stderr", completed.stderr, 65536))
    except subprocess.TimeoutExpired as error:
        result.update(error=type(error).__name__, detail=str(error)[:2000], timed_out=True)
        result.update(_retained_output("stdout", error.stdout, 1_048_576))
        result.update(_retained_output("stderr", error.stderr, 65536))
    except (OSError, subprocess.SubprocessError) as error:
        result.update(error=type(error).__name__, detail=str(error)[:2000])
    return result


def terminal_descendants(snapshot: str) -> list[int]:
    """Select only exact Terminal roots and their observed child processes."""
    processes = {}
    roots = set()
    for line in snapshot.splitlines():
        parts = line.split(maxsplit=4)
        if len(parts) != 5 or not parts[0].isdecimal() or not parts[1].isdecimal():
            continue
        pid, parent = int(parts[0]), int(parts[1])
        processes[pid] = parent
        if parts[4] == "/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal":
            roots.add(pid)
    selected = roots.copy()
    while True:
        children = {pid for pid, parent in processes.items() if parent in selected}
        expanded = selected | children
        if len(expanded) > 64:
            raise ValueError("Refusing an unexpectedly large Terminal chain (>64 processes)")
        if expanded == selected:
            return sorted(selected)
        selected = expanded


def capture(
    output: Path,
    temporary: Path,
    source_ref: str,
    workflow_ref: str,
    *,
    run: Callable[[tuple[str, ...]], dict] = capture_command,
) -> dict:
    """Copy failed app evidence and read native state without starting any app."""
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a fresh diagnostic evidence directory")
    output.mkdir(parents=True)
    started = time.monotonic()
    entered_at = datetime.now(timezone.utc).isoformat()

    def observed(command: tuple[str, ...]) -> dict:
        before = time.monotonic()
        captured_at = datetime.now(timezone.utc).isoformat()
        result = run(command)
        return {
            **result,
            "captured_at_utc": captured_at,
            "collector_elapsed_seconds": round(before - started, 3),
            "command_elapsed_seconds": round(time.monotonic() - before, 3),
        }

    snapshot = observed(("/bin/ps", "-axo", "pid=,ppid=,sess=,tty=,comm="))
    pids = terminal_descendants(snapshot.get("stdout", ""))
    commands = [snapshot]
    if pids:
        commands.append(
            observed(
                (
                    "/bin/ps",
                    "-ww",
                    "-p",
                    ",".join(str(pid) for pid in pids),
                    "-o",
                    "pid=,ppid=,comm=,args=",
                )
            )
        )
    screen = output / "failure-screen.png"
    screen_capture = observed(("/usr/sbin/screencapture", "-x", str(screen)))
    screen_available = screen_capture.get("returncode") == 0 and screen.is_file()
    screenshot = {
        "capture": screen_capture,
        "available": screen_available,
        "path": screen.name,
        "sha256": hashlib.sha256(screen.read_bytes()).hexdigest() if screen_available else None,
    }
    failures = []
    for index, work in enumerate(sorted(temporary.glob("bb-dmg-smoke-*"))):
        failure = work / "failure.json"
        if not failure.is_file() or failure.is_symlink():
            continue
        data = json.loads(failure.read_text(encoding="utf-8"))
        app = Path(data["retained_app"])
        if app.is_symlink() or not app.resolve().is_relative_to(work.resolve()):
            raise ValueError("Foreign retained app path in failed smoke evidence")
        if any(path.is_symlink() for path in app.rglob("*")):
            raise ValueError("Symlink in retained app evidence")
        destination = output / f"failure-{index}"
        destination.mkdir()
        shutil.copy2(failure, destination / "failure.json")
        if app.is_dir():
            shutil.copytree(app, destination / "installed/Bowl Bound.app")
        files = {
            str(path.relative_to(app)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(app.rglob("*"))
            if path.is_file()
        }
        failures.append(
            {
                "failure": data,
                "retained_app_sha256": files,
                "retained_app_modes": {
                    str(path.relative_to(app)): oct(stat.S_IMODE(path.stat().st_mode))
                    for path in sorted(app.rglob("*"))
                },
                "retained_app_sizes": {
                    str(path.relative_to(app)): path.stat().st_size
                    for path in sorted(app.rglob("*"))
                    if path.is_file()
                },
                "file_types": observed(
                    (
                        "/usr/bin/file",
                        str(app / "Contents/MacOS/launch"),
                        str(app / "Contents/Resources/start.command"),
                        str(app / "Contents/Resources/BowlBound/start.sh"),
                        str(app / "Contents/Resources/BowlBound/Bowl-Bound"),
                    )
                ),
                "quarantine_attributes": observed(("/usr/bin/xattr", "-lr", str(app))),
            }
        )
    commands.extend(
        [
            observed(("/usr/bin/stat", "-f", "%Su", "/dev/console")),
            observed(("/bin/launchctl", "list")),
        ]
    )
    captured_at = datetime.now(timezone.utc).isoformat()
    for predicate in (
        'process == "Terminal"',
        'process == "lsd" OR process == "runningboardd" '
        'OR subsystem BEGINSWITH "com.apple.launchservices"',
    ):
        commands.append(
            observed(
                (
                    "/usr/bin/log",
                    "show",
                    "--last",
                    "5m",
                    "--style",
                    "compact",
                    "--predicate",
                    predicate,
                )
            )
        )
    result = {
        "status": "diagnostic-only",
        "collector_entered_utc": entered_at,
        "qualified": False,
        "source_ref": source_ref,
        "workflow_ref": workflow_ref,
        "failures": failures,
        "commands": commands,
        "terminal_descendant_pids": pids,
        "screenshot": screenshot,
        "log_requested_window": "5 minutes before each query; UTC capture timestamp below",
        "log_capture_started_utc": captured_at,
        "limits": [
            "No launch substitution, timeout change or native qualification",
            "Original temporary DMG may already be removed; its failure receipt preserves its hash",
            "No Automation request; screenshot denial does not change permissions",
            "Logs retain both ends within 1 MiB; explicit ranges and counts flag omissions",
            "Arguments target observed Terminal descendants, which may exit before capture",
        ],
    }
    (output / "diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--workflow-ref", required=True)
    args = parser.parse_args()
    if sys.platform != "darwin" or os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("This read-only diagnostic is restricted to hosted macOS Actions")
    capture(args.output, Path(gettempdir()), args.source_ref, args.workflow_ref)
    print("Failed Finder evidence captured; artifacts remain unqualified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
