"""Common historical observations use fictional events and explicit denominators."""

from copy import deepcopy
from typing import Any

import pytest

from tools.reference_targets import source_observations


def event(
    identity: str = "1", kind: str = "complete", yards: int | None = 8, **changes: Any
) -> dict[str, Any]:
    return dict(
        game_id="g1",
        event_id=identity,
        team="home",
        opponent="away",
        kind=kind,
        yards=yards,
        no_play=False,
        event_phase=None,
        return_yards=None,
        kick_good=None,
        interception_yards=None,
        air_yards=None,
        called_family=None,
        family_confidence="unknown",
        family_evidence=[],
        **changes,
    )


def observe(rows: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    return source_observations(rows, team="home", game_ids=frozenset({"g1"}), **kwargs)


def test_sacks_use_dropbacks_and_separate_ncaa_rushing_population():
    rows = [
        event("1"),
        event("2", "incomplete", None),
        event("3", "interception", None),
        event("4", "sack", -6),
        event("5", "rush", 10),
    ]
    result = observe(rows)
    metrics = result["primary"]
    assert metrics["completion"]["point_observation"] == "1/3"
    assert metrics["interception"]["point_observation"] == "1/3"
    assert metrics["sack"]["point_observation"] == "1/4"
    assert metrics["pure_rush_yards"]["point_observation"] == "10"
    assert metrics["ncaa_rush_yards"]["point_observation"] == "2"
    assert metrics["pass_yards_per_attempt"]["point_observation"] == "8/3"


def test_defense_targets_select_opponent_holder_not_own_offense():
    own = event("1", yards=99)
    against = event("2", yards=5)
    against.update(team="away", opponent="home")
    assert (
        observe([own, against], role="defense")["primary"]["completion_yards"]["point_observation"]
        == "5"
    )


def test_no_play_try_and_outside_game_are_not_ordinary_attempts():
    rows = [event("1")]
    for ident, changes in [
        ("2", {"no_play": True}),
        ("3", {"event_phase": "try"}),
        ("4", {"game_id": "g2"}),
    ]:
        row = event(ident)
        row.update(changes)
        rows.append(row)
    assert observe(rows)["primary"]["completion"]["eligible_events"] == 1


def test_unknown_yards_cannot_become_zero_or_a_full_point_target():
    result = observe([event("1", "rush", 8), event("2", "rush", None)])
    metric = result["primary"]["pure_rush_yards"]
    assert (metric["eligible_events"], metric["known_events"], metric["unknown_events"]) == (
        2,
        1,
        1,
    )
    assert metric["known_only_observation"] == "8"
    assert metric["point_observation"] is None
    assert metric["known_numerator"] == 8


def test_incomplete_and_interception_have_zero_passing_yards_without_missing_completion():
    metric = observe([event("1", "incomplete", None), event("2", "interception", None)])["primary"][
        "pass_yards_per_attempt"
    ]
    assert metric["point_observation"] == "0"
    assert metric["unknown_events"] == 0


def test_unconditional_depth_cdf_retains_unknown_envelope_and_conflict():
    rows = [
        event("1", "interception", None),
        event("2", "interception", None),
        event("3", "interception", None),
    ]
    rows[0]["interception_yards"] = 3
    rows[2].update(interception_yards=17, air_yards=22)
    result = observe(rows)["interception_depth"]
    assert result["eligible_events"] == 3
    assert result["known_events"] == 1
    assert result["unknown_events"] == 2
    assert result["conflicting_depth_events"] == 1
    assert result["cdf"] == [{"depth": 3, "lower": "1/3", "upper": "1"}]
    assert result["point_mean"] is None


def test_generic_deep_is_not_designed_dropback_support():
    row = event(kind="interception", yards=None)
    row.update(
        interception_yards=44,
        called_family=9,
        family_confidence="narrative",
        family_evidence=["text:long-pass"],
    )
    result = observe([row])
    assert result["interception_depth"]["known_events"] == 1
    assert all(x["eligible_events"] == 0 for x in result["designed_call_depth"].values())


def test_explicit_designed_call_has_its_own_missing_depth_denominator():
    rows = [event("1", "interception", None), event("2", "interception", None)]
    for row in rows:
        row.update(called_family=6, family_confidence="narrative", family_evidence=["text:screen"])
    rows[0]["interception_yards"] = -8
    result = observe(rows)["designed_call_depth"]["6"]
    assert (result["eligible_events"], result["known_events"], result["unknown_events"]) == (
        2,
        1,
        1,
    )
    assert result["known_only_mean"] == "-8"


def test_return_holder_is_receiver_and_pat_provider_unknown_is_not_miss():
    kick = event("1", "kickoff", 60)
    kick.update(team="away", opponent="home", return_yards=12)
    pat = event("2", "pat", None)
    pat.update(event_phase="try")
    result = observe([kick, pat])
    assert result["special"]["kickoff_return"]["point_observation"] == "12"
    assert result["special"]["kickoff_distance"]["eligible_events"] == 0
    assert result["special"]["pat_good"]["unknown_events"] == 1
    assert result["special"]["pat_good"]["point_observation"] is None
    assert result["source_qualification"] == "UNVERIFIED"


def test_source_rows_and_requested_game_set_are_not_mutated():
    rows = [event()]
    before = deepcopy(rows)
    result = observe(rows)
    result["primary"]["completion"]["game_ids"].append("foreign")
    assert rows == before


@pytest.mark.parametrize("value", [True, "8", 8.5])
def test_noninteger_yardage_refuses(value):
    with pytest.raises(ValueError, match="integer"):
        observe([event(yards=value)])


def test_duplicate_event_identity_cannot_inflate_source_denominator():
    with pytest.raises(ValueError, match="duplicate"):
        observe([event(), event()])


def test_no_exposure_remains_missing_and_missing_game_is_explicit():
    result = observe([])
    assert result["primary"]["completion"]["point_observation"] is None
    assert result["missing_input_game_ids"] == ["g1"]
