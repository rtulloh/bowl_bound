"""Exact chart/primary benchmark measurements, without a terminal-fit claim.

The engine is the primary-resolution subject. A separately frozen independent
Priority observer may check it. No source family inference, chart fitting or
pending-branch renormalization is performed here.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict
from enum import Enum
from fractions import Fraction
from typing import Any

from bowl_bound.models import Defense, NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.resolution import resolve_cells
from bowl_bound.team_csv import format_cell

from .reference_inventory import physical_weights


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _cell_facts(cell: NormalizedCell) -> dict[str, Any]:
    result = asdict(cell)
    result.pop("provenance")
    result.pop("chart_color")
    return _plain(result)


def _counter(counter: Counter) -> dict:
    return dict(sorted(counter.items()))


def table_measures(chart: TeamChart) -> dict[str, Any]:
    """Measure every real chart procedure; a location payload is not a gain."""
    offense_weights, defense_weights = physical_weights()
    grouped = defaultdict(list)
    count = 0
    for table in ("offense", "supplemental", "defense", "special_teams"):
        for row in getattr(chart, table):
            if table == "offense":
                key = f"offense/{row.play.value}"
            elif table == "defense":
                key = f"defense/{row.defense.value}/{row.play.value}"
            else:
                key = f"{table}/{row.column.value}"
            weight = (defense_weights if table == "defense" else offense_weights)[row.roll]
            grouped[key].append((row.cell, weight))
            count += 1
    summaries = {}
    for key, rows in sorted(grouped.items()):
        kinds, tokens, gains, priorities, colors, locations = (Counter() for _ in range(6))
        bounds = 0
        for cell, weight in rows:
            kinds[cell.kind.value] += weight
            tokens[format_cell(cell)] += weight
            priorities[cell.priority.value] += weight
            color = cell.chart_color
            colors[color.value if color is not None else "unspecified"] += weight
            bounds += weight * cell.out_of_bounds
            if cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}:
                gains[cell.yards if cell.yards is not None else 0] += weight
            elif cell.kind in {ResultKind.INTERCEPTION, ResultKind.FUMBLE, ResultKind.BLOCKED_KICK}:
                if cell.yards is not None:
                    locations[f"{cell.kind.value}/{cell.yards}"] += weight
                else:
                    locations[f"{cell.kind.value}/variable:{cell.variable.value}"] += weight
        summaries[key] = {
            "records": len(rows),
            "physical_mass": sum(weight for _, weight in rows),
            "kind_mass": _counter(kinds),
            "token_mass": _counter(tokens),
            "numeric_gain_histogram": _counter(gains),
            "location_histogram": _counter(locations),
            "priority_mass": _counter(priorities),
            "color_mass": _counter(colors),
            "out_of_bounds_mass": bounds,
        }
    good = sum(offense_weights[row.roll] for row in chart.pat_outcomes if row.good)
    summaries["pat"] = {
        "records": len(chart.pat_outcomes),
        "physical_mass": 216,
        "good_mass": good,
        "missed_mass": 216 - good,
    }
    return {
        "chart_records": count + len(chart.pat_outcomes),
        "columns": summaries,
        "recovery": {
            "inclusive_range": [chart.recovery_range.start, chart.recovery_range.stop - 1],
            "retained_roll_mass": sum(offense_weights[roll] for roll in chart.recovery_range),
            "physical_mass": 216,
        },
        "interpretation": "weighted chart facts, not resolved terminal/source rates",
    }


def primary_measure(
    offense: TeamChart,
    defense: TeamChart,
    play: Play,
    formation: Defense,
    *,
    expected_priority: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Enumerate symbolic primary priority with exact 216 x 36 physical mass.

    Variables and conditional mechanisms remain symbolic/pending. This stops
    before state transitions, conditional rerolls and turnover choices. Face
    totals are sufficient here only because no DS/variable materialization runs.
    """
    offense_weights, defense_weights = physical_weights()
    off_rows = {row.roll: row.cell for row in offense.offense if row.play is play}
    def_rows = {
        row.roll: row.cell
        for row in defense.defense
        if row.play is play and row.defense is formation
    }
    kinds, operations, sources, depths, numbers = (Counter() for _ in range(5))
    bins = Counter()
    pending, bounds, checked = 0, 0, 0
    for off_roll, off_weight in offense_weights.items():
        for def_roll, def_weight in defense_weights.items():
            mass = off_weight * def_weight
            left, right = off_rows[off_roll], def_rows[def_roll]
            subject = resolve_cells(left, right)
            result = {
                key: _plain(getattr(subject, key))
                for key in (
                    "operation",
                    "source",
                    "kind",
                    "yards",
                    "pending",
                    "out_of_bounds",
                    "penalty",
                    "defensive_end_zone_depth",
                )
            }
            if subject.penalty is not None:
                result["penalty"] = _plain(asdict(subject.penalty))
            if expected_priority is not None:
                expected = expected_priority(_cell_facts(left), _cell_facts(right))
                if any(
                    key not in expected
                    or type(expected[key]) is not type(value)
                    or expected[key] != value
                    for key, value in result.items()
                ):
                    raise ValueError("independent priority mismatch")
                checked += 1
            result["offense_variable"] = _plain(left.variable)
            result["offense_variable_multiplier"] = left.variable_multiplier
            result["defense_variable"] = _plain(right.variable)
            result["defense_variable_multiplier"] = right.variable_multiplier
            bins[json.dumps(result, sort_keys=True, separators=(",", ":"))] += mass
            kind = subject.kind.value if subject.kind is not None else "unresolved_variable"
            kinds[kind] += mass
            operations[subject.operation.value] += mass
            sources[subject.source.value] += mass
            pending += mass * subject.pending
            bounds += mass * subject.out_of_bounds
            if subject.kind is ResultKind.INTERCEPTION and type(subject.yards) is int:
                depths[subject.yards] += mass
            if subject.kind is ResultKind.YARDS and not subject.pending:
                if type(subject.yards) is not int:
                    raise ValueError("ordinary numeric result lacks fixed integer yards")
                numbers[subject.yards] += mass
    total = sum(kinds.values())
    if total != 7776 or sum(bins.values()) != total:
        raise ValueError("primary physical denominator changed")
    return {
        "play": play.value,
        "formation": formation.value,
        "physical_mass": total,
        "kind_mass": _counter(kinds),
        "operation_mass": _counter(operations),
        "source_mass": _counter(sources),
        "pending_mass": pending,
        "out_of_bounds_mass": bounds,
        "ordinary_numeric_mass": sum(numbers.values()),
        "ordinary_numeric_histogram": _counter(numbers),
        "ordinary_yardage_contribution": str(
            Fraction(sum(yards * mass for yards, mass in numbers.items()), total)
        ),
        "selected_INT_location_histogram": _counter(depths),
        "semantic_bins": [
            {"facts": json.loads(key), "physical_mass": mass} for key, mass in sorted(bins.items())
        ],
        "independent_priority_checked": expected_priority is not None,
        "independent_priority_address_pairs": checked,
        "terminal_acceptance": "NOTRUN-symbolic-primary-only",
    }
