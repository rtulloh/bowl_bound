"""Local full-gate orchestration is fast, ordered and independently testable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts import run_full_regression as regression


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "audit_generated_charts.py").write_text("", encoding="utf-8")
    executable = tmp_path / ".venv/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)
    return tmp_path


class FakeRunner:
    """Record commands and return configured results without touching the project."""

    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[tuple[tuple[str, ...], Path, dict[str, str]]] = []

    def __call__(
        self, command: tuple[str, ...], cwd: Path, env: dict[str, str]
    ) -> regression.CommandResult:
        self.calls.append((command, cwd, env))
        for failure in self.failures:
            if failure in " ".join(command):
                return regression.CommandResult(1, ("synthetic failure",))
        return regression.CommandResult(0, ("ok",))


def options(**overrides: object) -> regression.RegressionOptions:
    values: dict[str, object] = {"python": sys.executable}
    values.update(overrides)
    return regression.RegressionOptions(**values)  # type: ignore[arg-type]


def test_runs_every_ci_command_in_order(repo: Path) -> None:
    runner = FakeRunner()
    report = regression.run_regression(repo, options(), runner)

    commands = [call[0] for call in runner.calls]
    assert commands[0][1:] == ("-m", "pytest", "-q")
    assert commands[1][1:] == ("-m", "ruff", "check", ".")
    assert commands[2][1:] == ("-m", "ruff", "format", "--check", ".")
    assert commands[3][1:] == ("-m", "pip", "check")
    assert commands[4] == ("npm", "ci", "--ignore-scripts")
    assert commands[5] == ("npm", "test")
    assert commands[6] == ("npm", "run", "build")
    assert ("npm", "audit") not in commands
    assert commands[7][1:4] == ("-m", "scripts.audit_generated_charts", "--report")
    assert not Path(commands[7][4]).is_relative_to(repo)
    assert Path(commands[7][4]).name == "generated-chart-audit.json"
    assert commands[8] == ("npx", "playwright", "install", "--with-deps", "chromium")
    assert commands[9] == ("npm", "run", "test:e2e")
    assert all(call[1] == repo / "frontend" for call in runner.calls[4:7])
    assert runner.calls[-1][1] == repo / "frontend"
    assert runner.calls[9][2]["BB_E2E_SEASONS"]
    assert all(call[2]["PYTHONNOUSERSITE"] == "1" for call in runner.calls)
    assert report.exit_code == 0
    assert [step.status for step in report.steps] == ["passed"] * 10


def test_stops_on_first_failure_by_default(repo: Path) -> None:
    runner = FakeRunner({"ruff check"})
    report = regression.run_regression(repo, options(), runner)

    assert len(runner.calls) == 2
    assert report.exit_code == 1
    assert [step.status for step in report.steps] == ["passed", "failed"]
    assert report.steps[1].name == "Python lint"


def test_keep_going_collects_all_failures(repo: Path) -> None:
    runner = FakeRunner({"pytest", "npm test", "audit_generated_charts"})
    report = regression.run_regression(repo, options(keep_going=True), runner)

    assert len(runner.calls) == 10
    assert [step.name for step in report.steps if step.status == "failed"] == [
        "Python tests",
        "Frontend tests",
        "Generated chart audit",
    ]
    assert report.exit_code == 1


def test_skip_flags_remove_work_and_mark_steps_skipped(repo: Path) -> None:
    runner = FakeRunner()
    report = regression.run_regression(
        repo,
        options(skip_frontend=True, skip_e2e=True, skip_chart_audit=True, skip_python=True),
        runner,
    )

    assert runner.calls == []
    assert report.exit_code == 0
    assert {step.status for step in report.steps} == {"skipped"}


def test_skip_python_keeps_chart_audit_and_e2e(repo: Path) -> None:
    runner = FakeRunner()
    regression.run_regression(repo, options(skip_python=True), runner)

    commands = [call[0] for call in runner.calls]
    assert not any(
        command[1] == "-m" and command[2] in {"pytest", "ruff", "pip"} for command in commands
    )
    assert commands[3][1:4] == ("-m", "scripts.audit_generated_charts", "--report")
    assert commands[-1] == ("npm", "run", "test:e2e")


def test_no_install_skips_only_install_steps(repo: Path) -> None:
    runner = FakeRunner()
    report = regression.run_regression(repo, options(no_install=True), runner)

    commands = [call[0] for call in runner.calls]
    assert ("npm", "ci", "--ignore-scripts") not in commands
    assert ("npx", "playwright", "install", "--with-deps", "chromium") not in commands
    assert ("npm", "test") in commands and ("npm", "run", "test:e2e") in commands
    skipped = [step.name for step in report.steps if step.status == "skipped"]
    assert skipped == ["Frontend install", "Playwright install"]


def test_report_json_has_stable_shape(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(regression, "ROOT", repo)
    result = regression.main(
        [
            "--python",
            sys.executable,
            "--report",
            str(manifest),
            "--skip-frontend",
            "--skip-e2e",
            "--skip-chart-audit",
            "--skip-python",
        ],
        runner=FakeRunner(),
    )

    assert result == 0
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["passed"] is True
    assert data["exit_code"] == 0
    assert data["totals"] == {"passed": 0, "failed": 0, "skipped": 10}
    assert set(data["steps"][0]) >= {
        "name",
        "status",
        "command",
        "cwd",
        "returncode",
        "elapsed_seconds",
        "tail",
    }


def test_failing_main_returns_nonzero(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(regression, "ROOT", repo)
    result = regression.main(
        ["--python", sys.executable, "--skip-frontend", "--skip-e2e", "--skip-chart-audit"],
        runner=FakeRunner({"pytest"}),
    )
    assert result == 1


def test_missing_interpreter_is_actionable(repo: Path) -> None:
    with pytest.raises(regression.RegressionConfigurationError, match="venv"):
        regression.run_regression(repo, options(python=str(repo / "missing-python")), FakeRunner())


def test_missing_frontend_directory_is_actionable(repo: Path) -> None:
    (repo / "frontend").rename(repo / "frontend-away")
    with pytest.raises(regression.RegressionConfigurationError, match="frontend"):
        regression.run_regression(repo, options(), FakeRunner())


def test_missing_e2e_interpreter_is_actionable(repo: Path) -> None:
    (repo / ".venv/bin/python").unlink()
    with pytest.raises(regression.RegressionConfigurationError, match="venv"):
        regression.run_regression(repo, options(skip_python=True), FakeRunner())


def test_report_tail_does_not_retain_local_paths(repo: Path) -> None:
    class PathRunner(FakeRunner):
        def __call__(self, command, cwd, env):  # type: ignore[no-untyped-def]
            self.calls.append((command, cwd, env))
            return regression.CommandResult(1, (str(repo / "tests/test_x.py") + ":1",))

    report = regression.run_regression(repo, options(), PathRunner())
    assert report.steps[0].tail == ("./tests/test_x.py:1",)


def test_symlinked_venv_interpreter_keeps_the_venv_path(repo: Path) -> None:
    """Resolving the venv symlink would lose the venv's installed dependencies."""
    base = repo / "base-python"
    base.write_text("", encoding="utf-8")
    base.chmod(0o755)
    (repo / ".venv/bin/python").unlink()
    (repo / ".venv/bin/python").symlink_to(base)

    runner = FakeRunner()
    regression.run_regression(repo, options(python=".venv/bin/python"), runner)

    assert runner.calls[0][0][0] == str(repo / ".venv/bin/python")


def test_browser_fixture_paths_are_resolved_before_use(repo: Path) -> None:
    """macOS TMPDIR traverses a symlink, and sample installation rejects it."""
    runner = FakeRunner()

    regression.run_regression(repo, options(), runner)

    seasons = Path(runner.calls[-1][2]["BB_E2E_SEASONS"])
    assert not any(parent.is_symlink() for parent in (seasons, *seasons.parents))


def test_missing_tests_directory_is_actionable(repo: Path) -> None:
    (repo / "tests").rename(repo / "tests-away")
    with pytest.raises(regression.RegressionConfigurationError, match="tests"):
        regression.run_regression(repo, options(), FakeRunner())
