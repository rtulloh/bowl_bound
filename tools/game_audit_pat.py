"""Independent dedicated PAT report/stat/award commitments, no engine imports.

The supplied conversion chooser is an anchor. External actual fixture/season,
loaded chart truth, later live fields and period/clock scheduling stay unverified.
"""

from collections import Counter
from typing import Any

from . import game_audit_commitment as commitment


class PatEvidenceError(ValueError):
    """Supplied PAT commitment contradicts pinned outcome or approved accounting."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PatEvidenceError(f"PAT commitment {message}")


def _equal(actual: Any, expected: Any, label: str) -> None:
    try:
        commitment._equal(actual, expected, label)
    except commitment.CommitmentEvidenceError as error:
        raise PatEvidenceError(f"PAT commitment {error}") from error


def _check(
    command: dict[str, Any],
    selected: list[dict[str, Any]],
    draws: list[Any],
    requests: list[Any],
    prior_report_ids: set[int],
) -> tuple[bool, dict[str, Any]]:
    before, after = (command[key]["view"] for key in ("before", "after"))
    _require(before["phase"] == "conversion_choice", "conversion-choice context")
    _require("state" in before and before["state"] is None, "before null field")
    pending = before["pending"]
    _require(type(pending) is dict, "conversion chooser")
    side = pending.get("chooser_side")
    _require(type(side) is str and side in {"home", "away"}, "conversion side")
    for label in ("home", "away"):
        _require(
            all(
                type(view.get(label)) is str and bool(view[label].strip())
                for view in (before, after)
            ),
            "view team label format",
        )
        _equal(after[label], before[label], "view team label continuity")
    _equal(pending.get("chooser"), before[side], "chooser label")
    _require(len(selected) == 1, "one dedicated row required")
    row = selected[0]
    _require(row["address"]["table"] == "pat", "dedicated PAT table required")
    _equal(row["address"]["team_id"], command["before"]["teams"][side]["id"], "dedicated row side")
    good = row["facts"]["good"]
    _require(type(good) is bool, "strict good outcome")
    start, end = command["draw_range"]
    _require(end > start and draws[start]["kind"] == "offensive", "first fresh PAT offensive draw")
    request_start, request_end = command["draw_request_range"]
    selected_requests = requests[request_start:request_end]
    _require(len(selected_requests) == end - start, "PAT request/draw exposure agreement")
    _require(
        all(
            request["completed"] is True and request["draw_number"] == start + index + 1
            for index, request in enumerate(selected_requests)
        ),
        "PAT successful request/draw order",
    )
    _require(selected_requests[0]["expected_type"] == "OffensiveRoll", "first PAT request kind")
    _equal(row["draw_binding"]["captured_draw_numbers"], [start + 1], "dedicated draw reference")
    _equal(row["address"]["roll"], draws[start]["total"], "dedicated roll total")
    for key in ("priority_range", "priority_attempt_range"):
        begin, finish = command[key]
        _require(finish == begin, f"{key} exposure")
    changes = command["report_changes"]
    _require(
        len(changes) == 1
        and changes[0]["index"] == command["before"]["reports"]
        and changes[0]["before"] is None,
        "one appended report required",
    )
    report = changes[0]["after"]
    _equal(command["returned_report"], report, "returned/appended report")
    _require(type(report["number"]) is int and report["number"] > 0, "report identity")
    _require(
        report["number"] not in prior_report_ids, "report identity reused in same-object prefix"
    )
    _require(report["supported"] is True and report["pending"] is False, "committed report")
    _equal(report["outcome"], "pat_good" if good else "pat_missed", "dedicated outcome")
    _equal(report["yards"], None, "no chart yardage")
    _equal(report["called_play"], "PAT kick", "called family format")
    _equal(report["resolved_play"], "PAT kick", "resolved family format")
    try:
        state = commitment._state(report["state_before"])
        _equal(state, dict(possession=side, yards_to_goal=2, down=1, yards_to_go=2), "try start")
        _equal(report["state_after"], None, "terminal report field")
        _equal(
            report["statistics"],
            dict(kind="excluded", team=None, yards=0, touchdown=False),
            "excluded-zero credit",
        )
        _equal(commitment._boxes(after), commitment._boxes(before), "both numeric boxes")
    except commitment.CommitmentEvidenceError as error:
        raise PatEvidenceError(f"PAT commitment {error}") from error
    for view in (before, after):
        _require(
            type(view["score"]) is dict
            and view["score"].keys() == {"home", "away"}
            and all(type(v) is int and v >= 0 for v in view["score"].values()),
            "score types",
        )
    expected_score = dict(before["score"])
    expected_score[side] += int(good)
    _equal(after["score"], expected_score, "one-point/no-point award")
    _require(
        type(before["scoring"]) is list and type(after["scoring"]) is list, "scoring ledger types"
    )
    scoring = list(before["scoring"])
    if good:
        scoring.append(
            dict(
                number=len(scoring) + 1,
                play_number=report["number"],
                team=before[side],
                kind="pat",
                points=1,
            )
        )
    _equal(after["scoring"], scoring, "scoring ledger")
    # Current report serialization carries empty timing facts even though the
    # regulation layer separately appends a zero-second charge. This checks only
    # that report format, never live clock/period/final-state qualification.
    _equal(
        report["timing"],
        {
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
        },
        "empty serialized timing facts",
    )
    _equal(report["extends_quarter"], False, "extends-quarter format")
    additional = list(range(start + 2, end + 1))
    # Supplied chronology establishes only whether the additional draws followed
    # the PAT row. Their football roles/legality are deliberately not inferred.
    return good, dict(
        additional_draw_numbers=additional,
        post_PAT_order_verified=row["captured_draw_frontier"] == start + 1,
    )


def audit_pat_reports(
    capture: dict[str, Any], *, typed_inventory_available: bool
) -> dict[str, Any]:
    """Check already validated supplied PAT rows; never external completeness."""
    typed = capture["typed_capture"]
    block = capture.get("lookup_rows")
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    dispositions = []
    seen_by_game: dict[int, list[Any]] = {}
    for command in typed["commands"]:
        # The supplied observed history is a conditional prefix, not a promise
        # that report numbers equal positions or that all commands were seen.
        seen = seen_by_game.setdefault(command["game_number"], [])
        prior_report_values = list(seen)
        if typed["version"] == "2":
            seen.extend(report.get("number") for report in command["initial_log"] or [])
            prior_report_values = list(seen)
            for change in command["report_changes"]:
                for endpoint in ("before", "after"):
                    report = change[endpoint]
                    if type(report) is dict:
                        seen.append(report.get("number"))
        reason = None
        core_checked = False
        extra = dict(additional_draw_numbers=[], post_PAT_order_verified=False)
        selected = (
            [row for row in block["events"] if row["command_number"] == command["number"]]
            if block
            else []
        )
        if command["exception_type"] is not None:
            reason = "failed_command"
        elif command["operation"] != "decide" or command["arguments"] != ["conversion:kick"]:
            counts["excluded"] += 1
            dispositions.append(
                dict(
                    command_number=command["number"],
                    game_number=command["game_number"],
                    status="EXCLUDED",
                    reason="non_PAT_command",
                    core_checked=False,
                    **extra,
                )
            )
            continue
        elif (
            typed["version"] != "2"
            or block is None
            or block["version"] != "2"
            or not typed_inventory_available
        ):
            reason = "typed_evidence_prerequisite"
        elif command["before"]["view"].get("overtime") is not None:
            reason = "overtime_context"
        elif any(
            row["chart_binding"] != "BOUND"
            or row["record_binding"] != "BOUND"
            or row["draw_binding"]["status"] != "BOUND"
            for row in selected
        ):
            reason = "unbound_selected_row"
        if reason is None:
            before_view = command["before"]["view"]
            for name in ("scoring", "timing_log"):
                references = before_view.get(name, [])
                _require(
                    type(references) is list and all(type(row) is dict for row in references),
                    f"prior {name} reference container",
                )
                prior_report_values.extend(row.get("play_number") for row in references)
            _require(
                all(type(value) is int and value > 0 for value in prior_report_values),
                "prior report identity domain",
            )
            prior_report_ids = set(prior_report_values)
            try:
                good, extra = _check(
                    command, selected, typed["draws"], typed["draw_requests"], prior_report_ids
                )
            except KeyError as error:
                raise PatEvidenceError(f"PAT commitment missing field {error}") from error
            core_checked = True
            counts["core_reports_checked"] += 1
            if extra["additional_draw_numbers"]:
                counts["additional_draws_unqualified"] += len(extra["additional_draw_numbers"])
                reason = (
                    "post_PAT_draw_authority"
                    if extra["post_PAT_order_verified"]
                    else "additional_draw_order_authority"
                )
            else:
                counts["checked"] += 1
                counts["good" if good else "missed"] += 1
        if reason is not None:
            reasons[reason] += 1
        dispositions.append(
            dict(
                command_number=command["number"],
                game_number=command["game_number"],
                status="GO" if reason is None else "UNVERIFIED",
                reason=reason,
                core_checked=core_checked,
                **extra,
            )
        )
    return dict(
        commands_observed=len(typed["commands"]),
        checked=counts["checked"],
        excluded=counts["excluded"],
        unknown=sum(reasons.values()),
        good=counts["good"],
        missed=counts["missed"],
        core_reports_checked=counts["core_reports_checked"],
        additional_draws_unqualified=counts["additional_draws_unqualified"],
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
        live_continuation="UNVERIFIED",
        actual_season_identity="UNVERIFIED",
    )
