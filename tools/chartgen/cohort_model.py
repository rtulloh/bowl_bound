"""Versioned reuse of the reviewed allocation algorithm for historical cohorts.

The original Alpha 9 contract remains immutable. This identity extends its
execution scope; it grants neither source qualification nor distribution rights.
"""

from __future__ import annotations

from copy import deepcopy

from bowl_bound.models import TeamChart

from .alpha_event_risks import apply_alpha_model
from .alpha_event_risks import model_identity as alpha_identity
from .coupled_depths import DepthSupport
from .coupled_event_risks import _digest

TOOL_VERSION = "bb-chartgen-cohort-v1"
SUPPORTED_SEASONS = (2002, 2007)
CONTRACT = {
    "origin": "authored-bb-cohort-v1",
    "parent": alpha_identity(),
    "seasons": SUPPORTED_SEASONS,
    "allocation": "unchanged-parent-budget-objective-and-payload-balancing",
    "authority": "experimental-generation-only;source-fit-and-publication-require-separate-review",
}


def model_identity() -> dict[str, object]:
    """Identify the explicit cohort extension without relabeling the old model."""
    return {
        "origin": CONTRACT["origin"],
        "sha256": _digest(CONTRACT),
        "authored_experimental": True,
        "contract": deepcopy(CONTRACT),
    }


def apply_cohort_model(
    chart: TeamChart, *, known_depths: DepthSupport, unknown_locations: int, source_identity: str
) -> tuple[TeamChart, dict[str, object]]:
    """Apply the recovered allocator under a distinct, bounded execution scope."""
    if chart.season not in SUPPORTED_SEASONS:
        raise ValueError("cohort model requires a supported season: 2002 or 2007")
    candidate, receipt = apply_alpha_model(
        chart,
        known_depths=known_depths,
        unknown_locations=unknown_locations,
        source_identity=source_identity,
    )
    receipt["parent_model_identity"] = receipt["model_identity"]
    receipt["model_identity"] = model_identity()
    receipt["tool_version"] = TOOL_VERSION
    return candidate, receipt
