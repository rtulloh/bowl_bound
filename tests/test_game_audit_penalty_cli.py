"""Current penalty qualification depends on the same frozen observer inputs."""

import hashlib
import json
from importlib.machinery import ModuleSpec
from types import SimpleNamespace

import pytest

from scripts.audit_game_receipts import main
from tests.test_game_audit_lookup_cli import command, inputs
from tests.test_game_audit_penalty_commitment import penalty_subject


def penalty_inputs(tmp_path):
    source, frozen, _, output = inputs(tmp_path)
    row, inventory = penalty_subject()
    source.write_text(json.dumps(row))
    frozen.write_text(json.dumps(inventory))
    return source, frozen, hashlib.sha256(frozen.read_bytes()).hexdigest(), output


@pytest.mark.parametrize("fault", ["file", "spec", "binding", "commitment", "priority"])
def test_penalty_dependency_refuses_before_comparison(monkeypatch, tmp_path, fault):
    from tools import game_audit, game_audit_penalty

    source, frozen, digest, output = penalty_inputs(tmp_path)
    if fault == "file":
        monkeypatch.setattr(game_audit_penalty, "__file__", str(tmp_path / "foreign.py"))
    elif fault == "spec":
        monkeypatch.setattr(
            game_audit_penalty,
            "__spec__",
            ModuleSpec(game_audit_penalty.__name__, None, origin="foreign.py"),
        )
    elif fault == "binding":
        original = game_audit.audit_penalty_commitments
        monkeypatch.setattr(
            game_audit, "audit_penalty_commitments", lambda *a, **k: original(*a, **k)
        )
    elif fault == "priority":
        monkeypatch.setattr(
            game_audit_penalty, "priority", SimpleNamespace(**vars(game_audit_penalty.priority))
        )
    else:
        monkeypatch.setattr(
            game_audit_penalty,
            "commitment",
            SimpleNamespace(**vars(game_audit_penalty.commitment)),
        )
    assert main(command(source, frozen, digest, output)) == 2
    assert not output.exists()


@pytest.mark.parametrize("fault", ["file", "commitment", "inventory", "priority"])
def test_late_penalty_dependency_invalidates_current_flags_and_details(
    monkeypatch, tmp_path, fault
):
    from pathlib import Path

    from scripts import audit_game_receipts
    from tools import game_audit, game_audit_penalty

    source, frozen, digest, output = penalty_inputs(tmp_path)
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
                monkeypatch.setattr(game_audit_penalty, "__file__", str(tmp_path / "foreign.py"))
            elif fault == "priority":
                monkeypatch.setattr(
                    game_audit_penalty,
                    "priority",
                    SimpleNamespace(**vars(game_audit_penalty.priority)),
                )
            else:
                monkeypatch.setattr(
                    game_audit_penalty,
                    "commitment",
                    SimpleNamespace(**vars(game_audit_penalty.commitment)),
                )
            return result

        monkeypatch.setattr(game_audit, "audit_receipt", changed)
        monkeypatch.setattr(audit_game_receipts, "audit_receipt", changed)
    assert main(command(source, frozen, digest, output)) == 1
    result = json.loads((output / "audit.json").read_text())
    item = result["results"][0]
    assert item["initial_comparison"]["components"]["accepted_previous_penalty_commitment"] == "GO"
    assert item["initial_comparison"]["penalty_commitment_counts"]["checked"] == 1
    assert item["audit"]["components"]["accepted_previous_penalty_commitment"] == "UNVERIFIED"
    assert item["audit"]["coverage"]["accepted_previous_penalty_commitment"] == dict(
        checked=0, excluded=0, unknown=2
    )
    assert "penalty_commitment_counts" not in item["audit"]
    assert result["games_passed_available_invariants"] == 0
