"""Synthetic chart book semantics, ordering and privacy."""

from dataclasses import asdict, replace

from bowl_bound.chart_view import chart_book
from bowl_bound.models import ChartColor, NormalizedCell, Play, Priority, ResultKind
from tests.synthetic_teams import team_chart
from tests.test_models import provenance


def test_complete_ordered_grids_even_when_records_are_reversed() -> None:
    chart = team_chart("Synthetic College")
    chart = replace(chart, offense=chart.offense[::-1], defense=chart.defense[::-1])
    book = chart_book(chart)
    assert book.team == "Synthetic College" and book.season == 2026
    assert [column.key for column in book.offense.columns] == [str(i) for i in range(1, 10)] + [
        "B",
        "QR",
        "QT",
    ]
    assert [row.label for row in book.offense.rows] == [str(i) for i in range(10, 40)]
    assert all(len(row.cells) == 12 for row in book.offense.rows)
    assert [row.label for row in book.defense.rows] == [
        f"{d} · {i}" for d in "ABCDEF" for i in range(1, 6)
    ]
    assert all(len(row.cells) == 9 for row in book.defense.rows)


def test_semantic_text_colors_and_no_source_evidence() -> None:
    chart = team_chart("Synthetic College")
    cells = [
        NormalizedCell(ResultKind.NO_CHANGE, provenance(), chart_color=ChartColor.WHITE),
        NormalizedCell(
            ResultKind.YARDS,
            provenance(),
            yards=-3,
            priority=Priority.BRACKETED,
            out_of_bounds=True,
            chart_color=ChartColor.RED,
        ),
        NormalizedCell(ResultKind.INCOMPLETE, provenance(), chart_color=ChartColor.BLACK),
        NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20, chart_color=ChartColor.RED),
    ]
    chart = replace(
        chart,
        offense=tuple(
            replace(r, cell=cells[r.play.value - 1]) if r.play.value <= 4 else r
            for r in chart.offense
        ),
    )
    row = chart_book(chart).offense.rows[0]
    assert [(c.label, c.color) for c in row.cells[:4]] == [
        ("", "white"),
        ("[-3]*", "red"),
        ("INC", "black"),
        ("INT 20", "red"),
    ]
    assert "out of bounds" in row.cells[1].description
    assert "interception" in row.cells[3].description.lower()
    payload = str(asdict(chart_book(chart)))
    assert "provenance" not in payload and "source_hash" not in payload
    assert "rgb_color" not in payload and "filename" not in payload
    assert "chart reference" in chart_book(chart).note.lower()


def test_unknown_color_is_explicit_and_zero_yard_markers_are_preserved() -> None:
    chart = team_chart("Synthetic College")
    cell = NormalizedCell(
        ResultKind.YARDS, provenance(), yards=0, priority=Priority.PARENTHESIZED, out_of_bounds=True
    )
    chart = replace(
        chart,
        offense=tuple(replace(r, cell=cell) if r.play is Play.ONE else r for r in chart.offense),
    )
    shown = chart_book(chart).offense.rows[0].cells[0]
    assert shown.label == "(0)*" and shown.color == "unclassified"


def test_no_change_out_of_bounds_marker_is_preserved() -> None:
    chart = team_chart("Synthetic College")
    cell = NormalizedCell(
        ResultKind.NO_CHANGE, provenance(), out_of_bounds=True, chart_color=ChartColor.WHITE
    )
    chart = replace(chart, offense=tuple(replace(record, cell=cell) for record in chart.offense))
    assert chart_book(chart).offense.rows[0].cells[0].label == "0*"


def test_ordinary_zero_is_blank_white_and_priority_zero_stays_visible() -> None:
    chart = team_chart("Synthetic College")
    zero = NormalizedCell(ResultKind.YARDS, provenance(), yards=0, chart_color=ChartColor.GREEN)
    fields = (
        zero,
        replace(zero, priority=Priority.PARENTHESIZED),
        replace(zero, out_of_bounds=True),
    )
    chart = replace(
        chart,
        defense=tuple(
            replace(record, cell=fields[record.play.value - 1])
            if record.play.value <= 3
            else record
            for record in chart.defense
        ),
    )
    row = chart_book(chart).defense.rows[0]
    assert [(c.label, c.color) for c in row.cells[:3]] == [
        ("", "white"),
        ("(0)", "green"),
        ("0*", "green"),
    ]
    assert row.cells[0].description == "No yardage adjustment"


def test_scrimmage_legend_explains_colors_and_individual_result_codes() -> None:
    book = chart_book(team_chart("Synthetic College"))
    colors = {entry.color: entry.description for entry in book.legend}
    assert "positive yards" in colors["green"]
    assert "negative yards" in colors["red"]
    assert "no yardage adjustment" in colors["white"]
    codes = {entry.label: entry.description for entry in book.symbols}
    for label, meaning in {
        "B": "Breakaway",
        "QR": "Quarterback run",
        "QT": "Quarterback trapped",
        "SOP": "Sprint Out",
        "BLP": "Boot-leg",
    }.items():
        assert meaning in codes[label]
