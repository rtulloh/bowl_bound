"""AI-036: rare, committed-history-aware RZDZ mixtures; fictional charts only."""

import json
from collections import Counter
from dataclasses import replace
from unittest.mock import patch

import pytest

from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_audit_sampling import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation


def coach(mode: str, *, version: int = CURRENT_DIFFICULTY_VERSION) -> DifficultyCoach:
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=version)


def situation(**changes: object) -> CoachObservation:
    return observation(
        offense=tuple("123456789") + ("Q", "RZDZ"),
        special=(),
        game_actions=(),
        **changes,
    )


def mixture(policy: DifficultyCoach, obs: CoachObservation) -> dict[str, float]:
    with capture_preferences(policy, observation=obs) as draws:
        chosen = policy.offense(obs)
    assert chosen in obs.offense + obs.special + obs.game_actions
    assert draws and chosen in draws[-1]
    assert sum(draws[-1].values()) == pytest.approx(1)
    return draws[-1]


@pytest.fixture
def flat_estimates(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen = []

    def estimate(
        home: TeamChart, away: TeamChart, obs: CoachObservation, key: str, **kwargs: object
    ) -> ActionEstimate:
        seen.append(key)
        # An unrealistically attractive RZDZ must not bypass its surprise policy.
        return ActionEstimate(key, 32, 0, 1000.0 if key == "RZDZ" else 0.0, 0.0, 0.0)

    monkeypatch.setattr("bowl_bound.difficulty.evaluate_action", estimate)
    return seen


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize(
    "facts",
    [
        {},
        {"down": 3, "distance": 12},
        {"quarter": 2, "remaining": 60},
        {"quarter": 4, "remaining": 60, "score_difference": -7},
        {"down": 4, "distance": 1, "yards_to_goal": 60},
    ],
)
def test_current_surprise_weight_is_separate_from_pass_and_utility(mode, facts, flat_estimates):
    weights = mixture(coach(mode), situation(**facts))
    assert weights["RZDZ"] == pytest.approx(0.03)
    assert "RZDZ" not in flat_estimates
    assert all(weights[key] > 0 for key in "123456789")


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_recent_committed_use_discourages_reuse_without_a_hard_ban(
    mode: str, flat_estimates: list[str]
) -> None:
    policy = coach(mode)
    obs = situation()
    initial = mixture(policy, obs)["RZDZ"]
    before = policy.call_history()
    assert mixture(policy, obs)["RZDZ"] == initial
    assert policy.call_history() == before
    policy.commit_call("home", "RZDZ", "A", observation=obs)
    recent = mixture(policy, obs)["RZDZ"]
    assert 0 < recent < initial / 4
    for _ in range(6):
        policy.commit_call("home", "1", "A", observation=obs)
    rested = mixture(policy, obs)["RZDZ"]
    assert recent < rested < initial
    other = replace(obs, side="away", possession="away")
    assert mixture(policy, other)["RZDZ"] == initial


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_public_kick_and_kneel_priorities_are_not_replaced(
    mode: str, flat_estimates: list[str]
) -> None:
    policy = coach(mode)
    kick = replace(situation(down=4, distance=7, yards_to_goal=17), special=("field_goal", "punt"))
    kneel = replace(situation(), game_actions=("kneel",), can_kneel_out_game=True)
    for i in range(30):
        assert policy.offense(replace(kick, play_number=i)) == "field_goal"
        assert policy.offense(replace(kneel, play_number=i)) == "kneel"


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_failed_analysis_uses_the_same_rare_fallback(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(key, 32, 1, None, None, None),
    )
    policy = coach(mode)
    weights = mixture(policy, situation(quarter=2, remaining=60))
    assert policy.analysis_fallback
    assert weights["RZDZ"] == pytest.approx(0.03)


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_frozen_v12_retains_ordinary_and_critical_razzle_preferences(
    mode: str, flat_estimates: list[str]
) -> None:
    policy = coach(mode, version=12)
    ordinary = mixture(policy, situation())
    assert ordinary["RZDZ"] > 0.03
    if mode != "hard":
        assert ordinary["RZDZ"] == ordinary["6"]
    critical = mixture(policy, situation(quarter=2, remaining=60))
    assert critical["RZDZ"] > 0.5
    assert "RZDZ" in flat_estimates


def test_no_forced_minimum_or_hard_game_quota(flat_estimates: list[str]) -> None:
    policy = coach("medium")
    obs = situation()
    with patch.object(policy, "_random") as random:
        random.return_value.choices.side_effect = lambda population, **kwargs: [population[0]]
        assert all(policy.offense(replace(obs, play_number=i)) != "RZDZ" for i in range(100))
    for _ in range(20):
        policy.commit_call("home", "RZDZ", "A", observation=obs)
    assert mixture(policy, obs)["RZDZ"] > 0


def test_frozen_load_and_current_named_upgrade_preserve_actual_commands() -> None:
    home, away = team_chart("Home"), team_chart("Away")
    saved = SavedGame.new(
        home,
        away,
        home_id="2007/home",
        away_id="2007/away",
        seed=7,
        coach_seed=31,
        coach_policy="medium-v12",
    )
    saved.snap("RZDZ", "A")
    loader = {"2007/home": home, "2007/away": away}.__getitem__
    payload = dumps_game(saved)
    frozen = loads_game(payload, loader, preserve_development_policy=True)
    current = loads_game(payload, loader)
    assert frozen._coach.version == 12
    assert current._coach.version == CURRENT_DIFFICULTY_VERSION
    assert frozen.view() == current.view() == saved.view()
    assert json.loads(dumps_game(frozen))["commands"] == json.loads(payload)["commands"]
    assert mixture(current._coach, situation())["RZDZ"] < 0.01


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_normal_synthetic_call_distribution_matches_surprise_intent(
    mode: str, flat_estimates: list[str]
) -> None:
    counts = []
    adjacent = 0
    for seed in range(100):
        policy = DifficultyCoach(seed, team_chart("Home"), team_chart("Away"), mode, version=13)
        calls = []
        for index in range(80):
            obs = situation(
                quarter=1 + index // 20,
                remaining=900 - (index % 20) * 40,
                play_number=index,
            )
            called = policy.offense(obs)
            policy.commit_call("home", called, "A", observation=obs)
            calls.append(called)
        counts.append(Counter(calls)["RZDZ"])
        adjacent += sum(a == b == "RZDZ" for a, b in zip(calls, calls[1:], strict=False))
    assert 1 <= sum(counts) / len(counts) <= 3
    assert sum(1 <= count <= 3 for count in counts) >= 75
    assert 0 in counts  # No forced minimum.
    assert adjacent <= 2  # Statistical control, not an engine prohibition.


def test_surprise_call_does_not_depend_on_future_gameplay_rolls(flat_estimates: list[str]) -> None:
    home, away = team_chart("Home"), team_chart("Away")
    games = [
        SavedGame.new(
            home,
            away,
            home_id="2007/home",
            away_id="2007/away",
            seed=seed,
            coach_seed=31,
            difficulty="medium",
        )
        for seed in (7, 29)
    ]
    obs = situation()
    before = [dumps_game(game) for game in games]
    assert games[0]._coach.offense(obs) == games[1]._coach.offense(obs)
    assert mixture(games[0]._coach, obs) == mixture(games[1]._coach, obs)
    assert [json.loads(dumps_game(game))["commands"] for game in games] == [
        json.loads(value)["commands"] for value in before
    ]
    assert [json.loads(dumps_game(game))["rolls"] for game in games] == [
        json.loads(value)["rolls"] for value in before
    ]


def test_complete_game_audit_retains_actual_razzle_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.coaching_audit import audit_game, audit_seed
    from bowl_bound.sample_teams import sample_teams

    captured = []
    original = SavedGame.new

    def capture(*args: object, **kwargs: object) -> SavedGame:
        game = original(*args, **kwargs)
        captured.append(game)
        return game

    monkeypatch.setattr(SavedGame, "new", staticmethod(capture))
    result = audit_game(
        *sample_teams(),
        seed=101,
        coach_seed=audit_seed(101, "coach:False:home:easy-v13"),
        stand_in_seed=audit_seed(101, "stand-in:False:home:easy-v13"),
        policy="easy-v13",
        cpu_side="home",
    )
    records = [
        report
        for report in captured[0].view().log
        if report.called_play == "Razzle-Dazzle" and report.state_before.possession == "home"
    ]
    assert records
    assert result.razzle_outcomes == Counter(report.outcome for report in records)
    assert result.razzle_statistics == Counter(report.statistics.kind.value for report in records)
