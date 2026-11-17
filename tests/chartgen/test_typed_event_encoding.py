"""Whole-cell protection and truthful ancestry for the private typed producer."""

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from bowl_bound.models import Defense, Play, ResultKind
from bowl_bound.team_csv import format_cell, parse_cell
from tests.chartgen.test_event_risks import primary_counts, terminal_credit_counts
from tests.chartgen.test_typed_event_model import legacy_factory
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chartgen.research_inputs import semantic_sha256
from tools.chartgen.typed_event_risks import allocate_typed_column, apply_typed_event_model


@pytest.mark.parametrize(
    "token",
    [
        "(4)",
        "[4]",
        "4*",
        "(B)",
        "QR",
        "F + 6",
        "QT",
        "INT X",
        "INT -X",
        "INT DS",
        "INT T1",
        "INT T2",
        "INT T3",
        "X",
    ],
)
def test_inactive_or_flagged_whole_cells_and_their_ancestry_are_fixed(token):
    baseline = legacy_factory()
    baseline = replace(
        baseline,
        defense=tuple(
            replace(row, cell=parse_cell(token, provenance()))
            if row.defense is Defense.D and row.play is Play.SIX and row.roll == 1
            else row
            for row in baseline.defense
        ),
    )
    before = semantic_sha256(baseline)
    candidate, _ = apply_typed_event_model(baseline)
    old = next(
        row
        for row in baseline.defense
        if row.defense is Defense.D and row.play is Play.SIX and row.roll == 1
    )
    assert (
        next(
            row
            for row in candidate.defense
            if row.defense is Defense.D and row.play is Play.SIX and row.roll == 1
        )
        == old
    )
    assert semantic_sha256(baseline) == before


def test_a_b_c_runs_nondefense_and_f_interceptions_are_whole_fact_invariants():
    baseline = legacy_factory()
    candidate, receipt = apply_typed_event_model(baseline)
    assert candidate.offense == baseline.offense
    assert candidate.supplemental == baseline.supplemental
    assert candidate.special_teams == baseline.special_teams
    assert candidate.pat_outcomes == baseline.pat_outcomes
    assert candidate.recovery_range == baseline.recovery_range
    for old, new in zip(baseline.defense, candidate.defense, strict=True):
        if (
            old.defense in (Defense.A, Defense.B, Defense.C)
            or old.play.value < 6
            or (old.defense is Defense.F and old.cell.kind is ResultKind.INTERCEPTION)
        ):
            assert new == old
    assert receipt["source_fit"] == "UNVERIFIED"
    assert all(row["conditional_depth"] == "UNKNOWN" for row in receipt["int_support"].values())


def test_changed_cells_have_derived_recipe_text_color_and_exact_baseline_ancestry():
    baseline = legacy_factory()
    candidate, receipt = apply_typed_event_model(baseline)
    assert receipt["baseline_sha256"] == semantic_sha256(baseline)
    assert receipt["output_sha256"] == semantic_sha256(candidate)
    changed = 0
    for old, new in zip(baseline.defense, candidate.defense, strict=True):
        if old == new:
            continue
        changed += 1
        p = new.cell.provenance
        assert p is not None and old.cell.provenance is not None
        assert p.original_text == format_cell(new.cell)
        assert p.filename == "authored-bb-typed-joint-opportunity-private-v2.json"
        recipe = receipt["derived_ancestry"][p.source_sha256]
        assert recipe["baseline_sha256"] == receipt["baseline_sha256"]
        assert semantic_sha256(old) in recipe["baseline_cells"]
        assert (
            hashlib.sha256(
                json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            == p.source_sha256
        )
        assert parse_cell(p.original_text, p) == new.cell
    assert changed > 0
    assert apply_typed_event_model(baseline) == (candidate, receipt)


def test_zero_printed_int_is_unknown_and_zero_inc_concessions_are_saturated():
    baseline = team_chart("Fictional unsupported model", defense=0)
    candidate, receipt = apply_typed_event_model(baseline)
    assert all(value["state"] == "unknown" for value in receipt["int_support"].values())
    assert not any(row.cell.kind is ResultKind.INTERCEPTION for row in candidate.defense)
    for formation, play in ((Defense.D, Play.EIGHT), (Defense.E, Play.SIX), (Defense.F, Play.SIX)):
        record = receipt["allocations"][f"{formation.value}/{play.value}"]
        assert record["status"] == "saturated-negative-request"
        assert tuple(
            row for row in candidate.defense if row.defense is formation and row.play is play
        ) == tuple(row for row in baseline.defense if row.defense is formation and row.play is play)


@pytest.mark.parametrize("mapping", [{}, {ResultKind.INCOMPLETE: 1, ResultKind.INTERCEPTION: 0}])
def test_explicit_incomplete_direction_contract_is_not_replaced_with_defaults(mapping):
    chart = team_chart("Fictional admission", defense=0)
    rows = tuple(row for row in chart.defense if row.defense is Defense.D and row.play is Play.SIX)
    with pytest.raises(ValueError, match="complete"):
        allocate_typed_column(rows, {ResultKind.INCOMPLETE: Fraction(3)}, directions=mapping)


def test_protected_offense_suppresses_printed_event_changes():
    baseline = legacy_factory()
    candidate, _ = apply_typed_event_model(baseline)
    offense = team_chart("Fictional protected offense", offense=10)
    offense = replace(
        offense,
        offense=tuple(
            replace(row, cell=parse_cell("(10)", provenance())) for row in offense.offense
        ),
    )
    before = primary_counts(offense, baseline, Play.SIX, Defense.D)
    after = primary_counts(offense, candidate, Play.SIX, Defense.D)
    assert before == after == {ResultKind.YARDS.value: 216 * 36}


@pytest.mark.parametrize("offensive_yards", [5, 15])
def test_crossed_fixed_offenses_retain_numeric_defense_strength(offensive_yards):
    baseline = legacy_factory()
    results = []
    for defense_yards in (-3, 3):
        chart = replace(
            baseline,
            defense=tuple(
                replace(row, cell=parse_cell(str(defense_yards), provenance()))
                if row.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}
                and row.cell.priority.value == "normal"
                and not row.cell.out_of_bounds
                else row
                for row in baseline.defense
            ),
        )
        candidate, receipt = apply_typed_event_model(chart)
        record = receipt["allocations"]["D/6"]
        assert record["original_formation_numeric_mean"] == str(defense_yards)
        assert record["numeric_mean_error"] == "0"
        results.append(
            terminal_credit_counts(
                team_chart("Fictional crossed offense", offense=offensive_yards),
                candidate,
                Play.SIX,
                Defense.D,
            )
        )
    assert results[0][0] == results[1][0]
    assert results[0][1] < results[1][1]


def test_fixed_normal_variable_event_mass_is_not_omitted_from_joint_objective():
    chart = team_chart("Fictional fixed event contribution", defense=0)
    rows = tuple(
        replace(row, cell=parse_cell("INT X", provenance())) if row.roll == 5 else row
        for row in chart.defense
        if row.defense is Defense.D and row.play is Play.SIX
    )
    selected, report = allocate_typed_column(
        rows,
        {ResultKind.INCOMPLETE: Fraction(3), ResultKind.INTERCEPTION: Fraction(1)},
        int_locations=((17, 1),),
    )
    assert selected[4] == rows[4]
    assert report["fixed_normal_family_mass"] == {"incomplete": 0, "interception": 1}
    assert dict(zip(report["families"], report["represented"], strict=True)) == {
        "incomplete": 3,
        "interception": 1,
    }
    assert report["requested_family_error"] == report["complete_partition_error"] == "0"
    assert all(point[1] >= 1 for point in report["attainable"])
