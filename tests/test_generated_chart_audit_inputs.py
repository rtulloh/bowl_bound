"""Exact release-audit inputs; synthetic charts and nonpatching race injection."""

import json
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from scripts import audit_generated_charts as audit
from tests.synthetic_teams import write_team
from tests.test_generated_chart_audit import fixture, repin


@contextmanager
def on_return(function: Callable[..., Any], action: Callable[[], None]) -> Iterator[None]:
    """Simulate a concurrent writer without replacing any audited function."""
    assert sys.getprofile() is None
    changed = False

    def profile(frame: Any, event: str, result: Any) -> None:
        nonlocal changed
        if not changed and event == "return" and frame.f_code is function.__code__:
            changed = True
            action()

    sys.setprofile(profile)
    try:
        yield
    finally:
        sys.setprofile(None)
    assert changed, "synthetic mutation must actually execute"


@pytest.mark.parametrize(
    "mutation", ["chart", "provenance", "manifest", "expectations", "engine", "removed", "symlink"]
)
def test_late_input_change_cannot_keep_a_pass(tmp_path: Path, mutation: str) -> None:
    root, _, _ = fixture(tmp_path)
    relative = {
        "chart": "seasons/2007/synthetic-generated/defense.csv",
        "provenance": "seasons/2007/provenance/synthetic-generated.csv",
        "manifest": "release/manifest.json",
        "expectations": audit.EXPECTATIONS,
        "engine": "bowl_bound/dice.py",
        "removed": "seasons/2007/synthetic-generated/defense.csv",
        "symlink": "seasons/2007/synthetic-generated/defense.csv",
    }[mutation]
    path = root / relative

    def change() -> None:
        if mutation == "removed":
            path.unlink()
        elif mutation == "symlink":
            saved = path.with_suffix(".held")
            path.rename(saved)
            path.symlink_to(saved)
        else:
            path.write_bytes(path.read_bytes() + b"\n")

    with on_return(audit._audit_roles, change):
        with pytest.raises(audit.ChartAuditError, match="changed|Stale|stale|Symlink|symlink"):
            audit.audit_candidate(root)


def test_transient_live_chart_cannot_replace_the_frozen_subject(tmp_path: Path) -> None:
    root, _, baseline = fixture(tmp_path)
    write_team(tmp_path / "neutral/seasons", baseline)
    names = json.loads((root / "release/manifest.json").read_text())["generated_sha256"]
    original = {name: (root / name).read_bytes() for name in names}
    neutral = {name: (tmp_path / "neutral" / name).read_bytes() for name in names}
    active = observed = False

    def profile(frame: Any, event: str, result: Any) -> None:
        nonlocal active, observed
        if frame.f_code is not audit.load_team.__code__:
            return
        if event == "call" and not observed:
            active = observed = True
            for name, content in neutral.items():
                (root / name).write_bytes(content)
        elif event == "return" and active:
            for name, content in original.items():
                (root / name).write_bytes(content)
            active = False

    assert sys.getprofile() is None
    sys.setprofile(profile)
    try:
        result = audit.audit_candidate(root)
    finally:
        sys.setprofile(None)
        for name, content in original.items():
            (root / name).write_bytes(content)
    assert observed
    assert result["passed"] is True


def builder_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root, expected, _ = fixture(tmp_path / "current")
    prior, _, baseline = fixture(tmp_path / "prior")
    write_team(prior / "seasons", baseline)
    repin(prior)
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {"model_identity": expected["model_identity"]}
            | {name: expected["source_review"][name] for name in audit.SOURCE_FIELDS}
        )
    )
    return root, prior, qualification


@pytest.mark.parametrize("subject", ["candidate", "baseline"])
def test_builder_rejects_late_catalog_subject_changes(tmp_path: Path, subject: str) -> None:
    root, prior, qualification = builder_fixture(tmp_path)
    path = (
        root if subject == "candidate" else prior
    ) / "seasons/2007/synthetic-generated/defense.csv"
    with on_return(audit.baseline_record, lambda: path.write_bytes(path.read_bytes() + b"\n")):
        with pytest.raises(audit.ChartAuditError, match="changed|Stale|stale"):
            audit.build_expectations(root, prior, qualification)


def test_builder_rejects_qualification_change_after_parse(tmp_path: Path) -> None:
    root, prior, qualification = builder_fixture(tmp_path)
    changed = False

    def profile(frame: Any, event: str, result: Any) -> None:
        nonlocal changed
        if (
            not changed
            and event == "return"
            and frame.f_code is audit._json.__code__
            and frame.f_locals["path"] == qualification
        ):
            changed = True
            qualification.write_bytes(qualification.read_bytes() + b"\n")

    assert sys.getprofile() is None
    sys.setprofile(profile)
    try:
        with pytest.raises(audit.ChartAuditError, match="changed|stale|Stale"):
            audit.build_expectations(root, prior, qualification)
    finally:
        sys.setprofile(None)
    assert changed


def test_cli_retains_rejection_after_a_late_chart_change(tmp_path: Path) -> None:
    root, _, _ = fixture(tmp_path)
    path = root / "seasons/2007/synthetic-generated/defense.csv"
    destination = tmp_path / "audit.json"
    with on_return(audit._audit_roles, lambda: path.write_bytes(path.read_bytes() + b"\n")):
        assert audit.main(["--root", str(root), "--report", str(destination)]) == 1
    report = json.loads(destination.read_text())
    assert report["passed"] is False
    assert report["reason"]
    assert report["source_truth_revalidated"] is False


def test_native_boundary_rejects_late_staged_input_change(tmp_path: Path) -> None:
    from scripts.release_package import ReleaseError, audit_staged_charts, stage_sources

    root, _, _ = fixture(tmp_path)
    stage = tmp_path / "stage"
    stage_sources(root, stage)
    path = stage / "seasons/2007/synthetic-generated/defense.csv"
    with on_return(audit._audit_roles, lambda: path.write_bytes(path.read_bytes() + b"\n")):
        with pytest.raises(ReleaseError, match="changed|stale|Stale"):
            audit_staged_charts(root, stage)
    assert not (stage / audit.EXPECTATIONS).exists()


@pytest.mark.parametrize("subject", ["auditor", "imported_engine", "source_manifest"])
def test_executing_source_change_invalidates_qualification(tmp_path: Path, subject: str) -> None:
    """Modify only a detached public synthetic subprocess, never working source."""
    root, _, _ = fixture(tmp_path)
    (root / "scripts").mkdir()
    (root / "scripts/__init__.py").write_text("")
    (root / "scripts/audit_generated_charts.py").write_bytes(Path(audit.__file__).read_bytes())
    program = """
import json
import sys
from pathlib import Path
from scripts import audit_generated_charts as audit
root = Path.cwd()
path = root / {
    'auditor': 'scripts/audit_generated_charts.py',
    'imported_engine': 'bowl_bound/dice.py',
    'source_manifest': 'release/manifest.json',
}[sys.argv[1]]
changed = False
def profile(frame, event, result):
    global changed
    if not changed and event == 'return' and frame.f_code is audit._audit_roles.__code__:
        changed = True
        path.write_bytes(path.read_bytes() + b'\\n')
sys.setprofile(profile)
try:
    try:
        audit.audit_candidate(root)
    except audit.ChartAuditError as error:
        print(json.dumps({'rejected': True, 'reason': str(error)}))
    else:
        print(json.dumps({'rejected': False}))
finally:
    sys.setprofile(None)
assert changed
"""
    result = subprocess.run(
        [sys.executable, "-c", program, subject],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    observed = json.loads(result.stdout)
    assert observed["rejected"] is True
    assert observed["reason"]


def test_auditor_report_identifies_its_frozen_source(tmp_path: Path) -> None:
    """Transient file changes cannot replace the successful evidence identity."""
    root, _, _ = fixture(tmp_path)
    (root / "scripts").mkdir()
    (root / "scripts/__init__.py").write_text("")
    (root / "scripts/audit_generated_charts.py").write_bytes(Path(audit.__file__).read_bytes())
    program = """
import hashlib
import sys
from pathlib import Path
from scripts import audit_generated_charts as audit
path = Path(audit.__file__)
original = path.read_bytes()
ready = active = changed = False
def profile(frame, event, result):
    global ready, active, changed
    if event == 'return' and frame.f_code is audit._audit_roles.__code__:
        ready = True
    if ready and frame.f_code is Path.read_bytes.__code__ and frame.f_locals['self'] == path:
        if event == 'call' and not changed:
            active = changed = True
            path.write_bytes(original + b'\\n')
        elif event == 'return' and active:
            path.write_bytes(original)
            active = False
sys.setprofile(profile)
try:
    try:
        result = audit.audit_candidate(Path.cwd())
    except audit.ChartAuditError:
        result = None
finally:
    sys.setprofile(None)
    path.write_bytes(original)
assert changed
if result is not None:
    assert result['passed'] is True
    assert result['auditor_sha256'] == hashlib.sha256(original).hexdigest()
"""
    observed = subprocess.run(
        [sys.executable, "-c", program], cwd=root, text=True, capture_output=True, check=False
    )
    assert observed.returncode == 0, observed.stderr


def test_missing_auditor_source_retains_rejected_cli_evidence(tmp_path: Path) -> None:
    """A missing source identity stays absent, without destroying failure JSON."""
    root, _, _ = fixture(tmp_path)
    (root / "scripts").mkdir()
    (root / "scripts/__init__.py").write_text("")
    (root / "scripts/audit_generated_charts.py").write_bytes(Path(audit.__file__).read_bytes())
    program = """
import json
import sys
from pathlib import Path
from scripts import audit_generated_charts as audit
changed = False
def profile(frame, event, result):
    global changed
    if not changed and event == 'return' and frame.f_code is audit._audit_roles.__code__:
        changed = True
        Path(audit.__file__).unlink()
sys.setprofile(profile)
try:
    status = audit.main(['--root', str(Path.cwd()), '--report', 'rejected.json'])
finally:
    sys.setprofile(None)
assert changed
assert status == 1
report = json.loads(Path('rejected.json').read_text())
assert report['passed'] is False
assert report['reason']
assert 'auditor_sha256' not in report
"""
    observed = subprocess.run(
        [sys.executable, "-c", program], cwd=root, text=True, capture_output=True, check=False
    )
    assert observed.returncode == 0, observed.stderr
