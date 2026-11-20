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
from collections.abc import Callable
from pathlib import Path
from tempfile import gettempdir


def capture_command(command: tuple[str, ...]) -> dict:
    """Bound each read-only diagnostic command; a capture is not qualification."""
    result: dict = {"command": list(command), "qualified": False}
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, errors="replace", timeout=10, check=False
        )
        result.update(
            returncode=completed.returncode,
            stdout=completed.stdout[-65536:],
            stderr=completed.stderr[-65536:],
        )
    except (OSError, subprocess.SubprocessError) as error:
        result.update(error=type(error).__name__, detail=str(error)[:2000])
    return result


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
                "file_types": run(
                    (
                        "/usr/bin/file",
                        str(app / "Contents/MacOS/launch"),
                        str(app / "Contents/Resources/start.command"),
                        str(app / "Contents/MacOS/BowlBound/start.sh"),
                        str(app / "Contents/MacOS/BowlBound/Bowl-Bound"),
                    )
                ),
                "quarantine_attributes": run(("/usr/bin/xattr", "-lr", str(app))),
            }
        )
    commands = [
        run(("/usr/bin/stat", "-f", "%Su", "/dev/console")),
        run(("/bin/ps", "-axo", "pid=,ppid=,sess=,tty=,comm=")),
        run(("/bin/launchctl", "list")),
        run(
            (
                "/usr/bin/log",
                "show",
                "--last",
                "3m",
                "--style",
                "compact",
                "--predicate",
                'process == "Terminal" OR process == "launchservicesd" '
                'OR process == "syspolicyd" OR process == "tccd" OR process == "amfid"',
            )
        ),
    ]
    result = {
        "status": "diagnostic-only",
        "qualified": False,
        "source_ref": source_ref,
        "workflow_ref": workflow_ref,
        "failures": failures,
        "commands": commands,
        "limits": [
            "No launch substitution, timeout change or native qualification",
            "Original temporary DMG may already be removed; its failure receipt preserves its hash",
            "No AppleScript or Automation request; Terminal window text is not captured",
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
