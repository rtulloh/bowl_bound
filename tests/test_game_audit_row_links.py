"""Synthetic supplied-row corruption controls; engine is only a subject."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll
from bowl_bound.models import ChartColor, NormalizedCell, ResultKind
from tests.test_game_audit_lookup import inventory
from tests.test_game_audit_typed_capture import game
from tests.test_game_receipt_audit import receipt
from tests.test_models import provenance
from tests.test_save_game import charts
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_capture import capture_receipts


def frozen_inventory():
    result = dict(version="1", teams=[], cells=[])
    for side in ("home", "away"):
        part = deepcopy(inventory())
        for team in part["teams"]:
            team.update(team_id=f"2002/{side}", season=2002)
        for cell in part["cells"]:
            cell["address"].update(team_id=f"2002/{side}", season=2002)
            if cell["address"]["table"] not in {"defense", "pat"}:
                cell["facts"]["yards"] = 3
        result["teams"].extend(part["teams"])
        result["cells"].extend(part["cells"])
    return result


def subject_teams():
    ordinary = NormalizedCell(ResultKind.YARDS, provenance(), yards=3, chart_color=ChartColor.WHITE)
    defense = replace(ordinary, yards=-1)
    return tuple(
        replace(
            team,
            offense=tuple(replace(row, cell=ordinary) for row in team.offense),
            defense=tuple(replace(row, cell=defense) for row in team.defense),
            supplemental=tuple(replace(row, cell=ordinary) for row in team.supplemental),
            special_teams=tuple(replace(row, cell=ordinary) for row in team.special_teams),
            pat_outcomes=tuple(replace(row, good=True) for row in team.pat_outcomes),
        )
        for team in charts()
    )


def observed():
    subject = game(subject_teams(), [OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)])
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap("1", "F")
    row = receipt()
    row["audit_capture"] = capture.payload()
    return row


def test_actual_rows_link_to_supplied_commands_draws_and_pinned_typed_inventory():
    row = observed()
    block = row["audit_capture"]["lookup_rows"]
    assert block["version"] == "2"
    assert [event["captured_draw_frontier"] for event in block["events"]] == [2, 2]
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["captured_row_linkage"] == "GO"
    assert result["components"]["typed_lookup_agreement"] == "GO"
    assert result["coverage"]["captured_row_linkage"] == dict(checked=2, excluded=0, unknown=0)
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "number",
        "boolean-number",
        "command",
        "game",
        "site",
        "table",
        "team",
        "facts",
        "roll",
        "faces",
        "future-draw",
        "tape-index",
        "prewindow",
        "missing-initial",
        "duplicate-initial",
        "initial-count",
        "false-count",
    ],
)
def test_corrupt_actual_supplied_row_links_refuse(mutation):
    row = observed()
    block = row["audit_capture"]["lookup_rows"]
    event = block["events"][0]
    if mutation == "number":
        event["number"] = 2
    elif mutation == "boolean-number":
        event["number"] = True
    elif mutation == "command":
        event["command_number"] = 999
    elif mutation == "game":
        event["game_number"] = 2
    elif mutation == "site":
        event["site_id"] = "unknown"
    elif mutation == "table":
        event["address"]["table"] = "defense"
    elif mutation == "team":
        event["address"]["team_id"] = "2002/foreign"
    elif mutation == "facts":
        event["facts"]["yards"] = 99
    elif mutation == "roll":
        event["roll"]["total"] = 22
    elif mutation == "faces":
        event["roll"]["faces"]["black"] = True
    elif mutation == "future-draw":
        event["draw_binding"]["captured_draw_numbers"] = [999]
    elif mutation == "tape-index":
        event["draw_binding"]["tape_indices"] = [1]
    elif mutation == "prewindow":
        event["draw_binding"].update(status="PREWINDOW", captured_draw_numbers=[])
    elif mutation == "missing-initial":
        block["initial_tapes"].clear()
    elif mutation == "duplicate-initial":
        block["initial_tapes"].append(deepcopy(block["initial_tapes"][0]))
    elif mutation == "initial-count":
        block["initial_tapes"][0]["recorded_rolls"].append(deepcopy(event["roll"]))
    elif mutation == "false-count":
        block["exercised_sites"][event["site_id"]] = 0
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen_inventory())


def option_observed():
    option = NormalizedCell(ResultKind.SPRINT_OUT_PASS, provenance(), chart_color=ChartColor.WHITE)
    teams = tuple(
        replace(
            team,
            offense=tuple(
                replace(record, cell=option) if record.play.value == 5 else record
                for record in team.offense
            ),
        )
        for team in subject_teams()
    )
    subject = game(teams, [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)])
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap("5", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    frozen = frozen_inventory()
    for record in frozen["cells"]:
        if record["address"]["table"] == "offense" and record["address"]["play"] == 5:
            record["facts"].update(kind="SOP", yards=None)
    return row, frozen


@pytest.mark.parametrize("unobserved", [False, True])
def test_existing_later_same_face_option_draw_cannot_support_earlier_selection(unobserved):
    row, frozen = option_observed()
    assert audit_receipt(row, lookup_inventory=frozen)["components"]["captured_row_linkage"] == "GO"
    event = row["audit_capture"]["lookup_rows"]["events"][0]
    assert event["captured_draw_frontier"] == 2
    event["draw_binding"].update(tape_indices=[2], captured_draw_numbers=[3])
    if unobserved:
        event["draw_binding"].update(status="UNOBSERVED", captured_draw_numbers=[])
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_no_inventory_cannot_mint_typed_data_agreement():
    result = audit_receipt(observed())
    assert result["components"]["captured_row_linkage"] == "GO"
    assert result["components"]["typed_lookup_agreement"] == "UNVERIFIED"
    assert result["coverage"]["typed_lookup_agreement"] == dict(checked=0, excluded=0, unknown=2)


def test_legacy_raw_v1_has_no_independent_within_command_frontier():
    row = observed()
    block = row["audit_capture"]["lookup_rows"]
    block["version"] = "1"
    for event in block["events"]:
        del event["captured_draw_frontier"]
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["captured_row_linkage"] == "UNVERIFIED"
    assert result["components"]["typed_lookup_agreement"] == "GO"
    assert result["coverage"]["captured_row_linkage"] == dict(checked=0, excluded=0, unknown=2)


@pytest.mark.parametrize("kind", ["ambiguous-chart", "unobserved-draw"])
def test_actual_explicit_unknowns_cannot_become_complete_pass(monkeypatch, kind):
    from tools.game_audit_lookup_capture import LookupRowCapture

    teams = subject_teams()
    if kind == "ambiguous-chart":
        teams = (teams[0], teams[0])
    else:
        monkeypatch.setattr(LookupRowCapture, "observe_draw", lambda *args: None)
    subject = game(teams, [OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)])
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap("1", "F")
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["captured_row_linkage"] == "UNVERIFIED"
    assert result["components"]["typed_lookup_agreement"] == "UNVERIFIED"
    assert result["coverage"]["captured_row_linkage"] == dict(checked=0, excluded=0, unknown=2)


def test_zero_successful_rows_is_notrun_not_vacuous_success():
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        with pytest.raises(ValueError):
            game(subject_teams()).snap("bad", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["captured_row_linkage"] == "NOTRUN"
    assert result["coverage"]["captured_row_linkage"] == dict(checked=0, excluded=0, unknown=0)
    assert result["capture_linkage"]["failed_commands_observed"] == 1


@pytest.mark.parametrize(
    "path,value",
    [
        (("version",), True),
        (("usable",), False),
        (("qualification",), "GO"),
        (("errors",), [{}]),
        (("scope",), None),
        (("events", 0, "captured_draw_frontier"), True),
        (("events", 0, "captured_draw_frontier"), -1),
        (("events", 0, "captured_draw_frontier"), 999),
        (("events", 0, "draw_binding", "tape_indices"), [True]),
        (("events", 0, "draw_binding", "tape_indices"), [0, 0]),
        (("events", 0, "draw_binding", "captured_draw_numbers"), [True]),
        (("events", 0, "record_binding"), False),
        (("events", 0, "chart_binding"), "foreign"),
        (("events", 0, "facts", "out_of_bounds"), 0),
        (("events", 0, "facts", "yards"), 3.0),
        (("events", 0, "roll", "total"), float("nan")),
        (("sites", 0, "line"), True),
        (("sites", 0, "source_sha256"), "0" * 64),
        (("sources", 0, "source_sha256"), "invalid"),
        (("aliases", 0, "function_name"), "foreign"),
        (("initial_tapes", 0, "position"), True),
        (("initial_tapes", 0, "replaying"), True),
    ],
)
def test_nested_malformed_fields_refuse(path, value):
    row = observed()
    at = row["audit_capture"]["lookup_rows"]
    for key in path[:-1]:
        at = at[key]
    at[path[-1]] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen_inventory())


def test_simultaneous_legacy_and_new_lookups_refuse():
    row = observed()
    row["audit_capture"]["lookup"] = dict(
        version="1",
        draws=deepcopy(row["audit_capture"]["typed_capture"]["draws"]),
        events=[
            dict(
                number=event["number"],
                draw_number=event["draw_binding"]["captured_draw_numbers"][0],
                address=deepcopy(event["address"]),
                facts=deepcopy(event["facts"]),
            )
            for event in row["audit_capture"]["lookup_rows"]["events"]
        ],
    )
    legacy = deepcopy(row)
    del legacy["audit_capture"]["lookup_rows"]
    assert (
        audit_receipt(legacy, lookup_inventory=frozen_inventory())["components"][
            "typed_lookup_agreement"
        ]
        == "GO"
    )
    with pytest.raises(ReceiptAuditError, match="simultaneous"):
        audit_receipt(row, lookup_inventory=frozen_inventory())


def test_actual_restored_razzle_prefix_is_not_fresh_draw_exposure():
    from bowl_bound.save_game import dumps_game, loads_game

    teams = subject_teams()
    subject = game(teams, [OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0), DefensiveRoll(1, 0)])
    subject.snap("RZDZ", "A")
    restored = loads_game(
        dumps_game(subject),
        lambda key: dict(zip(("2002/home", "2002/away"), teams, strict=True))[key],
    )
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        restored.decide("razzle:1:10")
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["captured_row_linkage"] == "GO"
    assert result["captured_row_counts"]["prewindow_rows"] == 1
    assert result["captured_row_counts"]["physical_draws"] == 1
    assert result["captured_row_counts"]["typed_rows_checked"] == 2
    assert result["capture_linkage"]["captured_history_matches_final_row"] == "UNVERIFIED"


def test_multiple_actual_objects_cannot_borrow_same_face_draws():
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        for _ in range(2):
            game(subject_teams(), [OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)]).snap("1", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    assert (
        audit_receipt(row, lookup_inventory=frozen_inventory())["captured_row_counts"][
            "rows_linked"
        ]
        == 4
    )
    row["audit_capture"]["lookup_rows"]["events"][0]["draw_binding"]["captured_draw_numbers"] = [3]
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen_inventory())


def test_failed_partial_draw_attempt_is_retained_alongside_bound_rows():
    from bowl_bound.dice import DiceSequenceError

    with capture_receipts(typed=True, lookup_rows=True) as capture:
        with pytest.raises(DiceSequenceError):
            game(subject_teams(), [OffensiveRoll(1, 0, 0)]).snap("1", "A")
        game(subject_teams(), [OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)]).snap("1", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["capture_linkage"]["failed_commands_observed"] == 1
    assert result["capture_linkage"]["incomplete_draw_requests"] == 1
    assert result["captured_row_counts"]["physical_draws"] == 3
    assert result["captured_row_counts"]["rows_linked"] == 2


@pytest.mark.parametrize("wrong_good", [False, 1])
def test_actual_dedicated_pat_fact_is_compared_without_field_goal_guessing(wrong_good):
    from bowl_bound.dice import ScriptedDice
    from bowl_bound.save_game import SavedGame

    subject = SavedGame.new(
        *subject_teams(),
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        mode="drive",
        advanced_ii=False,
        start_yards_to_goal=1,
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap("1", "A")
        subject.decide("conversion:kick")
    row = receipt()
    row["audit_capture"] = capture.payload()
    assert (
        audit_receipt(row, lookup_inventory=frozen_inventory())["captured_row_counts"][
            "typed_rows_checked"
        ]
        == 3
    )
    row["audit_capture"]["lookup_rows"]["events"][-1]["facts"]["good"] = wrong_good
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen_inventory())


@pytest.mark.parametrize("boundary", ["before", "after"])
def test_replay_mode_command_boundaries_are_not_recording_draw_evidence(boundary):
    row = observed()
    row["audit_capture"]["typed_capture"]["commands"][0][boundary]["tape"]["replaying"] = True
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen_inventory())


def test_actual_in_window_load_skips_replay_then_links_only_recording_continuation():
    from bowl_bound.save_game import dumps_game, loads_game

    teams = subject_teams()
    subject = game(teams)
    subject.snap("1", "A")
    saved = dumps_game(subject)
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        restored = loads_game(
            saved, lambda key: dict(zip(("2002/home", "2002/away"), teams, strict=True))[key]
        )
        assert capture.replay_commands_skipped == 1
        assert capture.commands == []
        assert capture.draws == []
        restored.snap("2", "F")
    row = receipt()
    row["audit_capture"] = capture.payload()
    initial = row["audit_capture"]["lookup_rows"]["initial_tapes"][0]
    assert initial["replaying"] is False
    assert len(initial["recorded_rolls"]) == 2
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["captured_row_counts"]["rows_linked"] == 2
    assert result["captured_row_counts"]["physical_draws"] == 2
    assert result["captured_row_counts"]["prewindow_rows"] == 0
