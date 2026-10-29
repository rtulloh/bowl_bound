"""Every printed Priority Chart intersection, using an independent transcription.

This file tests the pure chart (``resolve_cells``). Rolls consumed by supplemental and
Option branches are covered in ``test_supplemental_resolution.py``.
"""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    Defense,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    Priority,
    ResultKind,
)
from bowl_bound.resolution import Operation, resolve_cells, resolve_play
from tests.priority_matrix import COLUMNS, PRIORITY_MATRIX, ROWS
from tests.test_models import complete_chart, provenance


def sample(label: str, variant: str = "") -> NormalizedCell:
    """Synthetic representatives chosen independently of the production classifier."""
    values = {
        "positive_yards_or_breakaway": (ResultKind.YARDS, 7, Priority.NORMAL),
        "positive_yards": (ResultKind.YARDS, 4, Priority.NORMAL),
        "negative_yards": (ResultKind.YARDS, -3, Priority.NORMAL),
        "blank": (ResultKind.NO_CHANGE, None, Priority.NORMAL),
        "parenthesized_positive": (ResultKind.YARDS, 6, Priority.PARENTHESIZED),
        "parenthesized_negative": (ResultKind.YARDS, -2, Priority.PARENTHESIZED),
        "bracketed_positive": (ResultKind.YARDS, 8, Priority.BRACKETED),
        "bracketed_negative": (ResultKind.YARDS, -5, Priority.BRACKETED),
        "touchdown": (ResultKind.TOUCHDOWN, None, Priority.NORMAL),
        "quarterback_run": (ResultKind.QUARTERBACK_RUN, None, Priority.NORMAL),
        "quarterback_trapped": (ResultKind.QUARTERBACK_TRAPPED, None, Priority.NORMAL),
        "interception": (ResultKind.INTERCEPTION, 12, Priority.NORMAL),
        "fumble": (ResultKind.FUMBLE, 9, Priority.NORMAL),
        "incomplete": (ResultKind.INCOMPLETE, None, Priority.NORMAL),
        "sprint_out_or_bootleg_pass": (ResultKind.SPRINT_OUT_PASS, None, Priority.NORMAL),
    }
    if label == "penalty":
        return NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S),
        )
    kind, yards, priority = values[label]
    if variant == "B":
        kind, yards = ResultKind.BREAKAWAY, None
    if variant == "BLP":
        kind = ResultKind.BOOTLEG_PASS
    if variant == "parenthesized":
        priority = Priority.PARENTHESIZED
    if variant == "bracketed":
        priority = Priority.BRACKETED
    return NormalizedCell(kind, provenance(), yards=yards, priority=priority)


def coordinates() -> list[object]:
    result = []
    for row, label in enumerate(ROWS):
        variants = ("", "B") if row == 0 else (("", "BLP") if row == 10 else ("",))
        for col, defensive in enumerate(COLUMNS):
            def_variants = ("parenthesized", "bracketed") if col == 7 else ("",)
            for variant in variants:
                for dv in def_variants:
                    result.append(
                        pytest.param(
                            label,
                            defensive,
                            variant,
                            dv,
                            PRIORITY_MATRIX[row][col],
                            id=f"r{row + 1}:{label}{variant}-c{col + 1}:{defensive}{dv}",
                        )
                    )
    return result


@pytest.mark.parametrize(("row", "column", "variant", "def_variant", "code"), coordinates())
def test_every_priority_chart_intersection(
    row: str, column: str, variant: str, def_variant: str, code: str
) -> None:
    offense, defense = sample(row, variant), sample(column, def_variant)
    result = resolve_cells(offense, defense)
    assert result.operation.value == code
    selected = {"O": offense, "D": defense, "OPTION": offense, "PENALTY": offense}.get(code)
    if selected is not None:
        assert result.source.value == ("defense" if code == "D" else "offense")
        assert result.kind is selected.kind and result.yards == selected.yards
        assert result.penalty == selected.penalty
        assert result.pending == (
            selected.kind
            not in {
                ResultKind.YARDS,
                ResultKind.NO_CHANGE,
                ResultKind.INCOMPLETE,
                ResultKind.TOUCHDOWN,
            }
        )
    elif code == "ADD":
        assert result.source.value == "both"
        if offense.kind in {ResultKind.BREAKAWAY, ResultKind.QUARTERBACK_RUN}:
            assert result.kind is offense.kind and result.yards is None and result.pending
        else:
            assert result.kind is ResultKind.YARDS and result.yards == (offense.yards or 0) + (
                defense.yards or 0
            )
            assert not result.pending
    elif code in {"INC", "QT"}:
        assert result.source.value == "priority_chart"
        assert result.kind is (
            ResultKind.INCOMPLETE if code == "INC" else ResultKind.QUARTERBACK_TRAPPED
        )
        assert result.pending == (code == "QT") and result.yards is None
    else:
        assert result.source.value == "both" and result.pending
        assert result.kind is (ResultKind.INTERCEPTION if code == "INT_MIN" else ResultKind.FUMBLE)
        if code == "F_ENDZONE":
            assert result.yards is None and result.defensive_end_zone_depth == 1
        elif code == "F_DEF":
            assert result.yards == defense.yards
        else:
            assert result.yards == min(offense.yards, defense.yards)


def test_expected_matrix_is_complete_and_has_no_skipped_coordinates() -> None:
    assert len(ROWS) == 12 and len(COLUMNS) == 13
    assert len(PRIORITY_MATRIX) == 12 and all(len(row) == 13 for row in PRIORITY_MATRIX)
    assert len(coordinates()) == 196


_BRANCHING = {ResultKind.BREAKAWAY, ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED}


@pytest.mark.parametrize(("row", "column", "variant", "def_variant", "code"), coordinates())
def test_dice_and_trace_use_at_every_coordinate(
    row: str, column: str, variant: str, def_variant: str, code: str
) -> None:
    """Two initial rolls; exactly one extra offensive roll only for B/QR/QT/Option."""
    offense, defense = sample(row, variant), sample(column, def_variant)
    chart = complete_chart()  # synthetic supplemental/Play 7/8 cells are plain yards
    off_chart = replace(
        chart,
        offense=tuple(
            replace(x, cell=offense) if x.play is Play.FIVE and x.roll == 10 else x
            for x in chart.offense
        ),
    )
    def_chart = replace(
        chart,
        name="Synthetic Defense",
        defense=tuple(
            replace(x, cell=defense)
            if x.play is Play.FIVE and x.defense is Defense.A and x.roll == 1
            else x
            for x in chart.defense
        ),
    )
    pure = resolve_cells(offense, defense)
    extra = 1 if pure.operation is Operation.OPTION or pure.kind in _BRANCHING else 0
    off_roll, def_roll = OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)
    extra_rolls = [OffensiveRoll(1, 0, 0)] * extra
    sentinel = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice([off_roll, def_roll, *extra_rolls, sentinel])
    play = resolve_play(off_chart, def_chart, Play.FIVE, Defense.A, dice)
    assert len(play.trace) == 2 + extra
    assert [(x.section, x.roll, x.cell) for x in play.trace[:2]] == [
        ("offense", off_roll, offense),
        ("defense", def_roll, defense),
    ]
    assert play.called_play is Play.FIVE
    assert (play.resolved_play is not Play.FIVE) == (pure.operation is Operation.OPTION)
    assert play.result.kind not in _BRANCHING
    assert dice.offensive() == sentinel
