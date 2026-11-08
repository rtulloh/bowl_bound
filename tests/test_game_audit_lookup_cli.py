"""External inventory pins and complete diagnostic failures are explicit."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit_game_receipts import main
from tests.test_game_audit_lookup import evidence, inventory
from tests.test_game_receipt_audit import receipt


def inputs(tmp_path):
    root = tmp_path / "private-data"
    root.mkdir()
    row = receipt()
    row["audit_capture"] = dict(lookup=evidence())
    source, frozen = root / "game.json", root / "inventory.json"
    source.write_text(json.dumps(row))
    frozen.write_text(json.dumps(inventory()))
    return source, frozen, hashlib.sha256(frozen.read_bytes()).hexdigest(), root / "audit"


def command(source, frozen, digest, output):
    return [
        str(source),
        "--output",
        str(output),
        "--lookup-inventory",
        str(frozen),
        "--lookup-inventory-sha256",
        digest,
    ]


def test_cli_uses_external_pinned_inventory_and_records_its_limited_authority(tmp_path):
    source, frozen, digest, output = inputs(tmp_path)
    already_loaded = sorted(
        name for name in sys.modules if name == "bowl_bound" or name.startswith("bowl_bound.")
    )
    assert main(command(source, frozen, digest, output)) == 0
    report = json.loads((output / "audit.json").read_text())
    assert report["lookup_inventory"] == dict(
        path=str(frozen.resolve()),
        sha256=digest,
        expected_sha256=digest,
        source_unchanged=True,
        teams=1,
        cells=840,
        scope="Pinned typed data agreement only; review authority and source truth not attested.",
    )
    assert report["capability_summary"]["typed_lookup_agreement"]["checked"] == 1
    assert report["loaded_engine_modules"] == already_loaded


def test_fresh_cli_process_imports_no_engine_for_lookup_expectations(tmp_path):
    source, frozen, digest, output = inputs(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.audit_game_receipts",
            *command(source, frozen, digest, output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((output / "audit.json").read_text())
    assert report["loaded_engine_modules"] == []


@pytest.mark.parametrize("option", ["wrong_sha", "missing_sha", "missing_file", "bad_inventory"])
def test_cli_rejects_unpinned_or_invalid_inventory(tmp_path, option):
    source, frozen, digest, output = inputs(tmp_path)
    args = command(source, frozen, digest, output)
    if option == "wrong_sha":
        args[-1] = "0" * 64
    elif option == "missing_sha":
        args = args[:-2]
    elif option == "missing_file":
        frozen.unlink()
    else:
        frozen.write_text("{}")
        args[-1] = hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert main(args) == 2
    assert not output.exists()


def test_cli_inventory_mutation_during_audit_is_retained_as_global_failure(monkeypatch, tmp_path):
    from scripts import audit_game_receipts
    from tools import game_audit

    source, frozen, digest, output = inputs(tmp_path)
    original = game_audit.audit_receipt

    def mutate(row, **kwargs):
        result = original(row, **kwargs)
        frozen.write_text(frozen.read_text() + " ")
        return result

    monkeypatch.setattr(audit_game_receipts, "audit_receipt", mutate)
    monkeypatch.setattr(game_audit, "audit_receipt", mutate)
    assert main(command(source, frozen, digest, output)) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["games_passed_available_invariants"] == 0
    assert report["games_passed_initial_comparison"] == 1
    assert report["capability_summary"] == {}
    assert report["lookup_inventory"]["source_unchanged"] is False
    assert report["status"] == "failed"
    assert report["results"][0]["audit"]["components"]["typed_lookup_agreement"] == "UNVERIFIED"
    assert (
        report["results"][0]["initial_comparison"]["components"]["typed_lookup_agreement"] == "GO"
    )


@pytest.mark.parametrize("origin", ["file", "spec", "binding"])
def test_cli_rejects_foreign_lookup_observer_origin_or_binding(monkeypatch, tmp_path, origin):
    from importlib.machinery import ModuleSpec

    from tools import game_audit, game_audit_lookup

    source, frozen, digest, output = inputs(tmp_path)
    if origin == "file":
        monkeypatch.setattr(game_audit_lookup, "__file__", str(tmp_path / "foreign.py"))
    elif origin == "spec":
        monkeypatch.setattr(
            game_audit_lookup,
            "__spec__",
            ModuleSpec(game_audit_lookup.__name__, None, origin="foreign.py"),
        )
    else:
        original = game_audit.audit_lookup
        monkeypatch.setattr(game_audit, "audit_lookup", lambda *args: original(*args))
    assert main(command(source, frozen, digest, output)) == 2
    assert not output.exists()


def test_unreadable_receipt_does_not_vanish_from_failure_inventory(monkeypatch, tmp_path):
    source, _, _, output = inputs(tmp_path)
    original = Path.read_bytes

    def unreadable(path):
        if path == source:
            raise OSError("synthetic unreadable receipt")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    assert main([str(source), "--output", str(output)]) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["games_checked"] == report["games_failed"] == 1
    assert report["results"][0]["sha256"] is None
    assert "unreadable receipt" in report["results"][0]["error"]


def test_missing_observer_on_final_recheck_retains_a_failure_report(monkeypatch, tmp_path):
    source, _, _, output = inputs(tmp_path)
    source.write_text(json.dumps(receipt()))
    original, calls = Path.read_bytes, 0

    def disappears(path):
        nonlocal calls
        if path.name == "game_audit.py":
            calls += 1
            if calls == 2:
                raise OSError("synthetic observer removed")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", disappears)
    assert main([str(source), "--output", str(output)]) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["observer_source_unchanged"] is False
    assert "observer removed" in report["observer_source_error"]
    assert report["results"][0]["audit"]["components"]["scoring_totals"] == "UNVERIFIED"
    assert report["results"][0]["initial_comparison"]["components"]["scoring_totals"] == "GO"


def test_truncated_gzip_is_retained_as_a_failed_input(tmp_path):
    import gzip

    source, _, _, output = inputs(tmp_path)
    source.unlink()
    source = source.with_suffix(".json.gz")
    source.write_bytes(gzip.compress(json.dumps(receipt()).encode())[:-5])
    assert main([str(source), "--output", str(output)]) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["games_checked"] == report["games_failed"] == 1
    assert "end-of-stream" in report["results"][0]["error"]
