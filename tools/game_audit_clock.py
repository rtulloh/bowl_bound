"""Independent standard-clock ledger for checked ordinary supplied observations.

Authority: rules-profile standard timing and documented deferred-clock format.
No engine imports, timing helpers, prose or claim of complete capture/source truth.
"""

import json
from collections import Counter
from copy import deepcopy
from typing import Any, cast

from . import game_audit_priority as priority


class ClockEvidenceError(ValueError):
    """A supported supplied clock observation violates the independent contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ClockEvidenceError("standard clock " + message)


def _same(actual: Any, expected: Any) -> bool:
    return json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        expected, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _clock(view: dict[str, Any]) -> dict[str, Any]:
    value = view.get("clock")
    _require(isinstance(value, dict), "missing clock")
    value = cast(dict[str, Any], value)
    q, r, timeouts = (value.get(k) for k in ("quarter", "remaining", "timeouts"))
    _require(type(q) is int and 1 <= q <= 4, "quarter domain")
    _require(type(r) is int and 0 <= r <= 900, "remaining domain")
    _require(
        isinstance(timeouts, list)
        and len(timeouts) == 2
        and all(type(n) is int and 0 <= n <= 3 for n in timeouts),
        "timeout domain",
    )
    return dict(quarter=q, remaining=r, timeouts=deepcopy(timeouts))


def _charges(view: dict[str, Any]) -> list[dict[str, Any]]:
    charges = view.get("timing_log")
    _require(isinstance(charges, list), "missing timing ledger")
    charges = cast(list[dict[str, Any]], charges)
    for charge in charges:
        _require(
            isinstance(charge, dict)
            and set(charge) == {"play_number", "quarter", "before", "seconds", "after", "method"},
            "charge fields",
        )
        _require(
            type(charge["play_number"]) is int and charge["play_number"] > 0, "charge reference"
        )
        _require(type(charge["quarter"]) is int and 1 <= charge["quarter"] <= 4, "charge quarter")
        _require(
            all(type(charge[k]) is int and 0 <= charge[k] <= 900 for k in ("before", "after")),
            "charge seconds domain",
        )
        _require(type(charge["seconds"]) is int and charge["seconds"] >= 0, "request domain")
        _require(type(charge["method"]) is str and bool(charge["method"]), "charge method")
    return charges


def _context(view: dict[str, Any]) -> None:
    for name in (
        "clock_optional",
        "normal_timing_ends_period",
        "conditional_timeout",
        "hurried",
        "untimed_down",
    ):
        _require(type(view.get(name)) is bool, f"{name} domain")
    _require(
        all(k in view for k in ("armed_timeout", "bounds_declaration", "overtime")),
        "missing optional context",
    )
    _require(
        view["armed_timeout"] is None
        or type(view["armed_timeout"]) is str
        and view["armed_timeout"] in {"home", "away"},
        "armed timeout domain",
    )
    _require(
        view["bounds_declaration"] is None
        or type(view["bounds_declaration"]) is str
        and view["bounds_declaration"] in {"out_of_bounds", "in_bounds"},
        "bounds domain",
    )
    _require(
        view["overtime"] is None or isinstance(view["overtime"], dict), "overtime context domain"
    )


def _view(view: dict[str, Any], clock: dict[str, Any], pending: dict[str, Any] | None) -> None:
    _context(view)
    _require(
        all(view[k] is None for k in ("armed_timeout", "overtime", "bounds_declaration"))
        and all(view[k] is False for k in ("conditional_timeout", "hurried", "untimed_down")),
        "unexpected modifier",
    )
    ending = pending is not None and clock["remaining"] <= pending["seconds"]
    _require(_same(_clock(view), clock), "committed view")
    _require(view.get("clock_optional") is (pending is not None), "deferred flag")
    _require(view.get("normal_timing_ends_period") is ending, "period flag")


def _charge(
    chain: dict[str, Any], pending: dict[str, Any], *, conversion_hold: bool = False
) -> bool:
    clock = chain["clock"]
    after = max(0, clock["remaining"] - pending["seconds"])
    chain["ledger"].append(
        dict(
            play_number=pending["report"]["number"],
            quarter=clock["quarter"],
            before=clock["remaining"],
            seconds=pending["seconds"],
            after=after,
            method="standard",
        )
    )
    clock["remaining"] = after
    if after == 0 and conversion_hold:
        return False
    if after == 0:
        _require(clock["quarter"] < 4, "unsupported Q4 expiration")
        if clock["quarter"] == 2:
            clock["timeouts"] = [3, 3]
        clock["quarter"] += 1
        clock["remaining"] = 900
        return True
    return False


def _timing_facts(command: dict[str, Any], event: dict[str, Any]) -> dict[str, bool] | None:
    result = priority.expected_priority(event["offense"], event["defense"])
    if result["pending"] or result["kind"] not in {"yards", "no_change", "incomplete", "touchdown"}:
        return None
    state = command["before"]["view"]["state"]
    gain = result["yards"] if result["kind"] == "yards" else 0
    if result["kind"] == "yards" and state["yards_to_goal"] - gain >= 100:
        return None
    touchdown = result["kind"] == "touchdown" or gain >= state["yards_to_goal"]
    facts = dict(
        first_down=not touchdown and gain >= state["yards_to_go"],
        change_of_possession=not touchdown and state["down"] == 4 and gain < state["yards_to_go"],
        penalty=False,
        incomplete=result["kind"] == "incomplete",
        scoring=touchdown,
        touchback=False,
        out_of_bounds=result["out_of_bounds"],
        guaranteed_out_of_bounds=False,
        unreturned_kickoff=False,
        conversion=False,
        no_elapsed_time=False,
    )
    _require(_same(command["returned_report"].get("timing"), facts), "terminal timing facts")
    if touchdown:
        _require(command["returned_report"].get("extends_quarter") is False, "TD extension flag")
    return facts


def _duration(facts: dict[str, bool], clock: dict[str, Any]) -> int:
    late = (clock["quarter"] == 2 and clock["remaining"] <= 120) or (
        clock["quarter"] == 4 and clock["remaining"] <= 300
    )
    if (
        facts["incomplete"]
        or facts["change_of_possession"]
        or facts["scoring"]
        or facts["out_of_bounds"]
        and late
    ):
        return 10
    return 20 if facts["first_down"] else 30


def _boxes(view: dict[str, Any]) -> dict[str, Any]:
    return {side: view["statistics"][side] for side in ("home", "away")}


def _pending(command: dict[str, Any], seconds: int) -> dict[str, Any]:
    after = command["after"]["view"]
    return dict(
        seconds=seconds,
        report=deepcopy(command["returned_report"]),
        statistics=deepcopy(_boxes(after)),
        score=deepcopy(after["score"]),
        scoring=deepcopy(after["scoring"]),
    )


def _no_new_play(command: dict[str, Any], pending: dict[str, Any], capture: dict[str, Any]) -> None:
    _require(
        not command["report_changes"]
        and all(
            command[k][0] == command[k][1]
            for k in (
                "draw_range",
                "draw_request_range",
                "priority_range",
                "priority_attempt_range",
                "report_range",
            )
        ),
        "runoff consumed new play evidence",
    )
    _require(
        not any(
            row["command_number"] == command["number"] for row in capture["lookup_rows"]["events"]
        ),
        "runoff consulted new chart row",
    )
    for endpoint in ("before", "after"):
        view = command[endpoint]["view"]
        _require(_same(_boxes(view), pending["statistics"]), "runoff changed statistics")
        _require(
            _same(view["score"], pending["score"]) and _same(view["scoring"], pending["scoring"]),
            "runoff changed scoring",
        )


def _period_boundary(command: dict[str, Any], pending: dict[str, Any]) -> None:
    report = command["returned_report"]
    _require(isinstance(report, dict), "missing period-boundary report")
    expected = dict(
        number=pending["report"]["number"],
        outcome="period_boundary",
        called_play="Period end",
        resolved_play="Period end",
        defense="No formation",
        yards=None,
        trace=[],
        supported=True,
        pending=False,
        statistics=dict(kind="excluded", team=None, yards=0, touchdown=False),
        timing={key: False for key in pending["report"]["timing"]},
        extends_quarter=False,
        state_before=pending["report"]["state_after"],
    )
    _require(
        all(k in report and _same(report[k], value) for k, value in expected.items()),
        "period-boundary format",
    )


def _timeout_mirrors(view: dict[str, Any], expected: dict[str, Any]) -> None:
    for index, name in enumerate(("home_timeouts", "away_timeouts")):
        _require(type(view.get(name)) is int and 0 <= view[name] <= 3, f"PAT {name} domain")
        _require(view[name] == expected["timeouts"][index], f"PAT {name} mirror")


def _conversion_charge(
    command: dict[str, Any], chain: dict[str, Any], counts: Counter[str], *, qualified: bool
) -> str | None:
    """Apply approved zero timing after independently checked dedicated PAT facts."""
    before, after = (command[key]["view"] for key in ("before", "after"))
    _require(before.get("finished") is False, "PAT before unfinished")
    _require(type(after.get("finished")) is bool, "PAT finished domain")
    _timeout_mirrors(before, chain["clock"])
    clock = chain["clock"]
    quarter, remaining = clock["quarter"], clock["remaining"]
    _require(
        command["returned_report"]["number"] not in {row["play_number"] for row in chain["ledger"]},
        "PAT report identity reused in charged prefix",
    )
    chain["ledger"].append(
        dict(
            play_number=command["returned_report"]["number"],
            quarter=quarter,
            before=remaining,
            seconds=0,
            after=remaining,
            method="standard",
        )
    )
    _require(_same(_charges(after), chain["ledger"]), "PAT zero charge and prefix")
    _context(after)
    if not qualified:
        return "PAT_additional_draw_authority"
    if quarter == 4 and remaining == 0 and after["score"]["home"] == after["score"]["away"]:
        # The actual historical OT profile is not established by this clock anchor.
        # Do not reject a legitimate OT view merely because its game clock is absent.
        return "Q4_tied_conversion_continuation_authority"
    final = quarter == 4 and remaining == 0
    if remaining == 0 and quarter < 4:
        clock["quarter"], clock["remaining"] = quarter + 1, 900
        if quarter == 2:
            clock["timeouts"] = [3, 3]
        counts["periods"] += 1
    _timeout_mirrors(after, clock)
    _require(after.get("phase") == ("final" if final else "kickoff"), "PAT continuation phase")
    _require(after["finished"] is final, "PAT continuation finished")
    counts["conversions"] += 1
    counts["finalizations"] += int(final)
    counts["immediate"] += 1
    return None


def audit_standard_clock(
    capture: dict[str, Any],
    *,
    ordinary: dict[str, Any],
    typed_inventory_available: bool,
    pat: dict[str, Any] | None = None,
    kickoff: dict[str, Any] | None = None,
    supplemental: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check normal supplied chains; initial anchors/completeness stay unverified."""
    typed = capture["typed_capture"]
    reasons: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    chains: dict[int, dict[str, Any]] = {}
    dispositions = []
    ordinary_by_number = {row["command_number"]: row for row in ordinary["dispositions"]}
    supplemental_by_number = {
        row["command_number"]: row for row in (supplemental or {}).get("dispositions", [])
    }
    # Global validated command numbers identify the actual object's invocation;
    # report IDs alone can be reused after reload or by another object.
    pat_by_number = {row["command_number"]: row for row in pat["dispositions"]} if pat else {}
    kick_by_number = (
        {row["command_number"]: row for row in kickoff["dispositions"]} if kickoff else {}
    )
    conversion_charge_diagnostics = 0
    for command in typed["commands"]:
        number, game = command["number"], command["game_number"]
        before, after = command["before"]["view"], command["after"]["view"]
        known = ordinary_by_number[number]
        conditional = supplemental_by_number.get(number, {})
        checked_conditional = conditional.get("game_number") == game and (
            conditional.get("status") == "GO"
            or conditional.get("reason") == "live_continuation_authority"
        )
        reason = None
        facts_checked = False
        command_counts: Counter[str] = Counter()
        is_pat = command["operation"] == "decide" and command["arguments"] == ["conversion:kick"]
        pat_fact = pat_by_number.get(number, {})
        same_pat_object = pat_fact.get("game_number") == game
        checked_pat = same_pat_object and pat_fact.get("status") == "GO"
        core_pat = same_pat_object and pat_fact.get("core_checked") is True
        opening = command["operation"] == "decide" and command["arguments"] in [
            ["toss:kick"],
            ["toss:receive"],
        ]
        kick_operation = (
            command["operation"] == "kick" and command["arguments"] == ["kickoff"]
        ) or (command["operation"] == "decide" and command["arguments"] == ["kick:touchback"])
        kick_fact = kick_by_number.get(number, {})
        same_kick_object = kick_fact.get("game_number") == game
        opening_checked = (
            same_kick_object
            and kick_fact.get("kind") == "opening"
            and kick_fact.get("core_checked") is True
            and kick_fact.get("reason") == "conditional_opening_anchor"
        )
        kick_checked = (
            same_kick_object
            and kick_fact.get("kind") in {"kick", "touchback"}
            and kick_fact.get("status") == "GO"
        )
        if typed["version"] != "2" or not typed_inventory_available:
            reason = "typed_evidence_prerequisite"
        elif command["before"]["configuration"].get("mode") != "regulation":
            reason = "nonregulation"
        elif command["exception_type"] is not None:
            reason = "failed_command"
        if reason is None:
            _context(before)
            if any(
                before[k] is not None for k in ("armed_timeout", "overtime", "bounds_declaration")
            ) or any(before[k] for k in ("conditional_timeout", "hurried", "untimed_down")):
                reason = "nonstandard_context"
        if game not in chains:
            if (
                reason is None
                and before["phase"] == "scrimmage"
                and before.get("clock_optional") is False
            ):
                clock = _clock(before)
                _require(clock["remaining"] > 0, "live initial remaining")
                chains[game] = dict(
                    clock=clock, ledger=deepcopy(_charges(before)), pending=None, tainted=False
                )
            elif reason is None and (
                (opening and opening_checked) or (kick_operation and kick_checked)
            ):
                clock = _clock(before)
                _require(clock["remaining"] > 0, "live initial kickoff remaining")
                chains[game] = dict(
                    clock=clock, ledger=deepcopy(_charges(before)), pending=None, tainted=False
                )
                command_counts["kickoff_anchors"] += 1
            elif reason is None and is_pat and core_pat and before["phase"] == "conversion_choice":
                chains[game] = dict(
                    clock=_clock(before),
                    ledger=deepcopy(_charges(before)),
                    pending=None,
                    tainted=False,
                )
                command_counts["conversion_anchors"] += 1
            else:
                chains[game] = dict(tainted=True)
                reason = reason or "unanchored_clock"
        chain = chains[game]
        if reason is None and chain["tainted"]:
            reason = "unverified_prior_continuation"
        is_runoff = command["operation"] == "decide" and command["arguments"] == ["clock:runoff"]
        args = command["arguments"]
        is_snap = (
            command["operation"] == "snap"
            and len(args) == 2
            and args[0] in set("123456789")
            and args[1] in set("ABCDEF")
        )
        pending = chain.get("pending")
        boundary = False
        if reason is None:
            pending = chain["pending"]
            boundary = bool(
                is_snap
                and pending is not None
                and chain["clock"]["quarter"] == 2
                and chain["clock"]["remaining"] <= pending["seconds"]
            )
            checked_report = (
                known["status"] == "GO" or known["reason"] == "live_continuation_authority"
            ) or checked_conditional
            if opening or kick_operation:
                if not (opening_checked if opening else kick_checked):
                    reason = "kickoff_report_prerequisite"
                else:
                    _require(pending is None, "kickoff cannot retain deferred scrimmage timing")
            elif is_pat:
                if not core_pat:
                    reason = "PAT_report_prerequisite"
                else:
                    _require(pending is None, "PAT cannot retain prior deferred timing")
            elif not is_runoff and not is_snap:
                reason = "nonstandard_operation"
            elif is_runoff and pending is None:
                reason = "unidentified_pending_timing"
            elif not is_runoff and not boundary and not checked_report:
                reason = "ordinary_report_prerequisite"
        if reason is None:
            _view(before, chain["clock"], chain["pending"])
            _require(_same(_charges(before), chain["ledger"]), "before ledger continuity")
            complete = False
            if opening or kick_operation:
                _timeout_mirrors(before, chain["clock"])
                if opening:
                    command_counts["opening_transitions"] += 1
                elif kick_fact["pending"]:
                    command_counts["pending_kicks"] += 1
                else:
                    seconds = kick_fact["seconds"]
                    deferred_kick = kick_fact.get("deferred", False)
                    _require(type(deferred_kick) is bool, "kickoff deferred domain")
                    _require(
                        type(seconds) is int
                        and (seconds == 30 if deferred_kick else seconds in {0, 10}),
                        "kickoff duration domain",
                    )
                    _require(chain["clock"]["remaining"] > seconds, "kickoff period authority")
                    _require(
                        command["returned_report"]["number"]
                        not in {row["play_number"] for row in chain["ledger"]},
                        "kickoff report identity reused in charged prefix",
                    )
                    if deferred_kick:
                        chain["pending"] = _pending(command, seconds)
                        command_counts["deferred"] += 1
                    else:
                        _charge(chain, dict(seconds=seconds, report=command["returned_report"]))
                    command_counts["kickoffs"] += 1
                _timeout_mirrors(after, chain["clock"])
                complete = True
            if is_pat:
                reason = _conversion_charge(command, chain, command_counts, qualified=checked_pat)
                conversion_charge_diagnostics += 1
                complete = True
            if pending is not None:
                old_q = chain["clock"]["quarter"]
                if old_q == 4 and chain["clock"]["remaining"] <= pending["seconds"]:
                    reason = "Q4_terminal_authority"
                else:
                    if is_runoff or boundary:
                        _no_new_play(command, pending, capture)
                        if boundary:
                            _period_boundary(command, pending)
                        else:
                            _require(
                                _same(command["returned_report"], pending["report"]),
                                "runoff report reference",
                            )
                    ended = _charge(chain, pending)
                    chain["pending"] = None
                    command_counts["periods"] += int(ended)
                    command_counts["implicit" if is_snap else "runoff"] += 1
                    if is_runoff or boundary:
                        command_counts["period_boundaries"] += int(boundary)
                        complete = True
                        _require(
                            after["phase"] == ("kickoff" if ended and old_q == 2 else "scrimmage"),
                            "runoff continuation phase",
                        )
            if reason is None and not complete:
                if checked_conditional:
                    # Already independently derived from the full typed graph,
                    # keyed to this actual object's command, never a report ID.
                    facts = conditional["timing_facts"]
                else:
                    start, _ = command["priority_range"]
                    facts = _timing_facts(command, capture["priority"]["events"][start])
                if facts is None:
                    reason = "nonstandard_result"
                else:
                    seconds = _duration(facts, chain["clock"])
                    if (
                        not facts["scoring"]
                        and chain["clock"]["quarter"] == 4
                        and chain["clock"]["remaining"] <= seconds
                    ):
                        reason = "Q4_terminal_authority"
                    else:
                        facts_checked = True
                        next_pending = _pending(command, seconds)
                        if seconds > 10:
                            chain["pending"] = next_pending
                            command_counts["deferred"] += 1
                            _require(after["phase"] == "clock_choice", "deferred phase")
                        else:
                            old_q = chain["clock"]["quarter"]
                            ended = _charge(chain, next_pending, conversion_hold=facts["scoring"])
                            command_counts["touchdowns"] += int(facts["scoring"])
                            command_counts["conversion_holds"] += int(
                                facts["scoring"] and chain["clock"]["remaining"] == 0
                            )
                            command_counts["immediate"] += 1
                            command_counts["periods"] += int(ended)
                            _require(
                                after["phase"]
                                == (
                                    "conversion_choice"
                                    if facts["scoring"]
                                    else "kickoff"
                                    if ended and old_q == 2
                                    else "scrimmage"
                                ),
                                "immediate continuation phase",
                            )
            if reason is None:
                _view(after, chain["clock"], chain["pending"])
                _require(_same(_charges(after), chain["ledger"]), "after ledger")
                counts.update(command_counts)
                counts["checked"] += 1
                counts["timing_facts_checked"] += int(facts_checked)
        if reason is not None:
            chain["tainted"] = True
            reasons[reason] += 1
        dispositions.append(
            dict(
                command_number=number,
                game_number=game,
                status="GO" if reason is None else "UNVERIFIED",
                reason=reason,
            )
        )
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        unknown=sum(reasons.values()),
        deferred=counts["deferred"],
        immediate=counts["immediate"],
        runoff=counts["runoff"],
        implicit=counts["implicit"],
        periods=counts["periods"],
        period_boundaries=counts["period_boundaries"],
        timing_facts_checked=counts["timing_facts_checked"],
        touchdowns=counts["touchdowns"],
        conversion_holds=counts["conversion_holds"],
        kickoff_anchors=counts["kickoff_anchors"],
        opening_transitions=counts["opening_transitions"],
        pending_kicks=counts["pending_kicks"],
        kickoffs=counts["kickoffs"],
        conversions=counts["conversions"],
        conversion_anchors=counts["conversion_anchors"],
        finalizations=counts["finalizations"],
        conversion_charge_diagnostics=conversion_charge_diagnostics,
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
