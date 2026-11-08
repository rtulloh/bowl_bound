"""Synthetic conditional charts; engine observations are subjects, never oracles."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import ChartColor, NormalizedCell, Priority, ResultKind
from bowl_bound.save_game import SavedGame
from tests.test_game_audit_ordinary_commitment import change_report
from tests.test_game_audit_row_links import frozen_inventory, subject_teams
from tests.test_game_receipt_audit import receipt
from tests.test_models import provenance
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_capture import capture_receipts


def subject_receipt(
    *,
    chain=("B",),
    terminal=3,
    play="9",
    defense=-1,
    option=None,
    spot=65,
    side="home",
    down=1,
    distance=None,
    clock=None,
    runoff=False,
    initial_fact=None,
    defense_fact=None,
    terminal_oob=False,
    defense_oob=False,
    allow_failure=False,
    last_roll=None,
    initial_priority="normal",
    after_actions=(),
    repeat=1,
    recovery_roll=None,
    recovery_return_roll=None,
    return_teams=False,
):
    """Literal independent table edits, including distinct repeated-column totals."""
    edits = {("offense", int(play), 21): initial_fact or (option or chain[0], None)}
    if option:
        edits[("offense", 7 if option == "SOP" else 8, 20)] = (chain[0], None)
    for index, column in enumerate(chain):
        value = chain[index + 1] if index + 1 < len(chain) else terminal
        total = (
            last_roll.black * 10 + last_roll.white_one + last_roll.white_two
            if last_roll is not None and index == len(chain) - 1
            else 30 + index
        )
        edits[("supplemental", column, total)] = (
            value
            if type(value) is tuple
            else ("yards", value)
            if type(value) is int
            else (value, None)
        )

    def selected(table, record):
        key = (table, record.play.value if table == "offense" else record.column.value, record.roll)
        kind, yards = edits.get(key, ("yards", 0))
        return replace(
            record,
            cell=NormalizedCell(
                ResultKind(kind),
                provenance(),
                yards=yards,
                chart_color=ChartColor.WHITE,
                priority=Priority(initial_priority)
                if key == ("offense", int(play), 21)
                else Priority.NORMAL,
                out_of_bounds=terminal_oob
                and table == "supplemental"
                and key == ("supplemental", chain[-1], 29 + len(chain)),
            ),
        )

    teams = tuple(
        replace(
            team,
            offense=tuple(selected("offense", record) for record in team.offense),
            supplemental=tuple(selected("supplemental", record) for record in team.supplemental),
            defense=tuple(
                replace(
                    record,
                    cell=NormalizedCell(
                        ResultKind(defense_fact[0]) if defense_fact else ResultKind.YARDS,
                        provenance(),
                        yards=defense_fact[1] if defense_fact else defense,
                        priority=Priority(defense_fact[2]) if defense_fact else Priority.NORMAL,
                        out_of_bounds=defense_oob,
                        chart_color=ChartColor.WHITE,
                    ),
                )
                for record in team.defense
            ),
            special_teams=tuple(
                replace(record, cell=replace(record.cell, yards=65))
                if record.column.value == "kickoff" and clock is not None
                else record
                for record in team.special_teams
            ),
        )
        for team in subject_teams()
    )
    draws = [OffensiveRoll(2, 0, 1), DefensiveRoll(1, 0)]
    if option:
        draws.append(OffensiveRoll(2, 0, 0))
    draws.extend(OffensiveRoll(3, min(i, 4), max(0, i - 4)) for i in range(len(chain)))
    if last_roll is not None:
        draws[-1] = last_roll
    if recovery_roll is not None:
        draws.append(recovery_roll)
    if recovery_return_roll is not None:
        draws.append(recovery_return_roll)
    draws = [replace(draw) for _ in range(repeat) for draw in draws]
    if clock is not None:
        draws = [OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)] + draws
    if after_actions:
        draws += [OffensiveRoll(2, 0, 0) for _ in range(4)]
    subject = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="regulation" if clock is not None else "drive",
        advanced_ii=False,
        start_yards_to_goal=spot,
        dice=ScriptedDice(draws),
        clock=clock,
    )
    if clock is not None:
        from tests.test_save_game import opening

        opening(subject)
    from bowl_bound.game_state import FieldState, Possession

    # Literal initial supplied anchor, not reconstructed pre-window history.
    session = subject._engine._session if clock is not None else subject._engine
    session._field = FieldState(Possession(side), spot, down, distance or min(10, spot))
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        if allow_failure:
            try:
                subject.snap(play, "A")
            except ValueError:
                pass  # The producer must retain failed attempts and all consumed draws.
        else:
            for _ in range(repeat):
                subject.snap(play, "A")
        if runoff:
            subject.decide("clock:runoff")
        for operation, arguments in after_actions:
            getattr(subject, operation)(*arguments)
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
    for item in frozen["cells"]:
        address = item["address"]
        table = address["table"]
        if table == "defense":
            item["facts"].update(
                kind=defense_fact[0] if defense_fact else "yards",
                yards=defense_fact[1] if defense_fact else defense,
                priority=defense_fact[2] if defense_fact else "normal",
                out_of_bounds=defense_oob,
            )
        elif table in {"offense", "supplemental"}:
            key = (
                table,
                address["play"] if table == "offense" else address["column"],
                address["roll"],
            )
            kind, yards = edits.get(key, ("yards", 0))
            item["facts"].update(kind=kind, yards=yards)
            if key == ("offense", int(play), 21):
                item["facts"]["priority"] = initial_priority
            item["facts"]["out_of_bounds"] = terminal_oob and key == (
                "supplemental",
                chain[-1],
                29 + len(chain),
            )
        elif table == "special_teams" and address["column"] == "kickoff" and clock is not None:
            item["facts"]["yards"] = 65
    return (row, frozen, teams) if return_teams else (row, frozen)


@pytest.mark.parametrize(
    "chain,terminal,play,option,category,yards",
    [
        (("B",), 3, "1", None, "rush", 2),
        (("B",), 3, "9", None, "completion", 2),
        (("QR",), -3, "9", None, "rush", -4),
        (("QT",), -3, "9", None, "sack", -3),
        (("QT",), 0, "9", None, "rush", 0),
        (("QT",), 3, "9", None, "rush", 3),
        (("QR", "B"), -3, "9", None, "rush", -4),
        (("QT", "B"), -3, "9", None, "sack", -3),
        (("B", "QT", "B"), 3, "9", None, "rush", 3),
        (("B", "QR"), -3, "9", None, "rush", -4),
        (("B",), 3, "5", "SOP", "completion", 3),
        (("B",), 3, "5", "BLP", "completion", 3),
        (("QR",), -3, "5", "SOP", "rush", -3),
        (("QT", "B"), -3, "5", "BLP", "sack", -3),
    ],
)
def test_numeric_chains_have_independently_derived_terminal_authority(
    chain, terminal, play, option, category, yards
):
    row, frozen = subject_receipt(chain=chain, terminal=terminal, play=play, option=option)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["supplemental_commitment"] == "GO"
    counts = result["supplemental_commitment_counts"]
    assert counts["checked"] == counts["report_checked"] == 1
    assert counts[category] == 1
    assert counts["dispositions"][0]["derived_yards"] == yards
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
        "credit-td",
        "box-home",
        "box-away",
        "score",
        "outcome",
        "timing-rush",
        "timing-complete",
        "pending",
        "unsupported",
    ],
)
def test_terminal_corruption_cannot_escape_as_unsupported_or_opaque_history(mutation):
    row, frozen = subject_receipt(chain=("QT", "B"), terminal=-3)

    def alter(report, command):
        if mutation in {"goal", "down", "distance", "owner"}:
            key, value = {
                "goal": ("yards_to_goal", 61),
                "down": ("down", 3),
                "distance": ("yards_to_go", 7),
                "owner": ("possession", "away"),
            }[mutation]
            report["state_after"][key] = value
            command["after"]["view"]["state"][key] = value
        elif mutation in {"called", "resolved"}:
            report[mutation + "_play"] = "Counter"
        elif mutation == "gain":
            report["yards"] = -4
        elif mutation == "credit-kind":
            report["statistics"]["kind"] = "completion"
        elif mutation == "credit-yards":
            report["statistics"]["yards"] = -4
        elif mutation == "credit-td":
            report["statistics"]["touchdown"] = True
        elif mutation.startswith("box-"):
            command["after"]["view"]["statistics"][mutation[4:]]["total_yards"] += 1
        elif mutation == "score":
            command["after"]["view"]["score"]["home"] += 1
        elif mutation == "outcome":
            report["outcome"] = "first_down"
        elif mutation == "timing-rush":
            report["timing"]["rushing"] = False
        elif mutation == "timing-complete":
            report["timing"]["completed_pass"] = True
        elif mutation == "pending":
            report["pending"] = True
        elif mutation == "unsupported":
            report["supported"] = False

    change_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_canceled_defense_never_resurrects_after_qt_then_breakaway():
    row, frozen = subject_receipt(chain=("B", "QT", "B"), terminal=3, defense=-4)
    result = audit_receipt(row, lookup_inventory=frozen)
    detail = result["supplemental_commitment_counts"]["dispositions"][0]
    assert detail["derived_yards"] == 3
    assert detail["derived_category"] == "rush"
    assert len(row["audit_capture"]["typed_capture"]["draws"]) == 5


def test_option_called_and_resolved_family_cannot_be_coherently_erased():
    row, frozen = subject_receipt(play="5", option="SOP")
    change_report(row, lambda report, command: report.update(resolved_play="Option"))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_last_qr_not_original_pass_controls_terminal_credit():
    row, frozen = subject_receipt(chain=("QT", "QR", "B"), terminal=-3)
    change_report(row, lambda report, command: report["statistics"].update(kind="sack"))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "flag", ["incomplete", "first_down", "change_of_possession", "scoring", "out_of_bounds"]
)
def test_actual_terminal_timing_flags_are_independently_checked(flag):
    row, frozen = subject_receipt(chain=("QR",), terminal=3)
    change_report(row, lambda report, command: report["timing"].update({flag: True}))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_regulation_supplemental_duration_is_bound_to_independent_terminal_facts():
    from bowl_bound.timing import Clock

    row, frozen = subject_receipt(clock=Clock(1, 300), runoff=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["standard_clock"] == "GO"
    assert result["standard_clock_counts"]["checked"] == 2
    assert result["standard_clock_counts"]["runoff"] == 1
    assert result["components"]["ordinary_continuity"] == "GO"


@pytest.mark.parametrize("fault", ["seconds", "reference", "remaining", "missing", "duplicate"])
def test_supplemental_deferred_charge_corruptions_refuse(fault):
    from bowl_bound.timing import Clock

    row, frozen = subject_receipt(clock=Clock(1, 300), runoff=True)
    after = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    ledger = after["timing_log"]
    if fault == "seconds":
        ledger[-1]["seconds"] = 20
    elif fault == "reference":
        ledger[-1]["play_number"] += 1
    elif fault == "remaining":
        after["clock"]["remaining"] -= 1
    elif fault == "missing":
        ledger.pop()
    else:
        ledger.append(deepcopy(ledger[-1]))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize(
    "chain,terminal,spot,down,distance,category,gain,outcome,state,credit",
    [
        (("B",), 3, 12, 4, 2, "completion", 2, "first_down", (10, 1, 10), 2),
        (("B",), 2, 12, 4, 2, "completion", 1, "turnover_on_downs", (89, 1, 10), 1),
        (("QR",), -3, 5, 2, 5, "rush", -4, "advance", (9, 3, 9), -4),
        (("QT",), -3, 5, 2, 5, "sack", -3, "advance", (8, 3, 8), -3),
        (("B",), "incomplete", 12, 1, 10, "incomplete", 0, "advance", (12, 2, 10), 0),
        (("B",), "no_change", 12, 1, 10, "completion", -1, "advance", (13, 2, 11), -1),
        (("B",), "touchdown", 12, 1, 10, "completion", 0, "touchdown", None, 12),
        (("QR",), 100, 12, 1, 10, "rush", 99, "touchdown", None, 12),
        (("B",), 13, 12, 1, 10, "completion", 12, "touchdown", None, 12),
    ],
)
def test_mirrored_terminal_fields_clipping_and_categories(
    side, chain, terminal, spot, down, distance, category, gain, outcome, state, credit
):
    row, frozen = subject_receipt(
        chain=chain, terminal=terminal, side=side, spot=spot, down=down, distance=distance
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    detail = result["supplemental_commitment_counts"]["dispositions"][0]
    assert detail["status"] == "GO"
    assert (detail["derived_yards"], detail["derived_category"]) == (gain, category)
    report = row["audit_capture"]["typed_capture"]["commands"][0]["returned_report"]
    assert report["outcome"] == outcome
    assert report["statistics"] == dict(
        kind=category, team=side, yards=credit, touchdown=state is None
    )
    if state is None:
        assert report["state_after"] is None
    else:
        final = report["state_after"]
        assert (final["yards_to_goal"], final["down"], final["yards_to_go"]) == state
        assert final["possession"] == (
            ("away" if side == "home" else "home") if outcome == "turnover_on_downs" else side
        )


@pytest.mark.parametrize("option", [None, "SOP", "BLP"])
def test_ten_supplemental_rerolls_do_not_include_option_redirect_budget(option):
    row, frozen = subject_receipt(
        chain=("B",) * 10, terminal=3, play="5" if option else "9", option=option
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["supplemental_commitment"] == "GO"
    typed = row["audit_capture"]["typed_capture"]
    assert len(typed["draws"]) == 12 + int(option is not None)
    assert len(row["audit_capture"]["lookup_rows"]["events"]) == 12 + int(option is not None)


def test_tenth_still_pending_consumes_no_eleventh_supplemental_draw():
    from tools.game_audit_supplemental import audit_supplemental_commitments

    row, _ = subject_receipt(chain=("B",) * 10, terminal="B", allow_failure=True)
    capture = row["audit_capture"]
    command = capture["typed_capture"]["commands"][0]
    assert command["exception_type"] == "ChartResolutionError"
    assert len(capture["typed_capture"]["draws"]) == len(capture["lookup_rows"]["events"]) == 12
    assert command["returned_report"] is None
    result = audit_supplemental_commitments(capture, typed_inventory_available=True)
    assert result["checked"] == 0 and result["unknown_reasons"] == {"failed_command": 1}


def test_selected_parenthesized_defensive_b_cancels_defense_for_new_support():
    row, frozen = subject_receipt(
        initial_fact=("yards", 4), defense_fact=("B", None, "parenthesized")
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    detail = result["supplemental_commitment_counts"]["dispositions"][0]
    assert detail["derived_yards"] == 3 and detail["derived_category"] == "completion"
    assert len(row["audit_capture"]["typed_capture"]["draws"]) == 3


@pytest.mark.parametrize("column", ["B", "QR", "QT"])
def test_numeric_defensive_oob_retention_is_distinct_from_marker_oob(column):
    row, frozen = subject_receipt(chain=(column,), defense_oob=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    detail = result["supplemental_commitment_counts"]["dispositions"][0]
    assert detail["status"] == "GO"
    assert detail["timing_facts"]["out_of_bounds"] is (column != "QT")


@pytest.mark.parametrize("column", ["B", "QR", "QT"])
def test_terminal_numeric_oob_survives_selected_priority(column):
    row, frozen = subject_receipt(chain=(column,), terminal_oob=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert (
        result["supplemental_commitment_counts"]["dispositions"][0]["timing_facts"]["out_of_bounds"]
        is True
    )


@pytest.mark.parametrize("column", ["B", "QR", "QT"])
def test_all_216_physical_supplemental_tuples_preserve_gain_and_explicit_class(column):
    from itertools import product

    checked = 0
    for black, white_one, white_two in product(
        (1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5)
    ):
        terminal = black * 10 + white_one + white_two - 25
        row, frozen = subject_receipt(
            chain=(column,), terminal=terminal, last_roll=OffensiveRoll(black, white_one, white_two)
        )
        result = audit_receipt(row, lookup_inventory=frozen)
        detail = result["supplemental_commitment_counts"]["dispositions"][0]
        gain = terminal if column == "QT" else terminal - 1
        category = (
            "sack" if column == "QT" and gain < 0 else "rush" if column != "B" else "completion"
        )
        assert (detail["status"], detail["derived_yards"], detail["derived_category"]) == (
            "GO",
            gain,
            category,
        )
        checked += 1
    assert checked == 216


def test_protected_offense_suppresses_defensive_b_without_supplemental_draw():
    row, frozen = subject_receipt(
        chain=(),
        initial_fact=("yards", 4),
        initial_priority="parenthesized",
        defense_fact=("B", None, "parenthesized"),
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_commitment"] == "GO"
    assert result["supplemental_commitment_counts"]["unknown_reasons"] == {
        "not_selected_supplemental": 1
    }
    assert len(row["audit_capture"]["typed_capture"]["draws"]) == 2


@pytest.mark.parametrize(
    "defense_fact", [("interception", 10, "normal"), ("touchdown", None, "normal")]
)
def test_option_redirect_cancels_initial_interception_or_td_defense(defense_fact):
    row, frozen = subject_receipt(play="5", option="SOP", defense_fact=defense_fact)
    result = audit_receipt(row, lookup_inventory=frozen)
    detail = result["supplemental_commitment_counts"]["dispositions"][0]
    assert (detail["status"], detail["derived_yards"], detail["derived_category"]) == (
        "GO",
        3,
        "completion",
    )


def test_checked_supplemental_td_can_precede_routine_conversion_and_kickoff():
    from bowl_bound.timing import Clock

    row, frozen = subject_receipt(
        terminal=7,
        spot=5,
        clock=Clock(1, 300),
        after_actions=[
            ("decide", ["conversion:kick"]),
            ("kick", ["kickoff"]),
            ("decide", ["kick:touchback"]),
        ],
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "GO"
    assert result["components"]["standard_clock"] == "GO"
    assert result["standard_clock_counts"]["checked"] == 4


@pytest.mark.parametrize("column", ["B", "QT"])
def test_later_same_object_supplemental_command_has_no_repeated_initial_log(column):
    row, frozen = subject_receipt(chain=(column,), repeat=2)
    commands = row["audit_capture"]["typed_capture"]["commands"]
    assert commands[0]["initial_log"] == [] and commands[1]["initial_log"] is None
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["supplemental_commitment"] == "GO"
    assert result["supplemental_commitment_counts"]["checked"] == 2
    assert result["components"]["ordinary_continuity"] == "GO"


def test_later_same_object_cannot_reuse_prior_observed_report_identity():
    from tests.test_game_audit_implicit_clock import change_last_report

    row, frozen = subject_receipt(repeat=2)
    first = row["audit_capture"]["typed_capture"]["commands"][0]["returned_report"]["number"]
    change_last_report(row, lambda report, command: report.update(number=first))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("prefix", ["scoring", "timing_log"])
def test_fresh_supplemental_report_cannot_reuse_supplied_ledger_reference(prefix):
    row, frozen = subject_receipt()
    command = row["audit_capture"]["typed_capture"]["commands"][0]
    number = command["returned_report"]["number"]
    entry = (
        dict(number=1, play_number=number, team="Home", kind="field_goal", points=3)
        if prefix == "scoring"
        else dict(
            play_number=number, quarter=1, before=300, seconds=30, after=270, method="standard"
        )
    )
    command["before"]["view"].setdefault(prefix, []).append(deepcopy(entry))
    command["after"]["view"].setdefault(prefix, []).append(deepcopy(entry))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_later_regulation_supplemental_uses_same_object_implicit_clock_chain():
    from bowl_bound.timing import Clock

    row, frozen = subject_receipt(clock=Clock(1, 300), repeat=2)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["supplemental_commitment"] == "GO"
    assert result["components"]["standard_clock"] == "GO"
    assert result["standard_clock_counts"]["checked"] == 2
    assert result["standard_clock_counts"]["implicit"] == 1
    assert result["components"]["ordinary_continuity"] == "GO"
