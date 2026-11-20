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
    assert all("--last" not in command or "3m" in command for command in commands)
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
