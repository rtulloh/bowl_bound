"""Synthetic Special Teams view facts, including the separate loaded PAT outcomes."""

from dataclasses import asdict, replace

from bowl_bound.chart_view import chart_book
from bowl_bound.models import SpecialTeamsColumn, TeamChart
from bowl_bound.normalization import CELL_LEGEND, ChartColor, chart_color_for_csv_token
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance

SPECIAL_COLUMNS = (
    (SpecialTeamsColumn.KICKOFF, "Kickoff"),
    (SpecialTeamsColumn.KICKOFF_RETURN, "Kickoff return"),
    (SpecialTeamsColumn.PUNT, "Punt"),
    (SpecialTeamsColumn.PUNT_RETURN, "Punt return"),
    (SpecialTeamsColumn.INTERCEPTION_RETURN, "Interception return"),
    (SpecialTeamsColumn.FIELD_GOAL, "Field goal"),
)


def special_view_chart(name: str, base: int = 0) -> TeamChart:
    """Give every loaded special coordinate a distinct public synthetic value."""
    chart = team_chart(name)
    positions = {column: index for index, (column, _) in enumerate(SPECIAL_COLUMNS)}
    return replace(
        chart,
        special_teams=tuple(
            replace(
                record,
                cell=parse_cell(
                    str(base + positions[record.column] * 100 + record.roll),
                    replace(provenance(), rgb_color=CELL_LEGEND[ChartColor.GREEN].rgb_color),
                ),
            )
            for record in chart.special_teams
        ),
        pat_outcomes=tuple(
            replace(
                outcome,
                good=(outcome.roll + base) % 3 != 1,
                provenance=replace(
                    provenance(),
                    original_text="" if (outcome.roll + base) % 3 != 1 else "NG",
                    rgb_color=(255, 255, 255) if (outcome.roll + base) % 3 != 1 else (255, 0, 0),
                ),
            )
            for outcome in chart.pat_outcomes
        ),
    )


def test_special_view_orders_every_loaded_cell_and_pat_without_source_evidence() -> None:
    chart = special_view_chart("Synthetic Special College")
    chart = replace(
        chart, special_teams=chart.special_teams[::-1], pat_outcomes=chart.pat_outcomes[::-1]
    )
    before = asdict(chart)
    book = chart_book(chart)
    table = book.special_teams
    assert table.key == "special_teams" and table.title == "Special Teams"
    assert [column.key for column in table.columns] == [
        *(column.value for column, _ in SPECIAL_COLUMNS),
        "pat",
    ]
    assert {column for column, _ in SPECIAL_COLUMNS} == set(SpecialTeamsColumn)
    assert [column.label.casefold() for column in table.columns] == [
        *(label.casefold() for _, label in SPECIAL_COLUMNS),
        "extra point",
    ]
    assert [row.label for row in table.rows] == [str(roll) for roll in range(10, 40)]
    for row, roll in zip(table.rows, range(10, 40), strict=True):
        assert len(row.cells) == 7
        assert [(cell.label, cell.color) for cell in row.cells[:6]] == [
            (str(index * 100 + roll), "green") for index in range(6)
        ]
        good = roll % 3 != 1
        assert (row.cells[6].label, row.cells[6].color) == (
            ("GOOD", "green") if good else ("NG", "red")
        )
        assert "point" in row.cells[6].description.casefold()
    assert asdict(chart) == before
    payload = str(asdict(book))
    assert all(
        forbidden not in payload
        for forbidden in ("provenance", "source_sha256", "filename", "rgb_color", "synthetic.pdf")
    )


def test_special_markers_keep_section_meanings_and_normalized_colors() -> None:
    chart = special_view_chart("Synthetic Special College")
    examples = {
        (SpecialTeamsColumn.KICKOFF, 10): ("*", "0*", "white"),
        (SpecialTeamsColumn.KICKOFF_RETURN, 11): ("F - 2", "F - 2", "red"),
        (SpecialTeamsColumn.PUNT, 12): ("FG", "FG", "red"),
        (SpecialTeamsColumn.PUNT, 13): ("KO*", "KO*", "green"),
        (SpecialTeamsColumn.PUNT, 14): ("BK -3", "BK -3", "red"),
        (SpecialTeamsColumn.PUNT_RETURN, 15): ("BLACK", "BLACK", "black"),
        (SpecialTeamsColumn.FIELD_GOAL, 16): ("NG", "NG", "red"),
        (SpecialTeamsColumn.FIELD_GOAL, 17): ("34", "34", "green"),
        (SpecialTeamsColumn.INTERCEPTION_RETURN, 18): ("-DS*", "-DS*", "red"),
        (SpecialTeamsColumn.KICKOFF, 19): ("OFF 5", "OFF 5", "yellow"),
        (SpecialTeamsColumn.KICKOFF_RETURN, 20): ("(TD)", "(TD)", "green"),
        (SpecialTeamsColumn.PUNT_RETURN, 21): ("0", "0", "green"),
    }
    records = []
    for record in chart.special_teams:
        example = examples.get((record.column, record.roll))
        if example is None:
            records.append(record)
            continue
        token = example[0]
        color = chart_color_for_csv_token(token)
        evidence = replace(
            provenance(), original_text=token, rgb_color=CELL_LEGEND[color].rgb_color
        )
        records.append(replace(record, cell=parse_cell(token, evidence)))
    chart = replace(chart, special_teams=tuple(records))
    table = chart_book(chart).special_teams
    index = {column.key: position for position, column in enumerate(table.columns)}
    for (column, roll), (_, label, color) in examples.items():
        cell = table.rows[roll - 10].cells[index[column.value]]
        assert (cell.label, cell.color) == (label, color)
        assert cell.description
    black = table.rows[5].cells[index[SpecialTeamsColumn.PUNT_RETURN.value]]
    assert "incomplete pass" not in black.description.casefold()
    assert "procedure" in black.description.casefold()
    assert "special teams" in black.description.casefold().replace("-", " ")
    no_good = table.rows[6].cells[index[SpecialTeamsColumn.FIELD_GOAL.value]]
    assert "no good" in no_good.description.casefold()


def test_special_help_is_section_specific_including_black_and_extra_points() -> None:
    table = chart_book(special_view_chart("Synthetic College")).special_teams
    help_text = " ".join(entry.description for entry in (*table.legend, *table.symbols)).lower()
    assert "incomplete pass" not in help_text
    assert "procedure" in help_text and "extra point" in help_text
    assert {entry.label for entry in table.legend} == {"Green", "Red", "White", "Black", "Yellow"}
