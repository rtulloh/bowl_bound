"""Turnover resolution uses synthetic charts only (Basic VI-9, VI-10 and VI-13)."""

from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    VariableReference,
)
from bowl_bound.turnovers import (
    EndZoneResult,
    TurnoverOutcome,
    resolve_fumble,
    resolve_interception,
    resolve_turnover_location,
)
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


def chart_with_return(name: str, return_cell: NormalizedCell, *, recovery_range: range) -> object:
    """Build a complete synthetic chart whose interception-return column has one forced cell."""
    chart = team_chart(name)
    return replace(
        chart,
        special_teams=tuple(
            SpecialTeamsCell(
                cell.column,
                cell.roll,
                return_cell if cell.column is SpecialTeamsColumn.INTERCEPTION_RETURN else cell.cell,
            )
            for cell in chart.special_teams
        ),
        recovery_range=recovery_range,
    )


def test_defensive_recovery_returns_a_fumble_from_its_actual_spot() -> None:
    fumbler = chart_with_return("Home", yards(0), recovery_range=range(10, 20))
    defender = chart_with_return("Away", yards(12), recovery_range=range(10, 20))
    result = resolve_fumble(
        FieldState(Possession.HOME, 65, 2, 8),
        location=5,
        fumbler=fumbler,
        opponent=defender,
        dice=ScriptedDice([OffensiveRoll(3, 4, 3), OffensiveRoll(1, 1, 0)]),
    )
    assert result.outcome is TurnoverOutcome.DEFENSIVE_RECOVERY
    assert result.state == FieldState(Possession.AWAY, 28, 1, 10)
    assert [entry.section for entry in result.trace] == ["fumble_recovery", "turnover_return"]


def test_offense_recovers_and_returns_only_on_the_designated_recovery_totals() -> None:
    home = chart_with_return("Home", yards(9), recovery_range=range(10, 40))
    away = chart_with_return("Away", yards(0), recovery_range=range(10, 40))
    result = resolve_fumble(
        FieldState(Possession.HOME, 55, 2, 7),
        location=4,
        fumbler=home,
        opponent=away,
        dice=ScriptedDice([OffensiveRoll(1, 4, 3), OffensiveRoll(1, 1, 0)]),
    )
    assert result.outcome is TurnoverOutcome.OFFENSIVE_RECOVERY
    assert result.state == FieldState(Possession.HOME, 42, 1, 10)
    assert [entry.section for entry in result.trace] == ["fumble_recovery", "turnover_return"]


def test_interception_can_be_declared_incomplete_without_a_return_roll() -> None:
    away = chart_with_return("Away", yards(18), recovery_range=range(10, 40))
    result = resolve_interception(
        FieldState(Possession.HOME, 65, 2, 8),
        location=20,
        interceptor=away,
        choice="decline",
        dice=ScriptedDice([]),
    )
    assert result.outcome is TurnoverOutcome.DECLINED_INTERCEPTION
    assert result.state == FieldState(Possession.HOME, 65, 3, 8)
    assert result.trace == ()


def test_interception_return_that_reaches_the_goal_scores_and_awards_six_points() -> None:
    away = chart_with_return("Away", yards(55), recovery_range=range(10, 40))
    result = resolve_interception(
        FieldState(Possession.HOME, 65, 2, 8),
        location=20,
        interceptor=away,
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 1, 0)]),
    )
    assert result.outcome is TurnoverOutcome.DEFENSIVE_TOUCHDOWN
    assert result.end_zone is EndZoneResult.TOUCHDOWN
    assert result.state is None and result.points == (0, 6)


def test_defensive_end_zone_recovery_requires_an_explicit_touchback_or_return_choice() -> None:
    home = chart_with_return("Home", yards(0), recovery_range=range(10, 20))
    away = chart_with_return("Away", yards(0), recovery_range=range(10, 20))
    result = resolve_fumble(
        FieldState(Possession.HOME, 5, 2, 3),
        location=8,
        fumbler=home,
        opponent=away,
        dice=ScriptedDice([OffensiveRoll(3, 4, 3)]),
    )
    assert result.outcome is TurnoverOutcome.END_ZONE_RETURN_PENDING
    assert result.end_zone is EndZoneResult.TOUCHBACK and result.end_zone_recovery


@pytest.mark.parametrize("choice", ["", "punt", "RETURN"])
def test_interception_rejects_unknown_choices(choice: str) -> None:
    with pytest.raises(ValueError, match="choice"):
        resolve_interception(
            FieldState(Possession.HOME, 65, 2, 8),
            location=20,
            interceptor=team_chart("Away"),
            choice=choice,
            dice=ScriptedDice([]),
        )


def test_a_return_fumble_starts_another_recovery_and_return_chain() -> None:
    return_fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5)
    home = chart_with_return("Home", yards(7), recovery_range=range(10, 20))
    away = chart_with_return("Away", return_fumble, recovery_range=range(10, 20))
    result = resolve_interception(
        FieldState(Possession.HOME, 65, 2, 8),
        location=20,
        interceptor=away,
        opponent=home,
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 1, 0), OffensiveRoll(3, 4, 3), OffensiveRoll(1, 1, 0)]),
    )
    assert result.outcome is TurnoverOutcome.DEFENSIVE_RECOVERY
    assert result.state == FieldState(Possession.HOME, 43, 1, 10)
    assert [entry.section for entry in result.trace] == [
        "turnover_return",
        "fumble_recovery",
        "turnover_return",
    ]


def test_offensive_recovery_return_keeps_the_original_down_when_it_is_short() -> None:
    home = chart_with_return("Home", yards(1), recovery_range=range(10, 40))
    away = chart_with_return("Away", yards(0), recovery_range=range(10, 40))
    result = resolve_fumble(
        FieldState(Possession.HOME, 55, 2, 7),
        location=0,
        fumbler=home,
        opponent=away,
        dice=ScriptedDice([OffensiveRoll(1, 4, 3), OffensiveRoll(1, 1, 0)]),
    )
    assert result.outcome is TurnoverOutcome.OFFENSIVE_RECOVERY
    assert result.state == FieldState(Possession.HOME, 54, 3, 6)


def test_a_return_penalty_rerolls_the_return_and_keeps_enforcement_facts() -> None:
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, yards=10),
    )
    chart = team_chart("Away")
    away = replace(
        chart,
        special_teams=tuple(
            SpecialTeamsCell(
                record.column,
                record.roll,
                penalty
                if record.column is SpecialTeamsColumn.INTERCEPTION_RETURN and record.roll == 10
                else yards(52)
                if record.column is SpecialTeamsColumn.INTERCEPTION_RETURN and record.roll == 11
                else record.cell,
            )
            for record in chart.special_teams
        ),
    )
    result = resolve_interception(
        FieldState(Possession.HOME, 33, 2, 8),
        location=20,
        interceptor=away,
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]),
    )
    assert result.return_penalty is not None and result.return_penalty.yards == 10
    assert result.return_start == FieldState(Possession.AWAY, 87, 1, 10)
    assert result.return_yards == 52
    assert [entry.section for entry in result.trace] == [
        "turnover_return",
        "turnover_return_reroll",
    ]


def test_variable_turnover_locations_use_their_documented_offensive_dice_values() -> None:
    cell = NormalizedCell(
        ResultKind.INTERCEPTION,
        provenance(),
        variable=VariableReference.DS,
        variable_multiplier=1,
    )
    result = resolve_turnover_location(
        cell, team_chart("Home"), ScriptedDice([OffensiveRoll(3, 2, 4)])
    )
    assert result.location == 9
    assert [entry.section for entry in result.trace] == ["turnover_location"]
    assert result.trace[0].roll == OffensiveRoll(3, 2, 4)


def test_variable_turnover_location_t2_sums_two_roll_totals_and_preserves_sign() -> None:
    cell = NormalizedCell(
        ResultKind.FUMBLE,
        provenance(),
        variable=VariableReference.T2,
        variable_multiplier=-1,
    )
    result = resolve_turnover_location(
        cell,
        team_chart("Home"),
        ScriptedDice([OffensiveRoll(1, 2, 3), OffensiveRoll(2, 3, 4)]),
    )
    assert result.location == -42
    assert [entry.roll.total for entry in result.trace] == [15, 27]
