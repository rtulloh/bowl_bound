"""Actual pending saves preserve one committed event and literal BB accounting.

These are forced synthetic subjects, not evidence that every pending state in a
historical game was observed. Save/replay equality is checked alongside independent
owner, credit, position and zero-premature-commit expectations.
"""

from dataclasses import asdict, replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll
from bowl_bound.models import NormalizedCell, PenaltyCode, PenaltyData, PenaltyTeam, ResultKind
from bowl_bound.save_game import dumps_game, loads_game
from tests.synthetic_teams import yards
from tests.test_game_audit_typed_capture import fixed_save_clock as fixed_save_clock
from tests.test_models import provenance
from tests.test_save_game import charts, new
from tools.game_audit_capture import capture_receipts
from tools.game_audit_envelope import audit_capture_links


@pytest.mark.parametrize(
    "case,choices,credit,owner,goal,down,distance",
    [
        ("interception", ("interception:decline",), "incomplete", "home", 65, 2, 10),
        ("interception", ("interception:return",), "interception", "away", 30, 1, 10),
        (
            "endzone",
            ("interception:return", "end_zone:touchback"),
            "interception",
            "away",
            80,
            1,
            10,
        ),
        ("penalty", ("accept:0:previous",), "excluded", "home", 60, 1, 5),
        ("penalty", ("decline",), "completion", "home", 57, 2, 2),
    ],
)
def test_pending_save_has_no_credit_until_one_resolved_commit(
    case, choices, credit, owner, goal, down, distance, fixed_save_clock
) -> None:
    cell = (
        NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
        )
        if case == "penalty"
        else NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15)
    )
    teams = charts(cell=cell)
    if case == "penalty":
        teams = tuple(
            replace(
                team,
                offense=tuple(
                    replace(row, cell=yards(8)) if row.play.value == 9 and row.roll != 10 else row
                    for row in team.offense
                ),
            )
            for team in teams
        )
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    rolls += [OffensiveRoll(2, 0, 0) for _ in range(4)]
    subject = new(teams=teams, rolls=rolls, spot=10 if case == "endzone" else 65)
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        pending = subject.snap("9", "A")
        assert pending.pending is True
        assert asdict(pending.statistics) == dict(
            kind="excluded", team=None, yards=0, touchdown=False
        )
        assert len(subject.view().log) == 0
        initial_boxes = asdict(subject.view().statistics)
        assert subject.view().score.home == subject.view().score.away == 0
        for index, choice in enumerate(choices):
            saved = dumps_game(subject)
            restored = loads_game(saved, lambda key: teams[0] if key == "2002/home" else teams[1])
            assert dumps_game(restored) == saved
            left, right = subject.decide(choice), restored.decide(choice)
            assert left == right
            assert dumps_game(subject) == dumps_game(restored)
            if index < len(choices) - 1:
                assert left.pending is True
                assert len(subject.view().log) == 0
                assert asdict(subject.view().statistics) == initial_boxes
                assert subject.view().score.home == subject.view().score.away == 0
        view = subject.view()
    assert len(view.log) == 1
    report = view.log[0]
    assert report.pending is False
    assert report.statistics.kind.value == credit
    assert (
        report.statistics.team.value == "home"
        if credit != "excluded"
        else report.statistics.team is None
    )
    assert report.statistics.yards == (8 if credit == "completion" else 0)
    assert report.statistics.touchdown is False
    assert view.state.possession == owner
    assert (view.state.yards_to_goal, view.state.down, view.state.yards_to_go) == (
        goal,
        down,
        distance,
    )
    assert view.score.home == view.score.away == 0
    box = view.statistics.home
    assert box.rushing_attempts == box.rushing_yards == box.sacks_taken == 0
    assert box.passing_attempts == int(credit != "excluded")
    assert box.completions == int(credit == "completion")
    assert box.passing_yards == (8 if credit == "completion" else 0)
    assert box.interceptions == int(credit == "interception")
    assert view.statistics.away.total_plays == view.statistics.away.total_yards == 0
    linkage = audit_capture_links(capture.payload())
    assert linkage["report_revision_address_linkage"] == "GO"
