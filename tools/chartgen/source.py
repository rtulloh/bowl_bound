"""Versioned, checksummed evidence files and optional raw-source adapters."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from .evidence import FAMILY_POLICY, RECOVERY_POLICY, Event, classify_espn, summarize_events
from .locations import LOCATION_POLICY, enrich_interception_locations
from .optional_flags import LEGACY_FLAG_POLICY, OPTIONAL_FLAG_POLICY, validate_optional_flags

ESPN_FIELDS = (
    "season",
    "game_id",
    "id",
    "game_play_number",
    "pos_team_id",
    "def_pos_team_id",
    "pos_team",
    "def_pos_team",
    "text",
    "type.text",
    "type.id",
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
    "change_of_pos_team",
    "pos_fumble_lost",
    "def_fumble_lost",
    "recovery_team",
    "recovery_team_2",
    "fumble_recovery_team",
    "fumbling_team",
    "pass_depth",
    "pass_direction",
    "rush_direction",
    "air_yards",
    "qb_scramble",
    "penalty_flag",
    "isPenalty",
    "penalty_declined",
    "penalty_all_declined",
    "penalty_no_play",
    "penalty_negated_play",
    "penalty_offset",
    "yds_penalty",
    "penalty_side",
    "penalty_type",
    "penalty_detail",
    "clock.displayValue",
    "period.number",
    "down",
    "distance",
    "start.yardsToEndzone",
    "end.team.id",
    "end.pos_team.id",
    "end.yardsToEndzone",
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


def _optional_observations_sha256(events: Sequence[Event]) -> str:
    value = [
        {
            "season": event.season,
            "game_id": event.game_id,
            "event_id": event.event_id,
            "policy": event.optional_flag_policy,
            "raw_sha256": event.optional_flag_source_sha256,
            "observations": [asdict(item) for item in event.optional_flag_observations],
            "basis": event.optional_flag_evidence,
        }
        for event in events
    ]
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _validate_optional_receipt(events: Sequence[Event], source: dict[str, Any]) -> None:
    for event in events:
        validate_optional_flags(
            event.optional_flag_policy,
            event.optional_flag_observations,
            event.optional_flag_source_sha256,
        )
    if source.get("adapter") in {
        "espn-core-v2-conservative-v1",
        "espn-core-v2-conservative-v2",
        "espn-core-v2-conservative-v3",
        "espn-core-v2-conservative-v4",
    }:
        if source["adapter"] in {
            "espn-core-v2-conservative-v2",
            "espn-core-v2-conservative-v3",
            "espn-core-v2-conservative-v4",
        }:
            from .espn_returns import RETURN_FUMBLE_POLICY

            expected = (
                "espn-cross-drive-return-fumble-v1"
                if source["adapter"] == "espn-core-v2-conservative-v2"
                else RETURN_FUMBLE_POLICY
            )
            if source.get("return_fumble_policy") != expected:
                raise ValueError("core source return-fumble policy differs")
        if source["adapter"] == "espn-core-v2-conservative-v4":
            from .espn_fumbles import PRIMARY_FUMBLE_POLICY

            if source.get("primary_fumble_policy") != PRIMARY_FUMBLE_POLICY:
                raise ValueError("core source primary-fumble policy differs")
        hashes = source.get("game_source_sha256")
        if (
            not isinstance(hashes, dict)
            or set(hashes) != {event.game_id for event in events}
            or any(
                not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in hashes.values()
            )
            or source.get("raw_sha256")
            != hashlib.sha256(
                json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            or source.get("optional_flag_policy") != OPTIONAL_FLAG_POLICY
            or any(
                event.optional_flag_policy != OPTIONAL_FLAG_POLICY
                or event.optional_flag_source_sha256 != hashes.get(event.game_id)
                for event in events
            )
            or source.get("optional_flag_observations_sha256")
            != _optional_observations_sha256(events)
        ):
            raise ValueError("core source evidence receipt differs")
        return
    bound = any(event.optional_flag_source_sha256 is not None for event in events)
    current_metadata = (
        source.get("adapter") == "cfbfastR-ESPN-v4" or "optional_flag_policy" in source
    )
    if bound or current_metadata:
        raw_sha256 = source.get("raw_sha256")
        if (
            source.get("adapter") != "cfbfastR-ESPN-v4"
            or source.get("optional_flag_policy") != OPTIONAL_FLAG_POLICY
            or not isinstance(raw_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", raw_sha256) is None
            or any(
                event.optional_flag_policy != OPTIONAL_FLAG_POLICY
                or event.optional_flag_source_sha256 != raw_sha256
                for event in events
            )
            or source.get("optional_flag_observations_sha256")
            != _optional_observations_sha256(events)
        ):
            raise ValueError("optional flag evidence receipt/policy/adapter differs")
    elif str(source.get("adapter", "")).startswith("cfbfastR-ESPN") and any(
        event.optional_flag_policy != LEGACY_FLAG_POLICY for event in events
    ):
        raise ValueError("optional flag evidence cannot inherit a legacy adapter receipt")


def write_normalized(path: Path, events: Sequence[Event], source: dict[str, Any]) -> None:
    _validate(events)
    _validate_optional_receipt(events, source)
    encoded = _payload(events)
    value = {
        "schema_version": 6,
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
    if value.get("schema_version") not in {1, 2, 3, 4, 5, 6}:
        raise ValueError("unsupported normalized source schema")
    # Verify the immutable serialized evidence before upgrading legacy defaults.
    encoded = json.dumps(value["events"], sort_keys=True, separators=(",", ":"))
    checksum = hashlib.sha256(encoded.encode()).hexdigest()
    if checksum != value.get("events_sha256"):
        raise ValueError("normalized source checksum differs")
    events = [Event.from_dict(row) for row in value["events"]]
    if value["schema_version"] < 6 and any(e.blocked_kick_yards is not None for e in events):
        raise ValueError("physical blocked-kick movement requires normalized schema 6")
    if value["schema_version"] < 5 and any(
        event.optional_flag_policy != LEGACY_FLAG_POLICY for event in events
    ):
        raise ValueError("optional flag evidence requires normalized schema 5")
    _validate(events)
    _validate_optional_receipt(events, value["source"])
    return events, value["source"]


def _file_read_identity(stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def _stable_source_bytes(path: Path) -> bytes:
    """Capture bytes while refusing an observed change within the read window."""
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as error:
        raise ValueError("ESPN source changed or became unavailable during import") from error
    if _file_read_identity(before) != _file_read_identity(after):
        raise ValueError("ESPN source changed during import")
    return content


def import_espn(path: Path, *, url: str) -> tuple[list[Event], dict[str, Any]]:
    """Read a local CSV or optional DuckDB Parquet snapshot; no network at runtime."""
    missing_fields: list[str] = []
    if path.suffix not in {".csv", ".parquet"}:
        raise ValueError("ESPN source must be a local .csv or .parquet snapshot")
    captured = _stable_source_bytes(path)
    raw_sha256 = hashlib.sha256(captured).hexdigest()
    if path.suffix == ".parquet":
        try:
            import duckdb
        except ImportError as error:
            raise ValueError(
                "Parquet adapter requires optional duckdb; install .[generator]"
            ) from error
        # DuckDB's path reader must never reopen the mutable original. Close the
        # private snapshot handle before handing its path to the optional codec.
        with tempfile.TemporaryDirectory(prefix="bb-chartgen-source-") as directory:
            snapshot = Path(directory) / "source.parquet"
            descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(captured)
            connection = duckdb.connect()
            try:
                relation = connection.read_parquet(str(snapshot))
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
            finally:
                connection.close()
    elif path.suffix == ".csv":
        with io.StringIO(captured.decode("utf-8-sig"), newline="") as stream:
            reader = csv.DictReader(stream)
            if not REQUIRED_ESPN_FIELDS <= set(reader.fieldnames or ()):
                raise ValueError("unsupported ESPN CSV: required source fields are absent")
            missing_fields = sorted(set(ESPN_FIELDS) - set(reader.fieldnames or ()))
            rows = list(reader)
    events = []
    for row in rows:
        try:
            event = classify_espn(row)
        except ValueError as error:
            raise ValueError(
                f"ESPN game {row.get('game_id')} event {row.get('id')}: {error}"
            ) from error
        if event is not None:
            events.append(replace(event, optional_flag_source_sha256=raw_sha256))
    _validate(events)
    events, locations = enrich_interception_locations(events)
    provenance = {
        "adapter": "cfbfastR-ESPN-v4",
        "optional_flag_policy": OPTIONAL_FLAG_POLICY,
        "optional_flag_observations_sha256": _optional_observations_sha256(events),
        "recovery_policy": RECOVERY_POLICY,
        "family_policy": FAMILY_POLICY,
        "location_policy": LOCATION_POLICY,
        "interception_locations": locations,
        "url": url,
        "filename": path.name,
        "raw_sha256": raw_sha256,
        "raw_rows": len(rows),
        "identified_events": len(events),
        "unidentified_rows_excluded": len(rows) - len(events),
        "missing_fields": missing_fields,
        "scope": "complete supplied snapshot; season includes its postseason",
        "terms_review": "operator must review provider and underlying data rights",
    }
    # Do this after enrichment and every metadata digest, immediately before the
    # successful return. Fully restored transient changes cannot affect parsing.
    if _stable_source_bytes(path) != captured:
        raise ValueError("ESPN source changed during import")
    return events, provenance


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
