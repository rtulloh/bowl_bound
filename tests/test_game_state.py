"""Synthetic Milestone 9 game-state transitions (possession, spot, downs, distance).

Only final ordinary outcomes change state. Pending branches are refused, never
treated as zero yards.
"""

import pytest

from bowl_bound.game_state import (
    EndZonePending,
    FieldState,
    Outcome,
    PendingOutcomeError,
    Possession,
    apply_gain,
    apply_incomplete,
    apply_result,
    describe,
    start_drive,
)
from bowl_bound.models import NormalizedCell, ResultKind
from bowl_bound.resolution import Operation, PriorityResult, Source
from tests.test_models import provenance


def result(
    kind: ResultKind,
    yards: int | None = None,
    *,
    pending: bool = False,
) -> PriorityResult:
    cell = NormalizedCell(ResultKind.NO_CHANGE, provenance())
    return PriorityResult(
        Operation.ADD, Source.BOTH, kind, yards, pending, cell, cell, "synthetic", "synthetic"
    )


def test_start_drive_at_midfield_is_first_and_ten() -> None:
    state = start_drive(Possession.HOME, 50)
    assert (state.down, state.yards_to_go, state.yards_to_goal) == (1, 10, 50)
    assert describe(state) == "home: 1st and 10 at midfield"


def test_goal_to_go_applies_when_distance_reaches_the_goal_line() -> None:
    assert describe(start_drive(Possession.AWAY, 7)) == "away: 1st and Goal at opponent 7"
    assert describe(start_drive(Possession.AWAY, 10)) == "away: 1st and Goal at opponent 10"
    assert describe(start_drive(Possession.AWAY, 11)) == "away: 1st and 10 at opponent 11"


def test_own_side_spot_is_described_from_the_own_goal_line() -> None:
    assert describe(start_drive(Possession.HOME, 70)) == "home: 1st and 10 at own 30"


def test_gain_equal_to_distance_is_a_first_down_at_the_new_spot() -> None:
    outcome = apply_gain(start_drive(Possession.HOME, 60), 10)
    assert outcome.outcome is Outcome.FIRST_DOWN
    assert outcome.state == FieldState(Possession.HOME, 50, 1, 10)


def test_short_gain_advances_the_down_and_shrinks_distance() -> None:
    outcome = apply_gain(start_drive(Possession.HOME, 60), 9)
    assert outcome.outcome is Outcome.ADVANCE
    assert outcome.state == FieldState(Possession.HOME, 51, 2, 1)


def test_loss_lengthens_distance_and_moves_the_spot_back() -> None:
    outcome = apply_gain(start_drive(Possession.HOME, 60), -3)
    assert outcome.state == FieldState(Possession.HOME, 63, 2, 13)


@pytest.mark.parametrize("gain", [7, 12])
def test_gain_to_or_past_the_goal_line_is_a_touchdown(gain: int) -> None:
    outcome = apply_gain(start_drive(Possession.HOME, 7), gain)
    assert outcome.outcome is Outcome.TOUCHDOWN
    assert outcome.state is None
    assert outcome.description == "Touchdown for home"


def test_goal_to_go_loss_keeps_the_goal_distance() -> None:
    outcome = apply_gain(start_drive(Possession.HOME, 3), -1)
    assert outcome.state == FieldState(Possession.HOME, 4, 2, 4)
    assert describe(outcome.state) == "home: 2nd and Goal at opponent 4"


def test_fourth_down_failure_hands_the_ball_over_at_the_same_spot() -> None:
    outcome = apply_gain(FieldState(Possession.HOME, 70, 4, 10), 5)
    assert outcome.outcome is Outcome.TURNOVER_ON_DOWNS
    assert outcome.state == FieldState(Possession.AWAY, 35, 1, 10)
    assert describe(outcome.state) == "away: 1st and 10 at opponent 35"


def test_fourth_down_success_is_a_first_down_for_the_same_team() -> None:
    outcome = apply_gain(FieldState(Possession.HOME, 70, 4, 3), 3)
    assert outcome.outcome is Outcome.FIRST_DOWN
    assert outcome.state == FieldState(Possession.HOME, 67, 1, 10)


def test_incomplete_pass_advances_down_without_moving_the_ball() -> None:
    outcome = apply_incomplete(FieldState(Possession.HOME, 60, 2, 10))
    assert outcome.outcome is Outcome.ADVANCE
    assert outcome.state == FieldState(Possession.HOME, 60, 3, 10)


def test_incomplete_pass_on_fourth_down_is_a_turnover_on_downs() -> None:
    outcome = apply_incomplete(FieldState(Possession.HOME, 60, 4, 4))
    assert outcome.outcome is Outcome.TURNOVER_ON_DOWNS
    assert outcome.state == FieldState(Possession.AWAY, 40, 1, 10)


def test_gain_that_reaches_the_own_goal_line_is_refused_not_guessed() -> None:
    with pytest.raises(EndZonePending):
        apply_gain(FieldState(Possession.HOME, 99, 1, 10), -1)


@pytest.mark.parametrize(
    ("possession", "yards_to_goal", "down", "yards_to_go"),
    [
        (Possession.HOME, 0, 1, 1),
        (Possession.HOME, 100, 1, 10),
        (Possession.HOME, 50, 0, 10),
        (Possession.HOME, 50, 5, 10),
        (Possession.HOME, 50, 1, 0),
        (Possession.HOME, 10, 1, 11),
        ("home", 50, 1, 10),
        (Possession.HOME, True, 1, 10),
    ],
)
def test_invalid_field_states_are_rejected(
    possession: object, yards_to_goal: object, down: int, yards_to_go: int
) -> None:
    with pytest.raises((TypeError, ValueError)):
        FieldState(possession, yards_to_goal, down, yards_to_go)  # type: ignore[arg-type]


def test_every_legal_ordinary_gain_keeps_the_state_invariants() -> None:
    for yards_to_goal in range(1, 100):
        for down in range(1, 5):
            for yards_to_go in {1, min(10, yards_to_goal), yards_to_goal}:
                state = FieldState(Possession.HOME, yards_to_goal, down, yards_to_go)
                for gain in range(-9, 41):
                    if yards_to_goal - gain >= 100:
                        with pytest.raises(EndZonePending):
                            apply_gain(state, gain)
                        continue
                    outcome = apply_gain(state, gain)
                    if gain >= yards_to_goal:
                        assert outcome.outcome is Outcome.TOUCHDOWN and outcome.state is None
                        continue
                    new = outcome.state
                    assert new is not None
                    assert 1 <= new.yards_to_goal <= 99
                    assert 1 <= new.down <= 4
                    assert 1 <= new.yards_to_go <= new.yards_to_goal
                    if outcome.outcome is Outcome.TURNOVER_ON_DOWNS:
                        assert new.possession is Possession.AWAY
                        assert new.yards_to_goal == 100 - (yards_to_goal - gain)
                    else:
                        assert new.possession is Possession.HOME


def test_only_final_ordinary_results_change_state() -> None:
    start = FieldState(Possession.HOME, 60, 1, 10)
    assert apply_result(start, result(ResultKind.YARDS, 4)).state == FieldState(
        Possession.HOME, 56, 2, 6
    )
    assert apply_result(start, result(ResultKind.INCOMPLETE)).outcome is Outcome.ADVANCE
    assert apply_result(start, result(ResultKind.TOUCHDOWN)).outcome is Outcome.TOUCHDOWN


@pytest.mark.parametrize(
    "pending_result",
    [
        result(ResultKind.INTERCEPTION, None, pending=True),
        result(ResultKind.FUMBLE, 5, pending=True),
        result(ResultKind.VARIABLE_DS, None, pending=True),
        result(ResultKind.PENALTY, None, pending=True),
        result(ResultKind.BREAKAWAY, None, pending=True),
    ],
)
def test_pending_results_are_refused_rather_than_treated_as_zero(
    pending_result: PriorityResult,
) -> None:
    with pytest.raises(PendingOutcomeError):
        apply_result(FieldState(Possession.HOME, 60, 1, 10), pending_result)
