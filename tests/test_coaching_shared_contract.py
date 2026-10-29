"""AI-008: explicit coach hooks and shared weighted analysis preserve contracts."""

from dataclasses import replace

import pytest

from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import BaselineCoach
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.save_game import SavedGame
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation


def test_baseline_exposes_noop_history_and_explicit_analysis_status() -> None:
    coach = BaselineCoach(31)
    obs = observation()
    before = coach.offense(obs)
    assert coach.analysis_fallback is False
    coach.commit_call("home", "1", "A")
    assert coach.offense(obs) == before


def test_saved_command_dispatches_history_hook_without_concrete_tier_check() -> None:
    calls = []

    class RecordingCoach(BaselineCoach):
        def commit_call(self, offense_side: str, play: str, defense: str) -> None:
            calls.append((offense_side, play, defense))

    game = SavedGame.new(
        team_chart("Home"),
        team_chart("Away", defense=0),
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
    )
    game._coach = RecordingCoach(31)
    game.snap("1", "A")
    assert calls == [("home", "1", "A")]


@pytest.mark.parametrize("tier", ["chart", "hard"])
def test_shared_explicit_opponent_mixture_is_cached_separately(tier: str) -> None:
    home, away = team_chart("Home"), team_chart("Away", defense=0)
    coach = (
        ChartAwareCoach(31, home, away)
        if tier == "chart"
        else DifficultyCoach(31, home, away, "hard")
    )
    obs = observation(offense=("1",))
    weights = (1.0,) * 6
    first = coach.estimates(obs, "offense", opponent_weights=weights)
    assert (
        coach.estimates(replace(obs, play_number=1), "offense", opponent_weights=weights) is first
    )
    second = coach.estimates(obs, "offense", opponent_weights=(9.0, 1.0, 1.0, 1.0, 1.0, 1.0))
    assert second is not first and coach.cached_situations == 2


def test_public_observation_builder_retains_original_view_contract() -> None:
    from bowl_bound.coaching_session import _observation, observe_game

    game = SavedGame.new(
        team_chart("Home"), team_chart("Away"), home_id="2026/home", away_id="2026/away", seed=7
    )
    assert observe_game(game.view(), "home") == _observation(game.view(), "home")
