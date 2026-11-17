"""Synthetic multi-season release audits preserve each reviewed cohort contract."""

import copy
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.team_csv import load_team
from scripts import audit_generated_charts as audit
from tests.synthetic_teams import _with_legend_color, write_team
from tests.test_conditional_depth_release_audit import depth_fixture
from tests.test_generated_chart_audit import fixture


def combined_fixture(tmp_path: Path, *, modern: bool = False) -> tuple[Path, dict]:
    roots = {}
    expectations = {}
    for season in ("2002", "2007"):
        directory = tmp_path / season
        directory.mkdir()
        root, expected, _ = depth_fixture(directory) if modern else fixture(directory)
        if season == "2002":
            # The fixture's metadata says 2007; rewrite through the ordinary codec.
            chart, metadata = load_team(root / "seasons/2007", "synthetic-generated")
            chart = replace(chart, season=2002)
            write_team(root / "seasons", chart, metadata)
            manifest = json.loads((root / "release/manifest.json").read_text())
            pins = {
                name.replace("/2007/", "/2002/"): hashlib.sha256(
                    (root / name.replace("/2007/", "/2002/")).read_bytes()
                ).hexdigest()
                for name in manifest["generated_sha256"]
            }
            manifest["runtime"] = [name.replace("/2007/", "/2002/") for name in manifest["runtime"]]
            manifest["generated_sha256"] = pins
            (root / "release/manifest.json").write_text(json.dumps(manifest))
            expected["teams"] = {
                key.replace("2007/", "2002/"): value for key, value in expected["teams"].items()
            }
            # Rebind the synthetic baseline to the changed season identity.
            record = next(iter(expected["teams"].values()))
            if "nondefensive_sha256" in record:
                record["nondefensive_sha256"]["team.yaml"] = pins[
                    "seasons/2002/synthetic-generated/team.yaml"
                ]
            if modern:
                baseline_chart, baseline_metadata = load_team(
                    directory / "baseline/seasons/2007", "synthetic-generated"
                )
                expected["teams"]["2002/synthetic-generated"] = audit._budget_record(
                    replace(baseline_chart, season=2002), baseline_metadata, ignore_int_depths=True
                )
                expected["conditional_depth"]["known_designed_call_depth_samples"] = {
                    key.replace("2007/", "2002/"): value
                    for key, value in expected["conditional_depth"][
                        "known_designed_call_depth_samples"
                    ].items()
                }
                expected["model_identity"].update(
                    origin="authored-bb-cohort-v1",
                    sha256=audit.COHORT_MODEL_SHA256,
                    tool_version=audit.COHORT_TOOL_VERSION,
                )
            expected["source_review"]["candidate_sha256"] = audit._digest(pins)
            expected["source_review"]["baseline_expectations_sha256"] = audit._digest(
                expected["teams"]
            )
        roots[season] = root
        expectations[season] = expected
    root = roots["2007"]
    shutil.copytree(roots["2002"] / "seasons/2002", root / "seasons/2002")
    manifest = json.loads((root / "release/manifest.json").read_text())
    other = json.loads((roots["2002"] / "release/manifest.json").read_text())
    manifest["generated_sha256"].update(other["generated_sha256"])
    manifest["runtime"].extend(name for name in other["runtime"] if name not in manifest["runtime"])
    (root / "release/manifest.json").write_text(json.dumps(manifest))
    expected = {"schema_version": 4, "cohorts": expectations}
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    return root, expected


def test_separate_cohort_contracts_pass_without_relabeling_earlier_review(tmp_path: Path) -> None:
    root, expected = combined_fixture(tmp_path)
    saved = copy.deepcopy(expected)
    result = audit.audit_candidate(root)
    assert result["passed"] is True and result["generated_teams"] == 2
    assert result["source_truth_revalidated"] is False
    assert set(result["teams"]) == {"2002/synthetic-generated", "2007/synthetic-generated"}
    assert (
        result["cohorts"]["2007"]["source_review"] == expected["cohorts"]["2007"]["source_review"]
    )
    assert json.loads((root / audit.EXPECTATIONS).read_text()) == saved


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-cohort",
        "wrong-season",
        "overlap",
        "stale-source",
        "unknown-schema",
        "nested-envelope",
        "extra-field",
        "repinned-chart",
    ],
)
def test_each_cohort_is_required_and_independently_revalidated(
    tmp_path: Path, mutation: str
) -> None:
    root, expected = combined_fixture(tmp_path)
    if mutation == "missing-cohort":
        del expected["cohorts"]["2002"]
    elif mutation == "wrong-season":
        expected["cohorts"]["2003"] = expected["cohorts"].pop("2002")
    elif mutation == "overlap":
        expected["cohorts"]["2002"]["teams"].update(expected["cohorts"]["2007"]["teams"])
    elif mutation == "stale-source":
        expected["cohorts"]["2002"]["source_review"]["candidate_sha256"] = "0" * 64
    elif mutation == "unknown-schema":
        expected["cohorts"]["2002"]["schema_version"] = 99
    elif mutation == "nested-envelope":
        expected["cohorts"]["2002"] = copy.deepcopy(expected)
    elif mutation == "extra-field":
        expected["waive_source_review"] = True
    elif mutation == "repinned-chart":
        chart, metadata = load_team(root / "seasons/2002", "synthetic-generated")
        write_team(
            root / "seasons",
            replace(
                chart,
                defense=tuple(
                    replace(row, cell=_with_legend_color(replace(row.cell, yards=999)))
                    if row.cell.yards is not None
                    else row
                    for row in chart.defense
                ),
            ),
            metadata,
        )
        manifest_path = root / "release/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["generated_sha256"] = {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in manifest["generated_sha256"]
        }
        manifest_path.write_text(json.dumps(manifest))
        pins = {
            name: value
            for name, value in manifest["generated_sha256"].items()
            if name.startswith("seasons/2002/")
        }
        expected["cohorts"]["2002"]["source_review"]["candidate_sha256"] = audit._digest(pins)
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    with pytest.raises(audit.ChartAuditError):
        audit.audit_candidate(root)


@pytest.mark.parametrize("changed_season", [None, "2002", "2007"])
def test_mixed_current_models_keep_each_depth_guard(
    tmp_path: Path, changed_season: str | None
) -> None:
    root, expected = combined_fixture(tmp_path, modern=True)
    if changed_season is not None:
        key = f"{changed_season}/synthetic-generated"
        expected["cohorts"][changed_season]["conditional_depth"][
            "known_designed_call_depth_samples"
        ][key]["offense/6"] = None
        (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
        with pytest.raises(audit.ChartAuditError, match="conditional depth"):
            audit.audit_candidate(root)
    else:
        result = audit.audit_candidate(root)
        assert {record["conditional_depth"]["status"] for record in result["teams"].values()} == {
            "PASS-exhaustive"
        }
        assert result["cohorts"]["2002"]["model_identity"]["origin"] == "authored-bb-cohort-v1"
        assert (
            result["cohorts"]["2007"]["model_identity"]["origin"] == "authored-bb-budget-aware-v1"
        )


def test_rejected_cohort_envelope_does_not_claim_legacy_single_policy(tmp_path: Path) -> None:
    root, expected = combined_fixture(tmp_path)
    del expected["cohorts"]["2002"]
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    report = tmp_path / "rejected.json"
    assert audit.main(["--root", str(root), "--report", str(report)]) == 1
    rejected = json.loads(report.read_text())
    assert rejected["passed"] is False
    assert rejected["schema_version"] == 4
    assert "policy_sha256" not in rejected
    assert rejected["source_truth_revalidated"] is False
