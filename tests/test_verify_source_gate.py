"""Exact-commit CI reuse fails closed on failed, unrelated or pending runs."""

import pytest

from scripts.verify_source_gate import approved_run

SHA = "a" * 40
REPO = "example/bowl_bound"


def run(**updates: object) -> dict:
    result = {
        "id": 10,
        "run_attempt": 1,
        "head_sha": SHA,
        "head_branch": "main",
        "path": ".github/workflows/tests.yml",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "head_repository": {"full_name": REPO},
    }
    result.update(updates)
    return result


def test_successful_exact_main_push_is_reused() -> None:
    assert approved_run([run()], SHA, REPO)["id"] == 10


@pytest.mark.parametrize(
    "changes",
    [
        {"head_sha": "b" * 40},
        {"head_branch": "feature"},
        {"path": ".github/workflows/other.yml"},
        {"event": "pull_request"},
        {"head_repository": {"full_name": "fork/bowl_bound"}},
        {"status": "in_progress"},
        {"conclusion": "failure"},
        {"conclusion": "cancelled"},
        {"conclusion": "skipped"},
    ],
)
def test_unqualified_run_is_rejected(changes: dict) -> None:
    with pytest.raises(ValueError):
        approved_run([run(**changes)], SHA, REPO)


def test_newer_failure_cannot_reuse_an_older_success() -> None:
    with pytest.raises(ValueError):
        approved_run([run(), run(id=11, conclusion="failure")], SHA, REPO)


@pytest.mark.parametrize("sha", ["main", "a" * 39, "a" * 40 + "\n"])
def test_only_full_commit_ids_are_allowed(sha: str) -> None:
    with pytest.raises(ValueError):
        approved_run([run()], sha, REPO)


def test_no_run_is_rejected() -> None:
    with pytest.raises(ValueError):
        approved_run([], SHA, REPO)
