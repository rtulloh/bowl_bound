"""Synthetic evidence inventory and completeness mutations, without an engine."""

from copy import deepcopy

import pytest

from tests.test_game_receipt_audit import empty_totals, receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


@pytest.mark.parametrize("count", [0, 2, True, "1", None])
def test_declared_report_count_corruption_is_rejected(count: object) -> None:
    row = receipt()
    row["final"]["report_count"] = count
    with pytest.raises(ReceiptAuditError, match="final report count"):
        audit_receipt(row)


def test_boolean_report_identity_is_not_report_one() -> None:
    row = receipt()
    row["engine_log"][0]["number"] = True
    with pytest.raises(ReceiptAuditError, match="report 1.*identity"):
        audit_receipt(row)


@pytest.mark.parametrize("field,value", [("pending", True), ("supported", False)])
def test_completed_receipt_cannot_retain_uncommitted_reports(field: str, value: bool) -> None:
    row = receipt()
    row["engine_log"][0][field] = value
    row["engine_log"][0]["statistics"] = dict(kind="excluded", team=None, yards=0, touchdown=False)
    row["final"]["statistics"] = dict(home=empty_totals(), away=empty_totals())
    with pytest.raises(ReceiptAuditError, match="report 1.*completed"):
        audit_receipt(row)


def test_legacy_missing_count_is_unverified_and_versions_are_explicit() -> None:
    result = audit_receipt(receipt())
    assert result["observer_version"] == "20"
    inventory = result["evidence_inventory"]
    assert inventory["version"] == "1"
    assert inventory["input_format"] == "unversioned_retained_game"
    assert inventory["report_count"] == dict(actual=1, declared=None, status="UNVERIFIED")
    assert inventory["typed_lookup_priority"]["status"] == "UNVERIFIED"
    assert inventory["command_pending_boundaries"]["status"] == "UNVERIFIED"
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False


def test_matching_count_only_verifies_inventory_not_branch_or_runtime_claims() -> None:
    row = receipt()
    row["final"]["report_count"] = 1
    row["runtime"] = dict(
        python="synthetic",
        executable="synthetic",
        rules_profile="synthetic-v1",
        source_sha256={"synthetic.py": "a" * 64},
        loaded_modules={"synthetic": {}},
    )
    row["configuration"] = dict(engine_coach_policy="synthetic-policy")
    row["save_replay"] = dict(requested=True, checkpoint_verified=True, final_replay_verified=True)
    original = deepcopy(row)
    result = audit_receipt(row)
    inventory = result["evidence_inventory"]
    assert inventory["report_count"] == dict(actual=1, declared=1, status="GO")
    assert inventory["runtime_claims"]["status"] == "UNVERIFIED"
    assert inventory["runtime_claims"]["rules_profile"] == "synthetic-v1"
    assert inventory["runtime_claims"]["engine_coach_policy"] == "synthetic-policy"
    assert inventory["runtime_claims"]["source_hash_count"] == 1
    assert inventory["runtime_claims"]["loaded_module_count"] == 1
    assert inventory["replay_claims"]["status"] == "UNVERIFIED"
    assert result["components"]["chart_priority_and_cells"] == "UNVERIFIED"
    assert row == original


def test_zero_observation_is_not_an_exercised_ownership_or_award_check() -> None:
    row = receipt()
    row["engine_log"][0].update(
        outcome="pre_snap", statistics=dict(kind="excluded", team=None, yards=0, touchdown=False)
    )
    row["final"]["statistics"] = dict(home=empty_totals(), away=empty_totals())
    result = audit_receipt(row)
    assert result["components"]["event_ownership"] == "NOTRUN"
    assert result["components"]["scoring_awards"] == "NOTRUN"
    assert result["components"]["scoring_totals"] == "GO"
    assert result["coverage"]["event_ownership"] == dict(checked=0, excluded=1, unknown=0)
    assert result["coverage"]["chart_priority_and_cells"] == dict(checked=0, excluded=0, unknown=1)


def test_no_excluded_credit_is_not_excluded_mechanism_coverage() -> None:
    result = audit_receipt(receipt())
    assert result["components"]["excluded_statistics"] == "NOTRUN"
    assert result["coverage"]["event_ownership"] == dict(checked=1, excluded=0, unknown=0)
    assert result["coverage"]["excluded_statistics"] == dict(checked=0, excluded=1, unknown=0)


@pytest.mark.parametrize("field", ["runtime", "configuration", "save_replay"])
def test_present_identity_evidence_must_be_an_object(field: str) -> None:
    row = receipt()
    row[field] = []
    with pytest.raises(ReceiptAuditError, match=f"{field} evidence"):
        audit_receipt(row)


@pytest.mark.parametrize("row", [None, [], "completed"])
def test_receipt_root_must_be_an_object(row: object) -> None:
    with pytest.raises(ReceiptAuditError, match="receipt evidence"):
        audit_receipt(row)


@pytest.mark.parametrize("field", ["final", "audit_capture"])
def test_boundary_evidence_cannot_be_a_nonobject(field: str) -> None:
    row = receipt()
    row[field] = None
    with pytest.raises(ReceiptAuditError, match=f"{field} evidence"):
        audit_receipt(row)
