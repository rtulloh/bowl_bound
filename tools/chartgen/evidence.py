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
from enum import Enum
from typing import Any

from .optional_flags import (
    AUTHORED_FLAG_POLICY,
    LEGACY_FLAG_POLICY,
    OPTIONAL_FLAG_POLICY,
    OptionalFlagObservation,
    observe_optional_flags,
    validate_optional_flags,
)

FAMILY_POLICY = "bb-pbp-family-v2"
RECOVERY_POLICY = "cfb-physical-recovery-v1"
BLOCKED_KICK_LOCATION_POLICY = "bb-explicit-blocked-kick-movement-v1"
_OPTIONAL_FLAG_FIELDS = {
    "optional_flag_policy",
    "optional_flag_observations",
    "optional_flag_evidence",
    "optional_flag_source_sha256",
}
_CONTEXT_FIELDS = {
    "recovery_policy",
    "net_possession_fumble_lost",
    "provider_recovery_team",
    "recovery_confidence",
    "recovery_team_2",
    "fumble_count",
    "event_phase",
    "try_points",
    "try_scoring_team",
    "prior_touchdown_mention",
    "provider_pos_fumble_lost",
    "provider_def_fumble_lost",
}
_V2_FIELDS = {
    "resolved_family",
    "pass_depth",
    "pass_direction",
    "rush_direction",
    "air_yards",
    "quarterback_scramble",
    "penalty_type",
    "family_evidence",
    "recovery_evidence",
    "classification_policy",
}
_LOCATION_FIELDS = {
    "source_sequence",
    "source_type",
    "end_team",
    "end_yards_to_goal",
    "interception_yards",
    "location_evidence",
    "fumble_team",
}


class FamilyConfidence(str, Enum):
    UNKNOWN = "unknown"
    NARRATIVE = "narrative"
    INFERRED_DEPTH = "inferred-depth"
    AMBIGUOUS = "ambiguous"


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
    fumble: bool | None = None
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
    resolved_family: int | None = None
    pass_depth: str | None = None
    pass_direction: str | None = None
    rush_direction: str | None = None
    air_yards: int | None = None
    quarterback_scramble: bool | None = None
    penalty_type: str | None = None
    family_evidence: tuple[str, ...] = ()
    recovery_evidence: tuple[str, ...] = ()
    classification_policy: str = FAMILY_POLICY
    source_sequence: int | None = None
    source_type: str | None = None
    end_team: str | None = None
    end_yards_to_goal: int | None = None
    interception_yards: int | None = None
    location_evidence: tuple[str, ...] = ()
    fumble_team: str | None = None
    recovery_policy: str = "legacy"
    net_possession_fumble_lost: bool | None = None
    provider_recovery_team: str | None = None
    recovery_confidence: str = "unknown"
    recovery_team_2: str | None = None
    fumble_count: int | None = None
    event_phase: str = "legacy"
    try_points: int | None = None
    try_scoring_team: str | None = None
    prior_touchdown_mention: bool = False
    provider_pos_fumble_lost: bool | None = None
    provider_def_fumble_lost: bool | None = None
    optional_flag_policy: str = AUTHORED_FLAG_POLICY
    optional_flag_observations: tuple[OptionalFlagObservation, ...] = ()
    optional_flag_evidence: tuple[str, ...] = ()
    optional_flag_source_sha256: str | None = None
    blocked_kick_yards: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Event:
        expected = {field.name for field in fields(cls)} - {"blocked_kick_yards"}
        supplied_fields = set(value) - {"blocked_kick_yards"}
        if supplied_fields not in (
            expected,
            expected - _OPTIONAL_FLAG_FIELDS,
            expected - _OPTIONAL_FLAG_FIELDS - _CONTEXT_FIELDS,
            expected - _OPTIONAL_FLAG_FIELDS - _CONTEXT_FIELDS - _LOCATION_FIELDS,
            expected - _OPTIONAL_FLAG_FIELDS - _CONTEXT_FIELDS - _LOCATION_FIELDS - _V2_FIELDS,
        ):
            raise ValueError("event fields differ from normalized schema version 1 through 6")
        supplied = dict(value)
        if "optional_flag_policy" not in supplied:
            supplied["optional_flag_policy"] = LEGACY_FLAG_POLICY
        observations = supplied.get("optional_flag_observations", ())
        if not isinstance(observations, (tuple, list)):
            raise ValueError("optional flag evidence must be a sequence")
        supplied["optional_flag_observations"] = tuple(
            OptionalFlagObservation.from_dict(item) for item in observations
        )
        if (
            supplied_fields
            == expected - _OPTIONAL_FLAG_FIELDS - _CONTEXT_FIELDS - _LOCATION_FIELDS - _V2_FIELDS
        ):
            supplied["classification_policy"] = "legacy-v1"
        for key in (
            "family_evidence",
            "recovery_evidence",
            "location_evidence",
            "optional_flag_evidence",
        ):
            lineage = supplied.get(key, ())
            if not isinstance(lineage, (tuple, list)) or any(
                not isinstance(item, str) or not item for item in lineage
            ):
                raise ValueError("event evidence lineage must contain field/label strings")
            supplied[key] = tuple(lineage)
        event = cls(**supplied)
        validate_optional_flags(
            event.optional_flag_policy,
            event.optional_flag_observations,
            event.optional_flag_source_sha256,
        )
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
        for key in (
            "yards",
            "air_yards",
            "interception_yards",
            "blocked_kick_yards",
            "end_yards_to_goal",
            "source_sequence",
        ):
            if getattr(event, key) is not None and type(getattr(event, key)) is not int:
                raise ValueError("yardage must be an integer or null")
        if event.blocked_kick_yards is not None and not (event.kind == "punt" and event.blocked):
            raise ValueError("physical blocked-kick movement requires a blocked punt")
        for key in ("called_family", "resolved_family"):
            number = getattr(event, key)
            if number is not None and (type(number) is not int or not 1 <= number <= 9):
                raise ValueError("family must be a Bowl Bound play 1..9 or null")
        FamilyConfidence(event.family_confidence)
        if event.classification_policy not in {FAMILY_POLICY, "legacy-v1"}:
            raise ValueError("unsupported family classification policy")
        for key in (
            "pass_depth",
            "pass_direction",
            "rush_direction",
            "penalty_type",
            "source_type",
            "end_team",
        ):
            if getattr(event, key) is not None and not isinstance(getattr(event, key), str):
                raise ValueError("structured feature labels must be strings or null")
        if event.recovery_team is not None and event.recovery_team not in {
            event.team,
            event.opponent,
        }:
            raise ValueError("recovery team identity must match offense or defense")
        if event.fumble_team is not None and event.fumble_team not in {event.team, event.opponent}:
            raise ValueError("fumbling team identity must match offense or defense")
        for name in ("provider_recovery_team", "recovery_team_2", "try_scoring_team"):
            if getattr(event, name) is not None and getattr(event, name) not in {
                event.team,
                event.opponent,
            }:
                raise ValueError(f"{name} identity must match offense or defense")
        if event.recovery_policy not in {"legacy", RECOVERY_POLICY}:
            raise ValueError("unsupported recovery policy")
        if event.recovery_confidence not in {
            "unknown",
            "provider-parsed",
            "provider-inferred",
            "primary-adjudicated",
        }:
            raise ValueError("unsupported recovery confidence")
        if event.event_phase not in {"legacy", "scrimmage", "try", "kick", "other"}:
            raise ValueError("unsupported event phase")
        if event.fumble_count is not None and (
            type(event.fumble_count) is not int or event.fumble_count < 0
        ):
            raise ValueError("fumble count must be a nonnegative integer or null")
        if event.try_points is not None and (
            type(event.try_points) is not int or event.try_points not in {0, 1, 2}
        ):
            raise ValueError("try points must be 0, 1, 2 or null")
        for name in (
            "touchdown",
            "penalty",
            "penalty_declined",
            "no_play",
            "blocked",
            "touchback",
            "prior_touchdown_mention",
        ):
            if type(getattr(event, name)) is not bool:
                raise ValueError("normalized flags must be booleans")
        for name in (
            "fumble",
            "fumble_lost",
            "out_of_bounds",
            "kick_good",
            "quarterback_scramble",
            "net_possession_fumble_lost",
            "provider_pos_fumble_lost",
            "provider_def_fumble_lost",
        ):
            if getattr(event, name) is not None and type(getattr(event, name)) is not bool:
                raise ValueError("normalized optional flags must be booleans or null")
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


def _optional_text(row: Mapping[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} evidence must be a string or null")
    return value


def _recovery_identity(
    row: Mapping[str, Any], team: str, opponent: str
) -> tuple[str | None, str | None, str, tuple[str, ...]]:
    evidence = tuple(
        key for key in ("recovery_team", "fumble_recovery_team") if row.get(key) not in (None, "")
    )
    values = {_identity(row[key]) for key in evidence}
    if any(value not in {team, opponent} for value in values):
        raise ValueError("recovery team identity must match offense or defense")
    if len(values) > 1:
        raise ValueError("conflicting recovery team fields; reconcile the source event")
    parsed = _identity(row.get("recovery_team")) or None
    provider = _identity(row.get("fumble_recovery_team")) or None
    lower = str(row.get("text") or "").casefold()
    # A TEAM bookkeeping placeholder or dead ball is not a physical recoverer.
    placeholder = re.search(r"recovered by\s+(?:the\s+)?team\b", lower) is not None
    dead_ball = ("out-of-bounds" in lower or "out of bounds" in lower) and "recover" not in lower
    if placeholder or dead_ball:
        return None, provider, "unknown", evidence + ("physical-recovery:unidentified",)
    if parsed is not None:
        return parsed, provider, "provider-parsed", evidence
    if provider is not None:
        return None, provider, "provider-inferred", ("provider-inferred:fumble_recovery_team",)
    return None, None, "unknown", evidence


def _family(
    kind: str, text: str, pass_depth: str | None
) -> tuple[int | None, int | None, str, tuple[str, ...]]:
    """Classify supported labels without equating direction with a designed call.

    Explicit narrative labels outrank depth inference. A generic dropback is not
    a Bowl Bound Long Pass. The policy deliberately has no NFL yard thresholds or
    direction-to-Counter/Option/formation mapping.
    """
    rush = (
        (r"\bcounter\b", 2, "counter"),
        (r"\breverse\b", 3, "reverse"),
        (r"\bdraw\b", 4, "draw"),
        (r"\boption\b", 5, "option"),
        (r"\b(?:plunge|dive)\b", 1, "plunge-dive"),
    )
    passing = (
        (r"\bscreen\b", 6, "screen"),
        (r"\b(?:sprint[ -]?out|roll[ -]?out)\b", 7, "sprint-out"),
        (r"\bboot[ -]?leg\b", 8, "bootleg"),
        (r"\b(?:long|deep) pass\b", 9, "long-pass"),
    )
    is_pass = kind in {"complete", "incomplete", "interception", "sack"}
    patterns = rush if kind == "rush" else passing if is_pass else ()
    matches = [
        (family, "text:" + label) for pattern, family, label in patterns if re.search(pattern, text)
    ]
    option = is_pass and re.search(r"\boption\b", text) is not None
    if option and len(matches) == 1 and matches[0][0] in {7, 8}:
        return 5, matches[0][0], "narrative", ("text:option", matches[0][1])
    if len(matches) > 1 or option:
        evidence = tuple(label for _, label in matches) + (("text:option",) if option else ())
        return None, None, "ambiguous", evidence
    if matches:
        family, label = matches[0]
        return family, family, "narrative", (label,)
    if is_pass and pass_depth is not None and pass_depth.strip().casefold() == "deep":
        return 9, 9, "inferred-depth", ("pass_depth",)
    return None, None, "unknown", ()


def classify_espn(row: Mapping[str, Any]) -> Event | None:
    """Adapt cfbfastR ESPN-derived fields; never infer missing yards as zero.

    Sacks precede pass/rush flags, which overlap in some snapshots. Scoring-play
    yardage is retained. A declined penalty does not negate a live-play result.
    Return/kick ownership uses explicit kicking/return fields when available.
    """
    team, opponent = _identity(row.get("pos_team_id")), _identity(row.get("def_pos_team_id"))
    if not team or not opponent or team == opponent:
        return None
    flag_observations = observe_optional_flags(row)
    optional = {item.field: item.value for item in flag_observations}
    flag_evidence = []
    text = str(row.get("text") or "")
    team_name, opponent_name = (
        str(row.get("pos_team") or team),
        str(row.get("def_pos_team") or opponent),
    )
    label = str(row.get("type.text") or "").lower()
    lower = text.lower()
    original_type = _identity(row.get("type.id"))
    original_pat = original_type in {"61", "62"}
    defensive_try = "defensive" in label and ("2pt" in label or "two" in label)
    is_pat = original_pat or _flag(row, "xp_attempt") or "extra point" in label
    is_try = (
        is_pat or defensive_try or "two-point" in label or "two point" in label or "2pt" in label
    )
    sack = _flag(row, "sack") or label == "sack"
    interception = _flag(row, "int") or "interception" in label
    if is_try:
        kind, yards = ("pat" if is_pat and not defensive_try else "other"), None
    elif sack:
        kind, yards = "sack", _yards(row, "yds_sacked", "statYardage")
        if yards is not None:
            yards = -abs(yards)
    elif _flag(row, "punt_play") or _flag(row, "punt") or "punt" in label:
        kind, yards = "punt", _yards(row, "yds_punted", "statYardage")
    elif _flag(row, "kickoff_play") or "kickoff" in label:
        kind, yards = "kickoff", _yards(row, "yds_kickoff", "statYardage")
    elif _flag(row, "fg_attempt") or "field goal" in label:
        kind, yards = "field_goal", _yards(row, "yds_fg")
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
    depth = _optional_text(row, "pass_depth")
    family, resolved_family, confidence, family_evidence = _family(kind, lower, depth)
    returns = {
        "punt": "yds_punt_return",
        "kickoff": "yds_kickoff_return",
        "interception": "yds_int_return",
    }
    return_yards = (
        _yards(row, returns[kind])
        if kind in returns
        else (_yards(row, "yds_fumble_return") if optional["fumble_vec"] is True else None)
    )
    if kind in {"punt", "kickoff"}:
        prefix = "punt" if kind == "punt" else "kickoff"
        non_return = any(
            _flag(row, prefix + "_" + suffix) for suffix in ("tb", "fair_catch", "downed", "oob")
        ) or any(marker in lower for marker in ("touchback", "fair catch", "downed", "no return"))
        explicit_return = "return" in lower or bool(row.get(prefix + "_return_player_name"))
        if non_return or (return_yards == 0 and not explicit_return):
            return_yards = None
    kicking = row.get("kicking_team")
    # String team names cannot replace stable numerical identities.
    if kind in {"punt", "kickoff", "field_goal", "pat"} and kicking is not None:
        if _identity(kicking) == opponent:
            team, opponent = opponent, team
            team_name, opponent_name = opponent_name, team_name
    # A processed recovery-TD label may hide an original PAT row. Without a
    # kicking identity its pos_team can still describe the preceding snap.
    unknown_pat_owner = (
        original_pat and "extra point" not in label and _identity(kicking) not in {team, opponent}
    )
    if unknown_pat_owner:
        kind = "other"
    recovery_team, provider_recovery, recovery_confidence, recovery_evidence = _recovery_identity(
        row, team, opponent
    )
    second_recovery = _identity(row.get("recovery_team_2")) or None
    if second_recovery is not None and second_recovery not in {team, opponent}:
        raise ValueError("second recovery team identity must match offense or defense")
    fumble_team = _identity(row.get("fumbling_team")) or None
    if fumble_team is not None and fumble_team not in {team, opponent}:
        raise ValueError("fumbling team identity must match offense or defense")
    air_yards = _yards(row, "air_yards")
    fumble_values = (optional["fumble_vec"], optional["fumble_or_muff"])
    fumble = True if True in fumble_values else False if fumble_values == (False, False) else None
    flag_evidence.append("fumble:conservative-annotation-union")
    fumble_count = (
        max(
            1,
            len(re.findall(r"\bfumbl(?:ed|es|ing)\b", lower)),
            2 if second_recovery is not None else 0,
        )
        if fumble
        else (0 if fumble is False else None)
    )
    owner = fumble_team or (team if kind in {"rush", "complete", "sack"} and not is_try else None)
    first_lost = (
        recovery_team != owner
        if fumble and recovery_team is not None and owner is not None
        else None
    )
    # Older bulk seasons leave derived PAT flags false for every event. The
    # unambiguous original event label carries stronger evidence than that default.
    good = None
    if kind in {"field_goal", "pat"} or original_pat:
        if original_type == "61" or label in {"field goal good", "extra point good"}:
            good = True
            flag_evidence.append("type.id:61" if original_type == "61" else "type.text:" + label)
        elif original_type == "62" or "missed" in label or "blocked" in label:
            good = False
            flag_evidence.append("type.id:62" if original_type == "62" else "type.text:" + label)
        else:
            flag = "fg_made" if kind == "field_goal" else "xp_made"
            good = optional[flag]
            flag_evidence.append("provider-annotation:" + flag)
    scramble_narrative = re.search(r"\bscrambl(?:e|es|ed|ing)\b", lower) is not None
    if scramble_narrative:
        flag_evidence.append("text:scramble")
    blocked = _flag(row, "punt_blocked") or "blocked" in label
    initial_punt = re.search(
        r"\bpun(?:t|ts|ted)\s+(?:for\s+)?([+-]?\d+)\s+yards?\s+to\s+"
        r"(?:the\s+)?[a-z][a-z-]*\s*\d{1,2}\b",
        lower,
    )
    blocked_kick_yards = (
        int(initial_punt[1])
        if kind == "punt" and blocked and initial_punt and "recover" not in lower
        else None
    )
    return Event(
        season=_int(row.get("season")) or 0,
        game_id=_identity(row.get("game_id")),
        event_id=_identity(row.get("id")),
        team=team,
        opponent=opponent,
        team_name=team_name,
        opponent_name=opponent_name,
        kind=kind,
        yards=yards,
        called_family=family,
        family_confidence=confidence,
        touchdown=_flag(row, "touchdown") or _flag(row, "td_play"),
        fumble=fumble,
        fumble_lost=first_lost,
        recovery_team=recovery_team,
        return_yards=return_yards,
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
        blocked=blocked,
        blocked_kick_yards=blocked_kick_yards,
        touchback=_flag(row, "punt_tb") or _flag(row, "kickoff_tb"),
        source_text=text,
        resolved_family=resolved_family,
        pass_depth=depth,
        pass_direction=_optional_text(row, "pass_direction"),
        rush_direction=_optional_text(row, "rush_direction"),
        air_yards=air_yards,
        quarterback_scramble=True if scramble_narrative else optional["qb_scramble"],
        penalty_type=_optional_text(row, "penalty_type") or _optional_text(row, "penalty_detail"),
        family_evidence=family_evidence,
        recovery_evidence=recovery_evidence,
        source_sequence=_int(row.get("game_play_number")),
        source_type=str(row.get("type.text")) if row.get("type.text") else None,
        end_team=_identity(row.get("end.team.id")) or None,
        end_yards_to_goal=_yards(row, "end.yardsToEndzone"),
        interception_yards=air_yards if kind == "interception" else None,
        location_evidence=(BLOCKED_KICK_LOCATION_POLICY, "text:explicit-initial-punt-distance")
        if blocked_kick_yards is not None
        else ("air_yards",)
        if kind == "interception" and air_yards is not None
        else (),
        fumble_team=fumble_team,
        recovery_policy=RECOVERY_POLICY,
        net_possession_fumble_lost=optional["fumble_lost"],
        provider_recovery_team=provider_recovery,
        recovery_confidence=recovery_confidence,
        recovery_team_2=second_recovery,
        fumble_count=fumble_count,
        event_phase="try"
        if is_try
        else "kick"
        if kind in {"punt", "kickoff", "field_goal"}
        else "scrimmage"
        if kind in {"rush", "complete", "incomplete", "interception", "sack"}
        else "other",
        try_points=2 if defensive_try else (int(good) if is_pat and good is not None else None),
        try_scoring_team=opponent
        if defensive_try
        else team
        if is_pat and not unknown_pat_owner and good
        else None,
        prior_touchdown_mention=is_pat and "touchdown" in lower,
        provider_pos_fumble_lost=optional["pos_fumble_lost"],
        provider_def_fumble_lost=optional["def_fumble_lost"],
        optional_flag_policy=OPTIONAL_FLAG_POLICY,
        optional_flag_observations=flag_observations,
        optional_flag_evidence=tuple(flag_evidence),
    )


def summarize_events(events: Iterable[Event], team: str) -> dict[str, Any]:
    """College totals with known-yardage denominators and no-play exclusion."""
    all_events = list(events)
    all_own = [event for event in all_events if event.team == team]
    own = [event for event in all_own if not event.no_play]
    counts: Counter[str] = Counter()
    games = {event.game_id for event in own}
    for event in own:
        if event.event_phase == "try":
            counts["try_events"] += 1
            counts["pat"] += event.kind == "pat"
            continue
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
        counts["fumble_unknown_samples"] += event.fumble is None and event.event_phase != "try"
    # Kick events belong to the kicking team; a return fumbler can be its opponent.
    for event in all_events:
        if event.no_play or event.event_phase == "try" or (event.fumble_team or event.team) != team:
            continue
        counts["fumbles"] += event.fumble is True
        counts["fumbles_lost"] += event.fumble_lost is True
        counts["scrimmage_fumbles"] += (
            event.fumble is True
            and event.team == team
            and event.kind in {"rush", "sack", "complete", "incomplete", "interception"}
        )
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
                "scrimmage_fumbles",
                "fumble_unknown_samples",
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
