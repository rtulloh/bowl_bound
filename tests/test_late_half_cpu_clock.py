"""AI-035: synthetic clock conservation, separate from the valid Q1 report."""

import pytest

from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.coaching_session import plan_turn
from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.regulation import RegulationGame
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart
from tests.test_regulation import kickoff, new_game, snap


def scoring_opportunity(quarter: int, side: str, *, own_timeouts: int = 3) -> RegulationGame:
    """A completed third-down rush leaves a public 34-yard field-goal attempt."""
    budgets = (own_timeouts, 3) if side == "home" else (3, own_timeouts)
    game = new_game(clock=Clock(quarter, 30, budgets))
    kickoff(game, "toss:receive" if side == "home" else "toss:kick")
    game._session._field = FieldState(Possession(side), 20, 3, 10)
    snap(game)
    view = game.view()
    assert view.state.down == 4 and view.state.yards_to_goal == 17
    assert view.clock_optional and view.clock.remaining == 30
    assert (f"clock:timeout:{side}" in {choice.id for choice in view.pending.choices}) is (
        own_timeouts > 0
    )
    return game


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("own_timeouts", [0, 3])
def test_current_cpu_preserves_an_offered_field_goal_before_halftime(
    side: str, mode: str, own_timeouts: int
) -> None:
    game = scoring_opportunity(2, side, own_timeouts=own_timeouts)
    before = game.view()
    coach = DifficultyCoach(
        31, team_chart("Home"), team_chart("Away"), mode, version=CURRENT_DIFFICULTY_VERSION
    )
    human = "away" if side == "home" else "home"

    plan = plan_turn(before, human, coach)

    assert game.view() == before
    expected = f"clock:timeout:{side}" if own_timeouts else "clock:hurry"
    assert (plan.operation, plan.arguments) == ("decide", (expected,))


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_first_quarter_does_not_require_a_half_ending_timeout(side: str, mode: str) -> None:
    game = scoring_opportunity(1, side)
    coach = DifficultyCoach(
        31, team_chart("Home"), team_chart("Away"), mode, version=CURRENT_DIFFICULTY_VERSION
    )
    human = "away" if side == "home" else "home"

    plan = plan_turn(game.view(), human, coach)

    assert plan.operation == "kick" and plan.arguments == ("field_goal",)


@pytest.mark.parametrize("side", ["home", "away"])
def test_engine_timeout_preserves_a_real_attempt_before_halftime(side: str) -> None:
    """Prove this is a usable scoring opportunity without sampling future rolls."""
    game = scoring_opportunity(2, side)
    before = game.view()
    game.decide(f"clock:timeout:{side}")
    stopped = game.view()
    assert stopped.clock.quarter == 2 and stopped.clock.remaining == 20
    assert stopped.clock.timeouts == ((2, 3) if side == "home" else (3, 2))
    assert stopped.log == before.log
    assert stopped.timing_log[-1].seconds == 10
    report = game.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert report.called_play == "Field goal attempt"
    assert len(game.view().log) == len(before.log) + 1
    assert game.view().score.home + game.view().score.away == 3


@pytest.mark.parametrize("side", ["home", "away"])
def test_unchanged_v11_attempt_expires_before_any_field_goal_dice(side: str) -> None:
    """Historical behavior is real, versioned evidence; it is not owner-game data."""
    game = scoring_opportunity(2, side)
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "medium", version=11)
    human = "away" if side == "home" else "home"
    plan = plan_turn(game.view(), human, coach)
    assert plan.operation == "kick" and plan.arguments == ("field_goal",)
    before = game.view()
    report = game.kick("field_goal", dice=ScriptedDice([]))
    view = game.view()
    assert report.outcome == "period_boundary" and report.trace == ()
    assert view.log == before.log and view.score == before.score
    assert view.clock.quarter == 3 and view.phase == "kickoff"
    assert view.clock.timeouts == (3, 3)


@pytest.mark.parametrize("side", ["home", "away"])
def test_offered_hurry_without_a_timeout_keeps_the_attempt_legal(side: str) -> None:
    game = scoring_opportunity(2, side, own_timeouts=0)
    assert "clock:hurry" in {choice.id for choice in game.view().pending.choices}
    before = game.view()
    game.decide("clock:hurry")
    assert game.view().clock.quarter == 2 and game.view().clock.remaining == 10
    assert game.view().clock.timeouts == before.clock.timeouts
    report = game.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert report.called_play == "Field goal attempt"
    assert game.view().score.home + game.view().score.away == 3
