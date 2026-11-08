"""Conditional continuity of independently checked ordinary endpoint facts.

No engine imports or fixture/omitted-command authority. Initial supplied anchors
remain unverified; a raw view cannot establish a qualified endpoint by agreement.
"""

from collections import Counter
from copy import deepcopy
from typing import Any

from . import game_audit_commitment as commitment


class ContinuityEvidenceError(ValueError):
    """A supplied boundary contradicts a checked ordinary endpoint."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    try:
        commitment._equal(actual, expected, label)
    except commitment.CommitmentEvidenceError as error:
        raise ContinuityEvidenceError(f"ordinary continuity {error}") from error


def _field(value: Any) -> dict[str, Any] | None:
    try:
        return commitment._state(value) if value is not None else None
    except commitment.CommitmentEvidenceError as error:
        raise ContinuityEvidenceError(f"ordinary continuity {error}") from error


def _view_field(view: dict[str, Any]) -> dict[str, Any] | None:
    if "state" not in view:
        raise ContinuityEvidenceError("ordinary continuity missing state key")
    return _field(view["state"])


def _endpoint(view: dict[str, Any], field: Any) -> dict[str, Any]:
    try:
        if "state" not in view:
            raise KeyError("state")
        facts = dict(
            state=_field(field),
            statistics=commitment._boxes(view),
            score=view["score"],
            scoring=view["scoring"],
        )
        commitment._canonical(facts)
        return deepcopy(facts)
    except (KeyError, commitment.CommitmentEvidenceError) as error:
        raise ContinuityEvidenceError(f"ordinary continuity endpoint format: {error}") from error


def audit_ordinary_continuity(
    capture: dict[str, Any],
    *,
    ordinary: dict[str, Any],
    clock: dict[str, Any],
    typed_inventory_available: bool,
    kickoff: dict[str, Any] | None = None,
    supplemental: dict[str, Any] | None = None,
    punt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Link checked endpoints; report distinct comparison/unknown unit counts."""
    typed = capture["typed_capture"]
    ordinary_by_number = {row["command_number"]: row for row in ordinary["dispositions"]}
    clock_by_number = {row["command_number"]: row for row in clock["dispositions"]}
    kickoff_by_number = {
        row["command_number"]: row for row in (kickoff or {}).get("dispositions", [])
    }
    supplemental_by_number = {
        row["command_number"]: row for row in (supplemental or {}).get("dispositions", [])
    }
    punt_by_number = {row["command_number"]: row for row in (punt or {}).get("dispositions", [])}
    known: dict[int, dict[str, Any] | None] = {}
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    dispositions = []
    prerequisite = (
        typed["version"] == "2"
        and capture.get("lookup_rows", {}).get("version") == "2"
        and typed_inventory_available
    )
    for command in typed["commands"]:
        number, game = command["number"], command["game_number"]
        before, after = (command[key]["view"] for key in ("before", "after"))
        first = game not in known
        expected = known.get(game)
        if first:
            counts["initial_anchors"] += 1
        elif expected is None:
            counts["unknown_links"] += 1
            reasons["unverified_prior_endpoint"] += 1
        else:
            _equal(_endpoint(before, before.get("state")), expected, "before boundary")
            counts["boundary_links"] += 1
        reason = None
        if not prerequisite:
            reason = "typed_evidence_prerequisite"
        elif not first and expected is None:
            reason = "unverified_prior_continuation"
        elif command["exception_type"] is not None:
            reason = "failed_command"
        elif (
            (kick := kickoff_by_number.get(number)) is not None
            and kick["game_number"] == game
            and kick["core_checked"] is True
            and (
                kick["status"] == "GO"
                or kick["kind"] == "opening"
                and kick["status"] == "EXCLUDED"
                and kick["reason"] == "conditional_opening_anchor"
            )
        ):
            # The separate kickoff oracle has qualified this public field,
            # unchanged boxes/score, and live continuation. Initial anchor
            # authority remains conditional; an unknown prior never reaches here.
            expected = _endpoint(after, _view_field(after))
            counts["qualified_kickoff_endpoints"] += 1
        elif (
            (punt_row := punt_by_number.get(number)) is not None
            and punt_row["game_number"] == game
            and (
                punt_row["status"] == "GO"
                or punt_row["status"] == "EXCLUDED"
                and punt_row["reason"] == "pending_creation_checked"
            )
            and punt_row["core_checked"] is True
        ):
            expected = _endpoint(after, _view_field(after))
            counts["qualified_punt_endpoints"] += 1
        elif ordinary_by_number[number]["status"] == "GO" or (
            supplemental_by_number.get(number, {}).get("game_number") == game
            and supplemental_by_number[number]["status"] == "GO"
        ):
            # The prior independent rule/credit oracle has already checked this
            # report field, full box deltas, score award and scoring prefix.
            field = command["returned_report"]["state_after"]
            expected = _endpoint(after, field)
            counts["qualified_ordinary_endpoints"] += 1
        elif (
            expected is not None
            and command["operation"] == "decide"
            and command["arguments"] == ["clock:runoff"]
            and clock_by_number[number]["status"] == "GO"
        ):
            if after.get("phase") == "scrimmage":
                _equal(_view_field(after), expected["state"], "runoff field")
                # Qualified clock runoff separately proves no new box/score
                # credit. Keep the independently checked old endpoint.
                counts["runoff_fields"] += 1
            else:
                reason = "runoff_period_field_authority"
        else:
            reason = "unqualified_endpoint"
        if reason is not None:
            counts["unknown_endpoints"] += 1
            reasons[reason] += 1
            expected = None
        known[game] = expected
        dispositions.append(
            dict(
                command_number=number,
                game_number=game,
                endpoint="GO" if reason is None else "UNVERIFIED",
                reason=reason,
            )
        )
    return dict(
        commands_observed=len(typed["commands"]),
        game_objects_observed=len(known),
        initial_anchors=counts["initial_anchors"],
        initial_anchor_truth="UNVERIFIED",
        boundary_links=counts["boundary_links"],
        runoff_fields=counts["runoff_fields"],
        qualified_ordinary_endpoints=counts["qualified_ordinary_endpoints"],
        qualified_kickoff_endpoints=counts["qualified_kickoff_endpoints"],
        qualified_punt_endpoints=counts["qualified_punt_endpoints"],
        checked=counts["boundary_links"] + counts["runoff_fields"],
        unknown_links=counts["unknown_links"],
        unknown_endpoints=counts["unknown_endpoints"],
        unknown=counts["unknown_links"] + counts["unknown_endpoints"],
        unit_scope=(
            "inter-command before links and eligible no-new-play after fields; "
            "unqualified endpoint units retained separately"
        ),
        unknown_reasons=dict(sorted(reasons.items())),
        dispositions=dispositions,
    )
