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
