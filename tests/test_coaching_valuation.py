"""AI-003: value field position without a fixed possession-change charge."""

from dataclasses import replace

import pytest

from bowl_bound.coaching_evaluation import evaluate_action
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import SpecialTeamsColumn, TeamChart
from tests.synthetic_teams import team_chart, yards
from tests.test_coaching import observation


def special_chart(chart: TeamChart, column: SpecialTeamsColumn, value: int) -> TeamChart:
    return replace(
        chart,
        special_teams=tuple(
            replace(row, cell=yards(value)) if row.column is column else row
            for row in chart.special_teams
        ),
    )


@pytest.mark.parametrize("side", ["home", "away"])
def test_certain_field_goal_has_positive_value_and_beats_failed_fourth_down(side: str) -> None:
    offense = special_chart(team_chart("Offense", offense=0), SpecialTeamsColumn.FIELD_GOAL, 100)
    defense = team_chart("Defense", defense=0)
    home, away = (offense, defense) if side == "home" else (defense, offense)
    obs = observation(
        side=side,
        possession=side,
        down=4,
        distance=5,
        yards_to_goal=25,
        offense=("1",),
        defense=("A",),
        special=("field_goal",),
    )
    coach = DifficultyCoach(31, home, away, "hard")
    estimates = {entry.key: entry for entry in coach.estimates(obs, "offense")}
    assert all(entry.complete for entry in estimates.values())
    assert estimates["field_goal"].mean_points == 3
    assert estimates["field_goal"].mean_utility > 0
    assert estimates["field_goal"].mean_utility > estimates["1"].mean_utility


@pytest.mark.parametrize("side", ["home", "away"])
def test_goal_line_touchdown_is_worth_clearly_more_than_no_gain(side: str) -> None:
    offense = team_chart("Offense", offense=0)
    defense = team_chart("Defense", defense=0)
    home, away = (offense, defense) if side == "home" else (defense, offense)
    obs = observation(
        side=side,
        possession=side,
        down=1,
        distance=1,
        yards_to_goal=1,
        offense=("1",),
        defense=("A",),
        special=(),
    )
    no_gain = DifficultyCoach(31, home, away, "hard").estimates(obs, "offense")[0]
    scoring = team_chart("Offense", offense=1)
    home, away = (scoring, defense) if side == "home" else (defense, scoring)
    touchdown = DifficultyCoach(31, home, away, "hard").estimates(obs, "offense")[0]
    assert touchdown.complete and no_gain.complete
    assert touchdown.mean_points == 6 and no_gain.mean_points == 0
    assert touchdown.mean_utility >= no_gain.mean_utility + 2


@pytest.mark.parametrize("side", ["home", "away"])
def test_obvious_punt_dominates_failed_fourth_down_without_banning_exploration(side: str) -> None:
    offense = special_chart(team_chart("Offense", offense=0), SpecialTeamsColumn.PUNT, 40)
    defense = special_chart(team_chart("Defense", defense=0), SpecialTeamsColumn.PUNT_RETURN, 0)
    home, away = (offense, defense) if side == "home" else (defense, offense)
    obs = observation(
        side=side, possession=side, down=4, distance=10, yards_to_goal=80, special=("punt",)
    )
    coach = DifficultyCoach(31, home, away, "hard")
    calls = [coach.offense(replace(obs, play_number=index)) for index in range(300)]
    assert calls.count("punt") >= 180
    assert any(call in obs.offense for call in calls)


def test_legacy_chart_valuation_remains_unchanged() -> None:
    home = special_chart(team_chart("Home", offense=0), SpecialTeamsColumn.FIELD_GOAL, 100)
    result = evaluate_action(
        home,
        team_chart("Away", defense=0),
        observation(down=4, distance=5, yards_to_goal=25),
        "field_goal",
        role="offense",
        samples=4,
    )
    assert result.complete and result.mean_points == 3
    assert result.mean_utility == pytest.approx(-1.25)


@pytest.mark.parametrize("side", ["home", "away"])
def test_public_sample_obvious_punt_is_preferred_without_changing_dice(side: str) -> None:
    from bowl_bound.sample_teams import sample_teams

    coach = DifficultyCoach(31, *sample_teams(), "hard")
    obs = observation(side=side, possession=side, down=4, distance=10, yards_to_goal=80)
    calls = [coach.offense(replace(obs, play_number=index)) for index in range(300)]
    assert calls.count("punt") > 150
    assert any(call in obs.offense for call in calls)


def test_unknown_utility_policy_is_refused_before_sampling() -> None:
    with pytest.raises(ValueError, match="utility policy"):
        evaluate_action(
            team_chart("Home"),
            team_chart("Away"),
            observation(),
            "1",
            role="offense",
            utility_policy="not-a-policy",
        )
