"""Synthetic priority and ordinary chart-lookup regressions (no private teams)."""

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
    VariableReference,
)
from bowl_bound.resolution import Operation, Source, resolve_cells, resolve_play
from tests.test_models import complete_chart, provenance


def cell(
    kind: ResultKind = ResultKind.YARDS,
    yards: int | None = 4,
    priority: Priority = Priority.NORMAL,
    out_of_bounds: bool = False,
) -> NormalizedCell:
    return NormalizedCell(
        kind, provenance(), yards=yards, priority=priority, out_of_bounds=out_of_bounds
    )


def test_signed_addition_and_blank_are_not_incompletions() -> None:
    result = resolve_cells(cell(yards=5), cell(yards=-2))
    assert (result.operation, result.source, result.kind, result.yards, result.pending) == (
        Operation.ADD,
        Source.BOTH,
        ResultKind.YARDS,
        3,
        False,
    )
    result = resolve_cells(cell(ResultKind.NO_CHANGE, None), cell(yards=-3))
    assert result.yards == -3 and result.kind is ResultKind.YARDS
    result = resolve_cells(cell(ResultKind.NO_CHANGE, None), cell(ResultKind.NO_CHANGE, None))
    assert result.yards == 0 and not result.pending


def test_parenthesized_offense_overrides_parenthesized_loss_per_chart() -> None:
    result = resolve_cells(
        cell(priority=Priority.PARENTHESIZED), cell(yards=-1, priority=Priority.PARENTHESIZED)
    )
    assert (result.operation, result.source, result.yards) == (Operation.OFFENSE, Source.OFFENSE, 4)


def test_defensive_touchdown_correction_and_interception_exception() -> None:
    defense = cell(ResultKind.TOUCHDOWN, None, Priority.PARENTHESIZED)
    result = resolve_cells(cell(priority=Priority.PARENTHESIZED), defense)
    assert result.source is Source.DEFENSE and result.kind is ResultKind.TOUCHDOWN
    result = resolve_cells(cell(ResultKind.INTERCEPTION, 28), defense)
    assert result.operation is Operation.INCOMPLETE and result.kind is ResultKind.INCOMPLETE
    assert result.yards is None and not result.pending


def test_defensive_parenthesized_breakaway_overrides_and_triggers_offensive_b_column() -> None:
    defensive_breakaway = cell(ResultKind.BREAKAWAY, None, Priority.PARENTHESIZED)
    result = resolve_cells(cell(yards=4), defensive_breakaway)
    assert (result.operation, result.source, result.kind, result.pending) == (
        Operation.DEFENSE,
        Source.DEFENSE,
        ResultKind.BREAKAWAY,
        True,
    )
    parenthesized_offense = cell(yards=4, priority=Priority.PARENTHESIZED)
    result = resolve_cells(parenthesized_offense, defensive_breakaway)
    assert (result.operation, result.source, result.yards) == (
        Operation.OFFENSE,
        Source.OFFENSE,
        4,
    )
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S),
    )
    assert resolve_cells(penalty, defensive_breakaway).operation is Operation.PENALTY

    offense = replace(complete_chart(), name="Synthetic Offense")
    defense_chart = replace(complete_chart(), name="Synthetic Defense")
    target = defense_chart.defense[0]
    defense_chart = replace(
        defense_chart,
        defense=(replace(target, cell=defensive_breakaway), *defense_chart.defense[1:]),
    )
    initial_offense_roll = OffensiveRoll(1, 0, 0)
    initial_defense_roll = DefensiveRoll(1, 0)
    breakaway_roll = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice([initial_offense_roll, initial_defense_roll, breakaway_roll])

    play = resolve_play(offense, defense_chart, Play.ONE, Defense.A, dice)

    assert (play.result.source, play.result.kind, play.result.yards, play.result.pending) == (
        Source.BOTH,
        ResultKind.YARDS,
        1,
        False,
    )
    assert [trace.section for trace in play.trace] == [
        "offense",
        "defense",
        "supplemental:B",
    ]
    assert play.trace[2].team_name == offense.name


@pytest.mark.parametrize("kind", [ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS])
def test_option_branch_cancels_defense_without_inventing_a_reroll(kind: ResultKind) -> None:
    result = resolve_cells(cell(kind, None), cell(ResultKind.INTERCEPTION, 22))
    assert (result.operation, result.source, result.kind, result.pending) == (
        Operation.OPTION,
        Source.OFFENSE,
        kind,
        True,
    )


def test_penalty_is_an_explicit_pending_fact() -> None:
    offense = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S)
    )
    result = resolve_cells(offense, cell(ResultKind.TOUCHDOWN, None, Priority.BRACKETED))
    assert (result.operation, result.kind, result.pending) == (
        Operation.PENALTY,
        ResultKind.PENALTY,
        True,
    )
    assert result.penalty == offense.penalty


@pytest.mark.parametrize(
    "kind", [ResultKind.BREAKAWAY, ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED]
)
def test_supplemental_result_is_pending_not_a_final_zero(kind: ResultKind) -> None:
    result = resolve_cells(cell(kind, None), cell(ResultKind.NO_CHANGE, None))
    assert result.kind is kind and result.yards is None and result.pending


def test_variable_yardage_is_explicitly_pending() -> None:
    variable = NormalizedCell(
        ResultKind.VARIABLE_DS, provenance(), variable=VariableReference.DS, variable_multiplier=1
    )
    result = resolve_cells(variable, cell(yards=-2))
    assert result.operation is Operation.ADD and result.yards is None and result.pending
    assert result.offense == variable


@pytest.mark.parametrize(
    ("kind", "operation"),
    [
        (ResultKind.INTERCEPTION, Operation.INTERCEPTION_MIN),
        (ResultKind.FUMBLE, Operation.FUMBLE_MIN),
    ],
)
@pytest.mark.parametrize(
    ("off_yards", "def_yards", "expected"), [(28, -3, -3), (-5, -2, -5), (-2, -5, -5), (0, -3, -3)]
)
@pytest.mark.parametrize("priority", [Priority.PARENTHESIZED, Priority.BRACKETED])
def test_turnover_location_uses_signed_minimum(
    kind: ResultKind,
    operation: Operation,
    off_yards: int,
    def_yards: int,
    expected: int,
    priority: Priority,
) -> None:
    result = resolve_cells(cell(kind, off_yards), cell(yards=def_yards, priority=priority))
    assert (result.operation, result.kind, result.yards, result.pending) == (
        operation,
        kind,
        expected,
        True,
    )


def test_fumble_at_defensive_location_and_end_zone_remain_structured() -> None:
    result = resolve_cells(
        cell(ResultKind.FUMBLE, 22), cell(yards=4, priority=Priority.PARENTHESIZED)
    )
    assert (result.operation, result.kind, result.yards, result.pending) == (
        Operation.FUMBLE_DEFENSE,
        ResultKind.FUMBLE,
        4,
        True,
    )
    result = resolve_cells(
        cell(ResultKind.FUMBLE, 22), cell(ResultKind.TOUCHDOWN, None, Priority.BRACKETED)
    )
    assert result.operation is Operation.FUMBLE_END_ZONE and result.yards is None and result.pending
    assert result.defensive_end_zone_depth == 1


def test_interception_against_qr_changes_to_qt_without_a_roll() -> None:
    result = resolve_cells(
        cell(ResultKind.INTERCEPTION, 22), cell(ResultKind.QUARTERBACK_RUN, None)
    )
    assert result.kind is ResultKind.QUARTERBACK_TRAPPED and result.pending


def test_bounds_marker_follows_selected_source_not_overruled_cells() -> None:
    result = resolve_cells(cell(out_of_bounds=True), cell(yards=2, priority=Priority.PARENTHESIZED))
    assert not result.out_of_bounds
    result = resolve_cells(cell(out_of_bounds=True), cell(yards=-1))
    assert result.out_of_bounds


def test_lookup_records_only_the_two_actual_rolls_and_cells() -> None:
    offense_chart = complete_chart()
    defensive = replace(offense_chart.defense[0], cell=cell(yards=-2))
    defense_chart = replace(
        offense_chart, name="Synthetic Defense", defense=(defensive, *offense_chart.defense[1:])
    )
    off_roll, def_roll = OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)
    sentinel = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice([off_roll, def_roll, sentinel])
    result = resolve_play(offense_chart, defense_chart, Play.ONE, Defense.A, dice)
    assert result.called_play is result.resolved_play is Play.ONE
    assert result.result.yards == -1 and not result.result.pending
    assert len(result.trace) == 2
    assert result.trace[0].roll == off_roll and result.trace[1].roll == def_roll
    assert (result.trace[0].section, result.trace[1].section) == ("offense", "defense")
    assert result.trace[0].cell == offense_chart.offense[0].cell
    assert result.trace[1].cell == defensive.cell
    assert result.trace[0].team_name == offense_chart.name
    assert result.trace[1].team_name == defense_chart.name
    assert dice.offensive() == sentinel


@pytest.mark.parametrize("bad_play", [1, True, "1", None])
def test_invalid_call_is_rejected_before_consuming_dice(bad_play: object) -> None:
    roll = OffensiveRoll(1, 0, 0)
    dice = ScriptedDice([roll])
    with pytest.raises(TypeError):
        resolve_play(complete_chart(), complete_chart(), bad_play, Defense.A, dice)
    assert dice.offensive() == roll


@pytest.mark.parametrize("bad_defense", ["A", None, 1])
def test_invalid_formation_is_rejected_before_consuming_dice(bad_defense: object) -> None:
    roll = OffensiveRoll(1, 0, 0)
    dice = ScriptedDice([roll])
    with pytest.raises(TypeError):
        resolve_play(complete_chart(), complete_chart(), Play.ONE, bad_defense, dice)
    assert dice.offensive() == roll


@pytest.mark.parametrize(
    "kind", [ResultKind.BLOCKED_KICK, ResultKind.NO_GOOD_FIELD_GOAL, ResultKind.KICKOFF_REFERENCE]
)
def test_special_team_cells_are_not_ordinary_plays(kind: ResultKind) -> None:
    source = cell(kind, 3 if kind is ResultKind.BLOCKED_KICK else None)
    with pytest.raises(ValueError):
        resolve_cells(source, cell())


def test_bracketed_offensive_yardage_is_not_a_printed_chart_row() -> None:
    with pytest.raises(ValueError):
        resolve_cells(cell(priority=Priority.BRACKETED), cell())
