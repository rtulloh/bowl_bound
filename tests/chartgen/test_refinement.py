"""Refinement gates and held-out selection use synthetic metric evidence."""

from dataclasses import asdict

import pytest

from tools.chartgen.generate import CalibrationProfile
from tools.chartgen.refine import SeedPlan, aggregate_games, assess_metrics, propose_profile


def test_seed_domains_are_disjoint_and_candidate_pairing_stable() -> None:
    plan = SeedPlan(2007, 8, 16)
    assert not set(plan.training) & set(plan.validation)
    assert plan.training == SeedPlan(2007, 8, 16).training
    with pytest.raises(ValueError, match="positive"):
        SeedPlan(1, 0, 16)


def test_tolerances_do_not_pass_underexposed_metrics() -> None:
    measured = {"completion": {"value": 0.6, "n": 5, "variance": 0.24}}
    result = assess_metrics(measured, {"completion": 0.6}, minimum_samples=100)
    assert not result["passed"]
    assert result["metrics"]["completion"]["insufficient_samples"]


def test_proposal_joint_metrics_stays_bounded() -> None:
    profile = CalibrationProfile()
    next_profile = propose_profile(
        profile,
        {
            "rush_yards_per_attempt": 3.0,
            "pass_yards_per_attempt": 5.0,
            "completion": 0.5,
            "interception": 0.06,
            "sack": 0.1,
            "fumble": 0.05,
        },
        {
            "rush_yards_per_attempt": 6.0,
            "pass_yards_per_attempt": 8.0,
            "completion": 0.65,
            "interception": 0.03,
            "sack": 0.05,
            "fumble": 0.02,
        },
    )
    assert next_profile.run_yards_scale > profile.run_yards_scale
    assert next_profile.completion_shift > 0
    assert next_profile.interception_scale < 1
    assert all(0.6 <= v <= 1.4 for k, v in asdict(next_profile).items() if not k.endswith("shift"))


def test_failed_games_cannot_be_hidden_by_successful_averages() -> None:
    report = aggregate_games([{"status": "failed", "error": "SyntheticFailure"}])
    assert report["failed_games"] == 1 and report["passed_games"] == 0
    assert report["metrics"] == {}


def test_missing_fumble_evidence_does_not_become_zero_target() -> None:
    from tools.chartgen.evidence import Event
    from tools.chartgen.refine import source_targets

    sample = [
        Event(2007, "g", "1", "a", "b", "A", "B", "rush", 5),
        Event(2007, "g", "2", "a", "b", "A", "B", "complete", 10),
    ]
    assert "fumble" not in source_targets(sample, ["a"])


def test_missing_yardage_cannot_create_a_zero_efficiency_target() -> None:
    from tools.chartgen.evidence import Event
    from tools.chartgen.refine import source_targets

    sample = [
        Event(2007, "g", "1", "a", "b", "A", "B", "rush", None),
        Event(2007, "g", "2", "a", "b", "A", "B", "complete", 10),
    ]
    with pytest.raises(ValueError, match="yardage"):
        source_targets(sample, ["a"])


def test_pooled_uncertainty_clusters_whole_games_and_preserves_raw_exposure() -> None:
    def game(home_attempts: int, away_attempts: int, returns: int) -> dict:
        def statistics(attempts: int) -> dict:
            return {
                "passing_attempts": attempts,
                "completions": attempts // 2,
                "interceptions": 0,
                "sacks_taken": 0,
                "rushing_attempts": 10,
                "rushing_yards": 40,
                "passing_yards": attempts * 6,
            }

        return {
            "status": "passed",
            "teams": {"home": "A", "away": "B"},
            "final": {
                "statistics": {
                    "home": statistics(home_attempts),
                    "away": statistics(away_attempts),
                },
                "home_score": 7,
                "away_score": 3,
            },
            "engine_log": [],
            "coaching_calls": [],
            "normalized_chart_draws": [
                {"team_id": "A", "column": "punt_return", "yards": 10} for _ in range(returns)
            ],
        }

    first = game(10, 20, 2)
    first["final"]["statistics"]["home"]["completions"] = 8
    first["final"]["statistics"]["away"]["completions"] = 12
    report = aggregate_games([first, game(20, 20, 1)])
    completion = report["metrics"]["completion"]
    assert completion["n"] == 70
    assert completion["value"] == pytest.approx(40 / 70)
    assert completion["standard_error"] == pytest.approx(4 / 49)
    assert completion["clusters"] == 2
    assert completion["effective_sample_size"] == pytest.approx(70**2 / (30**2 + 40**2))
    drawn = report["metrics"]["drawn_punt_return_yards"]
    assert drawn["n"] == 3 and drawn["clusters"] == 2
    assert drawn["effective_sample_size"] == pytest.approx(9 / 5)
    assert drawn["standard_error"] == 0
    assert report["per_team"]["A"]["metrics"]["completion"]["n"] == 30


def test_normalized_return_observer_uses_engine_sections_not_display_text() -> None:
    from bowl_bound.models import SpecialTeamsColumn
    from tests.synthetic_teams import metadata, team_chart
    from tools.chartgen.refine import observe_chart_draws

    chart = team_chart("Synthetic A")
    teams = {"A": (chart, metadata())}
    roll = next(
        r.roll for r in chart.special_teams if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN
    )
    report = {
        "engine_log": [
            {
                "trace": [
                    {
                        "team": chart.name,
                        "section": section,
                        "roll": {"total": roll},
                        "cell": "display is deliberately irrelevant",
                    }
                    for section in (
                        "turnover_return",
                        "turnover_return_reroll",
                        "end_zone_recovery_return",
                        "punt_return",
                    )
                ]
            }
        ]
    }
    draws = observe_chart_draws(report, teams)
    assert [d["column"] for d in draws] == ["interception_return"] * 3 + ["punt_return"]
    assert all(d["team_id"] == "A" for d in draws)


def test_current_public_observation_policy_is_recorded_for_both_cpu_sides() -> None:
    from scripts.run_local_season import GameSpec, _play_one
    from tests.synthetic_teams import metadata, team_chart

    teams = {
        f"2007/{name.lower()}": (team_chart(name, season=2007), metadata()) for name in ("A", "B")
    }
    result = _play_one(
        GameSpec(1, 2007, "2007/a", "2007/b", 340010),
        teams,
        coach_policy="baseline-v10",
        simulation_coach_version=10,
    )
    assert result["status"] == "passed", result.get("error_detail")
    assert result["configuration"]["engine_coach_policy"] == "baseline-v10"
    assert result["configuration"]["simulation_coach_policy"] == "baseline-v10"
    assert {c["team_id"] for c in result["coaching_calls"]} == {"2007/a", "2007/b"}
