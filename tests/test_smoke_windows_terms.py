"""Synthetic dialog facts; no native window or process is launched."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import smoke_windows_terms as smoke


def dialog(**changes: object) -> smoke.Dialog:
    baseline = smoke.Dialog(
        handle=10,
        pid=123,
        text="Synthetic terms" + smoke.PROMPT,
        yes=11,
        no=12,
        default_id=7,
        within_work_area=True,
        text_fits=True,
    )
    return replace(baseline, **changes)


def test_dialog_requires_full_terms_owned_pid_default_no_and_readable_geometry() -> None:
    assert smoke.validate_dialog(dialog(), {123}, "Synthetic terms") == 10


@pytest.mark.parametrize(
    "changes",
    [
        {"pid": 999},
        {"text": "truncated"},
        {"default_id": 6},
        {"yes": 0},
        {"no": 0},
        {"within_work_area": False},
        {"text_fits": False},
    ],
)
def test_foreign_truncated_or_unreadable_dialog_is_rejected(changes: dict) -> None:
    with pytest.raises(RuntimeError):
        smoke.validate_dialog(dialog(**changes), {123}, "Synthetic terms")


def test_owned_pid_closure_ignores_unrelated_processes_and_cycles() -> None:
    assert smoke.owned_pids(123, {123: 1, 124: 123, 125: 124, 9: 8, 8: 9, 999: 1}) == {
        123,
        124,
        125,
    }


def test_terms_hash_and_duplicate_bytes_are_required(tmp_path: Path) -> None:
    text = b"Synthetic terms"
    for name in ["WINDOWS-RUNTIME-TERMS.txt", "_internal/WINDOWS-RUNTIME-TERMS.txt"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text)
    digest = hashlib.sha256(text).hexdigest()
    assert smoke.read_terms(tmp_path / "BowlBound.exe", digest) == text.decode()
    (tmp_path / "_internal/WINDOWS-RUNTIME-TERMS.txt").write_text("Changed")
    with pytest.raises(ValueError):
        smoke.read_terms(tmp_path / "BowlBound.exe", digest)


def test_off_windows_is_explicitly_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(smoke, "is_windows", lambda: False)
    with pytest.raises(RuntimeError, match="Windows"):
        smoke.smoke_windows_terms(tmp_path / "app.exe", "1.1.1", tmp_path, "a" * 64)


def test_click_rechecks_pid_before_posting() -> None:
    api = Mock()
    api.window_pid.return_value = 999
    with pytest.raises(RuntimeError, match="ownership"):
        smoke.click_choice(api, dialog(), {123}, 7, Path("app.exe"))
    api.post.assert_not_called()
    api.window_pid.return_value = 123
    api.image_matches.return_value = True
    smoke.click_choice(api, dialog(), {123}, 7, Path("app.exe"))
    api.post.assert_called_once_with(10, 0x111, 7, 12)


def test_rectangle_containment_requires_positive_fully_visible_dimensions() -> None:
    assert smoke.contained((1, 2, 10, 20), (0, 0, 100, 100))
    assert not smoke.contained((-1, 2, 10, 20), (0, 0, 100, 100))
    assert not smoke.contained((1, 2, 1, 20), (0, 0, 100, 100))


@pytest.mark.parametrize("bad_dialog", [False, True])
def test_native_smoke_orchestration_is_isolated_and_cleans_only_owned_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_dialog: bool
) -> None:
    import json
    from types import SimpleNamespace

    processes = []
    api = Mock()
    api.parents.return_value = {123: 1}
    api.window_pid.return_value = 123
    api.image_matches.return_value = True
    api.dialogs.return_value = [dialog(default_id=6 if bad_dialog else 7)]
    digest = "d" * 64

    def launch(args: list[str], **kwargs: object) -> object:
        process = Mock(pid=123, returncode=None)
        process.poll.side_effect = lambda: process.returncode
        process.wait.side_effect = lambda **_: process.returncode
        process.kill.side_effect = lambda: setattr(process, "returncode", -9)
        process.send_signal.side_effect = lambda _: setattr(process, "returncode", 0)
        processes.append(SimpleNamespace(process=process, args=args, kwargs=kwargs))
        return process

    def post(handle: int, message: int, choice: int, button: int) -> None:
        current = processes[-1]
        if choice == 7:
            current.process.returncode = 1
            current.kwargs["stdout"].write(
                "Windows runtime terms were not accepted; the game has not started.\n"
            )
        else:
            path = (
                Path(current.kwargs["env"]["LOCALAPPDATA"])
                / "BowlBound/accepted-windows-runtime-terms.json"
            )
            path.parent.mkdir()
            path.write_text(json.dumps({"schema": 1, "sha256": digest}))

    api.post.side_effect = post
    monkeypatch.setattr(smoke, "is_windows", lambda: True)
    monkeypatch.setattr(smoke, "read_terms", lambda *_: "Synthetic terms")
    monkeypatch.setattr(smoke, "_Windows", lambda: api)
    monkeypatch.setattr(smoke, "_open_port", lambda _: False)
    monkeypatch.setattr(smoke.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr(smoke.signal, "CTRL_BREAK_EVENT", 1, raising=False)
    monkeypatch.setattr(smoke.subprocess, "Popen", launch)
    monkeypatch.setattr(
        smoke,
        "request",
        lambda _, path, **__: (
            {"status": "healthy"} if path.endswith("health") else {"version": "1.1.1"}
        ),
    )
    if bad_dialog:
        with pytest.raises(RuntimeError, match="readability"):
            smoke.smoke_windows_terms(tmp_path / "app.exe", "1.1.1", tmp_path, digest)
        assert len(processes) == 1
        processes[0].process.kill.assert_called_once()
        api.post.assert_not_called()
    else:
        result = smoke.smoke_windows_terms(tmp_path / "app.exe", "1.1.1", tmp_path, digest)
        assert result["status"] == "passed"
        assert [entry["choice"] for entry in result["outcomes"]] == ["decline", "accept"]
        assert len(processes) == 2
        assert (
            processes[0].kwargs["env"]["LOCALAPPDATA"] != processes[1].kwargs["env"]["LOCALAPPDATA"]
        )
        for entry in processes:
            assert "--no-browser" in entry.args
            assert "--accept-windows-runtime-terms" not in entry.args
            entry.process.kill.assert_not_called()
        processes[1].process.send_signal.assert_called_once_with(1)


def test_changed_owner_image_is_rejected_before_post() -> None:
    api = Mock()
    api.window_pid.return_value = 123
    api.image_matches.return_value = False
    with pytest.raises(RuntimeError, match="image"):
        smoke.click_choice(api, dialog(), {123}, 7, Path("app.exe"))
    api.post.assert_not_called()


def test_source_probe_never_passes_on_unsupported_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(smoke, "is_windows", lambda: False)
    with pytest.raises(RuntimeError, match="Windows"):
        smoke.smoke_source_dialog(tmp_path / "WINDOWS-RUNTIME-TERMS.txt")


@pytest.mark.parametrize("failed", [False, True])
def test_cli_reports_source_scope_without_passing_unsupported_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed: bool
) -> None:
    import json

    report = tmp_path / "receipt.json"
    monkeypatch.setattr(
        smoke.sys,
        "argv",
        ["probe", "--source-dialog", "WINDOWS-RUNTIME-TERMS.txt", "--report", str(report)],
    )
    result = {
        "status": "passed",
        "scope": "source agreement dialog only; no packaged engine or browser",
    }
    probe = (
        Mock(side_effect=RuntimeError("Windows unavailable"))
        if failed
        else Mock(return_value=result)
    )
    monkeypatch.setattr(smoke, "smoke_source_dialog", probe)
    assert smoke.main() == (1 if failed else 0)
    saved = json.loads(report.read_text())
    assert saved["status"] == ("failed" if failed else "passed")
    assert "source agreement dialog only" in saved["scope"]
    probe.assert_called_once_with(Path("WINDOWS-RUNTIME-TERMS.txt"))


def test_source_dialog_orchestration_never_claims_packaged_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    from types import SimpleNamespace

    from backend import windows_terms

    digest = "e" * 64
    monkeypatch.setattr(windows_terms, "TERMS_SHA256", digest)
    monkeypatch.setattr(windows_terms, "reviewed_text", lambda _: "Synthetic terms")
    api = Mock()
    api.parents.return_value = {123: 1}
    api.window_pid.return_value = 123
    api.image_matches.return_value = True
    api.dialogs.return_value = [dialog()]
    children = []

    def launch(args: list[str], **kwargs: object) -> object:
        process = Mock(pid=123, returncode=None)
        process.poll.side_effect = lambda: process.returncode
        process.communicate.return_value = (b"", None)
        children.append(SimpleNamespace(process=process, args=args, kwargs=kwargs))
        return process

    def post(handle: int, message: int, choice: int, button: int) -> None:
        current = children[-1]
        current.process.returncode = 1 if choice == 7 else 0
        if choice == 7:
            current.process.communicate.return_value = (
                b"Windows runtime terms were not accepted; the game has not started.\n",
                None,
            )
        if choice == 6:
            receipt = (
                Path(current.kwargs["env"]["LOCALAPPDATA"])
                / "BowlBound/accepted-windows-runtime-terms.json"
            )
            receipt.parent.mkdir()
            receipt.write_text(json.dumps({"schema": 1, "sha256": digest}))

    api.post.side_effect = post
    monkeypatch.setattr(smoke, "is_windows", lambda: True)
    monkeypatch.setattr(smoke, "_Windows", lambda: api)
    monkeypatch.setattr(smoke.subprocess, "Popen", launch)
    result = smoke.smoke_source_dialog(tmp_path / "WINDOWS-RUNTIME-TERMS.txt")
    assert result["status"] == "passed"
    assert "no packaged engine" in result["scope"]
    assert len(children) == 2
    assert children[0].kwargs["env"]["LOCALAPPDATA"] != children[1].kwargs["env"]["LOCALAPPDATA"]
    for child in children:
        assert child.args[0] == smoke.sys.executable
        assert "ensure_accepted" in child.args[2]
        assert "--accept-windows-runtime-terms" not in child.args
        child.process.kill.assert_not_called()


def test_existing_source_probe_receipt_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    from unittest.mock import Mock

    from scripts import smoke_windows_terms as smoke

    report = tmp_path / "receipt.json"
    report.write_text("preserve failure")
    probe = Mock(return_value={"status": "passed"})
    monkeypatch.setattr(smoke, "smoke_source_dialog", probe)
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke", "--source-dialog", "WINDOWS-RUNTIME-TERMS.txt", "--report", str(report)],
    )
    with pytest.raises(SystemExit) as raised:
        smoke.main()
    assert raised.value.code == 2
    assert report.read_text() == "preserve failure"
    probe.assert_not_called()


@pytest.mark.parametrize(
    "output", ["", "Traceback (most recent call last):", "Fatal Python error: failed"]
)
def test_decline_rejects_crashes_and_missing_clean_refusal(output: str) -> None:
    from scripts import smoke_windows_terms as smoke

    with pytest.raises(RuntimeError, match="decline"):
        smoke.validate_decline_output(output)
    smoke.validate_decline_output(
        "Windows runtime terms were not accepted; the game has not started.\n"
    )
