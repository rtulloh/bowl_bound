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


def test_expanded_gate_has_independent_source_identical_python_and_web_budgets() -> None:
    """DATA-021: browser time cannot consume the Python job's remaining budget."""
    data = workflow("tests.yml")
    assert set(data["jobs"]) == {"test", "web"}
    for name, timeout in (("test", 45), ("web", 15)):
        job = data["jobs"][name]
        assert int(job["timeout-minutes"]) == timeout
        assert "needs" not in job and "if" not in job
        steps = job["steps"]
        guard_index = next(
            i
            for i, step in enumerate(steps)
            if step.get("name") == "Validate requested source commit"
        )
        checkout_index = next(
            i
            for i, step in enumerate(steps)
            if step.get("uses", "").startswith("actions/checkout@")
        )
        assert guard_index < checkout_index
        assert steps[guard_index]["env"]["SOURCE_REF"] == "${{ inputs.source_ref || github.sha }}"
        assert steps[checkout_index]["with"]["ref"] == "${{ inputs.source_ref || github.sha }}"
        assert all("if" not in step for step in steps)

    native = workflow("build.yml")
    assert native["jobs"]["test"]["uses"] == "./.github/workflows/tests.yml"
    assert native["jobs"]["build"]["needs"] == "test"


def test_automatic_gate_retains_the_whole_established_regression() -> None:
    data = workflow("tests.yml")
    assert set(data["jobs"]) == {"test", "web"}
    job = data["jobs"]["test"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert int(job["timeout-minutes"]) == 45
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    for required in (
        "python -m venv .venv",
        ".[dev,web,pdf]",
        ".venv/bin/python -m pytest --cov --cov-report=term-missing -q",
        ".venv/bin/python -m ruff check .",
        ".venv/bin/python -m ruff format --check .",
        ".venv/bin/python -m pip check",
    ):
        assert required in commands
    web = data["jobs"]["web"]
    assert web["runs-on"] == "ubuntu-24.04"
    assert int(web["timeout-minutes"]) == 15
    commands = "\n".join(step.get("run", "") for step in web["steps"])
    for required in (
        "python -m venv .venv",
        ".[dev,web,pdf]",
        "npm ci --ignore-scripts",
        "npm test",
        "npm run build",
        "npm audit",
        "npx playwright install --with-deps chromium",
        "npm run test:e2e",
    ):
        assert required in commands
    browser = next(
        step for step in web["steps"] if step.get("name") == "Real-engine browser regression"
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
    assert gate["uses"] == "./.github/workflows/tests.yml"
    assert native["jobs"]["build"]["needs"] == "test"
    checkout = native["jobs"]["build"]["steps"][0]
    expected = "${{ inputs.source_ref || github.sha }}"
    for job in source["jobs"].values():
        test_checkout = next(
            step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")
        )
        assert (
            checkout["with"]["ref"]
            == gate["with"]["source_ref"]
            == test_checkout["with"]["ref"]
            == expected
        )
    assert native["env"] == source["env"]


def test_both_workflows_retain_exact_pins_and_propagate_failures_without_publication() -> None:
    for name in ("tests.yml", "build.yml"):
        data = workflow(name)
        assert data["env"]["PYTHON_VERSION"] == "3.13.17"
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
    for job in workflow("tests.yml")["jobs"].values():
        steps = job["steps"]
        guard = next(
            step for step in steps if step.get("name") == "Validate requested source commit"
        )
        assert steps.index(guard) < next(
            index
            for index, step in enumerate(steps)
            if step.get("uses", "").startswith("actions/checkout@")
        )
        assert guard["env"]["SOURCE_REF"] == "${{ inputs.source_ref || github.sha }}"
        assert "^[0-9a-f]{40}$" in guard["run"]
        assert "exit 1" in guard["run"]


@pytest.mark.parametrize("job_name", ["test", "web"])
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
    job_name: str, source_ref: str, expected: int
) -> None:
    guard = next(
        step
        for step in workflow("tests.yml")["jobs"][job_name]["steps"]
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
