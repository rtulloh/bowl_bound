"""Scoring and conversion sessions using invented teams and exact scripted dice."""

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
from bowl_bound.session import (
    InvalidDecisionError,
    PendingDecisionError,
    PlaySession,
    SessionFinishedError,
)
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def snap_dice(*extra: OffensiveRoll) -> ScriptedDice:
    return ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), *extra])


def touchdown_session() -> PlaySession:
    session = PlaySession.new(
        team_chart("Home", offense=2), team_chart("Away", defense=0), seed=1, start_yards_to_goal=2
    )
    session.snap("1", "A", dice=snap_dice())
    return session


def test_touchdown_awards_six_once_and_requires_conversion_before_more_plays() -> None:
    session = touchdown_session()
    view = session.view()
    assert view.score.home == 6 and not view.finished
    assert view.phase == "conversion_choice"
    assert view.pending.chooser == "Home"
    assert [c.id for c in view.pending.choices] == ["conversion:kick", "conversion:two"]
    assert [e.points for e in view.scoring] == [6]
    assert view.scoring[0].kind == "touchdown" and view.scoring[0].team == "Home"
    with pytest.raises(PendingDecisionError):
        session.snap("1", "A")
    with pytest.raises(PendingDecisionError):
        session.kick("punt")
    with pytest.raises(InvalidDecisionError):
        session.decide("wrong")
    assert session.view() == view


@pytest.mark.parametrize("good", [False, True])
def test_pat_uses_dedicated_data_then_completes_the_scoring_demo(good: bool) -> None:
    home = team_chart("Home", offense=2)
    home = replace(home, pat_outcomes=tuple(replace(row, good=good) for row in home.pat_outcomes))
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=2)
    session.snap("1", "A", dice=snap_dice())
    report = session.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert report.outcome == ("pat_good" if good else "pat_missed")
    assert [t.section for t in report.trace] == ["pat"]
    assert session.view().score.home == 6 + int(good)
    assert session.view().finished and session.view().pending is None
    assert len(session.view().log) == 2
    assert sum(e.points for e in session.view().scoring) == 6 + int(good)
    with pytest.raises(PendingDecisionError):
        session.decide("conversion:kick")
    with pytest.raises(SessionFinishedError):
        session.snap("1", "A")


@pytest.mark.parametrize(("gain", "expected"), [(2, 8), (1, 6), (0, 6), (-1, 6)])
def test_two_point_try_starts_at_two_and_consumes_only_one_live_play(
    gain: int, expected: int
) -> None:
    session = touchdown_session()
    session.decide("conversion:two")
    view = session.view()
    assert view.phase == "two_point_try" and view.state.yards_to_goal == 2
    assert view.pending is None and view.actions.special == ()
    # Try play two is independent of the touchdown play.
    session._charts[session.possession] = team_chart("Home", offense=gain)
    report = session.snap("2", "A", dice=snap_dice())
    assert report.outcome == ("two_point_good" if expected == 8 else "two_point_failed")
    assert session.view().score.home == expected and session.view().score.away == 0
    assert session.view().finished and report.state_after is None
    assert len(session.view().log) == 2


def test_two_point_interception_return_awards_defense_two_not_six_or_another_try() -> None:
    home = team_chart(
        "Home",
        offense=2,
        plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=0)},
    )
    away = special_chart(
        "Away", interception_return=NormalizedCell(ResultKind.TOUCHDOWN, provenance())
    )
    away = replace(away, defense=team_chart("Away", defense=0).defense)
    session = PlaySession.new(home, away, seed=1, start_yards_to_goal=2)
    session.snap("1", "A", dice=snap_dice())
    session.decide("conversion:two")
    session.snap("9", "A", dice=snap_dice(OffensiveRoll(1, 1, 0)))
    assert session.view().score.away == 0
    report = session.decide("interception:return")
    assert report.outcome == "conversion_return"
    assert (session.view().score.home, session.view().score.away) == (6, 2)
    assert session.view().finished and session.view().pending is None
    assert [e.points for e in session.view().scoring] == [6, 2]


def test_try_penalty_acceptance_replays_from_enforced_spot_without_scoring() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 1),
    )
    home = team_chart("Home", offense=2, plays={Play.EIGHT: foul})
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=2)
    session.snap("1", "A", dice=snap_dice())
    session.decide("conversion:two")
    session.snap("8", "A", dice=snap_dice())
    assert session.view().score.home == 6
    session.decide("accept:0:previous")
    assert not session.view().finished and session.view().phase == "two_point_try"
    assert session.view().state.yards_to_goal == 1
    session.snap("1", "A", dice=snap_dice())
    assert session.view().score.home == 8
    assert [e.points for e in session.view().scoring] == [6, 2]


def test_ordinary_safety_awards_two_and_does_not_offer_a_conversion() -> None:
    session = PlaySession.new(
        team_chart("Home", offense=-5),
        team_chart("Away", defense=0),
        seed=1,
        start_yards_to_goal=95,
    )
    report = session.snap("1", "A", dice=snap_dice())
    assert report.supported and report.outcome == "safety"
    assert session.view().score.away == 2 and session.view().finished
    assert session.view().pending is None
    assert [e.kind for e in session.view().scoring] == ["safety"]


def test_field_goal_ledger_awards_three_without_a_conversion() -> None:
    session = PlaySession.new(
        special_chart("Home", field_goal=yards(40)),
        team_chart("Away"),
        seed=1,
        start_yards_to_goal=40,
    )
    session.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert session.view().score.home == 3 and session.view().finished
    assert [e.kind for e in session.view().scoring] == ["field_goal"]


@pytest.mark.parametrize("choice", ["interception:return", "interception:decline"])
def test_non_scoring_interception_completes_try_without_another_down(choice: str) -> None:
    home = team_chart(
        "Home",
        offense=2,
        plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=0)},
    )
    away = special_chart("Away", interception_return=yards(10))
    away = replace(away, defense=team_chart("Away", defense=0).defense)
    session = PlaySession.new(home, away, seed=1, start_yards_to_goal=2)
    session.snap("1", "A", dice=snap_dice())
    session.decide("conversion:two")
    session.snap("9", "A", dice=snap_dice(OffensiveRoll(1, 0, 0)))
    report = session.decide(choice)
    assert report.outcome == "two_point_failed"
    assert session.view().finished and session.view().score.home == 6
    assert session.view().score.away == 0 and len(session.view().scoring) == 1


def test_defensive_touchdown_uses_the_defending_teams_pat_data() -> None:
    home = team_chart(
        "Home", plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=0)}
    )
    away = special_chart(
        "Away", interception_return=NormalizedCell(ResultKind.TOUCHDOWN, provenance())
    )
    away = replace(
        away,
        defense=team_chart("Away", defense=0).defense,
        pat_outcomes=tuple(replace(row, good=False) for row in away.pat_outcomes),
    )
    session = PlaySession.new(home, away, seed=1)
    session.snap("9", "A", dice=snap_dice(OffensiveRoll(1, 0, 0)))
    session.decide("interception:return")
    assert session.view().pending.chooser == "Away"
    report = session.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert report.outcome == "pat_missed" and report.trace[0].team == "Away"
    assert session.view().score.away == 6


@pytest.mark.parametrize("gain", [1, 2])
def test_fumble_recovered_by_offense_can_only_score_when_recovery_reaches_goal(gain: int) -> None:
    home = team_chart(
        "Home",
        offense=2,
        plays={Play.TWO: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=gain)},
    )
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=2)
    session.snap("1", "A", dice=snap_dice())
    session.decide("conversion:two")
    report = session.snap("2", "A", dice=snap_dice(OffensiveRoll(1, 0, 0)))
    assert report.outcome == ("two_point_good" if gain == 2 else "two_point_failed")
    assert session.view().score.home == (8 if gain == 2 else 6)


def test_conversion_setup_and_invalid_choices_do_not_consume_dice() -> None:
    session = touchdown_session()
    sentinel = OffensiveRoll(3, 4, 5)
    dice = ScriptedDice([sentinel])
    with pytest.raises(InvalidDecisionError):
        session.decide("wrong", dice=dice)
    report = session.decide("conversion:two", dice=dice)
    assert report.trace == () and dice.offensive() == sentinel
    assert len(session.view().log) == 1 and len(session.view().scoring) == 1


@pytest.mark.parametrize(
    ("code", "distance"), [(PenaltyCode.FIVE_YARDS, 5), (PenaltyCode.FIXED, 15)]
)
def test_successful_try_can_carry_defensive_foul_to_following_kickoff(
    code: PenaltyCode, distance: int
) -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(
            PenaltyTeam.DEFENSE, code, distance if code is PenaltyCode.FIXED else None
        ),
    )
    home = team_chart("Home", offense=2)
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=foul) if row.play is Play.TWO and row.roll == 10 else row
            for row in home.offense
        ),
    )
    session = PlaySession.new(home, team_chart("Away", defense=0), seed=1, start_yards_to_goal=2)
    session.snap("1", "A", dice=snap_dice())
    session.decide("conversion:two")
    session.snap("2", "A", dice=snap_dice(OffensiveRoll(2, 0, 0)))
    pending = session.view().pending
    choice = next(c for c in pending.choices if c.id == "accept:0:kickoff")
    assert choice.enabled and session.view().score.home == 6
    report = session.decide(choice.id)
    assert report.outcome == "two_point_good" and session.view().score.home == 8
    assert session.view().finished
    carry = session.view().kickoff_penalties[0]
    assert carry.team == "Away" and carry.yards == distance
    assert report.description.endswith(
        f"{distance}-yard defensive penalty carried to the following kickoff."
    )
    before = session.view()
    with pytest.raises(PendingDecisionError):
        session.decide(choice.id)
    assert session.view() == before


def test_unsuccessful_try_has_no_kickoff_carry_choice() -> None:
    from tests.test_session_penalties import chart, foul

    session = PlaySession.new(
        chart(foul(PenaltyTeam.DEFENSE, 15), yards(1)),
        team_chart("Away", defense=0),
        seed=1,
        start_yards_to_goal=1,
    )
    # Play two scores a touchdown; play one is a foul followed by a short try gain.
    session.snap("2", "A", dice=snap_dice())
    session.decide("conversion:two")
    session.snap("1", "A", dice=snap_dice(OffensiveRoll(2, 0, 0)))
    assert all(c.id != "accept:0:kickoff" for c in session.view().pending.choices)
