"""Distinct difficulty preferences with committed-public, replayable Hard history."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.models import Play
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import team_chart, yards
from tests.test_cli import saved_facts
from tests.test_coaching import observation


@pytest.mark.parametrize("mode,aggression", [("easy", 0.3), ("medium", 0.5), ("hard", 0.7)])
def test_modes_are_versioned_and_have_explicit_aggression(mode: str, aggression: float) -> None:
    from bowl_bound.difficulty import DifficultyCoach

    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode)
    assert coach.aggression == aggression and coach.policy == f"{mode}-v1"
    with pytest.raises(ValueError, match="difficulty"):
        DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "unknown")


def test_medium_coarse_strength_adjusts_early_down_group_not_individual_play_ranking() -> None:
    from bowl_bound.difficulty import DifficultyCoach

    home = team_chart(
        "Home",
        offense=1,
        plays={play: yards(12) for play in (Play.ONE, Play.TWO, Play.THREE, Play.FOUR, Play.FIVE)},
    )
    reversed_chart = team_chart(
        "Home",
        offense=12,
        plays={play: yards(1) for play in (Play.ONE, Play.TWO, Play.THREE, Play.FOUR, Play.FIVE)},
    )
    run = DifficultyCoach(31, home, team_chart("Away"), "medium")
    passing = DifficultyCoach(31, reversed_chart, team_chart("Away"), "medium")
    easy = DifficultyCoach(31, home, team_chart("Away"), "easy")
    plain_easy = DifficultyCoach(31, reversed_chart, team_chart("Away"), "easy")
    obs = observation(special=(), game_actions=())
    run_calls = [run.offense(replace(obs, play_number=i)) for i in range(1000)]
    pass_calls = [passing.offense(replace(obs, play_number=i)) for i in range(1000)]
    assert sum(k in "12345" for k in run_calls) > sum(k in "12345" for k in pass_calls) + 150
    assert [easy.offense(replace(obs, play_number=i)) for i in range(50)] == [
        plain_easy.offense(replace(obs, play_number=i)) for i in range(50)
    ]
    assert [run.offense(replace(obs, down=3, play_number=i)) for i in range(50)] == [
        passing.offense(replace(obs, down=3, play_number=i)) for i in range(50)
    ]


def test_hard_estimates_use_only_public_committed_opponent_tendencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.difficulty import DifficultyCoach

    calls = []

    def estimate(home, away, obs, key, **kwargs):
        calls.append(kwargs["opponent_weights"])
        return ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0)

    monkeypatch.setattr("bowl_bound.difficulty.evaluate_action", estimate)
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard")
    obs = observation(special=(), game_actions=())
    first = coach.offense(obs)
    assert coach.offense(obs) == first
    assert all(len(set(weights)) == 1 for weights in calls)
    calls.clear()
    for _ in range(4):
        coach.commit_call("home", "1", "F")
    coach.offense(obs)
    assert calls and all(weights[-1] == 5 and weights[0] == 1 for weights in calls)
    calls.clear()
    coach.commit_call("away", "9", "A")
    coach.defense(replace(obs, possession="away"))
    assert calls and all(weights[-1] == 2 and weights[0] == 1 for weights in calls)


def test_hard_recent_call_variety_reduces_repetition_without_banning_legal_plays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.difficulty import DifficultyCoach

    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )
    plain = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard")
    recent = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard")
    for _ in range(6):
        recent.commit_call("home", "1", "A")
    obs = observation(special=(), game_actions=())
    ordinary = [plain.offense(replace(obs, play_number=i)) for i in range(2000)]
    varied = [recent.offense(replace(obs, play_number=i)) for i in range(2000)]
    assert 0 < varied.count("1") < ordinary.count("1") / 2
    assert set(varied) == set(obs.offense)


def test_hard_partial_estimate_failure_falls_back_for_whole_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.difficulty import DifficultyCoach

    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(
            key, 32, int(key == "1"), None if key == "1" else 100, 0.0, 0.0
        ),
    )
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard")
    obs = observation(special=(), game_actions=())
    assert coach.offense(obs) in obs.offense and coach.analysis_fallback


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_save_reconstructs_policy_history_and_exact_future(mode: str) -> None:
    home, away = (
        team_chart("Home", season=2002, offense=3),
        team_chart("Away", season=2002, offense=3),
    )
    game = SavedGame.new(
        home,
        away,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        coach_policy=f"{mode}-v1",
    )
    for _ in range(3):
        game.snap("1", "A")
    before = saved_facts(game)
    for _ in range(3):
        game.coach_view("home")
    assert saved_facts(game) == before
    restored = loads_game(dumps_game(game), lambda key: home if key.endswith("home") else away)
    assert restored.coach_policy == game.coach_policy
    for _ in range(3):
        view, turn = game.coach_view("home")
        if view.pending:
            choice = next(c.id for c in turn.pending.choices if c.enabled)
            game.coach_execute("home", "decide", choice)
            restored.coach_execute("home", "decide", choice)
        else:
            key = "1" if view.state.possession == "home" else "A"
            game.coach_step("home", key)
            restored.coach_step("home", key)
        assert saved_facts(game) == saved_facts(restored)


def test_baseline_stream_remains_a_separate_policy_not_a_new_difficulty_alias() -> None:
    from bowl_bound.difficulty import DifficultyCoach

    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "easy")
    obs = observation(special=(), game_actions=())
    assert any(
        coach.offense(replace(obs, play_number=i))
        != BaselineCoach(31).offense(replace(obs, play_number=i))
        for i in range(100)
    )


def test_hard_analysis_cache_is_bounded_and_history_changes_invalidate_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.difficulty import DifficultyCoach

    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard")
    obs = observation()
    for number in range(150):
        coach.estimates(replace(obs, remaining=number), "offense")
    assert coach.cached_situations == 128
    with pytest.raises(ValueError, match="role"):
        coach.estimates(obs, "hidden")
    with pytest.raises(ValueError, match="committed"):
        coach.commit_call("home", "hidden", "A")


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_specials_and_required_choices_use_legal_controls_and_ot_context(mode: str) -> None:
    from bowl_bound.difficulty import DifficultyCoach

    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode)
    assert coach.offense(observation(offense=(), special=("kickoff",))) == "kickoff"
    assert (
        coach.offense(
            observation(quarter=4, remaining=30, score_difference=7, game_actions=("kneel",))
        )
        == "kneel"
    )
    assert coach.offense(observation(offense=("1",), special=())) == "1"
    assert coach.decision(observation(choices=("ot:defense",), overtime=True)) == "ot:defense"
