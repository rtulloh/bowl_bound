"""Independent fixed previous-spot penalty facts from supplied typed evidence.

Only the declared ordinary prepared path is closed here. Source truth, omitted
commands and complex prepared/period continuations remain separate authorities.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, cast

from . import game_audit_commitment as commitment
from . import game_audit_priority as priority


class PenaltyEvidenceError(ValueError):
    """Retained fixed-penalty evidence contradicts its independent expectation."""


def _require(value: bool, label: str) -> None:
    if not value:
        raise PenaltyEvidenceError("fixed previous penalty " + label)


def _equal(actual: Any, expected: Any, label: str) -> None:
    _require(commitment._canonical(actual) == commitment._canonical(expected), label)


def _origin(command: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    """Derive selected fixed fouls and retained operands before inspecting credit."""
    before = command["before"]["view"]
    if command["operation"] != "snap" or len(command["arguments"]) != 2:
        return dict(reason="not_penalty_origin")
    call, formation = command["arguments"]
    if call not in set("123456789") or formation not in set("ABCDEF"):
        return dict(reason="unsupported_origin_action")
    if (
        not commitment._ordinary_start(command)
        or before.get("bounds_declaration") is not None
        or before.get("overtime") is not None
        or before.get("hurried", False) is not False
        or before.get("untimed_down", False) is not False
        or before.get("conditional_timeout", False) is not False
        or before.get("armed_timeout") is not None
        or command["before"]["configuration"].get("mode") not in {"drive", "regulation"}
        or command["before"]["configuration"].get("advanced_ii") is not False
    ):
        return dict(reason="unsupported_origin_context")
    ps, pe = command["priority_range"]
    events = capture.get("priority", {}).get("events", [])[ps:pe]
    if not events:
        return dict(reason="no_selected_penalty")
    first = priority.expected_priority(events[0]["offense"], events[0]["defense"])
    if first["kind"] != "penalty":
        return dict(reason="no_selected_penalty")
    defense = events[0]["defense"]
    if (
        defense["kind"] not in {"yards", "no_change"}
        or defense["variable"] is not None
        or defense["variable_multiplier"] is not None
        or defense["penalty"] is not None
        or defense["out_of_bounds"]
    ):
        return dict(reason="retained_defense_authority")
    rows = [r for r in capture["lookup_rows"]["events"] if r["command_number"] == command["number"]]
    if any(
        r["chart_binding"] != "BOUND"
        or r["record_binding"] != "BOUND"
        or r["draw_binding"]["status"] != "BOUND"
        for r in rows
    ):
        return dict(reason="unbound_origin_rows")
    fouls = []
    expected = first
    for event in events:
        _equal(event["defense"], defense, "retained defensive operand")
        expected = priority.expected_priority(event["offense"], event["defense"])
        if expected["kind"] == "penalty":
            foul = expected["penalty"]
            if (
                foul["code"] != "fixed"
                or type(foul["yards"]) is not int
                or foul["yards"] not in {5, 10, 15}
                or foul["variable"] is not None
                or foul["variable_multiplier"] is not None
            ):
                return dict(reason="penalty_distance_authority")
            fouls.append(foul)
        elif (
            event is not events[-1]
            or expected["pending"]
            or expected["kind"] not in {"yards", "no_change", "incomplete"}
        ):
            return dict(reason="prepared_terminal_authority")
    if len({f["team"] for f in fouls}) != 1:
        return dict(reason="offsetting_authority")
    if expected["out_of_bounds"]:
        return dict(reason="prepared_bounds_authority")
    _require(bool(fouls) and len(events) == len(fouls) + 1, "penalty reroll closure")
    _require(len(fouls) <= 100, "100 penalty reroll bound")
    typed = capture["typed_capture"]
    ds, de = command["draw_range"]
    rs, re = command["draw_request_range"]
    draws, requests = typed["draws"][ds:de], typed["draw_requests"][rs:re]
    _require(
        len(rows) == len(draws) == len(requests) == 2 + len(fouls), "complete ordered exposure"
    )
    side = commitment._state(before["state"])["possession"]
    other = "away" if side == "home" else "home"
    for i, (row, draw, request) in enumerate(zip(rows, draws, requests, strict=True)):
        is_defense = i == 1
        owner = other if is_defense else side
        address = row["address"]
        _require(
            address["table"] == ("defense" if is_defense else "offense")
            and address["team_id"] == command["before"]["teams"][owner]["id"]
            and address["play"] == int(call)
            and address["column"] is None
            and address["formation"] == (formation if is_defense else None),
            "ordered row role/play",
        )
        _require(
            draw["kind"] == ("defensive" if is_defense else "offensive")
            and request["completed"] is True
            and request["draw_number"] == draw["number"]
            and request["expected_type"] == ("DefensiveRoll" if is_defense else "OffensiveRoll"),
            "ordered request/draw kind",
        )
        _equal(
            row["draw_binding"]["captured_draw_numbers"], [draw["number"]], "fresh selected draw"
        )
        _equal(row["roll"]["faces"], draw["faces"], "physical faces")
        _equal(address["roll"], draw["total"], "roll total")
        _equal(row["captured_draw_frontier"], draws[max(1, i)]["number"], "row frontier")
        _equal(
            row["facts"],
            defense if is_defense else events[0 if i == 0 else i - 1]["offense"],
            "selected operands",
        )
    _require(
        command["priority_attempt_range"][1] - command["priority_attempt_range"][0] == len(events),
        "priority attempt closure",
    )
    after = command["after"]["view"]
    _equal(command["report_changes"], [], "no pending report append")
    _equal(command["after"]["reports"], command["before"]["reports"], "no pending log credit")
    for name in ["statistics", "score", "scoring", "state"]:
        _equal(after[name], before[name], "zero pending " + name)
    _require(command["returned_report"]["pending"] is True, "pending report flag")
    _equal(
        command["returned_report"]["statistics"],
        dict(kind="excluded", team=None, yards=0, touchdown=False),
        "pending excluded credit",
    )
    return dict(
        reason=None,
        command=command,
        fouls=fouls,
        called=commitment._PLAY_LABELS[int(call) - 1],
        prepared_gain=expected["yards"] if expected["kind"] == "yards" else 0,
        prepared_incomplete=expected["kind"] == "incomplete",
    )


def _decision(command: dict[str, Any], origin: dict[str, Any], prior_ids: set[int]) -> bool:
    source = origin["command"]
    before, after = (command[k]["view"] for k in ["before", "after"])
    _equal(command["before"], source["after"], "same-object pending boundary")
    choice = command["arguments"][0]
    bits = choice.split(":")
    _require(
        len(bits) == 3 and bits[0] == "accept" and bits[1].isdigit() and bits[2] == "previous",
        "previous choice domain",
    )
    index = int(bits[1])
    _require(str(index) == bits[1] and index < len(origin["fouls"]), "selected foul index")
    foul = origin["fouls"][index]
    state = commitment._state(source["before"]["view"]["state"])
    side = state["possession"]
    offender = side if foul["team"] == "offense" else ("away" if side == "home" else "home")
    offended = "away" if offender == "home" else "home"
    pending = before["pending"]
    _require(
        type(pending) is dict and pending.get("chooser_side") == offended, "offended chooser side"
    )
    pending = cast(dict[str, Any], pending)
    matches = [v for v in pending["choices"] if v["id"] == choice]
    _require(len(matches) == 1 and matches[0]["enabled"] is True, "unique enabled choice")
    for kind in ["draw_range", "draw_request_range", "priority_range", "priority_attempt_range"]:
        _require(command[kind][0] == command[kind][1], "no new decision exposure")
    goal, distance = state["yards_to_goal"], state["yards_to_go"]
    off = foul["team"] == "offense"
    assessed = min(foul["yards"], (100 - goal if off else goal) // 2)
    new_goal = goal + assessed if off else goal - assessed
    first = (not off and foul["yards"] == 15) or new_goal <= goal - distance
    field = dict(
        possession=side,
        yards_to_goal=new_goal,
        down=1 if first else state["down"],
        yards_to_go=min(10, new_goal) if first else new_goal - (goal - distance),
    )
    changes = command["report_changes"]
    _require(
        len(changes) == 1
        and changes[0]["index"] == command["before"]["reports"]
        and changes[0]["before"] is None,
        "one indexed accepted report",
    )
    report = changes[0]["after"]
    _equal(command["returned_report"], report, "returned committed report")
    _require(
        type(report["number"]) is int
        and report["number"] > 0
        and report["number"] not in prior_ids,
        "fresh report identity",
    )
    _require(report["pending"] is False and report["supported"] is True, "normal accepted flags")
    _equal(report["called_play"], origin["called"], "called family")
    _equal(report["resolved_play"], origin["called"], "resolved family")
    _equal(commitment._state(report["state_before"]), state, "original report field")
    _equal(commitment._state(report["state_after"]), field, "enforced report field")
    _equal(report["outcome"], "penalty_accepted", "accepted outcome")
    _equal(report["yards"], origin["prepared_gain"], "prepared gain format")
    _equal(report["extends_quarter"], not off, "defensive extension eligibility format")
    _equal(
        report["statistics"],
        dict(kind="excluded", team=None, yards=0, touchdown=False),
        "cancelled credit",
    )
    _equal(commitment._boxes(after), commitment._boxes(before), "both unchanged boxes")
    for name in ["score", "scoring"]:
        _equal(after[name], before[name], "unchanged " + name)
    timing = dict(
        change_of_possession=False,
        conversion=False,
        first_down=goal - new_goal >= distance,
        guaranteed_out_of_bounds=False,
        incomplete=origin["prepared_incomplete"],
        no_elapsed_time=False,
        out_of_bounds=False,
        penalty=True,
        scoring=False,
        touchback=False,
        unreturned_kickoff=False,
    )
    _equal(report["timing"], timing, "eleven accepted timing facts")
    if after["phase"] != "scrimmage":
        return False
    _equal(commitment._state(after["state"]), field, "live enforced field")
    return True


def _local_clock(command: dict[str, Any], origin: dict[str, Any]) -> bool:
    """Check one nonperiod charge, never reanchor a whole-game clock chain."""
    source = origin["command"]
    if source["before"]["configuration"].get("mode") != "regulation":
        return False
    initial = source["before"]["view"]
    if initial.get("clock_optional") is not False:
        return False
    clock: Any = initial.get("clock")
    _require(type(clock) is dict, "local clock object")
    clock = cast(dict[str, Any], clock)
    quarter, remaining, budgets = (clock.get(k) for k in ("quarter", "remaining", "timeouts"))
    _require(type(quarter) is int and 1 <= quarter <= 4, "local clock quarter")
    _require(type(remaining) is int and 0 <= remaining <= 900, "local clock remaining")
    _require(
        type(budgets) is list
        and len(budgets) == 2
        and all(type(n) is int and 0 <= n <= 3 for n in budgets),
        "local clock timeouts",
    )
    if remaining <= 10:
        return False
    prefix = initial.get("timing_log")
    _require(type(prefix) is list, "local clock ledger")
    report_id = command["returned_report"]["number"]
    prefix = cast(list[dict[str, Any]], prefix)
    for row in prefix:
        _require(
            type(row) is dict and type(row.get("play_number")) is int and row["play_number"] > 0,
            "local prefix report identity",
        )
        _require(row["play_number"] != report_id, "local charge fresh report identity")
    for view in [source["after"]["view"], command["before"]["view"]]:
        _equal(view.get("clock"), clock, "zero pending clock effect")
        _equal(view.get("timing_log"), prefix, "zero pending charge effect")
    after = command["after"]["view"]
    expected_clock = {k: clock[k] for k in ("quarter", "remaining", "timeouts")}
    expected_clock["remaining"] = remaining - 10
    actual_clock: Any = after.get("clock")
    _require(type(actual_clock) is dict, "local after clock object")
    actual_clock = cast(dict[str, Any], actual_clock)
    _equal(
        {k: actual_clock.get(k) for k in expected_clock}, expected_clock, "ten second live clock"
    )
    _equal(
        after.get("timing_log"),
        prefix
        + [
            dict(
                play_number=report_id,
                quarter=quarter,
                before=remaining,
                seconds=10,
                after=remaining - 10,
                method="standard",
            )
        ],
        "one ten second charge and prefix",
    )
    _require(
        after.get("clock_optional") is False and after.get("normal_timing_ends_period") is False,
        "immediate nonperiod timing format",
    )
    for view in (initial, source["after"]["view"], command["before"]["view"], after):
        for index, name in enumerate(("home_timeouts", "away_timeouts")):
            _require(
                type(view.get(name)) is int and view[name] == budgets[index], "local timeout mirror"
            )
    return True


def audit_penalty_commitments(
    capture: dict[str, Any], *, typed_inventory_available: bool
) -> dict[str, Any]:
    """Require structural row/history/priority validation before these facts."""
    typed = capture["typed_capture"]
    pending: dict[int, dict[str, Any]] = {}
    observed: dict[int, set[int]] = {}
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    dispositions = []
    for command in typed["commands"]:
        key = command["game_number"]
        ids = observed.setdefault(key, set())
        if typed["version"] == "2" and command["initial_log"] is not None:
            for report in command["initial_log"]:
                _require(
                    type(report["number"]) is int and report["number"] > 0,
                    "observed report identity",
                )
                ids.add(report["number"])
        reason, checked = "nonaccepted_previous_command", False
        args = command["arguments"]
        prerequisites = (
            typed["version"] == "2"
            and capture.get("lookup_rows", {}).get("version") == "2"
            and typed_inventory_available
        )
        if prerequisites and command["exception_type"] is None:
            if command["operation"] == "snap":
                result = _origin(command, capture)
                pending[key] = result
                if result["reason"] == "offsetting_authority":
                    reason = result["reason"]
            elif (
                command["operation"] == "decide"
                and len(args) == 1
                and type(args[0]) is str
                and args[0].startswith("accept:")
                and args[0].endswith(":previous")
            ):
                origin = pending.pop(key, None)
                reason = "pending_origin_authority" if origin is None else origin["reason"]
                if reason is None:
                    assert origin is not None
                    live = _decision(command, origin, ids)
                    counts[
                        "clock_checked" if _local_clock(command, origin) else "clock_unknown"
                    ] += 1
                    counts["report_checked"] += 1
                    checked = live
                    reason = None if live else "live_continuation_authority"
            else:
                pending.pop(key, None)
        elif command["exception_type"] is not None:
            pending.pop(key, None)
            reason = "failed_command"
        else:
            reason = "typed_evidence_prerequisite"
        if checked:
            counts["checked"] += 1
        excluded = reason == "nonaccepted_previous_command"
        if excluded:
            counts["excluded"] += 1
        elif reason is not None:
            reasons[reason] += 1
        dispositions.append(
            dict(
                command_number=command["number"],
                game_number=key,
                status="GO" if checked else "EXCLUDED" if excluded else "UNVERIFIED",
                reason=reason,
            )
        )
        for change in command["report_changes"] if typed["version"] == "2" else []:
            number = change["after"]["number"]
            _require(type(number) is int and number > 0, "observed changed report identity")
            ids.add(number)
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        excluded=counts["excluded"],
        report_checked=counts["report_checked"],
        clock_checked=counts["clock_checked"],
        clock_unknown=counts["clock_unknown"],
        unknown=sum(reasons.values()),
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
