"""Reference-blind bounded coordinate probes and beneficial joint composition."""

from dataclasses import asdict

import pytest

from tools.chartgen.cohort_refinement import profile_bounds
from tools.chartgen.generate import CalibrationProfile, DefensiveProfile


@pytest.mark.parametrize("unknown_error", [None, float("inf")])
def test_coordinate_bridge_retains_unobserved_targets_without_a_probe(
    unknown_error: float | None,
) -> None:
    from tools.chartgen.cohort_refinement import _training_coordinates

    assessment = {"metrics": {"completion": {"absolute_error": unknown_error}}}
    summary = {
        "per_source_team": {
            "a": {
                "offense": {"metrics": {}},
                "defense": {"metrics": {}},
                "offense_assessment": assessment,
                "defense_assessment": assessment,
            }
        }
    }
    targets = {
        "a": {
            "offense": {"completion": 0.5},
            "defense": {"completion": 0.5},
            "historical_exposure": {},
        }
    }
    coordinates, _ = _training_coordinates(
        {"a": CalibrationProfile()}, {"a": DefensiveProfile()}, summary, targets
    )
    assert coordinates == []


def baseline() -> tuple[dict, dict]:
    return (
        {"a": CalibrationProfile(), "b": CalibrationProfile()},
        {"a": DefensiveProfile(), "b": DefensiveProfile()},
    )


def test_probe_changes_exactly_one_coordinate_with_all_opponents_frozen() -> None:
    from tools.chartgen.coordinate_refinement import Coordinate, plan_coordinate_probe

    offense, defense = baseline()
    original = (
        {team: asdict(value) for team, value in offense.items()},
        {team: asdict(value) for team, value in defense.items()},
    )
    observed = []

    def fingerprint(team: str, own: CalibrationProfile, defended: DefensiveProfile) -> str:
        observed.append((team, own, defended))
        return "new"

    plan, ledger = plan_coordinate_probe(
        offense,
        defense,
        [
            Coordinate(
                "b", "offense", "pure_rush_yards_per_attempt", "run_yards_scale", 0.95, 2.0, True
            )
        ],
        profile_bounds(),
        {"baseline"},
        set(),
        fingerprint,
    )
    assert plan is not None and plan["fingerprint"] == "new"
    assert plan["offense"]["b"].run_yards_scale == 0.95
    assert plan["offense"]["a"] == offense["a"]
    assert plan["defense"] == defense
    assert observed == [("b", plan["offense"]["b"], defense["b"])]
    assert original == (
        {team: asdict(value) for team, value in offense.items()},
        {team: asdict(value) for team, value in defense.items()},
    )
    assert len(ledger) == 1


def test_probe_order_is_deterministic_from_errors_then_metric_and_identity() -> None:
    from tools.chartgen.coordinate_refinement import Coordinate, plan_coordinate_probe

    offense, defense = baseline()
    coordinates = [
        Coordinate(team, "defense", "sack", "sack_shift", 0.005, 2.0, True) for team in ("b", "a")
    ]
    args = (profile_bounds(), {"baseline"}, set(), lambda *args: "new")
    first = plan_coordinate_probe(offense, defense, coordinates, *args)
    second = plan_coordinate_probe(offense, defense, list(reversed(coordinates)), *args)
    assert first == second
    assert first[0]["coordinate"]["team"] == "a"
    coordinates.append(
        Coordinate("b", "offense", "completion", "completion_shift", 0.01, 3.0, True)
    )
    assert (
        plan_coordinate_probe(offense, defense, coordinates, *args)[0]["coordinate"]["metric"]
        == "completion"
    )


def test_finite_dice_plateau_is_detected_before_any_football_and_steps_are_bounded() -> None:
    from tools.chartgen.coordinate_refinement import Coordinate, plan_coordinate_probe

    offense, defense = baseline()
    observed = []

    def fingerprint(team: str, own: CalibrationProfile, defended: DefensiveProfile) -> str:
        observed.append(own.run_yards_scale)
        return "changed" if own.run_yards_scale >= 1.2 else "baseline"

    plan, ledger = plan_coordinate_probe(
        offense,
        defense,
        [
            Coordinate(
                "a", "offense", "pure_rush_yards_per_attempt", "run_yards_scale", 1.05, 2.0, True
            )
        ],
        profile_bounds(),
        {"baseline"},
        set(),
        fingerprint,
    )
    assert observed == [1.05, 0.95, 1.1, 0.9, 1.2]
    assert len(ledger) == 5
    assert plan["offense"]["a"].run_yards_scale == 1.2
    assert all(row["reason"] == "seen_chart_fingerprint" for row in ledger[:-1])
    assert all(0.6 <= value <= 1.4 for value in observed)


def test_unqualified_and_already_measured_coordinates_cannot_drive_probes() -> None:
    from tools.chartgen.coordinate_refinement import Coordinate, plan_coordinate_probe

    offense, defense = baseline()

    def forbidden(*args: object) -> str:
        raise AssertionError("unqualified coordinate reached generation")

    coordinates = [
        Coordinate("a", "offense", "completion", "completion_shift", 0.01, 2.0, False),
        Coordinate("b", "offense", "completion", "completion_shift", 0.01, 2.0, True),
    ]
    plan, ledger = plan_coordinate_probe(
        offense,
        defense,
        coordinates,
        profile_bounds(),
        set(),
        {("b", "offense", "completion_shift")},
        forbidden,
    )
    assert plan is None
    assert ledger[-1]["reason"] == "no_qualified_unmeasured_coordinate"


def test_trial_budget_is_hard_and_does_not_claim_exhausted_global_bounds() -> None:
    from tools.chartgen.coordinate_refinement import Coordinate, plan_coordinate_probe

    offense, defense = baseline()
    plan, ledger = plan_coordinate_probe(
        offense,
        defense,
        [
            Coordinate(
                "a", "offense", "pure_rush_yards_per_attempt", "run_yards_scale", 1.01, 2.0, True
            )
        ],
        profile_bounds(),
        {"baseline"},
        set(),
        lambda *args: "baseline",
        maximum_trials=3,
    )
    assert plan is None
    assert len(ledger) == 3
    assert ledger[-1]["search_stopping"] == "predeclared_trial_limit"


def test_joint_candidate_uses_only_locally_beneficial_training_changes() -> None:
    from tools.chartgen.coordinate_refinement import combine_beneficial_probes

    offense, defense = baseline()
    probes = [
        {
            "candidate": 1,
            "coordinate": {
                "team": "a",
                "role": "offense",
                "knob": "run_yards_scale",
                "source_qualified": True,
            },
            "value": 0.95,
            "local_baseline_loss": 10.0,
            "local_probe_loss": 5.0,
        },
        {
            "candidate": 2,
            "coordinate": {
                "team": "b",
                "role": "defense",
                "knob": "pass_yards_offset",
                "source_qualified": True,
            },
            "value": 0.25,
            "local_baseline_loss": 8.0,
            "local_probe_loss": 9.0,
        },
    ]
    own, defended, selected = combine_beneficial_probes(offense, defense, probes)
    assert own["a"].run_yards_scale == 0.95
    assert own["b"] == offense["b"] and defended == defense
    assert selected == [1]
    assert offense["a"].run_yards_scale == 1.0


def test_joint_conflicts_use_local_training_loss_then_earliest_index() -> None:
    from tools.chartgen.coordinate_refinement import combine_beneficial_probes

    offense, defense = baseline()
    probes = [
        {
            "candidate": index,
            "coordinate": {
                "team": "a",
                "role": "offense",
                "knob": "run_yards_scale",
                "source_qualified": True,
            },
            "value": value,
            "local_baseline_loss": 10.0,
            "local_probe_loss": loss,
        }
        for index, value, loss in ((1, 0.95, 5.0), (2, 0.9, 4.0), (3, 0.85, 4.0))
    ]
    a = combine_beneficial_probes(offense, defense, probes)
    b = combine_beneficial_probes(offense, defense, list(reversed(probes)))
    assert a == b
    assert a[0]["a"].run_yards_scale == 0.9
    assert a[2] == [2]


def test_zero_bounded_proposal_is_distinct_from_unknown_source() -> None:
    from tools.chartgen.coordinate_refinement import Coordinate, plan_coordinate_probe

    offense, defense = baseline()
    plan, ledger = plan_coordinate_probe(
        offense,
        defense,
        [
            Coordinate(
                "a", "offense", "pure_rush_yards_per_attempt", "run_yards_scale", 1.0, 2.0, True
            )
        ],
        profile_bounds(),
        set(),
        set(),
        lambda *args: "unused",
    )
    assert plan is None
    assert ledger[-1]["reason"] == "no_bounded_coordinate_movement"


def test_unqualified_or_unknown_probe_loss_cannot_enter_joint_candidate() -> None:
    from tools.chartgen.coordinate_refinement import combine_beneficial_probes

    offense, defense = baseline()
    probes = [
        {
            "candidate": 1,
            "coordinate": {
                "team": "a",
                "role": "offense",
                "knob": "run_yards_scale",
                "source_qualified": False,
            },
            "value": 0.95,
            "local_baseline_loss": 10.0,
            "local_probe_loss": 0.0,
        },
        {
            "candidate": 2,
            "coordinate": {
                "team": "b",
                "role": "offense",
                "knob": "run_yards_scale",
                "source_qualified": True,
            },
            "value": 0.9,
            "local_baseline_loss": 10.0,
            "local_probe_loss": None,
        },
    ]
    own, defended, selected = combine_beneficial_probes(offense, defense, probes)
    assert (own, defended) == (offense, defense)
    assert not selected
