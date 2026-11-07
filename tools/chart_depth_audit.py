"""Independent checks of declared depth policy against ordinary chart facts.

This verifier consumes a frozen policy document and source observations. It does
not call the producer's evidence selector or allocator.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict
from fractions import Fraction
from itertools import product
from typing import Any

from bowl_bound.models import Defense, Play, ResultKind, TeamChart
from bowl_bound.resolution import resolve_cells


class DepthAuditError(ValueError):
    """A generated depth or preserved football fact violates the declared model."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DepthAuditError(message)


def _facts(row: Any) -> dict[str, Any]:
    facts = asdict(row)
    facts["cell"].pop("provenance")
    return facts


def audit_depth_change(
    baseline: TeamChart,
    candidate: TeamChart,
    offense_events: Sequence[Any],
    defense_events: Sequence[Any],
    contract: dict[str, Any],
    *,
    prior_strength: int = 4,
) -> dict[str, Any]:
    """Check source support, unchanged incidence and real Priority-selected depths."""
    # Independently enumerate physical faces; uniform row totals are not dice.
    ow = Counter(
        10 * b + a + c
        for b, a, c in product((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5))
    )
    dw = Counter(a + b for a, b in product((1, 1, 1, 2, 2, 3), (0, 0, 0, 0, 1, 2)))
    _require(sum(ow.values()) == 216 and sum(dw.values()) == 36, "physical dice census")
    _require(
        baseline.name == candidate.name
        and baseline.season == candidate.season
        and baseline.schema_version == candidate.schema_version
        and baseline.recovery_range == candidate.recovery_range,
        "team facts changed",
    )
    for table in ("supplemental", "special_teams", "pat_outcomes"):
        left, right = getattr(baseline, table), getattr(candidate, table)
        _require(len(left) == len(right), f"{table} inventory changed")
        for a, b in zip(left, right, strict=True):
            aa, bb = asdict(a), asdict(b)
            (aa if table == "pat_outcomes" else aa["cell"]).pop("provenance")
            (bb if table == "pat_outcomes" else bb["cell"]).pop("provenance")
            _require(aa == bb, f"{table} football facts changed")
    columns = {}
    for side, events, weights in (("offense", offense_events, ow), ("defense", defense_events, dw)):
        left, right = getattr(baseline, side), getattr(candidate, side)
        _require(len(left) == len(right), f"{side} inventory changed")
        supports = {}
        for play in range(6, 10):
            prior = contract["priors"].get(play, contract["priors"].get(str(play)))
            counts = Counter(
                {x: Fraction(w * prior_strength, sum(w for _, w in prior)) for x, w in prior}
            )
            marker = {
                6: "text:screen",
                7: "text:sprint-out",
                8: "text:bootleg",
                9: "text:drop-back",
            }[play]
            observed, missing, unmatched = 0, 0, 0
            for event in events:
                if event.kind != "interception" or event.no_play:
                    continue
                depth = event.interception_yards
                if depth is None:
                    depth = event.air_yards
                if depth is None:
                    missing += 1
                elif (
                    event.called_family == play
                    and event.family_confidence == "narrative"
                    and marker in event.family_evidence
                ):
                    counts[depth] += 1
                    observed += 1
                else:
                    unmatched += 1
            supports[play] = counts
            columns[f"{side}/{play}"] = {
                "observed_conditional_samples": observed,
                "unknown_locations": missing,
                "known_unmatched_calls": unmatched,
                "physical_INT_mass": {},
            }
        for a, b in zip(left, right, strict=True):
            aa, bb = _facts(a), _facts(b)
            if a.cell.kind is ResultKind.INTERCEPTION and a.play.value >= 6:
                _require(
                    type(b.cell.yards) is int and b.cell.variable is None,
                    "unqualified variable or missing INT depth",
                )
                _require(
                    b.cell.yards in supports[a.play.value],
                    f"unsupported conditional depth: {side}/{a.play.value}/{a.roll}",
                )
                aa["cell"].pop("yards")
                bb["cell"].pop("yards")
            _require(aa == bb, f"nondepth football fact changed: {side}/{a.play.value}/{a.roll}")
        for play in range(6, 10):
            groups = ("offense",) if side == "offense" else tuple("ABCDEF")
            for group in groups:
                rows = [
                    r
                    for r in right
                    if r.play.value == play and (side == "offense" or r.defense.value == group)
                ]
                mass = sum(weights[r.roll] for r in rows if r.cell.kind is ResultKind.INTERCEPTION)
                columns[f"{side}/{play}"]["physical_INT_mass"][group] = mass
    pairs = {}
    old_o = {(r.play, r.roll): r.cell for r in baseline.offense}
    new_o = {(r.play, r.roll): r.cell for r in candidate.offense}
    old_d = {(r.defense, r.play, r.roll): r.cell for r in baseline.defense}
    new_d = {(r.defense, r.play, r.roll): r.cell for r in candidate.defense}
    for play, formation in product((Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE), Defense):
        before_mass, after_mass = Counter(), Counter()
        before_depth, after_depth = Counter(), Counter()
        for offense_roll, defense_roll in product(ow, dw):
            mass = ow[offense_roll] * dw[defense_roll]
            before = resolve_cells(old_o[play, offense_roll], old_d[formation, play, defense_roll])
            after = resolve_cells(new_o[play, offense_roll], new_d[formation, play, defense_roll])
            _require(
                (before.operation, before.kind, before.source)
                == (after.operation, after.kind, after.source),
                "Priority mechanism changed",
            )
            before_mass[str(before.kind)] += mass
            after_mass[str(after.kind)] += mass
            if before.kind is ResultKind.INTERCEPTION:
                _require(type(after.yards) is int, "unresolved selected INT location")
                before_depth[before.yards] += mass
                after_depth[after.yards] += mass
        _require(
            before_mass == after_mass and sum(after_mass.values()) == 7776,
            "selected physical probability changed",
        )
        pairs[f"{play.value}/{formation.value}"] = {
            "physical_pairs": 7776,
            "selected_INT_mass": sum(after_depth.values()),
            "before_depth_histogram": dict(sorted(before_depth.items())),
            "after_depth_histogram": dict(sorted(after_depth.items())),
        }
    return {
        "status": "PASS-declared-policy-and-incidence-only",
        "columns": columns,
        "pairs": pairs,
        "physical_offense": 216,
        "physical_defense": 36,
        "historical_fit": "UNVERIFIED",
        "terminal_rules": "requires-engine-context-panel",
    }
