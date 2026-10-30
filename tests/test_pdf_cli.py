"""CLI boundary tests; document inspection is independently tested with synthetic PDFs."""

import errno
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.pdf_import import cli


@dataclass(frozen=True)
class SyntheticPage:
    page: int = 1
    role: str = "offense"
    team_name: str = "Synthetic State"
    season: int = 2002


class SyntheticParserError(Exception):
    """Represents an exception raised by a PDF parser dependency."""


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(b"synthetic PDF placeholder")
    monkeypatch.setattr(
        cli,
        "inspect_document",
        lambda path: SimpleNamespace(source_sha256="a" * 64, pages=(SyntheticPage(),)),
    )
    return path


def test_dry_run_writes_nothing(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    output = tmp_path / "new" / "report.json"
    assert cli.main([str(source), "--output", str(output), "--dry-run"]) == 0
    assert not output.parent.exists()
    assert "Synthetic State" in capsys.readouterr().out


def test_report_is_explicitly_not_a_playable_team(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert cli.main([str(source), "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["report_version"] == 1
    assert report["status"] == "inspection_only"
    assert report["source_sha256"] == "a" * 64
    assert report["pages"][0]["team_name"] == "Synthetic State"


def test_existing_output_requires_force(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    output.write_text("keep me")
    assert cli.main([str(source), "--output", str(output)]) == 1
    assert output.read_text() == "keep me"
    assert cli.main([str(source), "--output", str(output), "--force"]) == 0
    assert json.loads(output.read_text())["status"] == "inspection_only"


def test_input_cannot_be_overwritten_even_with_force(source: Path) -> None:
    before = source.read_bytes()
    assert cli.main([str(source), "--output", str(source), "--force"]) == 1
    assert source.read_bytes() == before


def test_symlink_output_is_never_followed(source: Path, tmp_path: Path) -> None:
    target = tmp_path / "keep.json"
    target.write_text("keep")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert cli.main([str(source), "--output", str(link), "--force"]) == 1
    assert target.read_text() == "keep"


@pytest.mark.parametrize("pdf_count", [0, 1, 2], ids=["empty", "one-pdf", "multiple-pdfs"])
def test_inspection_rejects_directories_before_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    pdf_count: int,
) -> None:
    folder = tmp_path / "input"
    folder.mkdir()
    for index in range(pdf_count):
        (folder / f"{index}.pdf").write_bytes(b"placeholder")
    real_iterdir = Path.iterdir
    scanned: list[Path] = []

    def track_scan(path: Path) -> Iterator[Path]:
        if path == folder:
            scanned.append(path)
        return real_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", track_scan)
    inspected: list[Path] = []

    def inspect(path: Path) -> object:
        inspected.append(path)
        raise AssertionError("inspection must not run for directory input")

    monkeypatch.setattr(cli, "inspect_document", inspect)
    output = tmp_path / "report.json"

    assert cli.main([str(folder), "--output", str(output)]) == 1

    assert "single PDF file" in capsys.readouterr().err
    assert scanned == []
    assert inspected == []
    assert not output.exists()


def test_inspection_mode_takes_one_pdf_and_points_to_export(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Batch processing is export-only; inspection of several PDFs would need a second report."""
    (source.parent / "second.PDF").write_bytes(b"pdf")
    assert cli.main([str(source.parent), "--output", str(tmp_path / "report.json")]) == 1
    assert "--export" in capsys.readouterr().err
    assert not (tmp_path / "report.json").exists()


def test_inspection_directory_requires_export_mode(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    (source.parent / "second.PDF").write_bytes(b"second synthetic PDF")
    assert cli.main([str(source.parent), "--output", str(tmp_path / "report.json")]) == 1
    error = capsys.readouterr().err
    assert "inspection mode requires a single pdf file" in error.lower()
    assert "--export" in error


def test_missing_input_and_empty_directory_fail(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert cli.main([str(tmp_path / "missing.pdf"), "--output", str(output)]) == 1
    assert cli.main([str(tmp_path), "--output", str(output)]) == 1


def test_inspection_failure_never_writes_output(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(path: Path) -> None:
        raise ValueError("unsupported scanned document")

    monkeypatch.setattr(cli, "inspect_document", fail)
    output = tmp_path / "report.json"
    assert cli.main([str(source), "--output", str(output)]) == 1
    assert not output.exists()


def test_argument_errors_and_help(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main([])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as help_result:
        cli.main(["--help"])
    assert help_result.value.code == 0
    assert "5d" not in capsys.readouterr().out


def test_help_explains_that_directory_input_requires_export(
    capsys: pytest.CaptureFixture,
) -> None:
    with pytest.raises(SystemExit) as help_result:
        cli.main(["--help"])

    assert help_result.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "with --export, a directory of PDFs is also accepted" in help_text
    assert "Replace existing report or team files" in help_text


def test_hardlinked_source_cannot_be_destroyed(source: Path, tmp_path: Path) -> None:
    import os

    alias = tmp_path / "alias.json"
    os.link(source, alias)
    before = source.read_bytes()
    assert cli.main([str(source), "--output", str(alias), "--force"]) == 1
    assert source.read_bytes() == before


def test_output_directory_is_rejected(source: Path, tmp_path: Path) -> None:
    assert cli.main([str(source), "--output", str(tmp_path), "--force"]) == 1


def test_document_error_has_nonzero_exit(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(path: Path) -> None:
        raise cli.ImportInspectionError("Unsupported encrypted document")

    monkeypatch.setattr(cli, "inspect_document", fail)
    output = tmp_path / "report.json"
    assert cli.main([str(source), "--output", str(output)]) == 1
    assert not output.exists()


@pytest.mark.parametrize(
    "failure",
    [
        ValueError("SYNTHETIC_PRIVATE_SENTINEL /private/chart.pdf\nforged diagnostic"),
        UnicodeDecodeError(
            "utf-8",
            b"SYNTHETIC_PRIVATE_SENTINEL",
            0,
            1,
            "SYNTHETIC_PRIVATE_SENTINEL /private/chart.pdf\nforged diagnostic",
        ),
        cli.ImportInspectionError(
            "SYNTHETIC_PRIVATE_SENTINEL /private/chart.pdf\nforged diagnostic"
        ),
        SyntheticParserError("SYNTHETIC_PRIVATE_SENTINEL /private/chart.pdf\nforged diagnostic"),
    ],
    ids=["value-error", "decode-error", "inspection-error", "parser-error"],
)
def test_untrusted_inspection_errors_never_appear_in_cli_output(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    failure: Exception,
) -> None:
    def fail(path: Path) -> None:
        raise failure

    monkeypatch.setattr(cli, "inspect_document", fail)
    output = tmp_path / "report.json"

    assert cli.main([str(source), "--output", str(output)]) == 1

    captured = capsys.readouterr()
    assert "SYNTHETIC_PRIVATE_SENTINEL" not in captured.out + captured.err
    assert "/private/chart.pdf" not in captured.out + captured.err
    assert "forged diagnostic" not in captured.out + captured.err
    assert "PDF import error:" in captured.err
    assert not output.exists()


def test_safe_missing_dependency_error_keeps_install_hint(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    message = 'PDF inspection requires optional tools; run `python -m pip install -e ".[pdf]"`.'

    def fail(path: Path) -> None:
        raise cli.SafeImportInspectionError(message)

    monkeypatch.setattr(cli, "inspect_document", fail)

    assert cli.main([str(source), "--output", str(tmp_path / "report.json")]) == 1

    captured = capsys.readouterr()
    assert message in captured.err
    assert "pip install" in captured.err


def test_output_oserror_does_not_echo_message_or_path(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    output = tmp_path / "report.json"
    output.write_text("keep")

    def explode(*args: object, **kwargs: object) -> None:
        raise OSError(errno.EIO, "SYNTHETIC_PRIVATE_SENTINEL /private/output\nforged diagnostic")

    monkeypatch.setattr(cli.os, "replace", explode)

    assert cli.main([str(source), "--output", str(output), "--force"]) == 1

    captured = capsys.readouterr()
    assert "SYNTHETIC_PRIVATE_SENTINEL" not in captured.out + captured.err
    assert "/private/output" not in captured.out + captured.err
    assert "forged diagnostic" not in captured.out + captured.err
    assert "File operation failed" in captured.err
    assert output.read_text() == "keep"


def test_new_reports_are_private(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "private.json"
    assert cli.main([str(source), "--output", str(output)]) == 0
    assert output.stat().st_mode & 0o777 == 0o600


# --- Review corrections: atomic replacement, races, privacy, unexpected failures ---


def test_force_replaces_atomically_and_never_truncates_a_late_hardlink(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link to the source appearing after preflight must not destroy the source."""
    import os

    output = tmp_path / "report.json"
    output.write_text("previous report")
    original_inspect = cli.inspect_document

    def inspect_then_race(path: Path) -> object:
        result = original_inspect(path)
        output.unlink()
        os.link(source, output)  # race: output now aliases the source PDF
        return result

    monkeypatch.setattr(cli, "inspect_document", inspect_then_race)
    before = source.read_bytes()
    status = cli.main([str(source), "--output", str(output), "--force"])
    assert source.read_bytes() == before
    assert status in (0, 1)
    if status == 0:  # replaced the directory entry; the source inode is untouched
        assert json.loads(output.read_text())["status"] == "inspection_only"
        assert source.read_bytes() == before


def test_failed_write_preserves_previous_report_and_leaves_no_temp_files(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "report.json"
    output.write_text("previous report")

    def explode(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cli.os, "replace", explode)
    assert cli.main([str(source), "--output", str(output), "--force"]) == 1
    assert output.read_text() == "previous report"
    assert sorted(p.name for p in tmp_path.iterdir() if p.name != "synthetic.pdf") == [
        "report.json"
    ]


def test_forced_replacement_tightens_loose_permissions(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    output.write_text("previous")
    output.chmod(0o644)
    assert cli.main([str(source), "--output", str(output), "--force"]) == 0
    assert output.stat().st_mode & 0o777 == 0o600


def test_failed_inspection_creates_no_parent_directories(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "inspect_document", lambda path: (_ for _ in ()).throw(cli.ImportInspectionError("x"))
    )
    output = tmp_path / "new" / "deeper" / "report.json"
    assert cli.main([str(source), "--output", str(output)]) == 1
    assert not (tmp_path / "new").exists()


def test_unexpected_failure_prints_fixed_message_without_traceback_or_text(
    source: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, tmp_path: Path
) -> None:
    def explode(path: Path) -> None:
        raise KeyError("PRIVATE-CHART-TEXT")

    monkeypatch.setattr(cli, "inspect_document", explode)
    assert cli.main([str(source), "--output", str(tmp_path / "r.json")]) == 1
    captured = capsys.readouterr()
    assert "PRIVATE-CHART-TEXT" not in captured.err + captured.out
    assert "Traceback" not in captured.err
    assert "unexpected" in captured.err.lower()


def test_dry_run_with_force_leaves_existing_output_untouched(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    output.write_text("keep me")
    assert cli.main([str(source), "--output", str(output), "--dry-run", "--force"]) == 0
    assert output.read_text() == "keep me"


def test_symlinked_parent_directory_is_refused(source: Path, tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)
    assert cli.main([str(source), "--output", str(tmp_path / "linked" / "report.json")]) == 1
    assert list(real.iterdir()) == []


def test_dangling_symlink_output_is_refused(source: Path, tmp_path: Path) -> None:
    link = tmp_path / "dangling.json"
    link.symlink_to(tmp_path / "does-not-exist.json")
    assert cli.main([str(source), "--output", str(link), "--force"]) == 1
    assert not (tmp_path / "does-not-exist.json").exists()


def test_symlink_loop_output_is_a_clean_error(source: Path, tmp_path: Path) -> None:
    loop = tmp_path / "loop.json"
    loop.symlink_to(loop)
    assert cli.main([str(source), "--output", str(loop), "--force"]) == 1


def test_directory_rejects_symlinked_pdf(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    real = tmp_path / "real.pdf"
    real.write_bytes(b"pdf")
    (folder / "linked.pdf").symlink_to(real)
    assert cli.main([str(folder), "--output", str(tmp_path / "seasons"), "--export"]) == 1


@pytest.mark.parametrize("mode_flags", [[], ["--export"]], ids=["inspection", "export"])
@pytest.mark.parametrize("link_kind", ["directory", "file", "dangling"])
def test_symlink_input_is_refused_before_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode_flags: list[str],
    link_kind: str,
) -> None:
    target = tmp_path / f"real-{link_kind}"
    if link_kind == "directory":
        target.mkdir()
        (target / "team.pdf").write_bytes(b"placeholder")
    elif link_kind == "file":
        target = target.with_suffix(".pdf")
        target.write_bytes(b"placeholder")
    linked_input = tmp_path / f"linked-{link_kind}.pdf"
    linked_input.symlink_to(target, target_is_directory=(link_kind == "directory"))
    scanned: list[Path] = []
    real_iterdir = Path.iterdir

    def track_scan(path: Path) -> Iterator[Path]:
        if path == linked_input:
            scanned.append(path)
        return real_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", track_scan)
    processed: list[Path] = []

    def record_inspection(path: Path) -> object:
        processed.append(path)
        raise AssertionError("refused symlink input must not be inspected")

    def record_export(path: Path) -> list[object]:
        processed.append(path)
        raise AssertionError("refused symlink input must not be exported")

    monkeypatch.setattr(cli, "inspect_document", record_inspection)
    monkeypatch.setattr(cli, "export_document", record_export)
    output = tmp_path / ("seasons" if mode_flags else "report.json")

    assert cli.main([str(linked_input), "--output", str(output), *mode_flags]) == 1

    assert processed == []
    assert scanned == []
    assert not output.exists()


def test_error_messages_do_not_echo_document_text(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def fail(path: Path) -> None:
        from tools.pdf_import.inspection import UnsupportedDocumentError

        raise UnsupportedDocumentError("Page 3 lacks a supported header")

    monkeypatch.setattr(cli, "inspect_document", fail)
    assert cli.main([str(source), "--output", str(tmp_path / "r.json")]) == 1
    assert "Page 3 lacks a supported header" in capsys.readouterr().err


def test_end_to_end_with_real_inspection_of_a_synthetic_pdf(tmp_path: Path) -> None:
    """No mocks: the CLI and the inspector agree on a generated document."""
    from tests.test_pdf_inspection import _write_document

    pdf = tmp_path / "charts.pdf"
    _write_document(pdf, [("Synthetic State", "Synths", 2002)])
    output = tmp_path / "reports" / "r.json"
    assert cli.main([str(pdf), "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    import hashlib

    assert report["source_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert [p["role"] for p in report["pages"]] == ["offense", "defense_special"]
