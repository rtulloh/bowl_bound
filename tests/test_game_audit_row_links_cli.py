"""Row-link observer dependencies retain current qualification and failures."""

import hashlib
import json
import subprocess
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.audit_game_receipts import main
from tests.test_game_audit_lookup_cli import command, inputs
from tests.test_game_audit_row_links import frozen_inventory, observed


def row_inputs(tmp_path):
    source, frozen, _, output = inputs(tmp_path)
    source.write_text(json.dumps(observed()))
    frozen.write_text(json.dumps(frozen_inventory()))
    return source, frozen, hashlib.sha256(frozen.read_bytes()).hexdigest(), output


@pytest.mark.parametrize("fault", ["file", "spec", "binding", "lookup_alias", "envelope_alias"])
def test_cli_rejects_foreign_row_observer_dependencies_before_comparison(
    monkeypatch, tmp_path, fault
):
    from tools import game_audit, game_audit_row_links

    source, frozen, digest, output = row_inputs(tmp_path)
    if fault == "file":
        monkeypatch.setattr(game_audit_row_links, "__file__", str(tmp_path / "foreign.py"))
    elif fault == "spec":
        monkeypatch.setattr(
            game_audit_row_links,
            "__spec__",
            ModuleSpec(game_audit_row_links.__name__, None, origin="foreign.py"),
        )
    elif fault == "binding":
        original = game_audit.audit_row_links
        monkeypatch.setattr(game_audit, "audit_row_links", lambda *args: original(*args))
    else:
        name = "lookup" if fault == "lookup_alias" else "envelope"
        original = getattr(game_audit_row_links, name)
        monkeypatch.setattr(game_audit_row_links, name, SimpleNamespace(**vars(original)))
    assert main(command(source, frozen, digest, output)) == 2
    assert not output.exists()


@pytest.mark.parametrize("fault", ["origin", "source"])
def test_late_row_observer_change_invalidates_all_current_flags(monkeypatch, tmp_path, fault):
    from scripts import audit_game_receipts
    from tools import game_audit, game_audit_row_links

    source, frozen, digest, output = row_inputs(tmp_path)
    if fault == "origin":
        original = game_audit.audit_receipt

        def late(row, **kwargs):
            result = original(row, **kwargs)
            monkeypatch.setattr(game_audit_row_links, "__file__", str(tmp_path / "foreign.py"))
            return result

        monkeypatch.setattr(audit_game_receipts, "audit_receipt", late)
        monkeypatch.setattr(game_audit, "audit_receipt", late)
    else:
        original_read = Path.read_bytes
        count = 0

        def changed(path):
            nonlocal count
            content = original_read(path)
            if path.name == "game_audit_row_links.py":
                count += 1
                if count > 1:
                    return content + b"\n"
            return content

        monkeypatch.setattr(Path, "read_bytes", changed)
    assert main(command(source, frozen, digest, output)) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["games_passed_available_invariants"] == 0
    assert report["capability_summary"] == {}
    item = report["results"][0]
    assert item["initial_comparison"]["components"]["captured_row_linkage"] == "GO"
    assert item["audit"]["components"]["captured_row_linkage"] == "UNVERIFIED"


def test_row_consumer_fresh_cli_has_no_engine_import_and_pins_exact_observers(tmp_path):
    source, frozen, digest, output = row_inputs(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.audit_game_receipts",
            *command(source, frozen, digest, output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((output / "audit.json").read_text())
    assert report["loaded_engine_modules"] == []
    assert {Path(path).name for path in report["source_sha256"]} == {
        "audit_game_receipts.py",
        "game_audit.py",
        "game_audit_priority.py",
        "game_audit_lookup.py",
        "game_audit_envelope.py",
        "game_audit_row_links.py",
        "game_audit_commitment.py",
        "game_audit_clock.py",
        "game_audit_continuity.py",
        "game_audit_pat.py",
        "game_audit_final_binding.py",
        "game_audit_kickoff.py",
        "game_audit_supplemental.py",
        "game_audit_penalty.py",
        "game_audit_punt.py",
    }
    assert len(report["source_sha256"]) == 15


@pytest.mark.parametrize("helper", ["fact", "equality", "physical"])
@pytest.mark.parametrize("late", [False, True])
def test_shared_row_helper_change_refuses_current_qualification(
    monkeypatch, tmp_path, helper, late
):
    from scripts import audit_game_receipts
    from tools import game_audit, game_audit_envelope, game_audit_lookup

    source, frozen, digest, output = row_inputs(tmp_path)
    module, name = {
        "fact": (game_audit_envelope, "_facts"),
        "equality": (game_audit_lookup, "_same_fact"),
        "physical": (game_audit_envelope, "audit_physical_draws"),
    }[helper]
    original_helper = getattr(module, name)

    def replacement(*args, **kwargs):
        return original_helper(*args, **kwargs)

    if late:
        original = game_audit.audit_receipt

        def changed(row, **kwargs):
            result = original(row, **kwargs)
            monkeypatch.setattr(module, name, replacement)
            return result

        monkeypatch.setattr(audit_game_receipts, "audit_receipt", changed)
        monkeypatch.setattr(game_audit, "audit_receipt", changed)
    else:
        monkeypatch.setattr(module, name, replacement)
    assert main(command(source, frozen, digest, output)) == (1 if late else 2)
    if late:
        report = json.loads((output / "audit.json").read_text())
        item = report["results"][0]
        assert item["initial_comparison"]["components"]["captured_row_linkage"] == "GO"
        assert item["audit"]["components"]["captured_row_linkage"] == "UNVERIFIED"
        assert report["games_passed_available_invariants"] == 0
    else:
        assert not output.exists()
