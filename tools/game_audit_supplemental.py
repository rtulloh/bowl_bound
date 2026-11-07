"""Independent supplied B/QR/QT/Option graphs; no engine or prose oracle."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, cast

from . import game_audit_commitment as commitment
from . import game_audit_priority as priority
from .game_audit_lookup import LookupInventory


class SupplementalEvidenceError(ValueError):
    """Supplied conditional mechanics contradict independently derived facts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SupplementalEvidenceError("supplemental commitment " + message)


def _equal(actual: Any, expected: Any, label: str) -> None:
    _require(commitment._canonical(actual) == commitment._canonical(expected), label + " differs")


def _blank() -> dict[str, Any]:
    return dict(
        kind="no_change",
        yards=None,
        variable=None,
        variable_multiplier=None,
        priority="normal",
        out_of_bounds=False,
        penalty=None,
        chart_color=None,
    )


def _graph(
    command: dict[str, Any], capture: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Close actual command ranges before inspecting claimed report or credit."""
    typed = capture["typed_capture"]
    ds, de = command["draw_range"]
    rs, re = command["draw_request_range"]
    ps, pe = command["priority_range"]
    draws, requests = typed["draws"][ds:de], typed["draw_requests"][rs:re]
    events = capture["priority"]["events"][ps:pe]
    _require(len(rows) >= 2 and len(draws) >= 2 and bool(events), "initial operand evidence")
    _require(len(requests) == len(draws), "one completed request per consumed draw")
    for draw, request in zip(draws, requests, strict=True):
        _require(
            request["completed"] is True
            and request["draw_number"] == draw["number"]
            and request["expected_type"]
            == ("OffensiveRoll" if draw["kind"] == "offensive" else "DefensiveRoll"),
            "ordered draw/request closure",
        )
    side = commitment._state(command["before"]["view"]["state"])["possession"]
    other = "away" if side == "home" else "home"
    call, formation = command["arguments"]
    resolved = int(call)

    def row_at(
        index: int,
        draw_index: int,
        table: str,
        *,
        play: int | None = None,
        column: str | None = None,
    ) -> dict[str, Any]:
        _require(index < len(rows) and draw_index < len(draws), "missing selected row/draw")
        row, draw = rows[index], draws[draw_index]
        address = row["address"]
        owner = other if table == "defense" else side
        _require(
            address["table"] == table
            and address["team_id"] == command["before"]["teams"][owner]["id"]
            and address["play"] == play
            and address["column"] == column
            and address["formation"] == (formation if table == "defense" else None),
            "selected row role/address",
        )
        _require(
            draw["kind"] == ("defensive" if table == "defense" else "offensive"),
            "selected draw kind",
        )
        _equal(
            row["draw_binding"]["captured_draw_numbers"], [draw["number"]], "selected fresh draw"
        )
        _equal(row["roll"]["faces"], draw["faces"], "selected physical faces")
        _equal(address["roll"], draw["total"], "selected roll total")
        _equal(
            row["captured_draw_frontier"],
            draws[max(1, draw_index)]["number"],
            "selected draw frontier",
        )
        return row["facts"]

    offense = row_at(0, 0, "offense", play=resolved)
    defense = row_at(1, 1, "defense", play=resolved)
    cursor, event_index, supplemental, last_class = 2, 0, 0, None
    redirected = False
    while True:
        _require(event_index < len(events), "missing priority event")
        event = events[event_index]
        _equal(event["offense"], offense, "graph offensive operand")
        _equal(event["defense"], defense, "graph retained defensive operand")
        expected = priority.expected_priority(offense, defense)
        event_index += 1
        kind = expected["kind"]
        if kind in {"B", "QR", "QT", "SOP", "BLP"}:
            selected = defense if expected["operation"] == "D" else offense
            if selected["out_of_bounds"]:
                return dict(reason="nonterminal_marker_bounds_authority")
        if kind in {"SOP", "BLP"}:
            _require(int(call) == 5 and not redirected, "Option redirection origin")
            redirected = True
            resolved = 7 if kind == "SOP" else 8
            defense = _blank()
            offense = row_at(cursor, cursor, "offense", play=resolved)
            cursor += 1
        elif kind in {"B", "QR", "QT"}:
            supplemental += 1
            _require(supplemental <= 10, "supplemental reroll bound")
            if kind in {"QR", "QT"}:
                last_class = kind
            # Cancellation is permanent: only the CURRENT operand may survive.
            if kind == "QT" or expected["operation"] != "ADD":
                defense = _blank()
            offense = row_at(cursor, cursor, "supplemental", column=kind)
            cursor += 1
        else:
            fumble = kind == "fumble" and type(expected["yards"]) is int
            if (expected["pending"] and not fumble) or kind not in {
                "yards",
                "no_change",
                "touchdown",
                "incomplete",
                "fumble",
            }:
                return dict(reason="complex_terminal_authority")
            _require(
                (cursor <= len(rows) if fumble else cursor == len(rows))
                and (fumble or cursor == len(draws))
                and event_index == len(events),
                "entire selected graph closure",
            )
            gain = expected["yards"] if kind in {"yards", "fumble"} else 0
            category = (
                "incomplete"
                if kind == "incomplete"
                else "sack"
                if last_class == "QT" and gain < 0
                else "rush"
                if last_class is not None or resolved <= 5
                else "completion"
            )
            return dict(
                reason=None,
                expected=expected,
                category=category,
                gain=gain,
                resolved=resolved,
                supplemental=supplemental,
                redirected=redirected,
                recovery_draw_index=cursor if fumble else None,
            )


def audit_supplemental_commitments(
    capture: dict[str, Any],
    *,
    typed_inventory_available: bool,
    lookup_inventory: LookupInventory | None = None,
) -> dict[str, Any]:
    """Require prior structural row/history/priority validation; no omitted-command claim."""
    typed = capture["typed_capture"]
    block = capture.get("lookup_rows")
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    dispositions = []
    observed_reports: dict[int, list[Any]] = {}
    for command in typed["commands"]:
        reason = None
        before, args = command["before"]["view"], command["arguments"]
        prior_reports = observed_reports.setdefault(command["game_number"], [])
        if typed["version"] == "2" and command["initial_log"] is not None:
            # Only the first invocation on this actual object carries a full
            # initial log. Later indexed changes/returns remain observed facts.
            prior_reports.extend(deepcopy(command["initial_log"]))
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
            reason = "nonsupplemental_command"
        elif (
            not commitment._ordinary_start(command)
            or before.get("bounds_declaration") is not None
            or before.get("overtime") is not None
            or before.get("hurried", False)
            or command["before"]["configuration"].get("advanced_ii") is not False
            or command["before"]["configuration"].get("mode") not in {"drive", "regulation"}
        ):
            reason = "nonsupplemental_context"
        rows = (
            [row for row in block["events"] if row["command_number"] == command["number"]]
            if block
            else []
        )
        if reason is None and any(
            row["chart_binding"] != "BOUND"
            or row["record_binding"] != "BOUND"
            or row["draw_binding"]["status"] != "BOUND"
            for row in rows
        ):
            reason = "unbound_selected_rows"
        if reason is None:
            ps, pe = command["priority_range"]
            initial = capture["priority"]["events"][ps] if pe > ps else None
            if initial is None:
                reason = "missing_priority_evidence"
            elif priority.expected_priority(initial["offense"], initial["defense"])["kind"] not in {
                "B",
                "QR",
                "QT",
                "SOP",
                "BLP",
            }:
                reason = "not_selected_supplemental"
        graph: dict[str, Any] = {}
        state: dict[str, Any] = {}
        if reason is None:
            graph = cast(dict[str, Any], _graph(command, capture, rows))
            reason = graph["reason"]
        if reason is None:
            state = commitment._state(before["state"])
            if state["yards_to_goal"] - graph["gain"] >= 100:
                reason = "own_goal_authority"
        retained = None
        if reason is None and graph["recovery_draw_index"] is not None:
            side = state["possession"]
            team = command["before"]["teams"][side]
            interval = (
                lookup_inventory.recovery_interval(team["id"], team["fingerprint"])
                if lookup_inventory
                else None
            )
            if interval is None:
                reason = "recovery_range_authority"
            elif not 1 <= state["yards_to_goal"] - graph["gain"] <= 99:
                reason = "recovery_endzone_authority"
            else:
                ds, de = command["draw_range"]
                index = graph["recovery_draw_index"]
                _require(de - ds > index, "missing recovery draw")
                draw = typed["draws"][ds + index]
                _require(draw["kind"] == "offensive", "recovery draw kind")
                retained = interval[0] <= draw["total"] <= interval[1]
                if draw["total"] in ({17, 18, 19} if retained else {37, 38, 39}):
                    reason = "recovery_advance_authority"
                else:
                    _require(de - ds == index + 1, "one recovery draw only")
                    _require(len(rows) == index, "no recovery return lookup")
        detail = dict(command_number=command["number"], game_number=command["game_number"])
        if reason is None:
            category, live = commitment._check_terminal(
                command,
                graph["expected"],
                called=commitment._PLAY_LABELS[int(args[0]) - 1],
                resolved=commitment._PLAY_LABELS[graph["resolved"] - 1],
                category=graph["category"],
                recovered_by_fumbler=retained,
            )
            outcome, _ = commitment._field(state, graph["expected"]["kind"], graph["gain"])
            timing = dict(
                first_down=outcome == "first_down" and retained is not False,
                change_of_possession=outcome == "turnover_on_downs" or retained is False,
                penalty=False,
                incomplete=graph["expected"]["kind"] == "incomplete",
                scoring=outcome == "touchdown",
                touchback=False,
                out_of_bounds=graph["expected"]["out_of_bounds"],
                guaranteed_out_of_bounds=False,
                unreturned_kickoff=False,
                conversion=False,
                no_elapsed_time=False,
            )
            _equal(command["returned_report"]["timing"], timing, "terminal TimingFacts")
            _require(command["returned_report"]["extends_quarter"] is False, "extension flag")
            number = command["returned_report"]["number"]
            for report in prior_reports:
                report = cast(dict[str, Any], report)
                _require(
                    type(report) is dict
                    and type(report.get("number")) is int
                    and report["number"] > 0,
                    "prior report identity",
                )
                _require(number != report["number"], "fresh same-object report identity")
            for name in ("scoring", "timing_log"):
                ledger = before.get(name, [])
                _require(type(ledger) is list, "prior ledger domain")
                for entry in ledger:
                    entry = cast(dict[str, Any], entry)
                    _require(
                        type(entry) is dict
                        and type(entry.get("play_number")) is int
                        and entry["play_number"] > 0,
                        "prior ledger reference domain",
                    )
                    _require(number != entry["play_number"], "fresh prior-ledger report identity")
            counts["report_checked"] += 1
            counts[category] += 1
            counts["recoveries"] += int(retained is not None)
            detail.update(
                derived_yards=graph["gain"], derived_category=category, timing_facts=timing
            )
            if live:
                counts["checked"] += 1
            else:
                reason = "live_continuation_authority"
        if reason is not None:
            reasons[reason] += 1
        detail.update(status="GO" if reason is None else "UNVERIFIED", reason=reason)
        dispositions.append(detail)
        if typed["version"] == "2":
            prior_reports.extend(deepcopy(change["after"]) for change in command["report_changes"])
            if command["returned_report"] is not None:
                prior_reports.append(deepcopy(command["returned_report"]))
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        report_checked=counts["report_checked"],
        unknown=sum(reasons.values()),
        rush=counts["rush"],
        completion=counts["completion"],
        sack=counts["sack"],
        incomplete=counts["incomplete"],
        recoveries=counts["recoveries"],
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
