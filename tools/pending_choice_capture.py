"""Opt-in mandatory-choice saves for isolated audit processes, never a server.

Nest inside typed receipt capture. Clone verification must run after BOTH capture
contexts have exited. Replay equality is not independent football qualification.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import get_ident
from typing import Any
from unittest.mock import patch

from bowl_bound.models import TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game

from .game_audit_capture import _json_value

FIXED_SAVED_AT = "2000-01-01T00:00:00+00:00"


class PendingEvidenceError(ValueError):
    """Addressed save evidence is incomplete, foreign or inconsistent."""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fixed_save(game: SavedGame, saved_at: str = FIXED_SAVED_AT) -> str:
    """Fix only serialization metadata and its integrity, preserving save semantics."""
    clock = datetime.fromisoformat(saved_at)
    if clock.tzinfo is None:
        raise PendingEvidenceError("serialization clock requires an explicit timezone")
    data = json.loads(dumps_game(game))
    data["saved_at"] = saved_at
    data.pop("integrity")
    data["integrity"] = _sha(_json(data))
    return _json(data)


class PendingChoiceCapture:
    """Retain strong object identities, addressed boundaries and observed outcomes."""

    def __init__(self, typed_capture: Any, saved_at: str) -> None:
        self.typed_capture = typed_capture
        self.saved_at = saved_at
        self.commands: list[dict[str, Any]] = []
        self.boundaries: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.games: list[SavedGame] = []
        self.resumes: list[dict[str, Any]] = []
        self.owner_thread = get_ident()
        self.closed = False
        self.active = False
        self.replay_skipped = 0

    def error(self, stage: str, error: BaseException) -> None:
        self.errors.append(
            {"stage": stage, "type": type(error).__name__, "command": len(self.commands)}
        )

    def resume(self, game: SavedGame, loader: Callable[[str], TeamChart]) -> SavedGame:
        """Save/load an observed object and retain its explicit continuation edge."""
        try:
            if self.closed or self.active or get_ident() != self.owner_thread:
                raise PendingEvidenceError("resume requires an open isolated capture")
            if not any(known is game for known in self.games):
                raise PendingEvidenceError("resume origin must be an actual observed object")
            source = next(i for i, known in enumerate(self.games, 1) if known is game)
            text = fixed_save(game, self.saved_at)
            view = _json_value(game.view())
            boundary = (
                self.boundary(game, source, view, None) if view["pending"] is not None else None
            )
            restored = loads_game(text, loader)
            if restored is game or fixed_save(restored, self.saved_at) != text:
                raise PendingEvidenceError("resume did not create a detached exact saved object")
            if _json(_json_value(restored.view())) != _json(view):
                raise PendingEvidenceError("resume public boundary diverged")
            self.games.append(restored)
            target = len(self.games)
            child = self.boundary(restored, target, view, None) if boundary is not None else None
            self.resumes.append(
                {
                    "number": len(self.resumes) + 1,
                    "source_game_number": source,
                    "target_game_number": target,
                    "after_command": len(self.commands),
                    "source_boundary": boundary["number"] if boundary is not None else None,
                    "target_boundary": child["number"] if child is not None else None,
                    "save": text,
                    "save_sha256": _sha(text),
                    "view": view,
                }
            )
            return restored
        except Exception as error:
            self.error("resume", error)
            raise

    def boundary(
        self, game: SavedGame, number: int, view: dict[str, Any], creating: int | None
    ) -> dict[str, Any]:
        text = fixed_save(game, self.saved_at)
        digest = _sha(text)
        for boundary in self.boundaries:
            if boundary["game_number"] == number and boundary["save_sha256"] == digest:
                if _json(boundary["before_view"]) != _json(view):
                    raise PendingEvidenceError("same save has inconsistent public boundary")
                return boundary
        pending = view["pending"]
        choices = pending["choices"]
        ids = [choice["id"] for choice in choices]
        if len(ids) != len(set(ids)) or any(
            type(choice["id"]) is not str or type(choice["enabled"]) is not bool
            for choice in choices
        ):
            raise PendingEvidenceError("boundary choices require unique strict typed IDs")
        data = json.loads(text)
        result = {
            "number": len(self.boundaries) + 1,
            "game_number": number,
            "creating_command": creating,
            "initial_anchor": creating is None,
            "phase": view["phase"],
            "before_view": view,
            "save": text,
            "save_sha256": digest,
            "journal_frontier": len(game._commands),
            "roll_count": len(game._tape.rolls),
            "tape_position": game._tape.position,
            "team_identities": data["teams"],
            "configuration": data["config"],
            "enabled_ids": [c["id"] for c in choices if c["enabled"]],
            "attempts": [],
        }
        self.boundaries.append(result)
        return result

    def payload(self) -> dict[str, Any]:
        """Return detached private evidence; missing/failed boundaries remain counted."""
        return json.loads(
            _json(
                {
                    "pending_choice_saves": {
                        "version": "1",
                        "closed": self.closed,
                        "usable": not self.errors,
                        "saved_at": self.saved_at,
                        "commands": self.commands,
                        "boundaries": self.boundaries,
                        "resumes": self.resumes,
                        "errors": self.errors,
                        "replay_commands_skipped": self.replay_skipped,
                        "scope": (
                            "addressed replay evidence; independent football accounting separate"
                        ),
                    }
                }
            )
        )


@contextmanager
def capture_pending_choices(
    *, typed_capture: Any = None, saved_at: str = FIXED_SAVED_AT
) -> Iterator[PendingChoiceCapture]:
    """Wrap each actual command once, outside the existing typed profiler span."""
    if datetime.fromisoformat(saved_at).tzinfo is None:
        raise PendingEvidenceError("serialization clock requires an explicit timezone")
    capture = PendingChoiceCapture(typed_capture, saved_at)
    original = SavedGame._execute

    def execute(game: SavedGame, operation: str, arguments: list[str]) -> Any:
        if game._tape.replaying:
            capture.replay_skipped += 1
            return original(game, operation, arguments)
        if get_ident() != capture.owner_thread or capture.active:
            capture.error("foreign-thread-or-nested-command", PendingEvidenceError("isolation"))
            return original(game, operation, arguments)
        capture.active = True
        if not any(known is game for known in capture.games):
            capture.games.append(game)
        number = next(i for i, known in enumerate(capture.games, 1) if known is game)
        command: dict[str, Any] = {
            "number": len(capture.commands) + 1,
            "game_number": number,
            "operation": operation,
            "arguments": list(arguments),
            "boundary_number": None,
            "exception_type": None,
            "journal_before": len(game._commands),
        }
        capture.commands.append(command)
        boundary = None
        typed_start: int | None = None
        try:
            try:
                if typed_capture is not None:
                    typed_start = len(typed_capture.commands)
                before = _json_value(game.view())
                if before["pending"] is not None:
                    boundary = capture.boundary(game, number, before, None)
                    command["boundary_number"] = boundary["number"]
                    boundary["attempts"].append(command["number"])
                    command["enabled_choice"] = (
                        operation == "decide"
                        and len(arguments) == 1
                        and arguments[0] in boundary["enabled_ids"]
                    )
            except Exception as error:
                capture.error("before-boundary", error)
            returned = None
            try:
                returned = original(game, operation, arguments)
                return returned
            except BaseException as error:
                command["exception_type"] = type(error).__name__
                raise
            finally:
                try:
                    after = _json_value(game.view())
                    command["journal_after"] = len(game._commands)
                    command["returned"] = _json_value(returned)
                    command["after_view"] = after
                    command["after_save"] = fixed_save(game, saved_at)
                    command["after_save_sha256"] = _sha(command["after_save"])
                    command["after_pending_boundary_number"] = None
                    if after["pending"] is not None:
                        pending_after = capture.boundary(game, number, after, command["number"])
                        command["after_pending_boundary_number"] = pending_after["number"]
                    if typed_capture is not None:
                        if typed_start is None or len(typed_capture.commands) != typed_start + 1:
                            raise PendingEvidenceError("typed command exposure mismatch")
                        typed = typed_capture.commands[-1]
                        if typed_capture._games[typed["game_number"] - 1] is not game:
                            raise PendingEvidenceError("foreign typed command object")
                        if (typed["operation"], typed["arguments"]) != (operation, arguments):
                            raise PendingEvidenceError("typed command identity mismatch")
                        command["typed_command_number"] = typed["number"]
                        command["typed_game_number"] = typed["game_number"]
                except Exception as error:
                    capture.error("after-boundary", error)
        finally:
            capture.active = False

    with patch.object(SavedGame, "_execute", execute):
        try:
            yield capture
        except BaseException as error:
            capture.error("abnormal-capture-exit", error)
            raise
        finally:
            capture.closed = True


def verify_pending_choices(
    payload: dict[str, Any],
    loader: Callable[[str], TeamChart],
    *,
    typed_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay detached saves offline; refuse missing/extraneous addressed evidence."""
    native = SavedGame._execute
    if (
        native.__qualname__ != "SavedGame._execute"
        or Path(native.__code__.co_filename).name != "save_game.py"
    ):
        raise PendingEvidenceError("offline verification requires all capture contexts closed")
    block = payload["pending_choice_saves"]
    if not block["closed"] or not block["usable"]:
        raise PendingEvidenceError("incomplete or failed mandatory-save capture")
    commands: dict[int, dict[str, Any]] = {c["number"]: c for c in block["commands"]}
    boundaries: dict[int, dict[str, Any]] = {b["number"]: b for b in block["boundaries"]}
    if len(commands) != len(block["commands"]) or len(boundaries) != len(block["boundaries"]):
        raise PendingEvidenceError("duplicate command/boundary address")
    linked = False
    actual: dict[int, dict[str, Any]] = {}
    if typed_payload is not None:
        typed = typed_payload["typed_capture"]
        if not typed["usable"]:
            raise PendingEvidenceError("typed capture is unusable")
        actual = {c["number"]: c for c in typed["commands"]}
        if (
            len(commands) != len(actual)
            or len(actual) != len(typed["commands"])
            or {c.get("typed_command_number") for c in commands.values()} != set(actual)
        ):
            raise PendingEvidenceError("missing/extra typed command exposure")
        for c in commands.values():
            t = actual[c["typed_command_number"]]
            if (c["typed_game_number"], c["operation"], c["arguments"]) != (
                t["game_number"],
                t["operation"],
                t["arguments"],
            ):
                raise PendingEvidenceError("foreign/stale command address")
            if bool(t["before"]["view"]["pending"] is not None) != bool(c["boundary_number"]):
                raise PendingEvidenceError("missing mandatory boundary")
            for field, frontier, view in (
                ("boundary_number", "journal_before", t["before"]["view"]),
                ("after_pending_boundary_number", "journal_after", t["after"]["view"]),
            ):
                address = c.get(field)
                if bool(view["pending"] is not None) != bool(address):
                    raise PendingEvidenceError("missing mandatory boundary exposure")
                if address is not None:
                    if address not in boundaries:
                        raise PendingEvidenceError("missing mandatory boundary object")
                    b = boundaries[address]
                    observed = {k: v for k, v in b["before_view"].items() if k != "log"}
                    if (
                        _json(observed) != _json(view)
                        or b["game_number"] != c["game_number"]
                        or b["journal_frontier"] != c[frontier]
                    ):
                        raise PendingEvidenceError("foreign/stale boundary view")
                    snapshot = t["before" if field == "boundary_number" else "after"]
                    if (
                        b["tape_position"] != snapshot["tape"]["position"]
                        or b["roll_count"] != snapshot["tape"]["roll_count"]
                    ):
                        raise PendingEvidenceError(
                            "saved boundary metadata disagrees with typed tape"
                        )
        linked = True
    handoffs: dict[int, int] = {}
    seen_targets = set()
    for resume in block["resumes"]:
        source, target = resume["source_game_number"], resume["target_game_number"]
        marker = resume["after_command"]
        if source == target or target in seen_targets or marker > len(commands):
            raise PendingEvidenceError("invalid resume object addresses")
        seen_targets.add(target)
        if any(c["game_number"] == source and c["number"] > marker for c in commands.values()):
            raise PendingEvidenceError("forked source continued after explicit resume")
        if any(c["game_number"] == target and c["number"] <= marker for c in commands.values()):
            raise PendingEvidenceError("resume target existed before its source save")
        text = resume["save"]
        source_commands = [
            c for c in commands.values() if c["game_number"] == source and c["number"] <= marker
        ]
        if not source_commands:
            raise PendingEvidenceError("resume source has no observed command")
        last = max(source_commands, key=lambda c: c["number"])
        if last["after_save"] != text or last["after_save_sha256"] != resume["save_sha256"]:
            raise PendingEvidenceError("resume source differs from its last observed command")
        if _sha(text) != resume["save_sha256"]:
            raise PendingEvidenceError("resume save hash mismatch")
        restored = loads_game(text, loader)
        if fixed_save(restored, block["saved_at"]) != text or _json(
            _json_value(restored.view())
        ) != _json(resume["view"]):
            raise PendingEvidenceError("resume saved object identity mismatch")
        parent, child = resume["source_boundary"], resume["target_boundary"]
        if (parent is None) != (child is None):
            raise PendingEvidenceError("resume lost a mandatory boundary")
        if parent is not None:
            if parent not in boundaries or child not in boundaries or parent in handoffs:
                raise PendingEvidenceError("missing/duplicate resume boundary")
            a, b = boundaries[parent], boundaries[child]
            if (
                a["game_number"] != source
                or b["game_number"] != target
                or a["save_sha256"] != resume["save_sha256"]
                or b["save_sha256"] != resume["save_sha256"]
                or a["attempts"]
            ):
                raise PendingEvidenceError("foreign or already consumed resume boundary")
            handoffs[parent] = child
    checked, unknown = 0, []
    mandatory, normal_clock, explicit_clock = 0, 0, 0
    for number, boundary in boundaries.items():
        text = boundary["save"]
        if _sha(text) != boundary["save_sha256"]:
            raise PendingEvidenceError("saved boundary hash mismatch")
        clone = loads_game(text, loader)
        if fixed_save(clone, block["saved_at"]) != text or _json(
            _json_value(clone.view())
        ) != _json(boundary["before_view"]):
            raise PendingEvidenceError("saved boundary identity mismatch")
        data = json.loads(text)
        pending = clone.view().pending
        if pending is None:
            raise PendingEvidenceError("saved boundary has no mandatory decision")
        if boundary["phase"] != boundary["before_view"]["phase"]:
            raise PendingEvidenceError("boundary phase disagrees with saved subject")
        if any(
            type(boundary[key]) is not int
            for key in ("journal_frontier", "roll_count", "tape_position")
        ):
            raise PendingEvidenceError("saved boundary metadata requires strict integers")
        enabled = [choice.id for choice in pending.choices if choice.enabled]
        if boundary["enabled_ids"] != enabled:
            raise PendingEvidenceError("boundary enabled IDs disagree with saved subject")
        if (
            boundary["journal_frontier"] != len(data["commands"])
            or boundary["roll_count"] != len(data["rolls"])
            or _json(boundary["team_identities"]) != _json(data["teams"])
            or _json(boundary["configuration"]) != _json(data["config"])
        ):
            raise PendingEvidenceError("saved boundary metadata mismatch")
        for address in boundary["attempts"]:
            if (
                address not in commands
                or commands[address]["boundary_number"] != number
                or commands[address]["game_number"] != boundary["game_number"]
            ):
                raise PendingEvidenceError("foreign boundary attempt")
        attempts = [c["number"] for c in commands.values() if c["boundary_number"] == number]
        if boundary["attempts"] != attempts or len(attempts) != len(set(attempts)):
            raise PendingEvidenceError("missing/duplicate boundary attempts")
        origin = boundary["creating_command"]
        producers: list[dict[str, Any]] = [
            c for c in commands.values() if c.get("after_pending_boundary_number") == number
        ]
        producers.sort(key=lambda c: c["number"])
        if (
            producers
            and producers[0]["boundary_number"] != number
            and origin != producers[0]["number"]
        ):
            raise PendingEvidenceError("creating command link omitted or changed")
        if boundary["initial_anchor"] != (origin is None):
            raise PendingEvidenceError("boundary initial-anchor identity mismatch")
        if origin is not None:
            if (
                origin not in commands
                or commands[origin]["game_number"] != boundary["game_number"]
                or commands[origin]["journal_after"] != boundary["journal_frontier"]
                or any(origin >= attempt for attempt in attempts)
            ):
                raise PendingEvidenceError("stale creating command")
            if typed_payload is not None:
                t = actual[commands[origin]["typed_command_number"]]
                observed = {k: v for k, v in boundary["before_view"].items() if k != "log"}
                if _json(observed) != _json(t["after"]["view"]):
                    raise PendingEvidenceError("creating command did not produce boundary")
        successful = False
        for address in boundary["attempts"]:
            c = commands[address]
            if c["boundary_number"] != number or c["game_number"] != boundary["game_number"]:
                raise PendingEvidenceError("foreign boundary attempt")
            explicit = (
                c["operation"] == "decide"
                and len(c["arguments"]) == 1
                and c["arguments"][0] in enabled
            )
            if c["enabled_choice"] != explicit:
                raise PendingEvidenceError("enabled-choice claim disagrees with saved menu")
            default_clock = (
                boundary["phase"] == "clock_choice"
                and boundary["before_view"].get("clock_optional") is True
                and c["operation"] in {"snap", "kick", "action"}
            )
            if c["exception_type"] is not None or not (explicit or default_clock):
                unknown.append({"command": address, "reason": "original-error-or-disabled"})
                continue
            replay = loads_game(text, loader)
            returned = replay._run(c["operation"], c["arguments"])
            if (
                _json(_json_value(returned)) != _json(c["returned"])
                or _json(_json_value(replay.view())) != _json(c["after_view"])
                or _sha(c["after_save"]) != c["after_save_sha256"]
                or fixed_save(replay, block["saved_at"]) != c["after_save"]
            ):
                raise PendingEvidenceError("detached continuation diverged")
            checked += 1
            if default_clock:
                normal_clock += 1
            elif boundary["phase"] == "clock_choice":
                explicit_clock += 1
            else:
                mandatory += 1
            successful = True
        if not successful and number not in handoffs:
            unknown.append({"boundary": number, "reason": "no-successful-enabled-continuation"})
    return {
        "status": "GO-addressed-replay-only" if linked and not unknown else "UNVERIFIED-partial",
        "boundaries": len(boundaries),
        "continuations_checked": checked,
        "mandatory_decisions_checked": mandatory,
        "normal_clock_continuations_checked": normal_clock,
        "explicit_clock_decisions_checked": explicit_clock,
        "handoffs_checked": len(handoffs),
        "resumes_checked": len(block["resumes"]),
        "unknown": unknown,
        "typed_address_linkage": "GO" if linked else "UNVERIFIED",
        "independent_football_accounting": "REQUIRED-separate-observer",
    }
