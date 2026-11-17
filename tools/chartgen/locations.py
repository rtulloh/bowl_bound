"""Conservative PBP-only interception spots, without guessing mirrored end state.

SDV's v0.1.4 parser documents end distance against end possession and verifies
return-spot corrections against the next real snap. This original adapter uses
those field meanings with stricter identity/sequence guards; it is not a provider
runtime dependency or a promise that every historical spot is identifiable.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import replace

from .evidence import Event

LOCATION_POLICY = "bb-interception-spot-v1"


def _administrative(event: Event) -> bool:
    label = (event.source_type or "").strip().casefold()
    known = (
        re.fullmatch(
            r"timeout|end period|end of (?:(?:\d+(?:st|nd|rd|th)) )?"
            r"(?:quarter|period|half|game|regulation|overtime)",
            label,
        )
        is not None
    )
    return event.kind == "other" and known and not event.penalty and not event.no_play


def enrich_interception_locations(events: Sequence[Event]) -> tuple[list[Event], dict[str, int]]:
    """Retain direct evidence or reconstruct only verified same-game return spots.

    A receiver catch point x is the return's final point plus return yardage.
    With end distance measured for the new offense, the passing gain is
    start_distance + end_distance + return_yards - 100. Require exact agreement
    with the next consecutive real source event and preserve its ID in lineage.
    Missing/duplicate sequence, disputed spots, fouls, fumbles and end-zone
    consequences cannot silently produce a zero-distance interception.
    """
    games: dict[tuple[int, str], list[Event]] = defaultdict(list)
    identities = [(event.season, event.game_id, event.event_id) for event in events]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate source event identity; reconcile before location inference")
    for event in events:
        if not _administrative(event):
            games[event.season, event.game_id].append(event)
    successors: dict[tuple[int, str, str], Event] = {}
    for key, rows in games.items():
        numbers = [event.source_sequence for event in rows]
        if any(type(number) is not int for number in numbers) or len(numbers) != len(set(numbers)):
            continue
        ordered = sorted(rows, key=lambda event: event.source_sequence)
        for previous, following in zip(ordered, ordered[1:], strict=False):
            if following.source_sequence == previous.source_sequence + 1:
                successors[(*key, previous.event_id)] = following
    result = []
    counts: Counter[str] = Counter()
    for event in events:
        if event.kind != "interception":
            result.append(event)
            continue
        if (
            event.interception_yards is not None
            and event.air_yards is not None
            and event.interception_yards != event.air_yards
        ):
            raise ValueError(
                f"interception location evidence conflict in {event.game_id}/{event.event_id}"
            )
        direct = (
            event.interception_yards if event.interception_yards is not None else event.air_yards
        )
        following = successors.get((event.season, event.game_id, event.event_id))
        candidate = None
        if (
            following is not None
            and following.team == event.opponent
            and following.kind
            in {"rush", "complete", "incomplete", "interception", "sack", "punt", "field_goal"}
            and not following.no_play
            and event.end_team == event.opponent
            and event.end_yards_to_goal == following.yards_to_goal
            and event.yards_to_goal is not None
            and 0 <= event.yards_to_goal <= 100
            and event.end_yards_to_goal is not None
            and 0 <= event.end_yards_to_goal <= 100
            and event.return_yards is not None
            and not event.no_play
            and not (event.penalty and not event.penalty_declined)
            and not event.fumble
            and not event.touchdown
            and not event.touchback
            and "touchback" not in event.source_text.casefold()
        ):
            value = event.yards_to_goal + event.end_yards_to_goal + event.return_yards - 100
            if event.yards_to_goal - 100 <= value <= event.yards_to_goal + 10:
                candidate = value
        if candidate is not None and direct is not None and candidate != direct:
            raise ValueError(
                f"interception location evidence conflict in {event.game_id}/{event.event_id}"
            )
        if direct is not None:
            event = replace(
                event,
                interception_yards=direct,
                location_evidence=event.location_evidence or ("air_yards",),
            )
            counts["direct"] += 1
        elif candidate is not None:
            event = replace(
                event,
                interception_yards=candidate,
                location_evidence=(
                    "end-return-next-snap",
                    "start.yardsToEndzone",
                    "end.team.id",
                    "end.yardsToEndzone",
                    "yds_int_return",
                    "next-event:" + following.event_id,
                ),
            )
            counts["reconstructed"] += 1
        else:
            counts["unidentified"] += 1
        result.append(event)
    return result, {key: counts[key] for key in ("direct", "reconstructed", "unidentified")}
