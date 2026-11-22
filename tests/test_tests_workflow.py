"""DEV-059: automatic source validation is independent of manual native builds."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name: str) -> dict:
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_tests_runs_for_branch_pushes_pull_requests_and_native_gate_calls() -> None:
    data = workflow("tests.yml")
    assert data["name"] == "Tests"
    assert set(data["on"]) == {"push", "pull_request", "workflow_call"}
    assert data["on"]["push"]["branches"] == ["**"]
    assert "tags" not in data["on"]["push"]
    assert data["on"]["workflow_call"]["inputs"]["source_ref"]["type"] == "string"
    assert data["permissions"] == {"contents": "read"}
    assert data["concurrency"]["cancel-in-progress"] == "true"
    assert "github.workflow" in data["concurrency"]["group"]
    assert "github.ref" in data["concurrency"]["group"]


def test_automatic_gate_retains_the_whole_established_regression() -> None:
    data = workflow("tests.yml")
    assert set(data["jobs"]) == {"test", "coverage", "browser", "windows-terms-dialog"}
    assert "needs" not in data["jobs"]["browser"]
    job = data["jobs"]["test"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert int(job["timeout-minutes"]) == 60
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    for required in (
        "python -m venv .venv",
        ".[dev,web,pdf]",
        ".venv/bin/python -m pytest -p scripts.pytest_shard --cov --cov-report= "
        "--cov-fail-under=0 -n 2 --dist=loadgroup --durations=25 -q",
        ".venv/bin/python -m ruff check .",
        ".venv/bin/python -m ruff format --check .",
        ".venv/bin/python -m pip check",
    ):
        assert required in commands
    shard_count = int(data["env"]["BB_TEST_SHARDS"])
    assert list(map(int, job["strategy"]["matrix"]["shard"])) == list(range(shard_count))
    assert job["env"]["BB_TEST_SHARD"] == "${{ matrix.shard }}"
    coverage_job = data["jobs"]["coverage"]
    assert coverage_job["needs"] == "test"
    coverage_commands = "\n".join(step.get("run", "") for step in coverage_job["steps"])
    assert 'test -s "coverage-data/.coverage.$shard"' in coverage_commands
    assert "coverage combine coverage-data" in coverage_commands
    assert "coverage report" in coverage_commands
    browser_job = data["jobs"]["browser"]
    commands = "\n".join(step.get("run", "") for step in browser_job["steps"])
    for required in (
        "npm ci --ignore-scripts",
        "npm test",
        "npm run build",
        "npx playwright install --with-deps chromium",
        "npm run test:e2e",
    ):
        assert required in commands
    browser = next(
        step
        for step in browser_job["steps"]
        if step.get("name") == "Real-engine browser regression"
    )
    assert browser["working-directory"] == "frontend"
    assert "runner.temp" in browser["env"]["BB_E2E_SEASONS"]


def test_manual_native_workflow_reuses_tests_for_the_same_requested_commit() -> None:
    native, source = workflow("build.yml"), workflow("tests.yml")
    assert native["name"] == "Build and Release Standalone Executables"
    assert set(native["on"]) == {"workflow_dispatch"}
    assert native["on"]["workflow_dispatch"]["inputs"]["source_ref"]["type"] == "string"
    assert native["permissions"] == {"contents": "read"}
    gate = native["jobs"]["test"]
    assert gate["permissions"] == {"contents": "read", "actions": "read"}
    assert any("scripts.verify_source_gate" in step.get("run", "") for step in gate["steps"])
    assert native["jobs"]["build"]["needs"] == "test"
    checkout = native["jobs"]["build"]["steps"][0]
    test_checkout = next(
        step
        for step in source["jobs"]["test"]["steps"]
        if step.get("uses", "").startswith("actions/checkout@")
    )
    expected = "${{ inputs.source_ref || github.sha }}"
    assert checkout["with"]["ref"] == "${{ needs.test.outputs.source_ref }}"
    verifier = next(
        step for step in gate["steps"] if "scripts.verify_source_gate" in step.get("run", "")
    )
    assert verifier["env"]["SOURCE_REF"] == test_checkout["with"]["ref"] == expected
    assert native["env"] == {key: source["env"][key] for key in native["env"]}


def test_both_workflows_retain_exact_pins_and_propagate_failures_without_publication() -> None:
    for name in ("tests.yml", "build.yml"):
        data = workflow(name)
        assert data["env"]["PYTHON_VERSION"] == "3.12.16"
        assert data["env"]["NODE_VERSION"] == "24.22.1"
        text = (ROOT / ".github/workflows" / name).read_text()
        assert "continue-on-error" not in text
        assert "contents: write" not in text and "secrets:" not in text
        assert "gh release" not in text and "action-gh-release" not in text
        for job in data["jobs"].values():
            for step in job.get("steps", ()):
                if "uses" in step:
                    assert re.fullmatch(r"actions/[a-z-]+@[a-f0-9]{40}", step["uses"])
                assert "continue-on-error" not in step
                assert "|| true" not in step.get("run", "")
                if step.get("shell") == "pwsh":
                    assert "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }" in step["run"]


def test_requested_native_source_is_an_immutable_commit_before_checkout() -> None:
    steps = workflow("tests.yml")["jobs"]["test"]["steps"]
    guard = next(step for step in steps if step.get("name") == "Validate requested source commit")
    assert steps.index(guard) < next(
        index
        for index, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/checkout@")
    )
    assert guard["env"]["SOURCE_REF"] == "${{ inputs.source_ref || github.sha }}"
    assert "^[0-9a-f]{40}$" in guard["run"]
    assert "exit 1" in guard["run"]


@pytest.mark.parametrize(
    "source_ref,expected",
    [
        ("a" * 40, 0),
        ("03d1992d3a3811cf89879bce985e23937e3a3dc0", 0),
        ("main", 1),
        ("v0.1.0-alpha.4", 1),
        ("a" * 39, 1),
        ("bad\n$(exit 0)", 1),
    ],
)
def test_source_commit_guard_rejects_mutable_or_malformed_refs(
    source_ref: str, expected: int
) -> None:
    guard = next(
        step
        for step in workflow("tests.yml")["jobs"]["test"]["steps"]
        if step.get("name") == "Validate requested source commit"
    )
    result = subprocess.run(
        ["bash", "-c", guard["run"]],
        env={**os.environ, "SOURCE_REF": source_ref},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected
    if expected:
        assert "source_ref must be a full 40-character commit SHA" in result.stdout


def test_dependency_audit_is_visible_in_a_separate_workflow() -> None:
    source = workflow("tests.yml")
    data = workflow("dependency-audit.yml")
    assert data["name"] == "Dependency audit"
    assert set(data["on"]) == {"push", "pull_request", "workflow_dispatch"}
    assert data["permissions"] == {"contents": "read"}
    assert data["env"]["NODE_VERSION"] == source["env"]["NODE_VERSION"]
    assert "workflow_call" not in data["on"]
    audit = data["jobs"]["dependency-audit"]
    assert audit["runs-on"] == "ubuntu-24.04"
    assert int(audit["timeout-minutes"]) == 10
    assert "needs" not in audit
    steps = audit["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] == "false"
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "npm ci --ignore-scripts" in commands
    assert "python -m scripts.check_frontend_audit" in commands
    assert '--report "$RUNNER_TEMP/npm-audit.json"' in commands
    assert any(
        step.get("if") == "always()"
        and step.get("with", {}).get("path") == "${{ runner.temp }}/npm-audit.json"
        for step in steps
    )
    assert "npm audit" not in "\n".join(
        step.get("run", "") for step in source["jobs"]["test"]["steps"]
    )
    for step in steps:
        assert "continue-on-error" not in step
        assert "|| true" not in step.get("run", "")
        if "uses" in step:
            assert re.fullmatch(r"actions/[a-z-]+@[a-f0-9]{40}", step["uses"])


def test_reviewed_generator_runtime_is_checked_before_expensive_regression() -> None:
    steps = workflow("tests.yml")["jobs"]["test"]["steps"]
    preflight = next(
        step
        for step in steps
        if step.get("name") == "Verify reviewed generator runtime before regression"
    )
    install = next(step for step in steps if step.get("name") == "Install source test dependencies")
    regression = next(
        step for step in steps if step.get("name") == "Python tests with branch coverage"
    )
    assert steps.index(install) < steps.index(preflight) < steps.index(regression)
    assert (
        preflight["run"]
        == '.venv/bin/python -c "from tools.chartgen.refine import engine_identity; '
        'engine_identity()"'
    )
    assert "if" not in preflight and "continue-on-error" not in preflight


def test_windows_dialog_probe_is_mandatory_parallel_pinned_and_retains_evidence() -> None:
    job = workflow("tests.yml")["jobs"]["windows-terms-dialog"]
    assert job["runs-on"] == "windows-2025"
    assert job["env"] == {"PYTHON_VERSION": "3.12.10"}
    assert int(job["timeout-minutes"]) == 10
    assert "needs" not in job and "if" not in job and "continue-on-error" not in job
    steps = job["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ inputs.source_ref || github.sha }}"
    assert checkout["with"]["persist-credentials"] == "false"
    probe = next(step for step in steps if "scripts.smoke_windows_terms" in step.get("run", ""))
    assert probe["shell"] == "pwsh"
    assert "--source-dialog WINDOWS-RUNTIME-TERMS.txt" in probe["run"]
    assert '--report "$env:RUNNER_TEMP/windows-terms-source.json"' in probe["run"]
    assert "if" not in probe and "continue-on-error" not in probe
    evidence = next(
        step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert evidence["if"] == "always()"
    assert evidence["with"]["name"] == "windows-terms-source-${{ github.run_id }}"
    assert "windows-terms-source.json" in evidence["with"]["path"]


def test_failed_macos_launch_captures_workflow_bound_tools_without_changing_payload_source() -> (
    None
):
    steps = workflow("build.yml")["jobs"]["build"]["steps"]
    checkout = next(
        step for step in steps if step.get("name") == "Check out failed-launch diagnostic tools"
    )
    assert checkout["if"] == "failure() && startsWith(matrix.target, 'macos-')"
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert checkout["with"]["path"] == ".native-diagnostics"
    assert checkout["with"]["persist-credentials"] == "false"
    capture = next(
        step for step in steps if step.get("name") == "Capture failed Finder launch evidence"
    )
    assert capture["if"] == checkout["if"]
    assert "--source-ref" in capture["run"]
    assert "needs.test.outputs.source_ref" in capture["env"]["SOURCE_REF"]
    assert "--workflow-ref" in capture["run"] and "github.sha" in capture["env"]["WORKFLOW_REF"]
    assert "macos_finder_diagnostics.py" in capture["run"]
    evidence = next(
        step for step in steps if step.get("name") == "Retain unqualified macOS failure resources"
    )
    assert evidence["if"] == checkout["if"]
    assert "finder-diagnostics" in evidence["with"]["path"]
    assert "*.zip" in evidence["with"]["path"]
    assert "unqualified" in evidence["with"]["name"]
    assert steps.index(capture) > next(
        i for i, step in enumerate(steps) if step.get("name") == "Build and smoke macOS disk image"
    )


def test_source_format_and_dependency_checks_precede_expensive_regression() -> None:
    text = Path(".github/workflows/tests.yml").read_text()
    for command in ("ruff check .", "ruff format --check .", "pip check"):
        assert text.index(command) < text.index("-m pytest -p scripts.pytest_shard --cov")
