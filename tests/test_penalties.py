"""Synthetic penalty procedure chains; no state is applied before an explicit decision."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    Defense,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.penalties import prepare_play
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


def foul(
    team: PenaltyTeam, code: PenaltyCode = PenaltyCode.FIXED, distance: int | None = 5
) -> NormalizedCell:
    return NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(team, code, distance)
    )


def chart(first: NormalizedCell, second: NormalizedCell) -> object:
    base = team_chart("Synthetic U", plays={Play.ONE: first})
    return replace(
        base,
        offense=tuple(
            replace(r, cell=second) if r.play is Play.ONE and r.roll == 20 else r
            for r in base.offense
        ),
    )


def test_no_penalty_adds_no_extra_rolls() -> None:
    home = team_chart("Synthetic Home")
    away = team_chart("Synthetic Away", defense=2)
    sentinel = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), sentinel])
    prepared = prepare_play(home, away, Play.ONE, Defense.A, dice)
    assert prepared.penalties == () and prepared.resolution.result.yards == 6
    assert len(prepared.resolution.trace) == 2 and dice.offensive() == sentinel


def test_fixed_penalty_rerolls_only_offense_and_retains_the_original_defense() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE), yards(7))
    away = team_chart("Synthetic Away", defense=-2)
    prepared = prepare_play(
        home,
        away,
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    assert len(prepared.penalties) == 1 and prepared.penalties[0].yards == 5
    assert prepared.resolution.result.yards == 5
    assert [t.section for t in prepared.resolution.trace] == [
        "offense",
        "defense",
        "penalty_reroll",
    ]
    assert not prepared.offsetting and not prepared.pre_snap


def test_multiple_same_team_penalties_are_alternatives_not_added() -> None:
    first = foul(PenaltyTeam.DEFENSE, distance=5)
    second = foul(PenaltyTeam.DEFENSE, distance=15)
    home = chart(first, second)
    home = replace(
        home,
        offense=tuple(
            replace(r, cell=yards(3)) if r.play is Play.ONE and r.roll == 30 else r
            for r in home.offense
        ),
    )
    prepared = prepare_play(
        home,
        team_chart("Away", defense=0),
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
            ]
        ),
    )
    assert [p.yards for p in prepared.penalties] == [5, 15]
    assert prepared.resolution.result.yards == 3 and not prepared.offsetting


def test_opposite_team_penalties_offset_without_a_third_roll() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE), foul(PenaltyTeam.DEFENSE))
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0), sentinel]
    )
    prepared = prepare_play(home, team_chart("Away"), Play.ONE, Defense.A, dice)
    assert prepared.offsetting and len(prepared.penalties) == 2
    assert dice.offensive() == sentinel


def test_pi_stops_rerolls_and_cancels_defensive_qt() -> None:
    home = team_chart("Home", plays={Play.ONE: foul(PenaltyTeam.DEFENSE, PenaltyCode.PI, 12)})
    away = team_chart("Away")
    away = replace(
        away,
        defense=tuple(
            replace(r, cell=NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
            for r in away.defense
        ),
    )
    sentinel = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), sentinel])
    prepared = prepare_play(home, away, Play.ONE, Defense.A, dice)
    assert prepared.resolution.result.kind is ResultKind.INCOMPLETE
    assert prepared.penalties[0].source.code is PenaltyCode.PI
    assert len(prepared.resolution.trace) == 2 and dice.offensive() == sentinel


def test_s_assessment_roll_precedes_the_offensive_reroll_and_is_traced() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE, PenaltyCode.S, None), yards(7))
    prepared = prepare_play(
        home,
        team_chart("Away", defense=0),
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(3, 3, 2),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    assert prepared.penalties[0].yards == 10
    assert [t.section for t in prepared.resolution.trace] == [
        "offense",
        "defense",
        "penalty_yardage",
        "penalty_reroll",
    ]
    assert prepared.resolution.result.yards == 7


def test_pre_snap_foul_has_no_decline_or_result_reroll() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE, PenaltyCode.S, None), foul(PenaltyTeam.DEFENSE))
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0), sentinel]
    )
    prepared = prepare_play(home, team_chart("Away"), Play.ONE, Defense.A, dice)
    assert prepared.pre_snap and not prepared.offsetting
    assert len(prepared.penalties) == 1 and dice.offensive() == sentinel


def test_unresolved_turnover_after_penalty_remains_pending_not_zero() -> None:
    interception = NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)
    home = chart(foul(PenaltyTeam.OFFENSE), interception)
    prepared = prepare_play(
        home,
        team_chart("Away", defense=0),
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    assert prepared.resolution.result.pending
    assert prepared.resolution.result.kind is ResultKind.INTERCEPTION


def test_reroll_limit_fails_without_consuming_an_unbounded_stream() -> None:
    from bowl_bound.penalties import MAX_PENALTY_REROLLS

    home = team_chart("Home", plays={Play.ONE: foul(PenaltyTeam.OFFENSE)})
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
        + [OffensiveRoll(1, 0, 0)] * (MAX_PENALTY_REROLLS + 2)
    )
    with pytest.raises(ValueError, match="penalty reroll"):
        prepare_play(home, team_chart("Away"), Play.ONE, Defense.A, dice)


def test_offense_then_pi_offsets_and_stops_without_a_final_reroll() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE), foul(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8))
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            sentinel,
        ]
    )
    prepared = prepare_play(home, team_chart("Away"), Play.ONE, Defense.A, dice)
    assert prepared.offsetting and len(prepared.penalties) == 2
    assert dice.offensive() == sentinel


def test_option_pass_penalty_rerolls_the_resolved_column_without_restoring_defense() -> None:
    sop = NormalizedCell(ResultKind.SPRINT_OUT_PASS, provenance())
    home = team_chart("Home", plays={Play.FIVE: sop, Play.SEVEN: foul(PenaltyTeam.OFFENSE)})
    home = replace(
        home,
        offense=tuple(
            replace(r, cell=yards(8)) if r.play is Play.SEVEN and r.roll == 30 else r
            for r in home.offense
        ),
    )
    prepared = prepare_play(
        home,
        team_chart("Away", defense=-4),
        Play.FIVE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
            ]
        ),
    )
    assert prepared.resolution.called_play is Play.FIVE
    assert prepared.resolution.resolved_play is Play.SEVEN
    assert prepared.resolution.result.yards == 8
    assert [t.section for t in prepared.resolution.trace] == [
        "offense",
        "defense",
        "option",
        "penalty_reroll",
    ]


def test_penalty_reroll_to_option_nullifies_original_defense() -> None:
    sop = NormalizedCell(ResultKind.SPRINT_OUT_PASS, provenance())
    home = team_chart("Home", plays={Play.FIVE: foul(PenaltyTeam.OFFENSE), Play.SEVEN: yards(8)})
    home = replace(
        home,
        offense=tuple(
            replace(r, cell=sop) if r.play is Play.FIVE and r.roll == 20 else r
            for r in home.offense
        ),
    )
    prepared = prepare_play(
        home,
        team_chart("Away", defense=-4),
        Play.FIVE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
            ]
        ),
    )
    assert prepared.resolution.resolved_play is Play.SEVEN
    assert prepared.resolution.result.yards == 8


def test_penalty_from_a_supplemental_column_rerolls_the_offensive_play() -> None:
    from bowl_bound.models import SupplementalColumn

    home = team_chart("Home", plays={Play.ONE: NormalizedCell(ResultKind.BREAKAWAY, provenance())})
    home = replace(
        home,
        offense=tuple(
            replace(r, cell=yards(8)) if r.play is Play.ONE and r.roll == 30 else r
            for r in home.offense
        ),
        supplemental=tuple(
            replace(r, cell=foul(PenaltyTeam.OFFENSE))
            if r.column is SupplementalColumn.BREAKAWAY
            else r
            for r in home.supplemental
        ),
    )
    prepared = prepare_play(
        home,
        team_chart("Away", defense=2),
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
            ]
        ),
    )
    assert prepared.resolution.result.yards == 10
    assert [t.section for t in prepared.resolution.trace] == [
        "offense",
        "defense",
        "supplemental:B",
        "penalty_reroll",
    ]


def test_pi_after_an_already_rolled_qt_becomes_def10_without_automatic_first_down() -> None:
    from bowl_bound.models import SupplementalColumn

    home = team_chart(
        "Home", plays={Play.ONE: NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance())}
    )
    home = replace(
        home,
        supplemental=tuple(
            replace(r, cell=foul(PenaltyTeam.DEFENSE, PenaltyCode.PI, 12))
            if r.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else r
            for r in home.supplemental
        ),
    )
    prepared = prepare_play(
        home,
        team_chart("Away", defense=0),
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    assert prepared.penalties[0].yards == 10
    assert not prepared.penalties[0].automatic_first_down
    assert prepared.penalties[0].pi_as_def10
    assert prepared.penalties[0].source.code is PenaltyCode.PI
    assert prepared.resolution.result.kind is ResultKind.INCOMPLETE
