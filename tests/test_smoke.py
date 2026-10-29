"""Smoke tests for the initialized project skeleton."""

import subprocess
from pathlib import Path

import bowl_bound

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_imports_and_exposes_version() -> None:
    assert isinstance(bowl_bound.__version__, str)
    assert bowl_bound.__version__


def test_package_has_no_paydirt_runtime_dependency() -> None:
    import sys

    assert "paydirt" not in sys.modules


def test_private_data_paths_are_ignored_by_git() -> None:
    """Private charts, saves, and reports must never be trackable."""
    candidates = [
        "private-data/teams/ohio_state.json",
        "private-data/reports/import-report.json",
        "some-team-chart.pdf",
        "game.save",
        "my_save.json",
        "bowl-bound-save.json",
        "bowl-bound-save (1).json",
    ]
    for path in candidates:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=REPO_ROOT,
            check=False,
        )
        assert result.returncode == 0, f"{path} is not ignored by git"
