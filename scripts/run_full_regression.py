"""Run the project's complete local regression gate in CI order.

Ordinary checks are offline. ``npm ci`` and the Playwright browser install
download dependencies and therefore need network access on a cold machine.

Local Python tests intentionally omit coverage for speed. ``pytest --cov`` runs
as part of individual changes, and the upstream CI gate enforces the 75%
``fail_under`` threshold.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAIL_LINES = 20
INSTALL_HINT = "run python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev,web,pdf]'"


class RegressionConfigurationError(ValueError):
    """The local checkout cannot support the requested regression gate."""


@dataclass(frozen=True)
class RegressionOptions:
    """Select the interpreter, report destination and independently skippable groups."""

    python: str = ".venv/bin/python"
    report: Path | None = None
    keep_going: bool = False
    skip_frontend: bool = False
    skip_e2e: bool = False
    skip_chart_audit: bool = False
    skip_python: bool = False
    no_install: bool = False


@dataclass(frozen=True)
class CommandResult:
    """The exit code and a bounded output tail suitable for JSON evidence."""

    returncode: int
    tail: tuple[str, ...] = ()


@dataclass(frozen=True)
class Step:
    """One CI-equivalent command, including whether a skip flag disabled it."""

    name: str
    command: tuple[str, ...]
    cwd: str = "."
    env: Mapping[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass(frozen=True)
class StepResult:
    """A completed, failed or deliberately skipped gate step."""

    name: str
    status: str
    command: tuple[str, ...]
    cwd: str
    returncode: int | None
    elapsed_seconds: float
    tail: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegressionReport:
    """Machine-readable and printable facts from one local gate run."""

    steps: tuple[StepResult, ...]
    elapsed_seconds: float
    exit_code: int

    @property
    def totals(self) -> dict[str, int]:
        """Count each terminal status without conflating skips with passes."""
        return {
            status: sum(step.status == status for step in self.steps)
            for status in ("passed", "failed", "skipped")
        }


CommandExecutor = Callable[[tuple[str, ...], Path, Mapping[str, str]], CommandResult]


def _display_path(path: Path, root: Path, *, temporary: Path | None = None) -> str:
    if temporary is not None and path.is_relative_to(temporary):
        return "<temporary>/" + path.relative_to(temporary).as_posix()
    if path.is_relative_to(root):
        return path.relative_to(root).as_posix() or "."
    return path.name


def _display_command(
    command: Sequence[str], root: Path, *, temporary: Path | None = None
) -> tuple[str, ...]:
    displayed = []
    for item in command:
        path = Path(item)
        if path.is_absolute():
            displayed.append(_display_path(path, root, temporary=temporary))
        else:
            displayed.append(item)
    return tuple(displayed)


def _safe_lines(lines: Sequence[str], root: Path, temporary: Path | None = None) -> tuple[str, ...]:
    """Remove local checkout and home paths from retained report evidence."""
    replacements = [(str(root), ".")]
    if temporary is not None:
        replacements.append((str(temporary), "<temporary>"))
    replacements.append((str(Path.home()), "~"))
    safe = []
    for line in lines:
        for value, label in replacements:
            line = line.replace(value, label)
        safe.append(line)
    return tuple(safe)


def _execute_streaming(
    command: tuple[str, ...], cwd: Path, env: Mapping[str, str]
) -> CommandResult:
    """Stream combined output while retaining only a bounded tail for the report."""
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            errors="replace",
        )
    except OSError as error:
        message = f"Could not start {command[0]}: {error}"
        print(message, file=sys.stderr)
        return CommandResult(127, (message,))
    tail: deque[str] = deque(maxlen=TAIL_LINES)
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        tail.append(line.rstrip("\n"))
    return CommandResult(process.wait(), tuple(tail))


def _interpreter(options: RegressionOptions, root: Path, *, needed: bool) -> Path:
    if not needed:
        return root / options.python
    candidate = Path(options.python)
    if candidate.is_absolute():
        executable = candidate
    elif len(candidate.parts) == 1:
        found = shutil.which(options.python)
        if found is None:
            raise RegressionConfigurationError(
                f"Python interpreter {options.python!r} was not found on PATH; {INSTALL_HINT}"
            )
        executable = Path(found)
    else:
        executable = root / candidate
    if not executable.is_file():
        raise RegressionConfigurationError(
            f"Python interpreter not found at {_display_path(executable, root)}; {INSTALL_HINT}"
        )
    if not os.access(executable, os.X_OK):
        raise RegressionConfigurationError(
            f"Python interpreter is not executable: "
            f"{_display_path(executable, root)}; {INSTALL_HINT}"
        )
    # Keep the venv entry point: .venv/bin/python is a symlink to the base
    # interpreter, and resolving it would drop the venv's installed packages.
    return executable.absolute()


def _validate(options: RegressionOptions, root: Path) -> Path:
    if not root.is_dir():
        raise RegressionConfigurationError(f"Repository root does not exist: {root}")
    needs_frontend = not options.skip_frontend or not options.skip_e2e
    if needs_frontend:
        frontend = root / "frontend"
        if not frontend.is_dir():
            raise RegressionConfigurationError(
                "Missing frontend directory; run from the complete Bowl Bound checkout"
            )
        if not (frontend / "package.json").is_file():
            raise RegressionConfigurationError(
                "Missing frontend/package.json; restore the frontend sources before running"
            )
        if shutil.which("npm") is None:
            raise RegressionConfigurationError(
                "npm was not found on PATH; install Node 24.22.1/npm 11.19.1 first"
            )
        if not options.skip_e2e and shutil.which("npx") is None:
            raise RegressionConfigurationError(
                "npx was not found on PATH; install Node 24.22.1/npm 11.19.1 first"
            )
    needs_python = not options.skip_python or not options.skip_chart_audit
    executable = _interpreter(options, root, needed=needs_python)
    if not options.skip_python:
        if not (root / "tests").is_dir():
            raise RegressionConfigurationError(
                "Missing tests directory; run from the complete Bowl Bound checkout"
            )
        if not (root / "pyproject.toml").is_file():
            raise RegressionConfigurationError(
                "Missing pyproject.toml; restore the project configuration before running"
            )
    if not options.skip_e2e:
        venv_python = root / ".venv/bin/python"
        if not venv_python.is_file():
            raise RegressionConfigurationError(
                "Browser tests require the project .venv interpreter; " + INSTALL_HINT
            )
    if not options.skip_chart_audit and not (root / "scripts/audit_generated_charts.py").is_file():
        raise RegressionConfigurationError(
            "Missing scripts/audit_generated_charts.py; restore the chart audit sources"
        )
    if options.report is not None and not options.report.parent.is_dir():
        raise RegressionConfigurationError(
            f"Report parent directory does not exist: {options.report.parent}"
        )
    return executable


def _steps(executable: Path, temporary: Path, options: RegressionOptions) -> list[Step]:
    python = str(executable)
    audit_report = temporary / "generated-chart-audit.json"
    seasons = temporary / "e2e-seasons"
    seasons.mkdir(parents=True, exist_ok=True)
    python_steps = [
        Step("Python tests", (python, "-m", "pytest", "-q")),
        Step("Python lint", (python, "-m", "ruff", "check", ".")),
        Step("Python format", (python, "-m", "ruff", "format", "--check", ".")),
        Step("Python dependency check", (python, "-m", "pip", "check")),
    ]
    frontend_steps = [
        Step("Frontend install", ("npm", "ci", "--ignore-scripts"), cwd="frontend"),
        Step("Frontend tests", ("npm", "test"), cwd="frontend"),
        Step("Frontend build", ("npm", "run", "build"), cwd="frontend"),
        Step("Frontend audit", ("npm", "audit"), cwd="frontend"),
    ]
    audit_step = Step(
        "Generated chart audit",
        (python, "-m", "scripts.audit_generated_charts", "--report", str(audit_report)),
    )
    browser_steps = [
        Step(
            "Playwright install",
            ("npx", "playwright", "install", "--with-deps", "chromium"),
            cwd="frontend",
        ),
        Step(
            "Browser tests",
            ("npm", "run", "test:e2e"),
            cwd="frontend",
            env={"BB_E2E_SEASONS": str(seasons)},
        ),
    ]
    if options.skip_python:
        python_steps = [replace(step, enabled=False) for step in python_steps]
    if options.skip_frontend:
        frontend_steps = [replace(step, enabled=False) for step in frontend_steps]
    if options.no_install:
        frontend_steps[0] = replace(frontend_steps[0], enabled=False)
        browser_steps[0] = replace(browser_steps[0], enabled=False)
    if options.skip_e2e:
        browser_steps = [replace(step, enabled=False) for step in browser_steps]
    if options.skip_chart_audit:
        audit_step = replace(audit_step, enabled=False)
    return [*python_steps, *frontend_steps, audit_step, *browser_steps]


def _skipped(step: Step, root: Path) -> StepResult:
    return StepResult(
        step.name,
        "skipped",
        _display_command(step.command, root),
        step.cwd,
        None,
        0.0,
    )


def _emit_summary(report: RegressionReport) -> None:
    print("\nRegression summary")
    print(f"{'Status':<8} {'Step':<26} {'Time':>9} {'Exit':>5}")
    print("-" * 52)
    for step in report.steps:
        status = step.status.upper()
        exit_code = "" if step.returncode is None else str(step.returncode)
        print(f"{status:<8} {step.name:<26} {step.elapsed_seconds:>8.1f}s {exit_code:>5}")
    totals = report.totals
    print("-" * 52)
    print(
        f"Passed: {totals['passed']}  Failed: {totals['failed']}  "
        f"Skipped: {totals['skipped']}  Elapsed: {report.elapsed_seconds:.1f}s"
    )


def _report_json(report: RegressionReport) -> dict[str, object]:
    return {
        "schema_version": 1,
        "passed": report.exit_code == 0,
        "exit_code": report.exit_code,
        "elapsed_seconds": round(report.elapsed_seconds, 3),
        "totals": report.totals,
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "command": list(step.command),
                "cwd": step.cwd,
                "returncode": step.returncode,
                "elapsed_seconds": round(step.elapsed_seconds, 3),
                "tail": list(step.tail),
            }
            for step in report.steps
        ],
    }


def run_regression(
    root: Path,
    options: RegressionOptions,
    runner: CommandExecutor | None = None,
) -> RegressionReport:
    """Run the gate in canonical order, stopping on the first failure by default."""
    executable = _validate(options, root)
    execute = runner or _execute_streaming
    started = time.monotonic()
    results: list[StepResult] = []
    with tempfile.TemporaryDirectory(prefix="bowl-bound-regression-") as directory:
        # Resolve symlinked temp roots (macOS $TMPDIR -> /var -> /private/var):
        # the browser sample installer rejects any symlinked destination path.
        temporary = Path(directory).resolve()
        steps = _steps(executable, temporary, options)
        for index, step in enumerate(steps, start=1):
            print(f"\n[{index}/{len(steps)}] {step.name}")
            display = _display_command(step.command, root, temporary=temporary)
            print("$ " + " ".join(display))
            if not step.enabled:
                results.append(_skipped(step, root))
                print("SKIPPED")
                continue
            env = os.environ.copy()
            env["PYTHONNOUSERSITE"] = "1"
            env.update(step.env)
            step_started = time.monotonic()
            result = execute(step.command, root / step.cwd, env)
            elapsed = time.monotonic() - step_started
            status = "passed" if result.returncode == 0 else "failed"
            evaluated = StepResult(
                step.name,
                status,
                display,
                step.cwd,
                result.returncode,
                elapsed,
                _safe_lines(result.tail, root, temporary),
            )
            results.append(evaluated)
            print(f"{status.upper()} ({elapsed:.1f}s)")
            if status == "failed" and not options.keep_going:
                break
    report = RegressionReport(
        tuple(results),
        time.monotonic() - started,
        1 if any(step.status == "failed" for step in results) else 0,
    )
    _emit_summary(report)
    return report


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=".venv/bin/python", help="project Python interpreter")
    parser.add_argument("--report", type=Path, help="write a JSON summary to this path")
    parser.add_argument("--keep-going", action="store_true", help="continue after failures")
    parser.add_argument(
        "--skip-frontend", action="store_true", help="skip frontend unit/build/audit"
    )
    parser.add_argument("--skip-e2e", action="store_true", help="skip browser install/tests")
    parser.add_argument(
        "--skip-chart-audit", action="store_true", help="skip generated chart audit"
    )
    parser.add_argument("--skip-python", action="store_true", help="skip pytest/ruff/pip checks")
    parser.add_argument(
        "--no-install", action="store_true", help="skip npm ci and Playwright install"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, runner: CommandExecutor | None = None) -> int:
    """Run the full gate and write an optional JSON summary."""
    args = _parse(argv)
    options = RegressionOptions(
        python=args.python,
        report=args.report,
        keep_going=args.keep_going,
        skip_frontend=args.skip_frontend,
        skip_e2e=args.skip_e2e,
        skip_chart_audit=args.skip_chart_audit,
        skip_python=args.skip_python,
        no_install=args.no_install,
    )
    try:
        report = run_regression(ROOT, options, runner)
    except RegressionConfigurationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if options.report is not None:
        options.report.write_text(
            json.dumps(_report_json(report), indent=2) + "\n", encoding="utf-8"
        )
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
