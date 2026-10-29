"""Synthetic actor labels from structured facts, never private rosters."""

import json
from dataclasses import asdict, replace
from random import getstate

import pytest

from bowl_bound.game_state import Possession
from bowl_bound.roster import Roster, parse_roster
from bowl_bound.session import PlayReport, PlaySession, TraceEntry
from bowl_bound.statistics import PlayStatistics, StatKind
from tests.synthetic_teams import team_chart


def report(kind: StatKind = StatKind.RUSH, side: str = "home") -> PlayReport:
    game = PlaySession(team_chart("Home"), team_chart("Away"), 7, 65)
    original = game.snap("1", "A")
    return replace(
        original,
        statistics=PlayStatistics(kind, Possession(side), -4 if kind is StatKind.SACK else 4),
        outcome="defensive_recovery" if kind is StatKind.INTERCEPTION else "advance",
        state_before=replace(original.state_before, possession=side),
        description="Recorded engine facts.",
    )


def roster(prefix: str) -> Roster:
    return parse_roster(
        json.dumps(
            {
                "qb": [prefix + " Quill", prefix + " Reed"],
                "rb": [prefix + " Bolt"],
                "wr": [prefix + " Finch"],
            }
        )
    )


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize(
    "kind,expected,absent",
    [
        (StatKind.RUSH, "H Bolt", "H Quill"),
        (StatKind.COMPLETE, "H Finch", "H Bolt"),
        (StatKind.INCOMPLETE, "H Quill", "H Finch"),
        (StatKind.SACK, "H Quill", "H Finch"),
        (StatKind.INTERCEPTION, "H Quill", "H Finch"),
    ],
)
def test_structured_credit_selects_illustrative_roles(
    side: str, kind: StatKind, expected: str, absent: str
) -> None:
    from bowl_bound.commentary import narrate_report

    before = report(kind, side)
    home, away = (roster("H"), roster("A")) if side == "home" else (roster("A"), roster("H"))
    rendered = narrate_report(before, home, away)
    assert expected in rendered and absent not in rendered
    if kind is StatKind.COMPLETE:
        assert "H Quill" in rendered
    assert "defender:" not in rendered and "tackler:" not in rendered
    assert all(name not in rendered for name in ("A Quill", "A Reed", "A Bolt", "A Finch"))
    assert "Illustrative players" not in rendered
    assert before.commentary not in rendered
    assert before.description == "Recorded engine facts."


@pytest.mark.parametrize("flag", ["pending", "unsupported", "excluded", "missing_team"])
def test_uncommitted_or_ambiguous_results_remain_generic(flag: str) -> None:
    from bowl_bound.commentary import narrate_report

    original = report()
    changed = {
        "pending": {"pending": True},
        "unsupported": {"supported": False},
        "excluded": {"statistics": PlayStatistics()},
        "missing_team": {"statistics": PlayStatistics(StatKind.RUSH)},
    }[flag]
    value = replace(original, **changed)
    assert narrate_report(value, roster("H"), roster("A")) == value.commentary


@pytest.mark.parametrize("section", ["supplemental:QR", "supplemental:QT"])
def test_active_qb_branch_names_quarterback_not_running_back(section: str) -> None:
    from bowl_bound.commentary import narrate_report

    value = replace(report(), trace=(TraceEntry(section, "Home", "", None, {}, ""),))
    assert "H Quill" in narrate_report(value, roster("H"))
    assert "H Bolt" not in narrate_report(value, roster("H"))
    discarded = replace(
        value, trace=value.trace + (TraceEntry("penalty_reroll", "Home", "", None, {}, ""),)
    )
    assert "H Bolt" in narrate_report(discarded, roster("H"))
    assert "H Quill" not in narrate_report(discarded, roster("H"))
    active = replace(discarded, trace=discarded.trace + value.trace)
    assert "H Quill" in narrate_report(active, roster("H"))
    assert "H Bolt" not in narrate_report(active, roster("H"))


def test_fumble_actor_is_not_guessed_from_rushing_credit() -> None:
    from bowl_bound.commentary import narrate_report

    value = replace(report(), trace=(TraceEntry("fumble_recovery", "Home", "", None, {}, ""),))
    assert narrate_report(value, roster("H")) == value.commentary


def test_generic_fallback_and_partial_rosters() -> None:
    from bowl_bound.commentary import narrate_report

    value = report(StatKind.COMPLETE)
    assert "The quarterback finds the receiver for 4 yards." == narrate_report(value)
    assert narrate_report(value, parse_roster("{}")) == narrate_report(value)
    partial = parse_roster('{"qb":["Alex Quill"]}')
    assert "Alex Quill finds the receiver for 4 yards." == narrate_report(value, partial)


def test_names_use_report_index_without_mutating_report_roster_or_rng() -> None:
    from bowl_bound.commentary import narrate_report

    value = replace(report(StatKind.INCOMPLETE), number=2)
    names = roster("H")
    before, random, before_names = asdict(value), getstate(), asdict(names)
    assert "H Reed" in narrate_report(value, names)
    assert len({narrate_report(value, names) for _ in range(10)}) == 1
    assert asdict(value) == before and getstate() == random
    assert asdict(names) == before_names


@pytest.mark.parametrize("number,expected", [(0, "H Quill"), (-1, "H Quill"), (3, "H Quill")])
def test_index_clamps_and_wraps(number: int, expected: str) -> None:
    from bowl_bound.commentary import narrate_report

    assert expected in narrate_report(
        replace(report(StatKind.INCOMPLETE), number=number), roster("H")
    )


def test_statistics_team_not_final_possession_selects_names() -> None:
    from bowl_bound.commentary import narrate_report

    value = replace(report(), state_before=replace(report().state_before, possession="away"))
    assert "H Bolt" in narrate_report(value, roster("H"), roster("A"))


def test_real_bad_snap_remains_generic() -> None:
    from bowl_bound.commentary import narrate_report
    from bowl_bound.dice import OffensiveRoll
    from bowl_bound.models import (
        NormalizedCell,
        PenaltyCode,
        PenaltyData,
        PenaltyTeam,
        Play,
        ResultKind,
    )
    from tests.test_models import provenance
    from tests.test_statistics import dice, session_for

    foul = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S)
    )
    game = session_for(foul, Play.NINE)
    value = game.snap(
        "9", "A", hurried=True, dice=dice(OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0))
    )
    assert value.statistics.kind is StatKind.RUSH
    assert narrate_report(value, roster("H")) == value.commentary
