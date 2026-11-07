"""Bounded exhaustive verification of authored finite catch-depth encodings.

The target distributions are explicit inputs, bound by the caller to its source
and policy receipt. This module imports neither the producer nor its allocator.
A budget refusal is UNVERIFIED; it must never be counted as a qualified column.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
from itertools import product
from typing import Any

from bowl_bound.models import ResultKind, TeamChart

from .chart_depth_audit import DepthAuditError

Support = tuple[tuple[int, Fraction], ...]


def audit_slot_encoding(
    weights: tuple[int, ...],
    values: tuple[int, ...],
    target: Support,
    *,
    enumeration_budget: int = 2_000_000,
) -> dict[str, Any]:
    """Compare a candidate with every feasible assignment within a fixed budget."""
    if len(weights) != len(values) or any(type(w) is not int or w <= 0 for w in weights):
        raise DepthAuditError("finite encoding requires matching positive physical weights")
    atoms = tuple(x for x, _ in target)
    if (
        not atoms
        or atoms != tuple(sorted(set(atoms)))
        or any(type(x) is not int or p <= 0 for x, p in target)
        or type(enumeration_budget) is not int
        or enumeration_budget <= 0
    ):
        raise DepthAuditError("finite encoding requires sorted positive target support and budget")
    if any(type(x) is not int or x not in atoms for x in values):
        raise DepthAuditError("finite encoding has unsupported values")
    if not weights:
        return {
            "status": "dormant",
            "wasserstein": None,
            "cdf_error": None,
            "omitted_support": atoms,
        }
    evaluations = len(atoms) ** len(weights)
    if evaluations > enumeration_budget:
        return {
            "status": "UNVERIFIED-enumeration-budget",
            "assignments": evaluations,
            "budget": enumeration_budget,
        }
    total = sum(weights)
    normalization = sum(p for _, p in target)
    source_cdf = tuple(sum(p for x, p in target if x <= point) / normalization for point in atoms)

    def cost(assignment: tuple[int, ...]) -> tuple[Fraction, Fraction]:
        errors = tuple(
            abs(
                Fraction(
                    sum(w for x, w in zip(assignment, weights, strict=True) if x <= point), total
                )
                - expected
            )
            for point, expected in zip(atoms, source_cdf, strict=True)
        )
        return (
            sum((atoms[i + 1] - atoms[i]) * errors[i] for i in range(len(atoms) - 1)),
            max(errors),
        )

    observed = cost(values)
    optimum = min(cost(assignment) for assignment in product(atoms, repeat=len(weights)))
    if observed != optimum:
        raise DepthAuditError(
            f"finite encoding is suboptimal: actual={observed}, exhaustive={optimum}"
        )
    histogram: Counter[int] = Counter()
    for x, w in zip(values, weights, strict=True):
        histogram[x] += w
    return {
        "status": "PASS-exhaustive",
        "assignments": evaluations,
        "wasserstein": str(observed[0]),
        "cdf_error": str(observed[1]),
        "represented_histogram": tuple(sorted(histogram.items())),
        "omitted_support": tuple(x for x in atoms if x not in histogram),
    }


def audit_chart_encoding(
    chart: TeamChart, targets: Mapping[str, Support], *, enumeration_budget: int = 2_000_000
) -> dict[str, Any]:
    """Require all four offense and 24 formation-specific defense targets."""
    expected = {f"offense/{play}" for play in range(6, 10)}
    expected |= {f"defense/{play}/{formation}" for play in range(6, 10) for formation in "ABCDEF"}
    if set(targets) != expected:
        raise DepthAuditError("finite encoding target inventory must cover all 28 columns")
    offense_weights = Counter(
        10 * b + x + y
        for b, x, y in product((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5))
    )
    defense_weights = Counter(x + y for x, y in product((1, 1, 1, 2, 2, 3), (0, 0, 0, 0, 1, 2)))
    reports = {}
    for key in sorted(expected):
        parts = key.split("/")
        side, play = parts[:2]
        weights = offense_weights if side == "offense" else defense_weights
        rows = [
            row
            for row in getattr(chart, side)
            if row.play.value == int(play)
            and row.cell.kind is ResultKind.INTERCEPTION
            and (side == "offense" or row.defense.value == parts[2])
        ]
        if any(row.cell.variable is not None for row in rows):
            raise DepthAuditError("finite encoding cannot qualify variable locations")
        reports[key] = audit_slot_encoding(
            tuple(weights[row.roll] for row in rows),
            tuple(row.cell.yards for row in rows),
            targets[key],
            enumeration_budget=enumeration_budget,
        )
    qualified = all(r["status"] in {"dormant", "PASS-exhaustive"} for r in reports.values())
    return {
        "status": "PASS-exhaustive" if qualified else "UNVERIFIED-enumeration-budget",
        "columns": reports,
        "historical_fit": "UNVERIFIED",
    }
