"""Standalone ticket creation validates before writing and preserves existing files."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import build_issue_index as index
from scripts.create_issue import create_issue


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    notes = tmp_path / "docs/dev-notes"
    notes.mkdir(parents=True)
    (notes / "project-plan.md").write_text("### 19. UI\n### 18a. Hardening\n")
    monkeypatch.setattr(index, "ROOT", tmp_path)
    monkeypatch.setattr(index, "ISSUES", notes / "issues")
    monkeypatch.setattr(index, "INDEX", notes / "issue-tracker.md")
    return tmp_path


def test_create_numbering_yaml_safety_and_fresh_index(repo: Path) -> None:
    first = create_issue(
        "DEV", "A title: with # punctuation", "19", "Synthetic description", ["Verify it"]
    )
    second = create_issue("DEV", "Next", "18a", "Description", ["Check"])
    assert first.name == "DEV-001.md" and second.name == "DEV-002.md"
    assert [i["title"] for i in index.load_issues(index.ISSUES)] == [
        "A title: with # punctuation",
        "Next",
    ]
    assert index.INDEX.read_text() == index.render_index(index.ISSUES)
    original = first.read_text()
    create_issue("DEV", "Third", "19", "Description", ["Check"])
    assert first.read_text() == original


@pytest.mark.parametrize(
    "prefix,title,milestone",
    [
        ("../DEV", "Valid", "19"),
        ("dev", "Valid", "19"),
        ("DEV", "", "19"),
        ("DEV", "bad\nline", "19"),
        ("DEV", "Valid", "999"),
    ],
)
def test_invalid_inputs_write_nothing(repo: Path, prefix: str, title: str, milestone: str) -> None:
    with pytest.raises(ValueError):
        create_issue(prefix, title, milestone, "Description", ["Check"])
    assert not index.ISSUES.exists()


def test_index_failure_keeps_created_ticket_and_reports_path(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_: Path) -> str:
        raise ValueError("broken existing ticket")

    monkeypatch.setattr(index, "render_index", fail)
    with pytest.raises(RuntimeError, match="DEV-001.*index"):
        create_issue("DEV", "Valid", "19", "Description", ["Check"])
    assert (index.ISSUES / "DEV/DEV-001.md").is_file()


def test_help_works_outside_repository(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/create_issue.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--milestone" in result.stdout and "--acceptance" in result.stdout


def test_creation_collision_never_overwrites_competing_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.open
    raced = False

    def competing_open(path: Path, mode: str = "r", *args, **kwargs):
        nonlocal raced
        if mode == "x" and not raced:
            raced = True
            with original(path, "w", encoding="utf-8") as output:
                output.write("competitor")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", competing_open)
    monkeypatch.setattr(index, "render_index", lambda _: "index")
    path = create_issue("DEV", "Valid", "19", "Description", ["Check"])
    assert path.name == "DEV-002.md"
    assert (path.parent / "DEV-001.md").read_text() == "competitor"


def test_symlinked_destination_is_refused(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    index.ISSUES.mkdir()
    (index.ISSUES / "DEV").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        create_issue("DEV", "Valid", "19", "Description", ["Check"])
    assert not list(outside.iterdir())


def test_exhausted_number_range_is_refused(repo: Path) -> None:
    folder = index.ISSUES / "DEV"
    folder.mkdir(parents=True)
    (folder / "DEV-999.md").write_text("preserve")
    with pytest.raises(ValueError, match="no three-digit"):
        create_issue("DEV", "Valid", "19", "Description", ["Check"])
    assert [p.name for p in folder.iterdir()] == ["DEV-999.md"]


def test_retired_ids_are_never_reused_after_prefix_migration(repo: Path) -> None:
    index.ISSUES.mkdir(parents=True)
    (index.ISSUES / "retired-ids.yaml").write_text("UI-023: CLI-023\nUI-035: CLI-035\n")
    created = create_issue("UI", "New web issue", "19", "Description", ["Check"])
    assert created.name == "UI-036.md"
    assert (
        create_issue("CLI", "Terminal issue", "19", "Description", ["Check"]).name == "CLI-001.md"
    )
    assert index.INDEX.read_text() == index.render_index(index.ISSUES)


@pytest.mark.parametrize("content", ["[]", "bad: CLI-023", "UI-023: invalid", "[bad yaml"])
def test_invalid_retired_id_registry_is_refused_without_creating_a_ticket(
    repo: Path,
    content: str,
) -> None:
    index.ISSUES.mkdir(parents=True)
    (index.ISSUES / "retired-ids.yaml").write_text(content)
    with pytest.raises(ValueError, match="retired"):
        create_issue("UI", "Web issue", "19", "Description", ["Check"])
    assert not (index.ISSUES / "UI").exists()
