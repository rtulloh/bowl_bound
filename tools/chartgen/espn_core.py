"""Conservative adapter for archived ESPN core-v2 play records.

Older core feeds use statYardage for returns on kick records and often emit zero
for every starting yardsToEndzone. Neither is silently treated as kick distance
or field position. Unknown possession rows are counted instead of guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from .espn_fumbles import PRIMARY_FUMBLE_POLICY, link_primary_fumbles
from .espn_returns import RETURN_FUMBLE_POLICY, link_return_fumbles
from .evidence import Event, classify_espn
from .locations import enrich_interception_locations
from .optional_flags import OPTIONAL_FLAG_POLICY

ADAPTER = "espn-core-v2-conservative-v4"


def source_receipt(events: Sequence[Event], game_hashes: Mapping[str, str]) -> dict[str, Any]:
    """Bind a normalized cohort to each retained game's source bytes."""
    from .source import _optional_observations_sha256

    hashes = dict(game_hashes)
    return {
        "adapter": ADAPTER,
        "return_fumble_policy": RETURN_FUMBLE_POLICY,
        "primary_fumble_policy": PRIMARY_FUMBLE_POLICY,
        "url": "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football",
        "raw_sha256": hashlib.sha256(
            json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "game_source_sha256": hashes,
        "optional_flag_policy": OPTIONAL_FLAG_POLICY,
        "optional_flag_observations_sha256": _optional_observations_sha256(events),
    }


def _team(value: Mapping[str, Any]) -> str | None:
    reference = value.get("$ref", "")
    match = re.search(r"/teams/(\d+)(?:\?|$)", reference)
    return match.group(1) if match else None


def normalize_game(
    plays: Sequence[Mapping[str, Any]],
    *,
    season: int,
    game_id: str,
    teams: Mapping[str, str],
    source_sha256: str,
    home_team: str | None = None,
) -> tuple[list[Event], dict[str, Any]]:
    """Normalize one two-team game and retain measurable source limitations."""
    if len(teams) != 2:
        raise ValueError("core game requires exactly two identified teams")
    events = []
    receipt = {
        "adapter": ADAPTER,
        "source_rows": len(plays),
        "excluded_unknown_possession": 0,
        "unknown_kick_distance": 0,
    }
    for sequence, play in enumerate(plays, 1):
        start, end = play.get("start", {}), play.get("end", {})
        team = _team(start.get("team", {}))
        if team not in teams:
            receipt["excluded_unknown_possession"] += 1
            continue
        opponent = next(key for key in teams if key != team)
        kind = play.get("type", {})
        label = str(kind.get("text", ""))
        text = str(play.get("text") or "")
        if not label:
            narrative = text.lower()
            if "field goal" in narrative or "extra point" in narrative:
                label = "Field Goal" if "field goal" in narrative else "Extra Point"
                if "is good" in narrative:
                    label += " Good"
                elif any(token in narrative for token in ("no good", "missed", "blocked")):
                    label += " Missed"
        lower = label.lower()
        row = {
            "season": season,
            "game_id": game_id,
            "id": play["id"],
            # Core sequenceNumber restarts at every drive; preserve global input order.
            "game_play_number": sequence,
            "pos_team_id": team,
            "def_pos_team_id": opponent,
            "pos_team": teams[team],
            "def_pos_team": teams[opponent],
            "type.id": kind.get("id"),
            "type.text": label,
            "text": text,
            "statYardage": play.get("statYardage"),
            "clock.displayValue": play.get("clock", {}).get("displayValue"),
            "period.number": play.get("period", {}).get("number"),
            "down": start.get("down"),
            "distance": start.get("distance"),
            "end.team.id": _team(end.get("team", {})),
            "end.yardsToEndzone": end.get("yardsToEndzone"),
        }
        # yardLine uses the home team's goal as its origin. Require the end
        # coordinates to corroborate that orientation before using a start spot.
        end_team = row["end.team.id"]
        start_line, end_line = start.get("yardLine"), end.get("yardLine")
        if (
            home_team in teams
            and end_team in teams
            and type(start_line) is int
            and 0 < start_line < 100
            and type(end_line) is int
            and 0 <= end_line <= 100
            and end.get("yardsToEndzone") == (100 - end_line if end_team == home_team else end_line)
        ):
            row["start.yardsToEndzone"] = 100 - start_line if team == home_team else start_line
        if "interception" in lower:
            returned = re.search(r"returned\s+(?:for\s+)?(?:a\s+)?(-?\d+)\s+yard", text, re.I)
            if returned:
                row["yds_int_return"] = int(returned[1])
            elif "returned for no gain" in text.lower():
                row["yds_int_return"] = 0
        if "isPenalty" in play:
            row["isPenalty"] = play["isPenalty"]
        if "touchdown" in lower or (
            play.get("scoringPlay") is True
            and play.get("scoreValue") == 6
            and lower in {"rush", "pass completion"}
        ):
            row["touchdown"] = True
        if "fumble" in lower:
            row["fumble_vec"] = True
            recovery = _team(play.get("team", {}))
            if recovery in teams:
                row["recovery_team"] = recovery
                row["fumbling_team"] = team
        if "punt" in lower or "kickoff" in lower:
            prefix = "punt" if "punt" in lower else "kickoff"
            row["statYardage"] = None
            if "return" in lower and "no return" not in text.lower():
                row[f"yds_{prefix}_return"] = play.get("statYardage")
            # Only an explicit gross-distance phrase may supply the kick distance.
            distance = re.search(r"(?:punt|kickoff)(?:ed)?\s+(?:for\s+)?(\d+)\s+yards", text, re.I)
            if distance:
                row[f"yds_{'punted' if prefix == 'punt' else 'kickoff'}"] = int(distance[1])
            else:
                receipt["unknown_kick_distance"] += 1
        if "field goal" in lower:
            distance = re.search(r"(\d+)\s*(?:yard|yd)\s+field goal", text, re.I)
            if distance:
                row["yds_fg"] = int(distance[1])
        event = classify_espn(row)
        if event is not None:
            events.append(replace(event, optional_flag_source_sha256=source_sha256))
    events, receipt["return_fumbles"] = enrich_return_fumbles(events, plays)
    events, receipt["primary_fumbles"] = enrich_primary_fumbles(events, plays)
    events, receipt["interception_locations"] = enrich_interception_locations(events)
    return events, receipt


def enrich_return_fumbles(
    events: Sequence[Event], plays: Sequence[Mapping[str, Any]]
) -> tuple[list[Event], dict[str, Any]]:
    """Fold separate recovery evidence into return events once for chart fitting.

    Raw optional observations and narratives stay intact. The retained recovery
    row is marked no_play only to omit the duplicated fitting observation.
    """
    return _fold_fumbles(events, link_return_fumbles(plays), RETURN_FUMBLE_POLICY, primary=False)


def enrich_primary_fumbles(
    events: Sequence[Event], plays: Sequence[Mapping[str, Any]]
) -> tuple[list[Event], dict[str, Any]]:
    """Fold same-clock cross-drive primary recoveries without changing gains."""
    return _fold_fumbles(events, link_primary_fumbles(plays), PRIMARY_FUMBLE_POLICY, primary=True)


def _fold_fumbles(
    events: Sequence[Event], links: Sequence[Mapping[str, Any]], policy: str, *, primary: bool
) -> tuple[list[Event], dict[str, Any]]:
    by_id = {event.event_id: event for event in events}
    if len(by_id) != len(events):
        raise ValueError("duplicate normalized event identifier")
    applied = []
    for link in links:
        action = by_id.get(link["primary" if primary else "return_play"])
        recovery = by_id.get(link["recovery"])
        if (
            action is None
            or recovery is None
            or action.kind
            not in (
                {"rush", "complete", "sack"} if primary else {"punt", "kickoff", "interception"}
            )
            or (not primary and action.opponent != link["fumble_team"])
            or recovery.fumble is not True
        ):
            continue
        if "linked-recovery:" + recovery.event_id in action.recovery_evidence:
            applied.append(link)
            continue
        if action.fumble is not None or action.no_play or recovery.no_play:
            continue
        evidence = (
            policy,
            link["kind" if primary else "family"],
            "same-clock-context-carrier-next-drive" if primary else link["basis"],
        )
        by_id[action.event_id] = replace(
            action,
            fumble=True,
            fumble_count=1,
            fumble_team=action.team if primary else link["fumble_team"],
            recovery_team=recovery.recovery_team,
            fumble_lost=recovery.fumble_lost,
            recovery_confidence=recovery.recovery_confidence,
            provider_recovery_team=recovery.provider_recovery_team,
            recovery_evidence=(
                *recovery.recovery_evidence,
                *evidence,
                "linked-recovery:" + recovery.event_id,
            ),
        )
        by_id[recovery.event_id] = replace(
            recovery,
            no_play=True,
            event_phase="kick" if action.kind in {"punt", "kickoff"} else "scrimmage",
            recovery_evidence=(
                *recovery.recovery_evidence,
                *evidence,
                ("folded-into-primary:" if primary else "folded-into-return:") + action.event_id,
            ),
        )
        applied.append(link)
    return [by_id[event.event_id] for event in events], {
        "policy": policy,
        "links": applied,
    }
