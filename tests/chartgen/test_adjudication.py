"""Checked source adjudication uses fictional local evidence, never network or charts."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from tools.chartgen.adjudication import apply_adjudications
from tools.chartgen.evidence import Event, classify_espn
from tools.chartgen.source import read_normalized, write_normalized


def encoded_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def fixture(tmp_path: Path) -> tuple[Event, dict[str, object], Path, dict[str, object]]:
    row = {
        "season": 2007,
        "game_id": "fictional-game",
        "id": "snap",
        "pos_team_id": "1",
        "def_pos_team_id": "2",
        "pos_team": "Cedar Valley",
        "def_pos_team": "Harbor Tech",
        "type.text": "Sack",
        "sack": True,
        "text": "Team snap over the intended passer, ball out of the endzone for a safety.",
        "yds_sacked": -8,
        "fumble_vec": True,
        "fumble_lost": True,
        "fumbling_team": "1",
        "fumble_recovery_team": "1",
    }
    event = classify_espn(row)
    assert event is not None
    source = {"raw_sha256": "a" * 64, "url": "https://example.invalid/source.csv"}
    evidence = tmp_path / "fictional-gamebook.txt"
    evidence.write_text("The center snapped the ball through the endzone. No physical recovery.")
    manifest = {
        "schema_version": 1,
        "raw_sha256": source["raw_sha256"],
        "corrections": [
            {
                "season": 2007,
                "game_id": event.game_id,
                "event_id": event.event_id,
                "expected_event_sha256": encoded_hash(event.to_dict()),
                "changes": {
                    "kind": "other",
                    "yards": None,
                    "event_phase": "other",
                    "recovery_team": None,
                    "fumble_lost": None,
                },
                "reason": (
                    "Primary gamebook establishes an errant snap; "
                    "no observed sack or physical recoverer."
                ),
                "context": {
                    "origin": "errant-snap",
                    "physical_recovery": "none-dead-ball",
                    "resulting_score": "safety",
                    "scoring_is_engine_outcome": True,
                },
                "evidence": [
                    {
                        "url": "https://example.invalid/gamebook",
                        "path": evidence.name,
                        "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                    }
                ],
            }
        ],
    }
    path = tmp_path / "adjudications.json"
    path.write_text(json.dumps(manifest))
    return event, source, path, manifest


def test_checked_adjudication_retains_original_and_evidence_receipt(tmp_path: Path) -> None:
    original, source, path, manifest = fixture(tmp_path)
    original_dict, original_source = original.to_dict(), deepcopy(source)
    events, corrected_source = apply_adjudications([original], source, path)
    assert original.to_dict() == original_dict and source == original_source
    corrected = events[0]
    assert corrected.kind == "other" and corrected.yards is None
    assert corrected.fumble is True and corrected.recovery_team is None
    assert corrected.net_possession_fumble_lost is True
    assert corrected.source_text == original.source_text
    receipt = corrected_source["adjudication"]["corrections"][0]
    assert receipt["original"] == json.loads(json.dumps(original_dict))
    assert receipt["corrected_sha256"] == encoded_hash(corrected.to_dict())
    assert receipt["evidence"] == manifest["corrections"][0]["evidence"]
    assert receipt["context"]["scoring_is_engine_outcome"] is True
    assert (
        corrected_source["adjudication"]["manifest_sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    destination = tmp_path / "normalized.json"
    write_normalized(destination, events, corrected_source)
    assert read_normalized(destination) == (events, corrected_source)


def test_blocked_location_adjudication_preserves_credit_and_later_advance(tmp_path: Path) -> None:
    original, source, path, manifest = fixture(tmp_path)
    original = replace(original, kind="punt", yards=0, blocked=True, return_yards=5)
    correction = manifest["corrections"][0]
    correction["expected_event_sha256"] = encoded_hash(original.to_dict())
    correction["changes"] = {"blocked_kick_yards": -15}
    correction["context"] = {"snap": "CV40", "initial_recovery": "CV25", "later_advance": 5}
    correction["reason"] = "Explicit initial recovery spot is fifteen yards behind scrimmage."
    evidence = tmp_path / correction["evidence"][0]["path"]
    evidence.write_text("Fourth down CV40: punt blocked; recovered at CV25, advanced to CV30.")
    correction["evidence"][0]["sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    corrected, receipt = apply_adjudications([original], source, path)
    assert original.blocked_kick_yards is None
    assert corrected[0].blocked_kick_yards == -15
    assert corrected[0].yards == 0 and corrected[0].return_yards == 5
    assert (
        "adjudication:" + receipt["adjudication"]["manifest_sha256"]
        in corrected[0].location_evidence
    )


@pytest.mark.parametrize(
    "mutation, match",
    [
        ("raw", "source hash"),
        ("event", "event hash"),
        ("evidence", "evidence hash"),
        ("unknown", "unknown event"),
        ("duplicate", "duplicate"),
        ("opponent", "identit"),
        ("text", "unsupported correction"),
        ("invalid_kind", "unknown normalized"),
        ("no_evidence", "evidence"),
        ("empty_changes", "changes"),
        ("bad_url", "URL"),
    ],
)
def test_adjudication_rejects_unverified_or_unbounded_changes(
    tmp_path: Path,
    mutation: str,
    match: str,
) -> None:
    original, source, path, manifest = fixture(tmp_path)
    correction = manifest["corrections"][0]
    if mutation == "raw":
        manifest["raw_sha256"] = "b" * 64
    elif mutation == "event":
        correction["expected_event_sha256"] = "b" * 64
    elif mutation == "evidence":
        correction["evidence"][0]["sha256"] = "b" * 64
    elif mutation == "unknown":
        correction["event_id"] = "absent"
    elif mutation == "duplicate":
        manifest["corrections"].append(deepcopy(correction))
    elif mutation == "opponent":
        correction["changes"]["opponent"] = "3"
    elif mutation == "text":
        correction["changes"]["source_text"] = "Replace the original."
    elif mutation == "invalid_kind":
        correction["changes"]["kind"] = "safety_chart"
    elif mutation == "no_evidence":
        correction["evidence"] = []
    elif mutation == "empty_changes":
        correction["changes"] = {}
    elif mutation == "bad_url":
        correction["evidence"][0]["url"] = "file:///private/source"
    path.write_text(json.dumps(manifest))
    before, source_before = original.to_dict(), deepcopy(source)
    with pytest.raises(ValueError, match=match):
        apply_adjudications([original], source, path)
    assert original.to_dict() == before and source == source_before


def test_correction_can_swap_only_known_sides_with_matching_names(tmp_path: Path) -> None:
    original, source, path, manifest = fixture(tmp_path)
    manifest["corrections"][0]["changes"] = {
        "team": "2",
        "opponent": "1",
        "team_name": "Harbor Tech",
        "opponent_name": "Cedar Valley",
        "kind": "pat",
        "event_phase": "try",
        "yards": None,
        "kick_good": True,
        "try_points": 1,
        "try_scoring_team": "2",
        "prior_touchdown_mention": True,
    }
    path.write_text(json.dumps(manifest))
    corrected, _ = apply_adjudications([original], source, path)
    assert corrected[0].team == "2" and corrected[0].opponent == "1"
    assert corrected[0].source_text == original.source_text
    manifest["corrections"][0]["changes"]["team_name"] = "Invented"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="identit"):
        apply_adjudications([original], source, path)


def test_adjudicated_recoverer_recomputes_first_physical_loss(tmp_path: Path) -> None:
    original, source, path, manifest = fixture(tmp_path)
    manifest["corrections"][0]["changes"] = {"recovery_team": "2"}
    path.write_text(json.dumps(manifest))
    corrected, _ = apply_adjudications([original], source, path)
    assert corrected[0].recovery_team == "2"
    assert corrected[0].fumble_lost is True
    assert corrected[0].recovery_confidence == "primary-adjudicated"
    manifest["corrections"][0]["changes"]["fumble_lost"] = False
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="physical loss"):
        apply_adjudications([original], source, path)


def test_legacy_inputs_need_fresh_normalization_before_adjudication(tmp_path: Path) -> None:
    from dataclasses import replace

    original, source, path, manifest = fixture(tmp_path)
    original = replace(original, recovery_policy="legacy")
    manifest["corrections"][0]["expected_event_sha256"] = encoded_hash(original.to_dict())
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="fresh physical"):
        apply_adjudications([original], source, path)


@pytest.mark.parametrize("stale", [False, True])
def test_normalize_cli_applies_checked_corrections_before_publication(
    tmp_path: Path, stale: bool
) -> None:
    import csv

    from tools.chartgen.cli import normalize_main
    from tools.chartgen.source import import_espn

    _, _, manifest_path, manifest = fixture(tmp_path)
    raw = {
        "season": 2007,
        "game_id": "fictional-game",
        "id": "snap",
        "pos_team_id": 1,
        "def_pos_team_id": 2,
        "pos_team": "Cedar Valley",
        "def_pos_team": "Harbor Tech",
        "type.text": "Sack",
        "text": "Team snap out of the endzone.",
        "sack": True,
        "yds_sacked": -8,
        "fumble_vec": True,
        "fumbling_team": 1,
        "fumble_recovery_team": 1,
    }
    raw_path = tmp_path / "source.csv"
    with raw_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(raw))
        writer.writeheader()
        writer.writerow(raw)
    events, source = import_espn(raw_path, url="https://example.invalid/source.csv")
    manifest["raw_sha256"] = "b" * 64 if stale else source["raw_sha256"]
    manifest["corrections"][0]["expected_event_sha256"] = encoded_hash(events[0].to_dict())
    manifest_path.write_text(json.dumps(manifest))
    output = tmp_path / "private-data/normalized.json"
    status = normalize_main(
        [
            "--input",
            str(raw_path),
            "--source-url",
            source["url"],
            "--adjudications",
            str(manifest_path),
            "--output",
            str(output),
        ]
    )
    if stale:
        assert status == 2 and not output.exists()
    else:
        assert status == 0
        corrected, provenance = read_normalized(output)
        assert corrected[0].kind == "other" and corrected[0].yards is None
        assert provenance["adjudication"]["corrections"][0]["reason"]
