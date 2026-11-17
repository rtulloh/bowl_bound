"""Annotation receipts are not historical-measurement completeness evidence."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from tools.chartgen.evidence import Event, classify_espn
from tools.chartgen.source import read_normalized, write_normalized

from .test_csv_flags import OPTIONAL_FIELDS, imported


def authored() -> Event:
    return Event(2026, "fictional-csv", "rush", "a", "b", "A", "B", "rush", 4, fumble=False)


def test_import_receipt_binds_raw_input_adapter_policy_and_event_observations(
    tmp_path: Path,
) -> None:
    events, source = imported(tmp_path, {"fumble_vec": False, "fumble_or_muff": False})
    assert source["adapter"] == "cfbfastR-ESPN-v4"
    assert source["optional_flag_policy"] == "cfb-derived-optional-flags-v1"
    for event in events:
        assert event.optional_flag_policy == source["optional_flag_policy"]
        assert event.optional_flag_source_sha256 == source["raw_sha256"]
        assert {item.field for item in event.optional_flag_observations} == set(OPTIONAL_FIELDS)
    path = tmp_path / "normalized.json"
    write_normalized(path, events, source)
    assert json.loads(path.read_text())["schema_version"] == 6
    assert read_normalized(path) == (events, source)


@pytest.mark.parametrize("change", ["adapter", "policy", "raw", "observations", "authored"])
def test_imported_metadata_refuses_missing_or_fabricated_flag_evidence(
    tmp_path: Path, change: str
) -> None:
    events, source = imported(tmp_path, {"fumble_vec": False, "fumble_or_muff": False})
    if change == "adapter":
        source["adapter"] = "cfbfastR-ESPN-v3"
    elif change == "policy":
        source["optional_flag_policy"] = "legacy-unverified"
    elif change == "raw":
        source["raw_sha256"] = "b" * 64
    elif change == "observations":
        events[0] = replace(events[0], optional_flag_observations=())
    else:
        events[0] = authored()
    with pytest.raises(ValueError, match="optional.*(evidence|receipt|policy|adapter)"):
        write_normalized(tmp_path / "rejected.json", events, source)
    assert not (tmp_path / "rejected.json").exists()


def test_mutated_observation_rejects_even_after_outer_checksum_is_recomputed(
    tmp_path: Path,
) -> None:
    events, source = imported(tmp_path, {"fumble_vec": False, "fumble_or_muff": False})
    path = tmp_path / "normalized.json"
    write_normalized(path, events, source)
    value = json.loads(path.read_text())
    next(
        item
        for item in value["events"][0]["optional_flag_observations"]
        if item["field"] == "fumble_vec"
    )["value"] = True
    value["events_sha256"] = hashlib.sha256(
        json.dumps(value["events"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="optional.*evidence"):
        read_normalized(path)


def test_legacy_false_remains_unchanged_but_cannot_inherit_new_qualification(
    tmp_path: Path,
) -> None:
    from tools.chartgen.source_exposure import historical_exposure

    legacy = authored().to_dict()
    for field in (
        "optional_flag_policy",
        "optional_flag_observations",
        "optional_flag_evidence",
        "optional_flag_source_sha256",
    ):
        legacy.pop(field, None)
    payload = {
        "schema_version": 4,
        "events": [legacy],
        "events_sha256": hashlib.sha256(
            json.dumps([legacy], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "source": {"adapter": "cfbfastR-ESPN-v3", "raw_sha256": "a" * 64},
    }
    path = tmp_path / "immutable-legacy.json"
    original = json.dumps(payload)
    path.write_text(original)
    events, source = read_normalized(path)
    assert path.read_text() == original and source == payload["source"]
    assert events[0].fumble is False and events[0].optional_flag_policy == "legacy-unverified"
    many = [replace(events[0], game_id=f"g{i}") for i in range(6)]
    metric = historical_exposure(many, "a", {f"g{i}" for i in range(6)}, role="offense")["metrics"][
        "fumble"
    ]
    assert metric["source_events"] == 6 and metric["source_mean"] == 0 and not metric["qualified"]
    assert "legacy_optional_flag_evidence" in metric["missing_evidence"]


def test_parsed_provider_negatives_do_not_establish_complete_source_measurement(
    tmp_path: Path,
) -> None:
    from tools.chartgen.cohort_simulation import assess_team_metrics
    from tools.chartgen.readiness import qualification_status
    from tools.chartgen.scope import CORE_METRICS
    from tools.chartgen.source_exposure import historical_exposure

    events, _ = imported(tmp_path, {"fumble_vec": False, "fumble_or_muff": False})
    many = [replace(event, game_id=f"g{i}") for i in range(6) for event in events]
    exposure = historical_exposure(many, "a", {f"g{i}" for i in range(6)}, role="offense")
    metric = exposure["metrics"]["fumble"]
    assert metric["source_events"] == 12 and metric["source_mean"] == 0 and not metric["qualified"]
    assert "provider_optional_measurement_completeness_unverified" in metric["missing_evidence"]
    targets = dict.fromkeys(CORE_METRICS, 0.0)
    measured = {name: {"value": 0.0, "n": 1000} for name in targets}
    assessment = assess_team_metrics(measured, targets, minimum_samples=1, historical=exposure)
    assert not assessment["passed"]
    qualification = qualification_status(
        failed_games=0,
        coverage={"complete": True},
        expected_teams=("a",),
        per_team={
            "a": {
                "state": "not_fit",
                "offense_assessment": assessment,
                "defense_assessment": assessment,
            }
        },
    )
    assert qualification["state"] == "unverified" and not qualification["known_failures"]
    assert (
        "a/offense/fumble:provider_optional_measurement_completeness_unverified"
        in qualification["missing_evidence"]
    )


@pytest.mark.parametrize("raw", [True, False, 0, 1, None])
def test_native_raw_scalar_type_survives_normalization(
    tmp_path: Path, raw: bool | int | None
) -> None:
    event = classify_espn(
        {
            "season": 2026,
            "game_id": "native-fictional",
            "id": "one",
            "pos_team_id": "a",
            "def_pos_team_id": "b",
            "type.text": "Rush",
            "text": "Runner rush.",
            "yds_rushed": 3,
            "fumble_vec": raw,
        }
    )
    assert event is not None
    path = tmp_path / "unreceipted-diagnostic.json"
    write_normalized(path, [event], {"scope": "synthetic direct adapter diagnostic"})
    restored, _ = read_normalized(path)
    observation = {item.field: item for item in restored[0].optional_flag_observations}[
        "fumble_vec"
    ]
    assert observation.supplied is True
    assert type(observation.raw) is type(raw) and observation.raw == raw


@pytest.mark.parametrize("raw", [1.0, 0.0, [], {}, "NA", "None"])
def test_unapproved_native_or_textual_tokens_fail(raw: Any) -> None:
    with pytest.raises(ValueError, match="optional flag fumble_vec"):
        classify_espn(
            {
                "season": 2026,
                "game_id": "native-fictional",
                "id": "one",
                "pos_team_id": "a",
                "def_pos_team_id": "b",
                "type.text": "Rush",
                "text": "Runner rush.",
                "fumble_vec": raw,
            }
        )


@pytest.mark.parametrize("change", ["duplicate", "missing", "extra", "absent-with-value"])
def test_exact_observation_inventory_rejects_fabrication(tmp_path: Path, change: str) -> None:
    events, _ = imported(tmp_path, {"fumble_vec": False, "fumble_or_muff": False})
    value = events[0].to_dict()
    observations = value["optional_flag_observations"]
    if change == "duplicate":
        observations = (*observations[:-1], observations[0])
    elif change == "missing":
        observations = observations[:-1]
    elif change == "extra":
        observations = (*observations, observations[0])
    else:
        observations = ({**observations[0], "supplied": False}, *observations[1:])
    value["optional_flag_observations"] = observations
    with pytest.raises(ValueError, match="optional flag evidence"):
        Event.from_dict(value)


def test_consistent_observation_edit_cannot_reuse_original_source_receipt(tmp_path: Path) -> None:
    events, source = imported(tmp_path, {"fumble_vec": False, "fumble_or_muff": False})
    value = events[0].to_dict()
    observations = list(value["optional_flag_observations"])
    observations[0] = {**observations[0], "raw": "true", "value": True}
    value["optional_flag_observations"] = observations
    events[0] = Event.from_dict(value)
    with pytest.raises(ValueError, match="optional flag evidence receipt"):
        write_normalized(tmp_path / "rejected.json", events, source)


def test_provider_pat_counts_remain_diagnostic_without_completeness(tmp_path: Path) -> None:
    from tools.chartgen.source_exposure import historical_exposure

    events, _ = imported(
        tmp_path, {"xp_made": False}, {"type.text": "Extra Point Good", "type.id": 61}
    )
    many = [replace(event, game_id=f"g{i}") for i in range(6) for event in events]
    metric = historical_exposure(many, "a", {f"g{i}" for i in range(6)}, role="offense")["metrics"][
        "pat"
    ]
    assert metric["source_events"] == 12 and metric["source_mean"] == 1 and not metric["qualified"]
    assert metric["missing_evidence"] == ["provider_optional_measurement_completeness_unverified"]


def test_authored_fixture_authority_is_explicit_and_separate() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    events = [replace(authored(), game_id=f"g{i}") for i in range(6)]
    metric = historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role="offense")[
        "metrics"
    ]["fumble"]
    assert metric["qualified"] and not metric["missing_evidence"]
    assert all(event.optional_flag_policy == "authored-explicit-v1" for event in events)


def test_structural_flags_and_unrelated_numeric_facts_keep_existing_policy(tmp_path: Path) -> None:
    events, _ = imported(
        tmp_path,
        {"fumble_vec": " ", "fumble_or_muff": " "},
        {
            "penalty_no_play": True,
            "penalty_flag": True,
            "penalty_declined": False,
            "yds_penalty": 5,
        },
    )
    assert [event.kind for event in events] == ["rush", "complete"]
    assert [event.yards for event in events] == [4, 8]
    assert all(
        event.no_play and event.penalty and not event.penalty_declined and event.penalty_yards == 5
        for event in events
    )
