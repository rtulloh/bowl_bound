"""Public-safe model identity survives cohort serialization without source prose."""

import json
from pathlib import Path

import pytest

from tests.chartgen.test_generation import events as events
from tools.chartgen.batch import generate_cohort
from tools.chartgen.evidence import Event
from tools.chartgen.generate import TOOL_VERSION
from tools.chartgen.tactics import APPROVED_YARDAGE_POLICY_SHA256, TacticalProfile


@pytest.mark.parametrize("authored", (False, True))
def test_cohort_records_exact_safe_model_identity(
    tmp_path: Path, events: list[Event], authored: bool
) -> None:
    policy = (
        TacticalProfile.for_corrected_release(APPROVED_YARDAGE_POLICY_SHA256)
        if authored
        else TacticalProfile.neutral()
    )
    root = tmp_path / "private-data" / "cohort"
    result = generate_cohort(events, {"1": "Cedar Valley"}, 2007, root, seed=19, tactics=policy)
    identity = {
        "origin": policy.origin,
        "sha256": policy.sha256,
        "authored_experimental": authored,
        "tool_version": TOOL_VERSION,
        "source_sha256": result["source_sha256"],
    }
    assert result["model_identity"] == identity
    assert json.loads((root / "cohort-generation.json").read_text())["model_identity"] == identity
