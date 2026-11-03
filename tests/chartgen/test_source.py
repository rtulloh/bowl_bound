"""Source provenance and completeness use original synthetic events."""

from pathlib import Path

import pytest

from tools.chartgen.evidence import Event
from tools.chartgen.source import coverage_report, read_normalized, write_normalized


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
