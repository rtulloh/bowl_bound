"""Session-level turnover procedure uses only synthetic charts."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
)
from bowl_bound.session import PendingDecisionError, PlaySession
from tests.synthetic_teams import default_teams, team_chart
from tests.test_models import provenance


def return_chart(name: str, cell: NormalizedCell) -> object:
    chart = team_chart(name)
    return replace(
        chart,
        special_teams=tuple(
            SpecialTeamsCell(
                record.column,
                record.roll,
                cell if record.column is SpecialTeamsColumn.INTERCEPTION_RETURN else record.cell,
            )
            for record in chart.special_teams
        ),
    )


def test_interception_requires_the_defense_to_choose_return_or_incompletion() -> None:
    home, away = default_teams()
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    session = PlaySession.new(home, away, seed=1)

    report = session.snap("9", "A", dice=dice)

    assert report.outcome == "interception_pending" and report.pending
    pending = session.view().pending
    assert pending is not None and pending.chooser == "Beta State"
    assert [choice.id for choice in pending.choices] == [
        "interception:return",
        "interception:decline",
    ]
    with pytest.raises(PendingDecisionError):
        session.snap("1", "A", dice=dice)

    declined = session.decide("interception:decline")
    assert declined.outcome == "declined_interception"
    assert declined.state_after is not None and declined.state_after.situation == "2nd and 10"


def test_a_fumble_uses_the_fumbler_recovery_roll_and_updates_the_live_state() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5)
    home = team_chart("Alpha Tech", plays={Play.ONE: fumble})
    away = team_chart("Beta State", defense=0)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 2, 2)])

    report = PlaySession.new(home, away, seed=1).snap("1", "A", dice=dice)

    assert report.outcome == "offensive_recovery"
    assert report.state_after is not None and report.state_after.spot == "own 40"
    assert [entry.section for entry in report.trace] == ["offense", "defense", "fumble_recovery"]


def test_a_defensive_touchdown_updates_the_engine_scoreboard() -> None:
    home, _ = default_teams()
    away = return_chart("Beta State", NormalizedCell(ResultKind.TOUCHDOWN, provenance()))
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)])
    session = PlaySession.new(home, away, seed=1)

    session.snap("9", "A", dice=dice)
    report = session.decide("interception:return")

    assert report.outcome == "defensive_touchdown" and report.state_after is None
    assert session.view().score.home == 0 and session.view().score.away == 6
    assert not session.view().finished
    assert session.view().pending.chooser == "Beta State"
    session.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert session.view().score.away == 7 and session.view().finished


def test_return_penalty_requires_an_accept_or_decline_decision() -> None:
    home, _ = default_teams()
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, yards=10),
    )
    base = team_chart("Beta State")
    away = replace(
        base,
        special_teams=tuple(
            SpecialTeamsCell(
                row.column,
                row.roll,
                penalty
                if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN and row.roll == 10
                else NormalizedCell(ResultKind.YARDS, provenance(), yards=52)
                if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN and row.roll == 11
                else row.cell,
            )
            for row in base.special_teams
        ),
    )
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
        ]
    )
    session = PlaySession.new(home, away, seed=1)
    session.snap("9", "A", dice=dice)
    pending = session.decide("interception:return")
    assert pending.outcome == "return_penalty_pending"
    assert session.view().pending is not None
    accepted = session.decide("return:accept")
    assert accepted.outcome == "defensive_recovery"
    assert accepted.state_after is not None and accepted.state_after.yards_to_goal == 38


def test_defensive_end_zone_recovery_requires_a_touchback_or_return_choice() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70)
    home = replace(team_chart("Alpha Tech", plays={Play.ONE: fumble}), recovery_range=range(10, 20))
    away = return_chart("Beta State", NormalizedCell(ResultKind.YARDS, provenance(), yards=12))
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(3, 4, 3)])
    session = PlaySession.new(home, away, seed=1)

    pending = session.snap("1", "A", dice=dice)

    assert pending.outcome == "end_zone_recovery_pending"
    assert [choice.id for choice in session.view().pending.choices] == [
        "end_zone:return",
        "end_zone:touchback",
    ]
    touchback = session.decide("end_zone:touchback")
    assert touchback.outcome == "touchback"
    assert touchback.state_after is not None and touchback.state_after.yards_to_goal == 80


def test_defensive_end_zone_recovery_can_be_returned() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70)
    home = replace(team_chart("Alpha Tech", plays={Play.ONE: fumble}), recovery_range=range(10, 20))
    away = return_chart("Beta State", NormalizedCell(ResultKind.YARDS, provenance(), yards=12))
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(3, 4, 3),
            OffensiveRoll(1, 1, 0),
        ]
    )
    session = PlaySession.new(home, away, seed=1)
    session.snap("1", "A", dice=dice)

    returned = session.decide("end_zone:return")

    assert returned.outcome == "defensive_recovery"
    # Recovery was five yards inside the end zone: a 12-yard return reaches own 7.
    assert returned.state_after is not None and returned.state_after.yards_to_goal == 93
    assert [entry.section for entry in returned.trace][-2:] == [
        "fumble_recovery",
        "end_zone_recovery_return",
    ]
