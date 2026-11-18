"""An expiring, exact advisory waiver must never hide unrelated audit failures."""

from collections.abc import Callable
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

import pytest

from scripts.check_frontend_audit import evaluate_report

TODAY = date(2026, 11, 17)
URL = "https://github.com/advisories/GHSA-fc5q-39xc-vjpf"


def report() -> dict[str, Any]:
    return {
        "auditReportVersion": 2,
        "vulnerabilities": {
            "picomatch": {
                "severity": "high",
                "via": [
                    {
                        "name": "picomatch",
                        "dependency": "picomatch",
                        "url": URL,
                        "severity": "high",
                        "range": "<=4.0.7",
                    }
                ],
            },
            "builder": {"severity": "high", "via": ["picomatch"]},
        },
        "metadata": {"vulnerabilities": {"total": 2}},
    }


def test_exact_waiver_covers_inherited_findings_and_is_reported() -> None:
    result = evaluate_report(report(), today=TODAY)
    assert result.accepted == ("builder", "picomatch")
    assert result.blocked == ()


@pytest.mark.parametrize("severity", ["low", "moderate", "high", "critical"])
def test_unrelated_finding_still_blocks_even_when_mixed_with_accepted_one(severity: str) -> None:
    data = report()
    other = deepcopy(data["vulnerabilities"]["picomatch"]["via"][0])
    other.update(url="https://github.com/advisories/GHSA-aaaa-bbbb-cccc", severity=severity)
    data["vulnerabilities"]["picomatch"]["via"].append(other)
    result = evaluate_report(data, today=TODAY)
    assert result.blocked == ("builder", "picomatch")
    assert result.accepted == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"url": URL + "-other"},
        {"url": URL.replace("github.com", "github.com.evil.example")},
        {"severity": "critical"},
        {"name": "other"},
        {"dependency": "other"},
        {"range": "<=4.0.8"},
    ],
)
def test_waiver_is_exact_and_cannot_cover_changed_scope(changes: dict[str, str]) -> None:
    data = report()
    data["vulnerabilities"]["picomatch"]["via"][0].update(changes)
    assert evaluate_report(data, today=TODAY).blocked == ("builder", "picomatch")


def test_waiver_expires_and_does_not_expire_clean_reports() -> None:
    assert evaluate_report(report(), today=date(2026, 12, 17)).blocked == ()
    assert evaluate_report(report(), today=date(2026, 12, 18)).blocked
    data = report()
    data["vulnerabilities"] = {}
    data["metadata"]["vulnerabilities"]["total"] = 0
    assert evaluate_report(data, today=date(2026, 12, 18)).blocked == ()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(error={"code": "EAI_AGAIN"}),
        lambda d: d.pop("auditReportVersion"),
        lambda d: d.update(auditReportVersion=1),
        lambda d: d.pop("metadata"),
        lambda d: d["metadata"]["vulnerabilities"].update(total=0),
        lambda d: d["vulnerabilities"]["builder"].update(via=["missing"]),
        lambda d: d["vulnerabilities"]["builder"].update(via=["builder"]),
        lambda d: d["vulnerabilities"]["builder"].update(via=[]),
        lambda d: d["vulnerabilities"]["builder"].update(via=[42]),
        lambda d: d["vulnerabilities"]["builder"].update(severity="unknown"),
    ],
)
def test_malformed_or_incomplete_reports_fail_closed(
    mutation: Callable[[dict[str, Any]], Any],
) -> None:
    data = report()
    mutation(data)
    with pytest.raises(ValueError):
        evaluate_report(data, today=TODAY)


def test_critical_parent_is_never_waived() -> None:
    data = report()
    data["vulnerabilities"]["builder"]["severity"] = "critical"
    assert evaluate_report(data, today=TODAY).blocked == ("builder",)


@pytest.mark.parametrize(
    "status, payload, expected",
    [
        (1, "known", 0),
        (0, "known", 2),
        (2, "known", 2),
        (1, "not json", 2),
        (1, '{"error":{"code":"EAI_AGAIN"}}', 2),
    ],
)
def test_cli_preserves_raw_evidence_and_rejects_audit_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int, payload: str, expected: int
) -> None:
    import json
    import subprocess

    from scripts import check_frontend_audit as checker

    raw = json.dumps(report()) if payload == "known" else payload
    monkeypatch.setattr(checker, "WAIVER_EXPIRES", date.max)
    monkeypatch.setattr(
        checker.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, status, raw, "")
    )
    destination = tmp_path / "audit.json"
    assert checker.main(["--report", str(destination)]) == expected
    assert destination.read_text() == raw


def test_cli_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import subprocess

    from scripts import check_frontend_audit as checker

    def timeout(*args: Any, **kwargs: Any) -> NoReturn:
        raise subprocess.TimeoutExpired("npm", 120)

    monkeypatch.setattr(checker.subprocess, "run", timeout)
    assert checker.main(["--report", str(tmp_path / "audit.json")]) == 2
