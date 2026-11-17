"""Blocked-kick recovery movement differs from statistical punting credit."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.models import ResultKind, SpecialTeamsColumn
from tests.chartgen.test_generation import events as events
from tools.chartgen.evidence import Event, classify_espn
from tools.chartgen.generate import generate_team
from tools.chartgen.source import read_normalized, write_normalized


def blocked_event(**changes: object) -> Event:
    original = Event(
        2002, "fictional", "block", "1", "2", "Cedar Valley", "Harbor Tech", "punt", 0, blocked=True
    )
    return Event.from_dict(original.to_dict() | changes)


def test_missing_physical_movement_stays_unknown_on_legacy_upgrade() -> None:
    legacy = blocked_event().to_dict()
    legacy.pop("blocked_kick_yards", None)
    restored = Event.from_dict(legacy)
    assert restored.yards == 0
    assert restored.blocked_kick_yards is None


@pytest.mark.parametrize("value", [False, True, 1.5, "-15"])
def test_physical_movement_requires_integer_yards(value: object) -> None:
    with pytest.raises(ValueError, match="integer"):
        blocked_event(blocked_kick_yards=value)


@pytest.mark.parametrize("changes", [{"blocked": False}, {"kind": "rush"}])
def test_blocked_movement_cannot_describe_another_mechanism(changes: dict) -> None:
    with pytest.raises(ValueError, match="blocked punt"):
        blocked_event(blocked_kick_yards=-15, **changes)


def test_normalized_roundtrip_and_schema_separation(tmp_path: Path) -> None:
    event = blocked_event(blocked_kick_yards=-15)
    source = {"adapter": "fictional", "raw_sha256": "a" * 64}
    target = tmp_path / "normalized.json"
    write_normalized(target, [event], source)
    document = json.loads(target.read_text())
    assert document["schema_version"] == 6
    assert read_normalized(target) == ([event], source)
    document["schema_version"] = 5
    target.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="schema 6"):
        read_normalized(target)
    document["events"][0].pop("blocked_kick_yards")
    document["events_sha256"] = hashlib.sha256(
        json.dumps(document["events"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    target.write_text(json.dumps(document))
    restored, _ = read_normalized(target)
    assert restored[0].blocked_kick_yards is None
    assert restored[0].yards == 0


@pytest.mark.parametrize("movement", [-15, 0, 4])
def test_generator_uses_initial_physical_movement_without_changing_stat_credit(
    events: list[Event],
    movement: int,
) -> None:
    source = [
        Event.from_dict(e.to_dict() | {"blocked": True, "yards": 0, "blocked_kick_yards": movement})
        if e.kind == "punt" and e.team == "1" and int(e.event_id.split("-")[-1]) % 3 == 0
        else e
        for e in events
    ]
    chart, _, report = generate_team(source, "1", "Cedar Valley", 2007)
    locations = [
        r.cell.yards
        for r in chart.special_teams
        if r.column is SpecialTeamsColumn.PUNT and r.cell.kind is ResultKind.BLOCKED_KICK
    ]
    assert locations and set(locations) == {movement}
    assert all(e.yards == 0 for e in source if e.blocked)
    evidence = report["special_evidence"][SpecialTeamsColumn.PUNT.value]
    assert (
        evidence["blocked_location_policy"]
        == "explicit physical initial movement only; no statistical-credit or return-advance proxy"
    )
    assert evidence["known_blocked_locations"] == sum(e.blocked for e in source)
    assert evidence["unknown_blocked_locations"] == 0


@pytest.mark.parametrize("credit", [0, -7, 1])
def test_generator_refuses_statistical_credit_as_physical_location(
    events: list[Event], credit: int
) -> None:
    source = [
        replace(e, blocked=True, yards=credit) if e.kind == "punt" and e.team == "1" else e
        for e in events
    ]
    with pytest.raises(ValueError, match="no known BK location evidence"):
        generate_team(source, "1", "Cedar Valley", 2007)


def test_unknown_team_locations_pool_only_known_blocked_punt_movements(events: list[Event]) -> None:
    source = [
        Event.from_dict(
            e.to_dict()
            | {"blocked": True, "yards": 0, "blocked_kick_yards": -18 if e.team == "2" else None}
        )
        if e.kind == "punt" and int(e.event_id.split("-")[-1]) % 3 == 0
        else e
        for e in events
    ]
    chart, _, report = generate_team(source, "1", "Cedar Valley", 2007)
    locations = [
        r.cell.yards
        for r in chart.special_teams
        if r.column is SpecialTeamsColumn.PUNT and r.cell.kind is ResultKind.BLOCKED_KICK
    ]
    assert locations and set(locations) == {-18}
    evidence = report["special_evidence"][SpecialTeamsColumn.PUNT.value]
    assert evidence["blocked_location_method"] == "league-PBP"
    assert evidence["known_blocked_locations"] == 0
    assert evidence["unknown_blocked_locations"] > 0
    assert evidence["modeled_blocked_location_samples"] == sum(
        e.blocked and e.team == "2" for e in source
    )
    assert all(e.blocked_kick_yards is None for e in source if e.team == "1")


def test_team_physical_locations_take_precedence_over_league_pool(events: list[Event]) -> None:
    source = [
        Event.from_dict(
            e.to_dict()
            | {"blocked": True, "yards": 0, "blocked_kick_yards": -15 if e.team == "1" else -18}
        )
        if e.kind == "punt" and int(e.event_id.split("-")[-1]) % 3 == 0
        else e
        for e in events
    ]
    chart, _, report = generate_team(source, "1", "Cedar Valley", 2007)
    locations = [
        r.cell.yards
        for r in chart.special_teams
        if r.column is SpecialTeamsColumn.PUNT and r.cell.kind is ResultKind.BLOCKED_KICK
    ]
    assert locations and set(locations) == {-15}
    evidence = report["special_evidence"][SpecialTeamsColumn.PUNT.value]
    assert evidence["blocked_location_method"] == "team-PBP"
    assert evidence["modeled_blocked_location_samples"] == evidence["known_blocked_locations"]


def test_league_location_pool_does_not_add_blocks_to_unblocked_team(events: list[Event]) -> None:
    source = [
        Event.from_dict(e.to_dict() | {"blocked": True, "blocked_kick_yards": -18})
        if e.kind == "punt" and e.team == "2"
        else e
        for e in events
    ]
    chart, _, report = generate_team(source, "1", "Cedar Valley", 2007)
    assert not any(
        r.cell.kind is ResultKind.BLOCKED_KICK
        for r in chart.special_teams
        if r.column is SpecialTeamsColumn.PUNT
    )
    evidence = report["special_evidence"][SpecialTeamsColumn.PUNT.value]
    assert evidence["blocked_location_method"] == "unobserved"
    assert evidence["modeled_blocked_location_samples"] == 0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Team punt BLOCKED, recovered at CV25 and advanced five yards.", None),
        ("Team punt 0 yards, recovered at CV25 and advanced five yards.", None),
        ("Team punt 0 yards to CV40, recovered at CV25 and advanced five yards.", None),
        ("Team punt 1 yard to CV41 (blocked by Sam Example).", 1),
        ("Team punt -15 yards to CV25, returned five yards (blocked).", -15),
    ],
)
def test_adapter_uses_only_explicit_initial_kick_distance(text: str, expected: int | None) -> None:
    event = classify_espn(
        {
            "season": 2007,
            "game_id": "fictional",
            "id": "block",
            "pos_team_id": "1",
            "def_pos_team_id": "2",
            "pos_team": "Cedar Valley",
            "def_pos_team": "Harbor Tech",
            "type.text": "Blocked Punt",
            "text": text,
            "yds_punted": 0,
        }
    )
    assert event is not None
    assert event.yards == 0
    assert event.blocked_kick_yards == expected
    assert bool(event.location_evidence) is (expected is not None)
