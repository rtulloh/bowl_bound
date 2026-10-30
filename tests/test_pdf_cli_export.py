"""CLI --export: Paydirt-style seasons/<year>/<Team>/ folders with BB plays."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    NormalizedCell,
    OffensiveCell,
    PatOutcome,
    Play,
    Provenance,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.team_csv import TEAM_FILES, TeamFileMetadata, load_team
from tools.pdf_import import cli
from tools.pdf_import.export import ExportedTeam, ImportValidationError

SHA = "a" * 64
BB_OFFENSE_HEADER = (
    "#,Line Plunge,Counter,End Reverse,Draw,Option,Screen,Sprint Out,Boot-leg,Drop Back,"
    "B,QT,Fumble,QR"
)


def _provenance(text: str = "", rgb_color: tuple[int, int, int] = (0, 255, 0)) -> Provenance:
    return Provenance(SHA, "synthetic.pdf", 1, BoundingBox(0, 0, 1, 1), text, rgb_color)


def _team(name: str, season: int = 2002) -> ExportedTeam:
    cell = NormalizedCell(ResultKind.YARDS, _provenance("3"), yards=3)
    blank = NormalizedCell(ResultKind.NO_CHANGE, _provenance("", (255, 255, 255)))
    chart = TeamChart(
        1,
        name,
        season,
        tuple(OffensiveCell(p, r, cell) for p in Play for r in range(10, 40)),
        tuple(SupplementalCell(c, r, cell) for c in SupplementalColumn for r in range(10, 40)),
        tuple(DefensiveCell(d, p, r, blank) for d in Defense for p in Play for r in range(1, 6)),
        tuple(SpecialTeamsCell(c, r, cell) for c in SpecialTeamsColumn for r in range(10, 40)),
        tuple(
            PatOutcome(
                r,
                r != 16,
                _provenance(str(r), (255, 255, 255) if r != 16 else (255, 0, 0)),
            )
            for r in range(10, 40)
        ),
        range(10, 27),
    )
    return ExportedTeam(chart, TeamFileMetadata(200.5, ("W",), "Synths", SHA, ()))


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(b"placeholder")
    monkeypatch.setattr(cli, "export_document", lambda path: [_team("Synthetic State")])
    return path


def _run(source: Path, root: Path, *flags: str) -> int:
    return cli.main([str(source), "--export", "--output", str(root), *flags])


def test_export_matches_the_paydirt_season_layout(source: Path, tmp_path: Path) -> None:
    root = tmp_path / "seasons"
    assert _run(source, root) == 0
    team = root / "2002" / "synthetic-state"
    assert sorted(p.name for p in team.iterdir()) == sorted(TEAM_FILES)
    assert sorted(TEAM_FILES) == ["defense.csv", "offense.csv", "special.csv", "team.yaml"]
    assert (root / "2002" / "provenance" / "synthetic-state.csv").is_file()
    assert sorted(p.name for p in (root / "2002").iterdir()) == ["provenance", "synthetic-state"]
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.rglob("*") if p.is_file())


def test_chart_csvs_use_paydirt_names_and_bowl_bound_plays(source: Path, tmp_path: Path) -> None:
    assert _run(source, tmp_path / "seasons") == 0
    team = tmp_path / "seasons" / "2002" / "synthetic-state"
    assert (team / "offense.csv").read_text().splitlines()[0] == BB_OFFENSE_HEADER
    assert (team / "defense.csv").read_text().splitlines()[0] == (
        "#,Formation,Sub,Line Plunge,Counter,End Reverse,Draw,Option,Screen,Sprint Out,"
        "Boot-leg,Drop Back"
    )
    assert (team / "special.csv").read_text().splitlines()[0] == (
        "#,Kickoff,Kickoff Return,Punt,Punt Return,Int. Return,Field Goal,Extra Point"
    )
    for header in ("Off Tackle", "End Run", "Short", "Med", "Long", "T/E S/L"):
        assert header not in (team / "offense.csv").read_text().splitlines()[0]


def test_files_are_written_without_newline_translation(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows would write CRLF, which the strict reader rejects and which breaks byte identity."""
    import os

    seen: list[object] = []
    real = os.fdopen

    def spy(fd: int, mode: str = "r", *args: object, **kwargs: object) -> object:
        if "w" in mode:
            seen.append(kwargs.get("newline", "<default>"))
        return real(fd, mode, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "fdopen", spy)
    assert _run(source, tmp_path / "seasons") == 0
    assert seen and set(seen) == {""}


def test_exported_files_load_back_exactly(source: Path, tmp_path: Path) -> None:
    assert _run(source, tmp_path / "seasons") == 0
    chart, metadata = load_team(tmp_path / "seasons" / "2002", "synthetic-state")
    expected = _team("Synthetic State")
    assert (chart, metadata) == (expected.chart, expected.metadata)


def test_no_json_files_and_no_spaces_in_any_path(source: Path, tmp_path: Path) -> None:
    assert _run(source, tmp_path / "seasons") == 0
    written = list((tmp_path / "seasons").rglob("*"))
    assert not [p for p in written if p.suffix == ".json"]
    assert not [p for p in written if " " in p.name or "(" in p.name or p.name != p.name.lower()]
    assert not (tmp_path / "seasons" / "2002" / "Synthetic State").exists()


def test_two_teams_become_two_slugged_folders_keeping_real_names(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "export_document", lambda path: [_team("Ohio State"), _team("Miami (Florida)")]
    )
    root = tmp_path / "seasons"
    assert _run(source, root) == 0
    assert sorted(p.name for p in (root / "2002").iterdir()) == [
        "miami-florida",
        "ohio-state",
        "provenance",
    ]
    assert sorted(p.name for p in (root / "2002" / "provenance").iterdir()) == [
        "miami-florida.csv",
        "ohio-state.csv",
    ]
    assert load_team(root / "2002", "miami-florida")[0].name == "Miami (Florida)"
    assert "team_name: Miami (Florida)" in (root / "2002/miami-florida/team.yaml").read_text()


def test_dry_run_prints_counts_and_destinations_and_writes_nothing(
    source: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = tmp_path / "seasons"
    assert _run(source, root, "--dry-run") == 0
    assert not root.exists()
    printed = capsys.readouterr().out.replace(str(tmp_path) + "/", "")
    assert "810 chart cells, 30 PAT outcomes" in printed
    assert "seasons/2002/synthetic-state" in printed


def test_dry_run_does_not_refuse_existing_folders(source: Path, tmp_path: Path) -> None:
    team = tmp_path / "seasons" / "2002" / "synthetic-state"
    team.mkdir(parents=True)
    (team / "offense.csv").write_text("keep")
    assert _run(source, tmp_path / "seasons", "--dry-run") == 0
    assert (team / "offense.csv").read_text() == "keep"


def test_existing_team_requires_force_and_nothing_else_is_written(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "export_document", lambda path: [_team("Ohio State"), _team("Miami (Florida)")]
    )
    root = tmp_path / "seasons"
    existing = root / "2002" / "miami-florida"
    existing.mkdir(parents=True)
    (existing / "team.yaml").write_text("keep")
    assert _run(source, root) == 1
    assert (existing / "team.yaml").read_text() == "keep"
    assert not (root / "2002" / "ohio-state").exists()
    assert not (root / "2002" / "provenance").exists()
    assert _run(source, root, "--force") == 0
    assert load_team(root / "2002", "miami-florida")[0].name == "Miami (Florida)"


def test_failed_run_restores_everything_written_earlier(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "export_document", lambda path: [_team("Ohio State"), _team("Miami (Florida)")]
    )
    original = cli._write_report
    calls = {"count": 0}

    def fail_midway(*args: object, **kwargs: object) -> None:
        calls["count"] += 1
        if calls["count"] == 6:
            raise OSError("disk full")
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cli, "_write_report", fail_midway)
    root = tmp_path / "seasons"
    assert _run(source, root) == 1
    assert not root.exists() or not [p for p in root.rglob("*") if p.is_file()]


def test_validation_failure_writes_nothing_and_exits_one(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def reject(path: Path) -> None:
        raise ImportValidationError("chart is incomplete")

    monkeypatch.setattr(cli, "export_document", reject)
    root = tmp_path / "seasons"
    assert _run(source, root) == 1
    assert not root.exists()
    assert "incomplete" in capsys.readouterr().err


@pytest.mark.parametrize(
    "name",
    ["..", "../../evil", "a/b", "a\\b", " Ohio", "Ohio ", ".hidden", "provenance", "PROVENANCE"],
)
def test_unsafe_team_names_are_rejected_and_nothing_is_written(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    team = _team("Ohio State")
    unsafe = replace(team, chart=replace(team.chart, name=name))
    monkeypatch.setattr(cli, "export_document", lambda path: [unsafe])
    root = tmp_path / "seasons"
    assert _run(source, root) == 1
    assert not root.exists()
    assert not (tmp_path.parent / "evil").exists()


@pytest.mark.parametrize("other", ["OHIO STATE", "Ohio-State", "ohio  state", "Ohio (State)"])
def test_names_that_collide_after_slugging_are_rejected(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, other: str
) -> None:
    monkeypatch.setattr(cli, "export_document", lambda path: [_team("Ohio State"), _team(other)])
    root = tmp_path / "seasons"
    assert _run(source, root) == 1
    assert not root.exists()


def test_default_mode_remains_inspection_only(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        cli, "inspect_document", lambda path: SimpleNamespace(source_sha256="b" * 64, pages=())
    )
    output = tmp_path / "report.json"
    assert cli.main([str(source), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["status"] == "inspection_only"


def test_export_root_cannot_be_the_source_pdf(source: Path) -> None:
    before = source.read_bytes()
    assert _run(source, source, "--force") == 1
    assert source.read_bytes() == before


def test_written_files_contain_no_local_paths(source: Path, tmp_path: Path) -> None:
    assert _run(source, tmp_path / "seasons") == 0
    text = "".join(p.read_text() for p in (tmp_path / "seasons").rglob("*") if p.is_file())
    assert not re.search(r"/Users/|/private/", text)
