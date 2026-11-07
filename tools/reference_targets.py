"""Common provider observations for matched chart benchmarks.

These exact descriptive targets do not certify source completeness or identify
historical Bowl Bound calls. Unknown yardage/depth stays in its full population.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence, Set
from fractions import Fraction
from typing import Any, Literal

Event = Mapping[str, Any]
PASS = {"complete", "incomplete", "interception"}
MARKERS = {6: "text:screen", 7: "text:sprint-out", 8: "text:bootleg", 9: "text:drop-back"}


def _integer(value: Any) -> int | None:
    if value is not None and type(value) is not int:
        raise ValueError("source measurement requires integer yardage or explicit unknown")
    return value


def _metric(rows: Sequence[Event], values: Sequence[int | None]) -> dict[str, Any]:
    known = [value for value in values if value is not None]
    count, identified, numerator = len(rows), len(known), sum(known)
    games = Counter(row["game_id"] for row in rows)
    return {
        "eligible_events": count,
        "known_events": identified,
        "unknown_events": count - identified,
        "known_numerator": numerator,
        "point_observation": str(Fraction(numerator, count))
        if count and count == identified
        else None,
        "known_only_observation": str(Fraction(numerator, identified)) if identified else None,
        "game_ids": sorted(games),
        "events_per_game": dict(sorted(games.items())),
        "unknown_event_ids": [
            [row["game_id"], row["event_id"]]
            for row, value in zip(rows, values, strict=True)
            if value is None
        ],
    }


def _depth(rows: Sequence[Event]) -> dict[str, Any]:
    values, conflicts = [], 0
    for row in rows:
        direct, air = _integer(row.get("interception_yards")), _integer(row.get("air_yards"))
        if direct is not None and air is not None and direct != air:
            conflicts += 1
            values.append(None)
        else:
            values.append(direct if direct is not None else air)
    metric = _metric(rows, values)
    histogram = Counter(value for value in values if value is not None)
    total, unknown = len(rows), metric["unknown_events"]
    return {
        **metric,
        "known_only_mean": metric["known_only_observation"],
        "point_mean": metric["point_observation"],
        "known_histogram": dict(sorted(histogram.items())),
        "conflicting_depth_events": conflicts,
        "cdf": [
            {
                "depth": x,
                "lower": str(Fraction(sum(n for v, n in histogram.items() if v <= x), total)),
                "upper": str(
                    Fraction(sum(n for v, n in histogram.items() if v <= x) + unknown, total)
                ),
            }
            for x in sorted(histogram)
        ],
        "unknown_support": "unbounded; no inferred zero or universal depth cap",
        "cdf_scope": "observed atoms; bounds require no assumption about missing depths",
    }


def source_observations(
    events: Sequence[Event],
    *,
    team: str,
    game_ids: Set[str],
    role: Literal["offense", "defense"] = "offense",
) -> dict[str, Any]:
    """Describe one exact team/side population, shared by both chart sets.

    The caller must bind the original bytes and canonical conditioned population.
    No reference chart, simulated call mix or fitted tolerance is consumed here.
    """
    if role not in {"offense", "defense"} or type(team) is not str or not team:
        raise ValueError("source observation requires a team and offense/defense role")
    if any(type(game) is not str or not game for game in game_ids):
        raise ValueError("source game IDs must be nonempty strings")
    selected, identities = [], set()
    for row in events:
        if row.get("game_id") not in game_ids:
            continue
        if any(
            type(row.get(key)) is not str or not row[key]
            for key in ("game_id", "event_id", "team", "opponent", "kind")
        ):
            raise ValueError("source event requires explicit string identity, owner and kind")
        if type(row.get("no_play")) is not bool:
            raise ValueError("source no-play state must be explicit boolean")
        identity = row["game_id"], row["event_id"]
        if identity in identities:
            raise ValueError("duplicate source event identity")
        identities.add(identity)
        selected.append(row)
    live = [
        row
        for row in selected
        if not row["no_play"] and (row.get("event_phase") != "try" or row["kind"] == "pat")
    ]
    side = "team" if role == "offense" else "opponent"
    primary = [row for row in live if row[side] == team and row["kind"] != "pat"]
    attempts = [row for row in primary if row["kind"] in PASS]
    drops = [row for row in primary if row["kind"] in PASS | {"sack"}]
    rush = [row for row in primary if row["kind"] == "rush"]
    ncaa = [row for row in primary if row["kind"] in {"rush", "sack"}]
    completed = [row for row in primary if row["kind"] == "complete"]
    interceptions = [row for row in primary if row["kind"] == "interception"]
    metrics = {
        "completion": _metric(attempts, [int(row["kind"] == "complete") for row in attempts]),
        "interception": _metric(attempts, [int(row["kind"] == "interception") for row in attempts]),
        "sack": _metric(drops, [int(row["kind"] == "sack") for row in drops]),
        "pure_rush_yards": _metric(rush, [_integer(row.get("yards")) for row in rush]),
        "ncaa_rush_yards": _metric(ncaa, [_integer(row.get("yards")) for row in ncaa]),
        "completion_yards": _metric(completed, [_integer(row.get("yards")) for row in completed]),
        "pass_yards_per_attempt": _metric(
            attempts,
            [_integer(row.get("yards")) if row["kind"] == "complete" else 0 for row in attempts],
        ),
    }
    special = {}
    for kind in ("punt", "kickoff", "interception"):
        if kind != "interception":
            rows = [row for row in live if row["team"] == team and row["kind"] == kind]
            special[f"{kind}_distance"] = _metric(
                rows, [_integer(row.get("yards")) for row in rows]
            )
        rows = [row for row in live if row["opponent"] == team and row["kind"] == kind]
        special[f"{kind}_return"] = _metric(
            rows, [_integer(row.get("return_yards")) for row in rows]
        )
    pats = [row for row in live if row["team"] == team and row["kind"] == "pat"]
    if any(row.get("kick_good") is not None and type(row["kick_good"]) is not bool for row in pats):
        raise ValueError("provider PAT status must be boolean or explicit unknown")
    special["pat_good"] = _metric(
        pats, [int(row["kick_good"]) if row.get("kick_good") is not None else None for row in pats]
    )
    return {
        "schema_version": 1,
        "team": team,
        "role": role,
        "requested_game_ids": sorted(game_ids),
        "missing_input_game_ids": sorted(set(game_ids) - {row["game_id"] for row in selected}),
        "eligible_team_live_kind_counts": dict(
            sorted(Counter(row["kind"] for row in primary).items())
        ),
        "primary": metrics,
        "special": special,
        "interception_depth": _depth(interceptions),
        "designed_call_depth": {
            str(play): _depth(
                [
                    row
                    for row in interceptions
                    if row.get("called_family") == play
                    and row.get("family_confidence") == "narrative"
                    and marker in row.get("family_evidence", ())
                ]
            )
            for play, marker in MARKERS.items()
        },
        "source_qualification": "UNVERIFIED",
        "limits": [
            "Provider observations and legacy annotations are not independent "
            "completeness evidence.",
            "Special returns attach to actual receiver; primary side is explicit and separate.",
            "PAT good/miss are provider observations, not qualified mechanism targets.",
            "Generic deep passes are not designed-call evidence; call/formation "
            "frequencies remain unknown.",
            "Fumble mechanism, charged-FGA, OOB completeness and historical "
            "score/pace qualification are absent.",
            "Per-game counts permit later cluster analysis; no play-independent confidence claim.",
        ],
    }
