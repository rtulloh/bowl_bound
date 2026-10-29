"""Player-facing wording is supplied by the engine, not inferred from chart traces."""

from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.session import PlaySession
from tests.synthetic_teams import team_chart
from tests.test_special_teams import special_chart, yards


@pytest.mark.parametrize(
    "distance,expected", [(68, "3 yards deep"), (40, "own 25"), (75, "beyond the end line")]
)
def test_kickoff_description_has_named_origin_distance_and_landing(
    distance: int, expected: str
) -> None:
    home = team_chart("Home", season=2002)
    away = team_chart("Away", season=2002)
    home = replace(home, special_teams=special_chart("Home", kickoff=yards(distance)).special_teams)
    game = PlaySession.new(home, away, seed=1)
    report = game.kick(
        "kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)])
    )
    assert "Home" in report.description and "Away" in report.description
    assert "own 35" in report.description and f"{distance} yards" in report.description
    assert expected in report.description
    if report.pending:
        assert game.view().pending.chooser == "Away"


def test_completed_return_description_explains_return_and_resulting_spot() -> None:
    home = team_chart("Home", season=2002)
    away = team_chart("Away", season=2002)
    home = replace(home, special_teams=special_chart("Home", kickoff=yards(40)).special_teams)
    away = replace(
        away, special_teams=special_chart("Away", kickoff_return=yards(10)).special_teams
    )
    report = PlaySession.new(home, away, seed=1).kick(
        "kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)])
    )
    assert "returns 10 yards" in report.description
    assert "own 35" in report.description
    assert report.state_after.possession_name == "Away"


def test_punt_context_persists_through_fair_catch_choice() -> None:
    home = team_chart("Home", season=2002)
    away = team_chart("Away", season=2002)
    home = replace(home, special_teams=special_chart("Home", punt=yards(40)).special_teams)
    game = PlaySession.new(home, away, seed=1)
    pending = game.kick("punt", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert "Home punt from own 35: 40 yards" in pending.description
    assert "Away own 25" in pending.description
    report = game.decide("kick:fair_catch")
    assert "Home punt from own 35: 40 yards" in report.description
    assert "Away ball at own 25" in report.description


def test_field_goal_description_names_line_of_scrimmage_and_result() -> None:
    home = team_chart("Home", season=2002)
    away = team_chart("Away", season=2002)
    home = replace(home, special_teams=special_chart("Home", field_goal=yards(70)).special_teams)
    report = PlaySession.new(home, away, seed=1).kick(
        "field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)])
    )
    assert "Home field goal from own 35" in report.description
    assert "70 yards" in report.description and "field goal good" in report.description
