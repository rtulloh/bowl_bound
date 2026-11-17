"""Fictional mechanism support: unknown, zero and positive mass are distinct."""

from dataclasses import replace

import pytest

from tests.chartgen.test_generation import events as source_events
from tests.chartgen.test_historical_exposure import source as historical_source
from tools.chartgen.empirical import WeightedObservation
from tools.chartgen.evidence import Event
from tools.chartgen.generate import _fumble_distribution, _fumble_support, generate_team


def event(*, kind: str = "rush", fumble: bool | None = True, **changes: object) -> Event:
    base = Event(
        2007,
        "fictional-game",
        "fictional-event",
        "1",
        "2",
        "Cedar Valley",
        "Harbor Tech",
        kind,
        3,
        fumble=fumble,
    )
    return replace(base, **changes)


@pytest.mark.parametrize("kind", ["rush", "complete", "sack"])
@pytest.mark.parametrize("factor", [1e-13, 2.0**-80, 2.0**80])
def test_single_positive_mechanism_rate_survives_uniform_weight_scaling(kind: str, factor: float):
    ordinary = _fumble_distribution([WeightedObservation(event(kind=kind), 1.0)], 0, 1, kind=kind)
    scaled = _fumble_distribution([WeightedObservation(event(kind=kind), factor)], 0, 1, kind=kind)
    assert ordinary == scaled == (1.0, [3] * 216)


@pytest.mark.parametrize("factor", [2.0**-80, 2.0**80])
def test_mixed_positive_ratios_and_locations_have_no_epsilon_floor(factor: float):
    records = [
        WeightedObservation(event(), 1.0),
        WeightedObservation(event(fumble=False, event_id="known-no"), 3.0),
        WeightedObservation(event(kind="incomplete", fumble=False, event_id="other"), 4.0),
    ]
    expected = _fumble_distribution(records, 0, 1, kind="rush")
    actual = _fumble_distribution(
        [replace(r, weight=r.weight * factor) for r in records], 0, 1, kind="rush"
    )
    assert actual == expected == (1 / 8, [3] * 216)


def test_empty_effective_mechanism_is_dormant_without_fabricated_locations():
    assert _fumble_distribution([], 0, 1, kind="rush") == (0.0, [])
    assert _fumble_distribution([WeightedObservation(event(), 0.0)], 0, 1, kind="rush") == (0.0, [])


def test_known_false_is_a_distinct_observed_annotation_zero():
    assert _fumble_distribution(
        [WeightedObservation(event(fumble=False), 1.0)], 0, 1, kind="rush"
    ) == (0.0, [])


@pytest.mark.parametrize("changes", [{}, {"fumble": True, "fumble_team": "unsupported-holder"}])
def test_positive_all_unknown_primary_support_refuses_a_zero_mechanism(changes: dict):
    row = event(fumble=None)
    row = replace(row, **changes)
    with pytest.raises(ValueError, match="unknown.*fumble|fumble.*unknown"):
        _fumble_distribution([WeightedObservation(row, 1.0)], 0, 1, kind="rush")


def test_known_positive_without_location_retains_existing_refusal():
    with pytest.raises(ValueError, match="no known primary fumble location"):
        _fumble_distribution([WeightedObservation(event(yards=None), 1.0)], 0, 1, kind="rush")


@pytest.mark.parametrize("weight", [-1.0, float("nan"), float("inf"), True])
def test_invalid_probability_weights_are_not_accepted_as_support(weight: float):
    with pytest.raises(ValueError, match="weight"):
        _fumble_distribution([WeightedObservation(event(), weight)], 0, 1, kind="rush")


def test_complete_bundle_unknown_rush_refuses_even_with_known_recovery_elsewhere():
    events = [
        replace(e, fumble=None) if e.kind == "rush" else e for e in source_events.__wrapped__()
    ]
    assert any(
        e.kind == "complete" and e.fumble is True and e.fumble_lost is not None for e in events
    )
    with pytest.raises(ValueError, match="unknown.*fumble|fumble.*unknown"):
        generate_team(events, "1", "Cedar Valley", 2007, seed=19)


def test_mixed_unknown_source_reaches_actual_assessment_and_readiness_as_missing():
    from tools.chartgen.cohort_simulation import assess_team_metrics
    from tools.chartgen.readiness import qualification_status
    from tools.chartgen.scope import CORE_METRICS
    from tools.chartgen.source_exposure import historical_exposure

    events = [
        replace(e, fumble=None) if e.team == "a" and e.kind == "rush" else e
        for e in historical_source(6)
    ]
    history = historical_exposure(events, "a", {f"g{i}" for i in range(6)}, role="offense")
    assert history["metrics"]["fumble"]["source_mean"] == 0.0
    assert history["metrics"]["fumble"]["unknown_source_events"] == 6
    assert not history["metrics"]["fumble"]["qualified"]
    targets = {metric: history["metrics"][metric]["source_mean"] for metric in CORE_METRICS}
    measured = {metric: {"value": target, "n": 10000} for metric, target in targets.items()}
    assessment = assess_team_metrics(measured, targets, minimum_samples=1, historical=history)
    assert not assessment["passed"]
    result = qualification_status(
        failed_games=0,
        coverage={"complete": True},
        expected_teams=("a",),
        per_team={
            "a": {
                "state": "fit",
                "offense_assessment": assessment,
                "defense_assessment": assessment,
            }
        },
    )
    assert any("unknown_primary_fumble_presence" in reason for reason in result["missing_evidence"])


def test_complete_bundle_known_false_rush_remains_supported_annotation_zero():
    events = [
        replace(e, fumble=False) if e.kind == "rush" else e for e in source_events.__wrapped__()
    ]
    _, _, manifest = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
    for play in range(1, 6):
        support = manifest["family_evidence"][str(play)]["fumble_support"]
        assert support["state"] == "observed_zero"
        assert support["unknown_primary_presence"] == 0
        assert support["known_primary_fumbles"] == 0


def test_own_unknown_cannot_be_certified_by_pooled_known_league_negatives():
    source = source_events.__wrapped__()
    own_rush = {e.event_id for e in source if e.team == "1" and e.kind == "rush"}
    selected = set(sorted(own_rush)[:10])  # Actually enter the existing sparse-pooling branch.
    events = [
        replace(e, fumble=None if e.team == "1" else False) if e.kind == "rush" else e
        for e in source
        if e.team != "1" or e.kind != "rush" or e.event_id in selected
    ]
    _, _, manifest = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
    support = manifest["family_evidence"]["1"]["fumble_support"]
    assert support["state"] == "partial_known"
    assert support["own_state"] == "unsupported_all_unknown"
    assert support["own_unknown_primary_presence"] > 0
    assert support["pooled_known_primary_presence"] > 0
    assert support["known_primary_fumbles"] == 0
    assert support["source_accuracy_qualified"] is False


def test_support_mass_is_not_an_independent_observation_count():
    rows = [
        WeightedObservation(event(), 1.0),
        WeightedObservation(event(fumble=None, event_id="unknown"), 2.0),
        WeightedObservation(event(fumble=False, event_id="zero"), 0.0),
    ]
    support = _fumble_support(rows, kind="rush", team="1")
    assert support["state"] == support["own_state"] == "partial_known"
    assert support["raw_eligible_records"] == 3
    assert support["positive_weight_records"] == 2
    assert support["zero_weight_records"] == 1
    assert support["known_primary_presence"] == support["unknown_primary_presence"] == 1
    assert support["mechanism_weight_exact"] == "3"
    assert support["known_weight_exact"] == "1"
    assert support["unknown_weight_exact"] == "2"
    assert _fumble_distribution(rows, 0, 1, kind="rush") == _fumble_distribution(
        rows[::-1], 0, 1, kind="rush"
    )


def test_complete_bundle_distinguishes_dormant_qr_from_observed_zero_qt():
    _, _, manifest = generate_team(source_events.__wrapped__(), "1", "Cedar Valley", 2007, seed=19)
    assert manifest["supplemental_evidence"]["QR"]["fumble_support"]["state"] == "dormant_empty"
    qt = manifest["supplemental_evidence"]["QT"]["fumble_support"]
    assert qt["state"] == "observed_zero"
    assert qt["positive_weight_records"] > 0
