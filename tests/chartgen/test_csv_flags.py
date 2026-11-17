"""Fictional CSV optional measurements preserve unknown and supplied evidence."""

import csv
from pathlib import Path
from typing import Any

import pytest

from tools.chartgen.evidence import Event
from tools.chartgen.refine import source_targets
from tools.chartgen.source import import_espn, read_normalized, write_normalized

OPTIONAL_FIELDS = (
    "fumble_vec",
    "fumble_or_muff",
    "fumble_lost",
    "pos_fumble_lost",
    "def_fumble_lost",
    "fg_made",
    "xp_made",
    "qb_scramble",
)


def imported(
    tmp_path: Path,
    flags: dict[str, Any] | None,
    overrides: dict[str, Any] | None = None,
) -> tuple[list[Event], dict[str, Any]]:
    rows = [
        {
            "season": 2026,
            "game_id": "fictional-csv",
            "id": "rush",
            "pos_team_id": "a",
            "def_pos_team_id": "b",
            "type.text": "Rush",
            "text": "Runner rush for 4 yards.",
            "yds_rushed": 4,
        },
        {
            "season": 2026,
            "game_id": "fictional-csv",
            "id": "pass",
            "pos_team_id": "a",
            "def_pos_team_id": "b",
            "type.text": "Pass Completion",
            "text": "Pass complete for 8 yards.",
            "yds_receiving": 8,
        },
    ]
    rows = [{**row, **(flags or {}), **(overrides or {})} for row in rows]
    path = tmp_path / "fictional-source.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted({name for row in rows for name in row}))
        writer.writeheader()
        writer.writerows(rows)
    return import_espn(path, url="https://example.invalid/fictional-source.csv")


@pytest.mark.parametrize("raw", [None, "", " ", "\t"])
def test_blank_csv_fumbles_stay_unknown_through_normalized_roundtrip(
    tmp_path: Path, raw: Any
) -> None:
    events, provenance = imported(
        tmp_path, {"fumble_vec": raw, "fumble_or_muff": raw, "fumble_lost": raw}
    )
    path = tmp_path / "normalized.json"
    write_normalized(path, events, provenance)
    restored, source = read_normalized(path)
    assert source == provenance
    for event in restored:
        assert event.fumble is None and event.fumble_count is None
        assert event.net_possession_fumble_lost is None and event.fumble_lost is None


def test_blank_csv_fumbles_cannot_create_observed_zero_source_target(tmp_path: Path) -> None:
    events, _ = imported(tmp_path, {"fumble_vec": "", "fumble_or_muff": ""})
    assert "fumble" not in source_targets(events, ["a"])


def test_absent_csv_fumble_fields_are_unknown_control(tmp_path: Path) -> None:
    events, _ = imported(tmp_path, None)
    assert all(event.fumble is None and event.fumble_count is None for event in events)
    assert "fumble" not in source_targets(events, ["a"])


@pytest.mark.parametrize("raw", [False, 0, "false", "0"])
def test_explicit_csv_negative_annotations_stay_known_provider_zero(
    tmp_path: Path, raw: Any
) -> None:
    events, provenance = imported(
        tmp_path, {"fumble_vec": raw, "fumble_or_muff": raw, "fumble_lost": raw}
    )
    path = tmp_path / "normalized.json"
    write_normalized(path, events, provenance)
    restored, _ = read_normalized(path)
    assert all(
        event.fumble is False
        and event.fumble_count == 0
        and event.net_possession_fumble_lost is False
        for event in restored
    )
    assert source_targets(restored, ["a"])["fumble"] == 0


@pytest.mark.parametrize("raw", ["maybe", "1.0", "null", "NaN", "2"])
def test_unrecognized_csv_fumble_token_is_actionable_not_false(tmp_path: Path, raw: str) -> None:
    with pytest.raises(ValueError, match="fictional-csv.*rush.*fumble_vec"):
        imported(tmp_path, {"fumble_vec": raw, "fumble_or_muff": "false"})


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (True, True),
        (1, True),
        (" TrUe ", True),
        (False, False),
        (0, False),
        (" false ", False),
        (" ", None),
    ],
)
def test_csv_optional_raw_and_parsed_evidence_survives_roundtrip(
    tmp_path: Path, field: str, raw: Any, expected: bool | None
) -> None:
    events, provenance = imported(tmp_path, {field: raw})
    path = tmp_path / "normalized.json"
    write_normalized(path, events, provenance)
    restored, _ = read_normalized(path)
    observation = {item.field: item for item in restored[0].optional_flag_observations}[field]
    assert observation.supplied is True and observation.raw == str(raw)
    assert observation.value is expected


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
def test_absent_optional_field_is_distinct_from_supplied_blank(tmp_path: Path, field: str) -> None:
    events, _ = imported(tmp_path, None)
    observation = {item.field: item for item in events[0].optional_flag_observations}[field]
    assert observation.supplied is False and observation.raw is None and observation.value is None


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
def test_unsupported_optional_field_names_row_and_field(tmp_path: Path, field: str) -> None:
    with pytest.raises(ValueError, match="fictional-csv.*rush.*" + field):
        imported(tmp_path, {field: "unsupported"})


@pytest.mark.parametrize("vec", [True, False, None])
@pytest.mark.parametrize("broader", [True, False, None])
def test_csv_fumble_union_requires_complete_negative_annotations(
    tmp_path: Path, vec: bool | None, broader: bool | None
) -> None:
    events, _ = imported(tmp_path, {"fumble_vec": vec, "fumble_or_muff": broader})
    expected = (
        True
        if vec is True or broader is True
        else False
        if vec is False and broader is False
        else None
    )
    assert all(event.fumble is expected for event in events)
    assert all(
        event.fumble_count == (1 if expected is True else 0 if expected is False else None)
        for event in events
    )


def test_true_vec_exposes_attached_return_without_conflating_net_and_physical_loss(
    tmp_path: Path,
) -> None:
    events, provenance = imported(
        tmp_path,
        {
            "fumble_vec": " true ",
            "fumble_or_muff": "",
            "fumble_lost": "false",
            "pos_fumble_lost": "false",
            "def_fumble_lost": "true",
        },
        {"yds_fumble_return": 6, "recovery_team": "b", "fumbling_team": "a"},
    )
    path = tmp_path / "normalized.json"
    write_normalized(path, events, provenance)
    restored, _ = read_normalized(path)
    for event in restored:
        assert event.fumble is True and event.fumble_count == 1 and event.return_yards == 6
        assert event.fumble_team == "a" and event.recovery_team == "b" and event.fumble_lost is True
        assert event.net_possession_fumble_lost is False and event.provider_pos_fumble_lost is False
        assert event.provider_def_fumble_lost is True
    assert [event.yards for event in restored] == [4, 8]


@pytest.mark.parametrize("vec", [False, None])
def test_broader_muff_does_not_expose_vec_specific_return(tmp_path: Path, vec: bool | None) -> None:
    events, _ = imported(
        tmp_path, {"fumble_vec": vec, "fumble_or_muff": True}, {"yds_fumble_return": 6}
    )
    assert all(event.fumble is True and event.return_yards is None for event in events)


@pytest.mark.parametrize(
    ("label", "type_id", "field"),
    [("Extra Point Good", 61, "xp_made"), ("Field Goal Good", 59, "fg_made")],
)
def test_explicit_kick_success_retains_default_false_annotation(
    tmp_path: Path, label: str, type_id: int, field: str
) -> None:
    events, _ = imported(tmp_path, {field: False}, {"type.text": label, "type.id": type_id})
    for event in events:
        assert event.kick_good is True
        observation = {item.field: item for item in event.optional_flag_observations}[field]
        assert observation.value is False and observation.raw == "False"
        assert any("type" in basis for basis in event.optional_flag_evidence)


@pytest.mark.parametrize(
    ("label", "field"), [("Field Goal", "fg_made"), ("Extra Point", "xp_made")]
)
def test_blank_generic_kick_success_remains_unknown(tmp_path: Path, label: str, field: str) -> None:
    events, _ = imported(tmp_path, {field: " "}, {"type.text": label})
    assert all(event.kick_good is None for event in events)


def test_scramble_narrative_is_specific_and_retains_negative_annotation(tmp_path: Path) -> None:
    events, _ = imported(
        tmp_path,
        {"qb_scramble": False, "fumble_vec": "", "fumble_or_muff": ""},
        {"text": "Quarterback scrambles for 4 yards."},
    )
    for event in events:
        assert event.quarterback_scramble is True and event.fumble is None
        assert {item.field: item for item in event.optional_flag_observations}[
            "qb_scramble"
        ].value is False
        assert "text:scramble" in event.optional_flag_evidence
