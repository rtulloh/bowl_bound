"""Conditional linkage of one observed public endpoint/log to retained row facts.

No engine imports or football finality oracle. Caller first validates the supplied
command envelope. External fixture/command/source authority is separate.
"""

from typing import Any, cast

from . import game_audit_commitment as commitment
from . import game_audit_envelope as envelope


class FinalBindingEvidenceError(ValueError):
    """A final binding is malformed, stale or contradicts retained facts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FinalBindingEvidenceError(f"final row binding {message}")


def _equal(actual: Any, expected: Any, label: str) -> None:
    _require(
        envelope._log_content([actual]) == envelope._log_content([expected]), f"{label} differs"
    )


def audit_final_row_binding(row: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any] | None:
    """Bind validated supplied history, never omitted/external execution."""
    if "final_object" not in capture:
        return None
    try:
        return _audit(row, capture)
    except (envelope.CaptureEvidenceError, commitment.CommitmentEvidenceError, KeyError) as error:
        raise FinalBindingEvidenceError(f"final row binding {error}") from error


def _audit(row: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    block = capture["final_object"]
    fields = {
        "version",
        "status",
        "usable",
        "errors",
        "exit_exception_type",
        "game_number",
        "last_command_number",
        "frontiers",
        "snapshot",
        "reports",
    }
    _require(type(block) is dict and block.keys() == fields, "block fields")
    _require(
        type(block["version"]) is str
        and block["version"] == "1"
        and type(block["status"]) is str
        and block["status"] == "frozen"
        and block["usable"] is True
        and type(block["errors"]) is list
        and not block["errors"]
        and block["exit_exception_type"] is None,
        "block is not successfully frozen",
    )
    block = cast(dict[str, Any], block)
    typed = capture["typed_capture"]
    _require(typed["version"] == "2", "indexed history required")
    for key in ("game_number", "last_command_number"):
        _require(type(block[key]) is int and block[key] > 0, f"{key} identity")
    counts = {
        key: len(typed[key]) for key in ("commands", "draws", "draw_requests", "priority_attempts")
    }
    _require(
        type(block["frontiers"]) is dict
        and block["frontiers"].keys() == counts.keys()
        and all(type(v) is int and v >= 0 for v in block["frontiers"].values()),
        "frontier fields/types",
    )
    _equal(block["frontiers"], counts, "window-end frontiers")
    commands = [
        command for command in typed["commands"] if command["game_number"] == block["game_number"]
    ]
    _require(bool(commands), "selected object has no observed commands")
    last = commands[-1]
    _equal(block["last_command_number"], last["number"], "last per-object command")
    snapshot = cast(dict[str, Any], block["snapshot"])
    envelope._boundary(snapshot, True)
    _equal(snapshot, last["after"], "last observed public boundary")
    history = None
    for command in commands:
        history, _, _ = envelope._history(command, history)
    history = cast(list[dict[str, Any]], history)
    _require(
        type(block["reports"]) is list and all(type(p) is dict for p in block["reports"]),
        "complete log fields",
    )
    _equal(block["reports"], history, "frozen/indexed complete log")
    _equal(row["engine_log"], history, "retained/indexed complete log")
    _require(snapshot["reports"] == len(history), "frozen report count")
    _equal(snapshot["log_sha256"], envelope._log_digest(history), "frozen report digest")
    view = snapshot["view"]
    _require(
        {"state", "finished", "score", "statistics", "scoring"} <= view.keys(),
        "required public endpoint facts",
    )
    _require(
        type(view["finished"]) is bool and type(row["final"]["finished"]) is bool,
        "strict finished subject",
    )
    _equal(row["final"]["finished"], view["finished"], "retained finished flag")
    _require(
        type(view["score"]) is dict
        and view["score"].keys() == {"home", "away"}
        and all(type(v) is int and v >= 0 for v in view["score"].values()),
        "score types",
    )
    _equal(
        {side: row["final"][side + "_score"] for side in ("home", "away")},
        view["score"],
        "retained scores",
    )
    _equal(
        commitment._boxes({"statistics": row["final"]["statistics"]}),
        commitment._boxes(view),
        "retained complete numeric boxes",
    )
    _require(type(view["scoring"]) is list, "scoring ledger type")
    _equal(row["final"]["scoring"], view["scoring"], "retained scoring ledger")
    return dict(
        checked=1,
        excluded=0,
        unknown=0,
        selected_game_number=block["game_number"],
        last_command_number=last["number"],
        reports_linked=len(history),
        observed_commands_for_object=len(commands),
        failed_commands_for_object=sum(
            command["exception_type"] is not None for command in commands
        ),
        external_fixture_identity="UNVERIFIED",
        external_command_completeness="UNVERIFIED",
        football_finality="UNVERIFIED",
        source_truth="UNVERIFIED",
    )
