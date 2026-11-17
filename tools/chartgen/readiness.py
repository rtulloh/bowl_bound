"""Complete research evidence inventory, separate from experimental point losses."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def _identity(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def compare_run_inventory(
    expected: Sequence[Mapping[str, Any]] | None,
    observed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare complete fixture/repetition/spec identities, including multiplicity."""
    if expected is None:
        return {"complete": False, "state": "missing_expected_run_contract"}
    wanted = Counter(_identity(row) for row in expected)
    actual = Counter(_identity(row) for row in observed)
    duplicated_contract = any(count != 1 for count in wanted.values())
    missing = list((wanted - actual).elements())
    extra = list((actual - wanted).elements())
    complete = bool(wanted) and not duplicated_contract and not missing and not extra
    return {
        "complete": complete,
        "state": "complete" if complete else "invalid_or_incomplete_run_inventory",
        "expected_count": sum(wanted.values()),
        "observed_count": sum(actual.values()),
        "duplicate_expected_identity": duplicated_contract,
        "missing": [json.loads(row) for row in sorted(missing)],
        "unexpected_or_duplicate": [json.loads(row) for row in sorted(extra)],
        "expected_sha256": hashlib.sha256(_identity(dict(wanted)).encode()).hexdigest(),
        "observed_sha256": hashlib.sha256(_identity(dict(actual)).encode()).hexdigest(),
    }


def compare_team_inventory(
    expected: Sequence[str] | None, observed: Sequence[str]
) -> dict[str, Any]:
    """Compare required team keys to an independent frozen source-scope contract."""
    if expected is None:
        return {"complete": False, "state": "missing_expected_team_contract"}
    return compare_run_inventory(
        [{"team": team} for team in expected], [{"team": team} for team in observed]
    )


def qualification_status(
    *,
    failed_games: int,
    per_team: Mapping[str, Mapping[str, Any]],
    coverage: Mapping[str, Any],
    expected_teams: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Keep known failures NO-GO and missing evidence UNVERIFIED.

    No precision/equivalence contract is frozen yet. Existing point tolerances
    cannot certify accuracy, regardless of counts or a selected subset's loss.
    """
    failures = []
    missing = ["precision_contract_unfrozen"]
    if failed_games:
        failures.append("engine_or_reconciliation_failure")
    if coverage.get("complete") is not True:
        missing.append("complete_run_inventory")
        if coverage.get("unexpected_or_duplicate") or coverage.get("duplicate_expected_identity"):
            failures.append("invalid_run_inventory")
    team_inventory = compare_team_inventory(expected_teams, tuple(per_team))
    if expected_teams is None:
        missing.append("expected_source_team_contract")
    elif team_inventory.get("complete") is not True:
        for row in team_inventory.get("missing", []):
            missing.append(f"missing_required_source_team/{row['team']}")
        if team_inventory.get("unexpected_or_duplicate") or team_inventory.get(
            "duplicate_expected_identity"
        ):
            failures.append("invalid_source_team_inventory")
    diagnostics = {}
    for team, unit in sorted(per_team.items()):
        state = unit.get("state", "missing_team_assessment")
        diagnostics[team] = state
        if state not in {"fit", "not_fit"}:
            missing.append(f"{team}:{state}")
        for role in ("offense", "defense"):
            assessment = unit.get(f"{role}_assessment")
            address = f"{team}/{role}"
            if role == "offense":
                # A numeric/NG census is diagnostic. A separately reviewed
                # located-source/comparability/precision criterion is not yet
                # implemented and cannot be supplied by ordinary point losses.
                missing.append(f"{address}:located_field_goal_qualification")
            if assessment is None:
                missing.append(f"{address}:missing_assessment")
                continue
            for metric in assessment.get("unidentifiable_source_metrics", []):
                missing.append(f"{address}:unidentifiable_source_metric/{metric}")
            for metric in assessment.get("historically_sparse_metrics", []):
                missing.append(f"{address}:historically_sparse_metric/{metric}")
            historical = assessment.get("historical_exposure", {})
            for metric, source_evidence in historical.get("metrics", {}).items():
                for reason in source_evidence.get("missing_evidence", []):
                    missing.append(f"{address}/{metric}:{reason}")
            if historical.get("qualified") is not True:
                missing.append(
                    f"{address}:{historical.get('state', 'unqualified_historical_exposure')}"
                )
            for metric, evidence in assessment.get("metrics", {}).items():
                if evidence.get("insufficient_samples") is True:
                    missing.append(f"{address}:insufficient_simulation_metric/{metric}")
    if not per_team:
        missing.append("declared_team_inventory")
    return {
        "passed": False,
        "state": "no_go" if failures else "unverified",
        "known_failures": failures,
        "missing_evidence": missing,
        "precision_contract": "unfrozen",
        "point_diagnostics": diagnostics,
        "team_inventory": team_inventory,
        "scope": "qualification is not established by experimental point tolerances",
    }


def required_phase_status(
    phases: Mapping[str, Mapping[str, Any]],
    *,
    required: Sequence[str],
    checks: Mapping[str, bool | None],
    expected_teams: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Conjoin every declared phase and required mechanical check, without fitting.

    Point tolerances remain descriptive. No phase's qualified subset or successful
    heldout run can erase a retained engine failure or a missing phase inventory.
    """
    failures: list[str] = []
    missing: list[str] = []
    assessments = {}
    mechanics_ready = bool(required) and len(set(required)) == len(required)
    if not mechanics_ready:
        missing.append("required_phase_contract")
    if set(phases) - set(required):
        failures.append("unexpected_phase_inventory")
        mechanics_ready = False
    for name in required:
        if name not in phases:
            missing.append(f"{name}:missing_required_phase")
            mechanics_ready = False
            continue
        phase = phases[name]
        failed_games = phase.get("failed_games")
        if type(failed_games) is not int or failed_games < 0:
            missing.append(f"{name}:missing_failure_inventory")
            mechanics_ready = False
            failed_games = 0
        evidence = qualification_status(
            failed_games=failed_games,
            per_team=phase.get("per_source_team", {}),
            coverage=phase.get("coverage", {}),
            expected_teams=expected_teams,
        )
        assessments[name] = {**evidence, "coverage": phase.get("coverage", {})}
        failures.extend(f"{name}:{reason}" for reason in evidence["known_failures"])
        missing.extend(f"{name}:{reason}" for reason in evidence["missing_evidence"])
        mechanics_ready = (
            mechanics_ready
            and failed_games == 0
            and phase.get("coverage", {}).get("complete") is True
        )
    for name, passed in sorted(checks.items()):
        if passed is False:
            failures.append(f"{name}:failed_required_check")
        elif passed is not True:
            missing.append(f"{name}:missing_required_check")
        mechanics_ready = mechanics_ready and passed is True
    return {
        "passed": False,
        "state": "no_go" if failures else "unverified",
        "mechanics_ready": mechanics_ready,
        "known_failures": failures,
        "missing_evidence": missing,
        "precision_contract": "unfrozen",
        "phases": assessments,
        "required_phases": list(required),
        "required_checks": dict(checks),
    }


def refinement_phase_status(
    training: Sequence[tuple[int, Mapping[str, Any]]],
    *,
    attempted_candidates: Sequence[int],
    heldout: Mapping[str, Any] | None,
    coaching: Mapping[str, Any] | None,
    checks: Mapping[str, bool | None],
    expected_teams: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Bind retained history to the separate pre-batch attempt ledger.

    Candidate records are retained by position before checking declared IDs, so
    duplicate IDs cannot overwrite a failed record. Legitimate early stops require
    only the actual contiguous attempted prefix, not the maximum iteration count.
    """
    attempted = list(attempted_candidates)
    expected = list(range(len(attempted)))
    observed = [identity for identity, _ in training]
    valid = (
        bool(expected)
        and all(type(identity) is int for identity in attempted + observed)
        and attempted == expected
        and observed == expected
    )
    phases = {f"training:{position}": summary for position, (_, summary) in enumerate(training)}
    if heldout is not None:
        phases["heldout"] = heldout
    if coaching is not None:
        phases["coaching"] = coaching
    required = tuple(f"training:{identity}" for identity in expected) + ("heldout", "coaching")
    result = required_phase_status(
        phases, required=required, checks=checks, expected_teams=expected_teams
    )
    result["training_inventory"] = {
        "complete": valid,
        "attempted_candidates": attempted,
        "expected_candidates": expected,
        "observed_candidates": observed,
    }
    if not valid:
        result["known_failures"].append("invalid_training_phase_inventory")
        result.update(state="no_go", mechanics_ready=False)
    return result


def format_readiness_summary(
    *, mechanics_ready: bool, point_passed: bool, qualification: Mapping[str, Any]
) -> str:
    """Label diagnostic command completion separately from accuracy qualification."""
    return (
        f"Mechanics ready: {mechanics_ready}; exploratory point diagnostics: {point_passed}; "
        f"qualification: {qualification.get('state', 'unverified').upper()}"
    )
