"""Opt-in isolated observation of command attempts, tape draws and raw priority.

This module captures subjects, never derives expected football results. Code-object
profiling observes imported aliases without replacing the engine resolver or dice.
It is unsuitable for shared servers, threads or an existing profiler.
"""

from __future__ import annotations

import hashlib
import json
import marshal
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import fields
from pathlib import Path
from threading import get_ident
from types import FrameType
from typing import Any, cast
from unittest.mock import patch

from .game_audit_capture import ReceiptCapture, _json_value

_CELL_FIELDS = (
    "kind",
    "yards",
    "variable",
    "variable_multiplier",
    "priority",
    "out_of_bounds",
    "penalty",
    "chart_color",
)


def _log_content(reports: list[dict[str, Any]]) -> bytes:
    """Canonical finite JSON used for both endpoint hashes and net changes."""
    return json.dumps(reports, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )


def _log_sha256(reports: list[dict[str, Any]]) -> str:
    """Bind detached finite JSON log facts, not report numbers or descriptions."""
    return hashlib.sha256(_log_content(reports)).hexdigest()


def _cell_facts(cell: Any) -> dict[str, Any]:
    """Copy observed normalized facts, excluding source prose/provenance."""
    return {name: _json_value(getattr(cell, name)) for name in _CELL_FIELDS}


class TypedReceiptCapture(ReceiptCapture):
    """Retain diagnostic facts without claiming capture or football qualification."""

    def __init__(self, resolver: Any, tape_next: Any, *, lookup_rows: bool = False) -> None:
        super().__init__()
        self.commands: list[dict[str, Any]] = []
        self.draws: list[dict[str, Any]] = []
        self.draw_requests: list[dict[str, Any]] = []
        self.foreign_tape_requests: list[dict[str, Any]] = []
        self.priority_attempts: list[dict[str, Any]] = []
        self.priority_events: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.replay_commands_skipped = 0
        self.unprofiled_commands: list[dict[str, Any]] = []
        self.owner_thread = get_ident()
        self._active: tuple[Any, dict[str, Any]] | None = None
        self._games: list[Any] = []
        self._capture_closed = False
        self._final_game: Any = None
        self._final_block: dict[str, Any] | None = None
        self._frames: dict[int, tuple[str, dict[str, Any]]] = {}
        self._resolver, self._tape_next = resolver, tape_next
        self._resolver_code, self._tape_code = resolver.__code__, tape_next.__code__
        self._identity_broken = False
        self._codes = {resolver.__code__: "priority", tape_next.__code__: "draw"}
        self._aliases = []
        for name, module in tuple(sys.modules.items()):
            if name.startswith("bowl_bound.") and module is not None:
                for attribute, value in tuple(vars(module).items()):
                    if value is resolver:
                        self._aliases.append((module, attribute, value))
        self.targets = []
        self._source_pins = {}
        for function in (resolver, tape_next):
            code = function.__code__
            path = Path(code.co_filename).resolve()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self._source_pins[path] = digest
            module = sys.modules[function.__module__]
            module_file = getattr(module, "__file__", None)
            module_spec_origin = getattr(getattr(module, "__spec__", None), "origin", None)
            if (
                not isinstance(module_file, str)
                or not isinstance(module_spec_origin, str)
                or Path(module_file).resolve() != path
                or Path(module_spec_origin).resolve() != path
            ):
                raise ValueError("unexpected target module origin")
            self.targets.append(
                dict(
                    module=function.__module__,
                    name=function.__qualname__,
                    path=str(path),
                    line=code.co_firstlineno,
                    source_sha256=digest,
                    process_local_code_sha256=hashlib.sha256(marshal.dumps(code)).hexdigest(),
                    code_digest_scope=(
                        "Process-local marshal representation; not portable executable identity."
                    ),
                    module_file=getattr(module, "__file__", None),
                    module_spec_origin=getattr(getattr(module, "__spec__", None), "origin", None),
                )
            )
        self._lookup_rows = None
        if lookup_rows:
            from .game_audit_lookup_capture import LookupRowCapture

            self._lookup_rows = LookupRowCapture(self)

    def _final_error(self, stage: str, error: BaseException) -> None:
        assert self._final_block is not None
        self._final_block.update(status="failed", usable=False)
        self._final_block["errors"].append(dict(stage=stage, exception_type=type(error).__name__))
        self._error(stage, error)

    def bind_final_game(self, game: Any) -> bool:
        """Select an observed object; freeze its public facts at context exit.

        This diagnostic does not invoke gameplay or qualify actual fixture identity.
        Invalid selection remains explicit, unusable evidence.
        """
        if self._final_block is not None:
            self._final_error(
                "final_duplicate_selection", ValueError("selection already requested")
            )
            return False
        self._final_block = dict(
            version="1",
            status="pending",
            usable=False,
            errors=[],
            exit_exception_type=None,
            game_number=None,
            last_command_number=None,
            frontiers=None,
            snapshot=None,
            reports=None,
        )
        if (
            self._capture_closed
            or get_ident() != self.owner_thread
            or self._active is not None
            or sys.getprofile() is not None
        ):
            self._final_error(
                "final_selection_isolation", RuntimeError("selection outside isolated capture")
            )
            return False
        number = next((i for i, known in enumerate(self._games, 1) if known is game), None)
        if number is None:
            self._final_error("final_unobserved_object", ValueError("object was not observed"))
            return False
        # A strong reference preserves actual object identity through context exit.
        self._final_game = game
        self._final_block["game_number"] = number
        return True

    def close_final(self, exit_error: BaseException | None) -> None:
        """Freeze the selected public boundary/log, retaining diagnostic failure."""
        self._capture_closed = True
        block = self._final_block
        if block is None:
            return
        block["exit_exception_type"] = type(exit_error).__name__ if exit_error is not None else None
        if exit_error is not None:
            self._final_error("final_abnormal_exit", exit_error)
        if self._final_game is None:
            return
        try:
            if (
                get_ident() != self.owner_thread
                or self._active is not None
                or sys.getprofile() is not None
            ):
                raise RuntimeError("final snapshot outside isolated capture")
            last = next(
                command
                for command in reversed(self.commands)
                if command["game_number"] == block["game_number"]
            )
            snapshot, _, reports = self.snapshot(self._final_game)
            detached = json.loads(
                json.dumps(dict(snapshot=snapshot, reports=reports), allow_nan=False)
            )
            block.update(
                last_command_number=last["number"],
                frontiers={
                    key: len(getattr(self, key))
                    for key in ("commands", "draws", "draw_requests", "priority_attempts")
                },
                **detached,
            )
            block.update(
                status="failed" if self.errors or block["errors"] else "frozen",
                usable=not self.errors and not block["errors"],
            )
        except Exception as error:
            self._final_error("final_snapshot", error)

    def _error(self, stage: str, error: BaseException) -> None:
        self.errors.append(
            dict(
                stage=stage,
                exception_type=type(error).__name__,
                command_number=self._active[1]["number"] if self._active else None,
            )
        )

    def _check_bindings(self) -> None:
        from bowl_bound.save_game import _Tape

        if (
            self._resolver.__code__ is not self._resolver_code
            or _Tape._next is not self._tape_next
            or self._tape_next.__code__ is not self._tape_code
        ):
            raise ValueError("target code/binding changed")
        if any(
            getattr(module, name, None) is not original for module, name, original in self._aliases
        ):
            raise ValueError("resolver alias changed")
        if self._lookup_rows is not None:
            self._lookup_rows.check_bindings()

    def check_targets(self) -> None:
        """Retain identity changes; these checks are not loaded-code attestation."""
        try:
            self._check_bindings()
            for target in self.targets:
                module = sys.modules[target["module"]]
                if (
                    getattr(module, "__file__", None) != target["module_file"]
                    or getattr(getattr(module, "__spec__", None), "origin", None)
                    != target["module_spec_origin"]
                ):
                    raise ValueError("target module origin changed")
            if any(
                hashlib.sha256(path.read_bytes()).hexdigest() != digest
                for path, digest in self._source_pins.items()
            ):
                raise ValueError("target source changed")
            if self._lookup_rows is not None:
                self._lookup_rows.check_sources()
        except Exception as error:
            # Identity diagnostics must not replace the engine's original result.
            self._error("target_identity", error)

    def profile(self, frame: FrameType, event: str, result: Any) -> None:
        """Observe exact target code objects, including all imported aliases."""
        if self._active is not None and event == "call" and not self._identity_broken:
            try:
                self._check_bindings()
            except Exception as error:
                self._identity_broken = True
                self._error("target_identity_during_command", error)
        if self._active is not None and self._lookup_rows is not None:
            self._lookup_rows.profile(frame, event, result, *self._active)
        if self._active is None or frame.f_code not in self._codes:
            return
        try:
            game, command = self._active
            target = self._codes[frame.f_code]
            if target == "draw" and frame.f_locals.get("self") is not game._tape:
                if event == "call":
                    self._error("foreign_tape_request", ValueError("draw used a different tape"))
                    attempt: dict[str, Any] = dict(
                        number=len(self.foreign_tape_requests) + 1,
                        command_number=command["number"],
                        completed=False,
                        expected_type=frame.f_locals["expected"].__name__,
                        matched_active_game_tape=False,
                    )
                    self.foreign_tape_requests.append(attempt)
                    self._frames[id(frame)] = "foreign_draw", attempt
                elif event == "return":
                    _, attempt = self._frames.pop(id(frame))
                    if result is not None:
                        attempt.update(completed=True, faces=_json_value(result))
                return
            if event == "call":
                attempts = self.priority_attempts if target == "priority" else self.draw_requests
                attempt: dict[str, Any] = dict(
                    number=len(attempts) + 1, command_number=command["number"], completed=False
                )
                attempts.append(attempt)
                self._frames[id(frame)] = target, attempt
                if target == "priority":
                    attempt["offense"] = _cell_facts(frame.f_locals["offense"])
                    attempt["defense"] = _cell_facts(frame.f_locals["defense"])
                    caller = frame.f_back
                    attempt["caller"] = (
                        dict(
                            module=caller.f_globals.get("__name__"),
                            function=getattr(caller.f_code, "co_qualname", caller.f_code.co_name),
                        )
                        if caller
                        else None
                    )
                else:
                    attempt["expected_type"] = frame.f_locals["expected"].__name__
                return
            if event != "return":
                return
            _, attempt = self._frames.pop(id(frame))
            # Python profiles exception unwind as return(None). The outer command
            # retains the actual exception; no inner exception type is invented.
            if result is None:
                return
            if target == "draw":
                kind = "offensive" if hasattr(result, "black") else "defensive"
                draw: dict[str, Any] = dict(
                    number=len(self.draws) + 1,
                    kind=kind,
                    faces=_json_value(result),
                    total=result.total,
                )
                if kind == "offensive":
                    draw["direct_sum"] = result.direct_sum
                self.draws.append(draw)
                if self._lookup_rows is not None:
                    self._lookup_rows.observe_draw(game, result, draw["number"])
                attempt.update(completed=True, draw_number=draw["number"])
            else:
                observed = _json_value(result)
                observed["offense"], observed["defense"] = (
                    _cell_facts(result.offense),
                    _cell_facts(result.defense),
                )
                observed_event = dict(
                    number=len(self.priority_events) + 1,
                    offense=attempt["offense"],
                    defense=attempt["defense"],
                    result=observed,
                    caller=attempt["caller"],
                )
                self.priority_events.append(observed_event)
                attempt.update(completed=True, event_number=observed_event["number"])
        except Exception as error:
            # A diagnostic serialization failure must not change the delegated
            # operation. It makes this capture unusable and remains explicit.
            self._error(f"profile_{event}", error)

    def snapshot(self, game: Any) -> tuple[dict[str, Any], Any, list[dict[str, Any]]]:
        """Observe public live facts and tape state; do not call rule helpers."""
        view = game.view()
        live = {
            field.name: _json_value(getattr(view, field.name))
            for field in fields(view)
            if field.name != "log"
        }
        reports = _json_value(view.log)
        log_sha256 = _log_sha256(reports)
        future = game._tape.future
        if hasattr(future, "_rng"):
            source = dict(kind="random", state=_json_value(future._rng.getstate()))
        elif hasattr(future, "_rolls") and hasattr(future, "_position"):
            source = dict(
                kind="scripted", position=future._position, rolls=_json_value(future._rolls)
            )
        else:
            source = dict(kind=type(future).__qualname__, status="UNVERIFIED")
        return (
            dict(
                view=live,
                reports=len(view.log),
                log_sha256=log_sha256,
                journal_length=len(game._commands),
                teams=_json_value(game._teams),
                configuration=_json_value(game._config),
                tape=dict(
                    roll_count=len(game._tape.rolls),
                    position=game._tape.position,
                    replaying=game._tape.replaying,
                    future=source,
                ),
            ),
            view,
            reports,
        )

    def payload(self) -> dict[str, Any]:
        result = super().payload()
        result["typed_capture"] = dict(
            version="2",
            commands=self.commands,
            draws=self.draws,
            draw_requests=self.draw_requests,
            priority_attempts=self.priority_attempts,
            foreign_tape_requests=self.foreign_tape_requests,
            unprofiled_commands=self.unprofiled_commands,
            errors=self.errors,
            replay_commands_skipped=self.replay_commands_skipped,
            targets=self.targets,
            usable=not self.errors,
            aliases=[dict(module=module.__name__, name=name) for module, name, _ in self._aliases],
            scope=(
                "Observed isolated command/tape/raw-priority facts; "
                "completeness and source truth unverified."
            ),
        )
        if self._final_block is not None:
            result["final_object"] = self._final_block
        if self.priority_events:
            result["priority"] = dict(version="1", events=self.priority_events)
        if self._lookup_rows is not None:
            result["lookup_rows"] = self._lookup_rows.payload()
        return json.loads(json.dumps(result, allow_nan=False))


@contextmanager
def capture_typed_receipts(*, lookup_rows: bool = False) -> Iterator[TypedReceiptCapture]:
    """Capture one isolated process/thread, preserving original operation semantics."""
    from bowl_bound.resolution import resolve_cells
    from bowl_bound.save_game import SavedGame, _Tape

    if sys.getprofile() is not None:
        raise RuntimeError("typed receipt capture requires an isolated process without a profiler")
    original = SavedGame._execute
    capture = TypedReceiptCapture(resolve_cells, _Tape._next, lookup_rows=lookup_rows)
    callback = capture.profile

    def unprofiled(game: SavedGame, operation: str, arguments: list[str], reason: str) -> Any:
        attempt: dict[str, Any] = dict(
            number=len(capture.unprofiled_commands) + 1,
            operation=operation,
            reason=reason,
            exception_type=None,
        )
        capture.unprofiled_commands.append(attempt)
        capture.errors.append(
            dict(stage=reason, exception_type="RuntimeError", command_number=None)
        )
        try:
            attempt["arguments"] = list(arguments)
            attempt["teams"] = _json_value(game._teams)
        except Exception as error:
            capture._error("unprofiled_metadata", error)
        try:
            return original(game, operation, arguments)
        except BaseException as error:
            attempt["exception_type"] = type(error).__name__
            raise

    def execute(game: SavedGame, operation: str, arguments: list[str]) -> Any:
        if get_ident() != capture.owner_thread:
            return unprofiled(game, operation, arguments, "foreign_thread")
        if capture._active is not None:
            parent = capture._active
            capture._active = None
            try:
                return unprofiled(game, operation, arguments, "nested_command")
            finally:
                capture._active = parent
        if sys.getprofile() is not None:
            return unprofiled(game, operation, arguments, "profile_ownership")
        if game._tape.replaying:
            capture.replay_commands_skipped += 1
            return original(game, operation, arguments)
        command: dict[str, Any] = dict(
            number=len(capture.commands) + 1,
            operation=operation,
            exception_type=None,
        )
        first_seen = not any(known is game for known in capture._games)
        if first_seen:
            capture._games.append(game)
        command["game_number"] = next(
            i for i, known in enumerate(capture._games, 1) if known is game
        )
        capture.commands.append(command)
        capture._active = game, command
        capture.check_targets()
        before = None
        before_reports = None
        try:
            command["arguments"] = list(arguments)
            if first_seen and capture._lookup_rows is not None:
                capture._lookup_rows.observe_initial(game, command["game_number"])
            command["before"], before, before_reports = capture.snapshot(game)
            command["initial_log"] = before_reports if first_seen else None
        except Exception as error:
            capture._error("before_snapshot", error)
        starts = dict(
            draw_range=len(capture.draws),
            draw_request_range=len(capture.draw_requests),
            priority_range=len(capture.priority_events),
            priority_attempt_range=len(capture.priority_attempts),
        )
        returned = None
        sys.setprofile(callback)
        try:
            returned = original(game, operation, arguments)
            return returned
        except BaseException as error:
            command["exception_type"] = type(error).__name__
            raise
        finally:
            if sys.getprofile() is not callback:
                capture._error("profile_ownership", RuntimeError("profile ownership changed"))
            sys.setprofile(None)
            ends = dict(
                draw_range=len(capture.draws),
                draw_request_range=len(capture.draw_requests),
                priority_range=len(capture.priority_events),
                priority_attempt_range=len(capture.priority_attempts),
            )
            command.update({key: [start, ends[key]] for key, start in starts.items()})
            try:
                command["after"], after, after_reports = capture.snapshot(game)
                command["returned_report"] = _json_value(returned)
                if before is not None:
                    before_reports = cast(list[dict[str, Any]], before_reports)
                    command["report_range"] = [len(before.log), len(after.log)]
                    command["journal_range"] = [
                        command["before"]["journal_length"],
                        command["after"]["journal_length"],
                    ]
                    if len(after_reports) < len(before_reports):
                        capture._error(
                            "unsupported_log_truncation", ValueError("report log shrank")
                        )
                    command["report_changes"] = [
                        dict(
                            index=i,
                            before=before_reports[i] if i < len(before_reports) else None,
                            after=report,
                        )
                        for i, report in enumerate(after_reports)
                        if i >= len(before_reports)
                        or _log_content([report]) != _log_content([before_reports[i]])
                    ]
                    command["report_revisions"] = [
                        change["after"] for change in command["report_changes"]
                    ]
                retained = _json_value(
                    dict(
                        log=[None] * len(after.log),
                        score=after.score,
                        statistics=after.statistics,
                        review=getattr(after, "review", None),
                    )
                )
                capture.record(retained, operation, arguments, _json_value(returned))
            except Exception as error:
                capture._error("after_snapshot", error)
            capture.check_targets()
            capture._active = None

    with patch.object(SavedGame, "_execute", execute):
        exit_error = None
        try:
            yield capture
        except BaseException as error:
            exit_error = error
            raise
        finally:
            if sys.getprofile() is not None:
                capture._error("profile_ownership", RuntimeError("profile ownership changed"))
            sys.setprofile(None)
            capture.check_targets()
            capture.close_final(exit_error)
