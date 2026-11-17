"""Historical evidence and Monte Carlo repetitions are separate populations."""

from dataclasses import replace

import pytest

from tools.chartgen.evidence import Event
from tools.chartgen.scope import CORE_METRICS


def source(games: int, copies: int = 1) -> list[Event]:
    return [
        Event(
            2007,
            f"g{game}",
            f"{team}-{index}-{copy}",
            team,
            opponent,
            team,
            opponent,
            kind,
            yards,
            fumble=False,
        )
        for game in range(games)
        for team, opponent in (("a", "b"), ("b", "a"))
        for copy in range(copies)
        for index, (kind, yards) in enumerate(
            (
                ("rush", 3),
                ("sack", -4),
                ("complete", 10),
                ("incomplete", None),
                ("interception", None),
            )
        )
    ]


def test_historical_exposure_counts_exact_selected_games_and_roles() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    events = source(7)
    selected = {f"g{i}" for i in range(6)}
    own = historical_exposure(events, "a", selected, role="offense")
    defense = historical_exposure(events, "a", selected, role="defense")
    assert own["qualified"] and defense["qualified"]
    assert own["selected_game_ids"] == sorted(selected)
    assert set(own["metrics"]) == CORE_METRICS | {"drawn_interception_return_yards"}
    unknown_return = own["metrics"]["drawn_interception_return_yards"]
    assert unknown_return["source_events"] == 0 and unknown_return["unknown_source_events"] == 6
    assert unknown_return["source_mean"] is None and not unknown_return["qualified"]
    assert own["metrics"]["completion"]["source_events"] == 18
    assert own["metrics"]["pure_rush_yards_per_attempt"]["source_events"] == 6
    assert own["metrics"]["fumble"]["source_events"] == 30
    assert all(own["metrics"][name]["source_games"] == 6 for name in CORE_METRICS)
    assert own["metrics"]["sack"]["effective_game_count"] == 6
    assert {name: own["metrics"][name] for name in CORE_METRICS} == defense["metrics"]


def test_repeated_simulations_cannot_qualify_one_historical_fixture() -> None:
    from tools.chartgen.cohort_simulation import assess_team_metrics
    from tools.chartgen.source_exposure import historical_exposure

    evidence = historical_exposure(source(1, 100), "a", {"g0"}, role="offense")
    targets = dict.fromkeys(CORE_METRICS, 0.1)
    measured = {metric: {"value": target, "n": 1000000} for metric, target in targets.items()}
    assessment = assess_team_metrics(measured, targets, minimum_samples=1000, historical=evidence)
    assert not assessment["passed"]
    assert assessment["historical_exposure"]["state"] == "sparse_historical_exposure"
    assert not assessment["metrics"]["completion"]["insufficient_samples"]
    assert evidence["metrics"]["completion"]["source_games"] == 1


def test_unknown_fumble_owner_does_not_create_source_exposure() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    events = [replace(event, fumble=True, fumble_team="unidentified") for event in source(6)]
    evidence = historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role="defense")
    assert evidence["metrics"]["completion"]["qualified"]
    assert not evidence["metrics"]["fumble"]["qualified"]
    assert evidence["metrics"]["fumble"]["source_events"] == 0
    assert evidence["metrics"]["fumble"]["unknown_source_events"] == 30
    assert not evidence["qualified"]


def test_per_metric_source_game_coverage_and_concentration_are_visible() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    events = [event for event in source(6) if not (event.kind == "sack" and event.game_id == "g5")]
    events += [replace(event, event_id=event.event_id + "-extra") for event in source(1, 10)]
    evidence = historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role="offense")
    assert (
        evidence["metrics"]["sack"]["source_games"] == 6
    )  # Other dropbacks still observe sack incidence.
    assert 1 < evidence["metrics"]["sack"]["effective_game_count"] < 6
    assert evidence["minimum_source_games"] == 6
    with pytest.raises(ValueError, match="role"):
        historical_exposure(events, "a", {"g0"}, role="invalid")


def test_missing_historical_metadata_is_not_a_fit_pass() -> None:
    from tools.chartgen.cohort_simulation import assess_team_metrics

    targets = dict.fromkeys(CORE_METRICS, 0.1)
    measured = {metric: {"value": target, "n": 1000000} for metric, target in targets.items()}
    assessment = assess_team_metrics(measured, targets, minimum_samples=1000)
    assert not assessment["passed"]
    assert assessment["historical_exposure"]["state"] == "missing_historical_exposure"


def test_repeated_simulations_cannot_increase_historical_update_weight() -> None:
    from tools.chartgen.cohort_refinement import propose_team_profiles
    from tools.chartgen.generate import CalibrationProfile, DefensiveProfile
    from tools.chartgen.source_exposure import historical_exposure

    events = source(6, 50)
    historical = {
        role: historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role=role)
        for role in ("offense", "defense")
    }
    targets = {"pure_rush_yards_per_attempt": 4.0}
    first = {"pure_rush_yards_per_attempt": {"value": 6.0, "n": 2000}}
    repeated = {"pure_rush_yards_per_attempt": {"value": 6.0, "n": 2000000}}
    args = (CalibrationProfile(), DefensiveProfile())
    a = propose_team_profiles(*args, first, first, targets, targets, source_exposure=historical)
    b = propose_team_profiles(
        *args, repeated, repeated, targets, targets, source_exposure=historical
    )
    assert a[:2] == b[:2]
    assert a[2]["update_weights"] == b[2]["update_weights"]
    assert a[2]["source_exposure_weight_cap"] is True
    assert a[0] != CalibrationProfile()


def test_one_source_game_cannot_drive_a_cohort_profile_update() -> None:
    from tools.chartgen.cohort_refinement import propose_team_profiles
    from tools.chartgen.generate import CalibrationProfile, DefensiveProfile
    from tools.chartgen.source_exposure import historical_exposure

    events = source(1, 1000)
    historical = {
        role: historical_exposure(events, "a", {"g0"}, role=role) for role in ("offense", "defense")
    }
    measured = {"pure_rush_yards_per_attempt": {"value": 6.0, "n": 1000000}}
    own, defense = CalibrationProfile(), DefensiveProfile()
    a, b, diagnostics = propose_team_profiles(
        own,
        defense,
        measured,
        measured,
        {"pure_rush_yards_per_attempt": 4.0},
        {"pure_rush_yards_per_attempt": 4.0},
        source_exposure=historical,
    )
    assert (a, b) == (own, defense)
    assert (
        "offense/historical:pure_rush_yards_per_attempt"
        in diagnostics["unidentifiable_or_sparse_metrics"]
    )


def test_qualified_source_and_matching_simulations_can_pass() -> None:
    from tools.chartgen.cohort_simulation import assess_team_metrics
    from tools.chartgen.source_exposure import historical_exposure

    evidence = historical_exposure(source(6), "a", {f"g{i}" for i in range(6)}, role="offense")
    targets = dict.fromkeys(CORE_METRICS, 0.1)
    measured = {metric: {"value": target, "n": 1000000} for metric, target in targets.items()}
    assert assess_team_metrics(measured, targets, minimum_samples=1000, historical=evidence)[
        "passed"
    ]


def test_sparse_special_team_source_cannot_be_hidden_by_qualified_core() -> None:
    from tools.chartgen.cohort_simulation import assess_team_metrics
    from tools.chartgen.source_exposure import historical_exposure

    events = source(6)
    events.append(replace(events[0], kind="punt", yards=40, event_id="punt"))
    events.append(
        replace(
            events[0],
            kind="punt",
            team="b",
            opponent="a",
            yards=40,
            return_yards=8,
            event_id="opponent-punt",
        )
    )
    evidence = historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role="offense")
    assert evidence["qualified"]
    assert evidence["metrics"]["drawn_punt_yards"]["source_events"] == 1
    assert evidence["metrics"]["drawn_punt_return_yards"]["source_events"] == 1
    targets = {**dict.fromkeys(CORE_METRICS, 0.1), "drawn_punt_yards": 40.0}
    measured = {metric: {"value": target, "n": 1000000} for metric, target in targets.items()}
    assessment = assess_team_metrics(measured, targets, minimum_samples=1000, historical=evidence)
    assert not assessment["passed"]
    assert assessment["historically_sparse_metrics"] == ["drawn_punt_yards"]


def test_source_uncertainty_uses_game_clusters_not_independent_play_noise() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    template = source(1)[0]
    events = [replace(template, game_id="g0", event_id="a", yards=0)]
    events += [replace(template, game_id="g1", event_id=f"b{i}", yards=2) for i in range(3)]
    metric = historical_exposure(events, "a", {"g0", "g1"}, role="offense")["metrics"][
        "pure_rush_yards_per_attempt"
    ]
    assert metric["source_mean"] == 1.5
    assert metric["source_standard_error"] == 0.75
    assert metric["source_ratio_variance"] == 0.5625
    assert (
        metric["source_sampling_method"]
        == "observed-game cluster-robust ratio; finite-cluster correction"
    )


def test_one_historical_cluster_has_unidentified_sampling_uncertainty() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    metric = historical_exposure(source(1, 100), "a", {"g0"}, role="offense")["metrics"][
        "completion"
    ]
    assert metric["source_events"] == 300
    assert metric["source_standard_error"] is None
    assert metric["source_ratio_variance"] is None
    assert metric["uncertainty_state"] == "insufficient_source_clusters"


def test_no_observed_rare_event_does_not_prove_absence_of_historical_risk() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    metric = historical_exposure(source(6), "a", {f"g{i}" for i in range(6)}, role="offense")[
        "metrics"
    ]["fumble"]
    assert metric["source_mean"] == 0
    assert metric["source_standard_error"] == 0
    assert metric["uncertainty_state"] == "zero_between_game_variation_not_proof_of_no_risk"
    assert "not a population-confidence guarantee" in metric["uncertainty_limits"]


def test_source_exposure_point_estimates_match_conditioned_targets() -> None:
    from tools.chartgen.refine import source_targets
    from tools.chartgen.source_exposure import historical_exposure

    events = source(6)
    events[0] = replace(events[0], fumble=True, fumble_team="a")
    for role in ("offense", "defense"):
        facts = source_targets(events, ["a"], role=role)
        evidence = historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role=role)
        for name, value in facts.items():
            assert evidence["metrics"][name]["source_mean"] == pytest.approx(value)


def test_special_team_source_uncertainty_retains_known_and_unknown_observations() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    template = source(1)[0]
    events = [
        replace(template, game_id="g0", kind="punt", yards=30, event_id="p0"),
        replace(template, game_id="g1", kind="punt", yards=50, event_id="p1"),
        replace(template, game_id="g2", kind="punt", yards=None, event_id="p2"),
    ]
    metric = historical_exposure(events, "a", {"g0", "g1", "g2"}, role="offense")["metrics"][
        "drawn_punt_yards"
    ]
    assert metric["source_mean"] == 40
    assert metric["source_standard_error"] == 10
    assert metric["unknown_source_events"] == 1
    assert metric["source_games"] == 2


def test_unknown_only_special_source_is_reported_without_zero_fill() -> None:
    from tools.chartgen.source_exposure import historical_exposure

    event = replace(source(1)[0], kind="punt", yards=None)
    metric = historical_exposure([event], "a", {"g0"}, role="offense")["metrics"][
        "drawn_punt_yards"
    ]
    assert metric["source_events"] == 0
    assert metric["unknown_source_events"] == 1
    assert metric["source_mean"] is None
    assert metric["source_standard_error"] is None
    assert not metric["qualified"]
