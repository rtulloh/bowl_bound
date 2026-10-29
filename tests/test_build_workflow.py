"""The build workflow is manual, least-privilege and architecture-specific."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_three_native_builds_are_test_gated_and_do_not_publish_releases() -> None:
    text = (ROOT / ".github/workflows/build.yml").read_text()
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert jobs["build"]["needs"] == "test"
    targets = jobs["build"]["strategy"]["matrix"]["include"]
    assert {(row["target"], row["os"], row["arch"]) for row in targets} == {
        ("macos-arm64", "macos-26", "arm64"),
        ("macos-x86_64", "macos-26-intel", "x64"),
        ("windows-x64", "windows-2025", "x64"),
    }
    for job in jobs.values():
        assert int(job["timeout-minutes"]) <= 45
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"actions/[a-z-]+@[a-f0-9]{40}", step["uses"])
            assert "continue-on-error" not in step
    assert "contents: write" not in text and "action-gh-release" not in text
    assert "persist-credentials: false" in text and "npm ci --ignore-scripts" in text
    assert "--cov" in text and "npm run test:e2e" in text
    assert "scripts.build_standalone" in text and "scripts.smoke_standalone" in text
    assert "--no-deps" in text and "pip check" in text
    assert "if-no-files-found: error" in text


def test_native_requirements_are_exact_pins_not_editable_source() -> None:
    lines = (ROOT / "release/requirements-native.txt").read_text().splitlines()
    requirements = [line for line in lines if line and not line.startswith("#")]
    assert len(requirements) >= 20
    assert all(re.match(r"[A-Za-z0-9_.-]+==[0-9][^ ]*(?: ; .*)?$", line) for line in requirements)
    assert not any("bowl_bound" in line or "pytest" in line for line in requirements)


def test_browser_job_provides_the_interpreter_expected_by_the_harness() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/build.yml").read_text(), Loader=yaml.BaseLoader)
    commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["test"]["steps"])
    assert "python -m venv .venv" in commands
    assert '.venv/bin/python -m pip install -e ".[dev,web,pdf]"' in commands
    assert ".venv/bin/python -m pytest --cov" in commands
