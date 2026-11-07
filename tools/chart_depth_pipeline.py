"""Final conditional-depth stage after parent chart calibration.

The caller binds the selected team/side observations to its frozen source
population. This stage consumes the completed parent's ordinary files; it never
reruns or substitutes that calibration.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

from bowl_bound.team_csv import team_from_files

from .chart_depth_audit import DepthAuditError, audit_depth_change
from .chart_depth_encoding_audit import Support, audit_chart_encoding
from .chart_depth_export import encode_depth_candidate
from .chart_depth_policy import DepthEvent, apply_depth_policy, execution_identity

FILES = frozenset({"team.yaml", "offense.csv", "defense.csv", "special.csv", "provenance.csv"})


def _targets(audit: dict[str, Any]) -> dict[str, Support]:
    targets = {}
    for side in ("offense", "defense"):
        for play in range(6, 10):
            support = tuple(
                (x, Fraction(p)) for x, p in audit["columns"][f"{side}/{play}"]["modeled_target"]
            )
            groups = ("offense",) if side == "offense" else tuple("ABCDEF")
            for group in groups:
                key = f"offense/{play}" if side == "offense" else f"defense/{play}/{group}"
                targets[key] = support
    return targets


def finalize_depth_files(
    calibrated_files: Mapping[str, str],
    offense_events: Sequence[DepthEvent],
    defense_events: Sequence[DepthEvent],
    *,
    source_sha256: str,
    parent_model_sha256: str,
    prior_strength: int = 4,
    enumeration_budget: int = 2_000_000,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Correct final ordinary files and require independent pre/post-export checks."""
    if set(calibrated_files) != FILES:
        raise ValueError("final depth stage requires exactly five completed parent files")
    for value in (source_sha256, parent_model_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("final depth stage requires frozen source and parent model SHA256")
    identity = execution_identity(prior_strength)
    file_pins = {
        name: hashlib.sha256(text.encode()).hexdigest()
        for name, text in sorted(calibrated_files.items())
    }
    baseline_sha = hashlib.sha256(
        json.dumps(file_pins, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    baseline, metadata = team_from_files(
        {k: v for k, v in calibrated_files.items() if k != "provenance.csv"},
        calibrated_files["provenance.csv"],
    )
    candidate, producer = apply_depth_policy(
        baseline, offense_events, defense_events, prior_strength=prior_strength
    )
    audit = audit_depth_change(
        baseline,
        candidate,
        offense_events,
        defense_events,
        identity["contract"],
        prior_strength=prior_strength,
    )
    # Targets come from the separate source qualifier, never producer claims.
    encoding = audit_chart_encoding(
        candidate, _targets(audit), enumeration_budget=enumeration_budget
    )
    if encoding["status"] != "PASS-exhaustive":
        raise DepthAuditError("final depth export is unqualified: finite encoding budget")
    files, export = encode_depth_candidate(
        candidate,
        metadata,
        source_sha256=source_sha256,
        baseline_sha256=baseline_sha,
        model_identity=identity,
    )
    loaded, _ = team_from_files(
        {k: v for k, v in files.items() if k != "provenance.csv"}, files["provenance.csv"]
    )
    reloaded_audit = audit_depth_change(
        baseline,
        loaded,
        offense_events,
        defense_events,
        identity["contract"],
        prior_strength=prior_strength,
    )
    reloaded_encoding = audit_chart_encoding(
        loaded, _targets(reloaded_audit), enumeration_budget=enumeration_budget
    )
    if reloaded_audit != audit or reloaded_encoding != encoding:
        raise DepthAuditError("ordinary export changed independently qualified depth facts")
    return files, {
        "status": "PASS-final-depth-files",
        "stage_order": [
            "completed-parent-calibration",
            "conditional-depth",
            "ordinary-export-reload",
        ],
        "parent_model_sha256": parent_model_sha256,
        "source_sha256": source_sha256,
        "baseline_file_sha256": file_pins,
        "baseline_sha256": baseline_sha,
        "producer": producer,
        "independent_policy": reloaded_audit,
        "independent_encoding": reloaded_encoding,
        "export": export,
        "historical_fit": "UNVERIFIED",
        "terminal_behavior": "requires-engine-and-independent-event-panels",
    }
