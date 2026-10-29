"""Full-feature variable yardage uses independent observed face rolls."""

from itertools import product

import pytest

from bowl_bound.dice import (
    BLACK_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.models import Defense, NormalizedCell, Play, Priority, ResultKind, VariableReference
from bowl_bound.resolution import resolve_play
from bowl_bound.session import PlaySession
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


@pytest.mark.parametrize("reference", list(VariableReference))
def test_variable_distance_uses_all_216_physical_face_combinations(
    reference: VariableReference,
) -> None:
    from bowl_bound.variable_yardage import roll_variable

    count = (
        3 if reference is VariableReference.T3 else 2 if reference is VariableReference.T2 else 1
    )
    for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        roll = OffensiveRoll(*faces)
        script = ScriptedDice([roll] * count)
        expected = (
            sum(faces)
            if reference is VariableReference.DS
            else 40 - (10 * faces[0] + faces[1] + faces[2])
            if reference is VariableReference.X
            else (10 * faces[0] + faces[1] + faces[2]) * count
        )
        distance, rolls = roll_variable(reference, -2, script)
        assert distance == -2 * expected
        assert rolls == (roll,) * count


def variable(
    reference: VariableReference, multiplier: int = 1, priority: Priority = Priority.NORMAL
) -> NormalizedCell:
    return NormalizedCell(
        ResultKind("variable_" + reference.value.lower()),
        provenance(),
        variable=reference,
        variable_multiplier=multiplier,
        priority=priority,
    )


def test_scrimmage_variable_offense_and_defense_roll_separately_and_commit() -> None:
    home = team_chart("Home", plays={Play.ONE: variable(VariableReference.DS)})
    away = team_chart("Away")
    from dataclasses import replace

    away = replace(
        away,
        defense=tuple(replace(row, cell=variable(VariableReference.X, -1)) for row in away.defense),
    )
    script = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(3, 2, 5),
            OffensiveRoll(3, 4, 5),
        ]
    )
    game = PlaySession.new(home, away, seed=1)
    report = game.snap("1", "A", dice=script)
    assert report.supported and not report.pending and report.yards == 9
    assert report.state_after.yards_to_goal == 56
    assert [e.section for e in report.trace] == [
        "offense",
        "defense",
        "variable:offense",
        "variable:defense",
    ]
    assert report.statistics.yards == 9


def test_overridden_variable_offense_does_not_consume_unused_dice() -> None:
    from dataclasses import replace

    home = team_chart("Home", plays={Play.ONE: variable(VariableReference.T3)})
    away = team_chart("Away")
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=replace(yards(4), priority=Priority.BRACKETED))
            for row in away.defense
        ),
    )
    result = resolve_play(
        home, away, Play.ONE, Defense.A, ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    )
    assert result.result.yards == 4
    assert len(result.trace) == 2


def test_variable_defensive_location_controls_fumble_priority() -> None:
    from dataclasses import replace

    home = team_chart(
        "Home", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3)}
    )
    away = team_chart("Away")
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=variable(VariableReference.X, -1, Priority.PARENTHESIZED))
            for row in away.defense
        ),
    )
    game = PlaySession.new(home, away, seed=1)
    report = game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(3, 2, 5),
                OffensiveRoll(1, 0, 0),
            ]
        ),
    )
    assert report.yards == -3
    assert report.state_after.yards_to_goal == 68
    assert [e.section for e in report.trace] == [
        "offense",
        "defense",
        "variable:defense",
        "fumble_recovery",
    ]


def test_fumble_against_defensive_td_uses_one_yard_into_defenders_end_zone() -> None:
    from dataclasses import replace

    home = team_chart(
        "Home", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3)}
    )
    away = team_chart("Away")
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=NormalizedCell(ResultKind.TOUCHDOWN, provenance()))
            for row in away.defense
        ),
    )
    game = PlaySession.new(home, away, seed=1)
    report = game.snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)]),
    )
    assert report.outcome == "offensive_touchdown" and game.view().score.home == 6
    assert report.yards == 66


@pytest.mark.parametrize("kind", [ResultKind.INTERCEPTION, ResultKind.FUMBLE])
@pytest.mark.parametrize("priority", [Priority.PARENTHESIZED, Priority.BRACKETED])
def test_turnover_minimum_compares_independent_variable_distances(
    kind: ResultKind, priority: Priority
) -> None:
    from dataclasses import replace

    home = team_chart(
        "Home",
        plays={
            Play.ONE: NormalizedCell(
                kind, provenance(), variable=VariableReference.DS, variable_multiplier=1
            )
        },
    )
    away = team_chart("Away")
    defensive = variable(VariableReference.X, -1, priority)
    away = replace(away, defense=tuple(replace(r, cell=defensive) for r in away.defense))
    result = resolve_play(
        home,
        away,
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 2, 3),
                OffensiveRoll(3, 2, 5),
            ]
        ),
    )
    assert result.result.kind is kind and result.result.yards == -3
    assert result.result.operation.value == (
        "INT_MIN" if kind is ResultKind.INTERCEPTION else "F_MIN"
    )
    assert [e.section for e in result.trace] == [
        "offense",
        "defense",
        "variable:offense",
        "variable:defense",
    ]
    assert result.result.offense.variable is VariableReference.DS
    assert result.result.defense == defensive


def test_defensive_fumble_location_does_not_roll_unused_offensive_location() -> None:
    from dataclasses import replace

    home = team_chart(
        "Home",
        plays={
            Play.ONE: NormalizedCell(
                ResultKind.FUMBLE,
                provenance(),
                variable=VariableReference.T3,
                variable_multiplier=1,
            )
        },
    )
    away = team_chart("Away")
    away = replace(
        away,
        defense=tuple(
            replace(r, cell=variable(VariableReference.T2, 1, Priority.PARENTHESIZED))
            for r in away.defense
        ),
    )
    result = resolve_play(
        home,
        away,
        Play.ONE,
        Defense.A,
        ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 2, 3),
                OffensiveRoll(2, 1, 0),
            ]
        ),
    )
    assert result.result.yards == 36 and result.result.operation.value == "F_DEF"
    assert [e.section for e in result.trace] == [
        "offense",
        "defense",
        "variable:defense",
        "variable:defense",
    ]
