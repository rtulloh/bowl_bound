"""Versioned coaching access to Bowl Bound Advanced II defenses."""

from dataclasses import replace

import pytest

from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_evaluation import evaluate_action
from bowl_bound.coaching_session import observe_policy, plan_turn
from bowl_bound.coaching_situations import situation_bucket
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import Play
from bowl_bound.save_game import SavedGame
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_coaching import observation


def test_v8_keeps_legacy_defense_menu() -> None:
    home, away = default_teams()
    session = PlaySession.new(
        home,
        away,
        seed=41,
        start_yards_to_goal=15,
        advanced_ii=True,
        away_privileges=("W",),
    )

    legacy = plan_turn(session.view(), "home", BaselineCoach(9, version=8))
    assert legacy.computer_choice is not None
    assert legacy.computer_choice.key in "ABCDEF"


@pytest.mark.parametrize("mode", ["baseline", "easy", "medium", "hard", "chart"])
def test_v9_coaches_see_legal_advanced_ii_calls_without_exposing_them(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, away = default_teams()
    session = PlaySession.new(
        home,
        away,
        seed=41,
        start_yards_to_goal=15,
        advanced_ii=True,
        away_privileges=("W",),
    )
    coach = (
        BaselineCoach(9, version=9)
        if mode == "baseline"
        else ChartAwareCoach(9, home, away, version=9)
        if mode == "chart"
        else DifficultyCoach(9, home, away, mode, version=9)
    )
    seen = []
    monkeypatch.setattr(coach, "defense", lambda view: seen.append(view) or "RUN")

    plan = plan_turn(session.view(), "home", coach)

    assert seen[0].advanced_ii and seen[0].free_advanced_defense
    assert {"RUN", "PASS", "NICKEL", "REDZONE", "WC1", "WCSNEAK"} <= set(seen[0].defense)
    assert plan.computer_choice is not None and plan.computer_choice.key == "RUN"
    assert plan.turn.actions.defense == ()


def test_advanced_action_metadata_exposes_free_and_conditional_eligibility() -> None:
    home, away = default_teams()
    free = PlaySession.new(home, away, seed=41, advanced_ii=True, away_privileges=("W",)).view()
    conditional = PlaySession.new(home, away, seed=41, advanced_ii=True).view()
    free_calls = {action.key: action for action in free.actions.defense}
    conditional_calls = {action.key: action for action in conditional.actions.defense}

    assert free_calls["WC1"].free_advanced and free_calls["RUN"].free_advanced
    assert not free_calls["NICKEL"].free_advanced
    assert not conditional_calls["WC1"].free_advanced
    assert not conditional_calls["RUN"].free_advanced


@pytest.mark.parametrize(("policy", "include_advanced"), [("hard-v8", False), ("hard-v9", True)])
def test_saved_coach_history_uses_its_versioned_advanced_action_set(
    policy: str, include_advanced: bool
) -> None:
    home, away = default_teams()
    game = SavedGame.new(
        home,
        away,
        home_id="2007/home",
        away_id="2007/away",
        seed=41,
        coach_policy=policy,
        mode="drive",
        advanced_ii=True,
    )
    before = game.view()

    game.snap("1", "WC1")

    history = game._coach._situational_recent[("away", "defense")]
    assert len(history) == 1
    expected = observe_policy(before, "home", 9 if include_advanced else 8)
    expected = replace(expected, side="away", score_difference=-expected.score_difference)
    assert history[0][0] == situation_bucket(expected, "defense")


def test_chart_evaluator_simulates_free_and_conditional_advanced_calls() -> None:
    home = team_chart("Home", plays={Play.NINE: yards(4)})
    away = team_chart("Away")
    conditional = replace(
        observation(side="away", offense=("9",), defense=("RUN",)),
        advanced_ii=True,
    )
    free = replace(conditional, free_advanced_defense=True)

    conditional_value = evaluate_action(
        home,
        away,
        conditional,
        "RUN",
        role="defense",
        samples=32,
    )
    free_value = evaluate_action(home, away, free, "RUN", role="defense", samples=32)

    assert conditional_value.complete and free_value.complete
    assert conditional_value.mean_utility is not None
    assert free_value.mean_utility is not None
    assert free_value.mean_utility > conditional_value.mean_utility

    offense_view = replace(
        observation(side="home", offense=("9",), defense=("RUN",)),
        advanced_ii=True,
    )
    conditional_opponent = evaluate_action(
        home, away, offense_view, "9", role="offense", samples=32
    )
    free_opponent = evaluate_action(
        home,
        away,
        replace(offense_view, free_advanced_defense=True),
        "9",
        role="offense",
        samples=32,
    )
    assert conditional_opponent.complete and free_opponent.complete
    assert conditional_opponent.mean_utility > free_opponent.mean_utility


def test_hard_v9_compares_all_legal_advanced_defenses_without_fallback() -> None:
    home, away = default_teams()
    coach = DifficultyCoach(17, home, away, "hard", version=9)
    view = PlaySession.new(
        home,
        away,
        seed=41,
        advanced_ii=True,
        away_privileges=("W",),
    ).view()
    advanced = replace(
        observation(
            side="away",
            offense=("1", "9"),
            defense=tuple(action.key for action in view.actions.defense),
        ),
        advanced_ii=True,
        free_advanced_defense=True,
    )

    estimates = coach.estimates(advanced, "defense")

    assert {estimate.key for estimate in estimates} == set(advanced.defense)
    assert all(estimate.complete for estimate in estimates)
    assert coach.defense(advanced) in advanced.defense
    assert not coach.analysis_fallback

    chart_coach = ChartAwareCoach(17, home, away, version=9)
    chart_estimates = chart_coach.estimates(advanced, "defense")
    assert {estimate.key for estimate in chart_estimates} == set(advanced.defense)
    assert all(estimate.complete for estimate in chart_estimates)
    assert chart_coach.defense(advanced) in advanced.defense
    assert not chart_coach.analysis_fallback
