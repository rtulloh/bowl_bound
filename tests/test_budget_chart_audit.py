"""Synthetic schema-two release checks; no historical team inputs."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.models import Defense, NormalizedCell, Play, Priority, ResultKind, TeamChart
from bowl_bound.team_csv import TeamFileMetadata, format_cell, load_team
from scripts import audit_generated_charts as audit
from tests.synthetic_teams import _with_legend_color, metadata, write_team, yards
from tests.test_generated_chart_audit import fixture, repin
from tests.test_models import provenance


def rebase(chart: TeamChart, source: str = "e" * 64) -> tuple[TeamChart, TeamFileMetadata]:
    def cell(value: NormalizedCell) -> NormalizedCell:
        assert value.provenance is not None
        return replace(
            value,
            provenance=replace(
                value.provenance,
                source_sha256=source,
                filename="synthetic-derived-model.json",
                original_text=format_cell(value),
            ),
        )

    result = replace(
        chart,
        offense=tuple(replace(r, cell=cell(r.cell)) for r in chart.offense),
        supplemental=tuple(replace(r, cell=cell(r.cell)) for r in chart.supplemental),
        defense=tuple(replace(r, cell=cell(r.cell)) for r in chart.defense),
        special_teams=tuple(replace(r, cell=cell(r.cell)) for r in chart.special_teams),
        pat_outcomes=tuple(
            replace(
                r,
                provenance=replace(
                    r.provenance, source_sha256=source, filename="synthetic-derived-model.json"
                ),
            )
            for r in chart.pat_outcomes
        ),
    )
    meta = metadata()
    meta = replace(
        meta,
        source_sha256=source,
        evidence=tuple(
            (k, replace(v, source_sha256=source, filename="synthetic-derived-model.json"))
            for k, v in meta.evidence
        ),
    )
    return result, meta


def budget_fixture(tmp_path: Path) -> tuple[Path, Path, TeamChart, TeamFileMetadata, dict, str]:
    root, legacy, _ = fixture(tmp_path)
    key = next(iter(legacy["teams"]))
    original, _ = load_team(root / "seasons/2007", "synthetic-generated")
    records = []
    for r in original.defense:
        value = r.cell
        if r.play.value >= 6:
            if r.roll == 4:
                value = NormalizedCell(ResultKind.INCOMPLETE, provenance())
            elif r.roll == 5:
                value = NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=17)
        records.append(replace(r, cell=_with_legend_color(value)))
    baseline_chart = replace(original, defense=tuple(records))
    baseline = tmp_path / "baseline"
    shutil.copytree(root, baseline)
    write_team(baseline / "seasons", baseline_chart)
    repin(baseline)
    changed = []
    for r in baseline_chart.defense:
        value = r.cell
        if r.play is Play.SIX:
            if r.defense is Defense.D and r.roll in {3, 4}:
                value = (
                    NormalizedCell(ResultKind.INCOMPLETE, provenance()) if r.roll == 3 else yards(0)
                )
            elif r.defense in {Defense.E, Defense.F} and r.roll == 4:
                value = yards(0)
        if value.kind is ResultKind.INTERCEPTION:
            value = replace(value, yards=3 if r.defense is Defense.A else 22)
        changed.append(replace(r, cell=_with_legend_color(value)))
    candidate, meta = rebase(replace(baseline_chart, defense=tuple(changed)))
    write_team(root / "seasons", candidate, meta)
    repin(root)
    identity = {
        "origin": "authored-bb-budget-aware-v1",
        "sha256": getattr(audit, "BUDGET_MODEL_SHA256", "f" * 64),
        "authored_experimental": True,
        "tool_version": getattr(audit, "BUDGET_TOOL_VERSION", "college-chartgen-budget-v1"),
        "source_sha256": "a" * 64,
    }
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "model_identity": identity,
                **{k: legacy["source_review"][k] for k in audit.SOURCE_FIELDS},
            }
        )
    )
    expected = audit.build_expectations(root, baseline, qualification)
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    return root, baseline, candidate, meta, expected, key


def test_budget_model_allows_declared_response_redistribution_and_derived_provenance(
    tmp_path: Path,
) -> None:
    root, _, _, _, expected, key = budget_fixture(tmp_path)
    assert expected["schema_version"] == 2
    result = audit.audit_candidate(root)
    assert result["passed"] and result["source_truth_revalidated"] is False
    team = result["teams"][key]
    assert team["family_budgets_preserved"] is True
    assert team["primary_physical_mass"] == 7776
    assert team["source_fit"] == "UNVERIFIED"
    assert any(r["status"] == "limited" for r in team["roles"].values())
    assert any(r["status"] == "dormant" for r in team["roles"].values())


@pytest.mark.parametrize(
    "mutation",
    [
        "family",
        "formation-int",
        "fixed",
        "oob",
        "variable",
        "run",
        "nondefense",
        "rating",
        "markers",
        "role-reversal",
    ],
)
def test_repin_cannot_hide_budget_or_semantic_corruption(tmp_path: Path, mutation: str) -> None:
    root, _, chart, meta, _, _ = budget_fixture(tmp_path)
    records = list(chart.defense)

    def change(formation: Defense, play: int, roll: int, cell: NormalizedCell) -> None:
        for i, r in enumerate(records):
            if (r.defense, r.play.value, r.roll) == (formation, play, roll):
                records[i] = replace(r, cell=_with_legend_color(cell))
                return
        raise AssertionError("fixture coordinate missing")

    if mutation == "family":
        change(Defense.B, 7, 1, NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
    elif mutation == "formation-int":
        # Keep call INT total unchanged, alter conserved formation totals.
        change(Defense.A, 6, 5, yards(0))
        change(Defense.B, 6, 4, NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=9))
        change(Defense.B, 6, 5, yards(0))
        change(Defense.C, 6, 5, yards(0))
    elif mutation == "fixed":
        change(Defense.A, 6, 1, replace(yards(0), priority=Priority.PARENTHESIZED))
    elif mutation == "oob":
        change(Defense.A, 6, 1, replace(yards(0), out_of_bounds=True))
    elif mutation == "variable":
        from bowl_bound.models import VariableReference

        change(
            Defense.A,
            6,
            5,
            NormalizedCell(
                ResultKind.INTERCEPTION,
                provenance(),
                variable=VariableReference.X,
                variable_multiplier=1,
            ),
        )
    elif mutation == "run":
        change(Defense.A, 1, 1, yards(7))
    elif mutation == "nondefense":
        chart = replace(
            chart,
            supplemental=tuple(
                replace(r, cell=_with_legend_color(yards(11))) for r in chart.supplemental
            ),
        )
    elif mutation == "rating":
        meta = replace(meta, power_rating=meta.power_rating + 1)
    elif mutation == "markers":
        meta = replace(meta, defense_chart_markers=("W",))
    else:
        # Exchange D/E INC masses: budgets and fixed domains are unchanged, but D reverses.
        for f in (Defense.D, Defense.E):
            for roll in (3, 4):
                inc = f is Defense.E and roll == 3
                change(
                    f,
                    6,
                    roll,
                    NormalizedCell(ResultKind.INCOMPLETE, provenance()) if inc else yards(0),
                )
    chart = replace(chart, defense=tuple(records))
    chart, rebased = rebase(chart)
    meta = replace(
        rebased, power_rating=meta.power_rating, defense_chart_markers=meta.defense_chart_markers
    )
    write_team(root / "seasons", chart, meta)
    repin(root)
    with pytest.raises(audit.ChartAuditError):
        audit.audit_candidate(root)


@pytest.mark.parametrize("mutation", ["model", "version", "bool-budget", "stale-baseline"])
def test_budget_expectations_fail_closed(tmp_path: Path, mutation: str) -> None:
    root, _, _, _, expected, key = budget_fixture(tmp_path)
    if mutation == "model":
        expected["model_identity"]["sha256"] = "0" * 64
    elif mutation == "version":
        expected["schema_version"] = True
    elif mutation == "bool-budget":
        expected["teams"][key]["call_family_mass"]["6"]["INC"] = True
    else:
        expected["source_review"]["baseline_catalog_sha256"] = "not-a-hash"
    expected["source_review"]["baseline_expectations_sha256"] = digest(expected["teams"])
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    with pytest.raises(audit.ChartAuditError):
        audit.audit_candidate(root)


def digest(value: object) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_budget_source_and_native_stage_audit_the_same_installed_objects(tmp_path: Path) -> None:
    from scripts.release_package import audit_staged_charts, stage_sources

    root, _, _, _, _, _ = budget_fixture(tmp_path)
    before = audit.audit_candidate(root)
    stage = tmp_path / "stage"
    stage_sources(root, stage)
    after = audit_staged_charts(root, stage)
    assert after["model_identity"] == before["model_identity"]
    assert after["candidate_sha256"] == before["candidate_sha256"]
    assert after["teams"] == before["teams"]


def test_budget_gate_does_not_certify_neutral_run_tactics(tmp_path: Path) -> None:
    root, baseline, chart, meta, expected, _ = budget_fixture(tmp_path)
    for path in (root, baseline):
        original, original_meta = load_team(path / "seasons/2007", "synthetic-generated")
        original = replace(
            original,
            defense=tuple(
                replace(r, cell=_with_legend_color(replace(r.cell, kind=ResultKind.YARDS, yards=0)))
                if r.play.value <= 5
                else r
                for r in original.defense
            ),
        )
        write_team(path / "seasons", original, original_meta)
        repin(path)
    qualification = tmp_path / "qualification.json"
    expected = audit.build_expectations(root, baseline, qualification)
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    with pytest.raises(audit.ChartAuditError, match="run|tactic"):
        audit.audit_candidate(root)


def test_pressure_overshoot_is_explicit_residual_not_requested_attainment(tmp_path: Path) -> None:
    _, _, chart, meta, _, _ = budget_fixture(tmp_path)
    chart = replace(
        chart,
        defense=tuple(
            replace(
                r,
                cell=_with_legend_color(
                    NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance())
                ),
            )
            if (r.defense, r.play, r.roll) == (Defense.F, Play.SEVEN, 3)
            else r
            for r in chart.defense
        ),
    )
    result = audit._audit_budget(chart, meta, audit._budget_record(chart, meta), "synthetic")
    role = result["roles"]["F/7/QT"]
    assert role["requested"] == 3 and role["represented"] == 9
    assert role["residual"] == 6 and role["status"] == "limited"
    assert result["optimizer_optimality_revalidated"] is False


def test_rejected_budget_report_names_the_supported_successor_model(tmp_path: Path) -> None:
    root, _, _, _, expected, _ = budget_fixture(tmp_path)
    expected["model_identity"]["sha256"] = "0" * 64
    (root / audit.EXPECTATIONS).write_text(json.dumps(expected))
    report = tmp_path / "rejected.json"
    assert audit.main(["--root", str(root), "--report", str(report)]) == 1
    rejected = json.loads(report.read_text())
    assert rejected["schema_version"] == 2
    assert rejected["policy_sha256"] == audit.BUDGET_MODEL_SHA256
    assert rejected["passed"] is False


@pytest.mark.parametrize("play", [6, 8])
def test_budget_counterplay_may_redistribute_nonpressure_anchor_qt(
    tmp_path: Path, play: int
) -> None:
    root, baseline, chart, meta, _, key = budget_fixture(tmp_path)
    original, original_meta = load_team(baseline / "seasons/2007", "synthetic-generated")
    qt = _with_legend_color(NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
    old = replace(
        original,
        defense=tuple(
            replace(r, cell=qt)
            if r.defense is Defense.A and r.play.value == play and r.roll == 2
            else r
            for r in original.defense
        ),
    )
    candidate = replace(
        chart,
        defense=tuple(
            replace(r, cell=qt)
            if r.defense is Defense.B and r.play.value == play and r.roll == 2
            else r
            for r in chart.defense
        ),
    )
    report = audit._audit_budget(candidate, meta, audit._budget_record(old, original_meta), key)
    assert report["family_budgets_preserved"] is True
    assert report["roles"][f"F/{play}/noncompletion"]["represented"] >= 0


@pytest.mark.parametrize("play", [7, 9])
def test_budget_pressure_anchor_qt_still_cannot_move(tmp_path: Path, play: int) -> None:
    _, baseline, chart, meta, _, key = budget_fixture(tmp_path)
    original, original_meta = load_team(baseline / "seasons/2007", "synthetic-generated")
    qt = _with_legend_color(NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
    old = replace(
        original,
        defense=tuple(
            replace(r, cell=qt)
            if r.defense is Defense.A and r.play.value == play and r.roll == 2
            else r
            for r in original.defense
        ),
    )
    candidate = replace(
        chart,
        defense=tuple(
            replace(r, cell=qt)
            if r.defense is Defense.B and r.play.value == play and r.roll == 2
            else r
            for r in chart.defense
        ),
    )
    with pytest.raises(audit.ChartAuditError, match="family budgets"):
        audit._audit_budget(candidate, meta, audit._budget_record(old, original_meta), key)
