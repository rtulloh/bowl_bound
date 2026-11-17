"""Deterministic training-only choice and immutable pre-validation receipts.

Developer charts and downstream reference diagnostics are not inputs. The policy
is deliberately conservative: aggregate improvement cannot buy a worse baseline
OFF/DEF unit or remove a previously passing core measure.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .batch import write_json_new
from .cohort_report import canonical_hash
from .scope import CORE_METRICS

SELECTION_POLICY = {
    "version": 1,
    "rank": ["failed_games", "equal_team_joint_loss", "candidate_index"],
    "guard": "no baseline unit-loss regression and no loss of previously passing core metrics",
    "objective_scope": (
        "historically qualified units and metrics only; sparse outer units descriptive"
    ),
    "no_improvement_candidate_limit": 2,
    "comparison": "training observations only; fixed baseline candidate zero",
    "reference_inputs": False,
    "limits": (
        "conservative safeguards may retain a statistically unfit baseline; no global optimum claim"
    ),
}


def _units(record: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        f"{team}/{role}": value.get(f"{role}_assessment", {})
        for team, value in sorted(record["summary"]["per_source_team"].items())
        if value["game_ids"]
        for role in ("offense", "defense")
    }


def _unit_loss(assessment: Mapping[str, Any]) -> float | None:
    historical = assessment.get("historical_exposure", {})
    if historical.get("qualified") is not True:
        return None
    source_metrics = historical.get("metrics", {})
    losses = []
    for name, metric in sorted(assessment["metrics"].items()):
        if source_metrics.get(name, {}).get("qualified") is not True:
            continue
        error, tolerance = metric["absolute_error"], metric["tolerance"]
        if tolerance <= 0 or not math.isfinite(tolerance):
            raise ValueError("training metric tolerance must be finite and positive")
        if error is None:
            losses.append(10000.0)
        elif not math.isfinite(error) or error < 0:
            raise ValueError("training metric error must be finite and nonnegative or unknown")
        else:
            losses.append(min(100, error / tolerance) ** 2)
    return sum(losses) / len(losses) if losses else None


def qualified_training_objective(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Keep sparse opponents in diagnostics without weighting a historical fit."""
    units = _units({"summary": summary})
    values = {name: _unit_loss(unit) for name, unit in units.items()}
    qualified = {name: value for name, value in values.items() if value is not None}
    return {
        "loss": sum(qualified.values()) / len(qualified) if qualified else 10000.0,
        "qualified_units": sorted(qualified),
        "descriptive_only_units": sorted(set(units) - set(qualified)),
        "per_unit_losses": qualified,
    }


def choose_training_candidate(history: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Choose an admissible candidate with explicit earliest-index tie breaking."""
    ordered = sorted(history, key=lambda record: record["candidate"])
    indices = [record["candidate"] for record in ordered]
    if (
        not indices
        or indices[0] != 0
        or any(type(value) is not int or value < 0 for value in indices)
        or len(set(indices)) != len(indices)
    ):
        raise ValueError(
            "training candidate indices must be unique nonnegative integers including zero"
        )
    fingerprints = [record["chart_fingerprint"] for record in ordered]
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError("duplicate training fingerprint must stop before another simulation batch")
    all_baseline = _units(ordered[0])
    baseline = {
        name: value for name, value in all_baseline.items() if _unit_loss(value) is not None
    }
    if not all_baseline:
        raise ValueError("training candidate has no identified team units")
    choices, assessments = [], []
    for record in ordered:
        units = _units(record)
        reasons = []
        if set(units) != set(all_baseline):
            reasons.append("team_unit_set_changed")
        for address in sorted(set(baseline) & set(units)):
            before, after = baseline[address], units[address]
            before_loss, after_loss = _unit_loss(before), _unit_loss(after)
            if after_loss is None:
                reasons.append(f"{address}:historical_qualification_removed")
            elif before_loss is not None and after_loss > before_loss:
                reasons.append(f"{address}:unit_loss_regressed")
            for name, metric in sorted(before["metrics"].items()):
                if (
                    name in CORE_METRICS
                    and metric["passed"]
                    and not after["metrics"].get(name, {}).get("passed", False)
                ):
                    reasons.append(f"{address}:previously_passing_core/{name}")
            if set(before["metrics"]) - set(after["metrics"]):
                reasons.append(f"{address}:identified_metric_removed")
        failed, loss, index = (
            record["summary"]["failed_games"],
            record["equal_team_joint_loss"],
            record["candidate"],
        )
        if type(failed) is not int or failed < 0 or not math.isfinite(loss) or loss < 0:
            raise ValueError("training rank requires finite nonnegative loss and integer failures")
        admissible = not reasons
        assessments.append(
            {
                "candidate": index,
                "rank": [failed, loss, index],
                "admissible": admissible,
                "reasons": reasons,
            }
        )
        if admissible:
            choices.append(((failed, loss, index), record))
    _, selected = min(choices, key=lambda item: item[0])
    return json.loads(
        json.dumps(
            {
                "policy": SELECTION_POLICY,
                "qualified_units": sorted(baseline),
                "descriptive_only_units": sorted(set(all_baseline) - set(baseline)),
                "selected_candidate": selected["candidate"],
                "selected_profiles": selected["profiles"],
                "selected_chart_fingerprint": selected["chart_fingerprint"],
                "candidate_assessments": assessments,
            },
            allow_nan=False,
        )
    )


def seal_training_selection(
    destination: Path, history: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    """Freeze training choice before fresh validation, retaining strict resume.

    No timestamp or output path participates in this semantic receipt. The caller
    supplies the pinned execution/source/seed contract, not downstream audits.
    Existing differing or tampered receipts fail without overwriting evidence.
    """
    choice = choose_training_candidate(history)
    evidence = [
        {
            "candidate": record["candidate"],
            "profiles": record["profiles"],
            "chart_fingerprint": record["chart_fingerprint"],
            "failed_games": record["summary"]["failed_games"],
            "equal_team_joint_loss": record["equal_team_joint_loss"],
            "unit_assessments": _units(record),
            "fixture_exposure": record["summary"].get("fixture_exposure", {}),
        }
        for record in sorted(history, key=lambda record: record["candidate"])
    ]
    body = {
        "schema_version": 1,
        "execution_contract": config,
        "training_evidence_sha256": canonical_hash(evidence),
        **choice,
    }
    receipt = json.loads(
        json.dumps({**body, "semantic_sha256": canonical_hash(body)}, allow_nan=False)
    )
    if destination.exists():
        if json.loads(destination.read_text()) != receipt:
            raise ValueError("retained training selection differs from verified evidence")
    else:
        write_json_new(destination, receipt)
    return receipt


def claim_training_fingerprint(fingerprint: str, seen: set[str]) -> bool:
    """Claim a new candidate before simulation; reject even nonconsecutive cycles."""
    if fingerprint in seen:
        return False
    seen.add(fingerprint)
    return True


def training_plateau_reached(no_improvement: int) -> bool:
    """Apply the already-declared finite candidate plateau policy."""
    return no_improvement >= SELECTION_POLICY["no_improvement_candidate_limit"]
