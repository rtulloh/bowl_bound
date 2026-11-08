"""Literal fixed previous-spot penalty subjects; engine is never the oracle."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    ChartColor,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    ResultKind,
)
from bowl_bound.save_game import SavedGame
from tests.test_game_audit_ordinary_commitment import log_digest
from tests.test_game_audit_row_links import frozen_inventory, subject_teams
from tests.test_game_receipt_audit import receipt
from tests.test_models import provenance
from tools.game_audit import ReceiptAuditError, audit_receipt


def penalty_subject(
    *,
    team="offense",
    yards=5,
    side="home",
    spot=65,
    down=1,
    distance=10,
    multiple=False,
    rerolls=None,
    prepared_incomplete=False,
    offset=False,
    clock=None,
    choice="accept:0:previous",
):
    def cell(roll):
        if offset and roll == 20:
            return NormalizedCell(
                ResultKind.PENALTY,
                provenance(),
                penalty=PenaltyData(
                    PenaltyTeam.DEFENSE if team == "offense" else PenaltyTeam.OFFENSE,
                    PenaltyCode.FIXED,
                    yards=5,
                ),
                chart_color=ChartColor.WHITE,
            )
        if roll in ({10, 11} if multiple else {10}):
            return NormalizedCell(
                ResultKind.PENALTY,
                provenance(),
                penalty=PenaltyData(PenaltyTeam(team), PenaltyCode.FIXED, yards=yards),
                chart_color=ChartColor.WHITE,
            )
        return NormalizedCell(
            ResultKind.INCOMPLETE if prepared_incomplete else ResultKind.YARDS,
            provenance(),
            yards=None if prepared_incomplete else 3,
            chart_color=ChartColor.WHITE,
        )

    teams = tuple(
        replace(
            chart,
            offense=tuple(replace(row, cell=cell(row.roll)) for row in chart.offense),
            special_teams=tuple(
                replace(record, cell=replace(record.cell, yards=65))
                if record.column.value == "kickoff" and clock is not None
                else record
                for record in chart.special_teams
            ),
            defense=tuple(
                replace(row, cell=replace(row.cell, yards=-1, chart_color=ChartColor.WHITE))
                for row in chart.defense
            ),
        )
        for chart in subject_teams()
    )
    draws = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    for _ in range((rerolls if rerolls is not None else 2 if multiple else 1) - 1):
        draws.append(OffensiveRoll(1, 0, 1) if multiple else OffensiveRoll(1, 0, 0))
    draws += [OffensiveRoll(2, 0, 0), OffensiveRoll(3, 4, 5)]
    if clock is not None:
        draws = [OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)] + draws
    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive" if clock is None else "regulation",
        clock=clock,
        start_yards_to_goal=spot,
        advanced_ii=False,
        dice=ScriptedDice(draws),
    )
    # Explicit supplied anchor, not reconstructed pre-window history.
    if clock is None:
        game._engine._field = FieldState(Possession(side), spot, down, distance)
    else:
        from tests.test_save_game import opening

        opening(game)
        game._engine._session._field = FieldState(Possession(side), spot, down, distance)
    from tools.game_audit_capture import capture_receipts

    with capture_receipts(typed=True, lookup_rows=True) as capture:
        pending = game.snap("9", "A")
        assert pending.pending is not offset
        if not offset:
            game.decide(choice)
    row = receipt()
    row["audit_capture"] = capture.payload()
    commands = row["audit_capture"]["typed_capture"]["commands"]
    final = commands[-1]["after"]["view"]
    row["engine_log"] = deepcopy(
        (commands[0]["initial_log"] or []) + commands[-1]["report_revisions"]
    )
    row["final"].update(
        statistics=deepcopy(final["statistics"]),
        home_score=final["score"]["home"],
        away_score=final["score"]["away"],
        scoring=deepcopy(final["scoring"]),
    )
    inventory = frozen_inventory()
    for record in inventory["cells"]:
        table = record["address"]["table"]
        if table == "defense":
            record["facts"].update(yards=-1, chart_color="white")
        elif table == "offense":
            penalty = record["address"]["roll"] in ({10, 11} if multiple else {10})
            record["facts"].update(
                kind="penalty" if penalty else "incomplete" if prepared_incomplete else "yards",
                yards=None if penalty or prepared_incomplete else 3,
                penalty=dict(
                    team=team, code="fixed", yards=yards, variable=None, variable_multiplier=None
                )
                if penalty
                else None,
                chart_color="white",
            )
    if offset:
        for record in inventory["cells"]:
            if record["address"]["table"] == "offense" and record["address"]["roll"] == 20:
                record["facts"].update(
                    kind="penalty",
                    yards=None,
                    penalty=dict(
                        team="defense" if team == "offense" else "offense",
                        code="fixed",
                        yards=5,
                        variable=None,
                        variable_multiplier=None,
                    ),
                )
    return row, inventory


def change_penalty_report(row, mutation):
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    report = command["report_changes"][0]["after"]
    mutation(report, command)
    command["returned_report"] = deepcopy(report)
    command["report_revisions"] = [deepcopy(report)]
    command["after"]["log_sha256"] = log_digest([report])
    row["engine_log"] = [deepcopy(report)]


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize(
    "team,yards,spot,down,distance,goal,newdown,newdistance",
    [
        ("offense", 5, 65, 4, 10, 70, 4, 15),
        ("offense", 10, 65, 2, 10, 75, 2, 20),
        ("defense", 5, 65, 3, 5, 60, 1, 10),
        ("defense", 15, 65, 4, 30, 50, 1, 10),
        ("offense", 5, 97, 4, 3, 98, 4, 4),
        ("defense", 5, 1, 4, 1, 1, 4, 1),
        ("defense", 15, 1, 4, 1, 1, 1, 1),
        ("offense", 5, 5, 2, 5, 10, 2, 10),
    ],
)
def test_fixed_previous_penalty_checks_literal_half_distance_and_replayed_down(
    side, team, yards, spot, down, distance, goal, newdown, newdistance
):
    row, inventory = penalty_subject(
        team=team, yards=yards, side=side, spot=spot, down=down, distance=distance
    )
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["accepted_previous_penalty_commitment"] == "GO"
    assert result["penalty_commitment_counts"]["checked"] == 1
    report = row["engine_log"][0]
    assert (
        report["state_after"]["possession"],
        report["state_after"]["yards_to_goal"],
        report["state_after"]["down"],
        report["state_after"]["yards_to_go"],
    ) == (side, goal, newdown, newdistance)
    assert report["statistics"] == dict(kind="excluded", team=None, yards=0, touchdown=False)
    assert report["yards"] == 2
    assert report["extends_quarter"] is (team == "defense")


@pytest.mark.parametrize(
    "fault",
    [
        "goal",
        "down",
        "distance",
        "possession",
        "called",
        "resolved",
        "timing",
        "chooser",
        "selected-index",
        "pending-box",
        "pending-score",
        "pending-field",
        "prepared-gain",
        "extension-flag",
    ],
)
def test_previous_penalty_corruptions_not_protected_by_old_opaque_fold_refuse(fault):
    row, inventory = penalty_subject()
    commands = row["audit_capture"]["typed_capture"]["commands"]
    origin, decision = commands
    if fault == "chooser":
        origin["after"]["view"]["pending"]["chooser_side"] = "home"
        decision["before"]["view"]["pending"]["chooser_side"] = "home"
    elif fault == "selected-index":
        decision["arguments"][0] = "accept:9:previous"
    elif fault.startswith("pending-"):
        key = fault.removeprefix("pending-")
        for snapshot in [origin["after"], decision["before"]]:
            if key == "box":
                snapshot["view"]["statistics"]["home"]["total_yards"] = 8
            elif key == "score":
                snapshot["view"]["score"]["home"] = 3
            else:
                snapshot["view"]["state"]["yards_to_goal"] = 66
    else:

        def mutate(report, command):
            if fault in {"goal", "down", "distance", "possession"}:
                key, value = {
                    "goal": ("yards_to_goal", 69),
                    "down": ("down", 2),
                    "distance": ("yards_to_go", 14),
                    "possession": ("possession", "away"),
                }[fault]
                report["state_after"][key] = value
                command["after"]["view"]["state"][key] = value
            elif fault in {"called", "resolved"}:
                report[fault + "_play"] = "Screen"
            elif fault == "prepared-gain":
                report["yards"] = 0
            elif fault == "extension-flag":
                report["extends_quarter"] = True
            else:
                report["timing"]["penalty"] = False

        change_penalty_report(row, mutate)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


def test_same_team_fouls_are_alternatives_not_summed():
    row, inventory = penalty_subject(multiple=True)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["checked"] == 1
    assert row["engine_log"][0]["state_after"]["yards_to_goal"] == 70


def test_summed_same_team_fouls_cannot_match_claimed_field():
    row, inventory = penalty_subject(multiple=True)

    def mutate(report, command):
        for state in [report["state_after"], command["after"]["view"]["state"]]:
            state.update(yards_to_goal=75, yards_to_go=20)

    change_penalty_report(row, mutate)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


def test_declined_penalty_is_not_accepted_excluded_credit():
    row, inventory = penalty_subject(choice="decline")
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["checked"] == 0
    assert row["engine_log"][0]["statistics"]["kind"] == "completion"


def test_prepared_incomplete_format_survives_without_offensive_credit():
    row, inventory = penalty_subject(prepared_incomplete=True)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["checked"] == 1
    report = row["engine_log"][0]
    assert report["yards"] == 0
    assert report["timing"]["incomplete"] is True
    assert report["statistics"] == dict(kind="excluded", team=None, yards=0, touchdown=False)


def test_one_hundred_penalty_rerolls_have_complete_ordered_draws():
    row, inventory = penalty_subject(rerolls=100)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["checked"] == 1
    capture = row["audit_capture"]
    assert len(capture["typed_capture"]["draws"]) == 102
    assert len(capture["priority"]["events"]) == 101
    assert len(capture["lookup_rows"]["events"]) == 102


@pytest.mark.parametrize(
    "field,value",
    [
        ("untimed_down", True),
        ("conditional_timeout", True),
        ("armed_timeout", "home"),
        ("hurried", 0),
    ],
)
def test_unqualified_modifier_context_cannot_gain_fixed_penalty_authority(field, value):
    row, inventory = penalty_subject()
    row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"][field] = value
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["checked"] == 0
    assert result["components"]["accepted_previous_penalty_commitment"] == "UNVERIFIED"


def test_penalty_graph_refuses_a_101st_selected_foul_before_missing_tail_can_hide_it():
    from tools.game_audit_penalty import PenaltyEvidenceError, _origin

    row, _ = penalty_subject(rerolls=100)
    capture = row["audit_capture"]
    command = capture["typed_capture"]["commands"][0]
    events = capture["priority"]["events"]
    events.insert(-1, deepcopy(events[0]))
    command["priority_range"][1] += 1
    with pytest.raises(PenaltyEvidenceError, match="100 penalty reroll bound"):
        _origin(command, capture)


@pytest.mark.parametrize("team", ["offense", "defense"])
def test_actual_offset_stops_before_prepared_tail_and_remains_unknown(team):
    row, inventory = penalty_subject(team=team, offset=True)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert row["engine_log"][0]["outcome"] == "offsetting"
    assert result["penalty_commitment_counts"]["checked"] == 0
    assert result["components"]["accepted_previous_penalty_commitment"] == "UNVERIFIED"
    assert result["penalty_commitment_counts"]["unknown_reasons"]["offsetting_authority"] == 1


@pytest.mark.parametrize("side", ["home", "away"])
def test_normal_regulation_penalty_checks_actual_ten_second_charge(side):
    from bowl_bound.timing import Clock

    row, inventory = penalty_subject(side=side, clock=Clock(1, 600, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    commands = row["audit_capture"]["typed_capture"]["commands"]
    before, after = commands[-1]["before"]["view"], commands[-1]["after"]["view"]
    assert {k: before["clock"][k] for k in ("quarter", "remaining", "timeouts")} == dict(
        quarter=1, remaining=600, timeouts=[1, 2]
    )
    assert {k: after["clock"][k] for k in ("quarter", "remaining", "timeouts")} == dict(
        quarter=1, remaining=590, timeouts=[1, 2]
    )
    assert result["penalty_commitment_counts"]["clock_checked"] == 1
    assert result["components"]["standard_clock"] == "UNVERIFIED"


@pytest.mark.parametrize(
    "fault",
    [
        "seconds",
        "before",
        "after",
        "quarter",
        "play",
        "method",
        "missing",
        "duplicate",
        "prefix",
        "clock",
        "timeouts",
        "pending-charge",
    ],
)
def test_wrong_penalty_elapsed_charge_is_not_hidden_by_correct_timing_flags(fault):
    from bowl_bound.timing import Clock

    row, inventory = penalty_subject(clock=Clock(1, 600, (1, 2)))
    origin, command = row["audit_capture"]["typed_capture"]["commands"]
    view = command["after"]["view"]
    charge = view["timing_log"][-1]
    if fault in {"seconds", "before", "after", "quarter"}:
        charge[fault] += 1
    elif fault == "play":
        charge["play_number"] += 1
    elif fault == "method":
        charge["method"] = "clock:hurry"
    elif fault == "missing":
        view["timing_log"].pop()
    elif fault == "duplicate":
        view["timing_log"].append(deepcopy(charge))
    elif fault == "prefix":
        view["timing_log"][0]["seconds"] = 1
    elif fault == "clock":
        view["clock"]["remaining"] += 1
    elif fault == "timeouts":
        view["clock"]["timeouts"][0] = 3
    else:
        for endpoint in [origin["after"], command["before"]]:
            endpoint["view"]["timing_log"].append(deepcopy(charge))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


def test_drive_penalty_does_not_claim_elapsed_clock_authority():
    row, inventory = penalty_subject()
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["clock_checked"] == 0
    assert result["penalty_commitment_counts"]["clock_unknown"] == 1


def test_period_crossing_penalty_keeps_local_clock_unknown_after_report_check():
    from bowl_bound.timing import Clock

    row, inventory = penalty_subject(clock=Clock(1, 5, (1, 2)))
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["penalty_commitment_counts"]["report_checked"] == 1
    assert result["penalty_commitment_counts"]["clock_checked"] == 0
    assert result["penalty_commitment_counts"]["clock_unknown"] == 1


@pytest.mark.parametrize("stage", ["initial", "pending", "both"])
@pytest.mark.parametrize("side", ["home", "away"])
def test_penalty_clock_initial_and_pending_timeout_mirrors_cannot_contradict_budgets(stage, side):
    from bowl_bound.timing import Clock

    row, inventory = penalty_subject(clock=Clock(1, 600, (1, 2)))
    origin, command = row["audit_capture"]["typed_capture"]["commands"]
    targets = []
    if stage in {"initial", "both"}:
        targets.append(origin["before"]["view"])
    if stage in {"pending", "both"}:
        targets.extend([origin["after"]["view"], command["before"]["view"]])
    for view in targets:
        view[side + "_timeouts"] = 3
    with pytest.raises(ReceiptAuditError, match="timeout mirror"):
        audit_receipt(row, lookup_inventory=inventory)
