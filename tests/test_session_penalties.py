"""Session-level penalty decisions use only prepared engine outcomes."""

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
)
from bowl_bound.session import PlaySession
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


def foul(team: PenaltyTeam, yards_value: int = 5) -> NormalizedCell:
    return NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(team, PenaltyCode.FIXED, yards_value)
    )


def chart(first: NormalizedCell, second: NormalizedCell) -> object:
    base = team_chart("Home", plays={Play.ONE: first})
    return replace(
        base,
        offense=tuple(
            replace(row, cell=second) if row.play is Play.ONE and row.roll == 20 else row
            for row in base.offense
        ),
    )


def test_penalty_snap_waits_for_explicit_choice_without_extra_dice() -> None:
    home = chart(foul(PenaltyTeam.DEFENSE), yards(7))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1)
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0), sentinel]
    )

    before = session.view().state
    report = session.snap("1", "A", dice=dice)

    assert report.outcome == "penalty_pending" and report.pending and report.supported
    assert session.view().state == before
    pending = session.view().pending
    assert pending is not None and pending.chooser == "Home"
    assert [choice.id for choice in pending.choices] == [
        "accept:0:previous",
        "accept:0:end",
        "decline",
    ]
    with pytest.raises(RuntimeError, match="penalty decision"):
        session.snap("1", "A", dice=dice)
    assert dice.offensive() == sentinel


def test_accepting_one_of_multiple_penalties_does_not_sum_them() -> None:
    home = chart(foul(PenaltyTeam.DEFENSE, 5), foul(PenaltyTeam.DEFENSE, 15))
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=yards(3)) if row.play is Play.ONE and row.roll == 30 else row
            for row in home.offense
        ),
    )
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1)
    pending = session.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
            ]
        ),
    )
    assert pending.pending

    report = session.decide("accept:1:previous")

    assert report.outcome == "penalty_accepted"
    assert report.state_after is not None and report.state_after.spot == "midfield"
    assert len(session.view().log) == 1


def test_decline_applies_the_prepared_result_once_and_stale_decision_does_not_mutate() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE), yards(7))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1)
    session.snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )

    report = session.decide("decline")

    assert report.outcome == "advance" and report.yards == 7
    after = session.view().state
    with pytest.raises(RuntimeError, match="no penalty decision"):
        session.decide("decline")
    assert session.view().state == after and len(session.view().log) == 1


def test_offsetting_and_pre_snap_penalties_are_automatic() -> None:
    offset = chart(foul(PenaltyTeam.OFFENSE), foul(PenaltyTeam.DEFENSE))
    offset_report = PlaySession.new(offset, team_chart("Away"), seed=1).snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )
    assert offset_report.outcome == "offsetting" and not offset_report.pending

    presnap = chart(
        NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S),
        ),
        yards(7),
    )
    report = PlaySession.new(presnap, team_chart("Away"), seed=1).snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 2, 2)]),
    )
    assert report.outcome == "pre_snap" and not report.pending


def test_pi_decline_applies_incomplete_and_turnover_decline_continues_pending_choice() -> None:
    pi = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 12),
    )
    pi_session = PlaySession.new(
        team_chart("Home", plays={Play.ONE: pi}), team_chart("Away"), seed=1
    )
    pi_session.snap("1", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))
    report = pi_session.decide("decline")
    assert (
        report.outcome == "advance"
        and report.state_after is not None
        and report.state_after.down == 2
    )

    turnover = chart(
        foul(PenaltyTeam.OFFENSE), NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)
    )
    session = PlaySession.new(turnover, team_chart("Away", defense=0), seed=1)
    session.snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )
    assert session.view().pending is not None
    decline = next(choice for choice in session.view().pending.choices if choice.id == "decline")
    assert decline.enabled and decline.reason is None
    assert session.decide("decline").outcome == "interception_pending"
    assert session.decide("interception:decline").outcome == "declined_interception"
    assert len(session.view().log) == 1


def test_accepting_a_penalty_cancels_a_touchdown_gain_instead_of_crashing() -> None:
    """Found by the real-chart smoke run: the play's yards must not matter once it is cancelled."""
    home = chart(foul(PenaltyTeam.DEFENSE), yards(40))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=20)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    session.snap("1", "A", dice=dice)
    pending = session.view().pending
    assert pending is not None
    end = next(c for c in pending.choices if c.id == "accept:0:end")
    assert not end.enabled  # a touchdown gain cannot be marked from the end of the gain
    report = session.decide("accept:0:previous")
    assert report.outcome == "penalty_accepted"
    state = session.view().state
    assert state is not None and state.yards_to_goal == 15 and state.down == 1
    assert not session.view().finished


def test_accepting_a_penalty_cancels_a_gain_into_the_own_end_zone() -> None:
    home = chart(foul(PenaltyTeam.DEFENSE), yards(-30))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=90)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    session.snap("1", "A", dice=dice)
    session.decide("accept:0:previous")
    state = session.view().state
    assert state is not None and state.yards_to_goal == 85


def s_foul(team: PenaltyTeam) -> NormalizedCell:
    return NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(team, PenaltyCode.S, None)
    )


def test_pre_snap_foul_after_an_earlier_foul_enforces_the_pre_snap_penalty() -> None:
    """Review defect 1: the enforced penalty must be the 5A, not the first foul rolled."""
    home = chart(foul(PenaltyTeam.OFFENSE, 10), s_foul(PenaltyTeam.OFFENSE))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),  # offense cell: OFF 10
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),  # reroll: OFF S
            OffensiveRoll(2, 0, 0),  # S table total 20 -> 5A (5 yards, pre-snap)
        ]
    )
    report = session.snap("1", "A", dice=dice)
    assert report.outcome == "pre_snap"
    state = session.view().state
    # Five yards back from the own 35 is the own 30 (70 to goal); the 10-yard foul would give 25.
    assert state is not None and state.yards_to_goal == 70 and state.spot == "own 30"


def decline_into_safety_session() -> PlaySession:
    home = chart(foul(PenaltyTeam.DEFENSE), yards(-7))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=95)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    session.snap("1", "A", dice=dice)
    return session


def test_decline_is_enabled_when_the_result_would_be_a_safety() -> None:
    """Milestone 14 resolves safeties, so declining is now a legal choice."""
    pending = decline_into_safety_session().view().pending
    assert pending is not None
    decline = next(c for c in pending.choices if c.id == "decline")
    assert decline.enabled and decline.reason is None


def test_declining_applies_the_safety_once_and_closes_the_decision() -> None:
    session = decline_into_safety_session()
    report = session.decide("decline")
    assert report.outcome == "safety" and report.supported
    assert session.view().score.away == 2 and session.view().finished
    assert session.view().pending is None and len(session.view().log) == 1
    before = session.view()
    with pytest.raises(RuntimeError):
        session.decide("decline")
    assert session.view() == before
