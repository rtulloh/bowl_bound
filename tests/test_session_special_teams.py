"""Special-teams session decisions and engine-owned legal actions, synthetic only."""

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.session import (
    InvalidDecisionError,
    PendingDecisionError,
    PlaySession,
    SessionFinishedError,
)
from tests.test_special_teams import special_chart, yards


def test_session_offers_punt_and_field_goal_then_commits_a_fair_catch_once() -> None:
    session = PlaySession.new(special_chart("H", punt=yards(40)), special_chart("A"), seed=1)
    assert [action.key for action in session.view().actions.special] == ["punt", "field_goal"]
    before = session.view().state
    pending = session.kick("punt", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert pending.pending and session.view().state == before and session.view().log == ()
    assert session.view().pending.chooser == "A"
    with pytest.raises(PendingDecisionError):
        session.snap("1", "A")
    with pytest.raises(PendingDecisionError):
        session.kick("field_goal")
    with pytest.raises(InvalidDecisionError):
        session.decide("wrong")
    report = session.decide("kick:fair_catch")
    assert report.state_after.possession == "away" and report.state_after.yards_to_goal == 75
    assert report.called_play == "Punt" and report.resolved_play == "Punt"
    assert [entry.section for entry in report.trace] == ["punt"]
    assert session.view().pending is None and len(session.view().log) == 1
    with pytest.raises(PendingDecisionError):
        session.decide("kick:fair_catch")


def test_session_field_goal_updates_score_and_refuses_actions_after_scoring() -> None:
    session = PlaySession.new(special_chart("H", field_goal=yards(65)), special_chart("A"), seed=1)
    report = session.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert report.outcome == "field_goal_good" and session.view().score.home == 3
    assert session.view().finished and session.view().actions.special == ()
    with pytest.raises(SessionFinishedError):
        session.kick("punt")


def test_session_kickoff_only_available_at_start_with_a_supported_home_season() -> None:
    from dataclasses import replace

    home = replace(special_chart("H", kickoff=yards(75)), season=2002)
    session = PlaySession.new(home, special_chart("A"), seed=1)
    assert "kickoff" in [action.key for action in session.view().actions.special]
    report = session.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert report.outcome == "touchback" and report.state_after.yards_to_goal == 80
    assert "kickoff" not in [action.key for action in session.view().actions.special]
    with pytest.raises(InvalidDecisionError):
        session.kick("kickoff")
