"""Payload-only successor to the frozen private v3 authored defense model."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from fractions import Fraction
from typing import Any, cast

from bowl_bound.models import BoundingBox, Priority, Provenance, ResultKind, TeamChart
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import parse_cell

from .conditional_depth_balance import balance_conditionals
from .coupled_depths import DepthSupport
from .coupled_event_risks import WEIGHTS, _digest, apply_coupled_model
from .coupled_event_risks import model_identity as parent_identity
from .research_inputs import semantic_sha256

CONTRACT = {
    "origin": "authored-bb-conditional-depth-balanced-private-v4",
    "parent_model": parent_identity(),
    "population": "transported-normal/nonOOB/fixed-located-INT-only",
    "coordinate_order": "play-ascending;formation-A-F;roll-ascending",
    "preserve": "per-group(weight-class,depth)inventory;all-nonpayload-facts;unknowns",
    "objective": (
        "equal-active-formation-W1-sum+equal-active-call-W1-sum;worst-conditional-CDF;"
        "payload-edits-vs-immutable-v3-witness;canonical-addressed-values"
    ),
    "zero_population": "undefined-conditional-excluded;no-INT-dormant",
    "depth_prior": "parent-authored-short/long-CDF;not-historical-formation/call-truth",
    "downstream": "selected-INT_MIN/landing-diagnostic-not-optimization-target",
    "scope": "post-parent-allocation-payload-only;not-global-layout-optimum-or-fit-approval",
}


def model_identity() -> dict[str, object]:
    """Return the exact compiled contract admitted by the private transport."""
    return {
        "origin": CONTRACT["origin"],
        "sha256": _digest(CONTRACT),
        "authored_experimental": True,
        "contract": deepcopy(CONTRACT),
    }


def apply_balanced_model(
    chart: TeamChart, *, known_depths: DepthSupport, unknown_locations: int, source_identity: str
) -> tuple[TeamChart, dict[str, object]]:
    """Balance conditional depth CDFs while preserving the frozen v3 joint law inputs.

    Only fixed located normal INT payloads move within their original physical
    weight class and short/long group. Zero-INT conditionals are undefined.
    Source unknowns and all other normalized football facts remain unchanged.
    """
    parent, raw_report = apply_coupled_model(
        chart,
        known_depths=known_depths,
        unknown_locations=unknown_locations,
        source_identity=source_identity,
    )
    return _balance_parent_payloads(chart, parent, raw_report, model_identity())


def _balance_parent_payloads(
    chart: TeamChart,
    parent: TeamChart,
    raw_report: dict[str, object],
    identity: dict[str, object],
) -> tuple[TeamChart, dict[str, object]]:
    """Reuse the exact payload stage for a separately compiled parent model."""
    original = semantic_sha256(chart)
    parent_report = cast(dict[str, Any], raw_report)
    parent_sha = semantic_sha256(parent)
    report = deepcopy(parent_report)
    report.update(
        model_identity=identity,
        parent_model_identity=parent_report["model_identity"],
        parent_output_sha256=parent_sha,
        parent_depth=deepcopy(parent_report.get("depth", {})),
    )
    if report["status"] != "represented":
        return parent, report
    rows = {(r.defense, r.play, r.roll): r for r in parent.defense}
    ancestry = dict(parent_report["derived_ancestry"])
    balances = {}
    edits = 0
    for group, plays in (("short", (6, 7)), ("long", (8, 9))):
        population = tuple(
            sorted(
                (
                    r
                    for r in parent.defense
                    if r.play.value in plays
                    and r.cell.kind is ResultKind.INTERCEPTION
                    and r.cell.priority is Priority.NORMAL
                    and not r.cell.out_of_bounds
                    and r.cell.variable is None
                    and type(r.cell.yards) is int
                ),
                key=lambda r: (r.play.value, r.defense.value, r.roll),
            )
        )
        if not population:
            continue
        support = tuple((x, Fraction(w)) for x, w in parent_report["depth"][group]["known_support"])
        balanced = balance_conditionals(
            tuple(WEIGHTS[r.roll - 1] for r in population),
            tuple(cast(int, r.cell.yards) for r in population),
            tuple(r.defense.value for r in population),
            tuple(r.play.value for r in population),
            support,
        )
        balances[group] = {
            **{k: str(v) if isinstance(v, Fraction) else v for k, v in asdict(balanced).items()},
            "coordinates": tuple((r.defense.value, r.play.value, r.roll) for r in population),
            "parent_locations": tuple(r.cell.yards for r in population),
            "excluded_formations": tuple(
                d for d in "ABCDEF" if d not in balanced.active_formations
            ),
            "excluded_calls": tuple(p for p in plays if p not in balanced.active_calls),
        }
        report["depth"][group].update(
            coordinate_balance=CONTRACT["objective"],
            pair_wasserstein_sum=str(balanced.call_w1),
            formation_wasserstein_sum=str(balanced.formation_w1),
            worst_conditional_cdf=str(balanced.worst_cdf),
        )
        for row, location in zip(population, balanced.locations, strict=True):
            if location == row.cell.yards:
                continue
            edits += 1
            token = f"INT {location}"
            recipe = {
                "model": identity["sha256"],
                "baseline": original,
                "parent_model": parent_report["model_identity"]["sha256"],
                "parent_output": parent_sha,
                "parent_cell": semantic_sha256(row),
                "source": parent_report["source_identity"],
                "coordinate": (row.defense.value, row.play.value, row.roll),
                "group": group,
                "token": token,
            }
            sha = _digest(recipe)
            ancestry[sha] = recipe
            provenance = Provenance(
                sha,
                str(identity["origin"]) + ".json",
                1,
                BoundingBox(row.play.value, row.roll, row.play.value + 1, row.roll + 1),
                token,
                CELL_LEGEND[chart_color_for_csv_token(token)].rgb_color,
            )
            rows[row.defense, row.play, row.roll] = replace(row, cell=parse_cell(token, provenance))
    result = replace(parent, defense=tuple(rows[r.defense, r.play, r.roll] for r in parent.defense))
    if semantic_sha256(chart) != original:
        raise ValueError("balanced model input changed before returning candidate")
    report.update(
        output_sha256=semantic_sha256(result),
        derived_ancestry=ancestry,
        conditional_balance=balances or {"status": "dormant", "reason": "no-transported-INT"},
        parent_depth_payload_edits=parent_report["depth_payload_edits"],
        depth_payload_edits=sum(
            a.cell.kind is b.cell.kind is ResultKind.INTERCEPTION and a.cell.yards != b.cell.yards
            for a, b in zip(chart.defense, result.defense, strict=True)
        ),
        conditional_payload_edits_vs_parent=edits,
    )
    return result, report
