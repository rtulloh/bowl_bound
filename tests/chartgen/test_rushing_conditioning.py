"""Run-chart fit cannot compensate for the policy's NCAA sack mixture."""

from dataclasses import replace

import pytest

from tools.chartgen.evidence import Event
from tools.chartgen.generate import CalibrationProfile
from tools.chartgen.refine import aggregate_games, propose_profile, source_targets
from tools.chartgen.source_exposure import historical_exposure


def source(sacks: int) -> list[Event]:
    plays = [
        Event(2007, "g", "r1", "a", "b", "A", "B", "rush", 4),
        Event(2007, "g", "r2", "a", "b", "A", "B", "rush", 6),
        Event(2007, "g", "p", "a", "b", "A", "B", "complete", 10),
    ]
    return plays + [
        replace(plays[0], event_id=f"s{i}", kind="sack", yards=-8) for i in range(sacks)
    ]


def game(sacks: int) -> dict:
    stat = {
        "passing_attempts": 1,
        "completions": 1,
        "interceptions": 0,
        "sacks_taken": sacks,
        "sack_yards_lost": 8 * sacks,
        "rushing_attempts": 2 + sacks,
        "rushing_yards": 10 - 8 * sacks,
        "passing_yards": 10,
    }
    return {
        "status": "passed",
        "teams": {"home": "a", "away": "b"},
        "final": {"statistics": {"home": stat, "away": stat}, "home_score": 0, "away_score": 0},
        "engine_log": [],
        "coaching_calls": [],
        "normalized_chart_draws": [],
    }


def test_pure_rush_targets_exposure_and_proposals_do_not_follow_sack_mixture() -> None:
    a, b = source_targets(source(1), ["a"]), source_targets(source(3), ["a"])
    assert a["pure_rush_yards_per_attempt"] == b["pure_rush_yards_per_attempt"] == 5
    assert a["sack"] != b["sack"]
    for sacks in (1, 3):
        metric = historical_exposure(source(sacks), "a", {"g"}, role="offense")["metrics"][
            "pure_rush_yards_per_attempt"
        ]
        assert metric["source_events"] == 2 and metric["source_mean"] == 5
    profile = CalibrationProfile()
    observed = {"pure_rush_yards_per_attempt": 4.0}
    assert (
        propose_profile(profile, observed, a).run_yards_scale
        == propose_profile(profile, observed, b).run_yards_scale
        > 1
    )


def test_engine_pure_rushing_and_ncaa_diagnostic_preserve_both_denominators() -> None:
    a = aggregate_games([game(1)])["metrics"]
    b = aggregate_games([game(3)])["metrics"]
    for metrics in (a, b):
        assert metrics["pure_rush_yards_per_attempt"]["value"] == 5
        assert metrics["pure_rush_yards_per_attempt"]["n"] == 4
    assert a["ncaa_rush_yards_per_attempt"]["value"] == pytest.approx(2 / 3)
    assert b["ncaa_rush_yards_per_attempt"]["value"] == pytest.approx(-14 / 5)


def test_sack_yardage_is_required_instead_of_guessing_zero() -> None:
    result = game(1)
    del result["final"]["statistics"]["home"]["sack_yards_lost"]
    with pytest.raises(ValueError, match="sack yardage"):
        aggregate_games([result])


def test_source_ncaa_diagnostics_are_separate_from_chart_tuning_targets() -> None:
    from tools.chartgen.refine import source_ncaa_rushing

    diagnostic = source_ncaa_rushing(source(1), ["a"])
    assert diagnostic == {
        "attempts": 3,
        "yards": 2,
        "sacks": 1,
        "unknown_yardage": 0,
        "yards_per_attempt": pytest.approx(2 / 3),
    }
    assert "ncaa_rush_yards_per_attempt" not in source_targets(source(1), ["a"])
    unknown = source_ncaa_rushing([replace(source(1)[0], yards=None)], ["a"])
    assert unknown["yards_per_attempt"] is None and unknown["unknown_yardage"] == 1
