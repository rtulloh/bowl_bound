"""Independent release qualification for the explicitly source-unidentified cohort.

This guard supports only a reviewed zero-designed-call-sample declaration.
Nonzero, absent and unknown sample counts require a different qualified contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import replace
from fractions import Fraction
from typing import Any

from bowl_bound.models import ResultKind, TeamChart

from . import chart_depth_encoding_audit as encoding

POLICY_SHA256 = "f44fbd9822fa844155a94905aca30ff5c30a2ace52b62e4c2086178cacb224a1"


def validate_qualification(value: Any, teams: set[str]) -> dict[str, encoding.Support]:
    """Validate the compiled authored policy and explicit reviewed source counts."""
    if not isinstance(value, dict) or set(value) != {
        "identity",
        "source_qualification_sha256",
        "known_designed_call_depth_samples",
    }:
        raise ValueError("conditional depth qualification is incomplete")
    identity = value["identity"]
    if not isinstance(identity, dict) or set(identity) != {
        "origin",
        "sha256",
        "authored_experimental",
        "contract",
    }:
        raise ValueError("conditional depth identity is incomplete")
    contract = identity["contract"]
    digest = hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    if (
        identity["origin"] != "authored-bb-call-depth-v1"
        or identity["sha256"] != POLICY_SHA256
        or identity["authored_experimental"] is not True
        or digest != POLICY_SHA256
        or not isinstance(value["source_qualification_sha256"], str)
        or re.fullmatch(r"[a-f0-9]{64}", value["source_qualification_sha256"]) is None
    ):
        raise ValueError("conditional depth policy/source identity is unqualified")
    counts = value["known_designed_call_depth_samples"]
    expected = {f"{side}/{p}" for side in ("offense", "defense") for p in range(6, 10)}
    if not isinstance(counts, dict) or set(counts) != teams:
        raise ValueError("conditional depth source team inventory is incomplete")
    if any(
        not isinstance(record, dict)
        or set(record) != expected
        or any(type(n) is not int or n != 0 for n in record.values())
        for record in counts.values()
    ):
        raise ValueError(
            "conditional depth requires reviewed zero known samples; unknown is not zero"
        )
    priors = contract["priors"]
    targets = {}
    for play in range(6, 10):
        prior = priors[str(play)]
        target = tuple((x, Fraction(w)) for x, w in prior)
        targets[f"offense/{play}"] = target
        targets.update({f"defense/{play}/{f}": target for f in "ABCDEF"})
    return targets


def mask_depths(chart: TeamChart) -> TeamChart:
    """Mask only passing fixed INT payloads for the parent budget comparison."""

    def row(record: Any) -> Any:
        if record.play.value >= 6 and record.cell.kind is ResultKind.INTERCEPTION:
            if record.cell.variable is not None:
                raise ValueError("conditional depth requires fixed interception payloads")
            return replace(record, cell=replace(record.cell, yards=0))
        return record

    return replace(
        chart,
        offense=tuple(row(r) for r in chart.offense),
        defense=tuple(row(r) for r in chart.defense),
    )


def audit_encoding(chart: TeamChart, targets: Mapping[str, encoding.Support]) -> dict[str, Any]:
    """Refuse unsupported, noncanonical or unverified finite depth encodings."""
    report = encoding.audit_chart_encoding(chart, targets)
    if report["status"] != "PASS-exhaustive":
        raise ValueError("conditional depth encoding remains unverified")
    return report
