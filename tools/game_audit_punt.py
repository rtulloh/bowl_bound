"""Independent fixed unmarked punts and in-field receptions, engine-free."""

from collections import Counter
from typing import Any, cast

from . import game_audit_commitment as commitment
from . import game_audit_kickoff as kickoff


class PuntEvidenceError(ValueError):
    """Supplied punt evidence contradicts the bounded independent contract."""


def _require(value: bool, label: str) -> None:
    if not value:
        raise PuntEvidenceError("punt fair catch " + label)


def _equal(actual: Any, expected: Any, label: str) -> None:
    _require(commitment._canonical(actual) == commitment._canonical(expected), label)


def _context(command: dict[str, Any], view: dict[str, Any]) -> str | None:
    mode = command["before"]["configuration"].get("mode")
    if (
        mode not in {"drive", "regulation"}
        or command["before"]["configuration"].get("advanced_ii") is not False
    ):
        return "context_authority"
    _require(type(view.get("finished")) is bool, "finished domain")
    if view["finished"]:
        return "finished_context_authority"
    if mode == "regulation":
        for key in (
            "hurried",
            "conditional_timeout",
            "untimed_down",
            "clock_optional",
            "normal_timing_ends_period",
        ):
            _require(type(view.get(key)) is bool, key + " domain")
        for key in ("overtime", "armed_timeout", "bounds_declaration", "kickoff_penalties"):
            _require(key in view, "missing " + key)
        _require(type(view["kickoff_penalties"]) is list, "carried fouls domain")
        if (
            any(view[key] for key in ("hurried", "conditional_timeout", "untimed_down"))
            or any(
                view[key] is not None for key in ("overtime", "armed_timeout", "bounds_declaration")
            )
            or view["kickoff_penalties"]
        ):
            return "context_authority"
        if view["normal_timing_ends_period"]:
            return "period_start_authority"
    return None


def _rows(capture: dict[str, Any], command: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in capture["lookup_rows"]["events"]
        if row["command_number"] == command["number"]
    ]


def _report(
    command: dict[str, Any],
    original: dict[str, Any],
    final: dict[str, Any],
    *,
    pending: bool,
    number: int | None = None,
    outcome: str = "punt_fair_catch",
) -> int:
    report = command["returned_report"]
    _require(type(report) is dict, "returned report")
    ident = report.get("number")
    _require(type(ident) is int and ident > 0, "report identity")
    if number is not None:
        _equal(ident, number, "same pending report identity")
    for key in ("called_play", "resolved_play"):
        _equal(report[key], "Punt", key)
    _require(report["pending"] is pending and report["supported"] is True, "report flags")
    _require(
        report["unsupported_reason"] is None and report["extends_quarter"] is False,
        "report support format",
    )
    _equal(report["defense"], "No formation", "defense format")
    _equal(report["yards"], None, "symbolic yards")
    _equal(report["outcome"], "special_teams_pending" if pending else outcome, "outcome")
    _equal(commitment._state(report["state_before"]), original, "report original field")
    _equal(commitment._state(report["state_after"]), final, "report final field")
    _equal(
        report["statistics"],
        dict(kind="excluded", team=None, yards=0, touchdown=False),
        "excluded zero credit",
    )
    timing = {
        key: False
        for key in (
            "first_down",
            "change_of_possession",
            "penalty",
            "incomplete",
            "scoring",
            "touchback",
            "out_of_bounds",
            "guaranteed_out_of_bounds",
            "unreturned_kickoff",
            "conversion",
            "no_elapsed_time",
        )
    }
    timing["change_of_possession"] = not pending
    _equal(report["timing"], timing, "eleven timing facts")
    changes = command["report_changes"]
    if pending:
        _equal(changes, [], "no pending append")
    else:
        _require(
            len(changes) == 1
            and changes[0]["before"] is None
            and changes[0]["index"] == command["before"]["reports"],
            "one indexed append",
        )
        _equal(changes[0]["after"], report, "appended report")
    return ident


def _origin(command: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    before, after = (command[key]["view"] for key in ("before", "after"))
    reason = _context(command, before)
    if reason is not None:
        return dict(reason=reason)
    if before.get("phase") not in {"scrimmage", "clock_choice"}:
        return dict(reason="start_phase_authority")
    original = commitment._state(before["state"])
    rows = _rows(capture, command)
    if not rows or any(
        row["chart_binding"] != "BOUND"
        or row["record_binding"] != "BOUND"
        or row["draw_binding"]["status"] != "BOUND"
        for row in rows
    ):
        return dict(reason="row_binding_authority")
    row = rows[0]
    owner = original["possession"]
    _equal(row["address"]["team_id"], command["before"]["teams"][owner]["id"], "punter row owner")
    _require(
        row["address"]["table"] == "special_teams" and row["address"]["column"] == "punt",
        "punt row role",
    )
    facts = row["facts"]
    if (
        facts["kind"] != "yards"
        or facts["priority"] != "normal"
        or facts["out_of_bounds"]
        or facts["variable"] is not None
        or facts["penalty"] is not None
    ):
        return dict(reason="punt_distance_authority")
    _require(
        facts["variable_multiplier"] is None and type(facts["yards"]) is int, "fixed numeric domain"
    )
    if facts["yards"] < 0:
        return dict(reason="negative_punt_authority")
    landing = original["yards_to_goal"] - facts["yards"]
    if not 1 <= landing <= 99:
        return dict(reason="landing_authority")
    kickoff._exposure(command, rows, capture["typed_capture"], 1)
    receiver = "away" if owner == "home" else "home"
    kickoff._offered(after, receiver, {"kick:fair_catch", "kick:return"})
    kickoff._effects(command)
    _equal(commitment._state(after["state"]), original, "pending live field")
    _require(after.get("clock_optional", False) is False, "no pending deferred charge")
    if (
        command["before"]["configuration"]["mode"] == "regulation"
        and before["clock_optional"] is False
    ):
        _equal(after.get("clock"), before.get("clock"), "zero pending clock effect")
        _equal(
            after.get("timing_log"), before.get("timing_log"), "zero pending timing ledger effect"
        )
    number = _report(command, original, original, pending=True)
    goal = 100 - landing
    final = dict(possession=receiver, yards_to_goal=goal, down=1, yards_to_go=min(10, goal))
    return dict(
        reason=None,
        command=command,
        original=original,
        final=final,
        receiver=receiver,
        number=number,
    )


def _return_field(
    command: dict[str, Any], capture: dict[str, Any], origin: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Derive only fixed in-field return eligibility before closing its exposure."""
    rows = _rows(capture, command)
    if not rows or any(
        row["chart_binding"] != "BOUND"
        or row["record_binding"] != "BOUND"
        or row["draw_binding"]["status"] != "BOUND"
        for row in rows
    ):
        return None, "return_row_binding_authority"
    row = rows[0]
    _equal(
        row["address"]["team_id"],
        command["before"]["teams"][origin["receiver"]]["id"],
        "return row owner",
    )
    _require(
        row["address"]["table"] == "special_teams" and row["address"]["column"] == "punt_return",
        "return row role",
    )
    facts = row["facts"]
    if (
        facts["kind"] not in {"yards", "no_change"}
        or facts["priority"] != "normal"
        or facts["out_of_bounds"]
        or facts["variable"] is not None
        or facts["penalty"] is not None
    ):
        return None, "return_terminal_authority"
    _require(facts["variable_multiplier"] is None, "fixed return multiplier")
    if facts["kind"] == "no_change":
        _require(facts["yards"] is None, "no-change return fixed yards")
        gain = 0
    else:
        _require(type(facts["yards"]) is int, "fixed return gain domain")
        gain = facts["yards"]
    goal = origin["final"]["yards_to_goal"] - gain
    if not 1 <= goal <= 99:
        return None, "return_landing_authority"
    # A nonnumeric F/penalty path may legitimately consume additional rolls.
    # Only this independently eligible fixed population has exactly one draw.
    kickoff._exposure(command, rows, capture["typed_capture"], 1)
    return dict(
        possession=origin["receiver"], yards_to_goal=goal, down=1, yards_to_go=min(10, goal)
    ), None


def _clock(command: dict[str, Any], origin: dict[str, Any]) -> bool:
    if command["before"]["configuration"].get("mode") != "regulation":
        return False
    source = origin["command"]
    # The kick may commit a previous play. Its pending endpoint is the anchor
    # for this charge; no prior timing/history is certified by this comparison.
    pending = source["after"]["view"]
    before = command["before"]["view"]
    after = command["after"]["view"]
    for view in (pending, before):
        reason = _context(command, view)
        if reason is not None:
            return False
        _require(view["clock_optional"] is False, "pending clock optional")
    clock = before.get("clock")
    _require(type(clock) is dict, "clock object")
    quarter, remaining, budgets = (clock.get(k) for k in ("quarter", "remaining", "timeouts"))
    _require(type(quarter) is int and 1 <= quarter <= 4, "clock quarter")
    _require(type(remaining) is int and 0 <= remaining <= 900, "clock remaining")
    _require(
        type(budgets) is list
        and len(budgets) == 2
        and all(type(n) is int and 0 <= n <= 3 for n in budgets),
        "timeout budgets",
    )
    _equal(pending["clock"], clock, "pending clock anchor")
    prefix = before.get("timing_log")
    _require(type(prefix) is list, "timing ledger")
    prefix = cast(list[dict[str, Any]], prefix)
    _equal(pending["timing_log"], prefix, "pending ledger anchor")
    for view in (source["before"]["view"], pending, before):
        for index, key in enumerate(("home_timeouts", "away_timeouts")):
            _require(type(view.get(key)) is int and view[key] == budgets[index], "timeout mirror")
    number = command["returned_report"]["number"]
    for charge in prefix:
        _require(
            type(charge) is dict
            and type(charge.get("play_number")) is int
            and charge["play_number"] > 0,
            "charged identity domain",
        )
        _require(charge["play_number"] != number, "fresh charged identity")
    # Fresh report identity is required even when the ensuing period transition
    # is outside this local clock oracle. Only a qualified nonperiod endpoint
    # may be compared against the original timeout budgets.
    if remaining <= 10:
        return False
    _require(_context(command, after) is None, "nonperiod after context")
    for index, key in enumerate(("home_timeouts", "away_timeouts")):
        _require(type(after.get(key)) is int and after[key] == budgets[index], "timeout mirror")
    _equal(
        after.get("timing_log"),
        prefix
        + [
            dict(
                play_number=number,
                quarter=quarter,
                before=remaining,
                seconds=10,
                after=remaining - 10,
                method="standard",
            )
        ],
        "one ten second charge and prefix",
    )
    actual = after.get("clock")
    _require(type(actual) is dict, "after clock object")
    _equal(
        {key: actual.get(key) for key in ("quarter", "remaining", "timeouts")},
        dict(quarter=quarter, remaining=remaining - 10, timeouts=budgets),
        "ten second live clock",
    )
    _require(
        after.get("clock_optional") is False and after.get("normal_timing_ends_period") is False,
        "immediate nonperiod clock",
    )
    return True


def audit_punt_commitments(
    capture: dict[str, Any], *, typed_inventory_available: bool
) -> dict[str, Any]:
    """Check causal fixed punts; supplied anchors never certify full capture."""
    typed = capture["typed_capture"]
    counts: Counter[str] = Counter()
    pending: dict[int, dict[str, Any]] = {}
    observed: dict[int, set[int]] = {}
    dispositions = []
    prerequisite = (
        typed["version"] == "2"
        and capture.get("lookup_rows", {}).get("version") == "2"
        and typed_inventory_available
    )
    for command in typed["commands"]:
        game = command["game_number"]
        ids = observed.setdefault(game, set())
        if typed["version"] == "2" and command["initial_log"] is not None:
            for report in command["initial_log"]:
                _require(
                    type(report["number"]) is int and report["number"] > 0,
                    "initial observed identity",
                )
                ids.add(report["number"])
        status, reason, core = "EXCLUDED", "nonpunt_command", False
        if command["operation"] == "kick" and command["arguments"] == ["punt"]:
            status, reason = "UNVERIFIED", "typed_evidence_prerequisite"
            if prerequisite and command["exception_type"] is None:
                origin = _origin(command, capture)
                pending[game] = origin
                reason = origin["reason"]
                if reason is None:
                    counts["pending_checked"] += 1
                    core = True
                    reason = "pending_commitment"
                    origin["disposition_index"] = len(dispositions)
        elif command["operation"] == "decide" and command["arguments"] in (
            ["kick:fair_catch"],
            ["kick:return"],
        ):
            origin = pending.pop(game, None)
            status = "UNVERIFIED"
            reason = "pending_origin_authority" if origin is None else origin["reason"]
            if reason is None:
                assert origin is not None
                dispositions[origin["disposition_index"]].update(
                    status="EXCLUDED", reason="pending_creation_checked"
                )
                if command["exception_type"] is not None:
                    reason = "failed_command"
                else:
                    before, after = (command[key]["view"] for key in ("before", "after"))
                    _equal(before, origin["command"]["after"]["view"], "retained pending snapshot")
                    kickoff._offered(before, origin["receiver"], {"kick:fair_catch", "kick:return"})
                    is_return = command["arguments"] == ["kick:return"]
                    final = origin["final"]
                    if is_return:
                        final, reason = _return_field(command, capture, origin)
                    else:
                        kickoff._exposure(command, _rows(capture, command), typed, 0)
                    if reason is None:
                        assert final is not None
                        _require(origin["number"] not in ids, "fresh observed report identity")
                        _report(
                            command,
                            origin["original"],
                            final,
                            pending=False,
                            number=origin["number"],
                            outcome="punt_return" if is_return else "punt_fair_catch",
                        )
                        kickoff._effects(command)
                        counts["report_checked"] += 1
                        counts["return_report_checked"] += int(is_return)
                        local_clock = _clock(command, origin)
                        counts["clock_checked" if local_clock else "clock_unknown"] += 1
                        normal_live = (
                            command["before"]["configuration"]["mode"] == "drive" or local_clock
                        )
                        if local_clock:
                            _equal(after.get("phase"), "scrimmage", "nonperiod live phase")
                        if normal_live and after.get("phase") == "scrimmage":
                            _require("state" in after, "missing live state")
                            _equal(
                                commitment._state(after["state"]),
                                final,
                                "live receiving field",
                            )
                            _require(after.get("pending") is None, "finished reception decision")
                            core = True
                            status = "GO"
                            reason = None
                            counts["checked"] += 1
                            counts["return_checked"] += int(is_return)
                        else:
                            reason = "live_continuation_authority"
        else:
            pending.pop(game, None)
        dispositions.append(
            dict(
                command_number=command["number"],
                game_number=game,
                status=status,
                reason=reason,
                core_checked=core,
            )
        )
        for change in command["report_changes"] if typed["version"] == "2" else []:
            ident = change["after"]["number"]
            _require(type(ident) is int and ident > 0, "changed observed identity")
            ids.add(ident)
    reasons = Counter(row["reason"] for row in dispositions if row["status"] == "UNVERIFIED")
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        report_checked=counts["report_checked"],
        return_checked=counts["return_checked"],
        return_report_checked=counts["return_report_checked"],
        pending_checked=counts["pending_checked"],
        clock_checked=counts["clock_checked"],
        clock_unknown=counts["clock_unknown"],
        excluded=sum(row["status"] == "EXCLUDED" for row in dispositions),
        unknown=sum(reasons.values()),
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
