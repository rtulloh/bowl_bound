"""Priority reference agrees with the independently transcribed matrix."""

from dataclasses import asdict

from bowl_bound.chart_view import chart_book
from bowl_bound.resolution import resolve_cells
from tests.priority_matrix import COLUMNS, PRIORITY_MATRIX, ROWS
from tests.synthetic_teams import team_chart
from tests.test_priority_matrix import coordinates, sample


def test_priority_reference_contains_every_printed_intersection_and_extension() -> None:
    reference = chart_book(team_chart("Synthetic College")).priority
    table = reference.table
    assert len(table.rows) == 12 and len(table.columns) == 14
    assert [row.label for row in table.rows] == [
        "# / B",
        "-#",
        "(#)",
        "blank",
        "TD",
        "QR",
        "QT",
        "INC",
        "INT",
        "F",
        "SOP / BLP",
        "PEN",
    ]
    aliases = {"OPTION": "OPT", "PENALTY": "PEN"}
    expected = tuple(tuple(aliases.get(code, code) for code in row) for row in PRIORITY_MATRIX)
    assert tuple(tuple(cell.label for cell in row.cells[:13]) for row in table.rows) == expected
    assert [column.label for column in table.columns] == [
        "#",
        "-#",
        "blank",
        "(#)",
        "(-#)",
        "[#]",
        "[-#]",
        "(TD) / [TD]",
        "QR",
        "QT",
        "INT",
        "F",
        "INC",
        "(B) †",
    ]
    assert [row.cells[-1].label for row in table.rows] == [
        "D",
        "D",
        "O",
        "D",
        "D",
        "D",
        "D",
        "D",
        "D",
        "D",
        "OPT",
        "PEN",
    ]
    assert (
        "offensive row" in reference.note.lower() and "defensive column" in reference.note.lower()
    )
    assert any("signed" in note for note in reference.notes)
    extension = next(note for note in reference.notes if "(B)" in note and "extension" in note)
    assert all(term in extension for term in ("parenthesized", "SOP", "BLP", "penalty"))
    assert any("Offensive" in note and "brackets" in note for note in reference.notes)
    assert {entry.label for entry in reference.legend} == {code for row in expected for code in row}
    assert "provenance" not in str(asdict(reference))


def test_grouped_representatives_match_all_expanded_runtime_coordinates() -> None:
    rows = chart_book(team_chart("Synthetic College")).priority.table.rows
    aliases = {"OPTION": "OPT", "PENALTY": "PEN"}
    for case in coordinates():
        row, column, variant, defense_variant, expected = case.values
        actual = resolve_cells(sample(row, variant), sample(column, defense_variant))
        shown = rows[ROWS.index(row)].cells[COLUMNS.index(column)].label
        assert (
            shown
            == aliases.get(actual.operation.value, actual.operation.value)
            == aliases.get(expected, expected)
        ), (row, column, variant, defense_variant)
