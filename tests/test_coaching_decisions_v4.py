"""AI-013: score/time pressure changes version-4 Easy/Medium play mixtures."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_audit import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.difficulty import DifficultyCoach
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation


def preference_vector(mode: str, obs: CoachObservation, *, version: int = 4) -> dict[str, float]:
    """Capture the actual synthetic-chart mixture without sampling selected calls."""
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=version)
    with capture_preferences(coach, observation=obs) as draws:
        coach._basic_offense(obs)
    return draws[-1]


def pass_share(preferences: dict[str, float]) -> float:
    return sum(preferences[key] for key in "6789")


@pytest.mark.parametrize("mode", ["easy", "medium"])
def test_v4_pass_share_grows_with_deficit_and_falls_with_time(
    mode: str,
) -> None:
    tied_early = observation(quarter=1, remaining=900, score_difference=0)
    trailing_four_minutes = observation(quarter=4, remaining=240, score_difference=-7)
    trailing_two_scores = observation(quarter=4, remaining=240, score_difference=-14)
    trailing_before_halftime = observation(quarter=2, remaining=240, score_difference=-14)
    trailing_one_minute = observation(quarter=4, remaining=60, score_difference=-7)

    early_share = pass_share(preference_vector(mode, tied_early))
    down_score_share = pass_share(preference_vector(mode, trailing_four_minutes))
    two_score_share = pass_share(preference_vector(mode, trailing_two_scores))
    halftime_share = pass_share(preference_vector(mode, trailing_before_halftime))
    late_share = pass_share(preference_vector(mode, trailing_one_minute))

    assert early_share < down_score_share < two_score_share
    assert early_share < halftime_share
    assert down_score_share < late_share


def test_v4_lead_protection_tilts_long_down_calls_toward_runs() -> None:
    tied = observation(quarter=4, remaining=60, score_difference=0, down=3, distance=8)
    leading = replace(tied, score_difference=14)

    tied_preferences = preference_vector("medium", tied)
    leading_preferences = preference_vector("medium", leading)

    assert pass_share(leading_preferences) < pass_share(tied_preferences)
    assert set(leading_preferences) == set("123456789")
    assert min(leading_preferences.values()) > 0


@pytest.mark.parametrize("mode", ["easy", "medium"])
def test_v4_situational_pressure_reaches_late_chart_candidate_mixture(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=4)
    tied = observation(
        quarter=4,
        remaining=60,
        score_difference=0,
        special=(),
    )
    trailing = replace(tied, score_difference=-14)
    leading = replace(tied, score_difference=14)

    def evaluate(
        _: CoachObservation,
        key: str,
        __: str,
        ___: tuple[float, ...] | None,
    ) -> ActionEstimate:
        return ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(coach, "_evaluate", evaluate)

    def selected_pass_share(obs: CoachObservation) -> float:
        with capture_preferences(coach, observation=obs) as draws:
            coach.offense(obs)
        return pass_share(draws[-1])

    assert selected_pass_share(trailing) > selected_pass_share(tied)
    assert selected_pass_share(leading) < selected_pass_share(tied)


def test_v4_aggression_changes_passing_down_mixtures() -> None:
    obs = observation(quarter=1, down=3, distance=8)

    shares = [pass_share(preference_vector(mode, obs)) for mode in ("easy", "medium", "hard")]

    assert shares[0] < shares[1] < shares[2]


def test_v4_comeback_quarter_retains_at_least_seven_distinct_legal_calls() -> None:
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "easy", version=4)
    calls = {
        coach.offense(
            observation(
                quarter=4,
                remaining=900 - 30 * play_number,
                score_difference=-14,
                play_number=play_number,
                special=(),
            )
        )
        for play_number in range(30)
    }

    assert calls <= set("123456789")
    assert len(calls) >= 7


@pytest.mark.parametrize("mode", ["easy", "medium"])
def test_v3_mixture_remains_frozen_when_score_and_clock_change(mode: str) -> None:
    tied_early = observation(quarter=1, remaining=900, score_difference=0)
    trailing_late = observation(quarter=4, remaining=60, score_difference=-14)

    assert preference_vector(mode, tied_early, version=3) == preference_vector(
        mode, trailing_late, version=3
    )
