"""Source-neutral event facts and a conservative ESPN-derived PBP adapter.

An observed rush/pass is not an observed designed Bowl Bound call. Only explicit
narrative labels classify a family; generic events remain available to pooled
estimators without pretending they contain formation or route observations.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class Event:
    season: int
    game_id: str
    event_id: str
    team: str
    opponent: str
    team_name: str
    opponent_name: str
    kind: str
    yards: int | None
    called_family: int | None = None
    family_confidence: str = "unknown"
    touchdown: bool = False
    fumble: bool = False
    fumble_lost: bool | None = None
    recovery_team: str | None = None
    return_yards: int | None = None
    penalty: bool = False
    penalty_declined: bool = False
    no_play: bool = False
    penalty_yards: int | None = None
    penalty_side: str | None = None
    out_of_bounds: bool | None = None
    clock: str | None = None
    period: int | None = None
    down: int | None = None
    distance: int | None = None
    yards_to_goal: int | None = None
    kick_good: bool | None = None
    blocked: bool = False
    touchback: bool = False
    source_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Event:
        if set(value) != {field.name for field in fields(cls)}:
            raise ValueError("event fields differ from normalized schema version 1")
        event = cls(**value)
        if not event.team or not event.opponent or event.team == event.opponent:
            raise ValueError("event needs distinct team/opponent identities")
        if event.kind not in {
            "rush",
            "complete",
            "incomplete",
            "interception",
            "sack",
            "punt",
            "kickoff",
            "field_goal",
            "pat",
            "penalty",
            "other",
        }:
            raise ValueError("unknown normalized event kind")
        if event.yards is not None and type(event.yards) is not int:
            raise ValueError("yardage must be an integer or null")
        return event


def _flag(row: Mapping[str, Any], key: str) -> bool:
    value = row.get(key)
    return value is True or value == 1 or str(value).lower() in {"true", "1"}


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (ValueError, TypeError) as error:
        raise ValueError("numeric evidence must be an integer or null") from error
    if not math.isfinite(number) or number != int(number):
        raise ValueError("numeric evidence must be a finite integer")
    return int(number)


def _identity(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _yards(row: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if row.get(key) is not None and row.get(key) != "":
            return _int(row[key])
    return None


def classify_espn(row: Mapping[str, Any]) -> Event | None:
    """Adapt cfbfastR ESPN-derived fields; never infer missing yards as zero.

    Sacks precede pass/rush flags, which overlap in some snapshots. Scoring-play
    yardage is retained. A declined penalty does not negate a live-play result.
    Return/kick ownership uses explicit kicking/return fields when available.
    """
    team, opponent = _identity(row.get("pos_team_id")), _identity(row.get("def_pos_team_id"))
    if not team or not opponent or team == opponent:
        return None
    text = str(row.get("text") or "")
    label = str(row.get("type.text") or "").lower()
    lower = text.lower()
    sack = _flag(row, "sack") or label == "sack"
    interception = _flag(row, "int") or "interception" in label
    if sack:
        kind, yards = "sack", _yards(row, "yds_sacked", "statYardage")
        if yards is not None:
            yards = -abs(yards)
    elif _flag(row, "punt_play") or _flag(row, "punt") or "punt" in label:
        kind, yards = "punt", _yards(row, "yds_punted", "statYardage")
    elif _flag(row, "kickoff_play") or "kickoff" in label:
        kind, yards = "kickoff", _yards(row, "yds_kickoff", "statYardage")
    elif _flag(row, "fg_attempt") or "field goal" in label:
        kind, yards = "field_goal", _yards(row, "yds_fg")
    elif _flag(row, "xp_attempt") or "extra point" in label:
        kind, yards = "pat", None
    elif interception:
        kind, yards = "interception", None
    elif _flag(row, "pass") or _flag(row, "pass_attempt") or "pass" in label:
        completed = _flag(row, "completion") or label in {"pass completion", "passing touchdown"}
        kind = "complete" if completed else "incomplete"
        yards = _yards(row, "yds_receiving", "statYardage") if completed else None
    elif _flag(row, "rush") or "rush" in label:
        kind, yards = "rush", _yards(row, "yds_rushed", "statYardage")
    elif _flag(row, "penalty_flag") or label == "penalty":
        kind, yards = "penalty", None
    else:
        kind, yards = "other", None
    families = (
        [
            (r"\bcounter\b", 2),
            (r"\breverse\b", 3),
            (r"\bdraw\b", 4),
            (r"\boption\b", 5),
            (r"\b(?:plunge|dive)\b", 1),
        ]
        if kind == "rush"
        else [
            (r"\bscreen\b", 6),
            (r"\b(?:sprint out|rollout)\b", 7),
            (r"\bboot[ -]?leg\b", 8),
            (r"\bdrop[ -]?back\b", 9),
        ]
        if kind in {"complete", "incomplete", "interception", "sack"}
        else []
    )
    matches = [family for pattern, family in families if re.search(pattern, lower)]
    family = matches[0] if len(matches) == 1 else None
    returns = {
        "punt": "yds_punt_return",
        "kickoff": "yds_kickoff_return",
        "interception": "yds_int_return",
    }
    kicking = row.get("kicking_team")
    # String team names cannot replace stable numerical identities.
    if kind in {"punt", "kickoff", "field_goal", "pat"} and kicking is not None:
        if _identity(kicking) == opponent:
            team, opponent = opponent, team
    lost = row.get("fumble_lost")
    # Older bulk seasons leave derived PAT flags false for every event. The
    # unambiguous original event label carries stronger evidence than that default.
    good = None
    if kind in {"field_goal", "pat"}:
        if label in {"field goal good", "extra point good"}:
            good = True
        elif "missed" in label or "blocked" in label:
            good = False
        else:
            flag = "fg_made" if kind == "field_goal" else "xp_made"
            good = _flag(row, flag) if row.get(flag) is not None else None
    return Event(
        season=_int(row.get("season")) or 0,
        game_id=_identity(row.get("game_id")),
        event_id=_identity(row.get("id")),
        team=team,
        opponent=opponent,
        team_name=str(row.get("pos_team") or team),
        opponent_name=str(row.get("def_pos_team") or opponent),
        kind=kind,
        yards=yards,
        called_family=family,
        family_confidence="narrative" if family else "unknown",
        touchdown=_flag(row, "touchdown") or _flag(row, "td_play"),
        fumble=_flag(row, "fumble_vec") or _flag(row, "fumble_or_muff"),
        fumble_lost=None if lost is None else _flag(row, "fumble_lost"),
        recovery_team=_identity(row.get("recovery_team")) or None,
        return_yards=_yards(row, returns[kind])
        if kind in returns
        else _yards(row, "yds_fumble_return")
        if _flag(row, "fumble_vec")
        else None,
        penalty=_flag(row, "penalty_flag") or _flag(row, "isPenalty"),
        penalty_declined=_flag(row, "penalty_declined") or _flag(row, "penalty_all_declined"),
        no_play=_flag(row, "penalty_no_play")
        or _flag(row, "penalty_negated_play")
        or _flag(row, "penalty_offset"),
        penalty_yards=_yards(row, "yds_penalty"),
        penalty_side=str(row["penalty_side"]) if row.get("penalty_side") else None,
        out_of_bounds=True if "out-of-bounds" in lower or "out of bounds" in lower else None,
        clock=str(row["clock.displayValue"]) if row.get("clock.displayValue") else None,
        period=_int(row.get("period.number")),
        down=_int(row.get("down")),
        distance=_int(row.get("distance")),
        yards_to_goal=_int(row.get("start.yardsToEndzone")),
        kick_good=good,
        blocked=_flag(row, "punt_blocked") or "blocked" in label,
        touchback=_flag(row, "punt_tb") or _flag(row, "kickoff_tb"),
        source_text=text,
    )


def summarize_events(events: Iterable[Event], team: str) -> dict[str, Any]:
    """College totals with known-yardage denominators and no-play exclusion."""
    all_own = [event for event in events if event.team == team]
    own = [event for event in all_own if not event.no_play]
    counts: Counter[str] = Counter()
    games = {event.game_id for event in own}
    for event in own:
        counts[event.kind] += 1
        if event.kind in {"rush", "sack"}:
            counts["rush_attempts"] += 1
            if event.yards is not None:
                counts["rush_yards"] += event.yards
                counts["rush_yardage_samples"] += 1
        if event.kind in {"complete", "incomplete", "interception"}:
            counts["pass_attempts"] += 1
        if event.kind == "complete" and event.yards is not None:
            counts["pass_yards"] += event.yards
        if event.kind in {"rush", "sack", "complete", "punt", "kickoff", "field_goal"}:
            counts["unknown_yardage"] += event.yards is None
        counts["fumbles"] += event.fumble
        counts["fumbles_lost"] += event.fumble_lost is True
    counts["penalties"] = sum(event.penalty and not event.penalty_declined for event in all_own)
    return {
        **{
            key: counts[key]
            for key in (
                "rush_attempts",
                "rush_yards",
                "rush_yardage_samples",
                "pass_attempts",
                "pass_yards",
                "unknown_yardage",
                "fumbles",
                "fumbles_lost",
                "penalties",
            )
        },
        "completions": counts["complete"],
        "interceptions": counts["interception"],
        "sacks": counts["sack"],
        "games": len(games),
        "event_counts": dict(counts),
        "family_observations": dict(Counter(str(e.called_family) for e in own)),
    }
