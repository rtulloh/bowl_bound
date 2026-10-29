"""Build the local issue index; workflow adapted from Paydirt (MIT, rtulloh).

No Paydirt runtime dependency. See docs/ATTRIBUTION.md.
"""

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ISSUES = ROOT / "docs/dev-notes/issues"
INDEX = ROOT / "docs/dev-notes/issue-tracker.md"
STATUSES = ("open", "resolved", "closed")
PRIORITIES = ("High", "Medium", "Low")


def milestones() -> dict[str, str]:
    """Use the canonical roadmap, including lettered milestones, not a duplicate list."""
    text = (ROOT / "docs/dev-notes/project-plan.md").read_text(encoding="utf-8")
    result = {}
    for number, title in re.findall(r"^### (\d+[a-z]?)\. (.+)$", text, re.MULTILINE):
        slug = re.sub(r"[^\w\s-]", "", f"{number}. {title}".lower()).replace(" ", "-")
        result[number] = f"project-plan.md#{slug}"
    return result


def _day(value: object) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def _validate(fields: dict[str, Any], text: str, path: Path) -> None:
    issue_id = fields.get("id", "")
    if not isinstance(issue_id, str) or not re.fullmatch(r"[A-Z]+-\d{3}", issue_id):
        raise ValueError(f"{path}: invalid issue ID")
    if path.stem != issue_id or path.parent.name != issue_id.split("-")[0]:
        raise ValueError(f"{path}: ID must match filename and prefix directory")
    title = fields.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 120 or "\n" in title:
        raise ValueError(f"{path}: title must be one line of 1..120 characters")
    status = fields.get("status")
    if status not in STATUSES or fields.get("priority") not in PRIORITIES:
        raise ValueError(f"{path}: invalid status or priority")
    fields["milestone"] = str(fields.get("milestone", ""))
    if fields["milestone"] not in milestones():
        raise ValueError(f"{path}: milestone must exist in project-plan.md")
    created, resolved, closed = (
        _day(fields.get(key)) for key in ("created-at", "resolved-at", "closed-at")
    )
    if (
        created is None
        or (resolved and resolved < created)
        or (closed and closed < (resolved or created))
    ):
        raise ValueError(f"{path}: missing or out-of-order dates")
    if (
        (status == "open" and (resolved or closed))
        or (status == "resolved" and (not resolved or closed))
        or (status == "closed" and not closed)
    ):
        raise ValueError(f"{path}: dates do not match status")
    for key in ("tags", "links", "commits"):
        values = fields.get(key) or []
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError(f"{path}: {key} must be a list of strings")
        fields[key] = values
    if status in {"resolved", "closed"} and resolved and not fields["commits"]:
        raise ValueError(f"{path}: resolved fix requires a commit reference")
    if status == "closed" and "Play-test confirmation:" not in text:
        exceptions = {"duplicate", "re-scoped", "wont-fix"}
        if not exceptions.intersection(fields["tags"]):
            raise ValueError(f"{path}: closure requires play-test confirmation")
    for heading in ("Description", "Resolution / verification", "Comments"):
        if f"## {heading}\n" not in text:
            raise ValueError(f"{path}: missing {heading} section")


def load_issues(issues_dir: Path) -> list[dict[str, Any]]:
    """Read and validate individual tickets and reciprocal cross-references."""
    issues = []
    for path in sorted(issues_dir.glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---\n", 2)
        if not text.startswith("---\n") or len(parts) != 3:
            raise ValueError(f"{path}: missing front matter")
        fields = yaml.safe_load(parts[1])
        if not isinstance(fields, dict):
            raise ValueError(f"{path}: front matter must be a mapping")
        _validate(fields, text, path)
        fields["path"] = "issues/" + path.relative_to(issues_dir).as_posix()
        issues.append(fields)
    by_id = {issue["id"]: issue for issue in issues}
    if len(by_id) != len(issues):
        raise ValueError("duplicate issue IDs")
    for issue in issues:
        for link in issue["links"]:
            if link not in by_id:
                raise ValueError(f"{issue['id']}: unknown issue link {link}")
            if issue["id"] not in by_id[link]["links"]:
                raise ValueError(f"{issue['id']}: issue links must be mutual")
    return issues


def render_index(issues_dir: Path) -> str:
    """Render deterministic status and milestone views from the same ticket files."""
    issues = load_issues(issues_dir)
    roadmap = milestones()
    counts = ", ".join(f"{sum(i['status'] == s for i in issues)} {s}" for s in STATUSES)
    lines = [
        "# Developer Issue Tracker",
        "",
        "**Developer-only working record, not a player guide or a release promise.**",
        "",
        "Generated by `python3 scripts/build_issue_index.py`; do not edit by hand.",
        "See [ticket conventions](issues/README.md) and the [roadmap](project-plan.md).",
        "",
        f"{len(issues)} issues: {counts}.",
    ]
    for status in STATUSES:
        group = sorted(
            (i for i in issues if i["status"] == status),
            key=lambda i: (PRIORITIES.index(i["priority"]), i["id"]),
        )
        label = (
            "Resolved (awaiting play-test confirmation)" if status == "resolved" else status.title()
        )
        lines.extend(["", f"## {label} ({len(group)})", ""])
        if not group:
            lines.append("None.")
            continue
        lines.extend(
            ["| ID | Priority | Milestone | Title | Dates |", "| --- | --- | --- | --- | --- |"]
        )
        for issue in group:
            dates = "; ".join(
                f"{key.removesuffix('-at')} {issue[key]}"
                for key in ("created-at", "resolved-at", "closed-at")
                if issue.get(key)
            )
            number = issue["milestone"]
            title = issue["title"].replace("|", "\\|")
            lines.append(
                f"| [{issue['id']}]({issue['path']}) | {issue['priority']} | "
                f"[{number}]({roadmap[number]}) | {title} | {dates} |"
            )
    lines.extend(["", "## By milestone", ""])
    for number, target in roadmap.items():
        group = [i for i in issues if i["milestone"] == number]
        if group:
            lines.extend([f"### Milestone [{number}]({target})", ""])
            lines.extend(
                f"- [{i['id']}]({i['path']}) ({i['status']}, {i['priority']}) — {i['title']}"
                for i in group
            )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    """Validate tickets and regenerate the checked-in index."""
    INDEX.write_text(render_index(ISSUES), encoding="utf-8")
    print(f"Wrote {INDEX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
