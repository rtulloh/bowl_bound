"""AI-016: version-7 decisions prefer useful legal return and kickoff options."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.coaching_session import plan_turn
from bowl_bound.difficulty import DifficultyCoach
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation
from tests.test_overtime import overtime_game


@pytest.mark.parametrize("side", ["home", "away"])
def test_v7_returns_kicks_unless_protecting_a_large_late_lead(side: str) -> None:
    coach = BaselineCoach(31, version=7)
    return_menu = ("kick:touchback", "kick:return")
    obs = observation(side=side, choices=return_menu)

    assert coach.decision(obs) == "kick:return"
    protecting = replace(
        obs,
        quarter=4,
        remaining=30,
        score_difference=14,
        choices=("kick:return", "kick:fair_catch"),
    )
    assert coach.decision(protecting) == "kick:fair_catch"


@pytest.mark.parametrize("side", ["home", "away"])
def test_v7_selects_kickoff_spot_independent_of_engine_choice_order(side: str) -> None:
    coach = BaselineCoach(31, version=7)
    obs = observation(
        side=side,
        choices=("kick:out_of_bounds:rekick", "kick:out_of_bounds:spot"),
    )

    assert coach.decision(obs) == "kick:out_of_bounds:spot"


def test_v7_does_not_carry_chart_analysis_fallback_into_a_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = overtime_game(2021)
    view = game.view()
    assert view.pending is not None and view.pending.chooser_side is not None
    human_side = "away" if view.pending.chooser_side == "home" else "home"
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard", version=7)
    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(
            key, 32, int(key == "1"), None if key == "1" else 0.0, 0.0, 0.0
        ),
    )
    coach.offense(observation(special=(), game_actions=()))
    assert coach.analysis_fallback

    plan = plan_turn(view, human_side, coach)

    assert plan.computer_choice is not None
    assert not plan.computer_choice.fallback
    assert plan.computer_choice.key in {choice.id for choice in view.pending.choices}
