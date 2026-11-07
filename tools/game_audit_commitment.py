"""Independent fixed ordinary field/stat/score commitments, never engine imports.

Only supplied observed commands are considered. This cannot attest omitted
execution, actual fixture identity, later branches, clocks or source truth.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, cast

from . import game_audit_priority as priority

_PLAY_LABELS = (
    "Line Plunge",
    "Counter",
    "End Reverse",
    "Draw",
    "Option",
    "Screen",
    "Sprint Out",
    "Boot-leg",
    "Drop Back",
)
_BOX_FIELDS = {
    "rushing_attempts",
    "rushing_yards",
    "rushing_touchdowns",
    "passing_attempts",
    "completions",
    "passing_yards",
    "passing_touchdowns",
    "interceptions",
    "sacks_taken",
    "sack_yards_lost",
    "total_plays",
    "total_yards",
}
_CORE = ("possession", "yards_to_goal", "down", "yards_to_go")


class CommitmentEvidenceError(ValueError):
    """A supplied ordinary commitment disagrees with approved BB arithmetic."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CommitmentEvidenceError(f"ordinary commitment {message}")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as error:
        raise CommitmentEvidenceError("ordinary commitment requires finite JSON") from error


def _equal(actual: Any, expected: Any, label: str) -> None:
    _require(_canonical(actual) == _canonical(expected), f"{label} differs")


def _state(value: Any) -> dict[str, Any]:
    _require(type(value) is dict and all(key in value for key in _CORE), "core state fields")
    result: dict[str, Any] = {key: value[key] for key in _CORE}
    _require(
        type(result["possession"]) is str and result["possession"] in {"home", "away"},
        "core possession",
    )
    goal, down, distance = (result[key] for key in _CORE[1:])
    _require(
        all(type(v) is int for v in (goal, down, distance))
        and 1 <= goal <= 99
        and 1 <= down <= 4
        and 1 <= distance <= goal,
        "core field domain",
    )
    return result


def _boxes(view: dict[str, Any]) -> dict[str, dict[str, int]]:
    stats = view.get("statistics")
    _require(type(stats) is dict and {"home", "away"} <= stats.keys(), "complete statistics object")
    result: dict[str, dict[str, int]] = {}
    stats = cast(dict[str, Any], stats)
    for side in ("home", "away"):
        box = stats[side]
        _require(
            type(box) is dict
            and box.keys() == _BOX_FIELDS
            and all(type(v) is int for v in box.values()),
            "complete integer box",
        )
        box = cast(dict[str, int], box)
        _require(
            all(
                v >= 0
                for k, v in box.items()
                if k not in {"rushing_yards", "passing_yards", "total_yards"}
            ),
            "box counter domain",
        )
        result[side] = box
    return result


def _field(before: dict[str, Any], kind: str, gain: int) -> tuple[str, dict[str, Any] | None]:
    side, goal, down, distance = (before[key] for key in _CORE)
    if kind == "touchdown" or gain >= goal:
        return "touchdown", None
    next_goal = goal - gain
    if gain >= distance:
        return "first_down", dict(
            possession=side, yards_to_goal=next_goal, down=1, yards_to_go=min(10, next_goal)
        )
    if down == 4:
        next_goal = 100 - next_goal
        return "turnover_on_downs", dict(
            possession="away" if side == "home" else "home",
            yards_to_goal=next_goal,
            down=1,
            yards_to_go=min(10, next_goal),
        )
    return "advance", dict(
        possession=side,
        yards_to_goal=next_goal,
        down=down + 1,
        yards_to_go=min(distance - gain, next_goal),
    )


def _check(
    command: dict[str, Any],
    event: dict[str, Any],
    rows: list[dict[str, Any]],
    expected: dict[str, Any],
) -> tuple[str, bool]:
    number = command["number"]
    before, after = (command[key]["view"] for key in ("before", "after"))
    _require(all("state" in view for view in (before, after)), "view field key")
    for label in ("home", "away"):
        _require(
            all(
                type(view.get(label)) is str and bool(view[label].strip())
                for view in (before, after)
            ),
            "view team label format",
        )
        _equal(after[label], before[label], "view team label continuity")
    state = _state(before["state"])
    side = state["possession"]
    opponent = "away" if side == "home" else "home"
    call, formation = command["arguments"]
    _require(len(rows) == 2, f"command {number} requires two selected rows")
    _require(
        [row["address"]["table"] for row in rows] == ["offense", "defense"],
        "selected operand order",
    )
    for row, role in zip(rows, (side, opponent), strict=True):
        address = row["address"]
        _require(
            address["team_id"] == command["before"]["teams"][role]["id"]
            and address["play"] == int(call),
            "selected row role/play",
        )
    _require(rows[1]["address"]["formation"] == formation, "selected formation")
    for row, operand in zip(rows, ("offense", "defense"), strict=True):
        _equal(row["facts"], event[operand], f"{operand} row/priority facts")
    label = _PLAY_LABELS[int(call) - 1]
    category = (
        "incomplete"
        if expected["kind"] == "incomplete"
        else "rush"
        if int(call) <= 5
        else "completion"
    )
    return _check_terminal(command, expected, called=label, resolved=label, category=category)


def _check_terminal(
    command: dict[str, Any],
    expected: dict[str, Any],
    *,
    called: str,
    resolved: str,
    category: str,
    recovered_by_fumbler: bool | None = None,
) -> tuple[str, bool]:
    """Reuse independent arithmetic AFTER an independently checked branch graph.

    Callers must establish typed roles, complete selected operands and category;
    no reported credit or engine helper supplies those expectations.
    """
    before, after = (command[key]["view"] for key in ("before", "after"))
    _require(all("state" in view for view in (before, after)), "view field key")
    for label in ("home", "away"):
        _require(
            all(
                type(view.get(label)) is str and bool(view[label].strip())
                for view in (before, after)
            ),
            "view team label format",
        )
        _equal(after[label], before[label], "view team label continuity")
    state = _state(before["state"])
    side = state["possession"]
    changes = command["report_changes"]
    _require(
        len(changes) == 1
        and changes[0]["index"] == command["before"]["reports"]
        and changes[0]["before"] is None,
        "one indexed appended report required",
    )
    report = changes[0]["after"]
    _equal(command["returned_report"], report, "returned/appended report")
    _require(
        type(report["number"]) is int and report["number"] > 0,
        "positive nonboolean report identity",
    )
    _require(
        report["supported"] is True and report["pending"] is False, "ordinary result must commit"
    )
    _equal(_state(report["state_before"]), state, "before field")
    _require(
        report["called_play"] == called and report["resolved_play"] == resolved,
        "called/resolved family",
    )
    kind = expected["kind"]
    gain = expected["yards"] if kind in {"yards", "fumble"} else 0
    outcome, final_state = _field(state, kind, gain)
    if recovered_by_fumbler is not None:
        _require(
            kind == "fumble" and 1 <= state["yards_to_goal"] - gain <= 99, "fixed recovery spot"
        )
        if recovered_by_fumbler:
            if outcome != "turnover_on_downs":
                outcome = "offensive_recovery"
        else:
            goal = 100 - (state["yards_to_goal"] - gain)
            final_state = dict(
                possession="away" if side == "home" else "home",
                yards_to_goal=goal,
                down=1,
                yards_to_go=min(10, goal),
            )
            outcome = "defensive_recovery"
    touchdown = outcome == "touchdown"
    _equal(report["outcome"], outcome, "field outcome")
    _equal(report["yards"], gain, "fixed reported gain")
    _equal(
        _state(report["state_after"]) if report["state_after"] is not None else None,
        final_state,
        "after field",
    )
    credited = state["yards_to_goal"] if touchdown else gain
    expected_credit = dict(kind=category, team=side, yards=credited, touchdown=touchdown)
    _equal(report["statistics"], expected_credit, "derived statistical credit")
    delta = {field: 0 for field in _BOX_FIELDS}
    delta["total_plays"] = 1
    delta["total_yards"] = credited
    if category in {"rush", "sack"}:
        delta.update(rushing_attempts=1, rushing_yards=credited, rushing_touchdowns=int(touchdown))
        if category == "sack":
            delta.update(sacks_taken=1, sack_yards_lost=-credited)
    else:
        delta["passing_attempts"] = 1
        if category == "completion":
            delta.update(completions=1, passing_yards=credited, passing_touchdowns=int(touchdown))
    initial_boxes, final_boxes = _boxes(before), _boxes(after)
    for team in ("home", "away"):
        for field in _BOX_FIELDS:
            _require(
                final_boxes[team][field] - initial_boxes[team][field]
                == (delta[field] if team == side else 0),
                f"{team} {field} delta",
            )
    for view in (before, after):
        _require(
            type(view["score"]) is dict
            and view["score"].keys() == {"home", "away"}
            and all(type(v) is int and v >= 0 for v in view["score"].values()),
            "score types",
        )
    for team in ("home", "away"):
        _require(
            after["score"][team] - before["score"][team]
            == (6 if touchdown and team == side else 0),
            "score award/side delta",
        )
    _require(
        type(before["scoring"]) is list and type(after["scoring"]) is list, "scoring ledger type"
    )
    scoring = list(before["scoring"])
    if touchdown:
        scoring.append(
            dict(
                number=len(scoring) + 1,
                play_number=report["number"],
                team=before[side],
                kind="touchdown",
                points=6,
            )
        )
    _equal(after["scoring"], scoring, "scoring ledger")
    # Report/credit/box/score facts must pass before any unproved continuation
    # can remain unknown. A supplied phase never establishes period legitimacy.
    live_linked = True
    mode = command["before"]["configuration"]["mode"]
    if touchdown:
        _require(
            after["phase"] == "conversion_choice" and after["state"] is None,
            "TD conversion-choice state",
        )
    elif mode == "drive":
        _require(after["phase"] == "scrimmage", "ordinary drive non-scoring phase")
        _equal(_state(after["state"]), final_state, "after view field")
    elif after["phase"] == "clock_choice":
        _require(after.get("clock_optional") is True, "regulation clock-choice format")
        _equal(_state(after["state"]), final_state, "after view field")
    elif after["phase"] == "scrimmage":
        _equal(_state(after["state"]), final_state, "after view field")
    else:
        live_linked = False
    return category, live_linked


def _ordinary_start(command: dict[str, Any]) -> bool:
    """Recognize supplied ordinary starts; do not certify full menu legality."""
    before = command["before"]["view"]
    _require("state" in before, "view field key")
    if before["phase"] == "scrimmage":
        return before["pending"] is None
    if (
        before["phase"] != "clock_choice"
        or command["before"]["configuration"].get("mode") != "regulation"
        or before.get("clock_optional") is not True
        or before.get("armed_timeout") is not None
        or before.get("conditional_timeout") is not False
        or before.get("untimed_down") is not False
    ):
        return False
    _require("pending" in before, "optional clock pending key")
    pending = before["pending"]
    if pending is None:
        return True
    _require(isinstance(pending, dict), "optional clock menu type")
    _require(
        all(
            k in pending
            for k in (
                "choices",
                "chooser_side",
                "decision_outcomes",
                "razzle_context",
                "decision_context",
            )
        ),
        "optional clock menu fields",
    )
    _equal(pending["decision_outcomes"], [], "optional clock outcomes")
    _require(
        pending["razzle_context"] is None and pending["decision_context"] is None,
        "optional clock mandatory context",
    )
    _require(
        pending["chooser_side"] == _state(before["state"])["possession"], "optional clock side"
    )
    choices = pending["choices"]
    _require(isinstance(choices, list) and bool(choices), "optional clock choices")
    allowed = {
        "clock:timeout:home",
        "clock:timeout:away",
        "clock:hurry",
        "clock:delay",
        "clock:spike",
    }
    ids = []
    for choice in choices:
        _require(
            isinstance(choice, dict)
            and type(choice.get("id")) is str
            and choice["id"] in allowed
            and type(choice.get("enabled")) is bool,
            "optional clock choice format",
        )
        ids.append(choice["id"])
    _require(len(ids) == len(set(ids)), "optional clock duplicate choice")
    return True


def audit_ordinary_commitments(
    capture: dict[str, Any], *, typed_inventory_available: bool
) -> dict[str, Any]:
    """Check already structurally validated supplied captures; never omitted commands.

    The caller first runs the reviewed envelope/row/priority validators. Without
    those prerequisites these inputs have no qualification authority.
    """
    typed = capture["typed_capture"]
    block = capture.get("lookup_rows")
    events = capture.get("priority", {}).get("events", [])
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    dispositions = []
    for command in typed["commands"]:
        reason = None
        args = command["arguments"]
        before = command["before"]["view"]
        if (
            typed["version"] != "2"
            or block is None
            or block["version"] != "2"
            or not typed_inventory_available
        ):
            reason = "typed_evidence_prerequisite"
        elif command["exception_type"] is not None:
            reason = "failed_command"
        elif (
            command["operation"] != "snap"
            or len(args) != 2
            or args[0] not in set("123456789")
            or args[1] not in set("ABCDEF")
        ):
            reason = "nonordinary_command"
        elif (
            not _ordinary_start(command)
            or before.get("bounds_declaration") is not None
            or before.get("overtime") is not None
            or before.get("hurried", False)
            or command["before"]["configuration"].get("advanced_ii") is not False
            or command["before"]["configuration"].get("mode") not in {"drive", "regulation"}
        ):
            reason = "nonordinary_context"
        selected = (
            [row for row in block["events"] if row["command_number"] == command["number"]]
            if block
            else []
        )
        if reason is None and any(
            row["chart_binding"] != "BOUND"
            or row["record_binding"] != "BOUND"
            or row["draw_binding"]["status"] != "BOUND"
            for row in selected
        ):
            reason = "unbound_selected_rows"
        start, end = command["priority_range"]
        if reason is None and end - start != 1:
            reason = "nonordinary_priority_chain"
        event: dict[str, Any] = {}
        expected: dict[str, Any] = {}
        if reason is None:
            event = events[start]
            expected = priority.expected_priority(event["offense"], event["defense"])
            if expected["pending"] or expected["kind"] not in {
                "yards",
                "no_change",
                "incomplete",
                "touchdown",
            }:
                reason = "nonordinary_primary_result"
            elif (
                expected["kind"] == "yards"
                and _state(before["state"])["yards_to_goal"] - expected["yards"] >= 100
            ):
                reason = "own_goal_authority"
        if reason is None:
            category, live_linked = _check(command, event, selected, expected)
            counts[category] += 1
            counts["report_checked"] += 1
            if live_linked:
                counts["checked"] += 1
            else:
                reason = "live_continuation_authority"
        if reason is not None:
            reasons[reason] += 1
        dispositions.append(
            dict(
                command_number=command["number"],
                game_number=command["game_number"],
                status="GO" if reason is None else "UNVERIFIED",
                reason=reason,
            )
        )
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        report_checked=counts["report_checked"],
        unknown=sum(reasons.values()),
        rush=counts["rush"],
        completion=counts["completion"],
        incomplete=counts["incomplete"],
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
