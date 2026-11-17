"""Intentional RED checkpoint for the proposed generalized contract.

These probes exercise the existing numeric/v1 producers, not a missing-module placeholder.
The positive paired-role fixture uses explicit synthetic defensive residuals to
provide INC9/INT1 support; original zero-support requirement bytes remain archived.
This is fixture setup, not a production rate, coefficient or historical target.
Its numeric-only identity remains valid for its narrower scope. After contract
review, the required-subject fixture will target a separately identified opt-in
producer; the explicit legacy negative control remains. No failing test is a
historical-frequency assertion or a universal ban on repeated cells.
"""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Any

import pytest

from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import Defense, Play, ResultKind, SupplementalColumn, TeamChart
from bowl_bound.resolution import ChartResolutionError, resolve_cells
from bowl_bound.team_csv import parse_cell
from tests.chartgen.test_event_risks import primary_counts, terminal_credit_counts
from tests.chartgen.test_generation import events as source_events
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chartgen.generate import DefensiveProfile, generate_team
from tools.chartgen.tactics import TacticalProfile, TacticDelta
from tools.chartgen.typed_event_risks import allocate_typed_column, apply_typed_event_model

WEIGHTS = (12, 11, 9, 3, 1)
MATRIX = Path(__file__).with_name("fixtures") / "generalized_outcome_contract.json"


@lru_cache(maxsize=1)
def legacy_factory() -> TeamChart:
    chart, _, _ = generate_team(
        source_events.__wrapped__(),
        "1",
        "Cedar Valley",
        2007,
        seed=19,
        tactics=TacticalProfile.bowl_bound_yardage_v1(),
        defensive_profile=DefensiveProfile(completion_shift=-0.08, interception_shift=0.03),
    )
    return chart


@pytest.fixture(scope="module")
def required_subject() -> TeamChart:
    """Same frozen positive-support fixture, now through the typed producer."""
    return apply_typed_event_model(legacy_factory())[0]


@pytest.fixture(scope="module")
def ordinary_offense() -> TeamChart:
    chart = team_chart("Fictional ordinary offense", offense=10)
    return replace(
        chart,
        supplemental=tuple(
            replace(row, cell=parse_cell("-6", provenance()))
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in chart.supplemental
        ),
    )


def attainable() -> frozenset[tuple[int, int, int]]:
    """Independent tiny enumeration; zero denotes retained ordinary numeric support."""
    return frozenset(
        tuple(
            sum(w for w, code in zip(WEIGHTS, assignment, strict=True) if code == kind)
            for kind in (1, 2, 3)
        )
        for assignment in product(range(4), repeat=5)
        if 0 in assignment
    )


@pytest.mark.parametrize(
    "formation,play",
    [
        (Defense.D, Play.SIX),
        (Defense.D, Play.SEVEN),
        (Defense.E, Play.EIGHT),
        (Defense.E, Play.NINE),
    ],
)
def test_required_coverage_changes_terminal_completion_component(
    required_subject: TeamChart, ordinary_offense: TeamChart, formation: Defense, play: Play
) -> None:
    standard, _ = terminal_credit_counts(ordinary_offense, required_subject, play, Defense.A)
    covered, _ = terminal_credit_counts(ordinary_offense, required_subject, play, formation)
    assert covered["completion"] < standard["completion"]


@pytest.mark.parametrize("play", [Play.SEVEN, Play.NINE])
def test_required_pressure_changes_actual_negative_qt_sack_credit(
    required_subject: TeamChart, ordinary_offense: TeamChart, play: Play
) -> None:
    standard, _ = terminal_credit_counts(ordinary_offense, required_subject, play, Defense.A)
    blitz, _ = terminal_credit_counts(ordinary_offense, required_subject, play, Defense.F)
    assert blitz["sack"] > standard["sack"]


@pytest.mark.parametrize(
    "formation,play",
    [
        (Defense.D, Play.EIGHT),
        (Defense.D, Play.NINE),
        (Defense.E, Play.SIX),
        (Defense.E, Play.SEVEN),
        (Defense.F, Play.SIX),
        (Defense.F, Play.EIGHT),
    ],
)
def test_required_coverage_and_pressure_have_completion_countercost(
    required_subject: TeamChart, ordinary_offense: TeamChart, formation: Defense, play: Play
) -> None:
    standard, _ = terminal_credit_counts(ordinary_offense, required_subject, play, Defense.A)
    conceded, _ = terminal_credit_counts(ordinary_offense, required_subject, play, formation)
    assert conceded["completion"] > standard["completion"]


def test_blitz_draw_numeric_countercost_is_measured_separately(
    ordinary_offense: TeamChart,
) -> None:
    chart = legacy_factory()
    a, a_yards = terminal_credit_counts(ordinary_offense, chart, Play.FOUR, Defense.A)
    f, f_yards = terminal_credit_counts(ordinary_offense, chart, Play.FOUR, Defense.F)
    assert a == f
    assert f_yards > a_yards


def test_full_numeric_difference_does_not_erase_shared_component(
    ordinary_offense: TeamChart,
) -> None:
    chart = legacy_factory()
    a, ay = terminal_credit_counts(ordinary_offense, chart, Play.SIX, Defense.A)
    d, dy = terminal_credit_counts(ordinary_offense, chart, Play.SIX, Defense.D)
    assert ay != dy  # Existing numeric tradeoff is real.
    assert a["completion"] == d["completion"]  # Broader requirement is still missing.


def sequential_subject(requested: tuple[int, int, int]) -> tuple[TeamChart, dict[str, Any]]:
    effects = []
    for formation in Defense:
        for play in Play:
            sign = (
                1
                if formation is Defense.D and play is Play.SIX
                else (-1 if formation is Defense.A and play is Play.SIX else 0)
            )
            effects.append(
                TacticDelta(
                    formation,
                    play,
                    interception_delta=sign * requested[0] / 36,
                    sack_delta=sign * requested[1] / 36,
                    incomplete_delta=sign * requested[2] / 36,
                )
            )
    chart, _, manifest = generate_team(
        source_events.__wrapped__(),
        "1",
        "Cedar Valley",
        2007,
        seed=19,
        tactics=TacticalProfile(tuple(effects), "synthetic", ()),
    )
    return chart, manifest["defensive_quantization"]["D/6"]


def test_required_joint_error_is_not_sequential_local_error() -> None:
    requested = (1, 2, 3)  # Independent authored synthetic target, not candidate-derived.
    chart, _ = typed_joint_subject(requested)
    kinds = (ResultKind.INTERCEPTION, ResultKind.QUARTERBACK_TRAPPED, ResultKind.INCOMPLETE)
    represented = tuple(
        sum(
            WEIGHTS[row.roll - 1]
            for row in chart.defense
            if row.defense is Defense.D and row.play is Play.SIX and row.cell.kind is kind
        )
        for kind in kinds
    )
    error = sum(abs(a - b) for a, b in zip(represented, requested, strict=True))
    optimum = min(
        sum(abs(a - b) for a, b in zip(point, requested, strict=True)) for point in attainable()
    )
    assert error == optimum


def test_required_joint_infeasibility_is_explicit_not_individual_tables() -> None:
    _, evidence = typed_joint_subject((1, 1, 3))
    assert evidence.get("joint_exact_feasible") is False


def typed_joint_subject(requested: tuple[int, int, int]) -> tuple[TeamChart, dict[str, Any]]:
    """Use the same authored requests through whole-row joint allocation.

    The all-normal numeric baseline admits all five fixed BB physical rows.
    Located INT17 is fictional payload authority only, not a source claim.
    """
    chart = team_chart("Fictional joint row domain", defense=0)
    rows = tuple(row for row in chart.defense if row.defense is Defense.D and row.play is Play.SIX)
    selected, evidence = allocate_typed_column(
        rows,
        dict(
            zip(
                (ResultKind.INTERCEPTION, ResultKind.QUARTERBACK_TRAPPED, ResultKind.INCOMPLETE),
                map(Fraction, requested),
                strict=True,
            )
        ),
        int_locations=((17, 1),),
    )
    changed = {row.roll: row for row in selected}
    return replace(
        chart,
        defense=tuple(
            changed[row.roll] if row.defense is Defense.D and row.play is Play.SIX else row
            for row in chart.defense
        ),
    ), evidence


def test_legacy_sequential_allocation_remains_a_negative_control() -> None:
    chart, _ = sequential_subject((1, 2, 3))
    kinds = (ResultKind.INTERCEPTION, ResultKind.QUARTERBACK_TRAPPED, ResultKind.INCOMPLETE)
    represented = tuple(
        sum(
            WEIGHTS[row.roll - 1]
            for row in chart.defense
            if row.defense is Defense.D and row.play is Play.SIX and row.cell.kind is kind
        )
        for kind in kinds
    )
    assert sum(abs(a - b) for a, b in zip(represented, (1, 2, 3), strict=True)) > 2


def test_individual_attainability_does_not_prove_joint_attainability() -> None:
    individual = {
        sum(w for w, take in zip(WEIGHTS, bits, strict=True) if take)
        for bits in product((False, True), repeat=5)
    }
    assert all(value in individual for value in (1, 1, 3))
    assert (1, 1, 3) not in attainable()
    assert (1, 0, 3) in attainable()
    assert (
        min(
            sum(abs(a - b) for a, b in zip(point, (1, 2, 3), strict=True)) for point in attainable()
        )
        == 2
    )


def test_inc_can_replace_sacks_without_reducing_completions(ordinary_offense: TeamChart) -> None:
    chart = team_chart("Fictional signed countercost", defense=0)
    chart = replace(
        chart,
        defense=tuple(
            replace(
                row, cell=parse_cell("QT" if row.defense is Defense.A else "BLACK", provenance())
            )
            if row.play is Play.SIX and row.roll == 4 and row.defense in {Defense.A, Defense.D}
            else row
            for row in chart.defense
        ),
    )
    a, _ = terminal_credit_counts(ordinary_offense, chart, Play.SIX, Defense.A)
    d, _ = terminal_credit_counts(ordinary_offense, chart, Play.SIX, Defense.D)
    assert d["incomplete"] > a["incomplete"]
    assert d["completion"] == a["completion"]
    assert d["sack"] < a["sack"]


def test_generic_penalty_cell_is_not_an_admitted_ordinary_defense() -> None:
    with pytest.raises(ChartResolutionError, match="Priority Chart coordinate"):
        resolve_cells(parse_cell("10", provenance()), parse_cell("OFF 5", provenance()))


def test_matrix_covers_all_families_and_keeps_source_unknowns() -> None:
    matrix = json.loads(MATRIX.read_text())
    assert {row["kind"] for row in matrix["families"]} == {kind.value for kind in ResultKind}
    assert all(row["source_target"] is None for row in matrix["families"])
    assert not matrix["historical_source_fit_approved"]
    assert not matrix["production_solver_approved"]


def test_declared_context_grid_is_legal_and_contains_no_clamped_duplicates() -> None:
    matrix = json.loads(MATRIX.read_text())
    states = [
        FieldState(Possession(row["side"]), row["yards_to_goal"], row["down"], row["yards_to_go"])
        for row in matrix["legal_states"]
    ]
    assert len(states) == len(set(states)) == 24


@pytest.mark.parametrize(
    "formation,play,sign",
    [
        (Defense.D, Play.SIX, 1),
        (Defense.D, Play.SEVEN, 1),
        (Defense.D, Play.EIGHT, -1),
        (Defense.D, Play.NINE, -1),
        (Defense.E, Play.SIX, -1),
        (Defense.E, Play.SEVEN, -1),
        (Defense.E, Play.EIGHT, 1),
        (Defense.E, Play.NINE, 1),
    ],
)
def test_required_eligible_int_coverage_component_and_concession(
    required_subject, ordinary_offense, formation, play, sign
):
    a = primary_counts(ordinary_offense, required_subject, play, Defense.A)
    selected = primary_counts(ordinary_offense, required_subject, play, formation)
    assert (selected[ResultKind.INTERCEPTION.value] - a[ResultKind.INTERCEPTION.value]) * sign > 0


def test_role_fixture_has_positive_component_support_not_a_manufactured_floor():
    chart = legacy_factory()
    a = tuple(row for row in chart.defense if row.defense is Defense.A and row.play is Play.SIX)
    assert sum(WEIGHTS[row.roll - 1] for row in a if row.cell.kind is ResultKind.INCOMPLETE) == 9
    assert sum(WEIGHTS[row.roll - 1] for row in a if row.cell.kind is ResultKind.INTERCEPTION) == 1


@pytest.mark.parametrize("qt_yards", [-6, 0, 6])
def test_pressure_entry_is_sack_only_when_actual_qt_resolves_negative(qt_yards, required_subject):
    offense = team_chart("Fictional conditional QT credit", offense=10)
    offense = replace(
        offense,
        supplemental=tuple(
            replace(row, cell=parse_cell(str(qt_yards), provenance()))
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in offense.supplemental
        ),
    )
    a, _ = terminal_credit_counts(offense, required_subject, Play.SEVEN, Defense.A)
    f, _ = terminal_credit_counts(offense, required_subject, Play.SEVEN, Defense.F)
    if qt_yards < 0:
        assert f["sack"] > a["sack"]
    else:
        assert f["sack"] == a["sack"] == 0
        assert f["rush"] > a["rush"]
