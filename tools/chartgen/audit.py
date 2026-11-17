"""Exhaustive physical probability audit through the engine priority resolver."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import Any

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
)
from bowl_bound.models import Defense, NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.normalization import chart_color_for_rgb
from bowl_bound.resolution import ChartResolutionError, resolve_cells
from bowl_bound.team_csv import (
    LOCAL_PLACEHOLDER_POWER_RATING,
    TeamFileMetadata,
    TeamFormatError,
    provenance_to_csv,
    team_from_files,
    team_to_files,
)

_VARIABLES = {kind for kind in ResultKind if kind.name.startswith("VARIABLE_")}
_DISTANCES = _VARIABLES | {ResultKind.YARDS, ResultKind.NO_CHANGE}
_RETURNS = {"punt_return", "kickoff_return", "interception_return"}


def _normalized(values: Mapping[int, float]) -> dict[int, float]:
    if any(
        type(yards) is not int
        or type(mass) not in {int, float}
        or not math.isfinite(mass)
        or mass < 0
        for yards, mass in values.items()
    ):
        raise ValueError("distribution needs integer yardage and finite nonnegative mass")
    total = sum(values.values())
    if not math.isfinite(total):
        raise ValueError("distribution total mass must be finite")
    return {yards: mass / total for yards, mass in values.items() if mass > 0} if total else {}


def compare_distributions(
    source: Mapping[int, float],
    encoded: Mapping[int, float],
) -> dict[str, Any]:
    """Measure complete weighted CDF/support loss without declaring a fit tolerance.

    Inputs are evidence masses, not invented independent sample counts. Scoring
    and field-position effects belong to engine simulations, not this histogram.
    """
    left, right = _normalized(source), _normalized(encoded)
    report: dict[str, Any] = {
        "state": "measured" if left and right else "unidentifiable",
        "source_mass": sum(source.values()),
        "encoded_mass": sum(encoded.values()),
        "source_mean": sum(yards * mass for yards, mass in left.items()) if left else None,
        "encoded_mean": sum(yards * mass for yards, mass in right.items()) if right else None,
        "source_min": min(left) if left else None,
        "source_max": max(left) if left else None,
        "encoded_min": min(right) if right else None,
        "encoded_max": max(right) if right else None,
        "missing_support": sorted(left.keys() - right.keys()),
        "introduced_support": sorted(right.keys() - left.keys()),
        "max_cdf_error": None,
        "wasserstein_yards": None,
        "missing_lower_tail_mass": None,
        "missing_upper_tail_mass": None,
        "scope": "diagnostic only; no tolerance or historical fit is inferred",
    }
    if not left or not right:
        return report
    cdf_left = cdf_right = error = distance = 0.0
    previous = None
    for point in sorted(left.keys() | right.keys()):
        if previous is not None:
            distance += abs(cdf_left - cdf_right) * (point - previous)
        cdf_left += left.get(point, 0)
        cdf_right += right.get(point, 0)
        error = max(error, abs(cdf_left - cdf_right))
        previous = point
    report.update(
        {
            "max_cdf_error": error,
            "wasserstein_yards": distance,
            "missing_lower_tail_mass": sum(
                mass for yards, mass in left.items() if yards < min(right)
            ),
            "missing_upper_tail_mass": sum(
                mass for yards, mass in left.items() if yards > max(right)
            ),
        }
    )
    return report


@dataclass(frozen=True)
class ColumnEvidence:
    """Exact pre-integration evidence masses for a declared numeric projection."""

    section: str
    column: str
    formation: str | None
    numeric_gains: Mapping[int, float]
    scope: str
    locations: Mapping[str, Mapping[int, float]] = field(default_factory=dict)
    kind_probabilities: Mapping[str, float] = field(default_factory=dict)


def compare_column_distributions(
    chart_audit: Mapping[str, Any], evidence: Sequence[ColumnEvidence]
) -> list[dict[str, Any]]:
    """Compare raw physical numeric cells with exact source/model distributions.

    B/QR/QT, scoring and other conditional procedures are deliberately outside
    this projection. Their physical mass is retained, never treated as zero gain.
    This diagnostic does not declare a historical fit or a terminal distribution.
    """
    columns = {}
    for column in chart_audit["columns"]:
        address = column["section"], column["column"], column["formation"]
        if address in columns:
            raise ValueError("duplicate encoded column address")
        columns[address] = column
    output, seen = [], set()
    for source in evidence:
        address = source.section, source.column, source.formation
        if address in seen:
            raise ValueError("duplicate source column address")
        seen.add(address)
        if address not in columns:
            raise ValueError("source column is missing from the encoded audit")
        encoded = columns[address]
        numeric = {int(yards): mass for yards, mass in encoded["numeric_gains"].items()}
        comparison = compare_distributions(source.numeric_gains, numeric)
        locations = {}
        for kind, masses in source.locations.items():
            target = encoded.get("locations", {}).get(kind, {})
            locations[kind] = {
                "source_masses": {str(yards): mass for yards, mass in sorted(masses.items())},
                "encoded_masses": target,
                "comparison": compare_distributions(
                    masses, {int(yards): mass for yards, mass in target.items()}
                ),
            }
        rates = {}
        for kind, probability in source.kind_probabilities.items():
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("source kind probability must be finite within [0, 1]")
            achieved = encoded.get("kinds", {}).get(kind, 0) / encoded["physical_mass"]
            rates[kind] = {
                "requested": probability,
                "encoded": achieved,
                "error": achieved - probability,
            }
        output.append(
            {
                "section": source.section,
                "column": source.column,
                "formation": source.formation,
                "source_numeric_masses": {
                    str(yards): mass for yards, mass in sorted(source.numeric_gains.items())
                },
                "encoded_numeric_masses": encoded["numeric_gains"],
                "encoded_non_numeric_mass": encoded["physical_mass"] - sum(numeric.values()),
                "physical_mass": encoded["physical_mass"],
                "distribution": comparison,
                "location_distributions": locations,
                "kind_probabilities": rates,
                "scope": source.scope,
                "limitation": (
                    "conditional raw numeric projection; pending mechanisms are not zeroes; "
                    "not a terminal engine distribution or historical-fit gate"
                ),
            }
        )
    return output


def _placement_issue(section: str, column: str, cell: NormalizedCell) -> str | None:
    if (
        section == "offense"
        and column != "5"
        and cell.kind in {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS}
    ):
        return "SOP/BLP require the called Option/Play 5 column"
    if section == "special_teams":
        allowed = _DISTANCES | {ResultKind.PENALTY}
        if column in _RETURNS:
            allowed |= {ResultKind.FUMBLE, ResultKind.TOUCHDOWN}
        else:
            allowed |= {ResultKind.FUMBLE, ResultKind.BLOCKED_KICK}
            if column == "punt":
                allowed |= {ResultKind.FIELD_GOAL_REFERENCE, ResultKind.KICKOFF_REFERENCE}
            elif column == "field_goal":
                allowed |= {ResultKind.NO_GOOD_FIELD_GOAL}
        return None if cell.kind in allowed else "kind has no supported procedure in this column"
    if section == "supplemental" and cell.kind in {
        ResultKind.SPRINT_OUT_PASS,
        ResultKind.BOOTLEG_PASS,
    }:
        return "Option is resolved before the supplemental procedure, not inside it"
    blank = NormalizedCell(ResultKind.NO_CHANGE, cell.provenance)
    try:
        resolve_cells(blank, cell) if section == "defense" else resolve_cells(cell, blank)
    except ChartResolutionError:
        return "kind is unsupported by the ordinary engine priority resolver"
    return None


def _inventory(
    section: str,
    column: str,
    formation: str | None,
    cells: Sequence[tuple[int, NormalizedCell]],
    weights: Mapping[int, int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    kinds: Counter[str] = Counter()
    colors: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    semantics: Counter[str] = Counter()
    gains: Counter[int] = Counter()
    locations: dict[str, Counter[int]] = defaultdict(Counter)
    issues = []
    oob_mass = 0
    for row, cell in cells:
        mass = weights[row]
        kinds[cell.kind.value] += mass
        priorities[cell.priority.value] += mass
        color = chart_color_for_rgb(cell.provenance.rgb_color)
        colors[color.value if color is not None else "unrecognized"] += mass
        semantics[
            f"{cell.kind.value}/{cell.priority.value}/{color.value if color else 'unrecognized'}"
        ] += mass
        if cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}:
            gains[cell.yards if cell.yards is not None else 0] += mass
        elif (
            cell.kind in {ResultKind.FUMBLE, ResultKind.INTERCEPTION, ResultKind.BLOCKED_KICK}
            and cell.yards is not None
        ):
            locations[cell.kind.value][cell.yards] += mass
        oob_mass += mass if cell.out_of_bounds else 0
        reason = _placement_issue(section, column, cell)
        if color is None:
            reason = "unrecognized provenance color"
        elif cell.chart_color is not None and cell.chart_color is not color:
            reason = "normalized color disagrees with provenance"
        if reason:
            issues.append(
                {
                    "section": section,
                    "column": column,
                    "formation": formation,
                    "row": row,
                    "kind": cell.kind.value,
                    "reason": reason,
                }
            )
    return {
        "section": section,
        "column": column,
        "formation": formation,
        "physical_mass": sum(weights[row] for row, _ in cells),
        "kinds": dict(sorted(kinds.items())),
        "colors": dict(sorted(colors.items())),
        "priorities": dict(sorted(priorities.items())),
        "semantic_masses": dict(sorted(semantics.items())),
        "out_of_bounds_mass": oob_mass,
        "numeric_gains": {str(yards): mass for yards, mass in sorted(gains.items())},
        "locations": {
            kind: {str(yards): mass for yards, mass in sorted(values.items())}
            for kind, values in sorted(locations.items())
        },
    }, issues


def audit_chart(chart: TeamChart) -> dict[str, Any]:
    """Audit every play/formation and weighted physical pair without reroll guesses.

    Pending B/QR/QT/Option/penalty/recovery are reported as pending mechanisms.
    Complete-game batches validate their eventual engine-owned resolution.
    """
    offense = {(record.play, record.roll): record.cell for record in chart.offense}
    defense = {(record.defense, record.play, record.roll): record.cell for record in chart.defense}
    # Independent of generation's quantization helpers: use the engine's physical
    # roll objects, including duplicate die faces, as the probability authority.
    off_weights = Counter(
        OffensiveRoll(*faces).total
        for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    def_weights = Counter(DefensiveRoll(*faces).total for faces in product(RED_FACES, GREEN_FACES))
    groups: dict[tuple[str, str, str | None], list[tuple[int, NormalizedCell]]] = defaultdict(list)
    for record in chart.offense:
        groups["offense", str(record.play.value), None].append((record.roll, record.cell))
    for record in chart.defense:
        groups["defense", str(record.play.value), record.defense.value].append(
            (record.roll, record.cell)
        )
    for section, records in (
        ("supplemental", chart.supplemental),
        ("special_teams", chart.special_teams),
    ):
        for record in records:
            groups[section, record.column.value, None].append((record.roll, record.cell))
    columns, issues = [], []
    # Use the actual codec's measured-fill/zero/CMYK policies, not a new color
    # interpreter. A structurally typed cell can still carry an incorrect fill.
    provenance = chart.offense[0].cell.provenance
    assert provenance is not None
    metadata = TeamFileMetadata(
        LOCAL_PLACEHOLDER_POWER_RATING, (), "Independent audit", provenance.source_sha256, (), True
    )
    try:
        team_from_files(team_to_files(chart, metadata), provenance_to_csv(chart, metadata))
    except TeamFormatError as error:
        issues.append(
            {
                "section": "bundle",
                "column": "codec",
                "formation": None,
                "row": None,
                "kind": None,
                "reason": str(error),
            }
        )
    for (section, column, formation), cells in sorted(groups.items()):
        inventory, failures = _inventory(
            section, column, formation, cells, def_weights if section == "defense" else off_weights
        )
        columns.append(inventory)
        issues.extend(failures)
    pairs = []
    for play in Play:
        for formation in Defense:
            masses: Counter[str] = Counter()
            numeric: Counter[int] = Counter()
            pending_mass = 0
            for off_roll, off_mass in off_weights.items():
                for def_roll, def_mass in def_weights.items():
                    try:
                        result = resolve_cells(
                            offense[play, off_roll], defense[formation, play, def_roll]
                        )
                    except ChartResolutionError:
                        masses["invalid:priority"] += off_mass * def_mass
                        continue
                    label = result.kind.value if result.kind is not None else result.operation.value
                    masses[("pending:" if result.pending else "final:") + label] += (
                        off_mass * def_mass
                    )
                    if result.pending:
                        pending_mass += off_mass * def_mass
                    elif (
                        result.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}
                        and result.yards is not None
                    ):
                        numeric[result.yards] += off_mass * def_mass
            pairs.append(
                {
                    "play": play.value,
                    "formation": formation.value,
                    "outcome_masses": dict(masses),
                    "final_numeric_gains": {
                        str(yards): mass for yards, mass in sorted(numeric.items())
                    },
                    "pending_mass": pending_mass,
                }
            )
    return {
        "schema_version": 2,
        "physical_offensive_combinations": sum(off_weights.values()),
        "physical_defensive_combinations": sum(def_weights.values()),
        "play_formation_pairs": len(pairs),
        "pairs": pairs,
        "columns": columns,
        "structural_ready": not issues,
        "semantic_issues": issues,
        "recovery": {"mass": sum(off_weights[row] for row in chart.recovery_range), "total": 216},
        "pat": {
            "made_mass": sum(off_weights[row.roll] for row in chart.pat_outcomes if row.good),
            "total": 216,
        },
        "scope": "engine priority outcomes; pending branches are not terminal probability claims",
    }
