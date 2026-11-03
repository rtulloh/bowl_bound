"""Private reviewer exports must describe the identical historical simulation slate."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.chartgen.cohort_report import validate_simulation_fixtures, write_matchup_report
from tools.chartgen.scope import build_slate, qualified_games, slate_targets

from .test_scope import events, game, members


def test_private_report_matches_targets_and_actual_fixtures(tmp_path: Path) -> None:
    schedule = [
        game("ab", "a", "b", date="2007-09-01", neutral_site=True),
        game("ac", "a", "c", date="2007-09-08"),
    ]
    source = events("ab", "a", "b") + events("ac", "a", "c")
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b", "c"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha", "beta"},
    )
    targets = slate_targets(source, slate)
    root = tmp_path / "private-data" / "review"
    report = write_matchup_report(
        root,
        slate,
        targets,
        source={"sha256": "1" * 64},
        engine={"sha256": "2" * 64},
        profiles_sha256="3" * 64,
        chart_qualifications={t: {"state": "generated"} for t in members()},
    )
    rows = list(csv.DictReader((root / "matchups.csv").open()))
    assert [r["game_id"] for r in rows] == ["ab", "ac"]
    assert len({r["game_id"] for r in rows}) == 2
    assert len(report["manifest_sha256"]) == 64
    assert rows[0]["manifest_sha256"] == report["manifest_sha256"]
    assert rows[0]["profiles_sha256"] == "3" * 64
    assert report["teams"]["a"]["full_source_game_ids"] == ["ab", "ac"]
    assert report == json.loads((root / "manifest.json").read_text())
    text = (root / "matchups.md").read_text()
    assert "Cedar Valley" in text and "Excluded" in text and "source-held-out" in text
    validate_simulation_fixtures(report, schedule * 2, repetitions=2)
    corrupted = json.loads((root / "manifest.json").read_text())
    corrupted["games"][0]["neutral_site"] = False
    with pytest.raises(ValueError, match="hash"):
        validate_simulation_fixtures(corrupted, schedule, repetitions=1)
    for bad in [
        replace(schedule[0], neutral_site=False),
        replace(schedule[0], season=2008),
        replace(schedule[0], away="c"),
        replace(schedule[0], game_id="invented"),
    ]:
        with pytest.raises(ValueError, match="fixture"):
            validate_simulation_fixtures(report, [bad, schedule[1]], repetitions=1)
    with pytest.raises(ValueError, match="exposure"):
        validate_simulation_fixtures(report, schedule[:1], repetitions=1)
    with pytest.raises(ValueError, match="new"):
        write_matchup_report(
            root, slate, targets, source={}, engine={}, profiles_sha256="", chart_qualifications={}
        )


def test_report_rejects_target_game_leakage(tmp_path: Path) -> None:
    schedule = [game("ab", "a", "b")]
    source = events("ab", "a", "b")
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha"},
    )
    targets = slate_targets(source, slate)
    targets["a"]["game_ids"].append("omitted")
    with pytest.raises(ValueError, match="target"):
        write_matchup_report(
            tmp_path / "private-data" / "bad",
            slate,
            targets,
            source={},
            engine={},
            profiles_sha256="",
            chart_qualifications={},
        )
