"""Complete evidence cannot be replaced by a passing selected subset."""

from copy import deepcopy

import pytest

from tools.chartgen.cohort_refinement import _joint_assessment
from tools.chartgen.readiness import compare_run_inventory, qualification_status
from tools.chartgen.scope import CORE_METRICS


def passing_summary() -> dict:
    assessment = {
        "passed": True,
        "metrics": {
            name: {
                "passed": True,
                "absolute_error": 0.0,
                "tolerance": 1.0,
                "raw_sample_size": 10000,
                "independent_game_clusters": 1000,
                "standard_error": 0.0,
            }
            for name in CORE_METRICS
        },
        "historical_exposure": {
            "qualified": True,
            "metrics": {name: {"qualified": True} for name in CORE_METRICS},
        },
        "unidentifiable_source_metrics": [],
        "historically_sparse_metrics": [],
    }
    return {
        "failed_games": 0,
        "coverage": {"complete": True},
        "per_source_team": {
            "a": {
                "game_ids": ["ab"],
                "offense_assessment": deepcopy(assessment),
                "defense_assessment": deepcopy(assessment),
            }
        },
    }


def test_joint_point_diagnostic_keeps_a_complete_passing_control() -> None:
    passed, loss = _joint_assessment(passing_summary(), expected_teams=("a",))
    assert passed and loss == 0.0


def test_joint_point_diagnostic_cannot_ignore_an_empty_declared_team() -> None:
    summary = passing_summary()
    summary["per_source_team"]["missing"] = {"game_ids": [], "state": "no_eligible_games"}
    passed, loss = _joint_assessment(summary, expected_teams=("a", "missing"))
    assert not passed
    assert loss == 0.0  # Keep the qualified subset's diagnostic loss, not fake evidence.


def test_joint_point_diagnostic_cannot_ignore_a_failed_game() -> None:
    summary = passing_summary()
    summary["failed_games"] = 1
    assert not _joint_assessment(summary, expected_teams=("a",))[0]


def test_one_failing_team_cannot_hide_in_a_pooled_mean() -> None:
    summary = passing_summary()
    other = deepcopy(summary["per_source_team"]["a"])
    other["defense_assessment"]["passed"] = False
    summary["per_source_team"]["b"] = other
    assert not _joint_assessment(summary, expected_teams=("a", "b"))[0]


def test_summary_keeps_a_required_missing_chart_visible() -> None:
    from tools.chartgen.cohort_simulation import summarize_cohort

    result = summarize_cohort(
        [],
        {"teams": {"a": {"offensive_game_ids": ["ab"], "conference": None}}},
        {},
        {},
        minimum_samples=1,
    )
    assert result["per_source_team"]["a"]["state"] == "missing_chart"
    assert result["qualification"]["state"] == "unverified"


def test_summary_keeps_required_missing_source_targets_visible() -> None:
    from tools.chartgen.cohort_simulation import summarize_cohort

    result = summarize_cohort(
        [],
        {"teams": {"a": {"offensive_game_ids": ["ab"], "conference": None}}},
        {"a": "A"},
        {},
        minimum_samples=1,
    )
    assert result["per_source_team"]["a"]["state"] == "missing_source_targets"
    assert result["qualification"]["passed"] is False


@pytest.mark.parametrize(
    "mutation", ("missing", "duplicate", "team", "fixture", "repetition", "seed")
)
def test_complete_run_inventory_checks_identity_and_multiplicity(mutation: str) -> None:
    expected = [
        {
            "fixture_run": {"game_id": "ab", "repetition": i},
            "spec": {"number": i + 1, "away_id": "A", "home_id": "B", "seed": 17 + i},
        }
        for i in range(2)
    ]
    observed = deepcopy(expected)
    assert compare_run_inventory(expected, observed)["complete"]
    if mutation == "missing":
        observed.pop()
    elif mutation == "duplicate":
        observed[1] = deepcopy(observed[0])  # Same count, one omitted and one duplicated.
    elif mutation in {"fixture", "repetition"}:
        key = "game_id" if mutation == "fixture" else "repetition"
        observed[1]["fixture_run"][key] = "different"
    else:
        key = "home_id" if mutation == "team" else "seed"
        observed[1]["spec"][key] = "different"
    assert not compare_run_inventory(expected, observed)["complete"]


def test_missing_expected_contract_is_not_inferred_from_observed_subset() -> None:
    result = compare_run_inventory(None, [{"fixture_run": "one observed game"}])
    assert result["complete"] is False
    assert result["state"] == "missing_expected_run_contract"


def test_point_pass_is_unverified_without_an_independently_frozen_precision_contract() -> None:
    result = qualification_status(
        failed_games=0, per_team={"a": {"state": "fit"}}, coverage={"complete": True}
    )
    assert result["state"] == "unverified" and not result["passed"]
    assert "precision_contract_unfrozen" in result["missing_evidence"]


def test_pending_precision_never_hides_a_known_engine_failure() -> None:
    result = qualification_status(
        failed_games=1, per_team={"a": {"state": "fit"}}, coverage={"complete": True}
    )
    assert result["state"] == "no_go" and not result["passed"]
    assert "engine_or_reconciliation_failure" in result["known_failures"]


def test_exploratory_point_miss_is_diagnostic_not_an_approved_accuracy_failure() -> None:
    result = qualification_status(
        failed_games=0, per_team={"a": {"state": "not_fit"}}, coverage={"complete": True}
    )
    assert result["state"] == "unverified"
    assert not result["known_failures"]
    assert result["point_diagnostics"]["a"] == "not_fit"


def test_missing_source_support_keeps_exact_team_role_and_metric_reasons() -> None:
    unit = passing_summary()["per_source_team"]["a"]
    unit["state"] = "not_fit"  # Legacy diagnostic state must not obscure source facts.
    unit["offense_assessment"]["unidentifiable_source_metrics"] = ["interception"]
    unit["defense_assessment"]["historically_sparse_metrics"] = ["sack"]
    unit["defense_assessment"]["historical_exposure"] = {
        "qualified": False,
        "state": "missing_historical_exposure",
    }
    result = qualification_status(failed_games=0, per_team={"a": unit}, coverage={"complete": True})
    assert result["state"] == "unverified"
    assert "a/offense:unidentifiable_source_metric/interception" in result["missing_evidence"]
    assert "a/defense:historically_sparse_metric/sack" in result["missing_evidence"]
    assert "a/defense:missing_historical_exposure" in result["missing_evidence"]
    assert not result["known_failures"]


@pytest.mark.parametrize("bad_phase", ("training:0", "coaching"))
def test_complete_phase_consumer_keeps_a_failure_outside_heldout(bad_phase: str) -> None:
    from tools.chartgen.readiness import required_phase_status

    phases = {name: passing_summary() for name in ("training:0", "heldout", "coaching")}
    phases[bad_phase]["failed_games"] = 1
    result = required_phase_status(phases, required=tuple(phases), checks={"regeneration": True})
    assert result["state"] == "no_go" and not result["mechanics_ready"]
    assert f"{bad_phase}:engine_or_reconciliation_failure" in result["known_failures"]
    assert result["phases"]["heldout"]["state"] == "unverified"


def test_complete_phase_consumer_does_not_infer_missing_required_phase() -> None:
    from tools.chartgen.readiness import required_phase_status

    result = required_phase_status(
        {"heldout": passing_summary()},
        required=("training:0", "heldout", "coaching"),
        checks={"regeneration": True},
    )
    assert result["state"] == "unverified" and not result["mechanics_ready"]
    assert "training:0:missing_required_phase" in result["missing_evidence"]
    assert "coaching:missing_required_phase" in result["missing_evidence"]


def test_complete_phase_consumer_retains_failed_replay_and_missing_inventory() -> None:
    from tools.chartgen.readiness import required_phase_status

    phase = passing_summary()
    phase["coverage"] = {"complete": False, "state": "missing_expected_run_contract"}
    result = required_phase_status(
        {"heldout": phase}, required=("heldout",), checks={"save_replay": False}
    )
    assert result["state"] == "no_go" and not result["mechanics_ready"]
    assert "save_replay:failed_required_check" in result["known_failures"]
    assert "heldout:complete_run_inventory" in result["missing_evidence"]


def test_complete_phase_consumer_keeps_all_phase_inventories_and_cannot_promote_point_pass() -> (
    None
):
    from tools.chartgen.readiness import required_phase_status

    phases = {name: passing_summary() for name in ("training:0", "heldout", "coaching")}
    result = required_phase_status(phases, required=tuple(phases), checks={"regeneration": True})
    assert result["mechanics_ready"]
    assert result["state"] == "unverified" and not result["passed"]
    assert set(result["phases"]) == set(phases)
    assert all(value["coverage"] == {"complete": True} for value in result["phases"].values())


def test_joint_point_diagnostic_missing_chart_is_descriptive_not_a_crash() -> None:
    summary = passing_summary()
    summary["per_source_team"]["b"] = {"state": "missing_chart", "game_ids": ["ab"]}
    assert _joint_assessment(summary, expected_teams=("a", "b")) == (False, 0.0)


@pytest.mark.parametrize("indices", ([0], [0, 0], [1, 0]))
def test_training_phase_contract_cannot_shrink_with_observed_records(indices: list[int]) -> None:
    from tools.chartgen.readiness import refinement_phase_status

    history = [(index, passing_summary()) for index in indices]
    result = refinement_phase_status(
        history,
        attempted_candidates=(0, 1),
        heldout=passing_summary(),
        coaching=passing_summary(),
        checks={"regeneration": True},
    )
    assert result["state"] == "no_go" and not result["mechanics_ready"]
    assert "invalid_training_phase_inventory" in result["known_failures"]
    assert result["required_phases"] == ["training:0", "training:1", "heldout", "coaching"]
    assert result["training_inventory"]["observed_candidates"] == indices


def test_invalid_training_phase_inventory_does_not_discard_failed_duplicate_record() -> None:
    from tools.chartgen.readiness import refinement_phase_status

    failed = passing_summary()
    failed["failed_games"] = 1
    result = refinement_phase_status(
        [(0, passing_summary()), (0, failed)],
        attempted_candidates=(0, 1),
        heldout=passing_summary(),
        coaching=passing_summary(),
        checks={"regeneration": True},
    )
    assert "training:1:engine_or_reconciliation_failure" in result["known_failures"]
    assert result["training_inventory"]["observed_candidates"] == [0, 0]


def test_early_stop_expected_attempts_are_contiguous_not_maximum_iterations() -> None:
    from tools.chartgen.readiness import refinement_phase_status

    result = refinement_phase_status(
        [(0, passing_summary())],
        attempted_candidates=(0,),
        heldout=passing_summary(),
        coaching=passing_summary(),
        checks={"regeneration": True},
    )
    assert result["mechanics_ready"]
    assert result["required_phases"] == ["training:0", "heldout", "coaching"]
    bad = refinement_phase_status(
        [(0, passing_summary()), (2, passing_summary())],
        attempted_candidates=(0, 2),
        heldout=passing_summary(),
        coaching=passing_summary(),
        checks={"regeneration": True},
    )
    assert "invalid_training_phase_inventory" in bad["known_failures"]


@pytest.mark.parametrize("state", ("unverified", "no_go"))
def test_cli_summary_does_not_label_exploratory_point_pass_as_accuracy(state: str) -> None:
    from tools.chartgen.readiness import format_readiness_summary

    text = format_readiness_summary(
        mechanics_ready=True, point_passed=True, qualification={"state": state}
    )
    assert "Mechanics ready: True" in text
    assert "exploratory point diagnostics: True" in text
    assert f"qualification: {state.upper()}" in text
    assert "statistical gates: True" not in text


def test_qualification_cannot_infer_required_teams_from_the_supplied_subset() -> None:
    result = qualification_status(
        failed_games=0, per_team={"a": {"state": "fit"}}, coverage={"complete": True}
    )
    assert "expected_source_team_contract" in result["missing_evidence"]


@pytest.mark.parametrize("observed", (("a",), ("a", "b", "extra")))
def test_frozen_expected_team_inventory_checks_omissions_and_extra_teams(
    observed: tuple[str, ...],
) -> None:
    result = qualification_status(
        failed_games=0,
        per_team={team: {"state": "fit"} for team in observed},
        coverage={"complete": True},
        expected_teams=("a", "b"),
    )
    assert not result["team_inventory"]["complete"]
    assert result["team_inventory"]["expected_count"] == 2
    if len(observed) == 1:
        assert "missing_required_source_team/b" in result["missing_evidence"]
    else:
        assert "invalid_source_team_inventory" in result["known_failures"]


def test_final_phase_consumer_does_not_lose_zero_eligible_required_team() -> None:
    from tools.chartgen.readiness import refinement_phase_status

    result = refinement_phase_status(
        [(0, passing_summary())],
        attempted_candidates=(0,),
        heldout=passing_summary(),
        coaching=passing_summary(),
        checks={"regeneration": True},
        expected_teams=("a", "zero"),
    )
    assert all(not phase["team_inventory"]["complete"] for phase in result["phases"].values())
    assert "heldout:missing_required_source_team/zero" in result["missing_evidence"]


def test_joint_diagnostic_cannot_pass_with_an_omitted_required_team() -> None:
    summary = passing_summary()
    assert not _joint_assessment(summary, expected_teams=("a", "zero"))[0]
