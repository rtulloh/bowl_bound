"""Synthetic CSV metadata, independent of optional Parquet/network inputs."""

import csv
from pathlib import Path

import pytest

from tools.chartgen.cohort_sources import load_contracts


def table(path: Path, rows: list[dict[str, object]]) -> Path:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_season_specific_membership_and_actual_fixture_contract(tmp_path: Path) -> None:
    membership = table(
        tmp_path / "teams.csv",
        [
            {
                "season": 2007,
                "team_id": t,
                "team_id_source": "espn",
                "team_name": t,
                "subdivision_id": "cfb:fbs",
                "conference_id": "old-league",
            }
            for t in ["a", "b"]
        ],
    )
    groups = table(
        tmp_path / "groups.csv",
        [
            {"season": year, "group_id": "old-league", "name": name}
            for year, name in [(2007, "Original League"), (2008, "Renamed League")]
        ],
    )
    rows = [
        {
            "season": 2007,
            "game_id": "actual",
            "home_id": "a",
            "away_id": "b",
            "neutral_site": True,
            "completed": True,
            "season_type": "postseason",
            "start_date": "2008-01-01",
            "week": 16,
            "notes": "Fictional Bowl",
        }
    ]
    schedule = table(tmp_path / "games.csv", rows)
    contracts = load_contracts(membership, schedule, groups, season=2007)
    assert contracts.members["a"].conference_name == "Original League"
    assert contracts.games[0].game_id == "actual"
    assert contracts.games[0].postseason and contracts.games[0].neutral_site
    assert len(contracts.provenance["membership"]["sha256"]) == 64
    assert contracts.independent_membership_confirmation is False
    rows[0]["neutral_site"] = "unknown"
    table(schedule, rows)
    with pytest.raises(ValueError, match="neutral"):
        load_contracts(membership, schedule, groups, season=2007)


def test_raw_pbp_headers_must_match_canonical_sides_and_source_hash(tmp_path: Path) -> None:
    import hashlib

    from tools.chartgen.cohort_sources import HistoricalContracts, audit_espn_headers
    from tools.chartgen.scope import HistoricalGame

    rows = [
        {
            "game_id": "g",
            "season": 2007,
            "homeTeamId": "a",
            "awayTeamId": "b",
            "homeFinalScore": 21,
            "awayFinalScore": 17,
        }
    ]
    raw = table(tmp_path / "raw.csv", rows)
    contracts = HistoricalContracts({}, (HistoricalGame("g", 2007, "a", "b"),), {})
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    audit = audit_espn_headers(raw, contracts, expected_raw_sha256=digest)
    assert audit["games"]["g"]["canonical_sides_verified"]
    assert not audit["independent_official_confirmation"]
    with pytest.raises(ValueError, match="hash"):
        audit_espn_headers(raw, contracts, expected_raw_sha256="incorrect")
    rows[0]["homeTeamId"], rows[0]["awayTeamId"] = "b", "a"
    table(raw, rows)
    with pytest.raises(ValueError, match="canonical"):
        audit_espn_headers(
            raw, contracts, expected_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()
        )


def test_primary_override_preserves_raw_facts_and_cannot_invent_fixture(tmp_path: Path) -> None:
    import json

    from tools.chartgen.cohort_sources import HistoricalContracts, apply_primary_overrides
    from tools.chartgen.scope import HistoricalGame

    original = HistoricalContracts({}, (HistoricalGame("g", 2007, "a", "b"),), {})
    payload = {
        "schema_version": 1,
        "games": [
            {
                "game_id": "g",
                "season": 2007,
                "home": "a",
                "away": "b",
                "neutral_site": True,
                "classification": "conference_championship",
                "evidence": [
                    {
                        "url": "https://example.org/fictional-guide",
                        "sha256": "1" * 64,
                        "locator": "original fictional neutral championship fixture",
                    }
                ],
            }
        ],
    }
    path = tmp_path / "override.json"
    path.write_text(json.dumps(payload))
    updated = apply_primary_overrides(original, path)
    assert not original.games[0].neutral_site
    assert updated.games[0].neutral_site
    assert updated.games[0].classification == "conference_championship"
    assert updated.provenance["primary_overrides"]["changes"][0]["before"]["neutral_site"] is False
    assert updated.independent_membership_confirmation is False
    payload["games"][0]["away"] = "invented"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="identity"):
        apply_primary_overrides(original, path)
