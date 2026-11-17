"""Deterministic reference-blind training choice and immutable selection receipts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest


def candidate(
    index: int, loss: float, unit_losses: tuple[float, float], *, passing: bool = True
) -> dict:
    return {
        "candidate": index,
        "equal_team_joint_loss": loss,
        "profiles": {"offense": {"a": {"run_yards_scale": 1 + index / 100}}, "defense": {}},
        "chart_fingerprint": str(index) * 64,
        "summary": {
            "failed_games": 0,
            "per_source_team": {
                "a": {
                    "game_ids": ["ab"],
                    **{
                        role + "_assessment": {
                            "loss": unit_loss,
                            "metrics": {
                                "completion": {
                                    "passed": passing,
                                    "absolute_error": unit_loss**0.5,
                                    "tolerance": 1.0,
                                }
                            },
                            "unidentifiable_source_metrics": [],
                            "historical_exposure": {
                                "qualified": True,
                                "metrics": {"completion": {"qualified": True}},
                            },
                        }
                        for role, unit_loss in zip(("offense", "defense"), unit_losses, strict=True)
                    },
                }
            },
        },
    }


def test_global_improvement_cannot_hide_local_regression() -> None:
    from tools.chartgen.training_selection import choose_training_candidate

    history = [candidate(0, 10, (10, 10)), candidate(1, 5, (1, 11)), candidate(2, 6, (6, 6))]
    result = choose_training_candidate(history)
    assert result["selected_candidate"] == 2
    assert not result["candidate_assessments"][1]["admissible"]
    assert "a/defense:unit_loss_regressed" in result["candidate_assessments"][1]["reasons"]
    assert result == choose_training_candidate(list(reversed(history)))


def test_passing_core_metric_cannot_be_traded_away() -> None:
    from tools.chartgen.training_selection import choose_training_candidate

    result = choose_training_candidate(
        [candidate(0, 10, (10, 10)), candidate(1, 5, (5, 5), passing=False)]
    )
    assert result["selected_candidate"] == 0
    assert (
        "a/offense:previously_passing_core/completion"
        in result["candidate_assessments"][1]["reasons"]
    )


def test_equal_ranks_keep_earliest_candidate_and_duplicate_evidence_is_rejected() -> None:
    from tools.chartgen.training_selection import choose_training_candidate

    baseline = candidate(0, 10, (10, 10))
    assert (
        choose_training_candidate([baseline, candidate(1, 10, (10, 10))])["selected_candidate"] == 0
    )
    with pytest.raises(ValueError, match="candidate"):
        choose_training_candidate([baseline, deepcopy(baseline)])
    duplicate = candidate(1, 5, (5, 5))
    duplicate["chart_fingerprint"] = baseline["chart_fingerprint"]
    with pytest.raises(ValueError, match="fingerprint"):
        choose_training_candidate([baseline, duplicate])


def test_selection_receipt_is_semantic_immutable_and_tamper_checked(tmp_path: Path) -> None:
    from tools.chartgen.training_selection import seal_training_selection

    history = [candidate(0, 10, (10, 10)), candidate(1, 5, (5, 5))]
    config = {"source_sha256": "source", "master_seed": 77, "engine": {"engine_sha256": "engine"}}
    path = tmp_path / "selection.json"
    receipt = seal_training_selection(path, history, config)
    assert receipt == seal_training_selection(path, history, config)
    assert receipt == seal_training_selection(tmp_path / "another-path.json", history, config)
    assert "timestamp" not in receipt
    assert receipt["selected_candidate"] == 1
    history[1]["profiles"]["offense"]["a"]["run_yards_scale"] = 1.3
    assert receipt["selected_profiles"]["offense"]["a"]["run_yards_scale"] == 1.01
    original = path.read_bytes()
    with pytest.raises(ValueError, match="selection"):
        seal_training_selection(path, history, config)
    assert path.read_bytes() == original
    tampered = json.loads(original)
    tampered["selected_candidate"] = 0
    path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="selection"):
        seal_training_selection(path, [candidate(0, 10, (10, 10)), candidate(1, 5, (5, 5))], config)


def test_reference_absence_and_perturbation_have_no_selection_influence(tmp_path: Path) -> None:
    from tools.chartgen.training_selection import seal_training_selection

    history = [candidate(0, 10, (10, 10)), candidate(1, 5, (5, 5))]
    config = {"source_sha256": "source", "master_seed": 77}
    absent = seal_training_selection(tmp_path / "absent.json", history, config)
    reference = tmp_path / "developer-reference.json"
    reference.write_text(json.dumps({"fictional_cell": 99, "color": "red"}))
    first = seal_training_selection(tmp_path / "present.json", history, config)
    reference.write_text(json.dumps({"fictional_cell": -99, "color": "black"}))
    perturbed = seal_training_selection(tmp_path / "perturbed.json", history, config)
    assert absent == first == perturbed


def test_unqualified_outer_units_remain_descriptive_in_training_objective() -> None:
    from tools.chartgen.training_selection import qualified_training_objective

    summary = candidate(0, 10, (10, 10))["summary"]
    for role in ("offense", "defense"):
        summary["per_source_team"]["a"][role + "_assessment"]["metrics"]["completion"].update(
            absolute_error=0.1, tolerance=0.1
        )
    outer = deepcopy(summary["per_source_team"]["a"])
    for role in ("offense", "defense"):
        outer[role + "_assessment"]["historical_exposure"]["qualified"] = False
        outer[role + "_assessment"]["metrics"]["completion"].update(
            absolute_error=99, tolerance=0.1
        )
    summary["per_source_team"]["outer"] = outer
    result = qualified_training_objective(summary)
    assert result["loss"] == 1.0
    assert result["qualified_units"] == ["a/defense", "a/offense"]
    assert result["descriptive_only_units"] == ["outer/defense", "outer/offense"]
    outer["offense_assessment"]["metrics"]["completion"]["absolute_error"] = 0
    assert qualified_training_objective(summary) == result


def test_sparse_outer_unit_cannot_veto_qualified_unit_improvement() -> None:
    from tools.chartgen.training_selection import choose_training_candidate

    history = [candidate(0, 10, (10, 10)), candidate(1, 5, (5, 5))]
    for index, record in enumerate(history):
        outer = deepcopy(record["summary"]["per_source_team"]["a"])
        for role in ("offense", "defense"):
            outer[role + "_assessment"]["historical_exposure"]["qualified"] = False
            outer[role + "_assessment"]["loss"] = index * 1000
        record["summary"]["per_source_team"]["outer"] = outer
    result = choose_training_candidate(history)
    assert result["selected_candidate"] == 1
    assert result["descriptive_only_units"] == ["outer/defense", "outer/offense"]


def test_receipt_freezes_training_measurements_but_not_unrelated_timestamps(tmp_path: Path) -> None:
    from tools.chartgen.training_selection import seal_training_selection

    history = [candidate(0, 10, (10, 10)), candidate(1, 5, (5, 5))]
    a = seal_training_selection(tmp_path / "a.json", history, {"master_seed": 77})
    assert len(a["training_evidence_sha256"]) == 64
    history[1]["summary"]["completed_at"] = "different nondeterministic timestamp"
    assert a == seal_training_selection(tmp_path / "b.json", history, {"master_seed": 77})
    history[1]["summary"]["per_source_team"]["a"]["offense_assessment"]["metrics"]["completion"][
        "absolute_error"
    ] = 0.1
    b = seal_training_selection(tmp_path / "c.json", history, {"master_seed": 77})
    assert a["training_evidence_sha256"] != b["training_evidence_sha256"]


def test_unknown_engine_measurement_cannot_disappear_from_qualified_objective() -> None:
    from tools.chartgen.training_selection import qualified_training_objective

    summary = candidate(0, 10, (10, 10))["summary"]
    for role in ("offense", "defense"):
        summary["per_source_team"]["a"][role + "_assessment"]["metrics"]["completion"][
            "absolute_error"
        ] = None
    assert qualified_training_objective(summary)["loss"] == 10000.0
