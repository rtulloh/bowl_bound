"""Repository-local issue workflow, milestone ownership, and generated-index checks."""

from pathlib import Path

import pytest

from scripts.build_issue_index import INDEX, ISSUES, load_issues, render_index


def ticket(root: Path, **updates: str) -> Path:
    fields = {
        "id": "UI-001",
        "title": "Synthetic issue",
        "status": "open",
        "priority": "Medium",
        "milestone": "19",
        "created-at": "2026-10-26",
        "resolved-at": "",
        "closed-at": "",
    }
    fields.update(updates)
    path = root / "UI" / "UI-001.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    front = "\n".join(f"{key}: '{value}'" for key, value in fields.items())
    path.write_text(
        f"---\n{front}\n---\n\n## Description\n\nSynthetic evidence.\n\n"
        "## Resolution / verification\n\nSynthetic acceptance test.\n\n"
        "## Comments\n\n--- 2026-10-26 12:00 ---\nRecorded.\n",
        encoding="utf-8",
    )
    return path


def test_render_contains_status_milestone_and_relative_ticket_link(tmp_path: Path) -> None:
    ticket(tmp_path)
    rendered = render_index(tmp_path)
    assert "1 open, 0 resolved, 0 closed" in rendered
    assert "[UI-001](issues/UI/UI-001.md)" in rendered
    assert "[19](project-plan.md#19-complete-the-human-playable-ui)" in rendered
    assert "## By milestone" in rendered
    assert render_index(tmp_path) == rendered


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "done"),
        ("priority", "Urgent"),
        ("milestone", "999"),
        ("milestone", ""),
        ("id", "FLOW-001"),
        ("created-at", "tomorrow"),
        ("created-at", "2026-02-30"),
        ("title", ""),
        ("status", "resolved"),
        ("closed-at", "2026-10-26"),
        ("resolved-at", "2026-10-25"),
    ],
)
def test_invalid_metadata_is_rejected(tmp_path: Path, field: str, value: str) -> None:
    ticket(tmp_path, **{field: value})
    with pytest.raises(ValueError):
        load_issues(tmp_path)


def test_invalid_date_error_names_ticket_path(tmp_path: Path) -> None:
    path = ticket(tmp_path, **{"created-at": "2026-02-30"})
    with pytest.raises(ValueError) as error:
        load_issues(tmp_path)
    assert str(path) in str(error.value)


def test_resolved_requires_a_commit_and_closed_requires_playtest_evidence(tmp_path: Path) -> None:
    path = ticket(tmp_path, status="resolved", **{"resolved-at": "2026-10-26"})
    with pytest.raises(ValueError, match="commit"):
        load_issues(tmp_path)
    text = path.read_text().replace("closed-at: ''", "closed-at: ''\ncommits: [abc1234]")
    path.write_text(text)
    assert load_issues(tmp_path)[0]["status"] == "resolved"
    path.write_text(
        text.replace("status: 'resolved'", "status: 'closed'").replace(
            "closed-at: ''", "closed-at: '2026-10-26'"
        )
    )
    with pytest.raises(ValueError, match="play-test"):
        load_issues(tmp_path)
    with path.open("a") as output:
        output.write("\nPlay-test confirmation: synthetic browser audit passed.\n")
    assert load_issues(tmp_path)[0]["status"] == "closed"


def test_links_must_exist_and_be_mutual(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    path.write_text(path.read_text().replace("closed-at: ''", "closed-at: ''\nlinks: [UI-002]"))
    with pytest.raises(ValueError, match="link"):
        load_issues(tmp_path)
    second = path.with_name("UI-002.md")
    second.write_text(
        path.read_text().replace("UI-001", "UI-002").replace("links: [UI-002]", "links: []")
    )
    with pytest.raises(ValueError, match="mutual"):
        load_issues(tmp_path)
    second.write_text(second.read_text().replace("links: []", "links: [UI-001]"))
    assert len(load_issues(tmp_path)) == 2


def test_missing_front_matter_and_sections_are_rejected(tmp_path: Path) -> None:
    path = ticket(tmp_path)
    text = path.read_text()
    path.write_text(text.removeprefix("---\n"))
    with pytest.raises(ValueError):
        load_issues(tmp_path)
    path.write_text(text.replace("## Comments", "## Missing"))
    with pytest.raises(ValueError):
        load_issues(tmp_path)


def test_real_tracker_is_valid_and_committed_index_is_current() -> None:
    assert load_issues(ISSUES)
    assert INDEX.read_text(encoding="utf-8") == render_index(ISSUES)


def test_milestone_links_strip_heading_punctuation() -> None:
    from scripts.build_issue_index import milestones

    assert milestones()["5d"] == "project-plan.md#5d-batch-import-moved-to-milestone-25"
