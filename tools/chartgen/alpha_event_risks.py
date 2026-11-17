"""Experimental budget-aware alpha policy, separate from strict v3/v4 history."""

from __future__ import annotations

from copy import deepcopy

from bowl_bound.models import Defense, TeamChart

from .balanced_event_risks import _balance_parent_payloads
from .balanced_event_risks import model_identity as prior_identity
from .coupled_depths import DepthSupport
from .coupled_event_risks import FORMS, PLAYS, _digest, _mass, apply_coupled_model

TOOL_VERSION = "bb-chartgen-budget-alpha-v1"
CONTRACT = {
    "origin": "authored-bb-budget-aware-v1",
    "prior_model": prior_identity(),
    "scope": "existing-published-2007-116;no-new-B-policy/no-2008",
    "hard_budgets": "exact-original-call-INC/INT/QT-and-formation-INT;fixed-whole-facts",
    "hard_roles": "nonreversing-vs-revisedA;equality-is-not-strict-success",
    "signed_requests": "DE-INC+/-3;DE-pairINT+/-2;F7/9QT+3;F6/8INC-and-total-family-3",
    "zero": "dormant-undefined-role-no-floor;unknown-source-not-observed-zero",
    "objective": (
        "active-signed-role-L1;original-family-L1;complete-partition-L1;"
        "original-formation-numeric-mean;family/numeric-edits;canonical"
    ),
    "payload": "unchanged-prior-sourceCDF-and-exact-conditional-balancing-stage",
    "authority": "authored-experimental-not-historical-formation-or-fit-approval",
}


def model_identity() -> dict[str, object]:
    """Return the compiled experimental contract, not a fit certification."""
    return {
        "origin": CONTRACT["origin"],
        "sha256": _digest(CONTRACT),
        "authored_experimental": True,
        "contract": deepcopy(CONTRACT),
    }


def _role_effects(old: TeamChart, new: TeamChart) -> dict[str, dict[str, object]]:
    original = {
        (d, p): _mass(tuple(r for r in old.defense if r.defense is d and r.play is p))
        for d in FORMS
        for p in PLAYS
    }
    actual = {
        (d, p): _mass(tuple(r for r in new.defense if r.defense is d and r.play is p))
        for d in FORMS
        for p in PLAYS
    }
    effects = {}

    def add(key: str, requested: int, achieved: int, budget: int) -> None:
        effects[key] = {
            "requested_delta": requested,
            "represented_delta": achieved,
            "reference_chart_mass": budget,
            "residual": abs(achieved - requested) if budget else None,
            "status": "dormant"
            if not budget
            else "requested-attained"
            if achieved == requested
            else "limited-joint-optimum",
            "strict_direction_achieved": (achieved * requested > 0) if budget else None,
        }

    for p in PLAYS:
        inc = sum(original[d, p][0] for d in FORMS)
        qt = sum(original[d, p][2] for d in FORMS)
        for d in (Defense.D, Defense.E):
            sign = 1 if (d is Defense.D) == (p.value < 8) else -1
            add(
                f"{d.value}/{p.value}/INC", sign * 3, actual[d, p][0] - actual[Defense.A, p][0], inc
            )
        if p.value % 2:
            add(f"F/{p.value}/QT", 3, actual[Defense.F, p][2] - actual[Defense.A, p][2], qt)
        else:
            add(f"F/{p.value}/INC", -3, actual[Defense.F, p][0] - actual[Defense.A, p][0], inc)
            add(
                f"F/{p.value}/all-normal-family",
                -3,
                sum(actual[Defense.F, p]) - sum(actual[Defense.A, p]),
                sum(sum(original[d, p]) for d in FORMS),
            )
    int_mass = sum(original[d, p][1] for d in FORMS for p in PLAYS)
    for d in (Defense.D, Defense.E):
        for name, plays in (("short", PLAYS[:2]), ("long", PLAYS[2:])):
            sign = 1 if (d is Defense.D) == (name == "short") else -1
            add(
                f"{d.value}/{name}/INT",
                sign * 2,
                sum(actual[d, p][1] - actual[Defense.A, p][1] for p in plays),
                int_mass,
            )
    return effects


def apply_alpha_model(
    chart: TeamChart, *, known_depths: DepthSupport, unknown_locations: int, source_identity: str
) -> tuple[TeamChart, dict[str, object]]:
    """Preserve event mass and choose jointly attainable authored opportunities."""
    parent, report = apply_coupled_model(
        chart,
        known_depths=known_depths,
        unknown_locations=unknown_locations,
        source_identity=source_identity,
        _budget_aware=True,
    )
    candidate, report = _balance_parent_payloads(chart, parent, report, model_identity())
    if report["status"] == "represented":
        report["role_effects"] = _role_effects(chart, candidate)
        report["tactical_status"] = "joint-budget-optimum-not-universal-strict-role-pass"
        report["tool_version"] = TOOL_VERSION
        report["objective_scope"] = CONTRACT["objective"]
        for label, subject in (("original", chart), ("represented", candidate)):
            report[f"{label}_normal_family_totals"] = {
                f"{d.value}/{p.value}": _mass(
                    tuple(r for r in subject.defense if r.defense is d and r.play is p)
                )
                for d in FORMS
                for p in PLAYS
            }
    return candidate, report
