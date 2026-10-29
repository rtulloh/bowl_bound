"""Existing synthetic fumble facts used by the UI, with no engine changes."""

from dataclasses import replace

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.session import PlaySession
from tests.synthetic_teams import team_chart
from tests.test_models import provenance


def test_existing_touchback_records_fumble_recovery_without_extra_rolls() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2)
    home = replace(team_chart("Alpha Tech", plays={Play.ONE: fumble}), recovery_range=range(10, 20))
    away = team_chart("Beta State", defense=0)
    sentinel = OffensiveRoll(1, 4, 5)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(3, 0), OffensiveRoll(2, 4, 4), sentinel]
    )
    session = PlaySession.new(home, away, seed=1, start_yards_to_goal=2)
    pending = session.snap("1", "C", dice=dice)
    assert pending.outcome == "end_zone_recovery_pending"
    report = session.decide("end_zone:touchback")
    assert report.description.endswith(" - touchback.")
    assert report.outcome == "touchback" and report.yards == 2
    assert report.state_after is not None
    assert report.state_after.possession_name == "Beta State"
    assert report.state_after.spot == "own 20"
    assert [entry.section for entry in report.trace] == ["offense", "defense", "fumble_recovery"]
    assert dice.offensive() == sentinel
