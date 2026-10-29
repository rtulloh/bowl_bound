"""Exact probability analysis uses synthetic charts and the authoritative resolver."""

from collections import Counter
from dataclasses import replace
from fractions import Fraction
from itertools import product
from random import getstate

import pytest

from bowl_bound.coaching_probabilities import ChartDistribution, analyze_play
from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.models import Defense, NormalizedCell, Play, Priority, ResultKind, VariableReference
from bowl_bound.resolution import resolve_play
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


def masses(
    distribution: ChartDistribution,
) -> dict[tuple[Play, ResultKind | None, int | None, bool], Fraction]:
    result = Counter()
    for entry in distribution.outcomes:
        result[
            (
                entry.outcome.resolved_play,
                entry.outcome.kind,
                entry.outcome.yards,
                entry.outcome.pending,
            )
        ] += entry.probability
    return dict(result)


def test_exact_joint_distribution_matches_all_216_by_36_physical_combinations() -> None:
    offense = team_chart("Synthetic Offense")
    defense = team_chart("Synthetic Defense")
    offense = replace(
        offense, offense=tuple(replace(r, cell=yards(r.roll)) for r in offense.offense)
    )
    defense = replace(
        defense, defense=tuple(replace(r, cell=yards(-r.roll)) for r in defense.defense)
    )
    expected = Counter()
    offensive = [
        OffensiveRoll(*faces) for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    ]
    defensive = [DefensiveRoll(*faces) for faces in product(RED_FACES, GREEN_FACES)]
    assert len(offensive) == 216 and len(defensive) == 36
    for off, deff in product(offensive, defensive):
        resolution = resolve_play(offense, defense, Play.ONE, Defense.A, ScriptedDice([off, deff]))
        expected[(Play.ONE, resolution.result.kind, resolution.result.yards, False)] += 1
    before = getstate()
    distribution = analyze_play(offense, defense, Play.ONE, Defense.A)
    assert getstate() == before
    assert distribution.complete
    assert distribution.pending_probability == 0
    assert masses(distribution) == {
        key: Fraction(count, 216 * 36) for key, count in expected.items()
    }
    assert sum(entry.probability for entry in distribution.outcomes) == 1
    assert distribution == analyze_play(offense, defense, Play.ONE, Defense.A)


def test_priority_is_delegated_not_flattened_to_addition() -> None:
    offense, defense = team_chart("Offense", offense=20), team_chart("Defense", defense=-4)
    defense = replace(
        defense,
        defense=tuple(
            replace(r, cell=replace(r.cell, priority=Priority.BRACKETED)) for r in defense.defense
        ),
    )
    distribution = analyze_play(offense, defense, Play.ONE, Defense.F)
    assert distribution.complete
    assert masses(distribution) == {(Play.ONE, ResultKind.YARDS, -4, False): Fraction(1)}


@pytest.mark.parametrize(
    "kind,resolved",
    [(ResultKind.SPRINT_OUT_PASS, Play.SEVEN), (ResultKind.BOOTLEG_PASS, Play.EIGHT)],
)
def test_option_restarts_under_resolved_play_and_cancels_original_defense(
    kind: ResultKind,
    resolved: Play,
) -> None:
    offense = team_chart(
        "Offense", offense=8, plays={Play.FIVE: NormalizedCell(kind, provenance())}
    )
    defense = team_chart("Defense", defense=-30)
    distribution = analyze_play(offense, defense, Play.FIVE, Defense.C)
    assert distribution.complete
    assert all(entry.outcome.called_play is Play.FIVE for entry in distribution.outcomes)
    assert masses(distribution) == {(resolved, ResultKind.YARDS, 8, False): Fraction(1)}


@pytest.mark.parametrize(
    "kind", [ResultKind.BREAKAWAY, ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED]
)
def test_supplemental_rolls_are_independent_and_keep_engine_priority(kind: ResultKind) -> None:
    offense = team_chart("Offense", offense=9, plays={Play.ONE: NormalizedCell(kind, provenance())})
    defense = team_chart("Defense", defense=-2)
    distribution = analyze_play(offense, defense, Play.ONE, Defense.B)
    assert distribution.complete
    gain = 9 if kind is ResultKind.QUARTERBACK_TRAPPED else 7
    assert masses(distribution) == {(Play.ONE, ResultKind.YARDS, gain, False): Fraction(1)}


def test_variable_ds_uses_physical_direct_sum_not_uniform_totals() -> None:
    variable = NormalizedCell(
        ResultKind.VARIABLE_DS, provenance(), variable=VariableReference.DS, variable_multiplier=-2
    )
    offense = team_chart("Offense", plays={Play.ONE: variable})
    defense = team_chart("Defense", defense=0)
    distribution = analyze_play(offense, defense, Play.ONE, Defense.A)
    expected = Counter(
        -2 * sum(faces) for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    assert distribution.complete
    assert masses(distribution) == {
        (Play.ONE, ResultKind.YARDS, gain, False): Fraction(count, 216)
        for gain, count in expected.items()
    }


@pytest.mark.parametrize("kind", [ResultKind.FUMBLE, ResultKind.INTERCEPTION])
def test_pending_turnovers_are_not_reported_as_committed_possession_changes(
    kind: ResultKind,
) -> None:
    offense = team_chart("Offense", plays={Play.ONE: NormalizedCell(kind, provenance(), yards=12)})
    distribution = analyze_play(offense, team_chart("Defense"), Play.ONE, Defense.A)
    assert distribution.complete
    assert distribution.pending_probability == 1
    assert masses(distribution) == {(Play.ONE, kind, 12, True): Fraction(1)}


def test_penalty_facts_and_bounds_are_retained() -> None:
    from tests.synthetic_teams import default_teams

    offense, defense = default_teams()
    distribution = analyze_play(offense, defense, Play.EIGHT, Defense.A)
    assert distribution.complete and distribution.pending_probability == 1
    assert all(e.outcome.penalty is not None for e in distribution.outcomes)
    offense = team_chart("Offense", plays={Play.ONE: replace(yards(2), out_of_bounds=True)})
    distribution = analyze_play(offense, defense, Play.ONE, Defense.A)
    assert all(e.outcome.out_of_bounds for e in distribution.outcomes)


def test_work_limit_preserves_unexplored_probability_instead_of_inventing_outcomes() -> None:
    offense, defense = team_chart("Offense"), team_chart("Defense")
    distribution = analyze_play(offense, defense, Play.ONE, Defense.A, max_evaluations=10)
    assert not distribution.complete
    assert 0 < distribution.unexplored_probability <= 1
    assert distribution.evaluations == 10
    assert (
        sum(e.probability for e in distribution.outcomes)
        + distribution.unexplored_probability
        + distribution.failed_probability
        == 1
    )
    assert all(e.outcome.yards == 7 for e in distribution.outcomes)


def test_invalid_resolution_preserves_failed_mass_and_does_not_echo_chart_values() -> None:
    cell = replace(yards(4), priority=Priority.BRACKETED)
    offense = team_chart("Private-looking Name", plays={Play.ONE: cell})
    distribution = analyze_play(offense, team_chart("Defense"), Play.ONE, Defense.A)
    assert not distribution.complete
    assert distribution.failed_probability == 1
    assert not distribution.outcomes
    assert distribution.unexplored_probability == 0


@pytest.mark.parametrize("budget", [0, -1, True, 1.5])
def test_invalid_budget_is_rejected(budget: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        analyze_play(
            team_chart("Offense"),
            team_chart("Defense"),
            Play.ONE,
            Defense.A,
            max_evaluations=budget,
        )


def test_invalid_calls_are_not_swallowed_as_analysis_failures() -> None:
    with pytest.raises(TypeError):
        analyze_play(team_chart("Offense"), team_chart("Defense"), "1", Defense.A)


def test_option_reroll_is_independent_of_initial_option_trigger() -> None:
    offense = team_chart("Offense", offense=0)
    option = NormalizedCell(ResultKind.SPRINT_OUT_PASS, provenance())
    offense = replace(
        offense,
        offense=tuple(
            replace(record, cell=option if record.roll == 10 else yards(0))
            if record.play is Play.FIVE
            else replace(record, cell=yards(12 if record.roll == 10 else 0))
            if record.play is Play.SEVEN
            else record
            for record in offense.offense
        ),
    )
    distribution = analyze_play(offense, team_chart("Defense", defense=0), Play.FIVE, Defense.A)
    trigger = Fraction(2, 216)
    assert distribution.complete
    assert masses(distribution) == {
        (Play.FIVE, ResultKind.YARDS, 0, False): 1 - trigger,
        (Play.SEVEN, ResultKind.YARDS, 12, False): trigger * trigger,
        (Play.SEVEN, ResultKind.YARDS, 0, False): trigger * (1 - trigger),
    }


def test_branching_supplemental_chart_preserves_exact_unexplored_mass() -> None:
    base = team_chart(
        "Offense", plays={Play.ONE: NormalizedCell(ResultKind.BREAKAWAY, provenance())}
    )
    offense = replace(
        base,
        supplemental=tuple(
            replace(r, cell=NormalizedCell(ResultKind.BREAKAWAY, provenance()))
            for r in base.supplemental
        ),
    )
    distribution = analyze_play(
        offense, team_chart("Defense"), Play.ONE, Defense.A, max_evaluations=25
    )
    assert not distribution.complete
    assert distribution.evaluations == 25
    assert distribution.unexplored_probability + distribution.failed_probability == 1
    assert not distribution.outcomes


def test_invalid_charts_and_formation_are_rejected_before_enumeration() -> None:
    with pytest.raises(TypeError, match="TeamChart"):
        analyze_play(None, team_chart("Defense"), Play.ONE, Defense.A)
    with pytest.raises(TypeError, match="Defense"):
        analyze_play(team_chart("Offense"), team_chart("Defense"), Play.ONE, "A")
