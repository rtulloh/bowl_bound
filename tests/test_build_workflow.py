"""The build workflow is manual, least-privilege and architecture-specific."""

import json
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
    source_text = (ROOT / ".github/workflows/tests.yml").read_text()
    source = yaml.load(source_text, Loader=yaml.BaseLoader)
    assert any(
        "scripts.verify_source_gate" in step.get("run", "") for step in jobs["test"]["steps"]
    )
    assert source["permissions"] == {"contents": "read"}
    assert int(jobs["build"]["timeout-minutes"]) == 45
    assert int(source["jobs"]["test"]["timeout-minutes"]) == 240
    for job in (jobs["build"], *source["jobs"].values()):
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"actions/[a-z-]+@[a-f0-9]{40}", step["uses"])
            assert "continue-on-error" not in step
    text += source_text
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


def test_pdf_importer_is_not_part_of_native_runtime() -> None:
    requirements = (ROOT / "release/requirements-native.txt").read_text().splitlines()
    package_names = {line.split("==", 1)[0].lower() for line in requirements if "==" in line}
    assert package_names.isdisjoint({"pdfplumber", "reportlab", "pdfminer.six"})

    manifest = json.loads((ROOT / "release/manifest.json").read_text())
    runtime_files = manifest["runtime"]
    assert not any(path.startswith(("tools/", "tests/")) for path in runtime_files)
    assert "docs/pdf-import.md" not in runtime_files


def test_browser_job_provides_the_interpreter_expected_by_the_harness() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/tests.yml").read_text(), Loader=yaml.BaseLoader)
    commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["test"]["steps"])
    assert "python -m venv .venv" in commands
    assert '.venv/bin/python -m pip install -e ".[dev,web,pdf]"' in commands
    assert ".venv/bin/python -m pytest --cov" in commands
    assert "-n 4 --dist=loadgroup --durations=25" in commands
    pyproject = (ROOT / "pyproject.toml").read_text()
    dev = re.search(r"^dev = \[(.*?)^\]", pyproject, re.MULTILINE | re.DOTALL)
    assert dev is not None and '"pytest-xdist==3.8.0"' in dev.group(1)


def test_parallel_wheel_tests_share_only_the_checkout_build_group() -> None:
    assert '"pytest==9.1.1"' in (ROOT / "pyproject.toml").read_text()
    packaging = (ROOT / "tests/test_packaging.py").read_text()
    assert 'pytestmark = pytest.mark.xdist_group("checkout_wheel")' in packaging
    assert "xdist_group" not in (ROOT / "tests/chartgen/test_generation.py").read_text()


def test_native_python_pin_matches_the_reviewed_binary_catalog() -> None:
    build = yaml.load((ROOT / ".github/workflows/build.yml").read_text(), Loader=yaml.BaseLoader)
    validation = yaml.load(
        (ROOT / ".github/workflows/post-release-smoke.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert build["jobs"]["build"]["env"]["PYTHON_VERSION"] == "3.12.10"
    assert (
        json.loads((ROOT / "release/native-notices/manifest.json").read_text())["python"]
        == "3.12.10"
    )
    setup = next(
        step
        for step in validation["jobs"]["native"]["steps"]
        if step.get("uses", "").startswith("actions/setup-python@")
    )
    assert setup["with"]["python-version"] == "3.12.10"
    assert build["env"]["PYTHON_VERSION"] == "3.12.16"
