"""Transferred priority hypotheses use Bowl Bound's selected semantic result."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind, SupplementalColumn
from bowl_bound.resolution import Operation, resolve_cells
from bowl_bound.session import PlaySession
from bowl_bound.statistics import StatKind, summarize
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


def fact(kind: ResultKind, gain: int | None = None) -> NormalizedCell:
    return NormalizedCell(kind, provenance(), yards=gain)


@pytest.mark.parametrize("offense_fumbles", [False, True])
def test_normal_fumble_interception_conflict_uses_bb_priority(offense_fumbles: bool) -> None:
    fumble, interception = fact(ResultKind.FUMBLE, 2), fact(ResultKind.INTERCEPTION, 5)
    offense, defense = (fumble, interception) if offense_fumbles else (interception, fumble)
    selected = resolve_cells(offense, defense)
    assert selected.operation is (Operation.DEFENSE if offense_fumbles else Operation.OFFENSE)
    assert selected.kind is ResultKind.INTERCEPTION
    home = team_chart("Synthetic Home", plays={Play.NINE: offense})
    away = team_chart("Synthetic Away")
    away = replace(away, defense=tuple(replace(r, cell=defense) for r in away.defense))
    game = PlaySession.new(home, away, seed=1)
    report = game.snap("9", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))
    assert report.outcome == "interception_pending"
    assert game.view().statistics.home.total_plays == 0
    report = game.decide("interception:decline")
    assert report.statistics.kind is StatKind.INCOMPLETE
    assert game.view().statistics.home.interceptions == 0
    assert game.view().statistics.home.passing_attempts == 1
    assert game.view().statistics == summarize(r.statistics for r in game.view().log)


@pytest.mark.parametrize("branch,gain", [("option", 2), ("qt", -2), ("qt", 2)])
@pytest.mark.parametrize("retained", [False, True])
def test_discarded_raw_int_cannot_override_selected_fumble(
    branch: str, gain: int, retained: bool
) -> None:
    initial = (
        fact(ResultKind.SPRINT_OUT_PASS) if branch == "option" else fact(ResultKind.INTERCEPTION, 9)
    )
    defensive = (
        fact(ResultKind.INTERCEPTION, 9) if branch == "option" else fact(ResultKind.QUARTERBACK_RUN)
    )
    called = Play.FIVE if branch == "option" else Play.NINE
    home = team_chart(
        "Synthetic Home", plays={called: initial, Play.SEVEN: fact(ResultKind.FUMBLE, gain)}
    )
    home = replace(
        home,
        recovery_range=range(10, 11),
        supplemental=tuple(
            replace(r, cell=fact(ResultKind.FUMBLE, gain))
            if r.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else r
            for r in home.supplemental
        ),
    )
    away = team_chart("Synthetic Away")
    away = replace(
        away,
        defense=tuple(replace(r, cell=defensive) for r in away.defense),
        special_teams=tuple(replace(r, cell=yards(0)) for r in away.special_teams),
    )
    rolls = [
        OffensiveRoll(1, 0, 0),
        DefensiveRoll(1, 0),
        OffensiveRoll(2, 0, 0),
        OffensiveRoll(1, 0, 0) if retained else OffensiveRoll(1, 2, 2),
    ]
    if not retained:
        rolls.append(OffensiveRoll(1, 0, 0))
    game = PlaySession.new(home, away, seed=1)
    report = game.snap(str(called.value), "A", dice=ScriptedDice(rolls))
    assert any(entry.cell == "INT 9" for entry in report.trace)
    assert report.outcome == ("offensive_recovery" if retained else "defensive_recovery")
    assert any(entry.section == "fumble_recovery" for entry in report.trace)
    assert game.view().pending is None
    stat = game.view().statistics.home
    assert stat.total_plays == 1 and stat.interceptions == 0
    assert stat.passing_attempts == stat.completions == (branch == "option")
    assert stat.rushing_attempts == (branch == "qt")
    assert stat.sacks_taken == (branch == "qt" and gain < 0)
    assert stat.total_yards == gain
    assert game.view().statistics == summarize(r.statistics for r in game.view().log)
