"""Complete passing census; source envelopes do not imply conditional fit."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from bowl_bound.models import Defense, NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.team_csv import format_cell, parse_cell

from .reference_inventory import physical_weights
from .reference_measures import primary_measure, table_measures

PASS_PLAYS = (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE)
SCOPED_PLAYS = (Play.FIVE, *PASS_PLAYS)
_ALLOWED = {
    ResultKind.YARDS,
    ResultKind.NO_CHANGE,
    ResultKind.INCOMPLETE,
    ResultKind.TOUCHDOWN,
    ResultKind.VARIABLE_DS,
    ResultKind.VARIABLE_X,
    ResultKind.VARIABLE_T1,
    ResultKind.VARIABLE_T2,
    ResultKind.VARIABLE_T3,
    ResultKind.BREAKAWAY,
    ResultKind.QUARTERBACK_RUN,
    ResultKind.QUARTERBACK_TRAPPED,
    ResultKind.SPRINT_OUT_PASS,
    ResultKind.BOOTLEG_PASS,
    ResultKind.PENALTY,
    ResultKind.FUMBLE,
    ResultKind.INTERCEPTION,
}


class PassingAuditError(ValueError):
    """A complete census or declared hard support contract was violated."""


@dataclass(frozen=True)
class GainEnvelope:
    """Named source range, used diagnostically rather than as a universal cap."""

    lower: int
    upper: int
    samples: int
    missing: int
    label: str

    def __post_init__(self) -> None:
        if any(type(x) is not int for x in (self.lower, self.upper, self.samples, self.missing)):
            raise PassingAuditError("numeric envelope requires integer observations")
        if self.lower > self.upper or self.samples <= 0 or self.missing < 0 or not self.label:
            raise PassingAuditError("numeric envelope requires a nonempty named source population")


def _facts(cell: NormalizedCell) -> tuple[Any, ...]:
    return (
        cell.kind,
        cell.yards,
        cell.variable,
        cell.variable_multiplier,
        cell.priority,
        cell.out_of_bounds,
        cell.penalty,
    )


def _rows(chart: TeamChart) -> list[tuple[str, int, NormalizedCell, int, bool]]:
    ow, dw = physical_weights()
    result = [
        (f"offense/{r.play.value}", r.roll, r.cell, ow[r.roll], r.play in SCOPED_PLAYS)
        for r in chart.offense
    ]
    result += [
        (
            f"defense/{r.play.value}/{r.defense.value}",
            r.roll,
            r.cell,
            dw[r.roll],
            r.play in SCOPED_PLAYS,
        )
        for r in chart.defense
    ]
    result += [
        (f"supplemental/{r.column.value}", r.roll, r.cell, ow[r.roll], True)
        for r in chart.supplemental
    ]
    return result


def audit_passing_chart(
    chart: TeamChart,
    int_supports: Mapping[str, tuple[int, ...]],
    gain_envelopes: Mapping[str, GainEnvelope | None],
) -> dict[str, Any]:
    """Inspect an ordinarily loaded chart, retaining unresolved evidence.

    Hard INT supports must be independently constructed. Source gain envelopes
    are diagnostic: an additive chart contribution need not be a complete play
    gain. Being inside a pooled range never establishes designed-call support.
    """
    expected_int = {f"offense/{p.value}" for p in PASS_PLAYS} | {
        f"defense/{p.value}/{d.value}" for p in PASS_PLAYS for d in Defense
    }
    if set(int_supports) != expected_int or any(
        not support or any(type(x) is not int for x in support) for support in int_supports.values()
    ):
        raise PassingAuditError("complete independent INT support inventory is required")
    rows = _rows(chart)
    columns: dict[str, list[tuple[int, NormalizedCell, int, bool]]] = defaultdict(list)
    for key, roll, cell, weight, scoped in rows:
        columns[key].append((roll, cell, weight, scoped))
    expected_keys = (
        {f"offense/{p.value}" for p in Play}
        | {f"defense/{p.value}/{d.value}" for p in Play for d in Defense}
        | {f"supplemental/{s}" for s in ("B", "QR", "QT")}
    )
    if set(columns) != expected_keys or len(rows) != 630:
        raise PassingAuditError("complete 630-cell scrimmage/dependency inventory is required")
    summaries: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    cells = []
    token_members: dict[str, list[str]] = defaultdict(list)
    column_signatures: dict[str, list[str]] = defaultdict(list)
    for key, items in sorted(columns.items()):
        items.sort(key=lambda item: item[0])
        defense = key.startswith("defense/")
        rolls = set(range(1, 6)) if defense else set(range(10, 40))
        if {r for r, _, _, _ in items} != rolls or len(items) != len(rolls):
            raise PassingAuditError(f"missing/duplicate row: {key}")
        denominator = 36 if defense else 216
        if sum(w for _, _, w, _ in items) != denominator:
            raise PassingAuditError(f"physical mass mismatch: {key}")
        kinds: Counter[str] = Counter()
        flags: Counter[str] = Counter()
        numeric: Counter[int] = Counter()
        signature = []
        runs = []
        previous = None
        start = 0
        for roll, cell, weight, scoped in items:
            address = f"{key}/{roll}"
            if cell.kind not in _ALLOWED:
                raise PassingAuditError(f"unmapped scrimmage token: {address}")
            if cell.provenance is None:
                raise PassingAuditError(f"missing cell evidence: {address}")
            token = format_cell(cell)
            if _facts(parse_cell(token, cell.provenance)) != _facts(cell):
                raise PassingAuditError(f"semantic token roundtrip mismatch: {address}")
            sig = (token, cell.chart_color.value if cell.chart_color is not None else None)
            signature.append(sig)
            token_members[repr(sig)].append(address)
            if sig != previous:
                if previous is not None and roll - start > 1:
                    runs.append({"start": start, "end": roll - 1, "signature": previous})
                start, previous = roll, sig
            kinds[cell.kind.value] += weight
            flags[f"{cell.priority.value}/OOB={cell.out_of_bounds}/color={sig[1]}"] += weight
            if not scoped:
                continue
            status = "UNVERIFIED-conditional-terminal"
            detail: dict[str, Any] = {}
            if cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}:
                value = cell.yards if cell.kind is ResultKind.YARDS else 0
                if type(value) is not int:
                    raise PassingAuditError(f"unmapped numeric payload: {address}")
                numeric[value] += weight
                evidence_key = key
                if key == "supplemental/QT":
                    evidence_key += "/negative" if value < 0 else "/nonnegative"
                envelope = gain_envelopes.get(evidence_key)
                if envelope is None:
                    status = "UNVERIFIED-missing-numeric-evidence"
                else:
                    detail = {
                        "source_label": envelope.label,
                        "observed_range": [envelope.lower, envelope.upper],
                        "known": envelope.samples,
                        "missing": envelope.missing,
                    }
                    status = (
                        "REVIEW-outside-source-envelope"
                        if not envelope.lower <= value <= envelope.upper
                        else "UNVERIFIED-within-unidentified-source-envelope"
                    )
                detail["meaning"] = (
                    "sack"
                    if key == "supplemental/QT" and value < 0
                    else "rush"
                    if key in {"supplemental/QT", "supplemental/QR"}
                    else "origin-dependent gain"
                    if key == "supplemental/B"
                    else "chart gain contribution; not interception catch depth"
                )
            elif cell.kind is ResultKind.INTERCEPTION:
                if key not in int_supports or cell.variable is not None:
                    status = "UNVERIFIED-unmapped-INT-context"
                elif cell.yards not in int_supports[key]:
                    raise PassingAuditError(f"unsupported conditional INT depth: {address}")
                else:
                    status = "PASS-declared-INT-support-only"
                    detail["meaning"] = "catch depth, not return gain or historical call truth"
            elif cell.kind is ResultKind.INCOMPLETE:
                status = "PASS-incomplete-token-only"
            entry = {
                "address": address,
                "token": token,
                "kind": cell.kind.value,
                "physical_mass": weight,
                "denominator": denominator,
                "status": status,
                "detail": detail,
            }
            cells.append(entry)
            if not status.startswith("PASS"):
                findings.append(entry)
        last = items[-1][0]
        if previous is not None and last - start >= 1:
            runs.append({"start": start, "end": last, "signature": previous})
        column_signatures[repr(signature)].append(key)
        summaries[key] = {
            "records": len(items),
            "physical_mass": denominator,
            "kind_mass": dict(sorted(kinds.items())),
            "flag_union_mass": dict(sorted(flags.items())),
            "numeric_histogram": dict(sorted(numeric.items())),
            "runs": runs,
        }
    if len(cells) != 390:
        raise PassingAuditError("passing/Option/dependency coverage must be 390 cells")
    continuations = [
        {
            "called_play": 5,
            "trigger_roll": r.roll,
            "resolved_play": 7 if r.cell.kind is ResultKind.SPRINT_OUT_PASS else 8,
            "offensive_trigger_mass": physical_weights()[0][r.roll],
            "trigger_denominator": 216,
            "continuation_denominator": 216,
            "defense": "original ordinary defense canceled; no defensive reroll invented",
            "terminal_status": "UNVERIFIED-dependent-path",
        }
        for r in chart.offense
        if r.play is Play.FIVE
        and r.cell.kind in {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS}
    ]
    return {
        "status": "REVIEW-required"
        if any(f["status"].startswith("REVIEW") for f in findings)
        else "UNVERIFIED-required-components",
        "coverage": {
            "direct_pass_cells": 240,
            "option_cells": 60,
            "supplemental_cells": 90,
            "scoped_cells": len(cells),
            "all_family_cluster_cells": len(rows),
            "columns": len(columns),
        },
        "columns": summaries,
        "cells": cells,
        "findings": findings,
        "option_continuations": continuations,
        "clusters": {
            "repeated_token_flag_unions": [
                {"signature": sig, "addresses": addresses}
                for sig, addresses in sorted(token_members.items())
                if len(addresses) > 1
            ],
            "identical_columns": [
                keys for _, keys in sorted(column_signatures.items()) if len(keys) > 1
            ],
            "interpretation": "repetition is not a defect or license to shuffle",
        },
        "table_measures": table_measures(chart),
        "historical_conditional_fit": "UNVERIFIED",
        "terminal_and_field_panel": "REQUIRED-separate-engine-observation",
    }


def passing_primary_panel(
    offense: TeamChart,
    defense: TeamChart,
    *,
    expected_priority: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Measure five called plays under six formations using an independent oracle."""
    if not callable(expected_priority):
        raise PassingAuditError("independent Priority observer is required")
    results = {
        f"{p.value}/{d.value}": primary_measure(
            offense, defense, p, d, expected_priority=expected_priority
        )
        for p in SCOPED_PLAYS
        for d in Defense
    }
    return {
        "contexts": len(results),
        "physical_mass_per_context": 7776,
        "address_pairs": sum(r["independent_priority_address_pairs"] for r in results.values()),
        "results": results,
        "terminal_acceptance": "UNVERIFIED-conditional-residuals-retained",
    }
