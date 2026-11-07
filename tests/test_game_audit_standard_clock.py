"""Independent standard timing; engine creates subjects, never expectations."""

from copy import deepcopy

import pytest

from bowl_bound.models import ResultKind
from bowl_bound.timing import Clock
from tests.test_game_audit_ordinary_commitment import regulation_receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


def test_normal_deferred_clock_has_independently_checked_duration_and_committed_view():
    row, frozen = regulation_receipt()
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    assert result["coverage"]["standard_clock"] == dict(checked=1, excluded=0, unknown=0)
    assert result["standard_clock_counts"]["deferred"] == 1
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize(
    "fault",
    ["remaining", "quarter", "timeouts", "optional-type", "period-flag", "unexpected-charge"],
)
def test_deferred_clock_corruptions_ignored_by_prior_observer_refuse(fault):
    row, frozen = regulation_receipt()
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    after = command["after"]["view"]
    if fault == "remaining":
        after["clock"]["remaining"] += 1
    elif fault == "quarter":
        after["clock"]["quarter"] = 2
    elif fault == "timeouts":
        after["clock"]["timeouts"][0] = 2
    elif fault == "optional-type":
        after["normal_timing_ends_period"] = 0
    elif fault == "period-flag":
        after["normal_timing_ends_period"] = True
    else:
        after["timing_log"].append(
            dict(play_number=2, quarter=1, before=900, seconds=30, after=870, method="standard")
        )
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "fault",
    ["before", "seconds", "after", "quarter", "play", "method", "missing", "duplicate", "prefix"],
)
def test_immediate_charge_corruptions_ignored_by_prior_observer_refuse(fault):
    row, frozen = regulation_receipt(kind=ResultKind.INCOMPLETE)
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    charges = command["after"]["view"]["timing_log"]
    charge = charges[-1]
    if fault in {"before", "seconds", "after", "quarter"}:
        charge[fault] += 1
    elif fault == "play":
        charge["play_number"] += 1
    elif fault == "method":
        charge["method"] = "clock:hurry"
    elif fault == "missing":
        charges.pop()
    elif fault == "duplicate":
        charges.append(deepcopy(charge))
    else:
        charges[0]["seconds"] = 1
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("fault", ["remaining", "quarter", "timeouts"])
def test_incomplete_expiration_clock_and_halftime_reset_are_not_claimed_by_phase(fault):
    row, frozen = regulation_receipt(kind=ResultKind.INCOMPLETE, clock=Clock(2, 5, (1, 2)))
    after = row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"]
    if fault == "remaining":
        after["clock"]["remaining"] = 895
    elif fault == "quarter":
        after["clock"]["quarter"] = 2
    else:
        after["clock"]["timeouts"] = [1, 2]
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def sequence_receipt(
    *,
    clock=None,
    gain=2,
    kind=ResultKind.YARDS,
    second_gain=None,
    second_kind=None,
    oob=False,
    oob_roll=22,
    offensive_priority="normal",
    defensive_priority="normal",
    home_receives=True,
    actions=None,
    pat_good=None,
    pat_roll=None,
    pre_actions=None,
    random_dice=False,
):
    """Real subject, literal external facts; no engine serialization as oracle."""
    from dataclasses import replace

    from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
    from bowl_bound.models import NormalizedCell, Priority
    from bowl_bound.save_game import SavedGame
    from tests.test_game_audit_row_links import frozen_inventory, subject_teams
    from tests.test_game_receipt_audit import receipt
    from tests.test_models import provenance
    from tests.test_save_game import opening
    from tools.game_audit_capture import capture_receipts

    def ordinary_cell(record):
        selected_kind = second_kind if record.roll == 22 and second_kind is not None else kind
        selected_gain = second_gain if record.roll == 22 and second_gain is not None else gain
        return NormalizedCell(
            selected_kind,
            provenance(),
            yards=selected_gain
            if selected_kind is ResultKind.YARDS
            else 0
            if selected_kind is ResultKind.INTERCEPTION
            else None,
            out_of_bounds=oob and record.roll == oob_roll,
            priority=Priority(offensive_priority),
            chart_color=record.cell.chart_color,
        )

    teams = tuple(
        replace(
            team,
            offense=tuple(
                replace(
                    record,
                    cell=ordinary_cell(record),
                )
                for record in team.offense
            ),
            defense=tuple(
                replace(
                    record,
                    cell=replace(record.cell, yards=0, priority=Priority(defensive_priority)),
                )
                for record in team.defense
            ),
            pat_outcomes=tuple(
                replace(record, good=pat_good) if pat_good is not None else record
                for record in team.pat_outcomes
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
    toss = [OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]
    rolls = (toss if home_receives else list(reversed(toss))) + [OffensiveRoll(2, 0, 0)]
    rolls += [
        roll for n in range(8) for roll in (OffensiveRoll(2, 0, 1 + n % 2), DefensiveRoll(2, 1))
    ]
    if pat_roll is not None:
        rolls[5] = pat_roll
    subject = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="regulation",
        advanced_ii=False,
        clock=clock or Clock(),
        dice=None if random_dice else ScriptedDice(rolls),
    )
    opening(subject)
    for operation, args in pre_actions or []:
        getattr(subject, operation)(*args)
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        for operation, args in actions or [
            ("snap", ["1", "F"]),
            ("decide", ["clock:runoff"]),
            ("snap", ["1", "F"]),
        ]:
            getattr(subject, operation)(*args)
    row = receipt()
    row["audit_capture"] = capture.payload()
    commands = row["audit_capture"]["typed_capture"]["commands"]
    reports = deepcopy(commands[0]["initial_log"])
    for command in commands:
        for change in command["report_changes"]:
            if change["before"] is None:
                reports.append(deepcopy(change["after"]))
            else:
                reports[change["index"]] = deepcopy(change["after"])
    row["engine_log"] = reports
    after = commands[-1]["after"]["view"]
    row["final"].update(
        statistics=deepcopy(after["statistics"]),
        home_score=after["score"]["home"],
        away_score=after["score"]["away"],
        scoring=deepcopy(after["scoring"]),
    )
    frozen = frozen_inventory()
    for record in frozen["cells"]:
        address, facts = record["address"], record["facts"]
        if address["table"] == "offense":
            facts.update(
                kind=(
                    second_kind if address["roll"] == 22 and second_kind is not None else kind
                ).value,
                yards=(second_gain if address["roll"] == 22 and second_gain is not None else gain)
                if (second_kind if address["roll"] == 22 and second_kind is not None else kind)
                is ResultKind.YARDS
                else 0
                if address["roll"] == 22 and second_kind is ResultKind.INTERCEPTION
                else None,
                out_of_bounds=oob and address["roll"] == oob_roll,
                priority=offensive_priority,
            )
        elif address["table"] == "pat" and pat_good is not None:
            facts["good"] = pat_good
        elif address["table"] == "defense":
            facts.update(yards=0, priority=defensive_priority)
        elif address["table"] == "special_teams" and address["column"] == "kickoff":
            facts["yards"] = 65
    return row, frozen


@pytest.mark.parametrize("quarter,start,second_end", [(2, 125, 85), (4, 305, 265)])
def test_explicit_prior_runoff_crosses_oob_threshold_without_double_subtraction(
    quarter, start, second_end
):
    row, frozen = sequence_receipt(clock=Clock(quarter, start), oob=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    counts = result["standard_clock_counts"]
    assert (counts["checked"], counts["deferred"], counts["runoff"], counts["immediate"]) == (
        3,
        1,
        1,
        1,
    )
    commands = row["audit_capture"]["typed_capture"]["commands"]
    assert commands[0]["after"]["view"]["clock"]["remaining"] == start
    assert commands[1]["after"]["view"]["clock"]["remaining"] == start - 30
    assert commands[2]["after"]["view"]["clock"]["remaining"] == second_end


@pytest.mark.parametrize("quarter", [1, 2, 3])
def test_explicit_runoff_caps_at_period_and_does_not_carry_requested_residual(quarter):
    row, frozen = sequence_receipt(
        clock=Clock(quarter, 25, (1, 2)),
        actions=[("snap", ["1", "A"]), ("decide", ["clock:runoff"])],
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    assert result["standard_clock_counts"]["periods"] == 1
    last = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    charge = last["timing_log"][-1]
    assert (charge["before"], charge["seconds"], charge["after"]) == (25, 30, 0)
    assert last["clock"]["quarter"] == quarter + 1
    assert last["clock"]["remaining"] == 900
    assert last["clock"]["timeouts"] == ([3, 3] if quarter == 2 else [1, 2])


def test_reviewed_implicit_next_snap_and_explicit_runoff_share_one_known_chain():
    row, frozen = sequence_receipt(
        actions=[("snap", ["1", "A"]), ("snap", ["1", "A"]), ("decide", ["clock:runoff"])]
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    counts = result["standard_clock_counts"]
    assert result["components"]["standard_clock"] == "GO"
    assert counts["checked"] == 3 and counts["unknown"] == 0
    assert counts["implicit"] == 1 and counts["runoff"] == 1


@pytest.mark.parametrize(
    "field,value",
    [("clock_optional", 1), ("conditional_timeout", 0), ("hurried", None), ("untimed_down", False)],
)
def test_malformed_required_before_flags_do_not_escape_as_unknown(field, value):
    row, frozen = regulation_receipt()
    before = row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"]
    if field == "untimed_down":
        before.pop(field)
    else:
        before[field] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field,value",
    [
        ("armed_timeout", "home"),
        ("conditional_timeout", True),
        ("hurried", True),
        ("untimed_down", True),
    ],
)
def test_no_new_modifier_can_appear_from_supported_ordinary_clock_command(field, value):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"][field] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field,value",
    [
        ("quarter", True),
        ("quarter", 5),
        ("remaining", False),
        ("remaining", 901),
        ("remaining", 0),
        ("timeouts", [True, 3]),
        ("timeouts", [4, 3]),
    ],
)
def test_live_clock_anchor_requires_strict_physical_domains(field, value):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"]["clock"][field] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_missing_typed_inventory_remains_unknown_without_minting_clock_truth():
    row, _ = regulation_receipt()
    result = audit_receipt(row)
    assert result["components"]["standard_clock"] == "UNVERIFIED"
    assert result["standard_clock_counts"]["checked"] == 0
    assert result["standard_clock_counts"]["unknown"] == 1


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("gain,expected", [(0, 30), (2, 30), (12, 20)])
def test_numeric_ordinary_timing_uses_independent_first_down_and_mirrored_possession(
    home, gain, expected
):
    row, frozen = sequence_receipt(
        home_receives=home, gain=gain, actions=[("snap", ["9", "F"]), ("decide", ["clock:runoff"])]
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    assert command["after"]["view"]["timing_log"][-1]["seconds"] == expected


@pytest.mark.parametrize(
    "quarter,remaining,expected",
    [(1, 120, 30), (2, 121, 30), (2, 120, 10), (3, 120, 30), (4, 301, 30), (4, 300, 10)],
)
def test_natural_oob_exact_windows_derive_from_typed_priority(quarter, remaining, expected):
    actions = [("snap", ["1", "A"])]
    if expected > 10:
        actions.append(("decide", ["clock:runoff"]))
    row, frozen = sequence_receipt(
        clock=Clock(quarter, remaining), oob=True, oob_roll=21, actions=actions
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    assert command["after"]["view"]["timing_log"][-1]["seconds"] == expected


@pytest.mark.parametrize(
    "offense,defense,expected",
    [
        ("normal", "normal", 10),
        ("normal", "parenthesized", 30),
        ("parenthesized", "parenthesized", 10),
    ],
)
def test_priority_retains_or_replaces_oob_marker_without_parsing_stars(offense, defense, expected):
    actions = [("snap", ["1", "A"])]
    if expected > 10:
        actions.append(("decide", ["clock:runoff"]))
    row, frozen = sequence_receipt(
        clock=Clock(2, 110),
        oob=True,
        oob_roll=21,
        offensive_priority=offense,
        defensive_priority=defense,
        actions=actions,
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    assert command["after"]["view"]["timing_log"][-1]["seconds"] == expected


def test_turnover_on_downs_uses_ten_seconds_from_independent_short_fourth_down():
    actions = [
        pair for _ in range(3) for pair in [("snap", ["1", "A"]), ("decide", ["clock:runoff"])]
    ] + [("snap", ["1", "A"])]
    row, frozen = sequence_receipt(actions=actions)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    counts = result["standard_clock_counts"]
    assert (counts["checked"], counts["deferred"], counts["immediate"]) == (7, 3, 1)
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    assert command["before"]["view"]["state"]["down"] == 4
    assert command["after"]["view"]["timing_log"][-1]["seconds"] == 10


def test_zero_observed_commands_is_notrun_without_clock_authority():
    from tests.test_game_audit_row_links import frozen_inventory
    from tests.test_game_receipt_audit import receipt
    from tools.game_audit_capture import capture_receipts

    with capture_receipts(typed=True, lookup_rows=True) as capture:
        pass
    row = receipt()
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row, lookup_inventory=frozen_inventory())
    assert result["components"]["standard_clock"] == "NOTRUN"
    assert result["coverage"]["standard_clock"] == dict(checked=0, excluded=0, unknown=0)


def test_q4_expiring_deferred_play_keeps_terminal_authority_unknown():
    row, frozen = regulation_receipt(clock=Clock(4, 25))
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "UNVERIFIED"
    assert result["standard_clock_counts"]["checked"] == 0
    assert result["standard_clock_counts"]["unknown_reasons"] == {"Q4_terminal_authority": 1}


@pytest.mark.parametrize(
    "field,value", [("bounds_declaration", ""), ("overtime", False), ("overtime", {})]
)
def test_falsy_after_context_cannot_mint_supported_absence(field, value):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"][field] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("endpoint", ["before", "after"])
@pytest.mark.parametrize("field", ["armed_timeout", "overtime", "bounds_declaration"])
def test_missing_required_optional_context_is_not_observed_none(endpoint, field):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0][endpoint]["view"].pop(field)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field,value", [("bounds_declaration", ""), ("overtime", False), ("armed_timeout", False)]
)
def test_malformed_before_optional_context_is_not_unsupported_valid_context(field, value):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"][field] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field,value",
    [("bounds_declaration", "out_of_bounds"), ("overtime", {}), ("armed_timeout", "home")],
)
def test_structured_unsupported_before_context_remains_unverified(field, value):
    row, frozen = regulation_receipt()
    row["audit_capture"]["typed_capture"]["commands"][0]["before"]["view"][field] = value
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "UNVERIFIED"
    assert result["standard_clock_counts"]["checked"] == 0
    assert result["standard_clock_counts"]["unknown"] == 1
