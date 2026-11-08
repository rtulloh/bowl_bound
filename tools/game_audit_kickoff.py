"""Independent ordinary kickoff commitments from supplied typed observations.

Approved BB rules-profile kick/return/year/timing policies govern. No engine or
codec helpers, display-token parsing, external source or completeness authority.
"""

from collections import Counter
from copy import deepcopy
from typing import Any, cast

from . import game_audit_commitment as commitment
from .game_audit_lookup import LookupInventory


class KickoffEvidenceError(ValueError):
    """Supported supplied kickoff facts contradict the independent contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise KickoffEvidenceError("kickoff commitment " + message)


def _equal(actual: Any, expected: Any, label: str) -> None:
    try:
        commitment._equal(actual, expected, label)
    except commitment.CommitmentEvidenceError as error:
        raise KickoffEvidenceError(str(error)) from error


def _field(value: Any) -> dict[str, Any]:
    try:
        return commitment._state(value)
    except commitment.CommitmentEvidenceError as error:
        raise KickoffEvidenceError(str(error)) from error


def _core(side: str, goal: int) -> dict[str, Any]:
    return dict(possession=side, yards_to_goal=goal, down=1, yards_to_go=min(10, goal))


def _effects(command: dict[str, Any]) -> None:
    before, after = (command[key]["view"] for key in ("before", "after"))
    for name in ("home", "away"):
        _require(type(before.get(name)) is str and bool(before[name].strip()), "team label domain")
        _equal(after.get(name), before[name], "team label continuity")
    for view in (before, after):
        score = view.get("score")
        _require(
            type(score) is dict
            and score.keys() == {"home", "away"}
            and all(type(v) is int and v >= 0 for v in score.values()),
            "score domain",
        )
    for key in ("score", "scoring"):
        _equal(after[key], before[key], "unchanged " + key)
    try:
        _equal(commitment._boxes(after), commitment._boxes(before), "both boxes")
    except commitment.CommitmentEvidenceError as error:
        raise KickoffEvidenceError(str(error)) from error


def _context(view: dict[str, Any], *, deferred: bool = False) -> str | None:
    _require("pending" in view, "missing pending context")
    _require(type(view.get("finished")) is bool, "finished domain")
    for name in (
        "clock_optional",
        "normal_timing_ends_period",
        "conditional_timeout",
        "hurried",
        "untimed_down",
    ):
        _require(type(view.get(name)) is bool, name + " domain")
    for name in ("overtime", "armed_timeout", "bounds_declaration", "kickoff_penalties"):
        _require(name in view, "missing " + name)
    _require(view["overtime"] is None or type(view["overtime"]) is dict, "overtime domain")
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
    _require(type(view["kickoff_penalties"]) is list, "carried foul container")
    if view["kickoff_penalties"]:
        return "carried_kickoff_foul_authority"
    if any(
        view[key] is not None for key in ("overtime", "armed_timeout", "bounds_declaration")
    ) or any(view[key] for key in ("conditional_timeout", "hurried", "untimed_down")):
        return "nonstandard_context"
    _require(view["finished"] is False, "live unfinished context")
    _require(
        view["clock_optional"] is deferred and view["normal_timing_ends_period"] is False,
        "nonoptional kick timing context",
    )
    return None


def _offered(view: dict[str, Any], side: str, expected: set[str]) -> None:
    """Check only independently required IDs, typed availability and chooser."""
    _require("pending" in view, "missing offered chooser")
    pending = view["pending"]
    _require(type(pending) is dict, "offered chooser")
    _equal(pending.get("chooser_side"), side, "offered chooser side")
    _equal(pending.get("chooser"), view[side], "offered chooser label")
    choices = pending.get("choices")
    _require(type(choices) is list and len(choices) == len(expected), "offered choice count")
    identifiers = []
    for choice in choices:
        _require(type(choice) is dict, "offered choice object")
        choice = cast(dict[str, Any], choice)
        ident = choice.get("id")
        _require(type(ident) is str and ident in expected, "offered choice identity")
        _require(choice.get("enabled") is True, "offered choice enabled domain")
        identifiers.append(ident)
    _require(set(identifiers) == expected, "unique offered choices")


def _year(command: dict[str, Any], inventory: LookupInventory) -> int | None:
    before, after = (command[key]["view"] for key in ("before", "after"))
    home_id = command["before"]["teams"]["home"]["id"]
    season = inventory.unique_season(home_id)
    for view in (before, after):
        _require(type(view.get("rules_season")) is int, "rules season domain")
        if season is not None:
            _equal(view["rules_season"], season, "pinned home-year policy")
    return season


def _origin(season: int) -> int:
    return 40 if season <= 1985 else 35 if season <= 2006 else 30 if season <= 2011 else 35


def _exposure(
    command: dict[str, Any],
    rows: list[dict[str, Any]],
    typed: dict[str, Any],
    count: int,
    *,
    recovery: bool = False,
) -> None:
    start, end = command["draw_range"]
    draws = count + int(recovery)
    _require(end - start == draws and len(rows) == count, "draw/row exposure")
    begin, finish = command["draw_request_range"]
    requests = typed["draw_requests"][begin:finish]
    _require(len(requests) == draws, "request exposure")
    for index, request in enumerate(requests):
        number = start + index + 1
        _require(
            request["completed"] is True
            and request["expected_type"] == "OffensiveRoll"
            and request["draw_number"] == number,
            "ordered offensive request",
        )
        _require(typed["draws"][number - 1]["kind"] == "offensive", "offensive draw kind")
    for index, row in enumerate(rows):
        number = start + index + 1
        _equal(row["draw_binding"]["captured_draw_numbers"], [number], "role draw reference")
        _require(row["captured_draw_frontier"] == number, "role selection frontier")
    for key in ("priority_range", "priority_attempt_range"):
        _require(command[key][0] == command[key][1], "no " + key)


def _role(row: dict[str, Any], command: dict[str, Any], side: str, column: str) -> int | None:
    address, facts = row["address"], row["facts"]
    _equal(address["team_id"], command["before"]["teams"][side]["id"], "dedicated row side")
    _require(
        address["table"] == "special_teams" and address["column"] == column, "dedicated row role"
    )
    if (
        facts["kind"] not in {"yards", "no_change"}
        or facts["priority"] != "normal"
        or facts["out_of_bounds"]
    ):
        return None
    if facts["variable"] is not None or facts["penalty"] is not None:
        return None
    _require(facts["variable_multiplier"] is None, "numeric multiplier domain")
    if facts["kind"] == "no_change":
        _require(facts["yards"] is None, "no-change yardage domain")
        return 0
    _require(type(facts["yards"]) is int, "numeric yardage domain")
    return facts["yards"]


def _report(
    command: dict[str, Any],
    initial: dict[str, Any],
    final: dict[str, Any],
    *,
    pending: bool,
    report_id: int | None,
    touchback: bool = False,
    recovery: bool = False,
) -> int:
    report = command["returned_report"]
    _require(type(report) is dict, "returned report")
    number = report.get("number")
    _require(type(number) is int and number > 0, "report identity domain")
    if report_id is not None:
        _equal(number, report_id, "retained pending identity")
    _require(
        report["supported"] is True and report["pending"] is pending, "report commitment flags"
    )
    _equal(report["called_play"], "Kickoff", "called family")
    _equal(report["resolved_play"], "Kickoff", "resolved family")
    _equal(report["defense"], "No formation", "defense format")
    _equal(report["yards"], None, "yards sentinel")
    _equal(
        report["outcome"],
        "special_teams_pending"
        if pending
        else "touchback"
        if touchback
        else "kick_recovery"
        if recovery
        else "kickoff_return",
        "outcome",
    )
    _equal(_field(report["state_before"]), initial, "report before field")
    _equal(_field(report["state_after"]), final, "report after field")
    _equal(
        report["statistics"],
        dict(kind="excluded", team=None, yards=0, touchdown=False),
        "excluded-zero credit",
    )
    facts = {
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
    facts.update(
        change_of_possession=not pending and final["possession"] != initial["possession"],
        touchback=touchback,
        unreturned_kickoff=pending or touchback,
    )
    _equal(report["timing"], facts, "independent timing facts")
    _equal(report["extends_quarter"], False, "extends-quarter format")
    changes = command["report_changes"]
    if pending:
        _equal(changes, [], "pending history exposure")
    else:
        _require(
            len(changes) == 1
            and changes[0]["before"] is None
            and changes[0]["index"] == command["before"]["reports"],
            "one appended commitment",
        )
        _equal(changes[0]["after"], report, "appended/returned report")
    return number


def audit_kickoff_commands(
    capture: dict[str, Any],
    *,
    inventory: LookupInventory | None,
    ordinary: dict[str, Any] | None = None,
    pat: dict[str, Any] | None = None,
    supplemental: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check supplied routine commands; initial/external authority stays unknown."""
    typed, block = capture["typed_capture"], capture.get("lookup_rows")
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    chains: dict[int, dict[str, Any]] = {}
    dispositions = []
    known = {
        row["command_number"]: row
        for result in (ordinary, pat, supplemental)
        if result
        for row in result["dispositions"]
        if row["status"] == "GO"
    }
    pat_known = (
        {row["command_number"] for row in pat["dispositions"] if row["status"] == "GO"}
        if pat
        else set()
    )
    for command in typed["commands"]:
        number, game = command["number"], command["game_number"]
        before, after = (command[key]["view"] for key in ("before", "after"))
        chain = chains.setdefault(game, dict(tainted=False, pending=None, kicker=None, seen=[]))
        opening = command["operation"] == "decide" and command["arguments"] in [
            ["toss:kick"],
            ["toss:receive"],
        ]
        kick = command["operation"] == "kick" and command["arguments"] == ["kickoff"]
        touchback_choice = command["operation"] == "decide" and command["arguments"] == [
            "kick:touchback"
        ]
        kind = (
            "opening"
            if opening
            else "kick"
            if kick
            else "touchback"
            if touchback_choice
            else "other"
        )
        reason, core_checked, seconds, deferred = None, False, None, False
        if typed["version"] == "2":
            chain["seen"].extend(report.get("number") for report in command["initial_log"] or [])
        prior_ids = list(chain["seen"])
        rows = [row for row in block["events"] if row["command_number"] == number] if block else []
        if command["exception_type"] is not None:
            reason = "failed_command"
        elif kind == "other":
            counts["excluded"] += 1
            qualified = known.get(number)
            if (
                not qualified
                or qualified.get("game_number", game) != game
                or chain["pending"] is not None
            ):
                chain["tainted"] = True
            elif number in pat_known:
                chain["kicker"] = command["returned_report"]["state_before"]["possession"]
        elif (
            typed["version"] != "2" or block is None or block["version"] != "2" or inventory is None
        ):
            reason = "typed_evidence_prerequisite"
        elif command["before"]["configuration"].get("mode") != "regulation":
            reason = "nonregulation"
        if reason is None and kind != "other":
            reason = _context(before)
            if reason is None and chain["tainted"]:
                reason = "unverified_prior_continuation"
            if reason is None and any(
                row["chart_binding"] != "BOUND"
                or row["record_binding"] != "BOUND"
                or row["draw_binding"]["status"] != "BOUND"
                for row in rows
            ):
                reason = "unbound_kick_rows"
            season = _year(command, cast(LookupInventory, inventory)) if reason is None else None
            if reason is None and (season is None or not 1940 <= season <= 2023):
                reason = "home_year_authority"
            if reason is None:
                _require(
                    all(type(value) is int and value > 0 for value in prior_ids),
                    "prior report identity domain",
                )
                season = cast(int, season)
                origin = _origin(season)
                final: dict[str, Any] = {}
                if opening:
                    _effects(command)
                    _require(before["phase"] == "opening_choice", "opening phase")
                    pending = before.get("pending")
                    _require(type(pending) is dict, "opening chooser")
                    side = pending.get("chooser_side")
                    _require(type(side) is str and side in {"home", "away"}, "opening chooser side")
                    _offered(before, side, {"toss:kick", "toss:receive"})
                    kicker = (
                        side
                        if command["arguments"] == ["toss:kick"]
                        else "away"
                        if side == "home"
                        else "home"
                    )
                    _exposure(command, rows, typed, 0)
                    _equal(command["returned_report"], None, "opening null report")
                    _equal(command["report_changes"], [], "opening history exposure")
                    _equal(_field(after["state"]), _core(kicker, 100 - origin), "opening field")
                    _equal(after.get("opening_kicker"), kicker, "opening kicker")
                    _require(
                        after.get("phase") == "kickoff" and after.get("pending") is None,
                        "opening continuation",
                    )
                    for key in ("clock", "timing_log", "home_timeouts", "away_timeouts"):
                        _equal(after[key], before[key], "opening " + key)
                    _require(_context(after) is None, "opening after context")
                    chain["kicker"] = kicker
                    core_checked = True
                    counts["opening_transitions"] += 1
                    counts["excluded"] += 1
                else:
                    _require(before["phase"] == "kickoff", "kickoff phase")
                    initial = _field(before["state"])
                    kicker = initial["possession"]
                    receiver = "away" if kicker == "home" else "home"
                    if chain["kicker"] is not None:
                        _equal(kicker, chain["kicker"], "assigned kicker")
                    _equal(initial, _core(kicker, 100 - origin), "standard kickoff origin")
                    touchback, pending_result, report_id, recovery_result = (
                        False,
                        False,
                        None,
                        False,
                    )
                    if touchback_choice:
                        retained = chain["pending"]
                        if retained is None:
                            reason = "unbound_initial_pending_kick"
                        else:
                            _offered(before, receiver, {"kick:touchback", "kick:return"})
                            _exposure(command, rows, typed, 0)
                            _equal(initial, retained["initial"], "pending original field")
                            final = _core(receiver, 100 - (20 if season <= 2011 else 25))
                            report_id, touchback = retained["report_id"], True
                    else:
                        _require(
                            chain["pending"] is None and before.get("pending") is None,
                            "new kick pending context",
                        )
                        _require(bool(rows), "missing kick row")
                        flight = _role(rows[0], command, kicker, "kickoff")
                        if flight is None or flight < 0:
                            reason = "kick_flight_authority"
                        else:
                            landing = 100 - origin - flight
                            if landing <= -10:
                                _exposure(command, rows, typed, 1)
                                final = _core(receiver, 100 - (20 if season <= 2011 else 25))
                                touchback = True
                            elif landing <= 0:
                                _exposure(command, rows, typed, 1)
                                final, pending_result = initial, True
                            elif landing <= 99:
                                _require(len(rows) >= 2, "dedicated receiving row")
                                gain = _role(rows[1], command, receiver, "kickoff_return")
                                if gain is None:
                                    facts = rows[1]["facts"]
                                    interval = cast(LookupInventory, inventory).recovery_interval(
                                        command["before"]["teams"][receiver]["id"],
                                        command["before"]["teams"][receiver]["fingerprint"],
                                    )
                                    if (
                                        facts["kind"] != "fumble"
                                        or type(facts["yards"]) is not int
                                        or facts["variable"] is not None
                                        or facts["variable_multiplier"] is not None
                                        or facts["penalty"] is not None
                                        or facts["priority"] != "normal"
                                        or facts["out_of_bounds"]
                                        or not 1 <= landing + facts["yards"] <= 99
                                        or interval is None
                                    ):
                                        reason = "return_terminal_authority"
                                    else:
                                        start, end = command["draw_range"]
                                        _require(end - start >= 3, "missing recovery draw")
                                        roll = typed["draws"][start + 2]
                                        _require(roll["kind"] == "offensive", "recovery draw kind")
                                        retained = interval[0] <= roll["total"] <= interval[1]
                                        if roll["total"] in (
                                            {17, 18, 19} if retained else {37, 38, 39}
                                        ):
                                            reason = "recovery_advance_authority"
                                        else:
                                            _exposure(command, rows, typed, 2, recovery=True)
                                            spot = 100 - landing - facts["yards"]
                                            final = (
                                                _core(receiver, spot)
                                                if retained
                                                else _core(kicker, 100 - spot)
                                            )
                                            recovery_result = True
                                else:
                                    _exposure(command, rows, typed, 2)
                                    if not 1 <= landing + gain <= 99:
                                        reason = "return_terminal_authority"
                                    else:
                                        final = _core(receiver, 100 - (landing + gain))
                            else:
                                reason = "landing_authority"
                    if reason is None:
                        _effects(command)
                        report_number = _report(
                            command,
                            initial,
                            final,
                            pending=pending_result,
                            report_id=report_id,
                            touchback=touchback,
                            recovery=recovery_result,
                        )
                        if kick:
                            _require(
                                report_number not in prior_ids,
                                "report identity reused in same-object prefix",
                            )
                        core_checked = True
                        if pending_result:
                            _equal(_field(after["state"]), initial, "pending live field")
                            _require(after["phase"] == "kickoff", "pending phase")
                            _offered(after, receiver, {"kick:touchback", "kick:return"})
                            for key in ("clock", "timing_log", "home_timeouts", "away_timeouts"):
                                _equal(after[key], before[key], "pending " + key)
                            _require(_context(after) is None, "pending after context")
                            chain["pending"] = dict(
                                initial=deepcopy(initial), report_id=report_number
                            )
                            counts["pending"] += 1
                            seconds = 0
                        else:
                            deferred = (
                                recovery_result and final["possession"] == initial["possession"]
                            )
                            seconds = 0 if touchback else 30 if deferred else 10
                            clock = before.get("clock")
                            _require(
                                type(clock) is dict and type(clock.get("remaining")) is int,
                                "clock remaining domain",
                            )
                            if clock["remaining"] <= seconds:
                                reason = "period_continuation_authority"
                            else:
                                _equal(_field(after["state"]), final, "committed live field")
                                if deferred:
                                    _require(
                                        commitment._ordinary_start(dict(before=command["after"]))
                                        and after["phase"] == "clock_choice",
                                        "deferred recovery continuation",
                                    )
                                else:
                                    _require(
                                        after["phase"] == "scrimmage"
                                        and after.get("pending") is None,
                                        "live continuation",
                                    )
                                _require(
                                    _context(after, deferred=deferred) is None,
                                    "committed after context",
                                )
                                chain["pending"], chain["kicker"] = None, None
                                counts["touchbacks" if touchback else "returned"] += 1
                                counts["recoveries"] += int(recovery_result)
                                counts["committed"] += 1
                        if reason is None:
                            counts["checked"] += 1
        if reason is not None:
            chain["tainted"] = True
            reasons[reason] += 1
        dispositions.append(
            dict(
                command_number=number,
                game_number=game,
                kind=kind,
                status="UNVERIFIED"
                if reason
                else "EXCLUDED"
                if kind in {"opening", "other"}
                else "GO",
                reason=reason
                or (
                    "conditional_opening_anchor"
                    if opening
                    else "nonroutine_command"
                    if kind == "other"
                    else None
                ),
                core_checked=core_checked,
                seconds=seconds,
                deferred=deferred,
                pending=bool(
                    reason is None
                    and kind not in {"opening", "other"}
                    and chain["pending"] is not None
                ),
            )
        )
        if typed["version"] == "2":
            for change in command["report_changes"]:
                if type(change["after"]) is dict:
                    chain["seen"].append(change["after"].get("number"))
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        excluded=counts["excluded"],
        unknown=sum(reasons.values()),
        pending=counts["pending"],
        committed=counts["committed"],
        returned=counts["returned"],
        recoveries=counts["recoveries"],
        touchbacks=counts["touchbacks"],
        opening_transitions=counts["opening_transitions"],
        opening_authority="UNVERIFIED",
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
