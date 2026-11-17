"""Opt-in typed private opportunities, not historical formation observations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from itertools import product

from bowl_bound.models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    NormalizedCell,
    Play,
    Priority,
    Provenance,
    ResultKind,
    TeamChart,
)
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import format_cell, parse_cell

from .research_inputs import semantic_sha256

WEIGHTS = (12, 11, 9, 3, 1)
NUMERIC = frozenset({ResultKind.YARDS, ResultKind.NO_CHANGE})
EVENTS = frozenset({ResultKind.INCOMPLETE, ResultKind.QUARTERBACK_TRAPPED, ResultKind.INTERCEPTION})
MODEL_CONTRACT = {
    "origin": "authored-bb-typed-joint-opportunity-private-v2",
    "mass_denominator": 36,
    "weights": WEIGHTS,
    "opportunities": {"INC": 3, "QT": 3, "INT": 1},
    "roles": {
        "D": "INC/eligibleINT+6,7;-8,9;QTfixed",
        "E": "INC/eligibleINT-6,7;+8,9;QTfixed",
        "F": "QT+7,9;INC-6,8;INTfixed",
    },
    "protected": "A/B/C;run1-5;allnondefense;allpriority/OOB;allinactivewholecells",
    "domain": "active-normal/nonOOB/fixed-payload;variablewholecellsfixed-with-known-family-mass",
    "reference": "fixedA-samecall;uniform54-authored-diagnostic-not-historical",
    "objective": [
        "hard-domains/directions/numeric-support",
        "requested-family-L1",
        "complete-partition-L1",
        "original-formation-mutable-normal-numeric-mean",
        "semantic-edited-rows",
        "canonical-assignment-and-values",
    ],
    "encoder": "exact-adjacent-integers-exhaustive-no-seed",
    "int_support": "positive-modeled-baseline-or-bound-unrounded;zero/unknown-no-floor",
    "int_payload": (
        "samecallA-modeled-weighted-midpoints-leftclosed-rightopen;conditional-depthUNKNOWN"
    ),
    "source_fit": "UNVERIFIED",
    "terminal_scope": "declared-actual-controls-only;unclosed-massUNKNOWN",
}


def model_identity() -> dict[str, object]:
    """Return the separately named authored experiment and exact contract hash."""
    return {
        "origin": MODEL_CONTRACT["origin"],
        "sha256": _digest(MODEL_CONTRACT),
        "authored_experimental": True,
        "contract": json.loads(json.dumps(MODEL_CONTRACT)),
    }


class IntSupportState(str, Enum):
    POSITIVE_BASELINE = "positive-represented-model"
    POSITIVE_UNROUNDED = "positive-unrounded-model"
    MODELED_ZERO = "known-modeled-zero"
    UNKNOWN = "unknown"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha(value: str | None) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def classify_int_support(represented: int, unrounded: Fraction | int | None) -> IntSupportState:
    """Classify modeled support without treating a printed zero as source zero."""
    if type(represented) is not int or not 0 <= represented <= 36:
        raise ValueError("represented INT mass must be an integer within 0..36")
    if unrounded is not None and (
        type(unrounded) not in {int, Fraction} or not 0 <= unrounded <= 36
    ):
        raise ValueError("unrounded INT mass must be exact nonnegative mass within 0..36")
    if represented:
        if unrounded == 0:
            raise ValueError("positive represented INT contradicts a known zero modeled request")
        return IntSupportState.POSITIVE_BASELINE
    if unrounded is None:
        return IntSupportState.UNKNOWN
    return IntSupportState.POSITIVE_UNROUNDED if unrounded > 0 else IntSupportState.MODELED_ZERO


@dataclass(frozen=True)
class IntRequestEvidence:
    """Frozen modeled request; its expected receipt comes from a reviewed input.

    This record and a matching hash establish input consistency, not historical
    source qualification. Callers must freeze the expected hash independently of
    the candidate. No provider-completeness flag is inferred from this record.
    """

    baseline_sha256: str
    play: Play
    requested_mass: Fraction
    locations: tuple[tuple[int, int], ...]
    source_identity: str

    def __post_init__(self) -> None:
        if (
            not _sha(self.baseline_sha256)
            or not _sha(self.source_identity)
            or type(self.play) is not Play
        ):
            raise ValueError(
                "modeled INT request requires exact baseline/source identities and call"
            )
        if type(self.requested_mass) is not Fraction or not 0 <= self.requested_mass <= 36:
            raise ValueError("modeled INT request requires exact Fraction mass within 0..36")
        if type(self.locations) is not tuple or any(
            type(point) is not tuple
            or len(point) != 2
            or type(point[0]) is not int
            or type(point[1]) is not int
            or point[1] <= 0
            for point in self.locations
        ):
            raise ValueError(
                "modeled INT locations require immutable integer locations/positive support weights"
            )

    @property
    def receipt_sha256(self) -> str:
        return _digest(
            {
                "origin": "frozen-generation-model-request",
                "baseline": self.baseline_sha256,
                "play": self.play.value,
                "requested_mass": [self.requested_mass.numerator, self.requested_mass.denominator],
                "locations": self.locations,
                "source_identity": self.source_identity,
            }
        )


@dataclass(frozen=True)
class IntModelSupport:
    """A modeled support disposition, never a source-completeness certificate."""

    state: IntSupportState
    represented_mass: int
    unrounded_mass: Fraction | None
    location_support: tuple[tuple[int, int], ...]
    ancestry_sha256: str
    evidence_origin: str
    historical_source_status: str = "UNVERIFIED"
    unlocated_represented_mass: int = 0

    @property
    def allows_new_int(self) -> bool:
        return (
            self.state
            in {
                IntSupportState.POSITIVE_BASELINE,
                IntSupportState.POSITIVE_UNROUNDED,
            }
            and bool(self.location_support)
            and self.unlocated_represented_mass == 0
        )


def describe_int_support(
    chart: TeamChart,
    play: Play,
    *,
    evidence: IntRequestEvidence | None = None,
    approved_receipt_sha256: str | None = None,
) -> IntModelSupport:
    """Bind A's same-call modeled support and optional frozen unrounded request."""
    if type(play) is not Play or play.value < 6:
        raise ValueError("INT modeled support requires a real passing call6..9")
    baseline = semantic_sha256(chart)
    cells = tuple(
        row
        for row in chart.defense
        if row.defense is Defense.A
        and row.play is play
        and row.cell.kind is ResultKind.INTERCEPTION
        and row.cell.priority is Priority.NORMAL
        and not row.cell.out_of_bounds
    )
    represented = sum(WEIGHTS[row.roll - 1] for row in cells)
    locations = tuple(
        sorted(
            (row.cell.yards, WEIGHTS[row.roll - 1]) for row in cells if type(row.cell.yards) is int
        )
    )
    unlocated = sum(WEIGHTS[row.roll - 1] for row in cells if type(row.cell.yards) is not int)
    unrounded = None
    origin = "frozen-generated-baseline"
    ancestry = _digest(
        {
            "baseline": baseline,
            "play": play.value,
            "located_cells": [semantic_sha256(row) for row in cells],
        }
    )
    if evidence is not None:
        if type(evidence) is not IntRequestEvidence:
            raise ValueError("INT request evidence must use the frozen typed descriptor")
        if not _sha(approved_receipt_sha256) or evidence.receipt_sha256 != approved_receipt_sha256:
            raise ValueError("INT request receipt does not match independently approved input")
        if evidence.baseline_sha256 != baseline or evidence.play is not play:
            raise ValueError("INT request baseline/call does not match actual consumed chart")
        unrounded = evidence.requested_mass
        if evidence.locations:
            locations = evidence.locations
            unlocated = 0  # Explicit bound modeled payload recipe, not provider location inference.
        origin, ancestry = "frozen-generation-model-request", evidence.receipt_sha256
    elif approved_receipt_sha256 is not None:
        raise ValueError("INT request receipt supplied without matching evidence")
    state = classify_int_support(represented, unrounded)
    return IntModelSupport(
        state,
        represented,
        unrounded,
        locations,
        ancestry,
        origin,
        unlocated_represented_mass=unlocated,
    )


def _ordinary(cell: NormalizedCell) -> bool:
    return cell.priority is Priority.NORMAL and not cell.out_of_bounds and cell.kind in NUMERIC


def _facts(cell: NormalizedCell) -> tuple[object, ...]:
    return (
        cell.kind,
        cell.yards,
        cell.variable,
        cell.variable_multiplier,
        cell.priority,
        cell.out_of_bounds,
        cell.penalty,
        cell.chart_color,
    )


def _normal_mass(rows: tuple[DefensiveCell, ...], kind: ResultKind) -> int:
    return sum(
        WEIGHTS[row.roll - 1]
        for row in rows
        if row.cell.kind is kind
        and row.cell.priority is Priority.NORMAL
        and not row.cell.out_of_bounds
    )


def _midpoint_locations(
    selected: tuple[int, ...], support: tuple[tuple[int, int], ...]
) -> dict[int, int]:
    if not selected:
        return {}
    if not support:
        raise ValueError("new INT cells require frozen known modeled location support")
    points = sorted(support)
    support_mass, selected_mass = sum(w for _, w in points), sum(WEIGHTS[i] for i in selected)
    before = 0
    result = {}
    for i in selected:
        target = Fraction(2 * before + WEIGHTS[i], 2 * selected_mass) * support_mass
        cumulative = 0
        for location, weight in points:
            cumulative += weight
            if target < cumulative:
                result[i] = location
                break
        before += WEIGHTS[i]
    return result


def allocate_typed_column(
    rows: tuple[DefensiveCell, ...],
    requested: dict[ResultKind, Fraction],
    *,
    anchor: dict[ResultKind, int] | None = None,
    directions: dict[ResultKind, int] | None = None,
    int_locations: tuple[tuple[int, int], ...] = (),
) -> tuple[tuple[DefensiveCell, ...], dict[str, object]]:
    """Solve the bounded active families with every other whole cell fixed.

    This private experiment admits normal INC/QT/INT alternatives. Other families
    and priority/flag variants remain explicit fixed domains. Every assignment's
    payload and numeric encoding participates before mean/edit tie-breaking.
    Returned changed cells receive final derived ancestry at the model boundary.
    """
    if (
        type(rows) is not tuple
        or tuple(row.roll for row in rows) != (1, 2, 3, 4, 5)
        or len({(row.defense, row.play) for row in rows}) != 1
    ):
        raise ValueError("typed defense allocation requires five addressed rows1..5 of one column")
    if (
        not requested
        or not set(requested) <= EVENTS
        or any(type(value) not in {int, Fraction} or value < 0 for value in requested.values())
    ):
        raise ValueError(
            "typed experiment requires exact known requests for admitted active families"
        )
    kinds = tuple(sorted(requested, key=lambda kind: kind.value))
    wanted = tuple(Fraction(requested[kind]) for kind in kinds)
    anchors = {kind: _normal_mass(rows, kind) for kind in kinds} if anchor is None else anchor
    signs = dict.fromkeys(kinds, 0) if directions is None else directions
    if (
        set(anchors) != set(kinds)
        or set(signs) != set(kinds)
        or any(type(value) is not int or not 0 <= value <= 36 for value in anchors.values())
        or any(type(value) is not int or value not in (-1, 0, 1) for value in signs.values())
    ):
        raise ValueError("typed directions require complete integer anchor masses and signs")
    mutable = tuple(
        i
        for i, row in enumerate(rows)
        if _ordinary(row.cell)
        or (
            row.cell.priority is Priority.NORMAL
            and not row.cell.out_of_bounds
            and row.cell.variable is None
            and row.cell.kind in kinds
        )
    )
    fixed_mass = tuple(
        sum(
            WEIGHTS[i]
            for i, row in enumerate(rows)
            if i not in mutable
            and row.cell.kind is kind
            and row.cell.priority is Priority.NORMAL
            and not row.cell.out_of_bounds
        )
        for kind in kinds
    )
    original_numeric = tuple(i for i in mutable if _ordinary(rows[i].cell))
    report: dict[str, object] = {
        "families": tuple(kind.value for kind in kinds),
        "requested": tuple(str(value) for value in wanted),
        "physical_denominator": 36,
        "mutable_rows": tuple(i + 1 for i in mutable),
        "fixed_whole_rows": tuple(i + 1 for i in range(5) if i not in mutable),
        "fixed_normal_family_mass": {
            kind.value: mass for kind, mass in zip(kinds, fixed_mass, strict=True)
        },
        "target_population": "normal/nonOOB-family-mass-including-fixed-whole-cells",
        "joint_exact_feasible": False,
        "physical_exact_feasible": False,
    }
    if not original_numeric:
        return rows, {**report, "status": "undefined-numeric-support"}
    available = sum(WEIGHTS[i] for i in mutable)
    ordinary_target = available + sum(fixed_mass) - sum(wanted)
    if ordinary_target < 0:
        return rows, {**report, "status": "infeasible-budget"}
    mean_target = Fraction(
        sum(WEIGHTS[i] * (rows[i].cell.yards or 0) for i in original_numeric),
        sum(WEIGHTS[i] for i in original_numeric),
    )
    low = mean_target.numerator // mean_target.denominator
    numeric_values = (low,) if mean_target.denominator == 1 else (low, low + 1)
    report["original_formation_numeric_mean"] = str(mean_target)
    cache: dict[tuple[int, str], NormalizedCell] = {}

    def encoded(i: int, token: str) -> NormalizedCell:
        key = (i, token)
        if key not in cache:
            old = rows[i].cell
            if old.provenance is None:
                raise ValueError("typed experiment requires complete baseline ancestry")
            color = chart_color_for_csv_token(token)
            temporary = replace(
                old.provenance, original_text=token, rgb_color=CELL_LEGEND[color].rgb_color
            )
            cell = parse_cell(token, temporary)
            cache[key] = old if _facts(cell) == _facts(old) else cell
        return cache[key]

    attainable, admitted = set(), set()
    best = None
    scores = {}
    for assignment in product(range(len(kinds) + 1), repeat=len(mutable)):
        numeric_positions = tuple(
            i for i, code in zip(mutable, assignment, strict=True) if code == 0
        )
        if not numeric_positions:
            continue
        mass = tuple(
            fixed_mass[category - 1]
            + sum(
                WEIGHTS[i] for i, code in zip(mutable, assignment, strict=True) if code == category
            )
            for category in range(1, len(kinds) + 1)
        )
        attainable.add(mass)
        if any(
            signs[kind] and (value - anchors[kind]) * signs[kind] <= 0
            for kind, value in zip(kinds, mass, strict=True)
        ):
            continue
        admitted.add(mass)
        family_error = sum(
            (abs(value - target) for value, target in zip(mass, wanted, strict=True)), Fraction()
        )
        partition_error = family_error + abs(
            available + sum(fixed_mass) - sum(mass) - ordinary_target
        )
        scores[mass] = (family_error, partition_error)
        selected_int = tuple(
            i
            for i, code in zip(mutable, assignment, strict=True)
            if code and kinds[code - 1] is ResultKind.INTERCEPTION
        )
        locations = _midpoint_locations(selected_int, int_locations)
        for values in product(numeric_values, repeat=len(numeric_positions)):
            actual_mean = Fraction(
                sum(WEIGHTS[i] * value for i, value in zip(numeric_positions, values, strict=True)),
                sum(WEIGHTS[i] for i in numeric_positions),
            )
            cells = list(row.cell for row in rows)
            normal_values = dict(zip(numeric_positions, values, strict=True))
            for i, code in zip(mutable, assignment, strict=True):
                if code == 0:
                    token = str(normal_values[i]) if normal_values[i] else ""
                else:
                    kind = kinds[code - 1]
                    token = (
                        "BLACK"
                        if kind is ResultKind.INCOMPLETE
                        else "QT"
                        if kind is ResultKind.QUARTERBACK_TRAPPED
                        else f"INT {locations[i]}"
                    )
                cells[i] = encoded(i, token)
            changed = sum(
                _facts(cell) != _facts(row.cell) for row, cell in zip(rows, cells, strict=True)
            )
            objective = (
                family_error,
                partition_error,
                abs(actual_mean - mean_target),
                changed,
                assignment,
                values,
            )
            if best is None or objective < best[0]:
                best = objective, mass, tuple(cells)
    report["attainable"] = tuple(sorted(attainable))
    report["admitted_after_directions"] = tuple(sorted(admitted))
    report["physical_exact_feasible"] = wanted in attainable
    report["joint_exact_feasible"] = wanted in admitted
    if best is None:
        return rows, {**report, "status": "infeasible-direction"}
    objective, represented, cells = best
    minimum = min(score[0] for score in scores.values())
    first = tuple(sorted(mass for mass, score in scores.items() if score[0] == minimum))
    second = min(scores[mass][1] for mass in first)
    report.update(
        status="represented",
        represented=represented,
        requested_family_error=str(objective[0]),
        complete_partition_error=str(objective[1]),
        numeric_mean_error=str(objective[2]),
        changed_rows=objective[3],
        requested_family_minima=first,
        partition_frontier=tuple(mass for mass in first if scores[mass][1] == second),
    )
    return tuple(replace(row, cell=cell) for row, cell in zip(rows, cells, strict=True)), report


def apply_typed_event_model(
    chart: TeamChart,
    *,
    int_evidence: dict[Play, tuple[IntRequestEvidence, str]] | None = None,
) -> tuple[TeamChart, dict[str, object]]:
    """Apply the frozen private role matrix to a detached generated baseline.

    No historical formation exposures or conditional interception depths are
    inferred. Unsupported/saturated columns remain unchanged with their reason.
    Derived provenance names this model and keeps exact baseline cell ancestry.
    """
    if type(chart) is not TeamChart:
        raise ValueError("typed experiment requires one complete TeamChart baseline")
    original = semantic_sha256(chart)
    baseline = deepcopy(chart)
    supplied = deepcopy(int_evidence or {})
    if any(type(play) is not Play or play.value < 6 for play in supplied):
        raise ValueError("modeled INT evidence keys must be real passing calls6..9")
    identity = model_identity()
    cells = {(row.defense, row.play, row.roll): row for row in baseline.defense}
    reports, support_reports, ancestry = {}, {}, {}
    for play in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
        proof = supplied.get(play)
        if proof is not None and (type(proof) is not tuple or len(proof) != 2):
            raise ValueError("modeled INT evidence requires descriptor/approved-receipt pairs")
        support = describe_int_support(
            baseline,
            play,
            evidence=proof[0] if proof else None,
            approved_receipt_sha256=proof[1] if proof else None,
        )
        support_reports[str(play.value)] = {
            "state": support.state.value,
            "represented_mass": support.represented_mass,
            "unrounded_mass": str(support.unrounded_mass)
            if support.unrounded_mass is not None
            else None,
            "location_support": support.location_support,
            "unlocated_represented_mass": support.unlocated_represented_mass,
            "support_units": "modeled-physical-row-mass-not-historical-observations",
            "ancestry_sha256": support.ancestry_sha256,
            "evidence_origin": support.evidence_origin,
            "source_status": support.historical_source_status,
            "conditional_depth": "UNKNOWN",
        }
        a_rows = tuple(cells[Defense.A, play, roll] for roll in range(1, 6))
        a_inc = _normal_mass(a_rows, ResultKind.INCOMPLETE)
        a_qt = _normal_mass(a_rows, ResultKind.QUARTERBACK_TRAPPED)
        for formation in (Defense.D, Defense.E, Defense.F):
            rows = tuple(cells[formation, play, roll] for roll in range(1, 6))
            if formation is Defense.F:
                kind = (
                    ResultKind.QUARTERBACK_TRAPPED
                    if play in (Play.SEVEN, Play.NINE)
                    else ResultKind.INCOMPLETE
                )
                sign = 1 if kind is ResultKind.QUARTERBACK_TRAPPED else -1
                anchor = {kind: a_qt if sign == 1 else a_inc}
                requested = {kind: Fraction(anchor[kind] + sign * 3)}
                directions = {kind: sign}
            else:
                sign = 1 if (formation is Defense.D) == (play in (Play.SIX, Play.SEVEN)) else -1
                requested = {ResultKind.INCOMPLETE: Fraction(a_inc + sign * 3)}
                anchor = {ResultKind.INCOMPLETE: a_inc}
                directions = {ResultKind.INCOMPLETE: sign}
                if support.allows_new_int:
                    base_int = (
                        support.unrounded_mass
                        if support.unrounded_mass is not None
                        else Fraction(support.represented_mass)
                    )
                    requested[ResultKind.INTERCEPTION] = base_int + sign
                    anchor[ResultKind.INTERCEPTION] = support.represented_mass
                    directions[ResultKind.INTERCEPTION] = sign
            key = f"{formation.value}/{play.value}"
            if any(value < 0 for value in requested.values()):
                reports[key] = {
                    "status": "saturated-negative-request",
                    "requested": {kind.value: str(value) for kind, value in requested.items()},
                    "changed": False,
                }
                continue
            selected, report = allocate_typed_column(
                rows,
                requested,
                anchor=anchor,
                directions=directions,
                int_locations=support.location_support,
            )
            report["int_disposition"] = (
                "active-modeled-opportunity"
                if ResultKind.INTERCEPTION in requested
                else "fixed-no-new-opportunity"
            )
            report["int_support_state"] = support.state.value
            report["anchor_masses"] = {kind.value: value for kind, value in anchor.items()}
            report["strict_direction"] = {kind.value: value for kind, value in directions.items()}
            report["conditional_terminal_status"] = "UNVERIFIED"
            recipe = {
                "model_sha256": identity["sha256"],
                "baseline_sha256": original,
                "coordinate": key,
                "int_support_sha256": support.ancestry_sha256,
                "allocation": report,
                "selected_tokens": tuple(format_cell(row.cell) for row in selected),
                "baseline_cells": tuple(semantic_sha256(row) for row in rows),
            }
            recipe_sha = _digest(recipe)
            ancestry[recipe_sha] = recipe
            changed = []
            for old, new in zip(rows, selected, strict=True):
                if _facts(old.cell) == _facts(new.cell):
                    continue
                token = format_cell(new.cell)
                provenance = Provenance(
                    source_sha256=recipe_sha,
                    filename="authored-bb-typed-joint-opportunity-private-v2.json",
                    page=1,
                    bounding_box=BoundingBox(play.value, new.roll, play.value + 1, new.roll + 1),
                    original_text=token,
                    rgb_color=CELL_LEGEND[chart_color_for_csv_token(token)].rgb_color,
                )
                cells[formation, play, new.roll] = replace(
                    new, cell=replace(new.cell, provenance=provenance)
                )
                changed.append(new.roll)
            reports[key] = {
                **report,
                "changed_rows": tuple(changed),
                "derived_recipe_sha256": recipe_sha,
            }
    candidate = replace(
        baseline, defense=tuple(cells[row.defense, row.play, row.roll] for row in baseline.defense)
    )
    if semantic_sha256(chart) != original:
        raise ValueError("baseline input changed while applying typed experiment")
    return candidate, {
        "model_identity": identity,
        "baseline_sha256": original,
        "output_sha256": semantic_sha256(candidate),
        "allocations": reports,
        "int_support": support_reports,
        "derived_ancestry": ancestry,
        "source_fit": "UNVERIFIED",
        "reference_exposure": "uniform54-authored-diagnostic-not-historical",
        "terminal_scope": "declared-controls-only;remaining-massUNKNOWN",
    }
