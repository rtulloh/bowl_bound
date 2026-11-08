"""Independent fixed in-field punt returns; no engine expectations reused."""

from itertools import product

import pytest

from bowl_bound.dice import OffensiveRoll
from bowl_bound.timing import Clock
from tests.test_game_audit_punt_commitment import alter_final, punt_subject
from tools.game_audit import ReceiptAuditError, audit_receipt


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("gain,goal", [(3, 72), (0, 75), (-4, 79)])
def test_fixed_return_literal_gain_owner_and_excluded_boxes(side, gain, goal):
    row, inventory = punt_subject(side=side, choice="kick:return", return_gain=gain)
    result = audit_receipt(row, lookup_inventory=inventory)
    counts = result["punt_commitment_counts"]
    assert counts["checked"] == counts["return_checked"] == 1
    report = row["engine_log"][-1]
    assert {
        key: report["state_after"][key]
        for key in ("possession", "yards_to_goal", "down", "yards_to_go")
    } == dict(
        possession="away" if side == "home" else "home", yards_to_goal=goal, down=1, yards_to_go=10
    )
    assert report["statistics"] == dict(kind="excluded", team=None, yards=0, touchdown=False)
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize("spot,flight,gain,goal", [(99, 98, 0, 99), (90, 0, 9, 1)])
def test_literal_return_infield_endpoint_equalities(spot, flight, gain, goal):
    row, inventory = punt_subject(spot=spot, flight=flight, choice="kick:return", return_gain=gain)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["punt_commitment_counts"]["return_checked"] == 1
    assert row["engine_log"][-1]["state_after"]["yards_to_goal"] == goal
    assert row["engine_log"][-1]["state_after"]["yards_to_go"] == min(10, goal)


def test_explicit_no_change_return_is_zero_not_missing():
    row, inventory = punt_subject(choice="kick:return", return_kind="no_change")
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["punt_commitment_counts"]["return_checked"] == 1
    assert row["engine_log"][-1]["state_after"]["yards_to_goal"] == 75


@pytest.mark.parametrize(
    "fault",
    [
        "goal",
        "owner",
        "down",
        "distance",
        "called",
        "resolved",
        "timing",
        "yards",
        "outcome",
        "box-home",
        "box-away",
        "score",
    ],
)
def test_numeric_return_ignored_corruptions_must_refuse(fault):
    row, inventory = punt_subject(choice="kick:return")

    def corrupt(report, command):
        if fault in {"goal", "owner", "down", "distance"}:
            key, value = {
                "goal": ("yards_to_goal", 78),
                "owner": ("possession", "home"),
                "down": ("down", 2),
                "distance": ("yards_to_go", 9),
            }[fault]
            report["state_after"][key] = value
            command["after"]["view"]["state"][key] = value
        elif fault in {"called", "resolved"}:
            report[fault + "_play"] = "Kickoff"
        elif fault == "timing":
            report["timing"]["first_down"] = True
        elif fault == "yards":
            report["yards"] = 3
        elif fault == "outcome":
            report["outcome"] = "punt_fair_catch"
        elif fault.startswith("box-"):
            command["after"]["view"]["statistics"][fault[4:]]["total_yards"] += 1
        else:
            command["after"]["view"]["score"]["home"] += 1

    alter_final(row, corrupt)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("fault", ["seconds", "remaining", "charged-id"])
def test_numeric_return_local_charge_corruptions_must_refuse(fault):
    row, inventory = punt_subject(choice="kick:return", clock=Clock(1, 600, (1, 2)))
    view = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    if fault == "seconds":
        view["timing_log"][-1]["seconds"] += 1
    elif fault == "remaining":
        view["clock"]["remaining"] += 1
    else:
        view["timing_log"][-1]["play_number"] += 1
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("remaining", [5, 600])
def test_numeric_return_id_must_not_reuse_charged_prefix_even_period_unknown(remaining):
    row, inventory = punt_subject(choice="kick:return", clock=Clock(1, remaining, (1, 2)))
    commands = row["audit_capture"]["typed_capture"]["commands"]
    number = commands[-1]["returned_report"]["number"]
    for command in commands:
        for endpoint in ("before", "after"):
            command[endpoint]["view"]["timing_log"][0]["play_number"] = number
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("gain,kind", [(100, "yards"), (-100, "yards"), (0, "fumble")])
def test_nonfixed_or_goal_crossing_return_stays_unknown_without_false_refusal(gain, kind):
    row, inventory = punt_subject(choice="kick:return", return_gain=gain, return_kind=kind)
    # This deliberately partial wrapper may have no prior field naming the
    # scoring receiver. Inspect the bounded component, not the complete-game
    # score-name inventory, for the unsupported goal/recovery companion.
    from tools.game_audit_punt import audit_punt_commitments

    result = audit_punt_commitments(row["audit_capture"], typed_inventory_available=True)
    assert result["checked"] == 0
    assert result["unknown"] >= 1


def test_all_216_return_physical_faces_are_actual_consumed_lookup_subjects():
    seen = 0
    for black, one, two in product((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5)):
        roll = OffensiveRoll(black, one, two)
        gain = roll.total % 11 - 4
        row, inventory = punt_subject(choice="kick:return", return_gain=gain, return_roll=roll)
        result = audit_receipt(row, lookup_inventory=inventory)
        assert result["punt_commitment_counts"]["return_checked"] == 1
        assert row["engine_log"][-1]["state_after"]["yards_to_goal"] == 75 - gain
        seen += 1
    assert seen == 216


def test_eligible_numeric_return_cannot_hide_an_extra_recovery_draw():
    row, _ = punt_subject(choice="kick:return", return_gain=0, return_kind="fumble")
    capture = row["audit_capture"]
    command = capture["typed_capture"]["commands"][-1]
    assert command["draw_range"][1] - command["draw_range"][0] == 2
    selected = [
        event
        for event in capture["lookup_rows"]["events"]
        if event["command_number"] == command["number"]
    ][0]
    selected["facts"].update(kind="yards", yards=3)
    from tools.game_audit_punt import audit_punt_commitments

    with pytest.raises(ValueError, match="draw/row exposure"):
        audit_punt_commitments(capture, typed_inventory_available=True)


@pytest.mark.parametrize("fault", ["owner", "column", "no-change-fixed"])
def test_return_role_and_fixed_fact_domains_are_not_inferred_from_claimed_report(fault):
    row, _ = punt_subject(choice="kick:return")
    capture = row["audit_capture"]
    selected = capture["lookup_rows"]["events"][-1]
    if fault == "owner":
        selected["address"]["team_id"] = "2002/home"
    elif fault == "column":
        selected["address"]["column"] = "kickoff_return"
    else:
        selected["facts"].update(kind="no_change", yards=3)
    from tools.game_audit_punt import PuntEvidenceError, audit_punt_commitments

    with pytest.raises(PuntEvidenceError):
        audit_punt_commitments(capture, typed_inventory_available=True)


@pytest.mark.parametrize("quarter,remaining", [(1, 600), (1, 5), (2, 5), (3, 5)])
def test_return_local_clock_and_unsupported_period_are_distinct(quarter, remaining):
    row, inventory = punt_subject(choice="kick:return", clock=Clock(quarter, remaining, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    counts = result["punt_commitment_counts"]
    assert counts["return_report_checked"] == 1
    assert counts["clock_checked"] == int(remaining > 10)
    assert counts["clock_unknown"] == int(remaining <= 10)
    assert counts["return_checked"] == int(remaining > 10)


def test_checked_return_endpoint_never_reanchors_an_unknown_prior_chain():
    from copy import deepcopy

    from tools.game_audit_continuity import audit_ordinary_continuity

    row, inventory = punt_subject(choice="kick:return")
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["ordinary_continuity_counts"]["qualified_punt_endpoints"] == 2
    punt = deepcopy(result["punt_commitment_counts"])
    punt["dispositions"][0].update(
        core_checked=False, status="UNVERIFIED", reason="unsupported_prior"
    )
    continuity = audit_ordinary_continuity(
        row["audit_capture"],
        ordinary=result["ordinary_commitment_counts"],
        clock=result["standard_clock_counts"],
        typed_inventory_available=True,
        punt=punt,
    )
    assert continuity["qualified_punt_endpoints"] == 0
    assert continuity["unknown_endpoints"] == 2


@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
@pytest.mark.parametrize(
    "key,value", [("overtime", False), ("armed_timeout", False), ("bounds_declaration", "")]
)
def test_nonperiod_punt_local_clock_requires_strict_normal_after_context(choice, key, value):
    row, inventory = punt_subject(choice=choice, clock=Clock(1, 600, (1, 2)))
    row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"][key] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)
