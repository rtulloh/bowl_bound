"""Canonical calibration counters follow committed Bowl Bound engine credit.

These bounded synthetic sequences are observer controls, not complete-game
certification. In particular, Bowl Bound includes sacks in rushing attempts and
credits a zero-yard QT as a rush; Paydirt's NFL boundaries are not imported.
"""

from dataclasses import replace
from typing import Any

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    SpecialTeamsColumn,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.session import PlayReport, PlaySession
from bowl_bound.statistics import StatKind, summarize
from tests.synthetic_teams import metadata, team_chart, yards
from tests.test_models import provenance
from tools.chartgen.primary_fumbles import observe_primary_results
from tools.chartgen.refine import aggregate_games
from tools.chartgen.research_runner import _json_value


def _with_return(chart: TeamChart, gain: int) -> TeamChart:
    return replace(
        chart,
        special_teams=tuple(
            replace(row, cell=yards(gain))
            if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN
            else row
            for row in chart.special_teams
        ),
    )


def _sample(
    *, qt: bool, fumble: bool, initial: int, retained: bool, advance: int | None
) -> tuple[dict[str, Any], tuple[PlayReport, ...]]:
    terminal = NormalizedCell(
        ResultKind.FUMBLE if fumble else ResultKind.YARDS, provenance(), yards=initial
    )
    home = team_chart(
        "A",
        season=2007,
        defense=0,
        plays={
            Play.ONE: yards(2),
            Play.EIGHT: yards(7),
            Play.NINE: NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance())
            if qt
            else terminal,
        },
    )
    home = replace(
        home,
        supplemental=tuple(
            replace(row, cell=terminal)
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in home.supplemental
        ),
    )
    home = _with_return(home, advance or 0)
    away = _with_return(team_chart("B", season=2007, defense=0), advance or 0)
    session = PlaySession.new(home, away, seed=1, start_yards_to_goal=65)
    reports = []
    for choice in ("1", "8"):
        reports.append(
            session.snap(
                choice,
                "A",
                dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]),
            )
        )
    recovery = (
        (OffensiveRoll(1, 3, 4) if retained else OffensiveRoll(3, 3, 4))
        if advance is not None
        else (OffensiveRoll(1, 2, 2) if retained else OffensiveRoll(3, 1, 5))
    )
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    if qt:
        rolls.append(OffensiveRoll(1, 1, 0))
    if fumble:
        rolls.extend([recovery, OffensiveRoll(1, 0, 0)])
    reports.append(session.snap("9", "A", dice=ScriptedDice(rolls)))
    assert all(report.supported and not report.pending for report in reports)
    return _observed_result(session, home, away, reports, ("1", "8", "9"), eligible=3)


def _observed_result(
    session: PlaySession,
    home: TeamChart,
    away: TeamChart,
    reports: list[PlayReport],
    choices: tuple[str, ...],
    *,
    eligible: int,
) -> tuple[dict[str, Any], tuple[PlayReport, ...]]:
    view = session.view()
    credits = summarize(report.statistics for report in reports)
    assert credits.home == view.statistics.home
    assert credits.away == view.statistics.away
    # Count committed, eligible snaps independently of copied box-score totals.
    assert sum(report.statistics.kind is not StatKind.EXCLUDED for report in reports) == eligible
    assert view.statistics.home.total_plays == eligible
    assert eligible == (
        view.statistics.home.passing_attempts + view.statistics.home.rushing_attempts
    )
    result = {
        "status": "passed",
        "teams": {"home": "A", "away": "B"},
        "configuration": {"advanced_ii": False},
        "engine_log": [_json_value(report) for report in reports],
        "final": {
            "statistics": _json_value(view.statistics),
            "home_score": view.score.home,
            "away_score": view.score.away,
        },
        "coaching_calls": [
            {
                "team_id": "A",
                "choice": choice,
                "role": "offense",
                "observation": {"play_number": report.number - 1, "hurried": False},
            }
            for choice, report in zip(choices, reports, strict=True)
        ],
    }
    result["normalized_primary_results"] = observe_primary_results(
        result, {"A": (home, metadata()), "B": (away, metadata())}
    )
    return result, tuple(reports)


def _foul(team: PenaltyTeam, code: PenaltyCode = PenaltyCode.FIXED) -> NormalizedCell:
    return NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(team, code, 5 if code is PenaltyCode.FIXED else None),
    )


@pytest.mark.parametrize("play", [Play.ONE, Play.NINE], ids=["run", "pass"])
@pytest.mark.parametrize("pre_snap", [True, False], ids=["pre-snap", "offsetting"])
def test_replayed_snap_has_no_terminal_offensive_credit(play: Play, pre_snap: bool) -> None:
    first = _foul(PenaltyTeam.OFFENSE, PenaltyCode.S) if pre_snap else _foul(PenaltyTeam.OFFENSE)
    home = team_chart("A", season=2007, plays={play: first}, defense=0)
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=_foul(PenaltyTeam.DEFENSE))
            if row.play is play and row.roll == 20
            else row
            for row in home.offense
        ),
    )
    away = team_chart("B", season=2007, defense=0)
    session = PlaySession.new(home, away, seed=1)
    choice = str(play.value)
    report = session.snap(
        choice,
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )
    assert not report.pending
    assert report.outcome == ("pre_snap" if pre_snap else "offsetting")
    assert report.statistics.kind is StatKind.EXCLUDED
    result, _ = _observed_result(session, home, away, [report], (choice,), eligible=0)
    assert aggregate_games([result], team_filter="A")["metrics"] == {}


@pytest.mark.parametrize("previous_spot", [True, False], ids=["voided", "retained"])
@pytest.mark.parametrize(
    "play,qt,fumble,kind,gain",
    [
        (Play.ONE, False, False, StatKind.RUSH, 4),
        (Play.NINE, False, False, StatKind.COMPLETE, 7),
        (Play.NINE, True, False, StatKind.SACK, -5),
        (Play.NINE, True, True, StatKind.SACK, -5),
    ],
    ids=["run", "pass", "QT", "QT-F"],
)
def test_penalty_decision_distinguishes_voided_and_retained_play_credit(
    previous_spot: bool, play: Play, qt: bool, fumble: bool, kind: StatKind, gain: int
) -> None:
    terminal = NormalizedCell(
        ResultKind.FUMBLE if fumble else ResultKind.YARDS, provenance(), yards=gain
    )
    home = team_chart(
        "A",
        season=2007,
        plays={play: _foul(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS)},
        defense=0,
    )
    home = replace(
        home,
        offense=tuple(
            replace(
                row,
                cell=NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance())
                if qt
                else terminal,
            )
            if row.play is play and row.roll == 20
            else row
            for row in home.offense
        ),
        supplemental=tuple(
            replace(row, cell=terminal)
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in home.supplemental
        ),
    )
    away = team_chart("B", season=2007, defense=0)
    session = PlaySession.new(home, away, seed=1)
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]
    if qt:
        rolls.append(OffensiveRoll(1, 1, 0))
    if fumble:
        rolls.append(OffensiveRoll(1, 2, 2))
    choice = str(play.value)
    pending = session.snap(choice, "A", dice=ScriptedDice(rolls))
    assert pending.pending and pending.statistics.kind is StatKind.EXCLUDED
    assert session.view().statistics.home.total_plays == 0
    # End-of-gain enforcement is legal for the positive ordinary gains. The
    # negative QT controls retain their result by declining the penalty instead.
    decision = "accept:0:previous" if previous_spot else "decline" if qt else "accept:0:end"
    report = session.decide(decision)
    assert not report.pending
    if decision.startswith("accept:"):
        assert report.outcome == "penalty_accepted"
    assert report.statistics.kind is (StatKind.EXCLUDED if previous_spot else kind)
    result, _ = _observed_result(
        session, home, away, [report], (choice,), eligible=int(not previous_spot)
    )
    metrics = aggregate_games([result], team_filter="A")["metrics"]
    if previous_spot:
        assert metrics == {}
    else:
        assert report.statistics.yards == gain
        assert metrics["fumble"]["numerator"] == int(fumble)
        if kind is StatKind.COMPLETE:
            assert metrics["completion"]["numerator"] == metrics["completion"]["n"] == 1
        else:
            assert "completion" not in metrics
        if kind is StatKind.SACK:
            assert metrics["sack"]["numerator"] == metrics["sack"]["n"] == 1


@pytest.mark.parametrize("retained", [True, False], ids=["retained", "lost"])
@pytest.mark.parametrize(
    "qt,fumble,initial,kind",
    [
        (True, True, -5, StatKind.SACK),
        (True, True, 0, StatKind.RUSH),
        (True, True, 4, StatKind.RUSH),
        (True, False, -5, StatKind.SACK),
        (True, False, 0, StatKind.RUSH),
        (True, False, 4, StatKind.RUSH),
        (False, True, 4, StatKind.COMPLETE),
        (False, False, -4, StatKind.COMPLETE),
    ],
    ids=[
        "qt-F-loss",
        "qt-F-zero",
        "qt-F-gain",
        "qt-loss",
        "qt-zero",
        "qt-gain",
        "pass-F",
        "pass-loss",
    ],
)
def test_qt_fumble_counters_match_real_engine_credit(
    retained: bool, qt: bool, fumble: bool, initial: int, kind: StatKind
) -> None:
    result, reports = _sample(
        qt=qt, fumble=fumble, initial=initial, retained=retained, advance=None
    )
    assert reports[-1].statistics.kind is kind
    assert reports[-1].statistics.yards == initial
    if fumble:
        assert reports[-1].outcome == ("offensive_recovery" if retained else "defensive_recovery")
    _assert_metrics(result, kind=kind, credited=initial, fumble=fumble)


@pytest.mark.parametrize(
    "retained,initial,advance,kind,credited,outcome",
    [
        (True, -5, 8, StatKind.RUSH, 3, "offensive_recovery"),
        (True, -5, 0, StatKind.SACK, -5, "offensive_recovery"),
        (False, -5, 8, StatKind.SACK, -5, "defensive_recovery"),
        (True, 56, None, StatKind.RUSH, 56, "offensive_touchdown"),
        (True, -100, None, StatKind.SACK, -44, "safety"),
    ],
    ids=["own-advance", "own-zero-return", "opponent-return", "touchdown", "safety"],
)
def test_recovery_and_terminal_paths_keep_engine_statistics_authoritative(
    retained: bool,
    initial: int,
    advance: int | None,
    kind: StatKind,
    credited: int,
    outcome: str,
) -> None:
    result, reports = _sample(
        qt=True, fumble=True, initial=initial, retained=retained, advance=advance
    )
    assert reports[-1].outcome == outcome
    assert reports[-1].statistics.kind is kind
    assert reports[-1].statistics.yards == credited
    _assert_metrics(result, kind=kind, credited=credited, fumble=True)


def _assert_metrics(result: dict[str, Any], *, kind: StatKind, credited: int, fumble: bool) -> None:
    metrics = aggregate_games([result], team_filter="A")["metrics"]
    passing = kind is StatKind.COMPLETE
    sacks = kind is StatKind.SACK
    expected = {
        "completion": (1 + passing, 1 + passing),
        "interception": (0, 1 + passing),
        "sack": (int(sacks), 1 + passing + sacks),
        "pure_rush_yards_per_attempt": (
            2 + (credited if kind is StatKind.RUSH else 0),
            1 + (kind is StatKind.RUSH),
        ),
        "ncaa_rush_yards_per_attempt": (2 + (0 if passing else credited), 2 - passing),
        "pass_yards_per_attempt": (7 + (credited if passing else 0), 1 + passing),
        "fumble": (int(fumble), 3),
    }
    for name, (numerator, denominator) in expected.items():
        assert metrics[name]["numerator"] == numerator, name
        assert metrics[name]["n"] == denominator, name
        assert metrics[name]["value"] == pytest.approx(numerator / denominator), name
