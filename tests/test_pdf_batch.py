"""Batch import: a directory of PDFs, per-file status, partial failure, overwrite safety."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.team_csv import TEAM_FILES, load_team
from tests.synthetic_chart_pdf import write_chart_pdf
from tests.test_pdf_cli_export import _team
from tools.pdf_import import cli
from tools.pdf_import.export import ImportValidationError

ROOT = Path(__file__).resolve().parents[1]
SECRET = "PRIVATE-CHART-TOKEN"


@pytest.fixture
def pdfs(tmp_path: Path) -> Path:
    """A directory holding three placeholder PDFs; export_document is faked per file name."""
    folder = tmp_path / "pdfs"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (folder / name).write_bytes(b"placeholder")
    return folder


def _install(monkeypatch: pytest.MonkeyPatch, behaviours: dict[str, object]) -> None:
    def fake(path: Path) -> object:
        value = behaviours[path.name]
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(cli, "export_document", fake)


def _run(folder: Path, root: Path, *flags: str) -> int:
    return cli.main([str(folder), "--export", "--output", str(root), *flags])


def _three(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        {
            "a.pdf": [_team("Ohio State")],
            "b.pdf": [_team("Miami (Florida)")],
            "c.pdf": [_team("Texas A&M", 2003)],
        },
    )


def test_every_pdf_in_a_directory_is_exported(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _three(monkeypatch)
    root = tmp_path / "seasons"

    assert _run(pdfs, root) == 0

    for season, slug in ((2002, "ohio-state"), (2002, "miami-florida"), (2003, "texas-a-m")):
        assert sorted(p.name for p in (root / str(season) / slug).iterdir()) == sorted(TEAM_FILES)
        assert (root / str(season) / "provenance" / f"{slug}.csv").is_file()
    out = capsys.readouterr().out
    for index, name in enumerate(("a.pdf", "b.pdf", "c.pdf"), 1):
        assert f"[{index}/3] {name}: ok" in out
    assert "summary: 3 succeeded, 0 failed" in out


def test_one_failing_pdf_writes_nothing_and_does_not_stop_the_others(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _install(
        monkeypatch,
        {
            "a.pdf": [_team("Ohio State")],
            "b.pdf": ImportValidationError("chart is incomplete"),
            "c.pdf": [_team("Texas A&M", 2003)],
        },
    )
    root = tmp_path / "seasons"

    assert _run(pdfs, root) == 1

    assert (root / "2002" / "ohio-state").is_dir() and (root / "2003" / "texas-a-m").is_dir()
    assert sorted(p.name for p in (root / "2002").iterdir()) == ["ohio-state", "provenance"]
    captured = capsys.readouterr()
    assert "[2/3] b.pdf: FAILED - chart is incomplete" in captured.err
    assert "[1/3] a.pdf: ok" in captured.out and "[3/3] c.pdf: ok" in captured.out
    assert "summary: 2 succeeded, 1 failed" in captured.out


def test_unexpected_failure_in_one_pdf_leaks_nothing_and_continues(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _install(
        monkeypatch,
        {
            "a.pdf": KeyError(SECRET),
            "b.pdf": [_team("Miami (Florida)")],
            "c.pdf": [_team("Texas A&M", 2003)],
        },
    )
    assert _run(pdfs, tmp_path / "seasons") == 1
    captured = capsys.readouterr()
    assert SECRET not in captured.err + captured.out
    assert "[1/3] a.pdf: FAILED - unexpected failure while exporting" in captured.err
    assert "summary: 2 succeeded, 1 failed" in captured.out


def test_os_errors_do_not_echo_paths(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _install(
        monkeypatch,
        {
            "a.pdf": FileNotFoundError(2, "No such file or directory", "/Users/secret/ohio.pdf"),
            "b.pdf": [_team("Miami (Florida)")],
            "c.pdf": [_team("Texas A&M", 2003)],
        },
    )
    assert _run(pdfs, tmp_path / "seasons") == 1
    err = capsys.readouterr().err
    assert "/Users/secret" not in err and "No such file or directory" in err


def test_the_same_team_in_two_pdfs_is_never_merged(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    first, second = _team("Ohio State"), _team("OHIO  STATE")
    _install(
        monkeypatch,
        {"a.pdf": [first], "b.pdf": [second], "c.pdf": [_team("Texas A&M", 2003)]},
    )
    root = tmp_path / "seasons"

    assert _run(pdfs, root) == 1

    assert load_team(root / "2002", "ohio-state")[0].name == "Ohio State"
    assert sorted(p.name for p in (root / "2002" / "ohio-state").iterdir()) == sorted(TEAM_FILES)
    err = capsys.readouterr().err
    assert "[2/3] b.pdf: FAILED" in err and "refusing to merge" in err


def test_existing_team_fails_only_its_own_pdf_unless_forced(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _three(monkeypatch)
    root = tmp_path / "seasons"
    existing = root / "2002" / "miami-florida"
    existing.mkdir(parents=True)
    (existing / "team.yaml").write_text("keep")

    assert _run(pdfs, root) == 1
    assert (existing / "team.yaml").read_text() == "keep"
    assert sorted(p.name for p in existing.iterdir()) == ["team.yaml"]
    assert (root / "2002" / "ohio-state").is_dir() and (root / "2003" / "texas-a-m").is_dir()
    assert "[2/3] b.pdf: FAILED" in capsys.readouterr().err

    assert _run(pdfs, root, "--force") == 0
    assert load_team(root / "2002", "miami-florida")[0].name == "Miami (Florida)"


def test_a_write_failure_in_one_pdf_rolls_back_only_that_pdf(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _three(monkeypatch)
    original = cli._write_report
    state = {"calls": 0}

    def fail_in_second_pdf(*args: object, **kwargs: object) -> None:
        state["calls"] += 1
        if state["calls"] == 8:  # a.pdf wrote 5 files; this is the 3rd file of b.pdf
            raise OSError("disk full")
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cli, "_write_report", fail_in_second_pdf)
    root = tmp_path / "seasons"

    assert _run(pdfs, root) == 1

    assert load_team(root / "2002", "ohio-state")[0].name == "Ohio State"
    assert not (root / "2002" / "miami-florida").exists()
    assert not (root / "2002" / "provenance" / "miami-florida.csv").exists()
    assert load_team(root / "2003", "texas-a-m")[0].name == "Texas A&M"


def test_dry_run_checks_every_pdf_and_writes_nothing(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _install(
        monkeypatch,
        {
            "a.pdf": [_team("Ohio State")],
            "b.pdf": ImportValidationError("chart is incomplete"),
            "c.pdf": [_team("Texas A&M", 2003)],
        },
    )
    root = tmp_path / "seasons"

    assert _run(pdfs, root, "--dry-run") == 1

    assert not root.exists()
    captured = capsys.readouterr()
    printed = captured.out.replace(str(tmp_path) + "/", "")
    assert "[1/3] a.pdf: ok (dry run)" in printed
    assert "810 chart cells, 30 PAT outcomes" in printed
    assert "seasons/2002/ohio-state" in printed and "seasons/2003/texas-a-m" in printed
    assert "[2/3] b.pdf: FAILED" in captured.err


def test_dry_run_still_detects_a_team_repeated_across_pdfs(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _install(
        monkeypatch,
        {
            "a.pdf": [_team("Ohio State")],
            "b.pdf": [_team("Ohio State")],
            "c.pdf": [_team("Texas A&M", 2003)],
        },
    )
    assert _run(pdfs, tmp_path / "seasons", "--dry-run") == 1
    assert "[2/3] b.pdf: FAILED" in capsys.readouterr().err


def test_files_are_processed_in_sorted_order_and_non_pdfs_are_ignored(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    (pdfs / "notes.txt").write_text("not a pdf")
    (pdfs / ".hidden.pdf").write_bytes(b"x")
    (pdfs / "._a.pdf").write_bytes(b"x")
    (pdfs / "D.PDF").write_bytes(b"placeholder")
    (pdfs / "folder.pdf").mkdir()
    _install(
        monkeypatch,
        {
            "a.pdf": [_team("Ohio State")],
            "b.pdf": [_team("Miami (Florida)")],
            "c.pdf": [_team("Texas A&M", 2003)],
            "D.PDF": [_team("Michigan", 2003)],
        },
    )
    assert _run(pdfs, tmp_path / "seasons") == 0
    names = [
        line.split("] ")[1].split(":")[0]
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("[")
    ]
    assert names == sorted(names) == ["D.PDF", "a.pdf", "b.pdf", "c.pdf"]


def test_a_symlinked_pdf_refuses_the_whole_run(
    pdfs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (pdfs / "link.pdf").symlink_to(pdfs / "a.pdf")
    _three(monkeypatch)
    root = tmp_path / "seasons"
    assert _run(pdfs, root) == 1
    assert not root.exists()


def test_an_empty_directory_is_a_clear_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _run(empty, tmp_path / "seasons") == 1
    assert "no PDF" in capsys.readouterr().err


def test_inspection_mode_still_covers_exactly_one_pdf(
    pdfs: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    report = tmp_path / "report.json"
    assert cli.main([str(pdfs), "--output", str(report)]) == 1
    assert "--export" in capsys.readouterr().err
    assert not report.exists()


def test_a_single_pdf_is_processed_with_the_same_status_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """One PDF goes through the same per-file status path; the summary reports it as one."""
    path = tmp_path / "only.pdf"
    path.write_bytes(b"placeholder")
    monkeypatch.setattr(cli, "export_document", lambda p: [_team("Ohio State")])
    assert cli.main([str(path), "--export", "--output", str(tmp_path / "seasons")]) == 0
    out = capsys.readouterr().out
    assert "[1/1] only.pdf: ok" in out
    assert "summary: 1 succeeded, 0 failed" in out


def test_real_synthetic_pdfs_in_a_directory_with_one_corrupt(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    write_chart_pdf(
        folder / "1.pdf", [{"school": "Synthetic State", "mascot": "Synths", "season": 2002}]
    )
    write_chart_pdf(
        folder / "2.pdf",
        [{"school": "Broken College", "mascot": "Bugs", "season": 2004, "bad_pat": True}],
    )
    write_chart_pdf(
        folder / "3.pdf", [{"school": "Example University", "mascot": "Examples", "season": 2003}]
    )
    root = tmp_path / "seasons"

    assert _run(folder, root) == 1

    assert load_team(root / "2002", "synthetic-state")[0].name == "Synthetic State"
    assert load_team(root / "2003", "example-university")[0].name == "Example University"
    assert not (root / "2004").exists()


def test_two_teams_in_one_pdf_collide_only_when_they_share_season_and_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "pair.pdf"
    path.write_bytes(b"placeholder")
    a, b = _team("Ohio State"), _team("Ohio State", 2003)
    monkeypatch.setattr(cli, "export_document", lambda p: [a, replace(b)])
    assert cli.main([str(path), "--export", "--output", str(tmp_path / "seasons")]) == 0


# --- isolated PDF-tool dependencies --------------------------------------


def _modules_after(statement: str) -> set[str]:
    code = (
        "import sys\n"
        f"{statement}\n"
        "banned = {'pdfplumber', 'pdfminer', 'reportlab', 'tools'}\n"
        "print(sorted({m.split('.')[0] for m in sys.modules} & banned))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return set(eval(result.stdout.strip()))  # noqa: S307 - our own list literal


def test_the_engine_package_does_not_import_pdf_tools() -> None:
    assert _modules_after("import bowl_bound, bowl_bound.team_csv, bowl_bound.models") == set()


def test_importing_the_cli_does_not_load_pdf_libraries() -> None:
    loaded = _modules_after("import tools.pdf_import.cli")
    assert not loaded & {"pdfplumber", "pdfminer", "reportlab"}


@pytest.mark.parametrize("flags", [[], ["--export"]])
def test_missing_pdf_tools_give_an_install_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, flags: list[str]
) -> None:
    path = tmp_path / "x.pdf"
    path.write_bytes(b"%PDF-1.4 placeholder")
    monkeypatch.setitem(sys.modules, "pdfplumber", None)  # makes `import pdfplumber` fail
    output = tmp_path / ("seasons" if flags else "report.json")
    assert cli.main([str(path), "--output", str(output), *flags]) == 1
    err = capsys.readouterr().err
    assert "pip install" in err and ".[pdf]" in err
    assert not output.exists()
