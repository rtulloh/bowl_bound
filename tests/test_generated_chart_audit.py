"""Synthetic release audit controls; no historical chart dependencies."""

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.models import Defense, NormalizedCell, Play, ResultKind
from scripts.audit_generated_charts import (
    POLICY_SHA256,
    POLICY_YARDS,
    ChartAuditError,
    _audit_roles,
    audit_candidate,
    baseline_record,
    build_expectations,
    main,
    policy_effect,
    weighted_distributions,
)
from tests.synthetic_teams import _with_legend_color, team_chart, write_team, yards
from tests.test_models import provenance


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def fixture(tmp_path: Path) -> tuple[Path, dict, object]:
    root = tmp_path / "candidate"
    baseline = team_chart("Synthetic Generated", season=2007, defense=0)
    key = write_team(root / "seasons", baseline)
    record = baseline_record(root, key)
    candidate = replace(
        baseline,
        defense=tuple(
            replace(r, cell=_with_legend_color(yards(policy_effect(r.play, r.defense))))
            for r in baseline.defense
        ),
    )
    write_team(root / "seasons", candidate)
    paths = [
        *[
            f"seasons/{key}/{name}"
            for name in ("offense.csv", "defense.csv", "special.csv", "team.yaml")
        ],
        "seasons/2007/provenance/synthetic-generated.csv",
    ]
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
    source = Path(__file__).resolve().parents[1]
    approved = json.loads((source / "release/manifest.json").read_text())
    runtime_core = [n for n in approved["runtime"] if n.startswith("bowl_bound/")]
    frontend = ["frontend/package.json", "frontend/package-lock.json"]
    (root / "frontend").mkdir()
    for name in frontend:
        shutil.copy2(source / name, root / name)
    (root / "release").mkdir()
    (root / "release/manifest.json").write_text(
        json.dumps(
            {
                "generated_sha256": hashes,
                "runtime": paths + runtime_core,
                "frontend": frontend,
                "sample_sha256": {},
            }
        )
    )
    identity = {
        "origin": "authored-bb-yardage-v1",
        "sha256": POLICY_SHA256,
        "authored_experimental": True,
        "tool_version": "college-chartgen-v6",
        "source_sha256": "a" * 64,
    }
    expected = {
        "schema_version": 1,
        "model_identity": identity,
        "source_review": {
            "normalized_source_sha256": "b" * 64,
            "source_review_sha256": "c" * 64,
            "oob_review_sha256": "d" * 64,
        },
        "teams": {key: record},
    }
    for name in Path(__file__).resolve().parents[1].joinpath("bowl_bound").glob("*.py"):
        (root / "bowl_bound").mkdir(exist_ok=True)
        shutil.copy2(name, root / "bowl_bound" / name.name)
    expected["source_review"]["candidate_sha256"] = digest(hashes)
    expected["source_review"]["baseline_expectations_sha256"] = digest(expected["teams"])
    (root / "release/generated-chart-audit.json").write_text(json.dumps(expected))
    return root, expected, baseline


def repin(root: Path) -> None:
    p = root / "release/manifest.json"
    m = json.loads(p.read_text())
    m["generated_sha256"] = {
        k: hashlib.sha256((root / k).read_bytes()).hexdigest() for k in m["generated_sha256"]
    }
    p.write_text(json.dumps(m))
    p = root / "release/generated-chart-audit.json"
    expected = json.loads(p.read_text())
    expected["source_review"]["candidate_sha256"] = hashlib.sha256(
        json.dumps(m["generated_sha256"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    p.write_text(json.dumps(expected))


def test_selected_policy_and_source_invariance_pass(tmp_path: Path) -> None:
    root, _, _ = fixture(tmp_path)
    result = audit_candidate(root)
    assert result["passed"]
    assert result["generated_teams"] == 1
    assert result["physical_defensive_mass"] == 36
    assert result["source_truth_revalidated"] is False
    assert result["candidate_sha256"] and result["engine_sha256"]


def test_native_stage_engine_identity_matches_source_without_development_modules(
    tmp_path: Path,
) -> None:
    from scripts.release_package import audit_staged_charts, stage_sources

    root, _, _ = fixture(tmp_path)
    source_report = audit_candidate(root)
    stage = tmp_path / "native-stage"
    stage_sources(root, stage)
    assert (root / "bowl_bound/coaching_audit.py").is_file()
    assert not (stage / "bowl_bound/coaching_audit.py").exists()
    staged_report = audit_staged_charts(root, stage)
    assert staged_report["passed"]
    assert staged_report["engine_sha256"] == source_report["engine_sha256"]
    assert staged_report["candidate_sha256"] == source_report["candidate_sha256"]
    assert not (stage / "release/generated-chart-audit.json").exists()


def test_neutral_defense_is_rejected_even_after_manifest_repin(tmp_path: Path) -> None:
    root, _, baseline = fixture(tmp_path)
    write_team(root / "seasons", baseline)
    repin(root)
    with pytest.raises(ChartAuditError, match="baseline|formation|tradeoff"):
        audit_candidate(root)


def test_different_rows_can_be_exactly_equal_physical_distributions() -> None:
    chart = team_chart("Equal Mass", season=2007, defense=0)
    chart = replace(
        chart,
        defense=tuple(
            replace(r, cell=yards(1))
            if (r.defense is Defense.A and r.roll == 1)
            or (r.defense is Defense.B and r.roll in {2, 5})
            else r
            for r in chart.defense
        ),
    )
    distributions = weighted_distributions(chart)
    assert distributions["A/1"] == distributions["B/1"]
    assert chart.defense[:5] != chart.defense[5:10]
    with pytest.raises(ChartAuditError, match="role|tradeoff"):
        _audit_roles(chart, chart, "2007/equal-mass")


@pytest.mark.parametrize("mutation", ["response", "oob", "protected", "wrong-role"])
def test_plausible_looking_corruption_fails(tmp_path: Path, mutation: str) -> None:
    root, _, baseline = fixture(tmp_path)
    records = []
    for r in baseline.defense:
        cell = yards(policy_effect(r.play, r.defense))
        if r.defense is Defense.B and r.play is Play.ONE:
            if mutation == "response" and r.roll == 5:
                cell = NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=17)
            elif mutation == "oob" and r.roll == 1:
                cell = replace(cell, out_of_bounds=True)
            elif mutation == "protected" and r.roll == 1:
                from bowl_bound.models import Priority

                cell = replace(cell, priority=Priority.PARENTHESIZED)
            elif mutation == "wrong-role":
                cell = yards(3)
        records.append(replace(r, cell=_with_legend_color(cell)))
    write_team(root / "seasons", replace(baseline, defense=tuple(records)))
    repin(root)
    with pytest.raises(ChartAuditError):
        audit_candidate(root)


@pytest.mark.parametrize("mutation", ["missing", "neutral-policy", "stale-files", "team-set"])
def test_missing_or_stale_expectations_fail_closed(tmp_path: Path, mutation: str) -> None:
    root, expected, _ = fixture(tmp_path)
    p = root / "release/generated-chart-audit.json"
    if mutation == "missing":
        p.unlink()
    elif mutation == "neutral-policy":
        expected["model_identity"]["sha256"] = "e" * 64
        p.write_text(json.dumps(expected))
    elif mutation == "team-set":
        expected["teams"] = {}
        p.write_text(json.dumps(expected))
    else:
        p = root / "seasons/2007/synthetic-generated/offense.csv"
        p.write_text(p.read_text() + "\n")
        repin(root)
    with pytest.raises(ChartAuditError):
        audit_candidate(root)


def test_policy_has_specialization_costs_not_universal_defense_boost() -> None:
    assert policy_effect(Play.ONE, Defense.B) < policy_effect(Play.ONE, Defense.A)
    assert policy_effect(Play.THREE, Defense.B) > policy_effect(Play.THREE, Defense.A)
    assert policy_effect(Play.SIX, Defense.F) > policy_effect(Play.SIX, Defense.A)
    assert all(sum(row) == 0 for row in POLICY_YARDS)


def test_role_gate_rejects_equal_mass_and_directional_dominance() -> None:
    neutral = team_chart("Counterplay", season=2007, defense=0)
    with pytest.raises(ChartAuditError, match="Equivalent formation"):
        _audit_roles(neutral, neutral, "2007/counterplay")
    dominant = replace(
        neutral,
        defense=tuple(
            replace(
                r, cell=yards(-10 if r.defense is Defense.F else policy_effect(r.play, r.defense))
            )
            for r in neutral.defense
        ),
    )
    with pytest.raises(ChartAuditError, match="role|dominance"):
        _audit_roles(dominant, neutral, "2007/counterplay")


def test_native_freeze_is_blocked_before_frontend_if_chart_audit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import build_standalone as native
    from scripts.release_package import ReleaseError

    root, _, neutral = fixture(tmp_path)
    write_team(root / "seasons", neutral)
    repin(root)
    monkeypatch.setattr(native, "check_target", lambda *args: "BowlBound.exe")
    monkeypatch.setattr(native, "verify_environment", lambda source: None)
    monkeypatch.setattr(
        native, "stage_sources", lambda source, stage: shutil.copytree(source, stage)
    )

    def forbidden(stage: Path) -> None:
        pytest.fail("Frontend/freezing started before chart audit rejection")

    monkeypatch.setattr(native, "build_frontend", forbidden)
    with pytest.raises(ReleaseError, match="chart audit"):
        native.build(root, tmp_path / "artifacts", "windows-x64")


def test_rejected_candidate_retains_machine_readable_report(tmp_path: Path) -> None:
    root, _, neutral = fixture(tmp_path)
    write_team(root / "seasons", neutral)
    repin(root)
    report = tmp_path / "evidence" / "rejected.json"
    assert main(["--root", str(root), "--report", str(report)]) == 1
    rejected = json.loads(report.read_text())
    assert rejected["passed"] is False
    assert rejected["reason"]
    assert rejected["policy_sha256"] == POLICY_SHA256
    assert rejected["candidate_sha256"]
    assert rejected["engine_sha256"]


def test_candidate_cannot_unselect_runtime_engine_module(tmp_path: Path) -> None:
    root, _, _ = fixture(tmp_path)
    path = root / "release/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["runtime"].remove("bowl_bound/timing.py")
    path.write_text(json.dumps(manifest))
    with pytest.raises(ChartAuditError, match="runtime core"):
        audit_candidate(root)


def test_different_candidate_engine_is_not_certified(tmp_path: Path) -> None:
    root, _, _ = fixture(tmp_path)
    p = root / "bowl_bound/resolution.py"
    p.write_text(p.read_text() + "\n# unreviewed engine change\n")
    with pytest.raises(ChartAuditError, match="engine differs"):
        audit_candidate(root)


def test_foreign_imported_resolver_is_not_reported_as_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import bowl_bound.resolution as resolver

    root, _, _ = fixture(tmp_path)
    foreign = tmp_path / "foreign-resolution.py"
    foreign.write_text("# Different imported resolver\n")
    monkeypatch.setattr(resolver, "__file__", str(foreign))
    with pytest.raises(ChartAuditError, match="imported engine"):
        audit_candidate(root)


def test_stale_source_review_cannot_certify_revised_catalog(tmp_path: Path) -> None:
    root, expected, _ = fixture(tmp_path)
    expected["source_review"]["candidate_sha256"] = "f" * 64
    (root / "release/generated-chart-audit.json").write_text(json.dumps(expected))
    with pytest.raises(ChartAuditError, match="stale"):
        audit_candidate(root)


@pytest.mark.parametrize("protected", [False, True])
def test_blank_explicit_zero_and_parenthesized_sign_roundtrip(
    tmp_path: Path, protected: bool
) -> None:
    from bowl_bound.models import Priority
    from scripts.audit_generated_charts import _defense_fingerprint, _restore_baseline

    root = tmp_path / "source"
    base = team_chart("Zero Control", season=2007, defense=0)
    records = []
    for r in base.defense:
        cell = NormalizedCell(ResultKind.NO_CHANGE, provenance())
        if r.roll != 1:
            cell = yards(-1 if r.roll == 2 else 0 if r.roll == 3 else 1)
            if protected:
                cell = replace(cell, priority=Priority.PARENTHESIZED)
        records.append(replace(r, cell=_with_legend_color(cell)))
    base = replace(base, defense=tuple(records))
    key = write_team(root / "seasons", base)
    record = baseline_record(root, key)
    adjusted = []
    for r in base.defense:
        value = (r.cell.yards or 0) + policy_effect(r.play, r.defense)
        cell = replace(r.cell, kind=ResultKind.YARDS, yards=value)
        adjusted.append(replace(r, cell=_with_legend_color(cell)))
    restored = _restore_baseline(replace(base, defense=tuple(adjusted)), record)
    assert _defense_fingerprint(restored) == _defense_fingerprint(base)


def test_builder_uses_pinned_baseline_and_does_not_issue_a_green_receipt(tmp_path: Path) -> None:
    root, expected, baseline_chart = fixture(tmp_path)
    baseline = tmp_path / "accepted-baseline"
    shutil.copytree(root, baseline)
    write_team(baseline / "seasons", baseline_chart)
    repin(baseline)
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "model_identity": expected["model_identity"],
                **{
                    key: expected["source_review"][key]
                    for key in (
                        "normalized_source_sha256",
                        "source_review_sha256",
                        "oob_review_sha256",
                    )
                },
            }
        )
    )
    exported = build_expectations(root, baseline, qualification)
    assert "passed" not in exported
    assert exported["teams"] == expected["teams"]
    assert exported["source_review"]["baseline_catalog_sha256"]
    (root / "release/generated-chart-audit.json").write_text(json.dumps(exported))
    assert audit_candidate(root)["passed"]


@pytest.mark.parametrize("private_key", ["private_narrative", "path", "passed"])
def test_qualification_export_rejects_unapproved_private_fields(
    tmp_path: Path, private_key: str
) -> None:
    root, expected, _ = fixture(tmp_path)
    qualification = tmp_path / "private-report.json"
    qualification.write_text(
        json.dumps(
            {
                "model_identity": expected["model_identity"],
                "normalized_source_sha256": "a" * 64,
                "source_review_sha256": "b" * 64,
                "oob_review_sha256": "c" * 64,
                private_key: "DO NOT EXPORT",
            }
        )
    )
    with pytest.raises(ChartAuditError, match="qualification fields"):
        build_expectations(root, root, qualification)


def test_native_workflow_requires_fresh_generated_chart_gate() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    tests = yaml.safe_load((root / ".github/workflows/tests.yml").read_text())
    steps = tests["jobs"]["test"]["steps"]
    audits = [s for s in steps if "python -m scripts.audit_generated_charts" in s.get("run", "")]
    assert len(audits) == 1
    assert not audits[0].get("continue-on-error", False)
    assert "if" not in audits[0]
    build = yaml.safe_load((root / ".github/workflows/build.yml").read_text())
    assert build["jobs"]["test"]["uses"] == "./.github/workflows/tests.yml"
    assert build["jobs"]["build"]["needs"] == "test"


@pytest.mark.parametrize("kind", [ResultKind.QUARTERBACK_TRAPPED, ResultKind.FUMBLE])
def test_primary_pending_qt_and_fumble_are_not_zero_yard_completions(kind: ResultKind) -> None:
    from bowl_bound.resolution import resolve_cells
    from scripts.audit_generated_charts import _primary

    neutral = team_chart("Pending Class", season=2007, defense=0)
    offense = yards(10)
    defense = NormalizedCell(ResultKind.NO_CHANGE, provenance())
    if kind is ResultKind.QUARTERBACK_TRAPPED:
        defense = NormalizedCell(kind, provenance())
    else:
        offense = NormalizedCell(kind, provenance(), yards=0)
    result = resolve_cells(offense, defense)
    assert result.kind is kind
    pending = replace(neutral, defense=tuple(replace(r, cell=defense) for r in neutral.defense))
    numeric_contribution, actual_classes = _primary(pending, Play.NINE, Defense.A, offense)
    _, completed_classes = _primary(neutral, Play.NINE, Defense.A, yards(0))
    assert numeric_contribution == 0  # Excluded from numeric contribution, not a resolved gain.
    assert sum(actual_classes.values()) == 36
    assert actual_classes != completed_classes
