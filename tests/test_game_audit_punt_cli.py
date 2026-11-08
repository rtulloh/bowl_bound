"""Current punt qualification depends on the same frozen observer inputs."""

import hashlib
import json
from importlib.machinery import ModuleSpec
from types import SimpleNamespace

import pytest

from scripts.audit_game_receipts import main
from tests.test_game_audit_lookup_cli import command, inputs
from tests.test_game_audit_punt_commitment import punt_subject


def punt_inputs(tmp_path):
    source, frozen, _, output = inputs(tmp_path)
    row, inventory = punt_subject()
    source.write_text(json.dumps(row))
    frozen.write_text(json.dumps(inventory))
    return source, frozen, hashlib.sha256(frozen.read_bytes()).hexdigest(), output


@pytest.mark.parametrize("fault", ["file", "spec", "binding", "commitment", "kickoff"])
def test_punt_dependency_refuses_before_comparison(monkeypatch, tmp_path, fault):
    from tools import game_audit, game_audit_punt

    source, frozen, digest, output = punt_inputs(tmp_path)
    if fault == "file":
        monkeypatch.setattr(game_audit_punt, "__file__", str(tmp_path / "foreign.py"))
    elif fault == "spec":
        monkeypatch.setattr(
            game_audit_punt,
            "__spec__",
            ModuleSpec(game_audit_punt.__name__, None, origin="foreign.py"),
        )
    elif fault == "binding":
        original = game_audit.audit_punt_commitments
        monkeypatch.setattr(game_audit, "audit_punt_commitments", lambda *a, **k: original(*a, **k))
    elif fault == "kickoff":
        monkeypatch.setattr(
            game_audit_punt, "kickoff", SimpleNamespace(**vars(game_audit_punt.kickoff))
        )
    else:
        monkeypatch.setattr(
            game_audit_punt,
            "commitment",
            SimpleNamespace(**vars(game_audit_punt.commitment)),
        )
    assert main(command(source, frozen, digest, output)) == 2
    assert not output.exists()


@pytest.mark.parametrize("fault", ["file", "commitment", "inventory", "kickoff"])
def test_late_punt_dependency_invalidates_current_flags_and_details(monkeypatch, tmp_path, fault):
    from pathlib import Path

    from scripts import audit_game_receipts
    from tools import game_audit, game_audit_punt

    source, frozen, digest, output = punt_inputs(tmp_path)
    original = game_audit.audit_receipt
    if fault == "inventory":
        original_read = Path.read_bytes
        reads = 0

        def read(path):
            nonlocal reads
            data = original_read(path)
            if path.resolve() == frozen.resolve():
                reads += 1
                if reads > 1:
                    return data + b" "
            return data

        monkeypatch.setattr(Path, "read_bytes", read)
    else:

        def changed(row, **kwargs):
            result = original(row, **kwargs)
            if fault == "file":
                monkeypatch.setattr(game_audit_punt, "__file__", str(tmp_path / "foreign.py"))
            elif fault == "kickoff":
                monkeypatch.setattr(
                    game_audit_punt,
                    "kickoff",
                    SimpleNamespace(**vars(game_audit_punt.kickoff)),
                )
            else:
                monkeypatch.setattr(
                    game_audit_punt,
                    "commitment",
                    SimpleNamespace(**vars(game_audit_punt.commitment)),
                )
            return result

        monkeypatch.setattr(game_audit, "audit_receipt", changed)
        monkeypatch.setattr(audit_game_receipts, "audit_receipt", changed)
    assert main(command(source, frozen, digest, output)) == 1
    result = json.loads((output / "audit.json").read_text())
    item = result["results"][0]
    assert item["initial_comparison"]["components"]["punt_fair_catch_commitment"] == "GO"
    assert item["initial_comparison"]["punt_commitment_counts"]["checked"] == 1
    assert item["audit"]["components"]["punt_fair_catch_commitment"] == "UNVERIFIED"
    assert item["audit"]["coverage"]["punt_fair_catch_commitment"] == dict(
        checked=0, excluded=0, unknown=2
    )
    assert "punt_commitment_counts" not in item["audit"]
    assert result["games_passed_available_invariants"] == 0
