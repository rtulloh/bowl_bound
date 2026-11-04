"""AI-037: legal early-down punts stay outside the current AI candidate mixture."""

import json
from dataclasses import replace

import pytest

from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_audit_sampling import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.coaching_session import observe_game
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart
from tests.test_cli import saved_facts
from tests.test_cli_shortcuts import live, regulation
from tests.test_coaching import observation


@pytest.fixture
def tempting_punt(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    def estimate(
        home: TeamChart, away: TeamChart, obs: CoachObservation, key: str, **kwargs: object
    ) -> ActionEstimate:
        seen.append(key)
        # Eligibility must hold even when a bounded estimate strongly favors punting.
        return ActionEstimate(key, 32, 0, 1000.0 if key == "punt" else 0.0, 0.0, 0.0)

    monkeypatch.setattr("bowl_bound.difficulty.evaluate_action", estimate)
    return seen


def coach(mode: str, version: int = CURRENT_DIFFICULTY_VERSION) -> DifficultyCoach:
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=version)


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("down", [1, 2, 3])
@pytest.mark.parametrize("quarter,margin", [(2, -6), (4, 0)])
@pytest.mark.parametrize("side", ["home", "away"])
def test_current_early_down_mixture_never_includes_punt(
    mode: str, down: int, quarter: int, margin: int, side: str, tempting_punt: list[str]
) -> None:
    obs = observation(
        side=side,
        possession=side,
        down=down,
        quarter=quarter,
        remaining=80,
        yards_to_goal=72,
        distance=10,
        score_difference=margin,
    )
    policy = coach(mode)
    with capture_preferences(policy, observation=obs) as draws:
        selected = policy.offense(obs)
    assert "punt" not in tempting_punt
    assert "punt" not in draws[-1]
    assert selected != "punt"
    assert "punt" in obs.special  # Engine legality remains available to the human.


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_current_fourth_down_punts_and_last_snap_field_goals_remain(mode: str) -> None:
    policy = coach(mode)
    assert (
        policy.offense(
            observation(
                down=4, quarter=2, remaining=80, yards_to_goal=72, distance=10, score_difference=-6
            )
        )
        == "punt"
    )
    assert (
        policy.offense(
            observation(down=1, quarter=2, remaining=10, yards_to_goal=20, score_difference=-2)
        )
        == "field_goal"
    )


def test_frozen_v13_keeps_its_original_early_punt_candidates(tempting_punt: list[str]) -> None:
    policy = coach("hard", version=13)
    obs = observation(quarter=2, remaining=80, yards_to_goal=72, score_difference=-6)
    with capture_preferences(policy, observation=obs) as draws:
        policy.offense(obs)
    assert "punt" in tempting_punt and draws[-1]["punt"] > 0
    # Captured before v14: retain the frozen policy's exact seeded call stream.
    assert [policy.offense(replace(obs, play_number=i)) for i in range(20)] == [
        "punt",
        "7",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "6",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
        "punt",
    ]


def test_named_save_upgrades_future_coaching_without_changing_game_replay() -> None:
    home, away = team_chart("Home"), team_chart("Away")
    saved = SavedGame.new(
        home,
        away,
        home_id="2007/home",
        away_id="2007/away",
        seed=7,
        coach_seed=31,
        coach_policy="hard-v13",
    )
    saved.snap("1", "A")
    payload = dumps_game(saved)
    loader = {"2007/home": home, "2007/away": away}.__getitem__
    frozen = loads_game(payload, loader, preserve_development_policy=True)
    current = loads_game(payload, loader)
    assert frozen._coach.version == 13
    assert current._coach.version == CURRENT_DIFFICULTY_VERSION == 14
    assert frozen.view() == current.view() == saved.view()
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert json.loads(dumps_game(current))[key] == json.loads(payload)[key]


def test_real_engine_hard_estimates_after_kickoff_do_not_offer_early_punts() -> None:
    app = regulation(clock=Clock(2, 90))
    live(app)
    view = app.game.view()
    assert view.state.down == 1 and view.clock.quarter == 2 and view.clock.remaining <= 120
    obs = observe_game(view, view.state.possession)
    before = saved_facts(app.game)
    policy = DifficultyCoach(
        31,
        app.load_team("2002/home"),
        app.load_team("2002/away"),
        "hard",
        version=CURRENT_DIFFICULTY_VERSION,
    )
    calls = [policy.offense(replace(obs, play_number=i)) for i in range(20)]
    assert "punt" not in calls
    assert "punt" not in {estimate.key for estimate in policy.estimates(obs, "offense")}
    assert not policy.analysis_fallback
    assert saved_facts(app.game) == before
