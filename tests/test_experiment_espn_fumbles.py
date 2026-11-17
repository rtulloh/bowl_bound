"""Fictional controls for opt-in modeled ESPN attribution experiments."""

from copy import deepcopy
from dataclasses import replace

import pytest

from scripts.experiment_espn_fumbles import project_game
from tests.test_audit_espn_fumbles import pair
from tools.chartgen.espn_core import normalize_game


def normalized(rows: list[dict]) -> list:
    return normalize_game(
        rows,
        season=2002,
        game_id="fictional",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )[0]


def test_interception_return_link_is_not_reported_as_special_teams() -> None:
    from tests.test_audit_espn_fumbles import return_pair

    rows = return_pair()
    rows[0].update(
        type={"text": "Pass Interception"},
        text="Casey Sample (HT) pass intercepted by Alex Example (CV). Returned for 15 yards.",
    )
    rows[0]["start"]["team"]["$ref"] = "https://example.test/teams/2"
    rows[1]["clock"] = deepcopy(rows[0]["clock"])
    rows[1]["team"] = {"$ref": "https://example.test/teams/2"}
    projected, report = project_game(normalized(rows), rows)
    assert report["special_teams_links"] == 0
    assert report["interception_return_links"] == 1
    assert report["return_fumble_links"] == 1
    assert report["unresolved_recoveries"] == 0
    assert projected[0].fumble is True
    assert projected[0].fumble_team == "1"
    assert projected[1].no_play is True


@pytest.mark.parametrize("kind", ["Rush", "Pass Completion", "Sack"])
def test_link_preserves_gain_and_source_and_counts_the_recovery_only_once(kind: str) -> None:
    rows = pair(kind)
    rows[0]["statYardage"] = -3 if kind == "Sack" else 3
    rows[1]["statYardage"] = 17  # Recovery advance must never become primary gain.
    rows[1]["team"] = {"$ref": "https://example.test/teams/2"}
    source = normalized(rows)
    before = deepcopy(source)
    modeled, report = project_game(source, rows)
    assert source == before
    assert modeled[0].fumble is True
    assert modeled[0].yards == source[0].yards
    assert modeled[0].recovery_team == "2"
    assert modeled[0].fumble_lost is True
    assert modeled[1].no_play is True
    assert report["strict_links"] == 1
    assert report["source_truth_verified"] is False
    assert report["publication_authorized"] is False


def test_clock_fallback_is_opt_in_and_records_its_assumption() -> None:
    rows = pair()
    rows[0]["statYardage"] = 3
    rows[1]["clock"]["displayValue"] = "9:59"
    source = normalized(rows)
    strict, strict_report = project_game(source, rows)
    modeled, report = project_game(source, rows, relax_clock=True)
    assert strict[0].fumble is None
    assert strict_report["fallback_links"] == 0
    assert modeled[0].fumble is True
    assert report["fallback_links"] == 1
    assert report["links"][0]["basis"] == "modeled-clock-disagreement"


@pytest.mark.parametrize("missing", ["carrier", "gain", "owner", "period"])
def test_fallback_does_not_invent_missing_primary_evidence(missing: str) -> None:
    rows = pair()
    rows[0]["statYardage"] = 3
    rows[1]["clock"]["displayValue"] = "9:59"
    if missing == "carrier":
        rows[1]["text"] = rows[1]["text"].replace("Alex Example", "Taylor Sample")
    elif missing == "gain":
        rows[0].pop("statYardage")
    elif missing == "owner":
        rows[1]["start"]["team"]["$ref"] = "https://example.test/teams/2"
    else:
        rows[1]["period"]["number"] = 2
    _, report = project_game(normalized(rows), rows, relax_clock=True)
    assert report["fallback_links"] == 0
    assert report["unresolved_recoveries"] == 1


def test_incidence_denominator_is_a_disclosed_model_view_not_a_source_edit() -> None:
    rows = pair()
    rows[0]["statYardage"] = 3
    extra = deepcopy(rows[0])
    extra.update(id="p3", sequenceNumber="3")
    rows.append(extra)
    source = normalized(rows)
    modeled, report = project_game(source, rows)
    assert source[2].fumble is None
    assert modeled[2].fumble is False
    assert report["modeled_negative_primary_rows"] == 1
    assert "incidence" in report["denominator_policy"]
    assert report["source_negative_observations_established"] is False


def test_missing_normalized_primary_or_duplicate_key_rejects() -> None:
    rows = pair()
    source = normalized(rows)
    with pytest.raises(ValueError, match="normalized"):
        project_game(source[1:], rows)
    with pytest.raises(ValueError, match="duplicate"):
        project_game([*source, replace(source[0])], rows)


def return_rows(family: str = "punt") -> list[dict]:
    from tests.test_audit_espn_fumbles import return_pair

    rows = return_pair("kickoff" if family == "kickoff" else "punt")
    rows[0]["start"]["team"]["$ref"] = "https://example.test/teams/2"
    rows[0]["statYardage"] = 12
    rows[1]["team"] = {"$ref": "https://example.test/teams/1"}
    if family == "interception":
        rows[0].update(
            type={"text": "Pass Interception"},
            text="Casey Sample (HT) pass intercepted by Alex Example (CV). Returned for 12 yards.",
        )
    return rows


@pytest.mark.parametrize("family", ["punt", "kickoff", "interception"])
def test_return_denominator_is_opt_in_and_preserves_source_evidence(family: str) -> None:
    from tools.chartgen.optional_flags import AUTHORED_FLAG_POLICY

    rows = return_rows(family)[:1]
    source = normalized(rows)
    before = deepcopy(source)
    default, _ = project_game(source, rows)
    assert default[0].fumble is None
    modeled, report = project_game(source, rows, model_return_denominator=True)
    assert source == before
    assert modeled[0].fumble is False
    assert modeled[0].fumble_count == 0
    assert modeled[0].optional_flag_policy == AUTHORED_FLAG_POLICY
    assert modeled[0].optional_flag_observations == ()
    assert modeled[0].optional_flag_source_sha256 is None
    assert modeled[0].source_text == source[0].source_text
    assert modeled[0].return_yards == source[0].return_yards
    assert report["modeled_negative_return_rows"] == 1
    assert report["modeled_negative_return_ids"] == ["p1"]
    assert report["source_negative_observations_established"] is False


@pytest.mark.parametrize("family", ["punt", "kickoff", "interception"])
def test_return_model_counts_positive_once_and_uses_the_disclosed_denominator(family: str) -> None:
    from tools.chartgen.generate import _return_fumble_probability

    rows = return_rows(family)
    ordinary = deepcopy(rows[0])
    ordinary.update(id="ordinary", drive={"$ref": "https://example.test/games/1/drives/1003"})
    rows.append(ordinary)
    source = normalized(rows)
    default, _ = project_game(source, rows)
    with pytest.raises(ValueError, match="positive-only"):
        _return_fumble_probability([default[0], default[2]], 1.0)
    modeled, report = project_game(source, rows, model_return_denominator=True)
    assert modeled[0].fumble is True
    assert modeled[0].fumble_team == "1"
    assert modeled[1].no_play is True
    assert modeled[2].fumble is False
    assert _return_fumble_probability([modeled[0], modeled[2]], 1.0) == 0.5
    assert report["return_fumble_links"] == 1
    assert report["modeled_negative_return_rows"] == 1


@pytest.mark.parametrize("conflict", ["carrier", "clock", "position", "duplicate"])
def test_possible_returns_before_unresolved_recoveries_remain_unknown(conflict: str) -> None:
    rows = return_rows()
    if conflict == "carrier":
        rows[1]["text"] = rows[1]["text"].replace("Alex Example", "Other Sample")
    elif conflict == "clock":
        rows[1]["clock"]["displayValue"] = "8:00"
    elif conflict == "position":
        rows[1]["start"]["yardLine"] = 26
    else:
        rows.append(dict(deepcopy(rows[0]), id="duplicate"))
    modeled, report = project_game(normalized(rows), rows, model_return_denominator=True)
    assert modeled[0].fumble is None
    assert report["modeled_negative_return_rows"] == 0
    assert "p1" in report["uncertain_return_ids"]
    if conflict == "duplicate":
        assert modeled[2].fumble is None
        assert "duplicate" in report["uncertain_return_ids"]
    assert report["unresolved_recoveries"] == 1


@pytest.mark.parametrize("excluded", ["try", "penalty", "no_play", "missing_return_gain"])
def test_return_model_excludes_ineligible_or_unlocated_returns(excluded: str) -> None:
    rows = return_rows()[:1]
    source = normalized(rows)
    change = {
        "try": {"event_phase": "try"},
        "penalty": {"penalty": True},
        "no_play": {"no_play": True},
        "missing_return_gain": {"return_yards": None},
    }[excluded]
    source[0] = replace(source[0], **change)
    modeled, report = project_game(source, rows, model_return_denominator=True)
    assert modeled[0].fumble is None
    assert report["modeled_negative_return_rows"] == 0


def test_verified_standalone_primary_fumble_is_retained_for_fitting() -> None:
    rows = pair()[1:]
    source = normalized(rows)
    source[0] = replace(source[0], kind="rush", yards=-2, event_phase="scrimmage")
    assert source[0].fumble is True
    modeled, report = project_game(source, rows)
    assert modeled[0] == source[0]
    assert modeled[0].no_play is False
    assert report["retained_standalone_primary_ids"] == ["p2"]
    assert report["unresolved_recoveries"] == 1


@pytest.mark.parametrize("missing", ["drive", "sequence", "period", "normalized_predecessor"])
def test_missing_order_protects_returns_in_the_ambiguous_scope(missing: str) -> None:
    rows = return_rows()
    rows[1]["text"] = rows[1]["text"].replace("Alex Example", "Other Sample")
    extra = dict(deepcopy(rows[0]), id="other_return")
    extra["drive"]["$ref"] = "https://example.test/games/1/drives/1004"
    rows.append(extra)
    if missing == "drive":
        rows[1].pop("drive")
    elif missing == "sequence":
        rows[1].pop("sequenceNumber")
    elif missing == "period":
        rows[1].pop("period")
        rows[1].pop("drive")
    source = normalized(rows)
    if missing == "normalized_predecessor":
        source = source[1:]
    modeled, report = project_game(source, rows, model_return_denominator=True)
    assert next(event for event in modeled if event.event_id == "other_return").fumble is None
    assert report["modeled_negative_return_rows"] == 0


@pytest.mark.parametrize("observed", [False, True])
def test_return_model_preserves_already_annotated_presence(observed: bool) -> None:
    rows = return_rows()[:1]
    source = [replace(normalized(rows)[0], fumble=observed, fumble_count=int(observed))]
    modeled, report = project_game(source, rows, model_return_denominator=True)
    assert modeled == source
    assert report["modeled_negative_return_rows"] == 0
