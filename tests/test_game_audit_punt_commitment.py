"""Literal fixed-punt subjects; engine observations never supply expectations."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import ResultKind
from bowl_bound.save_game import SavedGame
from bowl_bound.timing import Clock
from tests.test_game_audit_ordinary_commitment import log_digest
from tests.test_game_audit_row_links import frozen_inventory, subject_teams
from tests.test_game_receipt_audit import receipt
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_capture import capture_receipts


def punt_subject(
    *,
    side="home",
    spot=65,
    flight=40,
    down=4,
    distance=10,
    clock=None,
    choice="kick:fair_catch",
    pending_only=False,
    roll=None,
    return_gain=3,
    return_kind="yards",
    return_roll=None,
):
    teams = tuple(
        replace(
            team,
            special_teams=tuple(
                replace(
                    record,
                    cell=replace(
                        record.cell,
                        kind=ResultKind(return_kind)
                        if record.column.value == "punt_return"
                        else record.cell.kind,
                        yards=(None if return_kind == "no_change" else return_gain)
                        if record.column.value == "punt_return"
                        else flight
                        if record.column.value == "punt"
                        else 65
                        if record.column.value == "kickoff"
                        else 3,
                    ),
                )
                for record in team.special_teams
            ),
        )
        for team in subject_teams()
    )
    rolls = [
        OffensiveRoll(2, 0, 1) if roll is None else roll,
        OffensiveRoll(3, 4, 5) if return_roll is None else return_roll,
        OffensiveRoll(2, 0, 0),
    ]
    if clock is not None:
        rolls = [OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)] + rolls
    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive" if clock is None else "regulation",
        clock=clock,
        advanced_ii=False,
        dice=ScriptedDice(rolls),
    )
    if clock is None:
        game._engine._field = FieldState(Possession(side), spot, down, distance)
    else:
        from tests.test_save_game import opening

        opening(game)
        game._engine._session._field = FieldState(Possession(side), spot, down, distance)
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        game.kick("punt")
        if not pending_only:
            game.decide(choice)
    row = receipt()
    row["audit_capture"] = capture.payload()
    commands = row["audit_capture"]["typed_capture"]["commands"]
    log = deepcopy(commands[0]["initial_log"])
    for command in commands:
        for change in command["report_changes"]:
            if change["before"] is None:
                log.append(deepcopy(change["after"]))
            else:
                log[change["index"]] = deepcopy(change["after"])
    row["engine_log"] = log
    final = commands[-1]["after"]["view"]
    row["final"].update(
        statistics=deepcopy(final["statistics"]),
        home_score=final["score"]["home"],
        away_score=final["score"]["away"],
        scoring=deepcopy(final["scoring"]),
    )
    inventory = frozen_inventory()
    for record in inventory["cells"]:
        if record["address"]["table"] == "special_teams":
            if record["address"]["column"] == "punt_return":
                record["facts"]["kind"] = return_kind
            record["facts"]["yards"] = (
                (None if return_kind == "no_change" else return_gain)
                if record["address"]["column"] == "punt_return"
                else flight
                if record["address"]["column"] == "punt"
                else 65
                if record["address"]["column"] == "kickoff"
                else 3
            )
    return row, inventory


def alter_final(row, change):
    commands = row["audit_capture"]["typed_capture"]["commands"]
    command = commands[-1]
    report = command["report_changes"][0]["after"]
    change(report, command)
    command["returned_report"] = deepcopy(report)
    command["report_revisions"] = [deepcopy(report)]
    log = deepcopy(commands[0]["initial_log"]) + [deepcopy(report)]
    command["after"]["log_sha256"] = log_digest(log)
    row["engine_log"] = log


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("spot,flight,goal", [(65, 40, 75), (99, 98, 99), (99, 0, 1)])
def test_literal_punt_faircatch_field_credit_and_mirrored_sides(side, spot, flight, goal):
    row, inventory = punt_subject(side=side, spot=spot, flight=flight)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["punt_fair_catch_commitment"] == "GO"
    assert result["punt_commitment_counts"]["checked"] == 1
    assert result["punt_commitment_counts"]["pending_checked"] == 1
    final = row["audit_capture"]["typed_capture"]["commands"][-1]["returned_report"]
    assert final["state_after"]["possession"] != side
    assert final["state_after"]["yards_to_goal"] == goal
    assert final["statistics"] == dict(kind="excluded", team=None, yards=0, touchdown=False)
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "goal",
        "owner",
        "down",
        "distance",
        "credit",
        "called",
        "resolved",
        "timing",
        "box-home",
        "box-away",
        "score",
        "outcome",
        "yards",
    ],
)
def test_faircatch_corruptions_ignored_by_previous_observer_refuse(fault):
    row, inventory = punt_subject()

    def mutate(report, command):
        if fault in {"goal", "owner", "down", "distance"}:
            key, value = {
                "goal": ("yards_to_goal", 74),
                "owner": ("possession", "home"),
                "down": ("down", 2),
                "distance": ("yards_to_go", 9),
            }[fault]
            report["state_after"][key] = value
            command["after"]["view"]["state"][key] = value
        elif fault == "credit":
            report["statistics"]["yards"] = 1
        elif fault in {"called", "resolved"}:
            report[fault + "_play"] = "Kickoff"
        elif fault == "timing":
            report["timing"]["first_down"] = True
        elif fault.startswith("box-"):
            command["after"]["view"]["statistics"][fault[4:]]["total_yards"] += 1
        elif fault == "score":
            command["after"]["view"]["score"]["home"] += 1
        elif fault == "outcome":
            report["outcome"] = "punt_return"
        else:
            report["yards"] = 0

    alter_final(row, mutate)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("fault", ["missing", "disabled", "boolean", "duplicate", "chooser"])
def test_initial_receiver_offer_must_be_exact_and_strict(fault):
    row, inventory = punt_subject()
    commands = row["audit_capture"]["typed_capture"]["commands"]
    for view in [commands[0]["after"]["view"], commands[1]["before"]["view"]]:
        pending = view["pending"]
        if fault == "missing":
            pending["choices"] = []
        elif fault == "disabled":
            pending["choices"][0]["enabled"] = False
        elif fault == "boolean":
            pending["choices"][0]["enabled"] = 1
        elif fault == "duplicate":
            pending["choices"][1] = deepcopy(pending["choices"][0])
        else:
            pending["chooser_side"] = "home"
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize(
    "fault", ["remaining", "seconds", "report-id", "prefix", "before-mirror", "pending-mirror"]
)
def test_local_faircatch_ten_second_charge_and_timeout_mirrors(fault):
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    commands = row["audit_capture"]["typed_capture"]["commands"]
    after = commands[-1]["after"]["view"]
    if fault == "remaining":
        after["clock"]["remaining"] += 1
    elif fault == "seconds":
        after["timing_log"][-1]["seconds"] += 1
    elif fault == "report-id":
        after["timing_log"][-1]["play_number"] += 1
    elif fault == "prefix":
        after["timing_log"][0]["seconds"] += 1
    elif fault == "before-mirror":
        commands[0]["before"]["view"]["home_timeouts"] = 3
    else:
        commands[0]["after"]["view"]["away_timeouts"] = 3
        commands[1]["before"]["view"]["away_timeouts"] = 3
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


def test_normal_regulation_faircatch_local_clock_and_pending_no_premature_credit():
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["punt_commitment_counts"]["clock_checked"] == 1
    assert result["punt_commitment_counts"]["clock_unknown"] == 0
    commands = row["audit_capture"]["typed_capture"]["commands"]
    assert commands[0]["report_changes"] == []
    assert commands[0]["before"]["view"]["statistics"] == commands[0]["after"]["view"]["statistics"]


def test_numeric_return_graduates_only_its_new_fixed_population():
    row, inventory = punt_subject(choice="kick:return")
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["punt_fair_catch_commitment"] == "GO"
    assert result["punt_commitment_counts"]["checked"] == 1
    assert result["punt_commitment_counts"]["return_checked"] == 1


@pytest.mark.parametrize("key", ["hurried", "conditional_timeout", "untimed_down"])
@pytest.mark.parametrize("bad", [0, None, "missing"])
def test_normal_context_boolean_domains_are_not_truthiness(key, bad):
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    view = row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"]
    if bad == "missing":
        view.pop(key)
    else:
        view[key] = bad
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize(
    "key,value",
    [
        ("hurried", True),
        ("untimed_down", True),
        ("conditional_timeout", True),
        ("kickoff_penalties", [{"team": "home"}]),
    ],
)
def test_known_unsupported_context_keeps_unknown_exposure(key, value):
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"][key] = value
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["punt_fair_catch_commitment"] == "UNVERIFIED"
    assert result["punt_commitment_counts"]["checked"] == 0


def test_near_period_continuation_keeps_checked_report_but_not_live_or_clock_authority():
    row, inventory = punt_subject(clock=Clock(1, 5, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    counts = result["punt_commitment_counts"]
    assert counts["report_checked"] == 1
    assert counts["checked"] == 0
    assert counts["clock_checked"] == 0 and counts["clock_unknown"] == 1
    assert result["components"]["punt_fair_catch_commitment"] == "UNVERIFIED"


def test_all_216_physical_punt_faces_use_their_actual_numeric_lookup():
    from itertools import product

    seen = 0
    for black, one, two in product((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5)):
        # Literal approved physical face multisets preserve repeated faces.
        roll = OffensiveRoll(black, one, two)
        flight = 30 + (10 * black + one + two) % 9
        row, inventory = punt_subject(flight=flight, roll=roll)
        result = audit_receipt(row, lookup_inventory=inventory)
        assert result["punt_commitment_counts"]["checked"] == 1
        final = row["engine_log"][-1]["state_after"]
        assert final["yards_to_goal"] == 35 + flight
        seen += 1
    assert seen == 216


def test_restored_pending_without_creating_command_is_unknown():
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    capture = row["audit_capture"]
    # A real detached reload has a new observed object/window; construct it
    # explicitly below rather than deleting a causal command from this receipt.
    from bowl_bound.save_game import dumps_game, loads_game

    teams = tuple(
        replace(
            team,
            special_teams=tuple(
                replace(
                    record,
                    cell=replace(record.cell, yards=40 if record.column.value == "punt" else 3),
                )
                for record in team.special_teams
            ),
        )
        for team in subject_teams()
    )
    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        mode="drive",
        seed=37,
        coach_seed=41,
        advanced_ii=False,
        dice=ScriptedDice([OffensiveRoll(2, 0, 1), OffensiveRoll(3, 4, 5)]),
    )
    game.kick("punt")
    game = loads_game(dumps_game(game), lambda ident: teams[0 if ident.endswith("home") else 1])
    with capture_receipts(typed=True, lookup_rows=True) as observed:
        game.decide("kick:fair_catch")
    from tools.game_audit_punt import audit_punt_commitments

    result = audit_punt_commitments(observed.payload(), typed_inventory_available=True)
    assert result["checked"] == 0 and result["unknown_reasons"] == {"pending_origin_authority": 1}
    assert capture["typed_capture"]["commands"][0]["operation"] == "kick"


@pytest.mark.parametrize("location", ["origin", "decision"])
def test_pending_and_committed_punt_id_cannot_reuse_observed_prefix(location):
    row, _ = punt_subject(clock=Clock(1, 600, (1, 2)))
    capture = row["audit_capture"]
    commands = capture["typed_capture"]["commands"]
    prior = commands[0]["initial_log"][0]["number"]
    commands[0]["returned_report"]["number"] = prior
    if location == "decision":
        final = commands[1]
        final["returned_report"]["number"] = prior
        final["report_changes"][0]["after"]["number"] = prior
        final["after"]["view"]["timing_log"][-1]["play_number"] = prior
    from tools.game_audit_punt import PuntEvidenceError, audit_punt_commitments

    with pytest.raises(PuntEvidenceError):
        audit_punt_commitments(capture, typed_inventory_available=True)


def test_checked_pending_punt_and_faircatch_continue_conditional_state_chain():
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    counts = result["ordinary_continuity_counts"]
    assert counts["qualified_punt_endpoints"] == 2
    assert counts["boundary_links"] == 1
    assert counts["unknown_endpoints"] == 0
    assert counts["initial_anchor_truth"] == "UNVERIFIED"


def test_prior_unqualified_punt_origin_cannot_be_reanchored_at_faircatch():
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    from tools.game_audit_continuity import audit_ordinary_continuity

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
    assert continuity["unknown_endpoints"] == 2
    assert continuity["qualified_punt_endpoints"] == 0


def test_local_nonperiod_clock_does_not_allow_claimed_period_phase():
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]["phase"] = "halftime"
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize(
    "key,value", [("overtime", False), ("armed_timeout", False), ("bounds_declaration", "")]
)
def test_optional_contexts_require_explicit_typed_absence(key, value):
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"][key] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("key", ["clock", "timing_log"])
def test_no_prior_pending_timing_requires_zero_punt_creation_charge(key):
    row, inventory = punt_subject(clock=Clock(1, 600, (1, 2)))
    before = row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"]
    if key == "clock":
        before["clock"]["remaining"] += 1
    else:
        before["timing_log"][0]["seconds"] += 1
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize("quarter", [1, 2, 3])
def test_valid_period_continuation_preserves_report_but_not_after_clock_authority(quarter):
    row, inventory = punt_subject(clock=Clock(quarter, 5, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    counts = result["punt_commitment_counts"]
    assert counts["report_checked"] == 1
    assert counts["checked"] == counts["clock_checked"] == 0
    assert counts["clock_unknown"] == 1


@pytest.mark.parametrize("remaining", [5, 600])
def test_punt_fresh_report_cannot_reuse_charged_prefix_even_if_period_unknown(remaining):
    row, inventory = punt_subject(clock=Clock(1, remaining, (1, 2)))
    commands = row["audit_capture"]["typed_capture"]["commands"]
    number = commands[-1]["returned_report"]["number"]
    for command in commands:
        for endpoint in ("before", "after"):
            command[endpoint]["view"]["timing_log"][0]["play_number"] = number
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)
