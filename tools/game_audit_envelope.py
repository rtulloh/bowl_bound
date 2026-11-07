"""Internal consistency of supplied v1 capture links, without engine imports.

This checks observed command/range/reference boundaries only. It cannot establish
omitted commands, actual game identity, target completeness, revision addresses,
state transitions or terminal football truth.
"""

import hashlib
import json
from copy import deepcopy
from typing import Any, cast

from .game_audit_lookup import LookupEvidenceError, _facts, audit_physical_draws
from .game_audit_priority import _same_fact


class CaptureEvidenceError(ValueError):
    """Supplied capture records disagree with their own declared links."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureEvidenceError(f"typed capture {message}")


def _count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _caller(value: Any) -> None:
    _require(
        type(value) is dict
        and value.keys() == {"module", "function"}
        and all(type(v) is str and bool(v) for v in value.values()),
        "caller fields",
    )


def _boundary(value: Any, indexed: bool) -> None:
    _require(
        type(value) is dict
        and value.keys()
        == {"view", "teams", "configuration", "tape", "reports", "journal_length"}
        | ({"log_sha256"} if indexed else set()),
        "boundary fields",
    )
    _require(
        type(value["view"]) is dict
        and type(value["configuration"]) is dict
        and all(_count(value[k]) for k in ("reports", "journal_length")),
        "boundary types",
    )
    if indexed:
        digest = value["log_sha256"]
        _require(
            type(digest) is str
            and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest),
            "log digest fields",
        )
    teams = cast(dict[str, Any], value["teams"])
    _require(type(teams) is dict and teams.keys() == {"home", "away"}, "team fields")
    for team in teams.values():
        _require(
            type(team) is dict
            and {"id", "fingerprint"}
            <= team.keys()
            <= {"id", "fingerprint", "defense_chart_markers"}
            and type(team["id"]) is str
            and bool(team["id"])
            and type(team["fingerprint"]) is str
            and len(team["fingerprint"]) == 64
            and all(c in "0123456789abcdef" for c in team["fingerprint"]),
            "team identity fields",
        )
        team = cast(dict[str, Any], team)
        if "defense_chart_markers" in team:
            markers = team["defense_chart_markers"]
            _require(
                type(markers) is list
                and all(type(x) is str and x in {"W", "FBO", "SPBO", "XWC"} for x in markers)
                and len(markers) == len(set(markers)),
                "team marker fields",
            )
    tape = cast(dict[str, Any], value["tape"])
    _require(
        type(tape) is dict
        and tape.keys() == {"roll_count", "position", "replaying", "future"}
        and _count(tape["roll_count"])
        and _count(tape["position"])
        and tape["position"] <= tape["roll_count"]
        and tape["replaying"] is False
        and type(tape["future"]) is dict
        and type(tape["future"].get("kind")) is str
        and bool(tape["future"]["kind"]),
        "tape boundary fields",
    )


def _log_content(reports: list[dict[str, Any]]) -> bytes:
    try:
        content = json.dumps(reports, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise CaptureEvidenceError("typed capture log facts are not finite JSON") from error
    return content.encode("utf-8")


def _log_digest(reports: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_log_content(reports)).hexdigest()


def _history(
    command: dict[str, Any], previous: list[dict[str, Any]] | None
) -> tuple[list[dict[str, Any]], int, int]:
    initial = command["initial_log"]
    before, after = command["before"], command["after"]
    if previous is None:
        _require(
            type(initial) is list and all(type(item) is dict for item in initial),
            "initial log fields",
        )
        current = deepcopy(cast(list[dict[str, Any]], initial))
        initial_count = len(initial)
    else:
        _require(initial is None, "repeated initial log")
        current = deepcopy(previous)
        initial_count = 0
    _require(
        len(current) == before["reports"] and _log_digest(current) == before["log_sha256"],
        "before log snapshot disagrees",
    )
    changes = command["report_changes"]
    _require(type(changes) is list, "report changes fields")
    last = -1
    for change in changes:
        _require(
            type(change) is dict and change.keys() == {"index", "before", "after"},
            "report change fields",
        )
        change = cast(dict[str, Any], change)
        index = change["index"]
        _require(
            type(index) is int and last < index < after["reports"] and index <= len(current),
            "report change index",
        )
        last = index
        _require(type(change["after"]) is dict, "report change after facts")
        if index == len(current):
            _require(change["before"] is None, "append has prior facts")
            current.append(deepcopy(change["after"]))
        else:
            _require(
                _log_content([change["before"]]) == _log_content([current[index]])
                and _log_content([change["after"]]) != _log_content([current[index]]),
                "stale or unchanged revision",
            )
            current[index] = deepcopy(change["after"])
    _require(
        len(current) == after["reports"] and _log_digest(current) == after["log_sha256"],
        "after log snapshot disagrees",
    )
    _require(
        _log_content([change["after"] for change in changes])
        == _log_content(command["report_revisions"]),
        "indexed changes/revisions disagree",
    )
    return current, len(changes), initial_count


def audit_capture_links(capture: dict[str, Any]) -> dict[str, Any]:
    """Check supplied links; preserve unresolved attempts and absent authority."""
    envelope = capture["typed_capture"]
    indexed = envelope["version"] == "2"
    commands, requests, attempts = (
        envelope[k] for k in ("commands", "draw_requests", "priority_attempts")
    )
    if "priority" in capture:
        _require(
            type(capture["priority"]) is dict and type(capture["priority"].get("events")) is list,
            "priority inventory fields",
        )
    events = capture.get("priority", {}).get("events", [])
    try:
        draws = audit_physical_draws(envelope["draws"])
    except LookupEvidenceError as error:
        raise CaptureEvidenceError(f"typed capture {error}") from error
    for number, event in enumerate(events, 1):
        _require(
            type(event) is dict and type(event.get("number")) is int and event["number"] == number,
            "priority event numbering",
        )
        _caller(event.get("caller"))
    cursors = dict(draw_range=0, draw_request_range=0, priority_range=0, priority_attempt_range=0)
    inventories = dict(
        draw_range=draws,
        draw_request_range=requests,
        priority_range=events,
        priority_attempt_range=attempts,
    )
    games: dict[int, dict[str, Any]] = {}
    histories: dict[int, list[dict[str, Any]]] = {}
    history_changes = history_initial = 0
    initial_reports = initial_journal = failed = 0
    draw_refs: set[int] = set()
    event_refs: set[int] = set()
    incomplete_draws = incomplete_priority = 0
    command_fields = {
        "number",
        "game_number",
        "operation",
        "arguments",
        "exception_type",
        "before",
        "after",
        "draw_range",
        "draw_request_range",
        "priority_range",
        "priority_attempt_range",
        "report_range",
        "journal_range",
        "returned_report",
        "report_revisions",
    }
    if indexed:
        command_fields |= {"initial_log", "report_changes"}
    for number, command in enumerate(commands, 1):
        _require(command.keys() == command_fields, "command fields")
        _require(
            type(command["number"]) is int and command["number"] == number, "command numbering"
        )
        exception = command["exception_type"]
        _require(exception is None or type(exception) is str and bool(exception), "exception type")
        failed += exception is not None
        game = command["game_number"]
        _require(type(game) is int and game > 0, "game number")
        before, after = command["before"], command["after"]
        _boundary(before, indexed)
        _boundary(after, indexed)
        if indexed:
            history, changes, initial = _history(command, histories.get(game))
            histories[game] = history
            history_changes += changes
            history_initial += initial
        if game not in games:
            _require(game == len(games) + 1, "game object sequence")
            initial_reports += before["reports"]
            initial_journal += before["journal_length"]
        else:
            for key in ("teams", "configuration", "tape", "reports", "journal_length"):
                _require(_same_fact(before[key], games[game][key]), f"inter-command {key} gap")
        for key in ("teams", "configuration"):
            _require(_same_fact(before[key], after[key]), f"within-command {key} changed")
        games[game] = after
        for key, inventory in inventories.items():
            start, end = command[key]
            _require(start == cursors[key] and end <= len(inventory), f"{key} gap/overflow")
            cursors[key] = end
        for key, count in (("report_range", "reports"), ("journal_range", "journal_length")):
            _require(command[key] == [before[count], after[count]], f"{key} boundary mismatch")
        added = after["reports"] - before["reports"]
        _require(
            added >= 0 and added <= len(command["report_revisions"]) <= after["reports"],
            "report revision count",
        )
        _require(after["journal_length"] >= before["journal_length"], "journal shrank")
        consumed = command["draw_range"][1] - command["draw_range"][0]
        _require(
            after["tape"]["position"] == before["tape"]["position"]
            and after["tape"]["roll_count"] - before["tape"]["roll_count"] == consumed,
            "recording tape/draw count mismatch",
        )
        for index in range(*command["draw_request_range"]):
            request = requests[index]
            _require(
                type(request) is dict and type(request.get("completed")) is bool,
                "draw request fields",
            )
            complete = request["completed"]
            fields = {"number", "command_number", "completed", "expected_type"}
            _require(
                request.keys() == fields | ({"draw_number"} if complete else set()),
                "draw request fields",
            )
            _require(
                type(request["number"]) is int
                and request["number"] == index + 1
                and type(request["command_number"]) is int
                and request["command_number"] == number,
                "draw request numbering/command",
            )
            _require(
                request["expected_type"] in ("OffensiveRoll", "DefensiveRoll"), "draw request kind"
            )
            if not complete:
                incomplete_draws += 1
                continue
            reference = request["draw_number"]
            start, end = command["draw_range"]
            _require(
                type(reference) is int and start < reference <= end and reference not in draw_refs,
                "draw request reference",
            )
            expected_kind = (
                "offensive" if request["expected_type"] == "OffensiveRoll" else "defensive"
            )
            reference = cast(int, reference)
            _require(draws[reference][0] == expected_kind, "draw request/result kind")
            draw_refs.add(cast(int, reference))
        for index in range(*command["priority_attempt_range"]):
            attempt = attempts[index]
            _require(
                type(attempt) is dict and type(attempt.get("completed")) is bool,
                "priority attempt fields",
            )
            complete = attempt["completed"]
            fields = {"number", "command_number", "completed", "offense", "defense", "caller"}
            _require(
                attempt.keys() == fields | ({"event_number"} if complete else set()),
                "priority attempt fields",
            )
            _require(
                type(attempt["number"]) is int
                and attempt["number"] == index + 1
                and type(attempt["command_number"]) is int
                and attempt["command_number"] == number,
                "priority attempt numbering/command",
            )
            _caller(attempt["caller"])
            _require(
                type(attempt["offense"]) is dict and type(attempt["defense"]) is dict,
                "priority attempt operands",
            )
            try:
                _facts(attempt["offense"], False)
                _facts(attempt["defense"], False)
            except LookupEvidenceError as error:
                raise CaptureEvidenceError(f"typed capture {error}") from error
            if not complete:
                incomplete_priority += 1
                continue
            reference = attempt["event_number"]
            start, end = command["priority_range"]
            _require(
                type(reference) is int and start < reference <= end and reference not in event_refs,
                "priority attempt reference",
            )
            reference = cast(int, reference)
            event = events[reference - 1]
            _require(
                all(
                    _same_fact(attempt[key], event[key]) for key in ("offense", "defense", "caller")
                ),
                "priority attempt/event disagreement",
            )
            event_refs.add(reference)
    _require(
        all(cursors[key] == len(value) for key, value in inventories.items()),
        "uncovered records outside command ranges",
    )
    _require(draw_refs == set(draws), "draws missing successful requests")
    _require(
        event_refs == set(range(1, len(events) + 1)), "priority events missing successful attempts"
    )
    return dict(
        commands_checked=len(commands),
        draws_checked=len(draws),
        priority_attempts_checked=len(attempts),
        draw_requests_checked=len(requests),
        priority_events_checked=len(events),
        game_objects_observed=len(games),
        failed_commands_observed=failed,
        incomplete_draw_requests=incomplete_draws,
        incomplete_priority_attempts=incomplete_priority,
        initial_reports_not_observed=initial_reports,
        initial_journal_entries_not_observed=initial_journal,
        report_revision_address_linkage=("GO" if history_changes else "NOTRUN")
        if indexed
        else "UNVERIFIED",
        report_history_boundaries_checked=2 * len(commands) if indexed else 0,
        report_changes_checked=history_changes,
        initial_report_facts_checked=history_initial,
        captured_history_matches_final_row="UNVERIFIED",
        external_command_completeness="UNVERIFIED",
        external_game_identity="UNVERIFIED",
        target_completeness="UNVERIFIED",
        unreturned_priority_results="UNVERIFIED" if incomplete_priority else "NOTRUN",
        state_transition_truth="UNVERIFIED",
        terminal_truth="UNVERIFIED",
    )
