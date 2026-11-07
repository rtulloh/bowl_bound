"""Isolated diagnostic capture of engine-owned decisions and halftime snapshots."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any
from unittest.mock import patch


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


class ReceiptCapture:
    """Collect immutable engine facts; replayed commands do not add exposure."""

    def __init__(self) -> None:
        self._halftime: dict[str, dict[str, Any]] = {}
        self._decisions: dict[str, dict[str, Any]] = {}

    def record(
        self,
        view: dict[str, Any],
        operation: str,
        arguments: list[str],
        report: dict[str, Any] | None,
        *,
        replaying: bool = False,
    ) -> None:
        if replaying:
            return
        review = view.get("review")
        if review is not None and review.get("kind") == "halftime":
            snapshot = {
                "report_number": len(view["log"]),
                "score": view["score"],
                "statistics": view["statistics"],
                "recap": review["halftime"],
            }
            key = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
            self._halftime[key] = json.loads(key)
        if (
            operation == "decide"
            and len(arguments) == 1
            and report is not None
            and report["outcome"] == "penalty_accepted"
        ):
            decision = {"report_number": report["number"], "choice": arguments[0]}
            key = json.dumps(decision, sort_keys=True)
            self._decisions[key] = decision

    def payload(self) -> dict[str, Any]:
        """Return a detached serializable receipt without game saves or prose."""
        return json.loads(
            json.dumps(
                {
                    "halftime": list(self._halftime.values()),
                    "decisions": sorted(
                        self._decisions.values(), key=lambda row: row["report_number"]
                    ),
                }
            )
        )


@contextmanager
def capture_receipts(*, typed: bool = False, lookup_rows: bool = False) -> Iterator[ReceiptCapture]:
    """Observe SavedGame commands in a dedicated audit process only.

    The delegate receives the original operation/arguments exactly once. This
    temporary class patch is unsuitable for a shared server or concurrent games.
    """
    if lookup_rows and not typed:
        raise ValueError("lookup-row observation requires typed capture")
    if typed:
        from .game_audit_typed_capture import capture_typed_receipts

        with capture_typed_receipts(lookup_rows=lookup_rows) as capture:
            yield capture
        return

    from bowl_bound.save_game import SavedGame

    original = SavedGame._execute
    capture = ReceiptCapture()

    def execute(game: SavedGame, operation: str, arguments: list[str]) -> Any:
        replaying = game._tape.replaying
        report = original(game, operation, arguments)
        if replaying:
            return report
        view = game.view()
        review = getattr(view, "review", None)
        retained = {"review": None}
        if review is not None and review.kind == "halftime":
            retained = _json_value(
                {
                    "log": [None] * len(view.log),
                    "score": view.score,
                    "statistics": view.statistics,
                    "review": review,
                }
            )
        capture.record(retained, operation, arguments, _json_value(report), replaying=replaying)
        return report

    with patch.object(SavedGame, "_execute", execute):
        yield capture
