"""Milestone 10 engine session: one real play at a time, with engine-owned labels."""

from random import Random

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, RandomDice, ScriptedDice
from bowl_bound.game_state import Possession
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.session import PendingDecisionError, PlaySession
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_models import provenance


def new_session(seed: int = 7, **kwargs: object) -> PlaySession:
    home, away = default_teams()
    return PlaySession.new(home, away, seed=seed, **kwargs)


def test_new_session_starts_first_and_ten_at_the_own_35() -> None:
    state = new_session().view().state
    assert (state.possession, state.down, state.yards_to_go) == ("home", 1, 10)
    assert state.spot == "own 35" and state.situation == "1st and 10"
    assert state.ball_from_left == 35 and state.first_down_from_left == 45
    assert state.attacking == "right" and state.possession_name == "Alpha Tech"


def test_actions_and_labels_come_from_the_engine() -> None:
    actions = new_session().view().actions
    assert [(a.key, a.label) for a in actions.offense] == [
        ("1", "Line Plunge"),
        ("2", "Counter"),
        ("3", "End Reverse"),
        ("4", "Draw"),
        ("5", "Option"),
        ("6", "Screen"),
        ("7", "Sprint Out"),
        ("8", "Boot-leg"),
        ("9", "Drop Back"),
    ]
    assert [a.key for a in actions.defense] == list("ABCDEF")
    assert [a.label for a in actions.defense] == [
        "Standard",
        "Short yardage (gaps)",
        "Short yardage (wide)",
        "Pass prevent (short)",
        "Pass prevent (long)",
        "Blitz",
    ]


def test_an_ordinary_play_adds_offense_and_defense_and_moves_the_ball() -> None:
    session = new_session()
    report = session.snap("1", "A")
    assert report.supported and report.pending is False
    assert report.yards == 6  # 4 (offense) + 2 (the away defense)
    assert report.called_play == "Line Plunge" and report.resolved_play == "Line Plunge"
    assert report.defense == "A Standard"
    assert report.state_before.situation == "1st and 10"
    assert report.state_after is not None and report.state_after.situation == "2nd and 4"
    assert report.state_after.spot == "own 41"
    assert report.description.startswith("Alpha Tech: Line Plunge vs A Standard")
    assert "6 yards" in report.description
    assert session.view().state.situation == "2nd and 4"


def test_the_trace_holds_the_two_real_rolls_and_cells() -> None:
    home, away = default_teams()
    first, second = OffensiveRoll(1, 2, 3), DefensiveRoll(2, 1)
    session = PlaySession.new(home, away, seed=1)
    report = session.snap("1", "C", dice=ScriptedDice([first, second]))
    assert [t.section for t in report.trace] == ["offense", "defense"]
    off, dfn = report.trace
    assert (off.team, off.play, off.formation) == ("Alpha Tech", "Line Plunge", None)
    assert (dfn.team, dfn.play, dfn.formation) == ("Beta State", "Line Plunge", "Formation C")
    assert off.roll == {
        "faces": [1, 2, 3],
        "total": 15,
        "dice_label": "Offensive dice",
        "dice": [
            {"role": "black", "label": "Black", "color": "black", "face": 1},
            {"role": "white_one", "label": "White 1", "color": "white", "face": 2},
            {"role": "white_two", "label": "White 2", "color": "white", "face": 3},
        ],
    }
    assert dfn.roll == {
        "faces": [2, 1],
        "total": 3,
        "dice_label": "Defensive dice",
        "dice": [
            {"role": "red", "label": "Red", "color": "red", "face": 2},
            {"role": "green", "label": "Green", "color": "green", "face": 1},
        ],
    }
    assert off.cell == "4" and dfn.cell == "2"


def test_a_touchdown_requires_a_conversion_before_more_scrimmage() -> None:
    session = new_session(start_yards_to_goal=5)
    report = session.snap("1", "A")
    assert report.outcome == "touchdown" and report.state_after is None
    assert report.description.endswith("Touchdown for Alpha Tech")
    view = session.view()
    assert not view.finished and view.state is None
    assert view.pending.chooser == "Alpha Tech"
    with pytest.raises(PendingDecisionError):
        session.snap("1", "A")


def test_four_failed_downs_hand_the_ball_to_the_other_team() -> None:
    home = team_chart("Alpha Tech", offense=0, defense=0)
    away = team_chart("Beta State", offense=0, defense=0)
    session = PlaySession.new(home, away, seed=3)
    for _ in range(3):
        assert session.snap("1", "A").outcome == "advance"
    last = session.snap("1", "A")
    assert last.outcome == "turnover_on_downs"
    after = last.state_after
    assert after is not None and after.possession == "away"
    assert after.possession_name == "Beta State" and after.situation == "1st and 10"
    # The ball has not moved: home's own 35 is the opponent 35 for the away team.
    assert after.attacking == "left" and after.spot == "opponent 35"
    assert after.ball_from_left == 35 and after.first_down_from_left == 25


def test_option_play_reports_both_the_called_and_the_resolved_play() -> None:
    sop = NormalizedCell(ResultKind.SPRINT_OUT_PASS, provenance())
    home = team_chart("Alpha Tech", offense=4, plays={Play.FIVE: sop})
    away = team_chart("Beta State", defense=2)
    report = PlaySession.new(home, away, seed=2).snap("5", "A")
    assert report.called_play == "Option" and report.resolved_play == "Sprint Out"
    assert [t.section for t in report.trace] == ["offense", "defense", "option"]
    assert report.supported and report.yards == 4


def test_an_interception_waits_for_an_explicit_engine_owned_decision() -> None:
    session = new_session()
    before = session.view().state
    report = session.snap("9", "A")  # forced interception
    assert report.supported and report.pending and report.outcome == "interception_pending"
    assert report.state_after == before
    pending = session.view().pending
    assert pending is not None and [choice.id for choice in pending.choices] == [
        "interception:return",
        "interception:decline",
    ]
    assert session.view().log == ()


def test_invalid_selections_are_rejected_before_any_dice_are_consumed() -> None:
    session = new_session()
    sentinel = OffensiveRoll(1, 0, 0)
    dice = ScriptedDice([sentinel])
    for play, formation in (("0", "A"), ("10", "A"), ("1", "G"), ("x", "A"), ("1", ""), (1, "A")):
        with pytest.raises(ValueError):
            session.snap(play, formation, dice=dice)  # type: ignore[arg-type]
    assert dice.offensive() == sentinel and session.view().log == ()


def test_same_seed_gives_identical_reports_and_different_seed_can_differ() -> None:
    def run(seed: int) -> list[tuple[object, ...]]:
        session = new_session(seed)
        return [
            (r.yards, r.description, tuple(t.roll["total"] for t in r.trace))
            for r in (session.snap("1", "A") for _ in range(3))
        ]

    assert run(11) == run(11)
    assert any(run(11) != run(s) for s in range(12, 20))


def test_the_session_uses_its_own_random_stream() -> None:
    session = new_session(5)
    rng = Random(5)
    expected = RandomDice(rng)
    first_roll, second_roll = expected.offensive(), expected.defensive()
    report = session.snap("1", "A")
    assert report.trace[0].roll["total"] == first_roll.total
    assert report.trace[1].roll["total"] == second_roll.total


def test_the_log_records_every_snap_with_numbered_entries() -> None:
    session = new_session()
    session.snap("1", "A")
    session.snap("2", "B")
    log = session.view().log
    assert [e.number for e in log] == [1, 2]
    assert log[1].called_play == "Counter" and log[1].defense == "B Short yardage (gaps)"


def test_possession_names_follow_the_team_not_the_side() -> None:
    session = new_session()
    view = session.view()
    assert view.home == "Alpha Tech" and view.away == "Beta State"
    assert session.possession is Possession.HOME


def test_the_same_chart_object_for_both_sides_is_allowed_for_a_mirror_match() -> None:
    chart = team_chart("Mirror U", offense=3, defense=1)
    assert PlaySession.new(chart, chart, seed=1).snap("1", "A").yards == 4


def test_yards_helper_builds_a_real_normalized_cell() -> None:
    assert yards(5).yards == 5 and yards(5).kind is ResultKind.YARDS
