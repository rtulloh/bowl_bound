"""Windows assent is tested with synthetic terms and mocked native dialogs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend import windows_terms


@pytest.fixture
def terms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, str]:
    root = tmp_path / "runtime"
    root.mkdir()
    text = b"Synthetic distribution conditions. Agree only explicitly.\n"
    (root / windows_terms.TERMS_FILENAME).write_bytes(text)
    digest = hashlib.sha256(text).hexdigest()
    monkeypatch.setattr(windows_terms, "TERMS_SHA256", digest)
    appdata = tmp_path / "user data"
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))
    return root, appdata / "BowlBound/accepted-windows-runtime-terms.json", digest


@pytest.mark.parametrize("answer", [False, None])
def test_decline_or_unavailable_dialog_does_not_persist(
    terms: tuple[Path, Path, str], answer: bool | None
) -> None:
    root, receipt, _ = terms
    dialog = Mock(return_value=answer)
    assert not windows_terms.ensure_accepted(root, None, ask=dialog)
    dialog.assert_called_once()
    assert "Synthetic distribution" in dialog.call_args.args[0]
    assert not receipt.exists()


def test_acceptance_is_hash_keyed_and_does_not_prompt_again(terms: tuple[Path, Path, str]) -> None:
    root, receipt, digest = terms
    assert windows_terms.ensure_accepted(root, None, ask=Mock(return_value=True))
    assert json.loads(receipt.read_text()) == {"schema": 1, "sha256": digest}
    dialog = Mock(side_effect=AssertionError("must not prompt"))
    assert windows_terms.ensure_accepted(root, None, ask=dialog)
    dialog.assert_not_called()


@pytest.mark.parametrize("old", ["invalid JSON", '{"schema":1,"sha256":"old"}', "[]"])
def test_invalid_or_stale_receipt_does_not_accept(terms: tuple[Path, Path, str], old: str) -> None:
    root, receipt, _ = terms
    receipt.parent.mkdir(parents=True)
    receipt.write_text(old)
    assert not windows_terms.ensure_accepted(root, None, ask=Mock(return_value=False))
    assert receipt.read_text() == old


def test_exact_explicit_flag_accepts_without_dialog(terms: tuple[Path, Path, str]) -> None:
    root, receipt, digest = terms
    assert windows_terms.ensure_accepted(root, digest, ask=Mock(side_effect=AssertionError))
    assert json.loads(receipt.read_text())["sha256"] == digest


def test_wrong_explicit_flag_is_refused_even_with_previous_acceptance(
    terms: tuple[Path, Path, str],
) -> None:
    root, _, digest = terms
    assert windows_terms.ensure_accepted(root, digest)
    assert not windows_terms.ensure_accepted(root, "wrong", ask=Mock(side_effect=AssertionError))


@pytest.mark.parametrize("mutation", ["missing", "changed"])
def test_unreviewed_terms_never_prompt_or_accept(
    terms: tuple[Path, Path, str], mutation: str
) -> None:
    root, receipt, digest = terms
    path = root / windows_terms.TERMS_FILENAME
    path.unlink() if mutation == "missing" else path.write_text("Changed conditions")
    assert not windows_terms.ensure_accepted(root, digest, ask=Mock(side_effect=AssertionError))
    assert not receipt.exists()


def test_persistence_failure_and_missing_appdata_refuse_startup(
    terms: tuple[Path, Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, receipt, digest = terms
    receipt.parent.parent.write_text("not a directory")
    assert not windows_terms.ensure_accepted(root, digest)
    monkeypatch.delenv("LOCALAPPDATA")
    assert not windows_terms.ensure_accepted(root, digest)


def test_public_terms_preserve_project_and_upstream_conditions_verbatim() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "WINDOWS-RUNTIME-TERMS.txt").read_bytes()
    assert text.startswith((root / "LICENSE").read_bytes())
    assert text.endswith((root / "release/native-notices/cpython-windows-binary.txt").read_bytes())
    assert hashlib.sha256(text).hexdigest() == windows_terms.TERMS_SHA256


@pytest.mark.parametrize(
    ("platform", "frozen", "expected"),
    [("win32", True, True), ("win32", False, False), ("darwin", True, False)],
)
def test_only_frozen_windows_requires_assent(
    monkeypatch: pytest.MonkeyPatch, platform: str, frozen: bool, expected: bool
) -> None:
    monkeypatch.setattr(windows_terms, "sys", SimpleNamespace(platform=platform, frozen=frozen))
    assert windows_terms.required() is expected


@pytest.mark.parametrize(("answer", "expected"), [(6, True), (7, False), (2, False), (-1, None)])
def test_scrollable_dialog_requires_explicit_yes(answer: int, expected: bool | None) -> None:
    show = Mock(return_value=answer)
    with patch.object(windows_terms, "_show_scrollable_dialog", show):
        assert windows_terms._ask("Synthetic terms") is expected
    assert show.call_args.args == (
        "Synthetic terms\n\nChoose Yes to agree to these conditions and continue. "
        "Choose No to quit.",
    )


@pytest.mark.parametrize("dpi", [96, 144, 192])
@pytest.mark.parametrize("work", [(0, 0, 1280, 720), (-1920, 0, 0, 1080)])
def test_scrollable_layout_stays_within_work_area(
    work: tuple[int, int, int, int], dpi: int
) -> None:
    x, y, width, height = windows_terms._dialog_bounds(work, dpi)
    assert work[0] <= x < x + width <= work[2]
    assert work[1] <= y < y + height <= work[3]
    controls = windows_terms._control_bounds(width - 20, height - 40, dpi)
    for cx, cy, cw, ch in controls.values():
        assert 0 <= cx < cx + cw <= width - 20
        assert 0 <= cy < cy + ch <= height - 40
    edit = controls[1001]
    assert edit[1] + edit[3] < controls[7][1]
    assert controls[6][0] + controls[6][2] < controls[7][0]


def test_dialog_template_preserves_text_scrollbar_readonly_and_default_no() -> None:
    import struct

    text = "Synthetic terms \u2603\nLast line"
    data = windows_terms._dialog_template(text)
    assert (text.replace("\n", "\r\n") + "\0").encode("utf-16-le") in data
    assert ("Bowl Bound Windows terms\0").encode("utf-16-le") in data
    assert struct.pack("I", 0x50A10844) in data  # readonly multiline scrollable EDIT
    assert struct.pack("I", 0x50010001) in data  # default No button
    assert struct.pack("H", 1001) in data


def test_failed_receipt_cleanup_does_not_override_fail_closed_result(
    terms: tuple[Path, Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, digest = terms
    monkeypatch.setattr(Path, "replace", Mock(side_effect=OSError("synthetic replace failure")))
    monkeypatch.setattr(Path, "unlink", Mock(side_effect=OSError("synthetic cleanup failure")))
    assert not windows_terms.ensure_accepted(root, digest)
    assert "synthetic replace failure" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("message", "wparam", "expected"),
    [
        (0x10, 0, 7),
        (0x111, 2, 7),
        (0x111, 7, 7),
        (0x111, 6, 6),
        (0x111, 1001, None),
        (0x100, 6, None),
    ],
)
def test_native_close_cancel_and_unrelated_messages_never_accept(
    message: int,
    wparam: int,
    expected: int | None,
) -> None:
    assert windows_terms._dialog_action(message, wparam) == expected
