"""Link separate return-fumble records using retained core-feed evidence."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

RETURN_FUMBLE_POLICY = "espn-cross-drive-return-fumble-v2"
MAX_RETURN_SECONDS = 30


def _team(value: Mapping[str, Any]) -> str | None:
    match = re.search(r"/teams/(\d+)(?:\?|$)", value.get("$ref", ""))
    return match[1] if match else None


def _clock(play: Mapping[str, Any]) -> int | None:
    value = play.get("clock", {}).get("displayValue")
    if not isinstance(value, str) or re.fullmatch(r"\d{1,2}:[0-5]\d", value) is None:
        return None
    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def drive_boundary_pairs(
    plays: Sequence[Mapping[str, Any]],
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """Pair unique terminal actions with next numbered drive's first fumble row."""
    drives: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for play in plays:
        reference = play.get("drive", {}).get("$ref", "")
        match = re.fullmatch(r"(.*/drives/)(\d+)(?:\?.*)?", reference)
        if match:
            drives[(match[1], int(match[2]))].append(play)
    pairs = []
    for (prefix, number), records in drives.items():
        first = [p for p in records if p.get("sequenceNumber") == "1"]
        if len(first) != 1 or "fumble" not in first[0].get("type", {}).get("text", "").lower():
            continue
        recovery = first[0]
        previous = drives.get((prefix, number - 1), [])
        if not previous or any(
            not isinstance(p.get("sequenceNumber"), str) or not p["sequenceNumber"].isdigit()
            for p in previous
        ):
            continue
        final_sequence = max(int(p["sequenceNumber"]) for p in previous)
        final = [p for p in previous if int(p["sequenceNumber"]) == final_sequence]
        if len(final) != 1:
            continue
        action = final[0]
        pairs.append((action, recovery))
    return pairs


def link_return_fumbles(plays: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Find bounded cross-drive associations, keeping muff versus fumble unknown.

    Drive identifiers and sequence numbers establish order independently of the
    response array. Named returns allow at most 30 elapsed seconds in one period.
    An unnamed no-return punt requires the exact same clock and handoff position.
    These are disclosed associations, not independent source-truth verification.
    """
    links = []
    for action, recovery in drive_boundary_pairs(plays):
        family = {
            "Punt Return": "punt_return",
            "Kickoff Return (Offense)": "kickoff_return",
            "Pass Interception": "interception_return",
        }.get(action.get("type", {}).get("text"))
        if family is None:
            continue
        start, end = recovery.get("start", {}), action.get("end", {})
        owner = _team(start.get("team", {}))
        period = action.get("period", {}).get("number")
        action_clock, recovery_clock = _clock(action), _clock(recovery)
        if (
            owner is None
            or owner != _team(end.get("team", {}))
            or type(period) is not int
            or period < 1
            or period != recovery.get("period", {}).get("number")
            or type(start.get("yardLine")) is not int
            or not 0 <= start["yardLine"] <= 100
            or start["yardLine"] != end.get("yardLine")
            or start.get("down") != 1
            or action_clock is None
            or recovery_clock is None
            or not 0 <= action_clock - recovery_clock <= MAX_RETURN_SECONDS
            or action.get("isPenalty") is True
            or recovery.get("isPenalty") is True
        ):
            continue
        text = action.get("text") or ""
        pattern = (
            r"intercepted by (.+?) \(([^)]+)\)"
            if family == "interception_return"
            else r"returned\s+(?:-?\d+\s+yards?\s+)?by (.+?) \(([^)]+)\)"
        )
        carrier = re.search(pattern, text, re.I)
        fumbler = re.search(r"fumble by (.+?) \(([^)]+)\)", recovery.get("text") or "", re.I)
        if fumbler is None:
            continue
        if carrier is not None:
            if tuple(s.casefold() for s in carrier.groups()) != tuple(
                s.casefold() for s in fumbler.groups()
            ):
                continue
            basis = "named-returner-next-drive"
        elif (
            family == "punt_return"
            and "no return by " in text.casefold()
            and action_clock == recovery_clock
        ):
            basis = "unnamed-no-return-punt-same-clock-position"
        else:
            continue
        links.append(
            {
                "return_play": action["id"],
                "recovery": recovery["id"],
                "family": family,
                "fumble_team": owner,
                "basis": basis,
                "elapsed_seconds": action_clock - recovery_clock,
                "policy": RETURN_FUMBLE_POLICY,
                "muff_or_possessed_fumble": "unknown",
                "source_truth_verified": False,
            }
        )
    return links
