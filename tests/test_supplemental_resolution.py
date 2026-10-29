"""Synthetic Milestone 8 resolution of B, QR, QT, and Option branches."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    Defense,
    NormalizedCell,
    Play,
    ResultKind,
    SupplementalColumn,
    TeamChart,
    VariableReference,
)
from bowl_bound.resolution import resolve_play
from tests.test_models import complete_chart, provenance


def cell(kind: ResultKind, yards: int | None = None) -> NormalizedCell:
    return NormalizedCell(kind, provenance(), yards=yards)


def chart_with(
    *,
    ordinary: NormalizedCell,
    defense: NormalizedCell | None = None,
    supplemental: tuple[SupplementalColumn, NormalizedCell] | None = None,
    play: Play = Play.ONE,
) -> tuple[TeamChart, TeamChart]:
    if defense is None:
        defense = cell(ResultKind.NO_CHANGE)
    chart = complete_chart()
    offense = tuple(
        replace(record, cell=ordinary) if record.play is play and record.roll == 10 else record
        for record in chart.offense
    )
    defensive = tuple(
        replace(record, cell=defense)
        if record.play is play and record.defense is Defense.A and record.roll == 1
        else record
        for record in chart.defense
    )
    supplementals = chart.supplemental
    if supplemental is not None:
        column, result = supplemental
        supplementals = tuple(
            replace(record, cell=result)
            if record.column is column and record.roll == 20
            else record
            for record in supplementals
        )
    return replace(chart, offense=offense, supplemental=supplementals), replace(
        chart, name="Synthetic Defense", defense=defensive
    )


@pytest.mark.parametrize(
    ("kind", "column"),
    [
        (ResultKind.BREAKAWAY, SupplementalColumn.BREAKAWAY),
        (ResultKind.QUARTERBACK_RUN, SupplementalColumn.QUARTERBACK_RUN),
        (ResultKind.QUARTERBACK_TRAPPED, SupplementalColumn.QUARTERBACK_TRAPPED),
    ],
)
def test_supplemental_result_uses_its_matching_column_and_records_only_its_reroll(
    kind: ResultKind, column: SupplementalColumn
) -> None:
    offense, defense = chart_with(
        ordinary=cell(kind), supplemental=(column, cell(ResultKind.YARDS, 9))
    )
    first, defensive, supplemental_roll = (
        OffensiveRoll(1, 0, 0),
        DefensiveRoll(1, 0),
        OffensiveRoll(2, 0, 0),
    )
    result = resolve_play(
        offense, defense, Play.ONE, Defense.A, ScriptedDice([first, defensive, supplemental_roll])
    )
    assert result.result.kind is ResultKind.YARDS and result.result.yards == 9
    assert not result.result.pending
    assert [(entry.section, entry.roll, entry.cell) for entry in result.trace] == [
        ("offense", first, cell(kind)),
        ("defense", defensive, cell(ResultKind.NO_CHANGE)),
        ("supplemental:" + column.value, supplemental_roll, cell(ResultKind.YARDS, 9)),
    ]


@pytest.mark.parametrize(
    ("kind", "column"),
    [
        (ResultKind.BREAKAWAY, SupplementalColumn.BREAKAWAY),
        (ResultKind.QUARTERBACK_RUN, SupplementalColumn.QUARTERBACK_RUN),
    ],
)
def test_breakaway_and_qr_add_the_original_defensive_yardage(
    kind: ResultKind, column: SupplementalColumn
) -> None:
    offense, defense = chart_with(
        ordinary=cell(kind),
        defense=cell(ResultKind.YARDS, -3),
        supplemental=(column, cell(ResultKind.YARDS, 11)),
    )
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    result = resolve_play(offense, defense, Play.ONE, Defense.A, dice)
    assert result.result.kind is ResultKind.YARDS and result.result.yards == 8


def test_priority_override_does_not_roll_a_supplemental_column() -> None:
    offense, defense = chart_with(
        ordinary=cell(ResultKind.BREAKAWAY),
        defense=cell(ResultKind.INCOMPLETE),
        supplemental=(SupplementalColumn.BREAKAWAY, cell(ResultKind.YARDS, 9)),
    )
    first, defensive, sentinel = OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)
    dice = ScriptedDice([first, defensive, sentinel])
    result = resolve_play(offense, defense, Play.ONE, Defense.A, dice)
    assert result.result.kind is ResultKind.INCOMPLETE and not result.result.pending
    assert len(result.trace) == 2 and dice.offensive() == sentinel


@pytest.mark.parametrize(
    ("option_kind", "resolved_play"),
    [(ResultKind.SPRINT_OUT_PASS, Play.SEVEN), (ResultKind.BOOTLEG_PASS, Play.EIGHT)],
)
def test_option_cancels_defense_rerolls_under_its_redirected_play(
    option_kind: ResultKind, resolved_play: Play
) -> None:
    offense, defense = chart_with(
        ordinary=cell(option_kind), defense=cell(ResultKind.INTERCEPTION, 17), play=Play.FIVE
    )
    redirected = tuple(
        replace(record, cell=cell(ResultKind.YARDS, 12))
        if record.play is resolved_play and record.roll == 20
        else record
        for record in offense.offense
    )
    offense = replace(offense, offense=redirected)
    first, defensive, reroll = OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)
    result = resolve_play(
        offense, defense, Play.FIVE, Defense.A, ScriptedDice([first, defensive, reroll])
    )
    assert result.called_play is Play.FIVE and result.resolved_play is resolved_play
    assert result.result.kind is ResultKind.YARDS
    assert result.result.yards == 12 and not result.result.pending
    assert [(entry.section, entry.play, entry.formation, entry.roll) for entry in result.trace] == [
        ("offense", Play.FIVE, None, first),
        ("defense", Play.FIVE, Defense.A, defensive),
        ("option", resolved_play, None, reroll),
    ]


def test_option_does_not_roll_or_retain_a_second_defensive_result() -> None:
    offense, defense = chart_with(ordinary=cell(ResultKind.SPRINT_OUT_PASS), play=Play.FIVE)
    redirected = tuple(
        replace(record, cell=cell(ResultKind.YARDS, 12))
        if record.play is Play.SEVEN and record.roll == 20
        else record
        for record in offense.offense
    )
    offense = replace(offense, offense=redirected)
    first, defensive, reroll, sentinel = (
        OffensiveRoll(1, 0, 0),
        DefensiveRoll(1, 0),
        OffensiveRoll(2, 0, 0),
        DefensiveRoll(1, 0),
    )
    dice = ScriptedDice([first, defensive, reroll, sentinel])
    result = resolve_play(offense, defense, Play.FIVE, Defense.A, dice)
    assert len(result.trace) == 3 and dice.defensive() == sentinel


def test_supplemental_variable_result_consumes_and_traces_its_distance_roll() -> None:
    variable = NormalizedCell(
        ResultKind.VARIABLE_DS, provenance(), variable_multiplier=1, variable=VariableReference.DS
    )
    offense, defense = chart_with(
        ordinary=cell(ResultKind.QUARTERBACK_TRAPPED),
        supplemental=(SupplementalColumn.QUARTERBACK_TRAPPED, variable),
    )
    first, defensive, reroll, sentinel = (
        OffensiveRoll(1, 0, 0),
        DefensiveRoll(1, 0),
        OffensiveRoll(2, 0, 0),
        OffensiveRoll(3, 0, 0),
    )
    dice = ScriptedDice([first, defensive, reroll, sentinel])
    result = resolve_play(offense, defense, Play.ONE, Defense.A, dice)
    assert not result.result.pending and result.result.yards == 3
    assert result.result.offense == variable
    assert len(result.trace) == 4 and result.trace[-1].section == "variable:offense"
    assert result.trace[-1].roll == sentinel
    from bowl_bound.dice import DiceSequenceError

    with pytest.raises(DiceSequenceError, match="exhausted"):
        dice.offensive()


def test_qt_discards_original_defensive_yardage_before_its_reroll() -> None:
    offense, defense = chart_with(
        ordinary=cell(ResultKind.QUARTERBACK_TRAPPED),
        defense=cell(ResultKind.YARDS, 6),
        supplemental=(SupplementalColumn.QUARTERBACK_TRAPPED, cell(ResultKind.YARDS, -4)),
    )
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    result = resolve_play(offense, defense, Play.ONE, Defense.A, dice)
    assert result.result.yards == -4 and not result.result.pending


def test_interception_against_defensive_qr_rolls_the_qt_column_not_qr() -> None:
    offense, defense = chart_with(
        ordinary=cell(ResultKind.INTERCEPTION, 20),
        defense=cell(ResultKind.QUARTERBACK_RUN),
        supplemental=(SupplementalColumn.QUARTERBACK_TRAPPED, cell(ResultKind.YARDS, -2)),
    )
    chart_qr = tuple(
        replace(record, cell=cell(ResultKind.YARDS, 99))
        if record.column is SupplementalColumn.QUARTERBACK_RUN
        else record
        for record in offense.supplemental
    )
    offense = replace(offense, supplemental=chart_qr)
    first, defensive, reroll = OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)
    result = resolve_play(
        offense, defense, Play.ONE, Defense.A, ScriptedDice([first, defensive, reroll])
    )
    assert result.result.yards == -2
    assert result.trace[-1].section == "supplemental:QT"


def test_defensive_qr_overrides_offensive_yards_then_rolls_offensive_qr_column() -> None:
    offense, defense = chart_with(
        ordinary=cell(ResultKind.YARDS, -2),
        defense=cell(ResultKind.QUARTERBACK_RUN),
        supplemental=(SupplementalColumn.QUARTERBACK_RUN, cell(ResultKind.YARDS, 7)),
    )
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    result = resolve_play(offense, defense, Play.ONE, Defense.A, dice)
    assert result.result.yards == 7
    assert result.trace[-1].section == "supplemental:QR"


@pytest.mark.parametrize("kind", [ResultKind.INTERCEPTION, ResultKind.FUMBLE, ResultKind.PENALTY])
def test_supplemental_turnover_or_penalty_remains_pending_and_consumes_no_more_dice(
    kind: ResultKind,
) -> None:
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam

    extra = (
        NormalizedCell(kind, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S))
        if kind is ResultKind.PENALTY
        else cell(kind, 5)
    )
    offense, defense = chart_with(
        ordinary=cell(ResultKind.BREAKAWAY),
        supplemental=(SupplementalColumn.BREAKAWAY, extra),
    )
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0), sentinel]
    )
    result = resolve_play(offense, defense, Play.ONE, Defense.A, dice)
    assert result.result.pending and len(result.trace) == 3
    assert dice.offensive() == sentinel


def test_option_result_that_is_qt_continues_into_the_qt_column() -> None:
    offense, defense = chart_with(ordinary=cell(ResultKind.SPRINT_OUT_PASS), play=Play.FIVE)
    offense = replace(
        offense,
        offense=tuple(
            replace(record, cell=cell(ResultKind.QUARTERBACK_TRAPPED))
            if record.play is Play.SEVEN and record.roll == 20
            else record
            for record in offense.offense
        ),
        supplemental=tuple(
            replace(record, cell=cell(ResultKind.YARDS, -6))
            if record.column is SupplementalColumn.QUARTERBACK_TRAPPED and record.roll == 30
            else record
            for record in offense.supplemental
        ),
    )
    rolls = [
        OffensiveRoll(1, 0, 0),
        DefensiveRoll(1, 0),
        OffensiveRoll(2, 0, 0),
        OffensiveRoll(3, 0, 0),
    ]
    result = resolve_play(offense, defense, Play.FIVE, Defense.A, ScriptedDice(rolls))
    assert result.called_play is Play.FIVE and result.resolved_play is Play.SEVEN
    assert result.result.yards == -6
    assert [entry.section for entry in result.trace] == [
        "offense",
        "defense",
        "option",
        "supplemental:QT",
    ]


def test_supplemental_cycle_is_rejected_instead_of_looping() -> None:
    offense, defense = chart_with(
        ordinary=cell(ResultKind.BREAKAWAY),
        supplemental=(SupplementalColumn.BREAKAWAY, cell(ResultKind.BREAKAWAY)),
    )
    offense = replace(
        offense,
        supplemental=tuple(
            replace(record, cell=cell(ResultKind.BREAKAWAY))
            if record.column is SupplementalColumn.BREAKAWAY
            else record
            for record in offense.supplemental
        ),
    )
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)] + [OffensiveRoll(2, 0, 0)] * 20
    with pytest.raises(ValueError, match="supplemental"):
        resolve_play(offense, defense, Play.ONE, Defense.A, ScriptedDice(rolls))
