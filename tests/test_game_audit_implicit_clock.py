"""Independent normal implicit timing and terminal facts; engine only a subject."""

from copy import deepcopy

import pytest

from bowl_bound.models import ResultKind
from bowl_bound.timing import Clock
from tests.test_game_audit_ordinary_commitment import log_digest, regulation_receipt
from tests.test_game_audit_standard_clock import sequence_receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


def implicit_receipt(**kwargs):
    return sequence_receipt(actions=[("snap", ["1", "A"]), ("snap", ["1", "A"])], **kwargs)


def change_last_report(row, alter):
    commands = row["audit_capture"]["typed_capture"]["commands"]
    command = commands[-1]
    report = command["report_changes"][0]["after"]
    alter(report, command)
    command["returned_report"] = deepcopy(report)
    command["report_revisions"] = [deepcopy(report)]
    history = deepcopy(commands[0]["initial_log"]) + [
        deepcopy(c["report_revisions"][0]) for c in commands
    ]
    command["after"]["log_sha256"] = log_digest(history)


def test_implicit_normal_checks_second_report_and_prior_charge():
    row, frozen = implicit_receipt()
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"
    assert result["ordinary_commitment_counts"]["checked"] == 2
    assert result["components"]["standard_clock"] == "GO"
    assert result["standard_clock_counts"]["checked"] == 2
    assert result["standard_clock_counts"]["implicit"] == 1
    assert result["standard_clock_counts"]["timing_facts_checked"] == 2


@pytest.mark.parametrize(
    "fault", ["goal", "down", "distance", "owner", "called", "resolved", "credit", "box"]
)
def test_second_implicit_report_corruptions_ignored_before_extension_refuse(fault):
    row, frozen = implicit_receipt()

    def alter(report, command):
        if fault in {"goal", "down", "distance", "owner"}:
            field, value = {
                "goal": ("yards_to_goal", 75),
                "down": ("down", 4),
                "distance": ("yards_to_go", 5),
                "owner": ("possession", "away"),
            }[fault]
            report["state_after"][field] = value
            command["after"]["view"]["state"][field] = value
        elif fault in {"called", "resolved"}:
            report[fault + "_play"] = "Counter"
        elif fault == "credit":
            report["statistics"]["yards"] = 3
        else:
            command["after"]["view"]["statistics"]["home"]["rushing_yards"] += 1

    change_last_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "seconds", "reference", "clock"])
def test_implicit_prior_charge_corruptions_cannot_hide_in_skipped_context(fault):
    row, frozen = implicit_receipt()
    after = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    ledger = after["timing_log"]
    if fault == "missing":
        ledger.pop()
    elif fault == "duplicate":
        ledger.append(deepcopy(ledger[-1]))
    elif fault == "seconds":
        ledger[-1]["seconds"] = 20
    elif fault == "reference":
        ledger[-1]["play_number"] += 1
    else:
        after["clock"]["remaining"] -= 30
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field",
    [
        "first_down",
        "change_of_possession",
        "penalty",
        "incomplete",
        "scoring",
        "touchback",
        "out_of_bounds",
        "guaranteed_out_of_bounds",
        "unreturned_kickoff",
        "conversion",
        "no_elapsed_time",
    ],
)
def test_terminal_timing_flags_are_subjects_not_expected_authority(field):
    row, frozen = regulation_receipt()

    def alter(report, command):
        report["timing"][field] = True

    change_last_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("fault", ["missing", "extra", "boolean-type"])
def test_terminal_timing_requires_exact_strict_fields(fault):
    row, frozen = regulation_receipt()

    def alter(report, command):
        if fault == "missing":
            report["timing"].pop("penalty")
        elif fault == "extra":
            report["timing"]["invented"] = False
        else:
            report["timing"]["first_down"] = 0

    change_last_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("quarter,start,end", [(2, 125, 85), (4, 305, 265)])
def test_implicit_commit_crosses_oob_window_before_second_snap(quarter, start, end):
    row, frozen = implicit_receipt(clock=Clock(quarter, start), oob=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    commands = row["audit_capture"]["typed_capture"]["commands"]
    assert commands[-1]["after"]["view"]["clock"]["remaining"] == end
    assert [c["seconds"] for c in commands[-1]["after"]["view"]["timing_log"][-2:]] == [30, 10]


@pytest.mark.parametrize("quarter", [1, 3])
def test_implicit_quarter_expiry_runs_new_play_in_next_period(quarter):
    row, frozen = implicit_receipt(clock=Clock(quarter, 25, (1, 2)))
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    assert result["ordinary_commitment_counts"]["checked"] == 2
    after = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    assert after["clock"]["quarter"] == quarter + 1 and after["clock"]["remaining"] == 900
    assert after["clock"]["timeouts"] == [1, 2]


def test_implicit_half_expiry_has_no_new_play_and_only_commits_prior_time():
    row, frozen = implicit_receipt(clock=Clock(2, 25, (1, 2)))
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    counts = result["standard_clock_counts"]
    assert counts["checked"] == 2 and counts["period_boundaries"] == 1
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    assert command["returned_report"]["outcome"] == "period_boundary"
    assert command["draw_range"][0] == command["draw_range"][1]
    assert command["report_range"][0] == command["report_range"][1]


def test_optional_clock_pending_none_with_zero_timeouts_is_valid_format():
    row, frozen = sequence_receipt(clock=Clock(1, 75, (0, 0)), actions=[("snap", ["1", "A"])] * 4)
    commands = row["audit_capture"]["typed_capture"]["commands"]
    assert commands[2]["after"]["view"]["pending"] is None
    assert commands[3]["before"]["view"]["pending"] is None
    assert commands[3]["before"]["view"]["clock_optional"] is True
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    assert result["ordinary_commitment_counts"]["checked"] == 4


@pytest.mark.parametrize(
    "fault",
    ["missing-pending", "mandatory-id", "duplicate-id", "outcomes", "context", "enabled-type"],
)
def test_claimed_optional_clock_context_cannot_hide_mandatory_or_malformed_evidence(fault):
    row, frozen = implicit_receipt()
    before = row["audit_capture"]["typed_capture"]["commands"][-1]["before"]["view"]
    if fault == "missing-pending":
        before.pop("pending")
    elif fault == "mandatory-id":
        before["pending"]["choices"][0]["id"] = "interception:return"
    elif fault == "duplicate-id":
        before["pending"]["choices"].append(deepcopy(before["pending"]["choices"][0]))
    elif fault == "outcomes":
        before["pending"]["decision_outcomes"] = [{}]
    elif fault == "context":
        before["pending"]["decision_context"] = {}
    else:
        before["pending"]["choices"][0]["enabled"] = 1
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_period_boundary_cannot_retain_previous_statistical_credit_as_new_return_fact():
    row, frozen = implicit_receipt(clock=Clock(2, 25, (1, 2)))
    commands = row["audit_capture"]["typed_capture"]["commands"]
    commands[-1]["returned_report"]["statistics"] = deepcopy(
        commands[0]["returned_report"]["statistics"]
    )
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_pending_new_interception_does_not_count_unqualified_implicit_mechanism():
    row, frozen = implicit_receipt(second_kind=ResultKind.INTERCEPTION)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "UNVERIFIED"
    assert result["standard_clock_counts"]["checked"] == 1
    assert result["standard_clock_counts"]["unknown"] == 1
    assert result["standard_clock_counts"]["implicit"] == 0


@pytest.mark.parametrize(
    "fault",
    ["outcome", "trace", "yards", "timing", "extends", "before-state", "box", "score", "phase"],
)
def test_half_boundary_requires_excluded_return_and_zero_new_credit(fault):
    row, frozen = implicit_receipt(clock=Clock(2, 25, (1, 2)))
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    report, after = command["returned_report"], command["after"]["view"]
    if fault == "outcome":
        report["outcome"] = "advance"
    elif fault == "trace":
        report["trace"] = [{}]
    elif fault == "yards":
        report["yards"] = 0
    elif fault == "timing":
        report["timing"]["first_down"] = True
    elif fault == "extends":
        report["extends_quarter"] = True
    elif fault == "before-state":
        report["state_before"]["yards_to_goal"] -= 1
    elif fault == "box":
        after["statistics"]["home"]["rushing_yards"] += 2
    elif fault == "score":
        after["score"]["home"] += 1
    else:
        after["phase"] = "scrimmage"
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_unsupported_hurry_taints_clock_chain_without_later_reanchor():
    row, frozen = sequence_receipt(
        actions=[
            ("snap", ["1", "A"]),
            ("decide", ["clock:hurry"]),
            ("snap", ["1", "A"]),
            ("decide", ["clock:runoff"]),
        ]
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    counts = result["standard_clock_counts"]
    assert result["components"]["standard_clock"] == "UNVERIFIED"
    assert (counts["checked"], counts["unknown"]) == (1, 3)
    assert counts["dispositions"][-1]["reason"] == "unverified_prior_continuation"


def test_no_new_play_boundary_keeps_previous_report_reference():
    row, frozen = implicit_receipt(clock=Clock(2, 25, (1, 2)))
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    command["returned_report"]["number"] += 1
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)
