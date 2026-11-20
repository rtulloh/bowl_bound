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


@pytest.mark.parametrize(("answer", "expected"), [(6, True), (7, False), (0, False)])
def test_native_dialog_defaults_to_no_and_requires_explicit_yes(
    answer: int, expected: bool
) -> None:
    show = Mock(return_value=answer)
    fake = SimpleNamespace(windll=SimpleNamespace(user32=SimpleNamespace(MessageBoxW=show)))
    with patch.dict("sys.modules", {"ctypes": fake}):
        assert windows_terms._ask("Synthetic terms") is expected
    assert show.call_args.args[1].startswith("Synthetic terms")
    assert show.call_args.args[3] == 0x124


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
