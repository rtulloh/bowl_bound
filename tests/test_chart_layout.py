"""Original-board presentation is explicit engine-owned metadata."""

from bowl_bound.chart_view import chart_book
from bowl_bound.models import Defense
from bowl_bound.session import DEFENSE_LABELS, PLAY_LABELS
from tests.synthetic_teams import team_chart


def test_chart_groups_keep_bowl_bound_plays_option_and_supplemental_separate() -> None:
    book = chart_book(team_chart("Synthetic College"))
    for table in (book.offense, book.defense):
        assert [(g.label, g.start, g.count) for g in table.column_groups[:3]] == [
            ("Running Plays", 0, 4),
            ("Option", 4, 1),
            ("Passing Plays", 5, 4),
        ]
        assert [c.number for c in table.columns[:9]] == list(map(str, range(1, 10)))
        assert [c.name for c in table.columns[:9]] == list(PLAY_LABELS.values())
    assert [(g.key, g.start, g.count, g.separate) for g in book.offense.column_groups[3:]] == [
        ("supplemental", 9, 3, True)
    ]
    assert [c.number for c in book.offense.columns[9:]] == ["B", "QR", "QT"]
    assert [r.dice_label for r in book.offense.rows] == list(map(str, range(10, 40)))


def test_defense_groups_have_explicit_letter_name_span_and_dice_labels() -> None:
    table = chart_book(team_chart("Synthetic College")).defense
    assert table.group_label == "Formation"
    assert [(g.key, g.label, g.start, g.count) for g in table.row_groups] == [
        (d.value, DEFENSE_LABELS[d], i * 5, 5) for i, d in enumerate(Defense)
    ]
    assert [r.dice_label for r in table.rows] == list(map(str, range(1, 6))) * 6
    assert table.rows[0].label == "A · 1"
    assert table.rows[-1].label == "F · 5"
