"""AI-014: Hard repetition weights use comparable, decaying public history."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_audit import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation


def hard_v5() -> DifficultyCoach:
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard", version=5)


def weight(
    coach: DifficultyCoach,
    obs: CoachObservation,
    key: str = "1",
    role: str = "offense",
) -> float:
    return coach._preference_weight(obs, role, key, 1.0)


def commit(coach: DifficultyCoach, obs: CoachObservation, play: str = "1") -> None:
    coach.commit_call("home", play, "A", observation=obs)


def test_v5_other_situation_history_does_not_discount_a_candidate() -> None:
    current = observation(down=1, distance=10, yards_to_goal=65)
    unrelated = replace(current, down=3, distance=15)
    coach = hard_v5()
    baseline = weight(coach, current)

    commit(coach, unrelated)
    commit(coach, unrelated)

    assert weight(coach, current) == baseline


def test_v5_repeated_comparable_calls_are_decayed_and_have_a_floor() -> None:
    current = observation(down=1, distance=10, yards_to_goal=65)
    coach = hard_v5()

    for _ in range(6):
        commit(coach, current)

    discounted = weight(coach, current)
    assert discounted == pytest.approx(0.30)
    assert discounted > 0


def test_v5_favorite_share_falls_without_banning_any_legal_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )
    current = observation(special=(), game_actions=())
    plain = hard_v5()
    repeated = hard_v5()
    for _ in range(96):
        commit(repeated, current)

    def preferences(coach: DifficultyCoach) -> dict[str, float]:
        with capture_preferences(coach, observation=current) as draws:
            coach.offense(current)
        return draws[-1]

    ordinary = preferences(plain)
    varied = preferences(repeated)

    assert varied["1"] < ordinary["1"]
    assert set(varied) == set(current.offense)
    assert min(varied.values()) > 0


def test_v5_repeated_uniquely_best_call_remains_favored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(
            key, 32, 0, 100.0 if key == "9" else 0.0, 0.0, 0.0
        ),
    )
    current = observation(special=(), game_actions=())
    coach = hard_v5()
    for _ in range(96):
        commit(coach, current, "9")

    with capture_preferences(coach, observation=current) as draws:
        coach.offense(current)

    mixture = draws[-1]
    assert mixture["9"] > max(weight for key, weight in mixture.items() if key != "9")
    assert mixture["9"] > 0


def test_v5_intervening_own_calls_decay_a_matching_repeat() -> None:
    current = observation(down=1, distance=10, yards_to_goal=65)
    other = replace(current, down=3, distance=15)
    immediate = hard_v5()
    aged = hard_v5()

    commit(immediate, current)
    commit(aged, current)
    for _ in range(3):
        commit(aged, other, "2")

    assert weight(aged, current) > weight(immediate, current)
    assert weight(aged, current) < 1.0


def test_v5_defense_history_uses_the_defender_side_and_public_situation() -> None:
    offensive_observation = observation()
    defensive_observation = replace(
        offensive_observation,
        side="away",
        score_difference=-offensive_observation.score_difference,
    )
    plain = hard_v5()
    repeated = hard_v5()
    for _ in range(3):
        commit(repeated, offensive_observation)

    assert weight(repeated, defensive_observation, "A", "defense") < weight(
        plain, defensive_observation, "A", "defense"
    )


def test_v5_bucket_matches_the_coaching_audit_definition() -> None:
    from bowl_bound.coaching_audit import CallAudit
    from bowl_bound.coaching_situations import situation_bucket

    first = observation(distance=8, yards_to_goal=65, remaining=650)
    comparable = replace(first, distance=10, yards_to_goal=61, remaining=620, play_number=8)
    material_change = replace(first, distance=2)

    assert situation_bucket(first, "offense") == situation_bucket(comparable, "offense")
    assert situation_bucket(first, "offense") != situation_bucket(material_change, "offense")

    audit = CallAudit()
    audit.record(first, "offense", "1", fallback=False)
    audit.record(comparable, "offense", "1", fallback=False)
    assert audit.comparable_calls == 1


def test_v5_save_replay_reconstructs_situational_history_and_future_calls() -> None:
    home = team_chart("Home", season=2002, offense=3)
    away = team_chart("Away", season=2002, offense=3)
    game = SavedGame.new(
        home,
        away,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        coach_policy="hard-v5",
    )
    for _ in range(4):
        game.snap("1", "A")

    restored = loads_game(dumps_game(game), lambda key: home if key.endswith("home") else away)

    assert restored._coach._situational_recent == game._coach._situational_recent
    current = observation(special=(), game_actions=())
    assert restored._coach.offense(current) == game._coach.offense(current)


def test_v4_keeps_its_original_global_repetition_weight() -> None:
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "hard", version=4)
    current = observation()
    for _ in range(3):
        coach.commit_call("home", "7", "A")

    expected = 1.0 * (1 + coach.aggression) / 4
    assert coach._preference_weight(current, "offense", "7", 1.0) == expected
