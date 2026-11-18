"""Report the complete npm audit with one explicit, expiring toolchain waiver."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ADVISORY = "https://github.com/advisories/GHSA-fc5q-39xc-vjpf"
WAIVER_EXPIRES = date(2026, 12, 17)
SEVERITIES = {"info", "low", "moderate", "high", "critical"}


@dataclass(frozen=True)
class AuditDecision:
    """Package entries accepted by the waiver or still requiring attention."""

    accepted: tuple[str, ...]
    blocked: tuple[str, ...]


def evaluate_report(document: Any, *, today: date) -> AuditDecision:
    """Follow indirect findings; malformed evidence and dependency cycles fail closed."""
    try:
        if not isinstance(document, dict) or "error" in document:
            raise ValueError
        if document["auditReportVersion"] != 2:
            raise ValueError
        entries = document["vulnerabilities"]
        count = document["metadata"]["vulnerabilities"]["total"]
        if not isinstance(entries, dict) or type(count) is not int or count != len(entries):
            raise ValueError
        for name, entry in entries.items():
            if not isinstance(name, str) or not name or not isinstance(entry, dict):
                raise ValueError
            if entry["severity"] not in SEVERITIES:
                raise ValueError
            if not isinstance(entry["via"], list) or not entry["via"]:
                raise ValueError
            for cause in entry["via"]:
                if isinstance(cause, str):
                    if cause not in entries:
                        raise ValueError
                elif isinstance(cause, dict):
                    if cause["severity"] not in SEVERITIES or not isinstance(cause["url"], str):
                        raise ValueError
                else:
                    raise ValueError

        memo: dict[str, bool] = {}

        def accepted(name: str, ancestors: frozenset[str]) -> bool:
            if name in ancestors:
                raise ValueError("Audit dependency cycle")
            if name in memo:
                return memo[name]
            decisions = []
            for cause in entries[name]["via"]:
                if isinstance(cause, str):
                    decisions.append(accepted(cause, ancestors | {name}))
                else:
                    decisions.append(
                        today <= WAIVER_EXPIRES
                        and cause["url"] == ADVISORY
                        and cause["severity"] == "high"
                        and cause.get("name") == "picomatch"
                        and cause.get("dependency") == "picomatch"
                        and cause.get("range") == "<=4.0.7"
                    )
            memo[name] = entries[name]["severity"] != "critical" and all(decisions)
            return memo[name]

        allowed = tuple(name for name in sorted(entries) if accepted(name, frozenset()))
        return AuditDecision(
            allowed, tuple(name for name in sorted(entries) if name not in allowed)
        )
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError("Invalid or incomplete npm audit report") from error


def main(argv: list[str] | None = None) -> int:
    """Keep raw evidence and preserve failures outside the narrow reviewed waiver."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report", type=Path, required=True, help="raw npm JSON evidence destination"
    )
    options = parser.parse_args(argv)
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=Path(__file__).resolve().parents[1] / "frontend",
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        options.report.write_text(result.stdout, encoding="utf-8")
        if result.returncode not in (0, 1):
            raise ValueError(f"npm audit failed with exit code {result.returncode}")
        document = json.loads(result.stdout)
        decision = evaluate_report(document, today=datetime.now(timezone.utc).date())
        if bool(document["vulnerabilities"]) != bool(result.returncode):
            raise ValueError("npm audit status disagrees with its report")
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"Dependency audit could not establish a valid result: {error}")
        return 2
    if decision.accepted:
        print(f"Accepted temporary toolchain waiver: {ADVISORY}; expires {WAIVER_EXPIRES}.")
        print("Affected package entries:", json.dumps(decision.accepted))
        print("The vulnerability is not fixed. The raw report retains every finding.")
    if decision.blocked:
        print("Unaccepted findings:", json.dumps(decision.blocked))
        return 1
    print("Dependency audit satisfies the current policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
