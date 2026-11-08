"""Routine kickoff state/stat/clock subjects with literal external typed facts."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.save_game import SavedGame
from bowl_bound.timing import Clock
from tests.test_game_audit_row_links import frozen_inventory, subject_teams
from tests.test_game_audit_typed_capture import fixed_save_clock as fixed_save_clock
from tests.test_game_receipt_audit import receipt
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_capture import capture_receipts


def kickoff_subject(
    *,
    season=2007,
    away_season=None,
    chooser="home",
    choice="toss:receive",
    flight=50,
    return_yards=12,
    finish=None,
    after_snap=False,
    kick_roll=None,
    return_roll=None,
    patterned=False,
    reload_pending=False,
    return_game=False,
    observe=True,
    no_change_roles=(),
    recovery_roll=None,
    recovery_return_roll=None,
    return_teams=False,
):
    """Real public commands; wrapper is partial, never an actual final-game claim."""
    seasons = dict(home=season, away=season if away_season is None else away_season)
    special = dict(
        kickoff=flight,
        kickoff_return=return_yards,
        punt=4,
        punt_return=5,
        field_goal=6,
        interception_return=7,
    )

    def special_yards(column, total):
        if patterned and column == "kickoff":
            return 40 + total % 7
        if patterned and column == "kickoff_return":
            return 8 + total % 5
        return special[column]

    from bowl_bound.models import ResultKind

    teams = tuple(
        replace(
            team,
            season=seasons[side],
            special_teams=tuple(
                replace(
                    record,
                    cell=(
                        replace(record.cell, kind=ResultKind.NO_CHANGE, yards=None)
                        if record.column.value in no_change_roles
                        else replace(
                            record.cell, yards=special_yards(record.column.value, record.roll)
                        )
                    ),
                )
                for record in team.special_teams
            ),
        )
        for side, team in zip(("home", "away"), subject_teams(), strict=True)
    )
    toss = [OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]
    if chooser == "away":
        toss.reverse()
    rolls = toss + [OffensiveRoll(2, 0, 1) if kick_roll is None else kick_roll]
    if finish is None:
        rolls += [OffensiveRoll(3, 0, 2) if return_roll is None else return_roll]
    if after_snap:
        rolls += [OffensiveRoll(2, 0, 2), DefensiveRoll(1, 0)]
    if reload_pending or return_game or recovery_roll is not None:
        rolls.append(OffensiveRoll(1, 0, 0) if recovery_roll is None else recovery_roll)
        if recovery_return_roll is not None:
            rolls.append(recovery_return_roll)
        rolls += [DefensiveRoll(1, 0), OffensiveRoll(2, 1, 0)]
    game = SavedGame.new(
        *teams,
        home_id=f"{season}/home",
        away_id=f"{seasons['away']}/away",
        seed=37,
        coach_seed=41,
        mode="regulation",
        advanced_ii=False,
        clock=Clock(1, 900, (1, 2)),
        dice=ScriptedDice(rolls),
    )
    from contextlib import nullcontext

    with (
        capture_receipts(typed=True, lookup_rows=True) if observe else nullcontext(None)
    ) as capture:
        game.decide(choice)
        game.kick("kickoff")
        if reload_pending:
            from bowl_bound.save_game import dumps_game, loads_game

            saved = dumps_game(game)
            game = loads_game(
                saved,
                lambda key: dict(
                    zip((f"{season}/home", f"{seasons['away']}/away"), teams, strict=True)
                )[key],
            )
            assert dumps_game(game) == saved
        if finish is not None:
            game.decide(finish)
        if after_snap:
            game.snap("1", "A")
    if return_game:
        return game, capture.payload() if capture is not None else None
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
    for team in frozen["teams"]:
        side = team["team_id"].split("/")[-1]
        team.update(team_id=f"{seasons[side]}/{side}", season=seasons[side])
    for record in frozen["cells"]:
        address = record["address"]
        side = address["team_id"].split("/")[-1]
        address.update(team_id=f"{seasons[side]}/{side}", season=seasons[side])
        if address["table"] == "special_teams":
            record["facts"]["yards"] = special_yards(address["column"], address["roll"])
            if address["column"] in no_change_roles:
                record["facts"].update(kind="no_change", yards=None)
    return (row, frozen, teams) if return_teams else (row, frozen)


@pytest.mark.parametrize(
    "chooser,choice",
    [
        ("home", "toss:receive"),
        ("home", "toss:kick"),
        ("away", "toss:receive"),
        ("away", "toss:kick"),
    ],
)
def test_routine_opening_return_and_following_snap_gain_checked_chain(chooser, choice):
    row, frozen = kickoff_subject(chooser=chooser, choice=choice, after_snap=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "GO"
    assert result["components"]["standard_clock"] == "GO"
    assert result["kickoff_counts"]["returned"] == 1
    assert result["kickoff_counts"]["opening_authority"] == "UNVERIFIED"
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "kicker",
        "goal",
        "down",
        "distance",
        "opening-kicker",
        "phase",
        "clock",
        "timeouts",
    ],
)
def test_ignored_opening_transition_corruption_refuses(fault):
    row, frozen = kickoff_subject()
    view = row["audit_capture"]["typed_capture"]["commands"][0]["after"]["view"]
    if fault == "kicker":
        view["state"]["possession"] = "home"
    elif fault in {"goal", "down", "distance"}:
        key = dict(goal="yards_to_goal", down="down", distance="yards_to_go")[fault]
        view["state"][key] += 1
    elif fault == "opening-kicker":
        view["opening_kicker"] = "home"
    elif fault == "phase":
        view["phase"] = "scrimmage"
    elif fault == "clock":
        view["clock"]["remaining"] -= 1
    else:
        view["clock"]["timeouts"] = [3, 3]
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "fault",
    [
        "receiver",
        "goal",
        "down",
        "distance",
        "seconds",
        "remaining",
        "missing-charge",
        "duplicate-charge",
        "timeout-mirror",
        "finished",
        "phase",
    ],
)
def test_ignored_returned_kickoff_live_state_and_clock_corruption_refuses(fault):
    row, frozen = kickoff_subject()
    view = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    if fault == "receiver":
        view["state"]["possession"] = "away"
    elif fault in {"goal", "down", "distance"}:
        view["state"][dict(goal="yards_to_goal", down="down", distance="yards_to_go")[fault]] += 1
    elif fault == "seconds":
        view["timing_log"][-1]["seconds"] = 0
    elif fault == "remaining":
        view["clock"]["remaining"] = 900
    elif fault == "missing-charge":
        view["timing_log"].pop()
    elif fault == "duplicate-charge":
        view["timing_log"].append(deepcopy(view["timing_log"][-1]))
    elif fault == "timeout-mirror":
        view["home_timeouts"] = 3
    elif fault == "finished":
        view["finished"] = True
    else:
        view["phase"] = "kickoff"
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def change_last_committed_report(row, alter):
    from tests.test_game_audit_ordinary_commitment import log_digest

    commands = row["audit_capture"]["typed_capture"]["commands"]
    command = commands[-1]
    report = command["report_changes"][0]["after"]
    alter(report, command)
    command["returned_report"] = deepcopy(report)
    command["report_revisions"] = [deepcopy(report)]
    reports = deepcopy(commands[0]["initial_log"])
    for current in commands:
        for change in current["report_changes"]:
            if change["before"] is None:
                reports.append(deepcopy(change["after"]))
            else:
                reports[change["index"]] = deepcopy(change["after"])
    command["after"]["log_sha256"] = log_digest(reports)


@pytest.mark.parametrize(
    "fault", ["called", "resolved", "outcome", "yards", "credit", "report-goal", "timing"]
)
def test_kickoff_inner_report_core_is_independently_checked(fault):
    row, frozen = kickoff_subject()

    def alter(report, command):
        if fault in {"called", "resolved"}:
            report[fault + "_play"] = "Punt"
        elif fault == "outcome":
            report["outcome"] = "touchback"
        elif fault == "yards":
            report["yards"] = 12
        elif fault == "credit":
            report["statistics"]["yards"] = 1
        elif fault == "report-goal":
            report["state_after"]["yards_to_goal"] += 1
        else:
            report["timing"]["unreturned_kickoff"] = True

    change_last_committed_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("landing", [1, 0, -9, -10, -11])
def test_literal_goal_and_endline_kickoff_boundaries(landing):
    row, frozen = kickoff_subject(
        flight=70 - landing, finish="kick:touchback" if -9 <= landing <= 0 else None
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "GO"
    assert result["components"]["standard_clock"] == "GO"
    counts = result["kickoff_counts"]
    assert counts["returned"] == int(landing == 1)
    assert counts["touchbacks"] == int(landing <= 0)
    assert counts["pending"] == int(-9 <= landing <= 0)
    after = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    assert after["state"]["yards_to_goal"] == (87 if landing == 1 else 80)
    assert after["clock"]["remaining"] == (890 if landing == 1 else 900)


@pytest.mark.parametrize("endpoint,expected", [(0, "UNVERIFIED"), (1, "GO"), (99, "GO")])
def test_return_goal_endpoints_are_not_guessed_from_numeric_cell(endpoint, expected):
    row, frozen = kickoff_subject(return_yards=endpoint - 20)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == expected
    assert result["components"]["standard_clock"] == expected
    assert result["kickoff_counts"]["checked"] == int(expected == "GO")
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize(
    "home_year,away_year,origin,touchback",
    [
        (1985, 2012, 40, 20),
        (1986, 2007, 35, 20),
        (2007, 1985, 30, 20),
        (2011, 2012, 30, 20),
        (2012, 2011, 35, 25),
        (2023, 2002, 35, 25),
    ],
)
def test_mixed_home_year_selects_kick_origin_and_free_kick_touchback(
    home_year, away_year, origin, touchback
):
    row, frozen = kickoff_subject(
        season=home_year, away_season=away_year, flight=100 - origin + 3, finish="kick:touchback"
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "GO"
    commands = row["audit_capture"]["typed_capture"]["commands"]
    assert commands[0]["after"]["view"]["state"]["yards_to_goal"] == 100 - origin
    assert commands[-1]["after"]["view"]["state"]["yards_to_goal"] == 100 - touchback
    assert result["full_play_by_play_qualification"] is False


def test_scoring_return_is_unknown_in_kickoff_consumer_before_outer_full_game_fold():
    from tools.game_audit_kickoff import audit_kickoff_commands
    from tools.game_audit_lookup import LookupInventory

    row, frozen = kickoff_subject(return_yards=80)
    result = audit_kickoff_commands(row["audit_capture"], inventory=LookupInventory(frozen))
    assert result["checked"] == 0
    assert result["unknown"] == 1
    assert result["opening_authority"] == "UNVERIFIED"


@pytest.mark.parametrize(
    "fault", ["pending-clock", "pending-field", "pending-credit", "pending-flag", "chooser"]
)
def test_uncommitted_kick_retains_zero_effect_and_receiving_chooser(fault):
    row, frozen = kickoff_subject(flight=75, finish="kick:touchback")
    command = row["audit_capture"]["typed_capture"]["commands"][1]
    after = command["after"]["view"]
    report = command["returned_report"]
    if fault == "pending-clock":
        after["clock"]["remaining"] -= 10
    elif fault == "pending-field":
        report["state_after"]["yards_to_goal"] = 80
    elif fault == "pending-credit":
        report["statistics"]["yards"] = 1
    elif fault == "pending-flag":
        report["pending"] = False
    else:
        after["pending"].update(chooser_side="away", chooser="Away")
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("role", ["kickoff", "kickoff_return"])
def test_bound_but_wrong_side_chart_cannot_supply_ordinary_kick_role(role):
    row, frozen = kickoff_subject()
    events = row["audit_capture"]["lookup_rows"]["events"]
    selected = next(event for event in events if event["address"]["column"] == role)
    selected["address"]["team_id"] = "2007/home" if role == "kickoff" else "2007/away"
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field,value",
    [
        ("rules_season", True),
        ("rules_season", 2012),
        ("finished", 0),
        ("kickoff_penalties", None),
        ("kickoff_penalties", False),
        ("overtime", False),
        ("untimed_down", 0),
    ],
)
def test_normal_kickoff_context_uses_strict_domains_and_pinned_home_year(field, value):
    row, frozen = kickoff_subject()
    row["audit_capture"]["typed_capture"]["commands"][1]["before"]["view"][field] = value
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize(
    "field,value",
    [("hurried", True), ("untimed_down", True), ("bounds_declaration", "out_of_bounds")],
)
def test_known_unsupported_kick_context_taints_and_never_reanchors(field, value):
    row, frozen = kickoff_subject(after_snap=True)
    row["audit_capture"]["typed_capture"]["commands"][1]["before"]["view"][field] = value
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "UNVERIFIED"
    assert result["components"]["standard_clock"] == "UNVERIFIED"
    assert result["kickoff_counts"]["checked"] == 0
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize("finish", [None, "kick:touchback"])
def test_checked_kickoff_endpoints_link_next_ordinary_command(finish):
    row, frozen = kickoff_subject(flight=75 if finish else 50, finish=finish, after_snap=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    counts = result["ordinary_continuity_counts"]
    assert counts["qualified_kickoff_endpoints"] == (3 if finish else 2)
    assert counts["boundary_links"] == (3 if finish else 2)
    assert counts["unknown"] == 0
    assert counts["initial_anchor_truth"] == "UNVERIFIED"


@pytest.mark.parametrize("field", ["state", "statistics", "score", "scoring"])
def test_next_command_cannot_rewrite_checked_kickoff_endpoint(field):
    row, frozen = kickoff_subject(after_snap=True)
    before = row["audit_capture"]["typed_capture"]["commands"][-1]["before"]["view"]
    if field == "state":
        before[field]["yards_to_goal"] += 1
    elif field == "statistics":
        before[field]["home"]["rushing_yards"] += 1
    elif field == "score":
        before[field]["home"] += 1
    else:
        before[field].append(dict(team="Home", points=3, quarter=1))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_unsupported_kickoff_context_cannot_reanchor_continuity():
    row, frozen = kickoff_subject(after_snap=True)
    row["audit_capture"]["typed_capture"]["commands"][1]["before"]["view"]["hurried"] = True
    result = audit_receipt(row, lookup_inventory=frozen)
    counts = result["ordinary_continuity_counts"]
    assert counts["qualified_kickoff_endpoints"] == 1
    assert counts["qualified_ordinary_endpoints"] == 0
    assert counts["unknown"] > 0


@pytest.mark.parametrize("role", ["kickoff", "kickoff_return"])
def test_all_216_physical_offensive_combinations_use_dedicated_patterned_role(role):
    from collections import Counter
    from itertools import product

    # Independent literal face multiplicities, not imported engine distributions.
    outcomes = Counter()
    for faces in product((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5)):
        roll = OffensiveRoll(*faces)
        total = 10 * faces[0] + faces[1] + faces[2]
        kick_total, return_total = (total, 32) if role == "kickoff" else (21, total)
        expected_goal = 100 - (70 - (40 + kick_total % 7) + 8 + return_total % 5)
        row, frozen = kickoff_subject(
            patterned=True,
            kick_roll=roll if role == "kickoff" else None,
            return_roll=roll if role == "kickoff_return" else None,
        )
        result = audit_receipt(row, lookup_inventory=frozen)
        assert result["components"]["ordinary_kickoff_commitment"] == "GO"
        assert result["kickoff_counts"]["returned"] == 1
        assert result["components"]["standard_clock"] == "GO"
        final = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
        assert final["state"]["yards_to_goal"] == expected_goal
        assert final["clock"]["remaining"] == 890
        outcomes[expected_goal] += 1
    assert sum(outcomes.values()) == 216
    assert len(outcomes) > 1
    assert len(set(outcomes.values())) > 1  # Not a uniform-total stand-in.


def test_restored_pending_kick_does_not_invent_same_object_retained_authority(fixed_save_clock):
    row, frozen = kickoff_subject(flight=75, finish="kick:touchback", reload_pending=True)
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "UNVERIFIED"
    counts = result["kickoff_counts"]
    assert counts["pending"] == 1
    assert counts["committed"] == 0
    assert counts["unknown_reasons"] == {"unbound_initial_pending_kick": 1}
    assert result["components"]["standard_clock"] == "UNVERIFIED"


def test_carried_foul_is_unknown_before_standard_origin_arithmetic():
    row, frozen = kickoff_subject()
    before = row["audit_capture"]["typed_capture"]["commands"][1]["before"]["view"]
    before["kickoff_penalties"] = [{"team": "away", "yards": 5}]
    before["state"]["yards_to_goal"] -= 5
    # Exercise the specific oracle; continuity would correctly reject the
    # separately unmodified preceding opening endpoint in this fault fixture.
    from tools.game_audit_kickoff import audit_kickoff_commands
    from tools.game_audit_lookup import LookupInventory

    result = audit_kickoff_commands(row["audit_capture"], inventory=LookupInventory(frozen))
    assert result["checked"] == 0
    assert result["unknown_reasons"] == {"carried_kickoff_foul_authority": 1}


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "chooser",
        "chooser-label",
        "missing-touchback",
        "disabled-touchback",
        "boolean-enabled",
    ],
)
def test_retained_touchback_must_have_the_checked_receiving_chooser(fault):
    row, frozen = kickoff_subject(flight=75, finish="kick:touchback")
    before = row["audit_capture"]["typed_capture"]["commands"][-1]["before"]["view"]
    if fault == "missing":
        before.pop("pending")
    elif fault == "chooser":
        before["pending"]["chooser_side"] = "away"
    elif fault == "chooser-label":
        before["pending"]["chooser"] = "Away"
    elif fault == "missing-touchback":
        before["pending"]["choices"] = before["pending"]["choices"][1:]
    else:
        before["pending"]["choices"][0]["enabled"] = 1 if fault == "boolean-enabled" else False
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("endpoint", ["before", "after"])
def test_normal_kickoff_pending_key_is_required_even_for_null(endpoint):
    row, frozen = kickoff_subject()
    row["audit_capture"]["typed_capture"]["commands"][-1][endpoint]["view"].pop("pending")
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("fault", ["wrong-id", "extra-append"])
def test_pending_commit_retains_identity_and_single_append(fault):
    row, frozen = kickoff_subject(flight=75, finish="kick:touchback")

    def alter(report, command):
        if fault == "wrong-id":
            report["number"] += 1
        else:
            command["report_changes"].append(deepcopy(command["report_changes"][0]))

    change_last_committed_report(row, alter)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


def test_unique_home_year_comes_only_from_complete_detached_metadata():
    from tools.game_audit_lookup import LookupInventory

    frozen = frozen_inventory()
    inventory = LookupInventory(frozen)
    assert inventory.unique_season("2002/home") == 2002
    assert inventory.unique_season("2007/missing") is None
    duplicate = deepcopy(frozen)
    duplicate["teams"] += [dict(team_id="2002/home", season=2012)]
    extra = []
    for record in duplicate["cells"]:
        if record["address"]["team_id"] == "2002/home":
            second = deepcopy(record)
            second["address"]["season"] = 2012
            extra.append(second)
    duplicate["cells"] += extra
    ambiguous = LookupInventory(duplicate)
    assert ambiguous.unique_season("2002/home") is None
    duplicate["teams"][0]["season"] = True
    assert inventory.unique_season("2002/home") == 2002
    from tools.game_audit_lookup import LookupEvidenceError

    with pytest.raises(LookupEvidenceError, match="identity"):
        LookupInventory(duplicate)


@pytest.mark.parametrize(
    "flight,finish", [(50, None), (75, None), (80, None), (75, "kick:touchback")]
)
def test_routine_and_pending_kickoff_capture_preserves_exact_save_and_journal(
    fixed_save_clock, flight, finish
):
    from bowl_bound.save_game import dumps_game

    ordinary, _ = kickoff_subject(flight=flight, finish=finish, return_game=True, observe=False)
    subject, captured = kickoff_subject(flight=flight, finish=finish, return_game=True)
    assert subject.view() == ordinary.view()
    assert subject._commands == ordinary._commands
    assert subject._tape.rolls == ordinary._tape.rolls
    assert dumps_game(subject) == dumps_game(ordinary)
    assert captured["typed_capture"]["usable"] is True
    assert captured["lookup_rows"]["usable"] is True


@pytest.mark.parametrize("fault", ["reversed", "reused-draw", "missing-row", "duplicate-row"])
def test_dedicated_kickoff_lookup_order_and_exposure_cannot_be_substituted(fault):
    row, frozen = kickoff_subject()
    events = row["audit_capture"]["lookup_rows"]["events"]
    if fault == "reversed":
        events.reverse()
    elif fault == "reused-draw":
        events[1]["draw_binding"] = deepcopy(events[0]["draw_binding"])
    elif fault == "missing-row":
        events.pop()
    else:
        events.append(deepcopy(events[-1]))
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("opening", [False, True])
@pytest.mark.parametrize(
    "fault",
    [
        "missing-first",
        "missing-second",
        "disabled-first",
        "boolean-second",
        "duplicate-second",
        "extra-choice",
    ],
)
def test_normal_offers_have_unique_strictly_enabled_bb_choices(opening, fault):
    from tools.game_audit_kickoff import KickoffEvidenceError, audit_kickoff_commands
    from tools.game_audit_lookup import LookupInventory

    row, frozen = kickoff_subject(flight=75, finish="kick:touchback")
    commands = row["audit_capture"]["typed_capture"]["commands"]
    view = commands[0]["before"]["view"] if opening else commands[1]["after"]["view"]
    choices = view["pending"]["choices"]
    if fault == "missing-first":
        choices.pop(0)
    elif fault == "missing-second":
        choices.pop()
    elif fault == "disabled-first":
        choices[0]["enabled"] = False
    elif fault == "boolean-second":
        choices[1]["enabled"] = 1
    elif fault == "duplicate-second":
        choices.append(deepcopy(choices[1]))
    else:
        choices.append(dict(id="kick:punt", enabled=True))
    # Direct pending component avoids relying on outer empty-log refusal.
    # Opening controls additionally run through the complete receipt wrapper.
    with pytest.raises(KickoffEvidenceError):
        audit_kickoff_commands(row["audit_capture"], inventory=LookupInventory(frozen))
    if opening:
        with pytest.raises(ReceiptAuditError):
            audit_receipt(row, lookup_inventory=frozen)


@pytest.mark.parametrize("fault", ["no-change-fixed-yards", "orphan-multiplier"])
def test_supported_numeric_kick_role_does_not_ignore_contradictory_typed_fields(fault):
    from tools.game_audit_kickoff import KickoffEvidenceError, audit_kickoff_commands
    from tools.game_audit_lookup import LookupInventory

    row, frozen = kickoff_subject(flight=0 if fault == "no-change-fixed-yards" else 50)
    fact = row["audit_capture"]["lookup_rows"]["events"][0]["facts"]
    if fault == "no-change-fixed-yards":
        fact.update(kind="no_change", yards=9)
    else:
        fact["variable_multiplier"] = 3
    # A structural inventory can retain this contradictory typed shape; this
    # oracle must not silently coerce it into its ordinary numeric population.
    with pytest.raises(KickoffEvidenceError):
        audit_kickoff_commands(row["audit_capture"], inventory=LookupInventory(frozen))


@pytest.mark.parametrize("role", ["kickoff", "kickoff_return"])
def test_actual_no_change_role_uses_zero_with_null_fixed_yardage(role):
    row, frozen = kickoff_subject(
        flight=0 if role == "kickoff" else 50,
        return_yards=0 if role == "kickoff_return" else 12,
        no_change_roles=(role,),
    )
    result = audit_receipt(row, lookup_inventory=frozen)
    assert result["components"]["ordinary_kickoff_commitment"] == "GO"
    assert result["components"]["standard_clock"] == "GO"
    after = row["audit_capture"]["typed_capture"]["commands"][-1]["after"]["view"]
    assert after["state"]["yards_to_goal"] == (18 if role == "kickoff" else 80)


@pytest.mark.parametrize("opening", [False, True])
def test_duplicate_offer_ids_cannot_replace_other_role_at_exact_cardinality(opening):
    from tools.game_audit_kickoff import KickoffEvidenceError, audit_kickoff_commands
    from tools.game_audit_lookup import LookupInventory

    row, frozen = kickoff_subject(flight=75, finish="kick:touchback")
    commands = row["audit_capture"]["typed_capture"]["commands"]
    view = commands[0]["before"]["view"] if opening else commands[1]["after"]["view"]
    choices = view["pending"]["choices"]
    choices[0] = deepcopy(choices[1])
    assert len(choices) == 2
    with pytest.raises(KickoffEvidenceError, match="unique offered choices"):
        audit_kickoff_commands(row["audit_capture"], inventory=LookupInventory(frozen))
