"""Budget-relative experimental tactics do not manufacture rare outcomes."""

from dataclasses import replace
from itertools import product
from typing import Any, cast

import pytest

from bowl_bound.models import Defense, Play, Provenance, ResultKind
from bowl_bound.team_csv import parse_cell
from tests.chartgen.test_coupled_event_risks import fictional, mass
from tools.chartgen.alpha_event_risks import apply_alpha_model, model_identity

SOURCE = ((-3, 1), (5, 1), (19, 1), (35, 1))
KINDS = (ResultKind.INCOMPLETE, ResultKind.INTERCEPTION, ResultKind.QUARTERBACK_TRAPPED)


def fixture(inc, interception, pressure):
    base = fictional(interceptions=False)
    inc_row = {0: None, 1: 5, 3: 4, 9: 3}[inc]
    return replace(
        base,
        defense=tuple(
            replace(
                r,
                cell=parse_cell(
                    "BLACK"
                    if r.roll == inc_row
                    else "INT 11"
                    if interception and r.roll == 5
                    else "QT"
                    if pressure and r.roll == 5
                    else "2",
                    cast(Provenance, r.cell.provenance),
                ),
            )
            if r.play.value >= 6
            else r
            for r in base.defense
        ),
    )


@pytest.fixture(
    scope="module", params=[(0, 0, 0), (1, 0, 0), (3, 0, 0), (3, 0, 1), (9, 1, 0), (0, 1, 0)]
)
def pair(request):
    old = fixture(*request.param)
    new, report = apply_alpha_model(
        old, known_depths=SOURCE, unknown_locations=2, source_identity="a" * 64
    )
    return old, new, report


def test_every_budget_case_is_represented_without_invented_events(pair):
    old, new, report = pair
    report = cast(dict[str, Any], report)
    assert report["status"] == "represented"
    for p in Play:
        if p.value < 6:
            continue
        for kind in KINDS:
            assert sum(mass(new, d, p, kind) for d in Defense) == sum(
                mass(old, d, p, kind) for d in Defense
            )
    for d in Defense:
        assert sum(mass(new, d, p, ResultKind.INTERCEPTION) for p in Play if p.value >= 6) == sum(
            mass(old, d, p, ResultKind.INTERCEPTION) for p in Play if p.value >= 6
        )
    assert replace(new, defense=old.defense) == old
    assert [r for r in new.defense if r.play.value < 6] == [
        r for r in old.defense if r.play.value < 6
    ]


def test_best_represented_roles_never_reverse_the_declared_opportunity(pair):
    _, chart, report = pair
    report = cast(dict[str, Any], report)
    assert report["status"] == "represented"
    for p in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
        a = mass(chart, Defense.A, p, ResultKind.INCOMPLETE)
        protect, concede = (Defense.D, Defense.E) if p.value < 8 else (Defense.E, Defense.D)
        assert mass(chart, protect, p, ResultKind.INCOMPLETE) >= a
        assert mass(chart, concede, p, ResultKind.INCOMPLETE) <= a
        if p in (Play.SIX, Play.EIGHT):
            assert sum(mass(chart, Defense.F, p, k) for k in KINDS) <= sum(
                mass(chart, Defense.A, p, k) for k in KINDS
            )
        else:
            assert mass(chart, Defense.F, p, ResultKind.QUARTERBACK_TRAPPED) >= mass(
                chart, Defense.A, p, ResultKind.QUARTERBACK_TRAPPED
            )


def test_zero_budget_has_explicit_dormancy_and_no_accuracy_claim():
    new, report = apply_alpha_model(
        fixture(0, 0, 0), known_depths=(), unknown_locations=2, source_identity="a" * 64
    )
    report = cast(dict[str, Any], report)
    assert report["status"] == "represented"
    assert not any(r.cell.kind in KINDS for r in new.defense)
    assert all(v["status"] == "dormant" for v in report["role_effects"].values())
    assert report["source_fit"] == "UNVERIFIED"
    assert report["model_identity"] == model_identity()


def test_positive_small_budget_reports_limited_contrasts_without_negative_requests():
    _, report = apply_alpha_model(
        fixture(1, 0, 0), known_depths=(), unknown_locations=0, source_identity="a" * 64
    )
    report = cast(dict[str, Any], report)
    assert report["status"] == "represented"
    assert any(v["status"] == "limited-joint-optimum" for v in report["role_effects"].values())
    assert report["model_identity"]["origin"] == "authored-bb-budget-aware-v1"


def test_role_residuals_reconcile_to_joint_objective(pair):
    _, _, report = pair
    assert int(report["objective"][0]) == sum(
        v["residual"] for v in report["role_effects"].values() if v["residual"] is not None
    )


def test_small_incidence_first_objective_matches_independent_finite_oracle():
    _, report = apply_alpha_model(
        fixture(1, 0, 0), known_depths=(), unknown_locations=0, source_identity="a" * 64
    )
    report = cast(dict[str, Any], report)
    expected = 0
    for call in (6, 7, 8, 9):
        costs = []
        for a, b, c, d, e, f in product((0, 1, 3, 4), repeat=6):
            if a + b + c + d + e + f != 6:
                continue
            protect, concede = (d, e) if call < 8 else (e, d)
            if protect < a or concede > a or call % 2 == 0 and f > a:
                continue
            cost = abs(protect - a - 3) + abs(concede - a + 3)
            if call % 2 == 0:
                cost += 2 * abs(f - a + 3)  # INC and complete-family counter requests
            costs.append(cost)
        expected += min(costs)
    assert int(report["objective"][0]) == expected


def test_fixed_whole_facts_and_their_normal_mass_remain_exact():
    old = fixture(0, 0, 0)
    tokens = {1: "INT X", 2: "(7)", 3: "-2*"}
    old = replace(
        old,
        defense=tuple(
            replace(r, cell=parse_cell(tokens[r.roll], cast(Provenance, r.cell.provenance)))
            if r.play.value >= 6 and r.roll in tokens
            else r
            for r in old.defense
        ),
    )
    new, report = apply_alpha_model(
        old, known_depths=(), unknown_locations=2, source_identity="a" * 64
    )
    report = cast(dict[str, Any], report)
    assert report["status"] == "represented"
    assert all(
        a == b
        for a, b in zip(old.defense, new.defense, strict=True)
        if a.play.value < 6 or a.roll in tokens
    )
    assert report["fixed_normal_INT_mass_outside_depth_transport"] == 288
    assert report["conditional_balance"]["status"] == "dormant"
