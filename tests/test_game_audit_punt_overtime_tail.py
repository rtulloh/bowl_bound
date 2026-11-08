"""A fixed punt can precede unqualified recorded overtime toss draws."""

from copy import deepcopy

import pytest

from bowl_bound.dice import OffensiveRoll
from bowl_bound.timing import Clock
from tests.test_game_audit_punt_commitment import alter_final, punt_subject
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_punt import PuntEvidenceError, audit_punt_commitments


def overtime_subject(*, choice="kick:fair_catch", side="home", repeated=False):
    extra = [OffensiveRoll(1, 0, 0)]
    return_roll = None
    if repeated:
        return_roll = OffensiveRoll(2, 0, 0)
        extra = [OffensiveRoll(2, 0, 0), OffensiveRoll(3, 0, 0), OffensiveRoll(1, 0, 0)]
    return punt_subject(
        choice=choice,
        side=side,
        clock=Clock(4, 10, (1, 2)),
        return_roll=return_roll,
        extra_rolls=extra,
    )


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
@pytest.mark.parametrize("repeated", [False, True])
def test_actual_punt_then_recorded_ot_toss_is_partial_not_refused(side, choice, repeated):
    row, inventory = overtime_subject(side=side, choice=choice, repeated=repeated)
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    assert command["before"]["view"]["clock"]["remaining"] == 10
    assert command["after"]["view"]["phase"] == "overtime_choice"
    assert len(command["after"]["view"]["overtime_toss_rolls"]) == (4 if repeated else 2)
    result = audit_receipt(row, lookup_inventory=inventory)
    counts = result["punt_commitment_counts"]
    assert counts["report_checked"] == 1
    assert counts["checked"] == counts["clock_checked"] == 0
    assert counts["clock_unknown"] == 1
    assert counts["dispositions"][-1]["status"] == "UNVERIFIED"
    assert counts["dispositions"][-1]["reason"] == "live_continuation_authority"
    assert result["components"]["punt_fair_catch_commitment"] == "UNVERIFIED"
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
@pytest.mark.parametrize("fault", ["goal", "credit", "score", "timing", "box-home", "box-away"])
def test_ot_tail_never_hides_a_corrupt_punt_report(choice, fault):
    row, inventory = overtime_subject(choice=choice)

    def corrupt(report, command):
        if fault == "goal":
            report["state_after"]["yards_to_goal"] += 1
        elif fault == "credit":
            report["statistics"]["yards"] = 1
        elif fault == "timing":
            report["timing"]["scoring"] = True
        elif fault == "score":
            command["after"]["view"]["score"]["home"] = 1
        else:
            command["after"]["view"]["statistics"][fault.removeprefix("box-")]["rushing_yards"] = 1

    alter_final(row, corrupt)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
@pytest.mark.parametrize(
    "fault", ["nonboundary", "quarter", "untied", "phase", "toss-faces", "prior-toss"]
)
def test_phase_or_inconsistent_boundary_never_waives_extra_draws(choice, fault):
    row, _ = overtime_subject(choice=choice)
    capture = row["audit_capture"]
    source, command = capture["typed_capture"]["commands"][-2:]
    before, after = command["before"]["view"], command["after"]["view"]
    if fault in {"nonboundary", "quarter", "untied", "prior-toss"}:
        for view in (source["before"]["view"], source["after"]["view"], before):
            if fault == "nonboundary":
                view["clock"]["remaining"] = 11
            elif fault == "quarter":
                view["clock"]["quarter"] = 3
            elif fault == "untied":
                view["score"]["home"] = 1
            else:
                view["overtime_toss_rolls"] = deepcopy(after["overtime_toss_rolls"])
    elif fault == "phase":
        after["phase"] = "scrimmage"
    else:
        after["overtime_toss_rolls"][0]["black"] = 1
    # Shared kick exposure validation raises its own ValueError subclass.
    with pytest.raises(ValueError, match="draw/row exposure"):
        audit_punt_commitments(capture, typed_inventory_available=True)


@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
def test_ot_tail_still_requires_fresh_charged_report_identity(choice):
    row, _ = overtime_subject(choice=choice)
    capture = row["audit_capture"]
    source, command = capture["typed_capture"]["commands"][-2:]
    number = command["returned_report"]["number"]
    for view in (source["before"]["view"], source["after"]["view"], command["before"]["view"]):
        view["timing_log"][0]["play_number"] = number
    with pytest.raises(PuntEvidenceError, match="fresh charged identity"):
        audit_punt_commitments(capture, typed_inventory_available=True)


@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
def test_ot_tail_cannot_hide_an_extra_chart_row(choice):
    row, _ = overtime_subject(choice=choice)
    capture = row["audit_capture"]
    command = capture["typed_capture"]["commands"][-1]
    extra = deepcopy(capture["lookup_rows"]["events"][-1])
    extra.update(command_number=command["number"], game_number=command["game_number"])
    capture["lookup_rows"]["events"].append(extra)
    with pytest.raises(ValueError):
        audit_punt_commitments(capture, typed_inventory_available=True)


def test_numeric_return_row_must_precede_the_recorded_toss_draws():
    row, _ = overtime_subject(choice="kick:return")
    capture = row["audit_capture"]
    command = capture["typed_capture"]["commands"][-1]
    selected = capture["lookup_rows"]["events"][-1]
    selected["captured_draw_frontier"] = command["draw_range"][1]
    with pytest.raises(ValueError, match="role selection frontier"):
        audit_punt_commitments(capture, typed_inventory_available=True)
