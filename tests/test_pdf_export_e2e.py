"""End-to-end export coverage using complete synthetic vector chart PDFs."""

from pathlib import Path

import pytest

from tests.synthetic_chart_pdf import write_chart_pdf
from tools.pdf_import.cells import CellExtractionError
from tools.pdf_import.export import ImportValidationError, export_document
from tools.pdf_import.inspection import ImportInspectionError, UnsupportedDocumentError
from tools.pdf_import.layout import LayoutError
from tools.pdf_import.metadata import MetadataError


def _teams() -> list[dict[str, object]]:
    return [
        {"school": "Synthetic State", "mascot": "Synths", "season": 2002},
        {"school": "Example University", "mascot": "Examples", "season": 2003},
    ]


def test_export_complete_two_team_synthetic_document(tmp_path: Path) -> None:
    path = tmp_path / "charts.pdf"
    spec = write_chart_pdf(path, _teams())

    teams = export_document(path)

    assert len(teams) == 2
    for index, exported in enumerate(teams):
        chart = exported.chart
        assert chart.name == _teams()[index]["school"]
        assert chart.season == _teams()[index]["season"]
        assert (len(chart.offense), len(chart.supplemental)) == (270, 90)
        assert (len(chart.defense), len(chart.special_teams), len(chart.pat_outcomes)) == (
            270,
            180,
            30,
        )
        assert chart.recovery_range == range(10, 26)
        assert exported.metadata.defense_label == _teams()[index]["mascot"]
        assert len(exported.metadata.source_sha256) == 64
        failures = {outcome.roll for outcome in chart.pat_outcomes if not outcome.good}
        assert failures == ({16} if index == 0 else {12, 26})
        cell = chart.offense[0].cell
        text, _ = spec[("offense", "1", 10, None)]
        assert (cell.kind.value, cell.yards, cell.priority.value) == ("yards", -int(text), "normal")


def test_exported_teams_are_paydirt_style_files_through_the_cli(tmp_path: Path) -> None:
    from bowl_bound.team_csv import TEAM_FILES, load_team
    from tools.pdf_import import cli

    path = tmp_path / "charts.pdf"
    write_chart_pdf(path, _teams())
    root = tmp_path / "seasons"

    assert cli.main([str(path), "--export", "--output", str(root)]) == 0

    expected = {"synthetic-state": 2002, "example-university": 2003}
    digest = export_document(path)[0].metadata.source_sha256
    for slug, season in expected.items():
        folder = root / str(season) / slug
        assert sorted(p.name for p in folder.iterdir()) == sorted(TEAM_FILES)
        assert (root / str(season) / "provenance" / f"{slug}.csv").is_file()
        chart, metadata = load_team(root / str(season), slug)
        assert len(chart.offense) == 270 and len(chart.pat_outcomes) == 30
        assert metadata.source_sha256 == digest
    assert not list(root.rglob("*.json"))


@pytest.mark.parametrize(
    "variation",
    [
        {"omit_boundary": True},
        {"bad_pat": True},
        {"unknown_fill": True},
        {"missing_rating": True},
        {"recovery": "Fumble Recovered 10-25; Fumble Lost 28-39"},
        {"bad_token": True},
        {"drop_defense": True},
    ],
)
def test_corrupt_synthetic_documents_are_rejected(
    tmp_path: Path, variation: dict[str, object]
) -> None:
    path = tmp_path / "corrupt.pdf"
    write_chart_pdf(path, [{**_teams()[0], **variation}])

    with pytest.raises(
        (
            ImportInspectionError,
            UnsupportedDocumentError,
            ImportValidationError,
            MetadataError,
            LayoutError,
            CellExtractionError,
        )
    ):
        export_document(path)


def test_same_mascot_does_not_merge_distinct_schools(tmp_path: Path) -> None:
    path = tmp_path / "tigers.pdf"
    write_chart_pdf(
        path,
        [
            {"school": "North Synthetic", "mascot": "Tigers", "season": 2002},
            {"school": "South Example", "mascot": "Tigers", "season": 2002},
        ],
    )

    teams = export_document(path)

    assert [team.chart.name for team in teams] == ["North Synthetic", "South Example"]
    assert [team.metadata.defense_label for team in teams] == ["Tigers", "Tigers"]
