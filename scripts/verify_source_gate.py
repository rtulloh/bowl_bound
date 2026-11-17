"""Require the latest exact-commit main push gate before native compilation."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def approved_run(runs: list[dict[str, Any]], source_ref: str, repository: str) -> dict[str, Any]:
    """Return qualified evidence, refusing stale success after a newer failed run."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("source_ref must be a full 40-character commit SHA")
    matching = [
        run
        for run in runs
        if run.get("head_sha") == source_ref
        and run.get("head_branch") == "main"
        and run.get("path") == ".github/workflows/tests.yml"
        and run.get("event") == "push"
        and run.get("head_repository", {}).get("full_name") == repository
    ]
    if not matching:
        raise ValueError("No Tests main push run exists for this exact commit")
    latest = max(matching, key=lambda run: (run["id"], run.get("run_attempt", 1)))
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        raise ValueError("Latest Tests run for this exact commit must complete successfully")
    return latest


def main() -> int:
    """Read trusted workflow settings and publish a verified immutable source ID."""
    source_ref = os.environ["SOURCE_REF"]
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise SystemExit("source_ref must be a full 40-character commit SHA")
    repository = os.environ["GH_REPO"]
    url = (
        f"{os.environ['GH_API_URL']}/repos/{repository}/actions/workflows/tests.yml/runs"
        f"?head_sha={source_ref}&event=push&per_page=100"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            document = json.load(response)
        run = approved_run(document["workflow_runs"], source_ref, repository)
    except (urllib.error.URLError, ValueError, KeyError) as error:
        raise SystemExit(f"Source validation refused: {error}") from error
    print("Verified Tests run", run["id"], "for", source_ref)
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"source_ref={source_ref}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
