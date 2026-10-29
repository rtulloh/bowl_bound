"""Verification report tests using synthetic team files only."""

from __future__ import annotations

from pathlib import Path

import pytest

from bowl_bound.team_csv import PROVENANCE_DIR, provenance_to_csv, team_to_files
from tests.test_team_csv import chart, metadata
from tools.pdf_import.verification import VerificationError, verify_team_export


def write_team(season_dir: Path, slug: str) -> None:
    folder = season_dir / slug
    folder.mkdir(parents=True)
    current_chart = chart()
    current_metadata = metadata()
    for name, text in team_to_files(current_chart, current_metadata).items():
        (folder / name).write_text(text, encoding="utf-8", newline="")
    provenance = season_dir / PROVENANCE_DIR
    provenance.mkdir(exist_ok=True)
    (provenance / f"{slug}.csv").write_text(
        provenance_to_csv(current_chart, current_metadata), encoding="utf-8", newline=""
    )


def test_verification_reports_complete_counts_and_metadata(tmp_path: Path) -> None:
    season = tmp_path / "2026"
    write_team(season, "ohio-state")

    report = verify_team_export(
        season,
        "ohio-state",
        expected={
            "team_name": "Ohio State",
            "season": 2026,
            "recovery_range": range(10, 27),
            "pat_failures": tuple(range(11, 40, 2)),
            "power_rating": 5.5,
            "privileges": ("W",),
        },
    )

    assert report.chart_cells == 810
    assert report.pat_outcomes == 30
    assert report.team_name == "Ohio State"
    assert report.recovery_range == range(10, 27)
    assert report.pat_failures == tuple(range(11, 40, 2))
    assert report.provenance_rows == 841


def test_verification_rejects_an_unexpected_real_value(tmp_path: Path) -> None:
    season = tmp_path / "2026"
    write_team(season, "ohio-state")

    with pytest.raises(VerificationError, match="power rating"):
        verify_team_export(season, "ohio-state", expected={"power_rating": 200.5})


def test_verification_rejects_missing_or_corrupt_export(tmp_path: Path) -> None:
    with pytest.raises(VerificationError, match="team export"):
        verify_team_export(tmp_path / "2026", "ohio-state")

    season = tmp_path / "2026"
    write_team(season, "ohio-state")
    (season / "ohio-state" / "offense.csv").write_text("broken", encoding="utf-8")
    with pytest.raises(VerificationError, match="team export"):
        verify_team_export(season, "ohio-state")
