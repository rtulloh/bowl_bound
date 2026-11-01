"""AI-015: version-6 defense preferences keep situational coverage available."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_audit import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.difficulty import DifficultyCoach
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation

DEFENSES = tuple("ABCDEF")


def v6_coach(mode: str, monkeypatch: pytest.MonkeyPatch) -> DifficultyCoach:
    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=6)


def defense_mix(coach: DifficultyCoach, obs: CoachObservation) -> dict[str, float]:
    with capture_preferences(coach, observation=obs) as draws:
        coach.defense(obs)
    return draws[-1]


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v6_goal_line_increases_short_yardage_weight_without_removing_formations(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    coach = v6_coach(mode, monkeypatch)
    ordinary = observation(defense=DEFENSES)
    goal_line = replace(ordinary, yards_to_goal=5)

    ordinary_mix = defense_mix(coach, ordinary)
    goal_line_mix = defense_mix(coach, goal_line)

    assert goal_line_mix["B"] > ordinary_mix["B"]
    assert goal_line_mix["C"] > ordinary_mix["C"]
    assert set(goal_line_mix) == set(DEFENSES)
    assert min(goal_line_mix.values()) > 0


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("kick_option", ["punt", "field_goal"])
def test_v6_fourth_down_likely_kick_favors_standard_but_keeps_all_formations(
    mode: str, kick_option: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    coach = v6_coach(mode, monkeypatch)
    ordinary = observation(defense=DEFENSES)
    kick_likely = replace(ordinary, down=4, distance=10, special=(kick_option,))

    ordinary_mix = defense_mix(coach, ordinary)
    kick_mix = defense_mix(coach, kick_likely)

    assert kick_mix["A"] > ordinary_mix["A"]
    assert set(kick_mix) == set(DEFENSES)
    assert min(kick_mix.values()) > 0


def test_v6_short_fourth_down_punt_does_not_trigger_kick_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coach = v6_coach("medium", monkeypatch)
    ordinary = observation(defense=DEFENSES)
    short_go_for_it = replace(ordinary, down=4, distance=2, special=("punt",))

    assert defense_mix(coach, short_go_for_it) == defense_mix(coach, ordinary)


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v6_late_multi_score_lead_favors_coverage_without_removing_formations(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    coach = v6_coach(mode, monkeypatch)
    tied_late = observation(defense=DEFENSES, quarter=4, remaining=30, score_difference=0)
    protecting = replace(tied_late, score_difference=14)

    tied_mix = defense_mix(coach, tied_late)
    protecting_mix = defense_mix(coach, protecting)

    assert protecting_mix["E"] > tied_mix["E"]
    assert set(protecting_mix) == set(DEFENSES)
    assert min(protecting_mix.values()) > 0


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v5_defense_keeps_its_previous_mixture(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bowl_bound.difficulty.evaluate_action",
        lambda home, away, obs, key, **kwargs: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=5)
    ordinary = observation(defense=DEFENSES)
    goal_line = replace(ordinary, yards_to_goal=5)

    assert defense_mix(coach, ordinary) == defense_mix(coach, goal_line)
