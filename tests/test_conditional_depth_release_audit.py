"""Synthetic release-boundary regressions for the composed depth policy."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.models import Play, ResultKind
from bowl_bound.team_csv import load_team
from scripts import audit_generated_charts as audit
from tests.synthetic_teams import _with_legend_color, write_team
from tests.test_budget_chart_audit import budget_fixture
from tests.test_generated_chart_audit import repin
from tools.chart_depth_policy import apply_depth_policy, execution_identity


def declaration(key: str) -> dict:
    return {
        "identity": execution_identity(),
        "source_qualification_sha256": "9" * 64,
        "known_designed_call_depth_samples": {
            key: {f"{side}/{p}": 0 for side in ("offense", "defense") for p in range(6, 10)}
        },
    }


def test_declared_depth_policy_cannot_be_silently_ignored(tmp_path: Path) -> None:
    root, _, _, _, expected, key = budget_fixture(tmp_path)
    expected["conditional_depth"] = declaration(key)
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    # Existing schema two accepts Screen INT22 and ignores this declared policy.
    with pytest.raises(audit.ChartAuditError, match="conditional|depth"):
        audit.audit_candidate(root)


def test_parent_budget_without_depth_claim_remains_supported(tmp_path: Path) -> None:
    root, _, _, _, _, _ = budget_fixture(tmp_path)
    result = audit.audit_candidate(root)
    assert result["passed"]
    for team in result["teams"].values():
        assert team["fixed_whole_facts_preserved"] is True
        assert team["nondefensive_gameplay_preserved"] is True


def test_parent_budget_still_refuses_unrelated_model_identity(tmp_path: Path) -> None:
    root, _, _, _, expected, _ = budget_fixture(tmp_path)
    expected["model_identity"]["sha256"] = "0" * 64
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    with pytest.raises(audit.ChartAuditError, match="model identity"):
        audit.audit_candidate(root)


def depth_fixture(tmp_path: Path) -> tuple[Path, dict, str]:
    root, baseline, chart, meta, parent, key = budget_fixture(tmp_path)

    def add_offense(value):
        return replace(
            value,
            offense=tuple(
                replace(
                    r,
                    cell=_with_legend_color(
                        replace(r.cell, kind=ResultKind.INTERCEPTION, yards=44)
                    ),
                )
                if r.play is Play.SIX and r.roll == 18
                else r
                for r in value.offense
            ),
        )

    original, original_meta = load_team(baseline / "seasons/2007", "synthetic-generated")
    write_team(baseline / "seasons", add_offense(original), original_meta)
    repin(baseline)
    corrected, _ = apply_depth_policy(add_offense(chart), (), ())
    write_team(root / "seasons", corrected, meta)
    repin(root)
    qualification = tmp_path / "depth-qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "model_identity": parent["model_identity"],
                **{k: parent["source_review"][k] for k in audit.SOURCE_FIELDS},
                "conditional_depth": declaration(key),
            }
        )
    )
    expected = audit.build_expectations(root, baseline, qualification)
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    return root, expected, key


def test_composed_model_preserves_parent_contract_and_qualifies_depths(tmp_path: Path) -> None:
    root, expected, key = depth_fixture(tmp_path)
    assert expected["schema_version"] == 3
    result = audit.audit_candidate(root)
    assert result["passed"] and not result["source_truth_revalidated"]
    assert result["teams"][key]["family_budgets_preserved"]
    assert result["teams"][key]["conditional_depth"]["status"] == "PASS-exhaustive"
    assert result["teams"][key]["conditional_depth"]["historical_fit"] == "UNVERIFIED"


@pytest.mark.parametrize("mutation", ["missing", "unknown", "nonzero", "boolean", "identity"])
def test_incomplete_or_unqualified_source_cannot_become_zero_support(
    tmp_path: Path, mutation: str
) -> None:
    root, expected, key = depth_fixture(tmp_path)
    spec = expected["conditional_depth"]
    if mutation == "missing":
        del spec["known_designed_call_depth_samples"][key]["offense/6"]
    elif mutation == "unknown":
        spec["known_designed_call_depth_samples"][key]["offense/6"] = None
    elif mutation == "nonzero":
        spec["known_designed_call_depth_samples"][key]["offense/6"] = 1
    elif mutation == "boolean":
        spec["known_designed_call_depth_samples"][key]["offense/6"] = False
    else:
        spec["identity"]["contract"]["prior_equivalent_observations"] = 2
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    with pytest.raises(audit.ChartAuditError, match="conditional|depth"):
        audit.audit_candidate(root)


@pytest.mark.parametrize("mutation", ["unsupported", "supported_collapsed", "nondepth"])
def test_repin_cannot_hide_depth_or_other_semantic_corruption(
    tmp_path: Path, mutation: str
) -> None:
    root, _, _ = depth_fixture(tmp_path)
    chart, meta = load_team(root / "seasons/2007", "synthetic-generated")
    if mutation == "nondepth":
        rows = tuple(
            replace(r, cell=_with_legend_color(replace(r.cell, yards=999)))
            if r.play is Play.ONE and r.roll == 18
            else r
            for r in chart.offense
        )
    else:
        rows = tuple(
            replace(r, cell=replace(r.cell, yards=44 if mutation == "unsupported" else -3))
            if r.play is Play.SIX and r.cell.kind is ResultKind.INTERCEPTION
            else r
            for r in chart.offense
        )
    write_team(root / "seasons", replace(chart, offense=rows), meta)
    repin(root)
    with pytest.raises(audit.ChartAuditError):
        audit.audit_candidate(root)


def test_enumeration_unknown_is_a_release_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = depth_fixture(tmp_path)
    import tools.chart_depth_encoding_audit as checker

    monkeypatch.setattr(
        checker,
        "audit_chart_encoding",
        lambda *_a, **_k: {
            "status": "UNVERIFIED-enumeration-budget",
            "columns": {},
            "historical_fit": "UNVERIFIED",
        },
    )
    with pytest.raises(audit.ChartAuditError, match="conditional|depth"):
        audit.audit_candidate(root)


def test_explicit_unknown_depth_declaration_cannot_downgrade_builder(tmp_path: Path) -> None:
    root, _, _ = depth_fixture(tmp_path)
    qualification = tmp_path / "depth-qualification.json"
    value = json.loads(qualification.read_text())
    value["conditional_depth"] = None
    qualification.write_text(json.dumps(value))
    with pytest.raises(audit.ChartAuditError, match="conditional depth"):
        audit.build_expectations(root, tmp_path / "baseline", qualification)


@pytest.mark.parametrize(
    "module_name",
    [
        "tools.chart_depth_release_audit",
        "tools.chart_depth_encoding_audit",
        "tools.chart_depth_audit",
    ],
)
def test_foreign_imported_depth_checker_is_not_attested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module_name: str
) -> None:
    import importlib

    root, _, _ = depth_fixture(tmp_path)
    foreign = tmp_path / "foreign-checker.py"
    foreign.write_text("# foreign checker\n")
    monkeypatch.setattr(importlib.import_module(module_name), "__file__", str(foreign))
    with pytest.raises(audit.ChartAuditError, match="imported conditional depth"):
        audit.audit_candidate(root)


def test_changed_depth_report_qualifies_the_preserved_fact_boundary(tmp_path: Path) -> None:
    root, _, key = depth_fixture(tmp_path)
    result = audit.audit_candidate(root)
    team = result["teams"][key]
    assert "fixed_whole_facts_preserved" not in team
    assert "nondefensive_gameplay_preserved" not in team
    assert team["fixed_facts_except_passing_int_depths_preserved"] is True
    assert team["nondefensive_gameplay_except_passing_int_depths_preserved"] is True
