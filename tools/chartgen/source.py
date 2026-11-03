"""Versioned, checksummed evidence files and optional raw-source adapters."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .evidence import Event, classify_espn, summarize_events

ESPN_FIELDS = (
    "season",
    "game_id",
    "id",
    "pos_team_id",
    "def_pos_team_id",
    "pos_team",
    "def_pos_team",
    "text",
    "type.text",
    "rush",
    "pass",
    "pass_attempt",
    "completion",
    "sack",
    "int",
    "yds_rushed",
    "yds_receiving",
    "yds_sacked",
    "statYardage",
    "punt_play",
    "punt",
    "kickoff_play",
    "fg_attempt",
    "xp_attempt",
    "yds_punted",
    "yds_kickoff",
    "yds_fg",
    "yds_punt_return",
    "yds_kickoff_return",
    "yds_int_return",
    "yds_fumble_return",
    "kicking_team",
    "fumble_vec",
    "fumble_or_muff",
    "fumble_lost",
    "recovery_team",
    "penalty_flag",
    "isPenalty",
    "penalty_declined",
    "penalty_all_declined",
    "penalty_no_play",
    "penalty_negated_play",
    "penalty_offset",
    "yds_penalty",
    "penalty_side",
    "clock.displayValue",
    "period.number",
    "down",
    "distance",
    "start.yardsToEndzone",
    "fg_made",
    "xp_made",
    "punt_blocked",
    "punt_tb",
    "punt_fair_catch",
    "punt_downed",
    "punt_oob",
    "punt_return_player_name",
    "kickoff_tb",
    "kickoff_fair_catch",
    "kickoff_downed",
    "kickoff_oob",
    "kickoff_return_player_name",
    "touchdown",
    "td_play",
)
REQUIRED_ESPN_FIELDS = {
    "season",
    "game_id",
    "id",
    "pos_team_id",
    "def_pos_team_id",
    "type.text",
    "text",
}


def _payload(events: Sequence[Event]) -> str:
    return json.dumps([event.to_dict() for event in events], sort_keys=True, separators=(",", ":"))


def _validate(events: Sequence[Event]) -> None:
    identities = [(event.game_id, event.event_id) for event in events]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate game/event identity in source; reconcile before generation")
    if any(not game or not event for game, event in identities):
        raise ValueError("source events need stable game and event identities")
    if not events:
        raise ValueError("source contains no identified events")


def write_normalized(path: Path, events: Sequence[Event], source: dict[str, Any]) -> None:
    _validate(events)
    encoded = _payload(events)
    value = {
        "schema_version": 1,
        "source": source,
        "events_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "events": [event.to_dict() for event in events],
    }
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def read_normalized(path: Path) -> tuple[list[Event], dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1:
        raise ValueError("unsupported normalized source schema")
    events = [Event.from_dict(row) for row in value["events"]]
    _validate(events)
    checksum = hashlib.sha256(_payload(events).encode()).hexdigest()
    if checksum != value.get("events_sha256"):
        raise ValueError("normalized source checksum differs")
    return events, value["source"]


def import_espn(path: Path, *, url: str) -> tuple[list[Event], dict[str, Any]]:
    """Read a local CSV or optional DuckDB Parquet snapshot; no network at runtime."""
    missing_fields: list[str] = []
    if path.suffix == ".parquet":
        try:
            import duckdb
        except ImportError as error:
            raise ValueError(
                "Parquet adapter requires optional duckdb; install .[generator]"
            ) from error
        connection = duckdb.connect()
        relation = connection.read_parquet(str(path))
        columns = set(relation.columns)
        if not REQUIRED_ESPN_FIELDS <= columns:
            raise ValueError("unsupported ESPN snapshot: required source fields are absent")
        names = [name for name in ESPN_FIELDS if name in columns]
        missing_fields = sorted(set(ESPN_FIELDS) - columns)
        relation.create_view("raw_events")
        projection = ",".join('"' + name + '"' for name in names)
        rows = [
            dict(zip(names, row, strict=True))
            for row in connection.sql(
                f"SELECT {projection} FROM raw_events ORDER BY game_id, id"
            ).fetchall()
        ]
        connection.close()
    elif path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not REQUIRED_ESPN_FIELDS <= set(reader.fieldnames or ()):
                raise ValueError("unsupported ESPN CSV: required source fields are absent")
            missing_fields = sorted(set(ESPN_FIELDS) - set(reader.fieldnames or ()))
            rows = list(reader)
    else:
        raise ValueError("ESPN source must be a local .csv or .parquet snapshot")
    events = [event for row in rows if (event := classify_espn(row)) is not None]
    _validate(events)
    return events, {
        "adapter": "cfbfastR-ESPN-v1",
        "url": url,
        "filename": path.name,
        "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "raw_rows": len(rows),
        "identified_events": len(events),
        "unidentified_rows_excluded": len(rows) - len(events),
        "missing_fields": missing_fields,
        "scope": "complete supplied snapshot; season includes its postseason",
        "terms_review": "operator must review provider and underlying data rights",
    }


def coverage_report(
    events: Sequence[Event],
    team: str,
    *,
    expected_games: Sequence[str] = (),
    official: dict[str, int] | None = None,
) -> dict[str, Any]:
    observed = summarize_events(events, team)
    games = sorted({e.game_id for e in events if team in {e.team, e.opponent}})
    deltas = {key: observed[key] - value for key, value in (official or {}).items()}
    missing, unexpected = (
        sorted(set(expected_games) - set(games)),
        sorted(set(games) - set(expected_games)),
    )
    return {
        "team": team,
        "observed": observed,
        "game_ids": games,
        "missing_games": missing,
        "unexpected_games": unexpected if expected_games else [],
        "expected_schedule_supplied": bool(expected_games),
        "official_totals_supplied": bool(official),
        "official_deltas": deltas,
        "historical_reconciliation_passed": bool(expected_games and official)
        and not missing
        and not unexpected
        and not any(deltas.values()),
    }
