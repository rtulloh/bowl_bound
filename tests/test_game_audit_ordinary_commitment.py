"""Independent fixed ordinary commitment: engine only supplies observations."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, ResultKind
from bowl_bound.save_game import SavedGame
from tests.test_game_audit_row_links import frozen_inventory, subject_teams
from tests.test_game_receipt_audit import receipt
from tests.test_models import provenance
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_capture import capture_receipts


def log_digest(reports):
    return hashlib.sha256(
        json.dumps(reports, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def subject_receipt(*, gain=2, play="1", spot=65, prior=0, kind=ResultKind.YARDS):
    """Explicit charts/expected facts; never serialize subject charts as oracle."""
    teams = tuple(
        replace(
            team,
            offense=tuple(
                replace(
                    record,
                    cell=replace(record.cell, yards=0)
                    if record.roll == 10
                    else NormalizedCell(
                        kind,
                        provenance(),
                        yards=gain if kind is ResultKind.YARDS else None,
                        chart_color=record.cell.chart_color,
                    ),
                )
                for record in team.offense
            ),
            defense=tuple(
                replace(record, cell=replace(record.cell, yards=0)) for record in team.defense
            ),
        )
        for team in subject_teams()
    )
    rolls = [value for _ in range(prior) for value in (OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0))]
    rolls += [OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)]
    if kind in {ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED, ResultKind.BREAKAWAY}:
        rolls.append(OffensiveRoll(2, 0, 0))
    subject = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive",
        advanced_ii=False,
        start_yards_to_goal=spot,
        dice=ScriptedDice(rolls),
    )
    for _ in range(prior):
        subject.snap("1", "A")
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap(play, "F")
    row = receipt()
    row["audit_capture"] = capture.payload()
    frozen = frozen_inventory()
    for record in frozen["cells"]:
        table = record["address"]["table"]
        if table == "defense":
            record["facts"]["yards"] = 0
        elif table == "offense":
            record["facts"].update(
                kind="yards" if record["address"]["roll"] == 10 else kind.value,
                yards=0
                if record["address"]["roll"] == 10
                else gain
                if kind is ResultKind.YARDS
                else None,
            )
    return row, frozen


def change_report(row, mutation):
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    report = command["report_changes"][0]["after"]
    mutation(report, command)
    command["returned_report"] = deepcopy(report)
    command["report_revisions"] = [deepcopy(report)]
    # Preserve the full pre-window history; report numbers are not log positions.
    reports = deepcopy(command["initial_log"])
    reports.append(deepcopy(report))
    command["after"]["log_sha256"] = log_digest(reports)


def test_fixed_primary_derives_ordinary_core_field_and_complete_stat_delta():
    row, frozen = subject_receipt()
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"
    assert result["coverage"]["ordinary_commitment"] == dict(checked=1, excluded=0, unknown=0)
    assert result["ordinary_commitment_counts"]["rush"] == 1
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "goal",
        "down",
        "distance",
        "owner",
        "called",
        "resolved",
        "gain",
        "credit-kind",
        "credit-yards",
        "box-home",
        "box-away",
        "score",
        "outcome",
        "row-role",
        "row-play",
        "row-formation",
        "operand",
    ],
)
def test_ordinary_corruptions_preserving_old_opaque_history_refuse(mutation):
    row, frozen = subject_receipt()

    def alter(report, command):
        if mutation in {"goal", "down", "distance", "owner"}:
            key, value = {
                "goal": ("yards_to_goal", 62),
                "down": ("down", 3),
                "distance": ("yards_to_go", 7),
                "owner": ("possession", "away"),
            }[mutation]
            report["state_after"][key] = value
            command["after"]["view"]["state"][key] = value
        elif mutation in {"called", "resolved"}:
            report[mutation + "_play"] = "Drop Back"
        elif mutation == "gain":
            report["yards"] = 3
        elif mutation == "credit-kind":
            report["statistics"]["kind"] = "completion"
        elif mutation == "credit-yards":
            report["statistics"]["yards"] = 3
        elif mutation.startswith("box-"):
            command["after"]["view"]["statistics"][mutation[4:]]["total_yards"] += 1
        elif mutation == "score":
            command["after"]["view"]["score"]["home"] += 1
        elif mutation == "outcome":
            report["outcome"] = "first_down"
        elif mutation.startswith("row-"):
            events = row["audit_capture"]["lookup_rows"]["events"]
            if mutation == "row-role":
                events[0]["address"]["team_id"] = "2002/away"
                events[1]["address"]["team_id"] = "2002/home"
            else:
                for event in events:
                    if mutation == "row-play":
                        event["address"]["play"] = 9
                    elif event["address"]["table"] == "defense":
                        event["address"]["formation"] = "A"
        elif mutation == "operand":
            event = row["audit_capture"]["priority"]["events"][0]
            event["offense"]["yards"] = event["result"]["offense"]["yards"] = 3
            event["result"]["yards"] = 3
            row["audit_capture"]["typed_capture"]["priority_attempts"][0]["offense"]["yards"] = 3

    change_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "gain,play,spot,prior,kind,outcome,state,credit,credited,td",
    [
        (2, "1", 65, 0, ResultKind.YARDS, "advance", ("home", 63, 2, 8), "rush", 2, False),
        (-4, "9", 65, 0, ResultKind.YARDS, "advance", ("home", 69, 2, 14), "completion", -4, False),
        (0, "9", 65, 0, ResultKind.YARDS, "advance", ("home", 65, 2, 10), "completion", 0, False),
        (
            12,
            "9",
            65,
            0,
            ResultKind.YARDS,
            "first_down",
            ("home", 53, 1, 10),
            "completion",
            12,
            False,
        ),
        (2, "1", 5, 0, ResultKind.YARDS, "advance", ("home", 3, 2, 3), "rush", 2, False),
        (-2, "9", 5, 0, ResultKind.YARDS, "advance", ("home", 7, 2, 7), "completion", -2, False),
        (
            0,
            "1",
            65,
            3,
            ResultKind.YARDS,
            "turnover_on_downs",
            ("away", 35, 1, 10),
            "rush",
            0,
            False,
        ),
        (12, "1", 65, 3, ResultKind.YARDS, "first_down", ("home", 53, 1, 10), "rush", 12, False),
        (2, "1", 65, 4, ResultKind.YARDS, "advance", ("away", 33, 2, 8), "rush", 2, False),
        (
            0,
            "1",
            65,
            0,
            ResultKind.INCOMPLETE,
            "advance",
            ("home", 65, 2, 10),
            "incomplete",
            0,
            False,
        ),
        (
            0,
            "9",
            65,
            0,
            ResultKind.NO_CHANGE,
            "advance",
            ("home", 65, 2, 10),
            "completion",
            0,
            False,
        ),
        (12, "9", 5, 0, ResultKind.YARDS, "touchdown", None, "completion", 5, True),
        (12, "1", 5, 0, ResultKind.YARDS, "touchdown", None, "rush", 5, True),
        (0, "9", 5, 0, ResultKind.TOUCHDOWN, "touchdown", None, "completion", 5, True),
    ],
)
def test_actual_ordinary_subjects_match_independently_written_rule_examples(
    gain, play, spot, prior, kind, outcome, state, credit, credited, td
):
    row, frozen = subject_receipt(gain=gain, play=play, spot=spot, prior=prior, kind=kind)
    report = row["audit_capture"]["typed_capture"]["commands"][0]["returned_report"]
    assert report["outcome"] == outcome
    actual = report["state_after"]
    assert (
        tuple(actual[k] for k in ["possession", "yards_to_goal", "down", "yards_to_go"])
        if actual is not None
        else None
    ) == state
    owner = "away" if prior == 4 else "home"
    assert report["statistics"] == dict(kind=credit, team=owner, yards=credited, touchdown=td)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"
    assert result["ordinary_commitment_counts"][credit] == 1


@pytest.mark.parametrize("gain", [-5, -6])
def test_unpinned_own_goal_edge_is_unknown_not_silent_success(gain):
    row, frozen = subject_receipt(gain=gain, spot=95)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "UNVERIFIED"
    assert result["coverage"]["ordinary_commitment"] == dict(checked=0, excluded=0, unknown=1)
    assert result["ordinary_commitment_counts"]["unknown_reasons"] == {"own_goal_authority": 1}


@pytest.mark.parametrize(
    "mutation",
    ["phase", "boolean-down", "boolean-credit", "boolean-box", "td-yards", "td-side", "td-award"],
)
def test_strict_core_and_scoring_corruptions_cannot_escape_via_claimed_phase(mutation):
    row, frozen = (
        subject_receipt(gain=12, spot=5, play="9")
        if mutation.startswith("td-")
        else subject_receipt()
    )

    def alter(report, command):
        if mutation == "phase":
            command["after"]["view"]["phase"] = "halftime"
            report["state_after"]["yards_to_goal"] = 62
            command["after"]["view"]["state"]["yards_to_goal"] = 62
        elif mutation == "boolean-down":
            report["state_after"]["down"] = True
        elif mutation == "boolean-credit":
            report["statistics"]["touchdown"] = 0
        elif mutation == "boolean-box":
            command["after"]["view"]["statistics"]["home"]["rushing_attempts"] = True
        elif mutation == "td-yards":
            report["statistics"]["yards"] = 12
        elif mutation == "td-side":
            command["after"]["view"]["score"] = {"home": 0, "away": 6}
            command["after"]["view"]["scoring"][0]["team"] = "Away"
        elif mutation == "td-award":
            command["after"]["view"]["score"]["home"] = 7
            command["after"]["view"]["scoring"][0]["points"] = 7

    change_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("play", list("123456789"))
def test_every_ordinary_call_uses_approved_explicit_marker_accounting(play):
    row, frozen = subject_receipt(play=play)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"
    assert result["ordinary_commitment_counts"]["rush" if int(play) <= 5 else "completion"] == 1


def test_missing_inventory_keeps_semantic_commitment_unverified():
    row, _ = subject_receipt()
    result = audit_receipt(row)
    assert result["components"]["ordinary_commitment"] == "UNVERIFIED"
    assert result["coverage"]["ordinary_commitment"] == dict(checked=0, excluded=0, unknown=1)


def test_option_chain_does_not_inherit_ordinary_call_five_rush_credit():
    from tests.test_game_audit_row_links import option_observed

    row, frozen = option_observed()
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "UNVERIFIED"
    assert result["ordinary_commitment_counts"]["checked"] == 0
    assert result["ordinary_commitment_counts"]["unknown"] == 1
    assert result["components"]["all_called_resolved_branches"] == "UNVERIFIED"


def test_zero_observed_commands_is_notrun():
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        pass
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["ordinary_commitment"] == "NOTRUN"
    assert result["coverage"]["ordinary_commitment"] == dict(checked=0, excluded=0, unknown=0)


@pytest.mark.parametrize(
    "kind", [ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED, ResultKind.BREAKAWAY]
)
def test_supplemental_branches_remain_unknown_in_fixed_primary_slice(kind):
    row, frozen = subject_receipt(kind=kind)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "UNVERIFIED"
    assert result["ordinary_commitment_counts"]["checked"] == 0
    assert result["ordinary_commitment_counts"]["unknown"] == 1


@pytest.mark.parametrize("numeric", [False, True])
def test_matching_zero_report_sentinel_cannot_replace_printed_td_semantics(numeric):
    row, frozen = subject_receipt(
        gain=0, kind=ResultKind.YARDS if numeric else ResultKind.TOUCHDOWN
    )

    def alter(report, command):
        if numeric:
            report["outcome"] = "touchdown"
            report["state_after"] = None
            report["statistics"].update(yards=65, touchdown=True)
        else:
            report["outcome"] = "advance"
            report["statistics"].update(yards=0, touchdown=False)

    change_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_protected_defensive_numeric_uses_independent_priority_before_classification():
    row, frozen = subject_receipt(play="9")
    # Build a separate actual subject with a reviewed parenthesized defensive fact.
    from bowl_bound.models import Priority

    teams = tuple(
        replace(
            team,
            defense=tuple(
                replace(record, cell=replace(record.cell, yards=7, priority=Priority.PARENTHESIZED))
                for record in team.defense
            ),
        )
        for team in subject_teams()
    )
    subject = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive",
        advanced_ii=False,
        dice=ScriptedDice([OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)]),
    )
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap("9", "F")
    row["audit_capture"] = capture.payload()
    frozen = frozen_inventory()
    for record in frozen["cells"]:
        if record["address"]["table"] == "defense":
            record["facts"].update(yards=7, priority="parenthesized")
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"
    assert result["ordinary_commitment_counts"]["completion"] == 1
    assert capture.commands[0]["returned_report"]["statistics"]["yards"] == 7


def test_failed_partial_attempt_cannot_be_hidden_by_one_valid_ordinary_commitment():
    from bowl_bound.dice import DiceSequenceError
    from tests.test_game_audit_typed_capture import game

    with capture_receipts(typed=True, lookup_rows=True) as capture:
        with pytest.raises(DiceSequenceError):
            game(subject_teams(), [OffensiveRoll(1, 0, 0)]).snap("1", "A")
        game(subject_teams(), [OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)]).snap("1", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["ordinary_commitment"] == "UNVERIFIED"
    assert result["coverage"]["ordinary_commitment"] == dict(checked=1, excluded=0, unknown=1)
    assert result["ordinary_commitment_counts"]["unknown_reasons"] == {"failed_command": 1}


@pytest.mark.parametrize("missing", ["box", "before-goal"])
def test_malformed_required_commitment_facts_raise_retained_audit_error(missing):
    row, frozen = subject_receipt()
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    if missing == "box":
        del command["after"]["view"]["statistics"]["away"]
    else:
        del command["before"]["view"]["state"]["yards_to_goal"]
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("identity", [True, 0])
def test_scoring_report_reference_requires_positive_nonboolean_id(identity):
    row, frozen = subject_receipt(gain=12, spot=5)

    def alter(report, command):
        report["number"] = identity
        command["after"]["view"]["scoring"][0]["play_number"] = identity

    change_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def regulation_receipt(gain=2, kind=ResultKind.YARDS, clock=None):
    from tests.test_save_game import opening

    teams = tuple(
        replace(
            team,
            offense=tuple(
                replace(
                    record,
                    cell=NormalizedCell(
                        kind,
                        provenance(),
                        yards=gain if kind is ResultKind.YARDS else None,
                        chart_color=record.cell.chart_color,
                    ),
                )
                for record in team.offense
            ),
            defense=tuple(
                replace(record, cell=replace(record.cell, yards=0)) for record in team.defense
            ),
            special_teams=tuple(
                replace(record, cell=replace(record.cell, yards=65))
                if record.column.value == "kickoff"
                else record
                for record in team.special_teams
            ),
        )
        for team in subject_teams()
    )
    rolls = [
        OffensiveRoll(3, 4, 5),
        OffensiveRoll(1, 0, 0),
        OffensiveRoll(2, 0, 0),
        OffensiveRoll(2, 0, 1),
        DefensiveRoll(2, 1),
    ]
    subject = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="regulation",
        advanced_ii=False,
        clock=clock,
        dice=ScriptedDice(rolls),
    )
    opening(subject)
    if subject.view().phase == "clock_choice":
        subject.decide("clock:runoff")
    assert subject.view().phase == "scrimmage"
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        subject.snap("9", "F")
    row = receipt()
    row["audit_capture"] = capture.payload()
    # This synthetic wrapper binds the observed prefix/boxes for existing halftime
    # checks; it does not claim the observed subject is a finished real game.
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    row["engine_log"] = deepcopy(command["initial_log"]) + deepcopy(command["report_revisions"])
    after = command["after"]["view"]
    row["final"].update(
        statistics=deepcopy(after["statistics"]),
        home_score=after["score"]["home"],
        away_score=after["score"]["away"],
        scoring=deepcopy(after["scoring"]),
    )

    frozen = frozen_inventory()
    for record in frozen["cells"]:
        if record["address"]["table"] == "offense":
            record["facts"].update(
                kind=kind.value, yards=gain if kind is ResultKind.YARDS else None
            )
        elif record["address"]["table"] == "defense":
            record["facts"]["yards"] = 0
        elif (
            record["address"]["table"] == "special_teams"
            and record["address"]["column"] == "kickoff"
        ):
            record["facts"]["yards"] = 65
    return row, frozen


@pytest.mark.parametrize(
    "gain,kind,phase,credited",
    [
        (2, ResultKind.YARDS, "clock_choice", 2),
        (100, ResultKind.YARDS, "conversion_choice", 80),
        (0, ResultKind.TOUCHDOWN, "conversion_choice", 80),
    ],
)
def test_actual_regulation_normal_timing_and_td_keep_independent_field_credit(
    gain, kind, phase, credited
):
    row, frozen = regulation_receipt(gain, kind)
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    assert command["after"]["view"]["phase"] == phase
    assert command["returned_report"]["statistics"]["yards"] == credited
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"


@pytest.mark.parametrize("optional", [False, 1, None])
def test_clock_choice_format_requires_strict_true_and_derived_field(optional):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"]["clock_optional"] = (
        optional
    )
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_drive_cannot_claim_regulation_clock_choice_to_waive_field():
    row, frozen = subject_receipt()
    after = row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"]
    after.update(phase="clock_choice", clock_optional=True)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_actual_expired_half_retains_checked_report_but_unverified_live_continuation():
    from bowl_bound.timing import Clock

    row, frozen = regulation_receipt(kind=ResultKind.INCOMPLETE, clock=Clock(2, 5))
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    assert command["returned_report"]["state_after"]["yards_to_goal"] == 80
    assert command["returned_report"]["state_after"]["down"] == 2
    assert command["after"]["view"]["phase"] == "kickoff"
    assert command["after"]["view"]["state"]["yards_to_goal"] == 65
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "UNVERIFIED"
    assert result["ordinary_commitment_counts"]["report_checked"] == 1
    assert result["ordinary_commitment_counts"]["unknown_reasons"] == {
        "live_continuation_authority": 1
    }
    assert result["coverage"]["ordinary_commitment"] == dict(checked=0, excluded=0, unknown=1)


@pytest.mark.parametrize("name", [True, "", None])
def test_view_team_label_format_cannot_mint_boolean_or_empty_scoring_team(name):
    row, frozen = subject_receipt(gain=12, spot=5)
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    command["before"]["view"]["home"] = name
    command["after"]["view"]["home"] = name
    command["after"]["view"]["scoring"][0]["team"] = name
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_unknown_period_continuation_cannot_hide_wrong_committed_report_field():
    from bowl_bound.timing import Clock

    row, frozen = regulation_receipt(kind=ResultKind.INCOMPLETE, clock=Clock(2, 5))

    def alter(report, command):
        report["state_after"]["yards_to_go"] = 9

    change_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_normal_regulation_clock_choice_still_requires_derived_live_field():
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"]["state"][
        "yards_to_goal"
    ] = 79
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)
