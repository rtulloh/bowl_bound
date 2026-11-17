"""Bind research to an independently reviewed release and reference context.

The source anchor supplements loaded-definition attestation. It does not certify
historical source facts, model accuracy or a hostile Python process.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .runtime_identity import RESEARCH_ROOT

APPROVED_ENGINE_COMMIT = "e218fd95942eecbd1f82b50111718b6c996d1a0a"
REVIEWED_CONTRACT_SHA256 = "7a4988db3f13bf39623dfdf28fbcd633c14ed00acff9d31ccf727c669dd9fa9a"
REFERENCE_COACH_POLICY = "hard-v15"
REFERENCE_SIMULATION_VERSION = 15
SOURCE_ONLY_ENGINE_PATHS = ("bowl_bound/__main__.py",)


def _document_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def read_contract(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    """Read one exact independently approved contract, not a candidate's pin."""
    document = json.loads(path.read_bytes())
    if not isinstance(document, dict) or _document_sha256(document) != expected_sha256:
        raise ValueError("reviewed research contract identity differs")
    return document


def verify_source_inventory(
    root: Path, expected: Mapping[str, str], *, package: str | None = None
) -> dict[str, str]:
    """Verify raw bytes and a recursive package census when a scope is supplied."""
    if any(Path(name).is_absolute() or ".." in Path(name).parts for name in expected):
        raise ValueError("reviewed research source path must stay inside its checkout")
    names = (
        {path.relative_to(root).as_posix() for path in (root / package).rglob("*.py")}
        if package is not None
        else set(expected)
    )
    if names != set(expected):
        raise ValueError("reviewed research source inventory differs")
    try:
        actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    except OSError as error:
        raise ValueError("reviewed research source is missing or unreadable") from error
    if actual != dict(expected):
        raise ValueError("reviewed research source identity differs")
    return actual


def verify_attested_sources(attestation: Mapping[str, Any], expected: Mapping[str, str]) -> None:
    """Bind the actual source bytes consulted during loaded-code verification."""
    observed = {}
    for entry in attestation.get("runtime_modules", {}).values():
        name = entry.get("path")
        if name in expected:
            if name in observed:
                raise ValueError("reviewed research attested source is duplicated")
            observed[name] = entry.get("source_sha256")
    if observed != dict(expected):
        raise ValueError("reviewed research attested source differs")


def reference_options() -> dict[str, Any]:
    """Return the reviewed experimental current-policy execution options."""
    return {
        "coach_policy": REFERENCE_COACH_POLICY,
        "simulation_coach_version": REFERENCE_SIMULATION_VERSION,
    }


def require_current_runtime(attestation: Mapping[str, Any]) -> dict[str, Any]:
    """Require current engine and reviewed runner/observer identities together."""
    contract = read_contract(
        Path(__file__).with_name("research-runtime-contract.json"),
        expected_sha256=REVIEWED_CONTRACT_SHA256,
    )
    if (
        contract.get("schema_version") != 1
        or contract.get("engine_commit") != APPROVED_ENGINE_COMMIT
        or attestation.get("runtime_origins_verified") is not True
    ):
        raise ValueError("reviewed research contract authority is missing or stale")
    engine = contract["engine_files"]
    runtime = contract["runtime_files"]
    verify_attested_sources(
        attestation,
        {
            **{
                name: digest
                for name, digest in engine.items()
                if name not in SOURCE_ONLY_ENGINE_PATHS
            },
            **runtime,
        },
    )
    verify_source_inventory(RESEARCH_ROOT, engine, package="bowl_bound")
    verify_source_inventory(RESEARCH_ROOT, runtime)
    reference = {
        **reference_options(),
        "decision_coach_version": None,
        "ordinary_away": "hard-v15",
        "ordinary_home": "baseline-v15",
        "pending_and_clock": "hard-v15",
        "advanced_ii": False,
    }
    if contract["reference_execution"] != reference:
        raise ValueError("reviewed research reference configuration differs")
    return {
        "reviewed_engine_verified": True,
        "engine_release_commit": APPROVED_ENGINE_COMMIT,
        "engine_release_contract_sha256": REVIEWED_CONTRACT_SHA256,
        "reviewed_runtime_source_sha256": _document_sha256(runtime),
        "reference_configuration": reference,
        "source_only_engine_paths": list(SOURCE_ONLY_ENGINE_PATHS),
    }
