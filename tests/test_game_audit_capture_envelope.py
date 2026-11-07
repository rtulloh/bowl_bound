"""Pure JSON capture links; coherent observations do not prove completeness."""

from copy import deepcopy

import pytest

from tests.test_game_audit_priority import priority_receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


def envelope_receipt():
    row = priority_receipt()
    capture = row["audit_capture"]
    event = capture["priority"]["events"][0]
    for key in ("offense", "defense"):
        event[key]["chart_color"] = "white"
        event["result"][key]["chart_color"] = "white"
    caller = dict(module="synthetic.subject", function="snap")
    event["caller"] = caller
    before = dict(
        view={},
        teams={
            side: dict(id=f"2007/{side}", fingerprint=letter * 64)
            for side, letter in (("home", "a"), ("away", "b"))
        },
        configuration=dict(mode="synthetic"),
        reports=0,
        journal_length=0,
        tape=dict(
            roll_count=0,
            position=0,
            replaying=False,
            future=dict(kind="synthetic", status="UNVERIFIED"),
        ),
    )
    after = deepcopy(before)
    after.update(reports=1, journal_length=1)
    after["tape"].update(roll_count=2, position=0)
    command = dict(
        number=1,
        game_number=1,
        operation="snap",
        arguments=["1", "A"],
        exception_type=None,
        before=before,
        after=after,
        draw_range=[0, 2],
        draw_request_range=[0, 2],
        priority_range=[0, 1],
        priority_attempt_range=[0, 1],
        report_range=[0, 1],
        journal_range=[0, 1],
        returned_report=deepcopy(row["engine_log"][0]),
        report_revisions=[deepcopy(row["engine_log"][0])],
    )
    capture["typed_capture"] = dict(
        version="1",
        usable=True,
        errors=[],
        commands=[command],
        draws=[
            dict(
                number=1,
                kind="offensive",
                faces=dict(black=2, white_one=0, white_two=1),
                total=21,
                direct_sum=3,
            ),
            dict(number=2, kind="defensive", faces=dict(red=2, green=1), total=3),
        ],
        draw_requests=[
            dict(
                number=1,
                command_number=1,
                completed=True,
                expected_type="OffensiveRoll",
                draw_number=1,
            ),
            dict(
                number=2,
                command_number=1,
                completed=True,
                expected_type="DefensiveRoll",
                draw_number=2,
            ),
        ],
        priority_attempts=[
            dict(
                number=1,
                command_number=1,
                completed=True,
                event_number=1,
                offense=deepcopy(event["offense"]),
                defense=deepcopy(event["defense"]),
                caller=deepcopy(caller),
            )
        ],
        foreign_tape_requests=[],
        unprofiled_commands=[],
        replay_commands_skipped=0,
        targets=[
            dict(
                module=module,
                name=name,
                path="synthetic.py",
                line=1,
                source_sha256="c" * 64,
                process_local_code_sha256="d" * 64,
                code_digest_scope="diagnostic only",
                module_file="synthetic.py",
                module_spec_origin="synthetic.py",
            )
            for module, name in (
                ("bowl_bound.resolution", "resolve_cells"),
                ("bowl_bound.save_game", "_Tape._next"),
            )
        ],
        aliases=[dict(module="bowl_bound.resolution", name="resolve_cells")],
        scope="Synthetic internal links only; external completeness unknown",
    )
    return row


@pytest.mark.parametrize(
    "mutation",
    [
        "draw_range_gap",
        "draw_range_overflow",
        "uncovered_draw",
        "request_range_gap",
        "request_number_bool",
        "request_number_gap",
        "request_command",
        "request_completed_bool",
        "request_ref_duplicate",
        "request_ref_absent",
        "request_kind",
        "failed_request_ref",
        "draw_number_bool",
        "draw_face",
        "draw_total",
        "draw_sum",
        "draw_extra",
        "priority_uncovered",
        "attempt_number",
        "attempt_command",
        "attempt_ref_absent",
        "attempt_operand",
        "attempt_caller",
        "failed_attempt_ref",
        "completed_attempt_no_event",
        "report_boundary",
        "journal_boundary",
        "boundary_team",
        "boundary_fingerprint",
        "boundary_configuration",
        "tape_boolean",
        "tape_negative",
        "game_sequence",
    ],
)
def test_internal_link_corruption_cannot_hide_behind_matching_final_totals(mutation):
    row = envelope_receipt()
    cap = row["audit_capture"]["typed_capture"]
    command, request, attempt = (
        cap["commands"][0],
        cap["draw_requests"][0],
        cap["priority_attempts"][0],
    )
    if mutation == "draw_range_gap":
        command["draw_range"] = [1, 2]
    elif mutation == "draw_range_overflow":
        command["draw_range"] = [0, 3]
    elif mutation == "uncovered_draw":
        command["draw_range"] = [0, 1]
    elif mutation == "request_range_gap":
        command["draw_request_range"] = [1, 2]
    elif mutation == "request_number_bool":
        request["number"] = True
    elif mutation == "request_number_gap":
        request["number"] = 3
    elif mutation == "request_command":
        request["command_number"] = 99
    elif mutation == "request_completed_bool":
        request["completed"] = 1
    elif mutation == "request_ref_duplicate":
        request["draw_number"] = 2
    elif mutation == "request_ref_absent":
        request["draw_number"] = 99
    elif mutation == "request_kind":
        request["expected_type"] = "DefensiveRoll"
    elif mutation == "failed_request_ref":
        request["completed"] = False
    elif mutation == "draw_number_bool":
        cap["draws"][0]["number"] = True
    elif mutation == "draw_face":
        cap["draws"][0]["faces"]["black"] = 9
    elif mutation == "draw_total":
        cap["draws"][0]["total"] = 22
    elif mutation == "draw_sum":
        cap["draws"][0]["direct_sum"] = 2
    elif mutation == "draw_extra":
        cap["draws"][0]["extra"] = "unreviewed"
    elif mutation == "priority_uncovered":
        command["priority_range"] = [0, 0]
    elif mutation == "attempt_number":
        attempt["number"] = 2
    elif mutation == "attempt_command":
        attempt["command_number"] = 2
    elif mutation == "attempt_ref_absent":
        attempt["event_number"] = 2
    elif mutation == "attempt_operand":
        attempt["offense"]["yards"] = 8
    elif mutation == "attempt_caller":
        attempt["caller"]["function"] = "different"
    elif mutation == "failed_attempt_ref":
        attempt["completed"] = False
    elif mutation == "completed_attempt_no_event":
        attempt.pop("event_number")
    elif mutation == "report_boundary":
        command["report_range"] = [1, 2]
    elif mutation == "journal_boundary":
        command["journal_range"] = [0, 2]
    elif mutation == "boundary_team":
        command["after"]["teams"]["home"]["id"] = "other"
    elif mutation == "boundary_fingerprint":
        command["after"]["teams"]["home"]["fingerprint"] = "e" * 64
    elif mutation == "boundary_configuration":
        command["after"]["configuration"]["mode"] = "other"
    elif mutation == "tape_boolean":
        command["after"]["tape"]["position"] = True
    elif mutation == "tape_negative":
        command["before"]["tape"]["position"] = -1
    elif mutation == "game_sequence":
        command["game_number"] = 2
    with pytest.raises(ReceiptAuditError, match="capture"):
        audit_receipt(row)


def test_coherent_internal_links_do_not_qualify_external_capture_or_terminal_truth():
    row = envelope_receipt()
    original = deepcopy(row)
    result = audit_receipt(row)
    assert result["components"]["capture_internal_linkage"] == "GO"
    assert result["capture_linkage"]["commands_checked"] == 1
    assert result["capture_linkage"]["draws_checked"] == 2
    assert result["capture_linkage"]["priority_attempts_checked"] == 1
    assert result["capture_linkage"]["report_revision_address_linkage"] == "UNVERIFIED"
    assert result["capture_linkage"]["external_command_completeness"] == "UNVERIFIED"
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False
    assert row == original


def add_second_command(row, *, game_number=1):
    cap = row["audit_capture"]["typed_capture"]
    command = deepcopy(cap["commands"][0])
    command.update(
        number=2,
        game_number=game_number,
        operation="synthetic-invalid",
        exception_type="ValueError",
        before=deepcopy(command["after"]),
        draw_range=[2, 2],
        draw_request_range=[2, 2],
        priority_range=[1, 1],
        priority_attempt_range=[1, 1],
        report_range=[1, 1],
        journal_range=[1, 1],
        returned_report=None,
        report_revisions=[],
    )
    cap["commands"].append(command)
    return command


@pytest.mark.parametrize("field", ["teams", "configuration", "tape", "reports", "journal_length"])
def test_same_game_boundary_gap_cannot_hide_in_locally_consistent_commands(field):
    row = envelope_receipt()
    command = add_second_command(row)
    if field == "teams":
        command["before"][field]["home"]["id"] = "changed"
    elif field == "configuration":
        command["before"][field]["mode"] = "changed"
    elif field == "tape":
        command["before"][field]["future"] = dict(kind="other")
    else:
        command["before"][field] += 1
    command["after"] = deepcopy(command["before"])
    command["report_range"] = [command["before"]["reports"]] * 2
    command["journal_range"] = [command["before"]["journal_length"]] * 2
    with pytest.raises(ReceiptAuditError, match="capture"):
        audit_receipt(row)


def test_multiple_commands_failures_and_restored_game_objects_are_counted_separately():
    row = envelope_receipt()
    add_second_command(row)
    third = add_second_command(row, game_number=2)
    third["number"] = 3
    result = audit_receipt(row)["capture_linkage"]
    assert result["commands_checked"] == 3
    assert result["game_objects_observed"] == 2
    assert result["failed_commands_observed"] == 2
    assert result["initial_reports_not_observed"] == 1
    assert result["initial_journal_entries_not_observed"] == 1
    assert result["external_game_identity"] == "UNVERIFIED"


@pytest.mark.parametrize(
    "mutation",
    [
        "game_gap",
        "command_gap",
        "global_range_gap",
        "request_missing",
        "request_extra",
        "attempt_missing",
        "attempt_extra",
        "caller_boolean",
        "team_bool",
        "team_missing",
        "tape_missing",
        "tape_extra",
        "position_drift",
        "roll_count_drift",
        "revisions_missing_append",
        "ref_bool",
        "exception_empty",
    ],
)
def test_strict_nested_fields_global_order_and_tape_links(mutation):
    row = envelope_receipt()
    cap = row["audit_capture"]["typed_capture"]
    command = add_second_command(row)
    first = cap["commands"][0]
    if mutation == "game_gap":
        command["game_number"] = 3
    elif mutation == "command_gap":
        command["number"] = 3
    elif mutation == "global_range_gap":
        command["draw_request_range"] = [1, 2]
    elif mutation == "request_missing":
        del cap["draw_requests"][0]["expected_type"]
    elif mutation == "request_extra":
        cap["draw_requests"][0]["unknown"] = False
    elif mutation == "attempt_missing":
        del cap["priority_attempts"][0]["caller"]
    elif mutation == "attempt_extra":
        cap["priority_attempts"][0]["unknown"] = 0
    elif mutation == "caller_boolean":
        cap["priority_attempts"][0]["caller"] = True
    elif mutation == "team_bool":
        first["before"]["teams"]["home"] = True
    elif mutation == "team_missing":
        del first["before"]["teams"]["home"]["fingerprint"]
    elif mutation == "tape_missing":
        del first["before"]["tape"]["future"]
    elif mutation == "tape_extra":
        first["before"]["tape"]["extra"] = 1
    elif mutation == "position_drift":
        first["after"]["tape"]["position"] = 1
    elif mutation == "roll_count_drift":
        first["after"]["tape"]["roll_count"] = 3
    elif mutation == "revisions_missing_append":
        first["report_revisions"] = []
    elif mutation == "ref_bool":
        cap["priority_attempts"][0]["event_number"] = True
    elif mutation == "exception_empty":
        command["exception_type"] = ""
    with pytest.raises(ReceiptAuditError, match="capture"):
        audit_receipt(row)


def test_zero_observations_are_not_an_exercised_capture_linkage_check():
    row = envelope_receipt()
    cap = row["audit_capture"]
    del cap["priority"]
    for field in ("commands", "draws", "draw_requests", "priority_attempts"):
        cap["typed_capture"][field] = []
    result = audit_receipt(row)
    assert result["components"]["capture_internal_linkage"] == "NOTRUN"
    assert result["capture_linkage"]["commands_checked"] == 0
    assert result["capture_linkage"]["external_command_completeness"] == "UNVERIFIED"


def test_failed_priority_and_draw_requests_retain_unknown_results_and_partial_consumption():
    row = envelope_receipt()
    cap = row["audit_capture"]["typed_capture"]
    command = add_second_command(row)
    command.update(draw_request_range=[2, 4], priority_attempt_range=[1, 3])
    for number in (3, 4):
        cap["draw_requests"].append(
            dict(number=number, command_number=2, completed=False, expected_type="OffensiveRoll")
        )
    for number in (2, 3):
        attempt = deepcopy(cap["priority_attempts"][0])
        attempt.update(number=number, command_number=2, completed=False)
        del attempt["event_number"]
        cap["priority_attempts"].append(attempt)
    result = audit_receipt(row)["capture_linkage"]
    assert result["incomplete_draw_requests"] == 2
    assert result["incomplete_priority_attempts"] == 2
    assert result["failed_commands_observed"] == 1
    assert result["unreturned_priority_results"] == "UNVERIFIED"


@pytest.mark.parametrize("field", ["errors", "unprofiled_commands", "foreign_tape_requests"])
def test_producer_failure_cannot_become_green_via_coherent_subset(field):
    row = envelope_receipt()
    row["audit_capture"]["typed_capture"][field] = [dict(reason="synthetic")]
    with pytest.raises(ReceiptAuditError, match="capture"):
        audit_receipt(row)


def test_optional_defense_markers_are_observed_facts_not_rule_authority():
    row = envelope_receipt()
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    for boundary in ("before", "after"):
        command[boundary]["teams"]["home"]["defense_chart_markers"] = ["W", "FBO"]
    result = audit_receipt(row)
    assert result["components"]["capture_internal_linkage"] == "GO"
    assert result["capture_linkage"]["external_game_identity"] == "UNVERIFIED"


def test_nested_priority_completion_order_need_not_equal_attempt_call_order():
    row = envelope_receipt()
    cap = row["audit_capture"]
    event = deepcopy(cap["priority"]["events"][0])
    event["number"] = 2
    cap["priority"]["events"].append(event)
    envelope = cap["typed_capture"]
    second = deepcopy(envelope["priority_attempts"][0])
    second["number"] = 2
    envelope["priority_attempts"].append(second)
    envelope["priority_attempts"][0]["event_number"] = 2
    envelope["commands"][0].update(priority_range=[0, 2], priority_attempt_range=[0, 2])
    assert audit_receipt(row)["capture_linkage"]["priority_events_checked"] == 2
    envelope["priority_attempts"][1]["event_number"] = 2
    with pytest.raises(ReceiptAuditError, match="capture"):
        audit_receipt(row)


def test_failed_command_can_have_partial_draw_and_journal_consumption_without_invented_results():
    row = envelope_receipt()
    command = add_second_command(row)
    cap = row["audit_capture"]["typed_capture"]
    draw = deepcopy(cap["draws"][0])
    draw["number"] = 3
    cap["draws"].append(draw)
    cap["draw_requests"].extend(
        [
            dict(
                number=3,
                command_number=2,
                completed=True,
                expected_type="OffensiveRoll",
                draw_number=3,
            ),
            dict(number=4, command_number=2, completed=False, expected_type="DefensiveRoll"),
            dict(number=5, command_number=2, completed=False, expected_type="DefensiveRoll"),
        ]
    )
    command.update(draw_range=[2, 3], draw_request_range=[2, 5], journal_range=[1, 2])
    command["after"]["tape"]["roll_count"] = 3
    command["after"]["journal_length"] = 2
    result = audit_receipt(row)["capture_linkage"]
    assert result["draws_checked"] == 3
    assert result["incomplete_draw_requests"] == 2
    assert result["failed_commands_observed"] == 1
    assert result["terminal_truth"] == "UNVERIFIED"


@pytest.mark.parametrize(
    "mutation",
    [
        "envelope_extra",
        "target_extra",
        "target_duplicate",
        "alias_extra",
        "alias_duplicate",
        "priority_bad_type",
        "priority_events_bad_type",
        "marker_bool",
        "marker_duplicate",
        "marker_unknown",
        "future_missing_kind",
    ],
)
def test_v1_nested_metadata_inventory_is_strict(mutation):
    row = envelope_receipt()
    cap = row["audit_capture"]
    env = cap["typed_capture"]
    if mutation == "envelope_extra":
        env["other"] = None
    elif mutation == "target_extra":
        env["targets"][0]["other"] = 0
    elif mutation == "target_duplicate":
        env["targets"].append(deepcopy(env["targets"][0]))
    elif mutation == "alias_extra":
        env["aliases"][0]["other"] = 0
    elif mutation == "alias_duplicate":
        env["aliases"].append(deepcopy(env["aliases"][0]))
    elif mutation == "priority_bad_type":
        cap["priority"] = True
    elif mutation == "priority_events_bad_type":
        cap["priority"]["events"] = True
    elif mutation.startswith("marker_"):
        env["commands"][0]["before"]["teams"]["home"]["defense_chart_markers"] = {
            "marker_bool": True,
            "marker_duplicate": ["W", "W"],
            "marker_unknown": ["anything"],
        }[mutation]
    else:
        del env["commands"][0]["before"]["tape"]["future"]["kind"]
    with pytest.raises(ReceiptAuditError, match="capture"):
        audit_receipt(row)
