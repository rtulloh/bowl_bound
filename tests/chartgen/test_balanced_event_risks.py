"""Payload-only successor preserves v3 mechanics and improves conditional CDFs."""

from collections import Counter
from dataclasses import replace

import pytest

from bowl_bound.models import ResultKind
from bowl_bound.team_csv import parse_cell
from tests.chartgen.test_coupled_event_risks import fictional
from tools.chartgen.balanced_event_risks import apply_balanced_model, model_identity
from tools.chartgen.coupled_event_risks import apply_coupled_model
from tools.chartgen.coupled_event_risks import model_identity as parent_identity
from tools.chartgen.research_inputs import semantic_sha256

SOURCE = ((-3, 1), (5, 1), (19, 1), (35, 1))


@pytest.fixture(scope="module", params=[False, True])
def subject(request):
    baseline = fictional(interceptions=request.param)
    args = dict(known_depths=SOURCE, unknown_locations=2, source_identity="a" * 64)
    parent, _ = apply_coupled_model(baseline, **args)
    result, report = apply_balanced_model(baseline, **args)
    return baseline, parent, result, report


def test_every_nonpayload_fact_and_unchanged_ancestry_survive(subject):
    _, parent, result, report = subject
    assert report["status"] == "represented"
    assert replace(result, defense=parent.defense) == parent
    for old, new in zip(parent.defense, result.defense, strict=True):
        if old != new:
            assert old.cell.kind is new.cell.kind is ResultKind.INTERCEPTION
            assert old.cell.yards != new.cell.yards
            assert (
                replace(new.cell, yards=old.cell.yards, provenance=old.cell.provenance) == old.cell
            )
            recipe = report["derived_ancestry"][new.cell.provenance.source_sha256]
            assert recipe["parent_cell"] == semantic_sha256(old)
            assert recipe["parent_output"] == semantic_sha256(parent)
        else:
            assert old.cell.provenance == new.cell.provenance


def test_exact_weight_class_atom_inventory_and_global_histogram_survive(subject):
    _, parent, result, report = subject
    for plays in ((6, 7), (8, 9)):

        def inventory(chart, plays=plays):
            return Counter(
                ((12, 11, 9, 3, 1)[r.roll - 1], r.cell.yards)
                for r in chart.defense
                if r.play.value in plays and r.cell.kind is ResultKind.INTERCEPTION
            )

        assert inventory(result) == inventory(parent)
    assert report["source_unknown_locations"] == 2
    assert report["source_conditional_status"] == "UNKNOWN"
    assert report["source_fit"] == "UNVERIFIED"


def test_new_model_binds_parent_and_exact_output(subject):
    baseline, parent, result, report = subject
    assert report["model_identity"] == model_identity()
    assert model_identity()["contract"]["parent_model"] == parent_identity()
    assert report["parent_output_sha256"] == semantic_sha256(parent)
    assert report["output_sha256"] == semantic_sha256(result)
    assert report["baseline_sha256"] == semantic_sha256(baseline)
    assert model_identity()["sha256"] != parent_identity()["sha256"]


def test_zero_incidence_stays_dormant_without_inventing_source_support():
    baseline = fictional(interceptions=False)
    result, report = apply_balanced_model(
        baseline, known_depths=(), unknown_locations=3, source_identity="a" * 64
    )
    assert report["status"] == "represented"
    assert report["conditional_balance"] == {"status": "dormant", "reason": "no-transported-INT"}
    assert not any(r.cell.kind is ResultKind.INTERCEPTION for r in result.defense)


def test_producer_is_independent_of_defense_tuple_iteration():
    baseline = fictional(interceptions=True)
    args = dict(known_depths=SOURCE, unknown_locations=2, source_identity="a" * 64)
    a, ar = apply_balanced_model(baseline, **args)
    b, br = apply_balanced_model(replace(baseline, defense=baseline.defense[::-1]), **args)
    # Complete source identity/order deliberately differs, addressed football facts do not.
    assert {(r.defense, r.play, r.roll): (r.cell.kind, r.cell.yards) for r in a.defense} == {
        (r.defense, r.play, r.roll): (r.cell.kind, r.cell.yards) for r in b.defense
    }
    assert ar["conditional_balance"] == br["conditional_balance"]


def test_fixed_variable_protected_and_oob_whole_cells_are_not_payload_slots(monkeypatch):
    import tools.chartgen.balanced_event_risks as producer

    baseline = fictional(interceptions=True)
    args = dict(known_depths=SOURCE, unknown_locations=2, source_identity="a" * 64)
    parent, report = apply_coupled_model(baseline, **args)
    locations = [i for i, r in enumerate(parent.defense) if r.cell.kind is ResultKind.INTERCEPTION]
    rows = list(parent.defense)
    for i, token in zip(locations[:3], ("INT X", "(9)", "-2*"), strict=True):
        rows[i] = replace(rows[i], cell=parse_cell(token, rows[i].cell.provenance))
    fixed_parent = replace(parent, defense=tuple(rows))
    # Pure wrapper boundary injection: the actual parent producer is covered
    # separately. This supplies whole facts that may never become payload slots.
    monkeypatch.setattr(producer, "apply_coupled_model", lambda *a, **kw: (fixed_parent, report))
    result, _ = producer.apply_balanced_model(baseline, **args)
    assert all(result.defense[i] == fixed_parent.defense[i] for i in locations[:3])


def test_constant_pool_does_not_acquire_artificial_depth_diversity():
    result, report = apply_balanced_model(
        fictional(interceptions=True),
        known_depths=((11, 1),),
        unknown_locations=0,
        source_identity="a" * 64,
    )
    assert {r.cell.yards for r in result.defense if r.cell.kind is ResultKind.INTERCEPTION} == {11}
    assert all(g["assignments_evaluated"] == 1 for g in report["conditional_balance"].values())
