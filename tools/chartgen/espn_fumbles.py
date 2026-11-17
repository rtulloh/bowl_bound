"""Associate primary fumbles split across numbered ESPN drive boundaries."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .espn_returns import _clock, _team, drive_boundary_pairs

PRIMARY_FUMBLE_POLICY = "espn-cross-drive-primary-fumble-v1"


def link_primary_fumbles(plays: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Require an exact same-clock continuation of a named primary action.

    Recovery advances never supply primary gains. Equal end/start down, distance,
    position and owner corroborate the boundary association; missing context
    stays unresolved. This does not establish nonfumble observations.
    """
    links = []
    for primary, recovery in drive_boundary_pairs(plays):
        kind = primary.get("type", {}).get("text")
        if kind not in {"Rush", "Pass Completion", "Sack"}:
            continue
        end, start = primary.get("end", {}), recovery.get("start", {})
        owner = _team(primary.get("start", {}).get("team", {}))
        period = primary.get("period", {}).get("number")
        if (
            owner is None
            or owner != _team(end.get("team", {}))
            or owner != _team(start.get("team", {}))
            or type(period) is not int
            or period < 1
            or period != recovery.get("period", {}).get("number")
            or _clock(primary) is None
            or _clock(primary) != _clock(recovery)
            or type(primary.get("statYardage")) is not int
            or primary.get("isPenalty") is True
            or recovery.get("isPenalty") is True
        ):
            continue
        if any(
            type(end.get(key)) is not int
            or not low <= end[key] <= high
            or start.get(key) != end[key]
            or type(start.get(key)) is not int
            for key, low, high in (("down", 1, 4), ("distance", 0, 100), ("yardLine", 0, 100))
        ):
            continue
        pattern = (
            r"complete to (.+?) \(([^)]+)\)"
            if kind == "Pass Completion"
            else r"^(.+?) \(([^)]+)\) (?:rushed|sacked)"
        )
        carrier = re.search(pattern, primary.get("text") or "", re.I)
        fumbler = re.search(r"fumble by (.+?) \(([^)]+)\)", recovery.get("text") or "", re.I)
        if (
            carrier is None
            or fumbler is None
            or tuple(s.casefold() for s in carrier.groups())
            != tuple(s.casefold() for s in fumbler.groups())
        ):
            continue
        links.append({"primary": primary["id"], "recovery": recovery["id"], "kind": kind})
    return links
