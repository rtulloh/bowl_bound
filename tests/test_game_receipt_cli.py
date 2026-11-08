"""Private observer command keeps failures concrete and inputs immutable."""

import gzip
import json

import pytest

from scripts.audit_game_receipts import main
from tests.test_game_receipt_audit import receipt


def test_cli_audits_each_input_and_retains_first_failure(tmp_path):
    source = tmp_path / "private-data/input"
    source.mkdir(parents=True)
    good = source / "game-0001.json.gz"
    good.write_bytes(gzip.compress(json.dumps(receipt()).encode(), mtime=0))
    bad = receipt()
    bad["engine_log"][0]["statistics"]["team"] = "away"
    (source / "game-0002.json.gz").write_bytes(gzip.compress(json.dumps(bad).encode(), mtime=0))
    original = good.read_bytes()
    output = tmp_path / "private-data/observer"
    assert main([str(source), "--output", str(output)]) == 1
    result = json.loads((output / "audit.json").read_text())
    assert result["games_checked"] == 2
    assert result["games_passed_available_invariants"] == 1
    assert result["results"][1]["error"].startswith("report 1:")
    assert result["full_play_by_play_qualification"] is False
    assert good.read_bytes() == original


def test_cli_rejects_nonprivate_output(tmp_path):
    assert main([str(tmp_path), "--output", str(tmp_path / "public-output")]) == 2
    assert not (tmp_path / "public-output").exists()


def test_cli_attests_actual_loaded_observer_origin(monkeypatch, tmp_path):
    from tools import game_audit

    source = tmp_path / "private-data/game.json.gz"
    source.parent.mkdir()
    source.write_bytes(gzip.compress(json.dumps(receipt()).encode(), mtime=0))
    monkeypatch.setattr(game_audit, "__file__", str(tmp_path / "foreign.py"))
    output = tmp_path / "private-data/observer"
    assert main([str(source), "--output", str(output)]) == 2
    assert not output.exists()


def test_cli_retains_empty_report_failure_and_nonzero_exit(tmp_path):
    from tests.test_game_receipt_audit import empty_totals

    row = receipt()
    row["engine_log"] = []
    row["final"]["statistics"] = dict(home=empty_totals(), away=empty_totals())
    source = tmp_path / "private-data/game.json.gz"
    source.parent.mkdir()
    source.write_bytes(gzip.compress(json.dumps(row).encode(), mtime=0))
    output = tmp_path / "private-data/audit"
    assert main([str(source), "--output", str(output)]) == 1
    result = json.loads((output / "audit.json").read_text())
    assert result["results"][0]["status"] == "failed"
    assert "retained reports" in result["results"][0]["error"]


def test_cli_versions_and_aggregates_available_coverage_without_hiding_failure(tmp_path):
    source = tmp_path / "private-data/input"
    source.mkdir(parents=True)
    good = receipt()
    good["final"]["report_count"] = 1
    bad = receipt()
    bad["final"]["report_count"] = 0
    for number, row in enumerate([good, bad], 1):
        (source / f"game-{number}.json.gz").write_bytes(
            gzip.compress(json.dumps(row).encode(), mtime=0)
        )
    output = tmp_path / "private-data/audit"
    assert main([str(source), "--output", str(output)]) == 1
    result = json.loads((output / "audit.json").read_text())
    assert result["observer_version"] == "21"
    assert result["games_failed"] == 1
    assert result["results"][1]["status"] == "failed"
    assert "final report count" in result["results"][1]["error"]
    coverage = result["capability_summary"]
    assert coverage["event_ownership"] == dict(statuses={"GO": 1}, checked=1, excluded=0, unknown=0)
    assert coverage["chart_priority_and_cells"] == dict(
        statuses={"UNVERIFIED": 1}, checked=0, excluded=0, unknown=1
    )
    assert result["full_play_by_play_qualification"] is False


def test_cli_retains_nonobject_receipt_as_failure(tmp_path):
    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text("[]")
    output = tmp_path / "private-data/audit"
    assert main([str(source), "--output", str(output)]) == 1
    result = json.loads((output / "audit.json").read_text())
    assert result["games_checked"] == result["games_failed"] == 1
    assert result["games_passed_available_invariants"] == 0
    assert "receipt evidence" in result["results"][0]["error"]


def test_cli_attests_priority_oracle_origin_and_hash(monkeypatch, tmp_path):
    from tools import game_audit_priority

    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(receipt()))
    output = tmp_path / "private-data/valid"
    assert main([str(source), "--output", str(output)]) == 0
    result = json.loads((output / "audit.json").read_text())
    assert str(game_audit_priority.__file__) in result["source_sha256"]
    monkeypatch.setattr(game_audit_priority, "__file__", str(tmp_path / "foreign-priority.py"))
    invalid = tmp_path / "private-data/rejected"
    assert main([str(source), "--output", str(invalid)]) == 2
    assert not invalid.exists()


@pytest.mark.parametrize("name", ["game_audit", "game_audit_priority"])
def test_cli_rejects_inconsistent_module_spec_origin(monkeypatch, tmp_path, name):
    from importlib.machinery import ModuleSpec

    from tools import game_audit, game_audit_priority

    module = {"game_audit": game_audit, "game_audit_priority": game_audit_priority}[name]
    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(receipt()))
    monkeypatch.setattr(
        module, "__spec__", ModuleSpec(module.__name__, None, origin=str(tmp_path / "foreign.py"))
    )
    output = tmp_path / "private-data/rejected"
    assert main([str(source), "--output", str(output)]) == 2
    assert not output.exists()


@pytest.mark.parametrize("binding", ["accounting", "priority"])
def test_cli_rejects_replaced_imported_observer_binding(monkeypatch, tmp_path, binding):
    from scripts import audit_game_receipts
    from tools import game_audit

    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(receipt()))
    if binding == "accounting":
        original = audit_game_receipts.audit_receipt
        monkeypatch.setattr(audit_game_receipts, "audit_receipt", lambda row: original(row))
    else:
        original = game_audit.audit_priority
        monkeypatch.setattr(game_audit, "audit_priority", lambda row: original(row))
    output = tmp_path / "private-data/rejected"
    assert main([str(source), "--output", str(output)]) == 2
    assert not output.exists()


def test_cli_retains_post_audit_origin_change_as_global_failure(monkeypatch, tmp_path):
    from importlib.machinery import ModuleSpec

    from scripts import audit_game_receipts
    from tools import game_audit

    original = game_audit.audit_receipt

    def altered_origin(row):
        result = original(row)
        monkeypatch.setattr(
            game_audit,
            "__spec__",
            ModuleSpec(game_audit.__name__, None, origin=str(tmp_path / "foreign.py")),
        )
        return result

    monkeypatch.setattr(game_audit, "audit_receipt", altered_origin)
    monkeypatch.setattr(audit_game_receipts, "audit_receipt", altered_origin)
    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(receipt()))
    output = tmp_path / "private-data/failed"
    assert main([str(source), "--output", str(output)]) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["status"] == "failed"
    assert report["games_passed_available_invariants"] == 0
    assert report["games_passed_initial_comparison"] == 1
    assert report["capability_summary"] == {}
    assert report["results"][0]["audit"]["components"]["symbolic_priority"] == "UNVERIFIED"
    assert report["observer_source_unchanged"] is True
    assert report["observer_bindings_consistent"] is False
    assert "observer origin" in report["observer_binding_error"]


@pytest.mark.parametrize("mutation", ["file_origin", "spec_origin", "binding", "draw_binding"])
def test_cli_rejects_inconsistent_capture_link_observer(monkeypatch, tmp_path, mutation):
    from importlib.machinery import ModuleSpec

    from tools import game_audit, game_audit_envelope

    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(receipt()))
    output = tmp_path / "private-data/rejected"
    if mutation == "file_origin":
        monkeypatch.setattr(game_audit_envelope, "__file__", str(tmp_path / "foreign.py"))
    elif mutation == "spec_origin":
        monkeypatch.setattr(
            game_audit_envelope,
            "__spec__",
            ModuleSpec(game_audit_envelope.__name__, None, origin=str(tmp_path / "foreign.py")),
        )
    elif mutation == "binding":
        original = game_audit.audit_capture_links
        monkeypatch.setattr(game_audit, "audit_capture_links", lambda row: original(row))
    else:
        original = game_audit_envelope.audit_physical_draws
        monkeypatch.setattr(game_audit_envelope, "audit_physical_draws", lambda row: original(row))
    assert main([str(source), "--output", str(output)]) == 2
    assert not output.exists()


def test_cli_pins_capture_link_observer_bytes(tmp_path):
    from tools import game_audit_envelope

    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(receipt()))
    output = tmp_path / "private-data/review"
    assert main([str(source), "--output", str(output)]) == 0
    observed = json.loads((output / "audit.json").read_text())
    assert str(game_audit_envelope.__file__) in observed["source_sha256"]


@pytest.mark.parametrize("mutation", ["binding", "source_read_failure"])
def test_late_capture_observer_identity_invalidates_current_linkage_but_retains_diagnostics(
    monkeypatch, tmp_path, mutation
):
    from pathlib import Path

    from scripts import audit_game_receipts
    from tests.test_game_audit_capture_envelope import envelope_receipt
    from tools import game_audit, game_audit_envelope

    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(envelope_receipt()))
    output = tmp_path / "private-data/failed"
    if mutation == "binding":
        original = game_audit.audit_receipt

        def mutate(row):
            result = original(row)
            selected = game_audit_envelope.audit_capture_links
            monkeypatch.setattr(game_audit, "audit_capture_links", lambda row: selected(row))
            return result

        monkeypatch.setattr(game_audit, "audit_receipt", mutate)
        monkeypatch.setattr(audit_game_receipts, "audit_receipt", mutate)
    else:
        original, calls = Path.read_bytes, 0

        def disappears(path):
            nonlocal calls
            if path.name == "game_audit_envelope.py":
                calls += 1
                if calls == 2:
                    raise OSError("synthetic capture observer removed")
            return original(path)

        monkeypatch.setattr(Path, "read_bytes", disappears)
    assert main([str(source), "--output", str(output)]) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["games_passed_available_invariants"] == 0
    assert report["capability_summary"] == {}
    item = report["results"][0]
    assert item["initial_comparison"]["components"]["capture_internal_linkage"] == "GO"
    assert item["audit"]["components"]["capture_internal_linkage"] == "UNVERIFIED"
    assert item["audit"]["coverage"]["capture_internal_linkage"] == dict(
        checked=0, excluded=0, unknown=1
    )


@pytest.mark.parametrize("alias", ["envelope_equality", "envelope_facts", "lookup_equality"])
def test_cli_rejects_foreign_imported_helper_alias_even_when_entry_binding_matches(
    monkeypatch, tmp_path, alias
):
    from tests.test_game_audit_capture_envelope import envelope_receipt
    from tools import game_audit_envelope, game_audit_lookup

    row = envelope_receipt()
    if alias == "envelope_equality":
        row["audit_capture"]["typed_capture"]["priority_attempts"][0]["offense"]["yards"] = 8
        monkeypatch.setattr(game_audit_envelope, "_same_fact", lambda *_: True)
    elif alias == "envelope_facts":
        monkeypatch.setattr(game_audit_envelope, "_facts", lambda *_: None)
    else:
        monkeypatch.setattr(game_audit_lookup, "_same_fact", lambda *_: True)
    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(row))
    output = tmp_path / "private-data/rejected"
    assert main([str(source), "--output", str(output)]) == 2
    assert not output.exists()


@pytest.mark.parametrize("alias", ["envelope_equality", "envelope_facts", "lookup_equality"])
def test_late_imported_helper_change_cannot_leave_reusable_current_component_pass(
    monkeypatch, tmp_path, alias
):
    from scripts import audit_game_receipts
    from tests.test_game_audit_capture_envelope import envelope_receipt
    from tools import game_audit, game_audit_envelope, game_audit_lookup

    original = game_audit.audit_receipt

    def mutate(row):
        result = original(row)
        if alias == "envelope_equality":
            monkeypatch.setattr(game_audit_envelope, "_same_fact", lambda *_: True)
        elif alias == "envelope_facts":
            monkeypatch.setattr(game_audit_envelope, "_facts", lambda *_: None)
        else:
            monkeypatch.setattr(game_audit_lookup, "_same_fact", lambda *_: True)
        return result

    monkeypatch.setattr(game_audit, "audit_receipt", mutate)
    monkeypatch.setattr(audit_game_receipts, "audit_receipt", mutate)
    source = tmp_path / "private-data/game.json"
    source.parent.mkdir()
    source.write_text(json.dumps(envelope_receipt()))
    output = tmp_path / "private-data/rejected"
    assert main([str(source), "--output", str(output)]) == 1
    report = json.loads((output / "audit.json").read_text())
    assert report["observer_bindings_consistent"] is False
    assert report["capability_summary"] == {}
    assert report["games_passed_available_invariants"] == 0
    item = report["results"][0]
    assert item["initial_comparison"]["components"]["capture_internal_linkage"] == "GO"
    assert item["audit"]["components"]["capture_internal_linkage"] == "UNVERIFIED"
