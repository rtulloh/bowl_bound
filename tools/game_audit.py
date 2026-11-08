"""Independent, read-only checks over retained structured game receipts.

This observer imports no engine code and never interprets commentary or chart
cell strings. It verifies the listed accounting invariants, not chart resolution.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, cast

from .game_audit_clock import ClockEvidenceError, audit_standard_clock
from .game_audit_commitment import CommitmentEvidenceError, audit_ordinary_commitments
from .game_audit_continuity import ContinuityEvidenceError, audit_ordinary_continuity
from .game_audit_envelope import CaptureEvidenceError, audit_capture_links
from .game_audit_final_binding import FinalBindingEvidenceError, audit_final_row_binding
from .game_audit_kickoff import KickoffEvidenceError, audit_kickoff_commands
from .game_audit_lookup import LookupEvidenceError, LookupInventory, audit_lookup
from .game_audit_pat import PatEvidenceError, audit_pat_reports
from .game_audit_penalty import PenaltyEvidenceError, audit_penalty_commitments
from .game_audit_priority import PriorityEvidenceError, audit_priority
from .game_audit_punt import PuntEvidenceError, audit_punt_commitments
from .game_audit_row_links import RowLinkEvidenceError, audit_row_links
from .game_audit_supplemental import SupplementalEvidenceError, audit_supplemental_commitments

LABEL_FIELDS = {
    "Rushing attempts": "rushing_attempts",
    "Rushing yards": "rushing_yards",
    "Rushing touchdowns": "rushing_touchdowns",
    "Pass attempts": "passing_attempts",
    "Completions": "completions",
    "Passing yards": "passing_yards",
    "Passing touchdowns": "passing_touchdowns",
    "Interceptions thrown": "interceptions",
    "Sacks taken": "sacks_taken",
    "Sack yards lost": "sack_yards_lost",
    "Total offensive plays": "total_plays",
    "Total offense yards": "total_yards",
}
SCORE_POINTS = {
    "touchdown": 6,
    "field_goal": 3,
    "safety": 2,
    "pat": 1,
    "two_point": 2,
    "conversion_return": 2,
}
CREDIT_KINDS = {"excluded", "rush", "completion", "incomplete", "interception", "sack"}
OBSERVER_VERSION = "21"
INVENTORY_VERSION = "1"


class ReceiptAuditError(ValueError):
    """The first inconsistent structured event or box fact."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptAuditError(message)


def _fold(reports: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    totals = {side: dict.fromkeys(LABEL_FIELDS.values(), 0) for side in ("home", "away")}
    for report in reports:
        credit = report["statistics"]
        kind = credit["kind"]
        if kind == "excluded":
            continue
        own = totals[credit["team"]]
        yards, touchdown = credit["yards"], int(credit["touchdown"])
        own["total_plays"] += 1
        own["total_yards"] += yards
        if kind in {"rush", "sack"}:
            own["rushing_attempts"] += 1
            own["rushing_yards"] += yards
            own["rushing_touchdowns"] += touchdown
            if kind == "sack":
                own["sacks_taken"] += 1
                own["sack_yards_lost"] -= yards
        else:
            own["passing_attempts"] += 1
            own["passing_yards"] += yards
            own["passing_touchdowns"] += touchdown
            own["completions"] += int(kind == "completion")
            own["interceptions"] += int(kind == "interception")
    return totals


def _compare_totals(
    actual: dict[str, Any], expected: dict[str, dict[str, int]], label: str
) -> None:
    for side, fields in expected.items():
        for field, value in fields.items():
            measured = actual.get(side, {}).get(field)
            _require(
                type(measured) is int and measured == value, f"{label}: {side} {field} differs"
            )


def _score_totals(
    events: list[dict[str, Any]], names: dict[str, str], reports: set[int]
) -> dict[str, int]:
    totals = {"home": 0, "away": 0}
    previous = 0
    for index, event in enumerate(events, 1):
        number = event["play_number"]
        _require(
            event["number"] == index and number > previous and number in reports,
            f"scoring event {index}: invalid report ownership/order",
        )
        _require(event["team"] in names, f"scoring event {index}: unknown team")
        _require(
            event["kind"] in SCORE_POINTS
            and type(event["points"]) is int
            and event["points"] == SCORE_POINTS[event["kind"]],
            f"scoring event {index}: points differ from award kind",
        )
        totals[names[event["team"]]] += event["points"]
        previous = number
    return totals


def _evidence_inventory(row: dict[str, Any], reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe legacy evidence without upgrading retained claims to verification."""
    declared = row["final"].get("report_count")
    if "report_count" in row["final"]:
        _require(
            type(declared) is int and declared == len(reports),
            "final report count differs from retained inventory or is invalid",
        )
    for name in ("runtime", "configuration", "save_replay", "audit_capture"):
        _require(
            name not in row or isinstance(row[name], dict), f"{name} evidence is not an object"
        )
    runtime, configuration = row.get("runtime", {}), row.get("configuration", {})
    return {
        "version": INVENTORY_VERSION,
        "input_format": "unversioned_retained_game",
        "report_count": {
            "actual": len(reports),
            "declared": declared,
            "status": "GO" if declared is not None else "UNVERIFIED",
        },
        "runtime_claims": {
            "status": "UNVERIFIED",
            "reason": "Retained identity claims are inventoried, not independently attested.",
            "present": "runtime" in row,
            "python": runtime.get("python"),
            "executable": runtime.get("executable"),
            "rules_profile": runtime.get("rules_profile"),
            "rules_document_sha256": runtime.get("rules_document_sha256"),
            "source_hash_count": len(runtime["source_sha256"])
            if isinstance(runtime.get("source_sha256"), dict)
            else None,
            "loaded_module_count": len(runtime["loaded_modules"])
            if isinstance(runtime.get("loaded_modules"), dict)
            else None,
            "engine_coach_policy": configuration.get("engine_coach_policy"),
            "simulation_coach_policy": configuration.get("simulation_coach_policy"),
        },
        "replay_claims": {
            "status": "UNVERIFIED",
            "reason": "Replay flags are not independent pending-save or source-position evidence.",
            "retained": dict(row.get("save_replay", {})),
        },
        "typed_lookup_priority": {
            "status": "UNVERIFIED",
            "reason": "Frozen lookup, capture completeness and terminal resolution are unverified.",
        },
        "command_pending_boundaries": {
            "status": "UNVERIFIED",
            "reason": "No complete command/pending boundary tape in the legacy receipt.",
        },
    }


def audit_receipt(
    row: dict[str, Any], *, lookup_inventory: LookupInventory | dict[str, Any] | None = None
) -> dict[str, Any]:
    """Audit all retained reports; explicitly report missing independent evidence."""
    _require(isinstance(row, dict), "receipt evidence is not an object")
    _require(isinstance(row.get("final"), dict), "final evidence is not an object")
    _require(
        row.get("status") == "passed" and row["final"].get("finished") is True,
        "receipt is not a successfully completed game",
    )
    reports = row["engine_log"]
    _require(
        isinstance(reports, list) and bool(reports),
        "receipt has no retained reports or an invalid report inventory",
    )
    inventory = _evidence_inventory(row, reports)
    capture = row.get("audit_capture", {})
    capture_links = None
    if "typed_capture" in capture:
        envelope = capture["typed_capture"]
        core = {
            "version",
            "usable",
            "errors",
            "commands",
            "draws",
            "draw_requests",
            "foreign_tape_requests",
            "unprofiled_commands",
            "priority_attempts",
            "replay_commands_skipped",
            "targets",
            "aliases",
            "scope",
        }
        _require(
            type(envelope) is dict
            and core == envelope.keys()
            and type(envelope.get("version")) is str
            and envelope["version"] in {"1", "2"}
            and envelope.get("usable") is True
            and type(envelope.get("errors")) is list
            and not envelope["errors"],
            "typed capture is unsupported or contains collector/identity failures",
        )
        for field in (
            "commands",
            "draws",
            "draw_requests",
            "foreign_tape_requests",
            "unprofiled_commands",
            "priority_attempts",
            "targets",
            "aliases",
        ):
            _require(type(envelope[field]) is list, f"typed capture {field} inventory")
        _require(
            bool(envelope["targets"])
            and not envelope["foreign_tape_requests"]
            and not envelope["unprofiled_commands"],
            "typed capture core commands/targets or isolation failures",
        )
        envelope = cast(dict[str, Any], envelope)
        _require(
            type(envelope["replay_commands_skipped"]) is int
            and envelope["replay_commands_skipped"] >= 0
            and type(envelope["scope"]) is str
            and bool(envelope["scope"]),
            "typed capture replay/scope fields",
        )
        target_fields = {
            "module",
            "name",
            "path",
            "line",
            "source_sha256",
            "process_local_code_sha256",
            "code_digest_scope",
            "module_file",
            "module_spec_origin",
        }
        for target in envelope["targets"]:
            _require(
                type(target) is dict and target_fields == target.keys(),
                "typed capture target identity fields",
            )
            target = cast(dict[str, Any], target)
            _require(
                type(target["line"]) is int
                and target["line"] > 0
                and all(
                    type(target[field]) is str and bool(target[field])
                    for field in target_fields - {"line"}
                ),
                "typed capture target identity types",
            )
            target = cast(dict[str, Any], target)
            for field in ("source_sha256", "process_local_code_sha256"):
                digest = target[field]
                _require(
                    len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
                    "typed capture target digest shape",
                )
        _require(
            len({(target["module"], target["name"]) for target in envelope["targets"]})
            == len(envelope["targets"]),
            "typed capture duplicate targets",
        )
        for alias in envelope["aliases"]:
            _require(
                type(alias) is dict
                and {"module", "name"} == alias.keys()
                and all(
                    type(alias[field]) is str and bool(alias[field]) for field in ("module", "name")
                ),
                "typed capture alias fields",
            )
        _require(
            len({(alias["module"], alias["name"]) for alias in envelope["aliases"]})
            == len(envelope["aliases"]),
            "typed capture duplicate aliases",
        )
        ranges = {
            "draw_range",
            "draw_request_range",
            "priority_range",
            "priority_attempt_range",
            "report_range",
            "journal_range",
        }
        command_fields = ranges | {
            "number",
            "game_number",
            "operation",
            "arguments",
            "exception_type",
            "before",
            "after",
            "returned_report",
            "report_revisions",
        }
        for number, command in enumerate(envelope["commands"], 1):
            _require(
                type(command) is dict and command_fields <= command.keys(),
                "typed capture command fields",
            )
            command = cast(dict[str, Any], command)
            _require(
                type(command["number"]) is int
                and command["number"] == number
                and type(command["game_number"]) is int
                and command["game_number"] > 0
                and type(command["operation"]) is str
                and bool(command["operation"])
                and type(command["arguments"]) is list
                and all(type(arg) is str for arg in command["arguments"])
                and (command["exception_type"] is None or type(command["exception_type"]) is str),
                "typed capture command identity/types",
            )
            for field in ranges:
                value: Any = command[field]
                _require(
                    type(value) is list
                    and len(value) == 2
                    and all(type(bound) is int for bound in value)
                    and 0 <= cast(int, value[0]) <= cast(int, value[1]),
                    "typed capture range shape",
                )
            for boundary in ("before", "after"):
                value = command[boundary]
                _require(
                    type(value) is dict
                    and {"view", "teams", "configuration", "tape", "reports", "journal_length"}
                    <= value.keys(),
                    "typed capture live boundary fields",
                )
                value = cast(dict[str, Any], value)
                _require(
                    all(
                        type(value[field]) is dict
                        for field in ("view", "teams", "configuration", "tape")
                    )
                    and all(
                        type(value[field]) is int and value[field] >= 0
                        for field in ("reports", "journal_length")
                    ),
                    "typed capture live boundary types",
                )
            _require(
                type(command["report_revisions"]) is list
                and all(type(report) is dict for report in command["report_revisions"])
                and (
                    command["returned_report"] is None or type(command["returned_report"]) is dict
                ),
                "typed capture report revision types",
            )
        try:
            capture_links = audit_capture_links(capture)
        except CaptureEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    lookup_counts = None
    frozen = None
    if lookup_inventory is not None:
        try:
            frozen = (
                lookup_inventory
                if isinstance(lookup_inventory, LookupInventory)
                else LookupInventory(lookup_inventory)
            )
        except LookupEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    if "lookup" in capture:
        _require(lookup_inventory is not None, "lookup evidence requires external inventory")
        try:
            frozen = (
                lookup_inventory
                if isinstance(lookup_inventory, LookupInventory)
                else LookupInventory(lookup_inventory)
            )
            lookup_counts = audit_lookup(capture["lookup"], frozen)
        except LookupEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    row_counts = None
    if "lookup_rows" in capture:
        try:
            row_counts = audit_row_links(capture, frozen)
        except RowLinkEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    priority_events = None
    if "priority" in capture:
        try:
            priority_events = audit_priority(capture["priority"])
        except PriorityEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    commitment_counts = None
    if "typed_capture" in capture:
        try:
            commitment_counts = audit_ordinary_commitments(
                capture, typed_inventory_available=frozen is not None
            )
        except CommitmentEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    supplemental_counts = None
    if "typed_capture" in capture:
        try:
            supplemental_counts = audit_supplemental_commitments(
                capture, typed_inventory_available=frozen is not None, lookup_inventory=frozen
            )
        except (SupplementalEvidenceError, CommitmentEvidenceError, LookupEvidenceError) as error:
            raise ReceiptAuditError(str(error)) from error
    pat_counts = None
    if "typed_capture" in capture:
        try:
            pat_counts = audit_pat_reports(capture, typed_inventory_available=frozen is not None)
        except PatEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    penalty_counts = None
    if "typed_capture" in capture:
        try:
            penalty_counts = audit_penalty_commitments(
                capture, typed_inventory_available=frozen is not None
            )
        except (PenaltyEvidenceError, CommitmentEvidenceError) as error:
            raise ReceiptAuditError(str(error)) from error
    punt_counts = None
    if "typed_capture" in capture:
        try:
            punt_counts = audit_punt_commitments(
                capture, typed_inventory_available=frozen is not None
            )
        except (PuntEvidenceError, KickoffEvidenceError, CommitmentEvidenceError) as error:
            raise ReceiptAuditError(str(error)) from error
    kickoff_counts = None
    if "typed_capture" in capture:
        try:
            kickoff_counts = audit_kickoff_commands(
                capture,
                inventory=frozen,
                ordinary=commitment_counts,
                pat=pat_counts,
                supplemental=supplemental_counts,
            )
        except (KickoffEvidenceError, LookupEvidenceError, KeyError) as error:
            raise ReceiptAuditError(str(error)) from error
    clock_counts = None
    if commitment_counts is not None:
        try:
            clock_counts = audit_standard_clock(
                capture,
                ordinary=commitment_counts,
                typed_inventory_available=frozen is not None,
                pat=pat_counts,
                kickoff=kickoff_counts,
                supplemental=supplemental_counts,
            )
        except ClockEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    continuity_counts = None
    if commitment_counts is not None and clock_counts is not None:
        try:
            continuity_counts = audit_ordinary_continuity(
                capture,
                ordinary=commitment_counts,
                clock=clock_counts,
                punt=punt_counts,
                kickoff=kickoff_counts,
                supplemental=supplemental_counts,
                typed_inventory_available=frozen is not None,
            )
        except ContinuityEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    final_binding = None
    if "final_object" in capture:
        try:
            final_binding = audit_final_row_binding(row, capture)
        except FinalBindingEvidenceError as error:
            raise ReceiptAuditError(str(error)) from error
    decisions: dict[int, str] = {}
    for decision in capture.get("decisions", []):
        number, choice = decision["report_number"], decision["choice"]
        _require(
            type(number) is int and 1 <= number <= len(reports),
            "acceptance capture refers to a missing report",
        )
        _require(
            reports[number - 1]["outcome"] == "penalty_accepted",
            f"acceptance capture report {number} is not an accepted penalty",
        )
        _require(
            number not in decisions or decisions[number] == choice,
            f"report {number}: conflicting decision evidence",
        )
        decisions[number] = choice
    unverified_penalties = []
    counts: Counter[str] = Counter()
    names = {}
    for number, report in enumerate(reports, 1):
        prefix = f"report {number}"
        _require(
            type(report["number"]) is int and report["number"] == number,
            f"{prefix}: noncontiguous or invalid report identity",
        )
        _require(
            report["supported"] is True and report["pending"] is False,
            f"{prefix}: completed receipt contains unsupported or pending report",
        )
        for state in (report.get("state_before"), report.get("state_after")):
            if state is not None:
                side, name = state["possession"], state["possession_name"]
                _require(
                    side in {"home", "away"} and names.get(name, side) == side,
                    f"{prefix}: ambiguous state ownership",
                )
                names[name] = side
        credit = report["statistics"]
        kind, team, yards, touchdown = (
            credit[key] for key in ("kind", "team", "yards", "touchdown")
        )
        _require(
            kind in CREDIT_KINDS and type(yards) is int and type(touchdown) is bool,
            f"{prefix}: invalid credit shape",
        )
        counts[kind] += 1
        excluded = (
            not report["supported"]
            or report["pending"]
            or report["outcome"] in {"pre_snap", "offsetting"}
            or report.get("timing", {}).get("conversion", False)
        )
        if excluded:
            _require(kind == "excluded", f"{prefix}: voided/conversion event must be excluded")
        if kind == "excluded":
            _require(
                team is None and yards == 0 and not touchdown,
                f"{prefix}: excluded credit has team, yards or touchdown",
            )
        else:
            before = report.get("state_before")
            _require(
                before is not None and team == before["possession"],
                f"{prefix}: offensive statistic ownership differs from pre-play possession",
            )
            if kind in {"incomplete", "interception"}:
                _require(yards == 0 and not touchdown, f"{prefix}: {kind} credited yards/touchdown")
            if kind == "sack":
                _require(yards < 0 and not touchdown, f"{prefix}: sack is not a negative rush")
            if touchdown:
                _require(
                    any(
                        event["play_number"] == number
                        and event["kind"] == "touchdown"
                        and names.get(event["team"]) == team
                        for event in row["final"]["scoring"]
                    ),
                    f"{prefix}: credited touchdown lacks same-side award",
                )
        if report["outcome"] == "penalty_accepted":
            choice = decisions.get(number, "")
            fields = choice.split(":")
            if (
                len(fields) != 3
                or fields[0] != "accept"
                or not fields[1].isdigit()
                or fields[2] not in {"previous", "end"}
            ):
                unverified_penalties.append(number)
            elif fields[2] == "previous":
                _require(kind == "excluded", f"{prefix}: previous-spot acceptance retained credit")
                counts["accepted_previous"] += 1
            else:
                if report.get("resolved_play") is not None and not excluded:
                    _require(
                        kind != "excluded" and yards == report["yards"],
                        f"{prefix}: end acceptance differs from underlying gain",
                    )
                counts["accepted_end"] += 1
    expected = _fold(reports)
    _compare_totals(row["final"]["statistics"], expected, "final statistics")
    numbers = {report["number"] for report in reports}
    scores = _score_totals(row["final"]["scoring"], names, numbers)
    for side in ("home", "away"):
        _require(scores[side] == row["final"][f"{side}_score"], f"final score: {side} differs")
    halftime = capture.get("halftime", [])
    _require(len(halftime) <= 1, "halftime: multiple different boundary snapshots")
    if halftime:
        half = halftime[0]
        boundary = half["report_number"]
        _require(type(boundary) is int and boundary in numbers, "halftime: missing report boundary")
        prefix_reports = reports[:boundary]
        half_totals = _fold(prefix_reports)
        _compare_totals(half["statistics"], half_totals, "halftime statistics")
        events = [event for event in row["final"]["scoring"] if event["play_number"] <= boundary]
        half_scores = _score_totals(events, names, set(range(1, boundary + 1)))
        for side in ("home", "away"):
            recap = half["recap"][side]
            _require(
                half["score"][side] == recap["total"] == half_scores[side]
                and recap["first"] + recap["second"] == recap["total"],
                f"halftime: {side} score differs",
            )
        rows = half["recap"]["statistics"]
        _require(
            len(rows) == len(LABEL_FIELDS) and {x["label"] for x in rows} == set(LABEL_FIELDS),
            "halftime: incomplete or duplicated box rows",
        )
        for item in rows:
            for side in ("home", "away"):
                _require(
                    item[side] == str(half_totals[side][LABEL_FIELDS[item["label"]]]),
                    f"halftime: {side} {item['label']} differs",
                )
    accepted_status = (
        "UNVERIFIED"
        if unverified_penalties
        else "GO"
        if counts["accepted_previous"] + counts["accepted_end"]
        else "NOTRUN"
    )
    report_count = len(reports)
    owned = report_count - counts["excluded"]
    awards = len(row["final"]["scoring"])
    coverage = {
        "punt_fair_catch_commitment": dict(
            checked=punt_counts["checked"] if punt_counts else 0,
            excluded=punt_counts["excluded"] if punt_counts else 0,
            unknown=punt_counts["unknown"] if punt_counts else report_count,
        ),
        "accepted_previous_penalty_commitment": dict(
            checked=penalty_counts["checked"] if penalty_counts else 0,
            excluded=penalty_counts["excluded"] if penalty_counts else 0,
            unknown=penalty_counts["unknown"] if penalty_counts else report_count,
        ),
        "supplemental_commitment": dict(
            checked=supplemental_counts["checked"] if supplemental_counts else 0,
            excluded=0,
            unknown=supplemental_counts["unknown"] if supplemental_counts else report_count,
        ),
        "ordinary_kickoff_commitment": dict(
            checked=kickoff_counts["checked"] if kickoff_counts else 0,
            excluded=kickoff_counts["excluded"] if kickoff_counts else 0,
            unknown=kickoff_counts["unknown"] if kickoff_counts else report_count,
        ),
        "final_row_linkage": dict(
            checked=1 if final_binding is not None else 0,
            excluded=0,
            unknown=0 if final_binding is not None else 1,
        ),
        "pat_report_commitment": dict(
            checked=pat_counts["checked"] if pat_counts else 0,
            excluded=pat_counts["excluded"] if pat_counts else 0,
            unknown=pat_counts["unknown"] if pat_counts else report_count,
        ),
        "ordinary_continuity": dict(
            checked=continuity_counts["checked"] if continuity_counts else 0,
            excluded=0,
            unknown=continuity_counts["unknown"] if continuity_counts else report_count,
        ),
        "standard_clock": dict(
            checked=clock_counts["checked"] if clock_counts else 0,
            excluded=0,
            unknown=clock_counts["unknown"] if clock_counts else report_count,
        ),
        "ordinary_commitment": dict(
            checked=commitment_counts["checked"] if commitment_counts else 0,
            excluded=0,
            unknown=commitment_counts["unknown"] if commitment_counts else report_count,
        ),
        "captured_row_linkage": dict(
            checked=row_counts["rows_linked"] if row_counts else 0,
            excluded=0,
            unknown=row_counts["rows_unverified"] if row_counts else report_count,
        ),
        "capture_report_history": dict(
            checked=(
                capture_links["report_changes_checked"]
                + capture_links["initial_report_facts_checked"]
            )
            if capture_links
            else 0,
            excluded=0,
            unknown=0
            if capture_links and capture["typed_capture"]["version"] == "2"
            else report_count,
        ),
        "capture_internal_linkage": dict(
            checked=capture_links["commands_checked"] if capture_links else 0,
            excluded=0,
            unknown=report_count if capture_links is None else 0,
        ),
        "typed_lookup_agreement": dict(
            checked=lookup_counts["lookups_checked"]
            if lookup_counts
            else row_counts["typed_rows_checked"]
            if row_counts
            else 0,
            excluded=0,
            unknown=row_counts["typed_rows_unknown"]
            if row_counts
            else report_count
            if lookup_counts is None
            else 0,
        ),
        "supplied_physical_draws": dict(
            checked=lookup_counts["draws_checked"]
            if lookup_counts
            else row_counts["physical_draws"]
            if row_counts
            else 0,
            excluded=0,
            unknown=report_count if lookup_counts is None and row_counts is None else 0,
        ),
        "symbolic_priority": dict(
            checked=priority_events or 0,
            excluded=0,
            unknown=report_count if priority_events is None else 0,
        ),
        "event_ownership": dict(checked=owned, excluded=counts["excluded"], unknown=0),
        "excluded_statistics": dict(checked=counts["excluded"], excluded=owned, unknown=0),
        "credit_shape": dict(checked=report_count, excluded=0, unknown=0),
        "final_statistics": dict(checked=2, excluded=0, unknown=0),
        "scoring_awards": dict(checked=awards, excluded=0, unknown=0),
        "scoring_totals": dict(checked=2, excluded=0, unknown=0),
        "accepted_voided_statistics": dict(
            checked=counts["accepted_previous"] + counts["accepted_end"],
            excluded=report_count
            - counts["accepted_previous"]
            - counts["accepted_end"]
            - len(unverified_penalties),
            unknown=len(unverified_penalties),
        ),
        "halftime": dict(checked=len(halftime), excluded=0, unknown=int(not halftime)),
    }
    for name in (
        "chart_priority_and_cells",
        "all_called_resolved_branches",
        "pending_choice_save",
        "forced_rare_branch_coverage",
        "independent_period_attribution",
    ):
        coverage[name] = dict(checked=0, excluded=0, unknown=report_count)
    return {
        "observer_version": OBSERVER_VERSION,
        "evidence_inventory": inventory,
        "status": "partial_pass",
        "reports_checked": len(reports),
        "event_counts": dict(sorted(counts.items())),
        "components": {
            "punt_fair_catch_commitment": (
                "UNVERIFIED"
                if punt_counts is None or punt_counts["unknown"]
                else "GO"
                if punt_counts["checked"]
                else "NOTRUN"
            ),
            "accepted_previous_penalty_commitment": (
                "UNVERIFIED"
                if penalty_counts is None or penalty_counts["unknown"]
                else "GO"
                if penalty_counts["checked"]
                else "NOTRUN"
            ),
            "supplemental_commitment": (
                "UNVERIFIED"
                if supplemental_counts is None or supplemental_counts["unknown"]
                else "GO"
                if supplemental_counts["checked"]
                else "NOTRUN"
            ),
            "ordinary_kickoff_commitment": (
                "UNVERIFIED"
                if kickoff_counts is None or kickoff_counts["unknown"]
                else "GO"
                if kickoff_counts["checked"]
                else "NOTRUN"
            ),
            "final_row_linkage": "GO" if final_binding is not None else "UNVERIFIED",
            "pat_report_commitment": (
                "UNVERIFIED"
                if pat_counts is None or pat_counts["unknown"]
                else "GO"
                if pat_counts["checked"]
                else "NOTRUN"
            ),
            "ordinary_continuity": (
                "UNVERIFIED"
                if continuity_counts is None or continuity_counts["unknown"]
                else "GO"
                if continuity_counts["checked"]
                else "NOTRUN"
            ),
            "standard_clock": (
                "UNVERIFIED"
                if clock_counts is None or clock_counts["unknown"]
                else "GO"
                if clock_counts["checked"]
                else "NOTRUN"
            ),
            "ordinary_commitment": (
                "UNVERIFIED"
                if commitment_counts is None or commitment_counts["unknown"]
                else "GO"
                if commitment_counts["checked"]
                else "NOTRUN"
            ),
            "captured_row_linkage": (
                "UNVERIFIED"
                if row_counts is None or row_counts["rows_unverified"]
                else "GO"
                if row_counts["rows_linked"]
                else "NOTRUN"
            ),
            "capture_report_history": (
                "UNVERIFIED"
                if capture_links is None or capture["typed_capture"]["version"] == "1"
                else "GO"
                if capture_links["report_changes_checked"]
                + capture_links["initial_report_facts_checked"]
                else "NOTRUN"
            ),
            "capture_internal_linkage": (
                "UNVERIFIED"
                if capture_links is None
                else "GO"
                if capture_links["commands_checked"]
                else "NOTRUN"
            ),
            "typed_lookup_agreement": (
                "GO"
                if lookup_counts
                else "UNVERIFIED"
                if row_counts is None or row_counts["typed_rows_unknown"]
                else "GO"
                if row_counts["typed_rows_checked"]
                else "NOTRUN"
            ),
            "supplied_physical_draws": (
                "GO"
                if lookup_counts
                else "UNVERIFIED"
                if row_counts is None
                else "GO"
                if row_counts["physical_draws"]
                else "NOTRUN"
            ),
            "symbolic_priority": "GO" if priority_events is not None else "UNVERIFIED",
            "event_ownership": "GO" if owned else "NOTRUN",
            "excluded_statistics": "GO" if counts["excluded"] else "NOTRUN",
            "credit_shape": "GO",
            "final_statistics": "GO",
            "scoring_awards": "GO" if awards else "NOTRUN",
            "scoring_totals": "GO",
            "accepted_voided_statistics": accepted_status,
            "halftime": "GO" if halftime else "UNVERIFIED",
            "chart_priority_and_cells": "UNVERIFIED",
            "all_called_resolved_branches": "UNVERIFIED",
            "pending_choice_save": "UNVERIFIED",
            "forced_rare_branch_coverage": "UNVERIFIED",
            "independent_period_attribution": "UNVERIFIED",
        },
        "coverage": coverage,
        "lookup_counts": lookup_counts,
        "captured_row_counts": row_counts,
        "penalty_commitment_counts": penalty_counts,
        "punt_commitment_counts": punt_counts,
        "ordinary_commitment_counts": commitment_counts,
        "supplemental_commitment_counts": supplemental_counts,
        "standard_clock_counts": clock_counts,
        "ordinary_continuity_counts": continuity_counts,
        "pat_report_counts": pat_counts,
        "kickoff_counts": kickoff_counts,
        "final_row_binding": final_binding,
        "capture_linkage": capture_links,
        "unverified_penalty_reports": unverified_penalties,
        "full_play_by_play_qualification": False,
        "accuracy_qualification": False,
        "remaining_ticket": "DATA-055",
        "limits": [
            "Statistic kinds and underlying gains are retained engine facts; "
            "chart results are not recomputed.",
            "Halftime checks prefix statistics and total score; quarter split arithmetic only.",
            "Observed event counts do not establish forced rare-branch coverage.",
        ],
    }
