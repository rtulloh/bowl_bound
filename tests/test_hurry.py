"""Synthetic no-huddle table and cancelled-defense hazards."""

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import Defense, PenaltyCode, PenaltyTeam, Play, ResultKind
from bowl_bound.penalties import prepare_play
from tests.synthetic_teams import team_chart, yards
from tests.test_penalties import chart, foul


@pytest.mark.parametrize(
    ("team", "code", "roll", "expected"),
    [
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.S,
            OffensiveRoll(1, 0, 0),
            (0, False, False, True, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.S,
            OffensiveRoll(1, 2, 0),
            (5, False, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.S,
            OffensiveRoll(2, 3, 4),
            (5, False, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.S,
            OffensiveRoll(3, 0, 0),
            (10, False, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.S,
            OffensiveRoll(3, 4, 5),
            (15, False, False, False, False),
        ),
        (PenaltyTeam.DEFENSE, PenaltyCode.S, OffensiveRoll(1, 0, 0), (5, False, True, False, True)),
        (PenaltyTeam.DEFENSE, PenaltyCode.S, OffensiveRoll(1, 4, 0), (5, False, True, False, True)),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.S,
            OffensiveRoll(1, 0, 5),
            (5, False, False, False, False),
        ),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.S,
            OffensiveRoll(2, 4, 0),
            (5, False, False, False, False),
        ),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.S,
            OffensiveRoll(2, 0, 5),
            (5, True, False, False, False),
        ),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.S,
            OffensiveRoll(3, 0, 5),
            (5, True, False, False, False),
        ),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.S,
            OffensiveRoll(3, 4, 2),
            (15, True, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.R,
            OffensiveRoll(1, 0, 0),
            (5, False, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.R,
            OffensiveRoll(1, 1, 0),
            (10, False, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.R,
            OffensiveRoll(3, 4, 0),
            (10, False, False, False, False),
        ),
        (
            PenaltyTeam.OFFENSE,
            PenaltyCode.R,
            OffensiveRoll(3, 0, 5),
            (15, False, False, False, False),
        ),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.R,
            OffensiveRoll(1, 1, 0),
            (5, True, False, False, False),
        ),
        (
            PenaltyTeam.DEFENSE,
            PenaltyCode.R,
            OffensiveRoll(2, 0, 0),
            (15, True, False, False, False),
        ),
    ],
)
def test_special_table_boundaries(team, code, roll, expected) -> None:
    from bowl_bound.penalty_yardage import assess_penalty

    p = assess_penalty(foul(team, code, None).penalty, ScriptedDice([roll]), hurried=True)
    assert (p.yards, p.from_end_of_gain, p.pre_snap, p.bad_snap, p.no_elapsed_time) == expected
    assert p.automatic_first_down == (team is PenaltyTeam.DEFENSE and expected[0] == 15)
    assert p.roll == roll


def test_false_start_cancels_defense_stops_rerolls_and_changes_penalized_team() -> None:
    sentinel = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0), sentinel]
    )
    p = prepare_play(
        chart(foul(PenaltyTeam.DEFENSE, PenaltyCode.S, None), yards(8)),
        team_chart("Away", defense=99),
        Play.ONE,
        Defense.A,
        dice,
        hurried=True,
    )
    assert p.pre_snap and p.no_elapsed_time
    assert p.penalties[0].source.team is PenaltyTeam.OFFENSE
    assert p.penalties[0].yards == 5 and dice.offensive() == sentinel
    assert p.resolution.result.defense.kind is ResultKind.NO_CHANGE


def test_bad_snap_becomes_f_minus_two_without_penalty_or_reroll() -> None:
    sentinel = OffensiveRoll(2, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 1, 0), sentinel]
    )
    p = prepare_play(
        chart(foul(PenaltyTeam.OFFENSE, PenaltyCode.S, None), yards(8)),
        team_chart("Away", defense=99),
        Play.ONE,
        Defense.A,
        dice,
        hurried=True,
    )
    assert p.penalties == () and p.resolution.result.kind is ResultKind.FUMBLE
    assert p.resolution.result.yards == -2 and dice.offensive() == sentinel
    assert p.resolution.result.defense.kind is ResultKind.NO_CHANGE


def test_printed_fouls_are_not_converted_by_hurry_up() -> None:
    home = chart(foul(PenaltyTeam.OFFENSE, distance=15), yards(8))
    p = prepare_play(
        home,
        team_chart("Away", defense=0),
        Play.ONE,
        Defense.A,
        ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
        hurried=True,
    )
    assert p.penalties[0].yards == 15 and p.penalties[0].roll is None


@pytest.mark.parametrize(("action", "distance"), [("punt", 13), ("field_goal", 7)])
def test_bad_snap_kick_uses_its_own_location(action: str, distance: int) -> None:
    from bowl_bound.game_state import FieldState, Possession
    from bowl_bound.special_teams import SpecialTeamsPlay
    from tests.test_special_teams import special_chart

    home = special_chart("Home", **{action: foul(PenaltyTeam.OFFENSE, PenaltyCode.S, None)})
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)])
    procedure = SpecialTeamsPlay(
        action,
        FieldState(Possession.HOME, 60, 2, 8),
        home,
        team_chart("Away"),
        dice,
        home_season=2002,
        hurried=True,
    )
    result = procedure.begin()
    assert result.state.yards_to_goal == 60 + distance
    assert result.state.down == 3 and result.points == (0, 0)
    assert [e.section for e in result.trace] == [action, "kick_penalty_yardage", "fumble_recovery"]


def test_def_r_ten_is_explicit_no_foul_and_resolves_next_return_result() -> None:
    from dataclasses import replace

    from bowl_bound.game_state import FieldState, Possession
    from bowl_bound.models import SpecialTeamsColumn
    from bowl_bound.special_teams import SpecialTeamsPlay
    from tests.test_special_teams import special_chart

    home = special_chart("Home", punt=yards(30))
    away = special_chart("Away", punt_return=foul(PenaltyTeam.DEFENSE, PenaltyCode.R, None))
    away = replace(
        away,
        special_teams=tuple(
            replace(r, cell=yards(12))
            if r.column is SpecialTeamsColumn.PUNT_RETURN and r.roll == 20
            else r
            for r in away.special_teams
        ),
    )
    procedure = SpecialTeamsPlay(
        "punt",
        FieldState(Possession.HOME, 60, 2, 8),
        home,
        away,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
        home_season=2002,
        hurried=True,
    )
    procedure.begin()
    result = procedure.decide("kick:return")
    assert result.state.yards_to_goal == 58 and not result.choices
    assert [e.section for e in result.trace] == [
        "punt",
        "punt_return",
        "kick_penalty_yardage",
        "punt_return",
    ]


def test_no_foul_rerolls_still_have_a_finite_chain_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import bowl_bound.penalties as module

    monkeypatch.setattr(module, "MAX_PENALTY_REROLLS", 3)
    home = chart(
        foul(PenaltyTeam.DEFENSE, PenaltyCode.R, None),
        foul(PenaltyTeam.DEFENSE, PenaltyCode.R, None),
    )
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    rolls.extend([OffensiveRoll(1, 0, 0)] * 10)
    with pytest.raises(ValueError, match="penalty reroll limit exceeded"):
        prepare_play(
            home,
            team_chart("Away", defense=0),
            Play.ONE,
            Defense.A,
            ScriptedDice(rolls),
            hurried=True,
        )
