"""Whole-row coupled roles, using fictional positive/zero residual support."""

from dataclasses import replace
from fractions import Fraction

import pytest

from bowl_bound.models import (
    Defense,
    NormalizedCell,
    Play,
    Priority,
    ResultKind,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.team_csv import parse_cell
from tests.chartgen.test_event_risks import primary_counts, terminal_credit_counts
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chartgen.coupled_event_risks import apply_coupled_model, enumerate_column

WEIGHTS = (12, 11, 9, 3, 1)


def fictional(*, interceptions: bool) -> TeamChart:
    chart = team_chart("Fictional positive" if interceptions else "Fictional zero")
    return replace(
        chart,
        defense=tuple(
            replace(
                row,
                cell=parse_cell(
                    ("BLACK" if row.roll == 3 else "INT 11" if row.roll == 5 else "2")
                    if interceptions
                    else ("BLACK" if row.roll == 4 else "QT" if row.roll == 5 else "2"),
                    provenance(),
                ),
            )
            if row.play.value >= 6
            else row
            for row in chart.defense
        ),
    )


def mass(chart: TeamChart, formation: Defense, play: Play, kind: ResultKind) -> int:
    return sum(
        WEIGHTS[r.roll - 1]
        for r in chart.defense
        if r.defense is formation
        and r.play is play
        and r.cell.kind is kind
        and r.cell.priority is Priority.NORMAL
        and not r.cell.out_of_bounds
    )


@pytest.fixture(scope="module", params=[False, True])
def pair(request: pytest.FixtureRequest) -> tuple[TeamChart, TeamChart, dict]:
    old = fictional(interceptions=request.param)
    new, report = apply_coupled_model(
        old,
        known_depths=((-3, 1), (5, 1), (19, 1), (35, 1)),
        unknown_locations=2,
        source_identity="a" * 64,
    )
    assert report["status"] == "represented"
    return old, new, report


def test_full_joint_budgets_and_exact_pressure(pair: tuple) -> None:
    old, new, report = pair
    for play in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
        for kind in (ResultKind.INCOMPLETE, ResultKind.INTERCEPTION):
            assert sum(mass(new, d, play, kind) for d in Defense) == sum(
                mass(old, d, play, kind) for d in Defense
            )
        if play in (Play.SEVEN, Play.NINE):
            assert (
                mass(new, Defense.F, play, ResultKind.QUARTERBACK_TRAPPED)
                == mass(new, Defense.A, play, ResultKind.QUARTERBACK_TRAPPED) + 3
            )
            assert (
                mass(new, Defense.F, play, ResultKind.QUARTERBACK_TRAPPED)
                == mass(old, Defense.A, play, ResultKind.QUARTERBACK_TRAPPED) + 3
            )
    for d in Defense:
        assert sum(mass(new, d, p, ResultKind.INTERCEPTION) for p in Play if p.value >= 6) == sum(
            mass(old, d, p, ResultKind.INTERCEPTION) for p in Play if p.value >= 6
        )
    assert report["source_unknown_locations"] == 2


def test_actual_revised_a_coverage_benefits_and_concessions(pair: tuple) -> None:
    _, chart, _ = pair
    for p in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
        a = mass(chart, Defense.A, p, ResultKind.INCOMPLETE)
        protect, concede = (Defense.D, Defense.E) if p.value <= 7 else (Defense.E, Defense.D)
        assert mass(chart, protect, p, ResultKind.INCOMPLETE) > a
        assert mass(chart, concede, p, ResultKind.INCOMPLETE) < a
        if p in (Play.SIX, Play.EIGHT):
            assert mass(chart, Defense.F, p, ResultKind.INCOMPLETE) < a


def test_counterplay_is_not_erased_by_joint_int_or_pressure(pair: tuple) -> None:
    _, chart, _ = pair
    families = (ResultKind.INCOMPLETE, ResultKind.INTERCEPTION, ResultKind.QUARTERBACK_TRAPPED)
    for p in (Play.SIX, Play.EIGHT):
        assert sum(mass(chart, Defense.F, p, k) for k in families) < sum(
            mass(chart, Defense.A, p, k) for k in families
        )


def test_all_formations_depths_coupled_without_floor(pair: tuple) -> None:
    old, new, report = pair
    if any(r.cell.kind is ResultKind.INTERCEPTION for r in old.defense):
        for d in Defense:
            assert any(
                r.cell.yards != 11
                for r in new.defense
                if r.defense is d and r.cell.kind is ResultKind.INTERCEPTION
            )
        short = {
            r.cell.yards
            for r in new.defense
            if r.play.value in (6, 7) and r.cell.kind is ResultKind.INTERCEPTION
        }
        long = {
            r.cell.yards
            for r in new.defense
            if r.play.value in (8, 9) and r.cell.kind is ResultKind.INTERCEPTION
        }
        assert short == {-3, 5}
        assert long == {19, 35}
    else:
        assert not any(r.cell.kind is ResultKind.INTERCEPTION for r in new.defense)
        assert report["int_incidence"] == "modeled-zero-no-floor"


def test_nondefense_and_run_cells_are_exact(pair: tuple) -> None:
    old, new, _ = pair
    assert replace(new, defense=old.defense) == old
    assert [r for r in new.defense if r.play.value < 6] == [
        r for r in old.defense if r.play.value < 6
    ]


def test_domains_keep_true_whole_flags_and_variable_cells() -> None:
    old = fictional(interceptions=True)
    rows = tuple(r for r in old.defense if r.defense is Defense.D and r.play is Play.SIX)
    rows = tuple(
        replace(
            r,
            cell=parse_cell(
                "(7)"
                if r.roll == 1
                else "-2*"
                if r.roll == 2
                else "INT X"
                if r.roll == 5
                else "BLACK"
                if r.roll == 3
                else "2",
                provenance(),
            ),
        )
        for r in rows
    )
    options = enumerate_column(rows, int_cap=6, qt_cap=3)
    assert options
    for option in options.values():
        assert option.codes[0] == option.codes[1] == option.codes[4] == -1
        assert option.mass[1] >= 1  # fixed normal variable INT still contributes


def test_infeasible_zero_coverage_refuses_instead_of_mislabeling_role() -> None:
    old = team_chart("No coverage support")
    new, report = apply_coupled_model(
        old, known_depths=((3, 1),), unknown_locations=0, source_identity="b" * 64
    )
    assert new == old
    assert report["status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("bad", [True, -1, 1.0])
def test_unknown_count_requires_nonnegative_integer(bad: object) -> None:
    with pytest.raises(ValueError):
        apply_coupled_model(
            fictional(interceptions=False),
            known_depths=((3, 1),),
            unknown_locations=bad,
            source_identity="b" * 64,
        )


def test_exact_column_numeric_mean_is_original_formation_target() -> None:
    old = fictional(interceptions=True)
    rows = tuple(r for r in old.defense if r.defense is Defense.C and r.play is Play.EIGHT)
    options = enumerate_column(rows, int_cap=6, qt_cap=3)
    assert all(o.mean_error == Fraction() for o in options.values())


def test_edit_objective_counts_emitted_blank_semantics() -> None:
    chart = fictional(interceptions=False)
    rows = tuple(
        replace(r, cell=parse_cell("", provenance()))
        for r in chart.defense
        if r.defense is Defense.A and r.play is Play.SIX
    )
    assert enumerate_column(rows, int_cap=0, qt_cap=0)[0, 0, 0].edits == 0


def test_literal_numeric_zero_is_not_same_as_emitted_no_change() -> None:
    chart = fictional(interceptions=False)
    rows = tuple(
        replace(
            r,
            cell=NormalizedCell(ResultKind.YARDS, provenance(), yards=0)
            if r.roll == 1
            else parse_cell("", provenance()),
        )
        for r in chart.defense
        if r.defense is Defense.A and r.play is Play.SIX
    )
    assert enumerate_column(rows, int_cap=0, qt_cap=0)[0, 0, 0].edits == 1


def test_minimum_pressure_budget_includes_pinned_mutable_a_pressure() -> None:
    old = fictional(interceptions=False)
    old = replace(
        old,
        defense=tuple(
            replace(r, cell=parse_cell("2", provenance()))
            if r.play.value >= 6
            and r.defense is not Defense.A
            and r.cell.kind is ResultKind.QUARTERBACK_TRAPPED
            else r
            for r in old.defense
        ),
    )
    _, report = apply_coupled_model(
        old, known_depths=(), unknown_locations=0, source_identity="c" * 64
    )
    assert report["QT_call_budgets"] == (1, 5, 1, 5)


def ordinary_offense(*, protected: bool = False) -> TeamChart:
    chart = team_chart("Fictional ordinary offense", offense=10)
    return replace(
        chart,
        offense=tuple(
            replace(r, cell=parse_cell("(12)", provenance())) if protected else r
            for r in chart.offense
        ),
        supplemental=tuple(
            replace(r, cell=parse_cell("-6", provenance()))
            if r.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else r
            for r in chart.supplemental
        ),
    )


@pytest.mark.parametrize("play", [Play.SIX, Play.EIGHT])
def test_actual_completion_countercost_survives_joint_priority(pair: tuple, play: Play) -> None:
    _, chart, _ = pair
    a, _ = terminal_credit_counts(ordinary_offense(), chart, play, Defense.A)
    f, _ = terminal_credit_counts(ordinary_offense(), chart, play, Defense.F)
    # INT remains an explicit pending branch; this compares the known numeric
    # completion component, not terminal INT returns or historical frequency.
    assert f["completion"] > a["completion"]


@pytest.mark.parametrize("play", [Play.SEVEN, Play.NINE])
def test_exact_qt_request_has_actual_negative_qt_sack_effect(pair: tuple, play: Play) -> None:
    _, chart, _ = pair
    a, _ = terminal_credit_counts(ordinary_offense(), chart, play, Defense.A)
    f, _ = terminal_credit_counts(ordinary_offense(), chart, play, Defense.F)
    assert f["sack"] - a["sack"] == 216 * 3


def test_protected_offense_suppresses_normal_defensive_changes(pair: tuple) -> None:
    _, chart, _ = pair
    offense = ordinary_offense(protected=True)
    assert primary_counts(offense, chart, Play.SEVEN, Defense.A) == primary_counts(
        offense, chart, Play.SEVEN, Defense.F
    )
