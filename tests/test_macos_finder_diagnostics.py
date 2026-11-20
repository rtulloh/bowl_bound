"""Synthetic failed-app evidence; never start a native application."""

import json
from pathlib import Path

import pytest

from scripts import macos_finder_diagnostics as diagnostics


def test_capture_preserves_failure_resources_and_only_bounded_fact_commands(tmp_path: Path) -> None:
    temporary = tmp_path / "temporary"
    work = temporary / "bb-dmg-smoke-synthetic"
    app = work / "installed/Bowl Bound.app"
    app.mkdir(parents=True)
    (app / "synthetic.txt").write_text("public synthetic payload")
    failure = {"passed": False, "retained_app": str(app), "image_sha256": "a" * 64}
    (work / "failure.json").write_text(json.dumps(failure))
    commands = []

    def run(command: tuple[str, ...]) -> dict:
        commands.append(command)
        return {"command": list(command), "returncode": 0, "stdout": "no Terminal process"}

    output = tmp_path / "evidence"
    result = diagnostics.capture(output, temporary, "a" * 40, "b" * 40, run=run)
    assert result["status"] == "diagnostic-only"
    assert result["qualified"] is False
    assert result["source_ref"] == "a" * 40
    assert (
        output / "failure-0/installed/Bowl Bound.app/synthetic.txt"
    ).read_text() == "public synthetic payload"
    assert json.loads((output / "failure-0/failure.json").read_text()) == failure
    assert not any(command[0].endswith(("open", "osascript")) for command in commands)
    assert all("--last" not in command or "5m" in command for command in commands)
    assert (app / "synthetic.txt").exists()


def test_capture_never_follows_foreign_app_path_or_overwrites_evidence(tmp_path: Path) -> None:
    work = tmp_path / "bb-dmg-smoke-foreign"
    work.mkdir()
    (work / "failure.json").write_text(json.dumps({"retained_app": "/Applications/Foreign.app"}))
    with pytest.raises(ValueError, match="retained app"):
        diagnostics.capture(tmp_path / "out", tmp_path, "a" * 40, "b" * 40, run=lambda _: {})
    with pytest.raises(ValueError, match="fresh"):
        diagnostics.capture(tmp_path / "out", tmp_path, "a" * 40, "b" * 40, run=lambda _: {})


def test_command_capture_bounds_timeout_and_records_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    def expired(command: tuple[str, ...], **kwargs: object) -> None:
        assert kwargs["timeout"] == 10
        assert kwargs["capture_output"] is True
        raise subprocess.TimeoutExpired(command, 10)

    monkeypatch.setattr(diagnostics.subprocess, "run", expired)
    result = diagnostics.capture_command(("synthetic-command",))
    assert result["error"] == "TimeoutExpired"
    assert result["qualified"] is False


def test_snapshot_never_uses_automation_even_when_terminal_exists(tmp_path: Path) -> None:
    commands = []

    def run(command: tuple[str, ...]) -> dict:
        commands.append(command)
        return {"stdout": "123\n", "returncode": 0}

    result = diagnostics.capture(tmp_path / "evidence", tmp_path, "a" * 40, "b" * 40, run=run)
    assert result["qualified"] is False
    assert not any(command[0].endswith(("open", "osascript")) for command in commands)


def test_cli_refuses_local_or_nonmac_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(
        diagnostics.sys,
        "argv",
        [
            "diagnose",
            "--output",
            str(tmp_path / "out"),
            "--source-ref",
            "a" * 40,
            "--workflow-ref",
            "b" * 40,
        ],
    )
    with pytest.raises(SystemExit) as raised:
        diagnostics.main()
    assert raised.value.code == 2
    assert not (tmp_path / "out").exists()


def test_capture_separates_logs_targets_terminal_descendants_and_records_screen_failure(
    tmp_path: Path,
) -> None:
    commands = []

    def run(command: tuple[str, ...]) -> dict:
        commands.append(command)
        if command == ("/bin/ps", "-axo", "pid=,ppid=,sess=,tty=,comm="):
            return {
                "returncode": 0,
                "stdout": (
                    "10 1 0 ?? /System/Applications/Utilities/Terminal.app/"
                    "Contents/MacOS/Terminal\n"
                    "11 10 0 ttys000 login\n12 11 0 ttys000 -bash\n"
                    "13 1 0 ?? /Applications/Foreign.app/Contents/MacOS/Foreign\n"
                ),
            }
        return {"returncode": 1, "stdout": "", "stderr": "synthetic denied"}

    result = diagnostics.capture(tmp_path / "out", tmp_path, "a" * 40, "b" * 40, run=run)
    logs = [c for c in commands if c[0] == "/usr/bin/log"]
    assert len(logs) == 2
    assert all("5m" in c for c in logs)
    assert logs[0][-1] == 'process == "Terminal"'
    assert 'process == "lsd"' in logs[1][-1]
    assert 'process == "runningboardd"' in logs[1][-1]
    assert result["terminal_descendant_pids"] == [10, 11, 12]
    assert ("/bin/ps", "-ww", "-p", "10,11,12", "-o", "pid=,ppid=,comm=,args=") in commands
    assert result["screenshot"]["available"] is False
    assert result["screenshot"]["capture"]["stderr"] == "synthetic denied"
    assert result["qualified"] is False


def test_command_capture_retains_initial_output_and_declares_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    output = "startup evidence\n" + "x" * 1_100_000
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, output, ""),
    )
    result = diagnostics.capture_command(("synthetic",))
    assert result["stdout"].startswith("startup evidence\n")
    assert result["stdout_original_chars"] == len(output)
    assert result["stdout_truncated"] is True
    assert result["stdout_retained_range"] == [0, len(result["stdout"])]
    assert len(result["stdout"]) <= 1_048_576


def test_descendant_arguments_never_query_foreign_process_or_unbounded_chain() -> None:
    assert diagnostics.terminal_descendants("17 1 0 ?? /Applications/Foreign.app\n") == []
    lines = ["1 0 0 ?? /System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal"]
    lines.extend(f"{pid} {pid - 1} 0 ?? -bash" for pid in range(2, 67))
    with pytest.raises(ValueError, match="64"):
        diagnostics.terminal_descendants("\n".join(lines))


def test_capture_keeps_both_output_ends_with_explicit_omission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    output = "startup\n" + "x" * 1_100_000 + "\nfinal failure"
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, output, ""),
    )
    result = diagnostics.capture_command(("synthetic",))
    assert result["stdout"].startswith("startup\n")
    assert result["stdout_tail"].endswith("\nfinal failure")
    assert result["stdout_omitted_chars"] == len(output) - len(result["stdout"]) - len(
        result["stdout_tail"]
    )
    assert result["stdout_tail_retained_range"] == [
        len(output) - len(result["stdout_tail"]),
        len(output),
    ]


def test_failure_screen_is_captured_before_slow_inventory(tmp_path: Path) -> None:
    work = tmp_path / "bb-dmg-smoke-order"
    app = work / "installed/Bowl Bound.app"
    app.mkdir(parents=True)
    (work / "failure.json").write_text(json.dumps({"retained_app": str(app)}))
    commands = []

    def run(command: tuple[str, ...]) -> dict:
        commands.append(command)
        return {"returncode": 1, "stdout": "", "stderr": "synthetic denied"}

    result = diagnostics.capture(tmp_path / "out", tmp_path, "a" * 40, "b" * 40, run=run)
    assert next(i for i, c in enumerate(commands) if c[0].endswith("screencapture")) < next(
        i for i, c in enumerate(commands) if c[0].endswith("file")
    )
    assert all("collector_elapsed_seconds" in c for c in result["commands"])
    assert "captured_at_utc" in result["screenshot"]["capture"]


def test_timeout_preserves_partial_byte_output(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    def expired(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            "synthetic", 10, output=b"early fact\xff", stderr=b"failure"
        )

    monkeypatch.setattr(diagnostics.subprocess, "run", expired)
    result = diagnostics.capture_command(("synthetic",))
    assert result["incomplete"] is True
    assert result["timed_out"] is True
    assert result["stdout"] == "early fact\ufffd"
    assert result["stderr"] == "failure"
    assert result["stdout_original_chars"] == 11


def test_mocked_screen_success_pins_actual_saved_bytes(tmp_path: Path) -> None:
    import hashlib

    screen_bytes = b"\x89PNG\r\n\x1a\nsynthetic"

    def run(command: tuple[str, ...]) -> dict:
        if command[0].endswith("screencapture"):
            Path(command[-1]).write_bytes(screen_bytes)
        return {"returncode": 0, "stdout": "", "stderr": ""}

    result = diagnostics.capture(tmp_path / "out", tmp_path, "a" * 40, "b" * 40, run=run)
    assert result["screenshot"]["available"] is True
    assert result["screenshot"]["path"] == "failure-screen.png"
    assert result["screenshot"]["sha256"] == hashlib.sha256(screen_bytes).hexdigest()
