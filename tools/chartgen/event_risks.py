"""Opt-in authored defensive event opportunities; not historical formation rates.

The joint allocator uses integer physical mass and exact rational numeric means.
It neither fits source data nor changes the established numeric-only policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from itertools import product

from bowl_bound.models import Defense, NormalizedCell, Play, Priority, ResultKind, TeamChart
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import parse_cell

WEIGHTS = (12, 11, 9, 3, 1)
KINDS = (ResultKind.YARDS, ResultKind.INCOMPLETE, ResultKind.QUARTERBACK_TRAPPED)
MODEL_CONTRACT = {
    "origin": "authored-bb-joint-event-private-v1",
    "opportunity_numerator": 3,
    "denominator": 36,
    "roles": {"D": "INC+6,7;-8,9", "E": "INC-6,7;+8,9", "F": "QT+7,9;INC-6,8"},
    "reference": "uniform-passes6-9-formationsA-F-midfield-first10-both-seats",
    "objective": ["joint-L1", "exact-conditional-numeric-mean-error", "changed-rows", "row-tuple"],
    "encoder": "exact-adjacent-integers-exhaustive-lex-v1-no-random-seed",
    "protected": "A,B,C;INT;nonordinary;priority;OOB;all-nondefense",
    "terminal_scope": "ordinary-closed-controls-only;other-mass-UNKNOWN",
}


def model_identity() -> dict[str, object]:
    """Return a separately versioned, deterministic experimental authority."""
    encoded = json.dumps(MODEL_CONTRACT, sort_keys=True, separators=(",", ":")).encode()
    return {
        "origin": MODEL_CONTRACT["origin"],
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "authored_experimental": True,
        "contract": json.loads(encoded),
    }


def _numeric(cell: NormalizedCell) -> bool:
    return cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}


def _mutable(cell: NormalizedCell) -> bool:
    return (
        cell.priority is Priority.NORMAL
        and not cell.out_of_bounds
        and (_numeric(cell) or cell.kind in KINDS[1:])
    )


def _class(cell: NormalizedCell) -> int:
    return 0 if _numeric(cell) else KINDS.index(cell.kind)


@dataclass(frozen=True)
class JointAllocation:
    """Exact requested/represented mass and independently visible finite error."""

    requested: tuple[int, int]
    represented: tuple[int, int] | None
    assignments: tuple[int, ...] | None
    numeric_yards: tuple[int | None, ...] | None
    attainable: tuple[tuple[int, int], ...]
    mass_error: int | None
    mean_error: str | None
    status: str


def joint_allocate(
    weights: tuple[int, ...],
    original_classes: tuple[int, ...],
    original_yards: tuple[int, ...],
    requested: tuple[int, int],
    *,
    baseline: tuple[int, int],
    direction: tuple[int, int] = (0, 0),
) -> JointAllocation:
    """Enumerate disjoint row assignments, preserving existing numeric support.

    No category independently rounds into a row already used by another category.
    The numeric conditional mean is defined only by original numeric rows.
    """
    if (
        not weights
        or len(weights) != len(original_classes)
        or len(weights) != len(original_yards)
        or any(type(w) is not int or w <= 0 for w in weights)
        or any(c not in (0, 1, 2) for c in original_classes)
        or any(type(v) is not int for v in original_yards)
        or any(type(v) is not int or v < 0 for v in (*requested, *baseline))
        or any(v not in (-1, 0, 1) for v in direction)
    ):
        raise ValueError(
            "joint allocation requires positive integer weights and typed class/mass facts"
        )
    numeric_mass = sum(w for w, c in zip(weights, original_classes, strict=True) if c == 0)
    if not numeric_mass:
        return JointAllocation(
            requested, None, None, None, (), None, None, "undefined-numeric-support"
        )
    target_mean = Fraction(
        sum(
            w * y
            for w, c, y in zip(weights, original_classes, original_yards, strict=True)
            if c == 0
        ),
        numeric_mass,
    )
    lower = target_mean.numerator // target_mean.denominator
    choices = (lower,) if target_mean.denominator == 1 else (lower, lower + 1)
    attainable = set()
    best = None
    for assignment in product(range(3), repeat=len(weights)):
        mass = tuple(
            sum(w for w, c in zip(weights, assignment, strict=True) if c == category)
            for category in (1, 2)
        )
        if 0 not in assignment:
            continue
        attainable.add(mass)
        if any(
            d and (new - old) * d <= 0
            for new, old, d in zip(mass, baseline, direction, strict=True)
        ):
            continue
        positions = tuple(i for i, c in enumerate(assignment) if c == 0)
        for values in product(choices, repeat=len(positions)):
            yards: list[int | None] = [None] * len(weights)
            for i, value in zip(positions, values, strict=True):
                yards[i] = value
            actual_mean = Fraction(
                sum(weights[i] * int(yards[i]) for i in positions),
                sum(weights[i] for i in positions),
            )
            error = abs(actual_mean - target_mean)
            changed = sum(
                a != b or (a == 0 and yards[i] != original_yards[i])
                for i, (a, b) in enumerate(zip(assignment, original_classes, strict=True))
            )
            objective = (
                sum(abs(a - b) for a, b in zip(mass, requested, strict=True)),
                error,
                changed,
                assignment,
                values,
            )
            if best is None or objective < best[0]:
                best = (objective, mass, assignment, tuple(yards))
    if best is None:
        return JointAllocation(
            requested,
            None,
            None,
            None,
            tuple(sorted(attainable)),
            None,
            None,
            "infeasible-direction",
        )
    objective, mass, assignment, yards = best
    return JointAllocation(
        requested,
        mass,
        assignment,
        yards,
        tuple(sorted(attainable)),
        objective[0],
        str(objective[1]),
        "represented",
    )


def _request(formation: Defense, play: Play) -> tuple[int, int]:
    if formation in {Defense.D, Defense.E}:
        sign = 1 if play.value in (6, 7) else -1
        return ((sign if formation is Defense.D else -sign) * 3, 0)
    if formation is Defense.F:
        return (0, 3) if play.value in (7, 9) else (-3, 0)
    return (0, 0)


def _encode(old: NormalizedCell, category: int, yards: int | None) -> NormalizedCell:
    if category == _class(old) and (category != 0 or (old.yards or 0) == yards):
        return old
    token = str(yards) if category == 0 else ("BLACK" if category == 1 else "QT")
    color = chart_color_for_csv_token(token)
    if old.provenance is None:
        raise ValueError("experimental chart changes require original provenance")
    evidence = replace(old.provenance, original_text=token, rgb_color=CELL_LEGEND[color].rgb_color)
    return parse_cell(token, evidence)


def apply_event_model(chart: TeamChart) -> tuple[TeamChart, dict[str, object]]:
    """Create a private candidate with joint ordinary event roles and full diagnostics."""
    original = {(r.defense, r.play, r.roll): r for r in chart.defense}
    replacements = {}
    reports = []
    for formation in (Defense.D, Defense.E, Defense.F):
        for play in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
            rows = [original[formation, play, i] for i in range(1, 6)]
            mutable = [i for i, r in enumerate(rows) if _mutable(r.cell)]
            anchor = [original[Defense.A, play, i].cell for i in range(1, 6)]
            baseline = tuple(
                sum(w for w, c in zip(WEIGHTS, anchor, strict=True) if c.kind is kind)
                for kind in KINDS[1:]
            )
            delta = _request(formation, play)
            requested = tuple(max(0, a + d) for a, d in zip(baseline, delta, strict=True))
            saturated = tuple(d < 0 and a == 0 for a, d in zip(baseline, delta, strict=True))
            fixed = tuple(
                sum(
                    WEIGHTS[i]
                    for i, r in enumerate(rows)
                    if i not in mutable and r.cell.kind is kind
                )
                for kind in KINDS[1:]
            )
            desired = tuple(max(0, x - y) for x, y in zip(requested, fixed, strict=True))
            direction = tuple(
                0 if not d or s else (1 if d > 0 else -1)
                for d, s in zip(delta, saturated, strict=True)
            )
            allocation = (
                joint_allocate(
                    tuple(WEIGHTS[i] for i in mutable),
                    tuple(_class(rows[i].cell) for i in mutable),
                    tuple(rows[i].cell.yards or 0 for i in mutable),
                    desired,
                    baseline=tuple(x - y for x, y in zip(baseline, fixed, strict=True)),
                    direction=direction,
                )
                if mutable
                else JointAllocation(desired, None, None, None, (), None, None, "no-mutable-rows")
            )
            if allocation.assignments is not None:
                for i, category, yards in zip(
                    mutable, allocation.assignments, allocation.numeric_yards, strict=True
                ):
                    row = rows[i]
                    replacements[formation, play, row.roll] = replace(
                        row, cell=_encode(row.cell, category, yards)
                    )
            report = asdict(allocation)
            report.update(
                formation=formation.value,
                play=play.value,
                baseline=baseline,
                requested_total=requested,
                fixed=fixed,
                saturated=saturated,
                represented_total=None
                if allocation.represented is None
                else tuple(x + y for x, y in zip(allocation.represented, fixed, strict=True)),
            )
            reports.append(report)
    candidate = replace(
        chart,
        defense=tuple(replacements.get((r.defense, r.play, r.roll), r) for r in chart.defense),
    )
    return candidate, {
        "model_identity": model_identity(),
        "allocations": reports,
        "historical_formation_exposure": "UNKNOWN",
        "historical_fit": "UNVERIFIED",
        "unsupported_terminal_mass": "UNKNOWN",
    }
