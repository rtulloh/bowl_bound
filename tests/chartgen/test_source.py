"""Source provenance and completeness use original synthetic events."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.chartgen.evidence import Event
from tools.chartgen.source import coverage_report, import_espn, read_normalized, write_normalized


def test_normalized_roundtrip_and_provenance(tmp_path: Path) -> None:
    event = Event(2007, "g1", "e1", "1", "2", "Cedar Valley", "Harbor Tech", "rush", 9)
    path = tmp_path / "events.json"
    write_normalized(
        path, [event], {"url": "https://example.invalid/synthetic", "raw_sha256": "a" * 64}
    )
    events, source = read_normalized(path)
    assert events == [event] and source["raw_sha256"] == "a" * 64
    path.write_text(path.read_text().replace('"yards": 9', '"yards": 8'))
    with pytest.raises(ValueError, match="checksum"):
        read_normalized(path)


def test_duplicate_event_identity_rejected(tmp_path: Path) -> None:
    event = Event(2007, "g1", "e1", "1", "2", "Cedar Valley", "Harbor Tech", "rush", 9)
    with pytest.raises(ValueError, match="duplicate"):
        write_normalized(tmp_path / "e.json", [event, event], {})


def test_coverage_distinguishes_missing_games_and_aggregate_deltas() -> None:
    event = Event(2007, "g1", "e1", "1", "2", "Cedar Valley", "Harbor Tech", "rush", 9)
    report = coverage_report([event], "1", expected_games=["g1", "g2"], official={"rush_yards": 17})
    assert report["missing_games"] == ["g2"]
    assert report["official_deltas"]["rush_yards"] == -8
    assert not report["historical_reconciliation_passed"]


def test_normalized_source_files_are_owner_only(tmp_path: Path) -> None:
    event = Event(2007, "g1", "e1", "1", "2", "Cedar Valley", "Harbor Tech", "rush", 9)
    path = tmp_path / "source.json"
    write_normalized(path, [event], {})
    assert path.stat().st_mode & 0o777 == 0o600


def test_import_preserves_structured_feature_and_recovery_field_provenance(tmp_path: Path) -> None:
    row = {
        "season": 2007,
        "game_id": "fictional-game",
        "id": "e1",
        "pos_team_id": 1,
        "def_pos_team_id": 2,
        "type.text": "Rush",
        "text": "Runner rush for 7 yards.",
        "rush_direction": "middle",
        "yds_rushed": 7,
        "fumble_recovery_team": 2,
    }
    path = tmp_path / "source.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    events, source = import_espn(path, url="https://example.invalid/fictional-pbp.csv")
    assert events[0].rush_direction == "middle" and events[0].recovery_team is None
    assert events[0].provider_recovery_team == "2"
    assert events[0].recovery_confidence == "provider-inferred"
    assert "fumble_recovery_team" not in source["missing_fields"]
    assert source["adapter"] == "cfbfastR-ESPN-v4"
    assert source["family_policy"] == "bb-pbp-family-v2"
    assert source["raw_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_old_normalized_snapshot_checksum_is_verified_before_upgrade(tmp_path: Path) -> None:
    legacy = {
        "season": 2007,
        "game_id": "fictional-game",
        "event_id": "e1",
        "team": "1",
        "opponent": "2",
        "team_name": "Cedar Valley",
        "opponent_name": "Harbor Tech",
        "kind": "rush",
        "yards": 7,
        "called_family": None,
        "family_confidence": "unknown",
        "touchdown": False,
        "fumble": None,
        "fumble_lost": None,
        "recovery_team": None,
        "return_yards": None,
        "penalty": False,
        "penalty_declined": False,
        "no_play": False,
        "penalty_yards": None,
        "penalty_side": None,
        "out_of_bounds": None,
        "clock": None,
        "period": None,
        "down": None,
        "distance": None,
        "yards_to_goal": None,
        "kick_good": None,
        "blocked": False,
        "touchback": False,
        "source_text": "",
    }
    encoded = json.dumps([legacy], sort_keys=True, separators=(",", ":"))
    payload = {
        "schema_version": 1,
        "source": {"adapter": "legacy-fictional"},
        "events_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "events": [legacy],
    }
    path = tmp_path / "v1.json"
    original = json.dumps(payload)
    path.write_text(original)
    events, _ = read_normalized(path)
    assert path.read_text() == original
    assert events[0].classification_policy == "legacy-v1" and events[0].pass_depth is None
    newer = tmp_path / "v2.json"
    write_normalized(newer, events, payload["source"])
    assert json.loads(newer.read_text())["schema_version"] == 6
    assert read_normalized(newer)[0] == events
    legacy["yards"] = 8
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="checksum"):
        read_normalized(path)


def test_schema_three_recovery_semantics_are_not_silently_rewritten(tmp_path: Path) -> None:
    legacy = Event(
        2007,
        "g1",
        "e1",
        "1",
        "2",
        "Cedar Valley",
        "Harbor Tech",
        "rush",
        9,
        fumble=True,
        fumble_lost=True,
        recovery_team="1",
    ).to_dict()
    for field in (
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
        "optional_flag_policy",
        "optional_flag_observations",
        "optional_flag_evidence",
        "optional_flag_source_sha256",
        "blocked_kick_yards",
    ):
        del legacy[field]
    encoded = json.dumps([legacy], sort_keys=True, separators=(",", ":"))
    payload = {
        "schema_version": 3,
        "source": {"adapter": "legacy-fictional"},
        "events_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "events": [legacy],
    }
    path = tmp_path / "legacy-v3.json"
    path.write_text(json.dumps(payload))
    original = path.read_bytes()
    events, _ = read_normalized(path)
    assert path.read_bytes() == original
    assert events[0].recovery_policy == "legacy"
    assert events[0].fumble_lost is True and events[0].recovery_team == "1"
    assert events[0].net_possession_fumble_lost is None
