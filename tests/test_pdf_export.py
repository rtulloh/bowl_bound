"""Synthetic extraction-to-chart validation and export assembly."""

from types import SimpleNamespace

import pytest

from bowl_bound.models import BoundingBox, Provenance
from bowl_bound.normalization import CELL_LEGEND, ChartColor
from tools.pdf_import.export import _COLORS, ImportValidationError, build_team
from tools.pdf_import.metadata import TeamMetadata


def records() -> list[object]:
    result = []
    for section, columns, rolls, defenses in [
        ("offense", [str(i) for i in range(1, 10)], range(10, 40), [None]),
        ("supplemental", ["B", "QR", "QT"], range(10, 40), [None]),
        ("defense", [str(i) for i in range(1, 10)], range(1, 6), list("ABCDEF")),
        (
            "special_teams",
            [
                "kickoff",
                "kickoff_return",
                "punt",
                "punt_return",
                "interception_return",
                "field_goal",
            ],
            range(10, 40),
            [None],
        ),
        ("pat", ["pat"], range(10, 40), [None]),
    ]:
        for defense in defenses:
            for roll in rolls:
                for column in columns:
                    text = str(roll) if section == "pat" else ""
                    rgb = (255, 0, 0) if section == "pat" and roll == 16 else (255, 255, 255)
                    proof = Provenance(
                        "a" * 64, "synthetic.pdf", 1, BoundingBox(0, 0, 1, 1), text, rgb
                    )
                    result.append(
                        (
                            SimpleNamespace(
                                section=section, column=column, roll=roll, defense=defense
                            ),
                            SimpleNamespace(provenance=proof, rgb_color=rgb, text=text, rotation=0),
                        )
                    )
    return result


def test_pdf_color_classification_uses_the_shared_cell_legend() -> None:
    assert set(CELL_LEGEND) == set(ChartColor)
    assert _COLORS == {legend.rgb_color: color for color, legend in CELL_LEGEND.items()}


def test_build_team_from_complete_synthetic_evidence() -> None:
    chart = build_team("Synthetic State", 2002, records(), TeamMetadata(200, range(10, 26), (), ()))
    cells = (chart.offense, chart.supplemental, chart.defense, chart.special_teams)
    assert sum(len(group) for group in cells) == 810
    assert [pat.roll for pat in chart.pat_outcomes if not pat.good] == [16]


def test_incomplete_cells_and_bad_pat_evidence_are_rejected() -> None:
    items = records()
    metadata = TeamMetadata(200, range(10, 26), (), ())
    with pytest.raises(ImportValidationError):
        build_team("Synthetic", 2002, items[:-1], metadata)
    items[-1][1].text = "38"
    with pytest.raises(ImportValidationError, match="PAT"):
        build_team("Synthetic", 2002, items, metadata)


def test_build_team_uses_the_canonical_order_the_csv_reader_produces() -> None:
    """Two producers of the same chart must agree, whatever order cells were extracted in."""
    from bowl_bound.team_csv import (
        TeamFileMetadata,
        provenance_to_csv,
        team_from_files,
        team_to_files,
    )

    shuffled = list(reversed(records()))
    chart = build_team("Synthetic State", 2002, shuffled, TeamMetadata(200, range(10, 26), (), ()))
    metadata = TeamFileMetadata(200.0, (), "Synths", "a" * 64, ())

    restored, _ = team_from_files(
        team_to_files(chart, metadata), provenance_to_csv(chart, metadata)
    )

    assert restored == chart
    assert [record.roll for record in chart.pat_outcomes] == list(range(10, 40))
