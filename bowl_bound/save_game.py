"""Versioned, private JSON saves, inspired by Paydirt's local-team save workflow.

Replaying fixed commands with observed rolls reconstructs engine-owned continuations
(including kick callbacks). No Python objects/code or chart contents are deserialized.
"""

import hashlib
import json
import sys
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from random import Random
from secrets import randbits
from threading import RLock
from typing import Any

from .coaching import BaselineCoach, CoachChoice
from .coaching_session import CoachingTurn, plan_turn
from .commentary import narrate_report
from .dice import DefensiveRoll, DiceSequenceError, OffensiveRoll, RandomDice, ScriptedDice
from .models import TeamChart
from .regulation import RegulationGame, RegulationView
from .resolution import ChartResolutionError
from .roster import Roster, RosterFormatError, load_roster
from .session import (
    DEFENSE_LABELS,
    InvalidDecisionError,
    PendingDecisionError,
    PlayReport,
    PlaySession,
    SessionFinishedError,
    SessionView,
)
from .team_catalog import TEAM_ID_MAX_LENGTH, TEAM_ID_RE
from .team_csv import TEAM_PRIVILEGES, TeamFileMetadata
from .timing import Clock

SCHEMA_VERSION = 1
ENGINE_PROFILE = "bowl-bound-m22-v1"
_SUPPORTED_ENGINE_PROFILES = {"bowl-bound-m21-v1", ENGINE_PROFILE}
MAX_SAVE_BYTES = 2 * 1024 * 1024
MAX_COMMANDS = 10_000
MAX_ROLLS = 50_000
_ERRORS = (
    InvalidDecisionError,
    PendingDecisionError,
    SessionFinishedError,
    ValueError,
    DiceSequenceError,
    ChartResolutionError,
)
_ERROR_NAMES = {error.__name__ for error in _ERRORS}
Roll = OffensiveRoll | DefensiveRoll
Source = RandomDice | ScriptedDice


class SaveFormatError(ValueError):
    """A save is invalid, incompatible or cannot safely reproduce its original state."""


class GameRevisionConflict(RuntimeError):
    """A coached command was planned from a stale game revision."""


def _fail() -> None:
    raise SaveFormatError("Save is invalid or incompatible; the current game was not replaced.")


def _validate_privileges(value: object) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or any(type(item) is not str or item not in TEAM_PRIVILEGES for item in value)
        or len(set(value)) != len(value)
    ):
        raise SaveFormatError("Team rules privileges are invalid.")
    return value


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    raise TypeError("Unsupported value in save state")


def _json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_value
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _fingerprint(chart: TeamChart) -> str:
    data = asdict(chart)
    # Keep legacy team fingerprints stable; this normalized fact is derived from RGB evidence.
    for section in ("offense", "defense", "supplemental", "special_teams"):
        for record in data[section]:
            record["cell"].pop("chart_color", None)
    # Chart recovery intervals are semantic ranges, not absolute local file paths.
    data["recovery_range"] = list(chart.recovery_range)
    return _digest(data)


def _roll_data(roll: Roll) -> list[int]:
    if isinstance(roll, OffensiveRoll):
        return [roll.black, roll.white_one, roll.white_two]
    return [roll.red, roll.green]


def _read_roll(data: Any) -> Roll:
    if (
        not isinstance(data, list)
        or len(data) not in {2, 3}
        or any(type(n) is not int for n in data)
    ):
        _fail()
    return OffensiveRoll(*data) if len(data) == 3 else DefensiveRoll(*data)


def _source_data(source: Source) -> dict[str, Any]:
    if type(source) is RandomDice and type(source._rng) is Random:
        return {"kind": "random", "state": source._rng.getstate()}
    if type(source) is ScriptedDice:
        if len(source._rolls) - source._position > MAX_ROLLS:
            raise SaveFormatError("Remaining dice script exceeds the supported save size.")
        return {
            "kind": "scripted",
            "remaining": [_roll_data(r) for r in source._rolls[source._position :]],
        }
    raise SaveFormatError("This dice source does not support deterministic saves.")


def _keys(value: Any, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        _fail()


def _read_source(data: Any) -> Source:
    if not isinstance(data, dict):
        _fail()
    if data.get("kind") == "scripted":
        _keys(data, {"kind", "remaining"})
        if not isinstance(data["remaining"], list) or len(data["remaining"]) > MAX_ROLLS:
            _fail()
        return ScriptedDice(_read_roll(r) for r in data["remaining"])
    _keys(data, {"kind", "state"})
    state = data["state"]
    if (
        data["kind"] != "random"
        or not isinstance(state, list)
        or len(state) != 3
        or type(state[0]) is not int
        or state[0] != 3
        or state[2] is not None
    ):
        _fail()
    numbers = state[1]
    if (
        not isinstance(numbers, list)
        or len(numbers) != 625
        or any(type(n) is not int or not 0 <= n <= 2**32 - 1 for n in numbers)
        or not 0 <= numbers[-1] <= 624
    ):
        _fail()
    rng = Random()
    rng.setstate((3, tuple(numbers), None))
    return RandomDice(rng)


class _Tape:
    """Shared by the session and pending procedures, preserving source identity."""

    def __init__(self, future: Source, rolls: list[Roll] | None = None) -> None:
        self.future = future
        self.rolls = list(rolls or [])
        self.replaying = rolls is not None
        self.position = 0

    def _next(self, expected: type[OffensiveRoll] | type[DefensiveRoll]) -> Roll:
        if self.replaying:
            if self.position >= len(self.rolls) or type(self.rolls[self.position]) is not expected:
                _fail()
            roll = self.rolls[self.position]
            self.position += 1
            return roll
        roll = self.future.offensive() if expected is OffensiveRoll else self.future.defensive()
        self.rolls.append(roll)
        return roll

    def offensive(self) -> OffensiveRoll:
        roll = self._next(OffensiveRoll)
        assert isinstance(roll, OffensiveRoll)
        return roll

    def defensive(self) -> DefensiveRoll:
        roll = self._next(DefensiveRoll)
        assert isinstance(roll, DefensiveRoll)
        return roll


class SavedGame:
    """Compose the real engine with a serializable command/dice journal.

    Create save-capable games here; never wrap an already-played engine whose earlier
    commands are unknown. Loading creates an independent game, not a live-game reset.
    """

    @classmethod
    def new(
        cls,
        home: TeamChart,
        away: TeamChart,
        *,
        home_id: str,
        away_id: str,
        seed: int,
        mode: str = "drive",
        start_yards_to_goal: int = 65,
        game_type: str = "regular",
        clock: Clock | None = None,
        dice: Source | None = None,
        coach_seed: int | None = None,
        coach_policy: str = "baseline",
        advanced_ii: bool = True,
        home_privileges: tuple[str, ...] = (),
        away_privileges: tuple[str, ...] = (),
    ) -> "SavedGame":
        config = {
            "seed": seed,
            "mode": mode,
            "start_yards_to_goal": start_yards_to_goal,
            "game_type": game_type,
            "clock": asdict(clock or Clock()),
            "coach_seed": randbits(63) if coach_seed is None else coach_seed,
            "advanced_ii": advanced_ii,
        }
        if coach_policy != "baseline":
            config["coach_policy"] = coach_policy
        # Run the same strict configuration checks used at the untrusted load boundary.
        config = json.loads(_json(config))
        _validate_config(config)
        home_privileges = _validate_privileges(home_privileges)
        away_privileges = _validate_privileges(away_privileges)
        if any(
            not isinstance(key, str)
            or len(key) > TEAM_ID_MAX_LENGTH
            or not TEAM_ID_RE.fullmatch(key)
            for key in (home_id, away_id)
        ):
            raise SaveFormatError("Save team identifiers must be canonical season/team references.")
        tape = _Tape(dice if dice is not None else RandomDice(Random(seed)))
        _source_data(tape.future)  # Refuse non-restorable custom sources before any dice.
        return cls(
            home,
            away,
            home_id,
            away_id,
            config,
            tape,
            home_privileges=home_privileges,
            away_privileges=away_privileges,
        )

    def __init__(
        self,
        home: TeamChart,
        away: TeamChart,
        home_id: str,
        away_id: str,
        config: dict[str, Any],
        tape: _Tape,
        *,
        home_privileges: tuple[str, ...] = (),
        away_privileges: tuple[str, ...] = (),
    ) -> None:
        self._lock = RLock()
        self._teams = {
            "home": {"id": home_id, "fingerprint": _fingerprint(home)},
            "away": {"id": away_id, "fingerprint": _fingerprint(away)},
        }
        if home_privileges:
            self._teams["home"]["privileges"] = list(home_privileges)
        if away_privileges:
            self._teams["away"]["privileges"] = list(away_privileges)
        self._charts = {"home": home, "away": away}
        self._rosters: tuple[Roster | None, Roster | None] = (None, None)
        self._config = dict(config)
        self._config.setdefault("coach_seed", randbits(63))
        if self.coach_policy in {
            "chart-v1",
            "chart-v2",
            "chart-v3",
            "chart-v4",
            "chart-v5",
            "chart-v6",
            "chart-v7",
            "chart-v8",
        }:
            from .chart_coaching import ChartAwareCoach

            version = int(self.coach_policy[-1])
            self._coach = ChartAwareCoach(self._config["coach_seed"], home, away, version=version)
        elif self.coach_policy in {
            "easy-v1",
            "medium-v1",
            "hard-v1",
            "easy-v2",
            "medium-v2",
            "hard-v2",
            "easy-v3",
            "medium-v3",
            "hard-v3",
            "easy-v4",
            "medium-v4",
            "hard-v4",
            "easy-v5",
            "medium-v5",
            "hard-v5",
            "easy-v6",
            "medium-v6",
            "hard-v6",
            "easy-v7",
            "medium-v7",
            "hard-v7",
            "easy-v8",
            "medium-v8",
            "hard-v8",
        }:
            from .difficulty import DifficultyCoach

            self._coach = DifficultyCoach(
                self._config["coach_seed"],
                home,
                away,
                self.coach_policy.rsplit("-v", 1)[0],
                version=int(self.coach_policy[-1]),
            )
        else:
            version = (
                8
                if self.coach_policy == "baseline-v8"
                else (2 if self.coach_policy == "baseline-v2" else 1)
            )
            self._coach = BaselineCoach(self._config["coach_seed"], version=version)
        self._tape = tape
        self._commands: list[dict[str, Any]] = []
        if config["mode"] == "regulation":
            clock = config["clock"]
            self._engine: PlaySession | RegulationGame = RegulationGame.new(
                home,
                away,
                seed=config["seed"],
                game_type=config["game_type"],
                clock=Clock(clock["quarter"], clock["remaining"], tuple(clock["timeouts"])),
                dice=tape,
                advanced_ii=config.get("advanced_ii", False),
                home_privileges=home_privileges,
                away_privileges=away_privileges,
            )
            # OT tosses use the owning game's default source, not a per-call override.
            self._engine._dice = tape
            self._engine._session._dice = tape
        else:
            self._engine = PlaySession.new(
                home,
                away,
                seed=config["seed"],
                start_yards_to_goal=config["start_yards_to_goal"],
                advanced_ii=config.get("advanced_ii", False),
                home_privileges=home_privileges,
                away_privileges=away_privileges,
            )
            self._engine._dice = tape

    def load_rosters(self, seasons_root: Path) -> None:
        """Atomically snapshot optional local rosters without changing saved state."""
        if seasons_root.is_symlink():
            raise RosterFormatError("roster: symlinked root")
        with self._lock:
            loaded: list[Roster | None] = []
            for side in ("home", "away"):
                season, slug = self._teams[side]["id"].split("/")
                loaded.append(load_roster(seasons_root / season, slug))
            self._rosters = (loaded[0], loaded[1])

    def commentary(self, report: PlayReport) -> str:
        """Render engine-owned narration using this game's private snapshot."""
        with self._lock:
            return narrate_report(report, *self._rosters)

    @property
    def seed(self) -> int:
        return self._config["seed"]

    @property
    def coach_policy(self) -> str:
        """Persisted policy version; legacy saves remain baseline."""
        return self._config.get("coach_policy", "baseline")

    @property
    def revision(self) -> int:
        """Return the command-journal position used for optimistic concurrency."""
        with self._lock:
            return len(self._commands)

    def postgame_call_summary(
        self,
    ) -> tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...] | None:
        """Expose Hard's committed call counts only after the engine ends the game."""
        with self._lock:
            if not self.view().finished or not self.coach_policy.startswith("hard-v"):
                return None
            return self._coach.call_history()

    @property
    def mode(self) -> str:
        return self._config["mode"]

    def view(self) -> SessionView | RegulationView:
        with self._lock:
            return self._engine.view()

    def execute_with_view(
        self, operation: str, arguments: list[str]
    ) -> tuple[PlayReport | None, SessionView | RegulationView]:
        """Execute and capture its matching view atomically for concurrent adapters."""
        with self._lock:
            report = self._execute(operation, arguments)
            return report, self.view()

    def coach_execute(
        self,
        human_side: str,
        operation: str,
        value: str,
    ) -> tuple[PlayReport | None, SessionView | RegulationView, CoachingTurn]:
        """Apply only a human-offered non-simultaneous action under the game lock."""
        with self._lock:
            _, turn = self.coach_view(human_side)
            legal = {
                "decide": tuple(c.id for c in turn.pending.choices if c.enabled)
                if turn.pending
                else (),
                "kick": tuple(a.key for a in turn.actions.special),
                "action": tuple(a.key for a in turn.game_actions),
            }
            if turn.automatic or value not in legal.get(operation, ()):
                raise InvalidDecisionError("That action is not offered to the human side.")
            report = self._execute(operation, [value])
            view, next_turn = self.coach_view(human_side)
            return report, view, next_turn

    def player_advice_available(self, human_side: str) -> bool:
        """Check Easy helper availability without analyzing charts or selecting CPU calls."""
        with self._lock:
            if human_side not in {"home", "away"}:
                raise ValueError("human side must be home or away")
            if self.coach_policy not in {
                "easy-v1",
                "easy-v2",
                "easy-v3",
                "easy-v4",
                "easy-v5",
                "easy-v6",
                "easy-v7",
                "easy-v8",
            }:
                return False
            view = self.view()
            if (
                view.finished
                or view.state is None
                or (view.pending and not getattr(view, "clock_optional", False))
            ):
                return False
            return bool(
                view.actions.offense
                if view.state.possession == human_side
                else view.actions.defense
            )

    def player_advice(self, human_side: str) -> tuple[str, ...]:
        """Provide Easy-only public advice without previewing the concealed CPU call."""
        from .coaching_session import observe_game
        from .player_coaching import advice_lines

        with self._lock:
            if not self.player_advice_available(human_side):
                return ()
            view = self.view()
            role = "offense" if view.state.possession == human_side else "defense"
            actions = view.actions.offense if role == "offense" else view.actions.defense
            return advice_lines(
                self._charts[human_side],
                observe_game(view, human_side),
                role,
                {a.key: a.label for a in actions},
            )

    def coach_view(self, human_side: str) -> tuple[SessionView | RegulationView, CoachingTurn]:
        """Expose human controls only, without advancing or revealing a private call."""
        with self._lock:
            view = self.view()
            return view, plan_turn(view, human_side, self._coach).turn

    def coach_step(
        self,
        human_side: str,
        human_call: str | None = None,
        *,
        expected_revision: int | None = None,
    ) -> tuple[PlayReport | None, SessionView | RegulationView, CoachingTurn]:
        """Commit one coached turn and expose only the public report, view and next turn."""
        report, view, turn, _ = self._coach_step_with_choice(
            human_side, human_call, expected_revision=expected_revision
        )
        return report, view, turn

    def _coach_step_with_choice(
        self,
        human_side: str,
        human_call: str | None = None,
        *,
        expected_revision: int | None = None,
    ) -> tuple[PlayReport | None, SessionView | RegulationView, CoachingTurn, CoachChoice | None]:
        """Commit a coached turn and retain the private computer choice for internal audits."""
        with self._lock:
            if expected_revision is not None and expected_revision != len(self._commands):
                raise GameRevisionConflict("The game changed after this coached turn was shown.")
            view = self.view()
            plan = plan_turn(view, human_side, self._coach)
            if view.finished:
                raise SessionFinishedError("the game is finished")
            if plan.turn.automatic:
                if human_call is not None:
                    raise InvalidDecisionError(
                        "No human call is expected for this computer action."
                    )
            elif plan.operation == "snap":
                if human_call not in plan.human_legal:
                    raise InvalidDecisionError("Select an offered play for your current role.")
            else:
                raise PendingDecisionError(
                    "Complete your required decision or special-team action."
                )
            arguments = [human_call if value is None else value for value in plan.arguments]
            report = self._execute(plan.operation, arguments)
            after = self.view()
            return (
                report,
                after,
                plan_turn(after, human_side, self._coach).turn,
                plan.computer_choice,
            )

    def _run(self, operation: str, arguments: list[str]) -> PlayReport | None:
        with self._lock:
            return self._execute(operation, arguments)

    def _execute(self, operation: str, arguments: list[str]) -> PlayReport | None:
        record = {"operation": operation, "arguments": arguments, "error": None}
        before = self._engine.view()
        roll_count, position = len(self._tape.rolls), self._tape.position
        try:
            if operation == "snap":
                result = self._engine.snap(*arguments, dice=self._tape)
            elif operation == "kick":
                result = self._engine.kick(*arguments, dice=self._tape)
            elif operation == "decide":
                if (
                    self._tape.replaying
                    and isinstance(self._engine, RegulationGame)
                    and self._engine._consume_legacy_halftime_choice(arguments[0])
                ):
                    result = None
                else:
                    result = self._engine.decide(*arguments, dice=self._tape)
            elif operation == "action" and isinstance(self._engine, RegulationGame):
                result = self._engine.action(*arguments, dice=self._tape)
            else:
                raise InvalidDecisionError("clock actions require regulation mode")
        except _ERRORS as error:
            record["error"] = type(error).__name__
            # No-op rejections need no replay entry. Preserve commands that changed
            # state or consumed dice, and legacy recorded errors during replay.
            if (
                self._tape.replaying
                or isinstance(error, DiceSequenceError)
                or len(self._tape.rolls) != roll_count
                or self._tape.position != position
                or self._engine.view() != before
            ):
                self._commands.append(record)
            raise
        # The engine command is authoritative; derived history must not prevent
        # its journal entry after state/dice have already advanced.
        self._commands.append(record)
        if operation == "snap" and result is not None and result.supported:
            from .coaching_session import observe_game

            offense_side = before.state.possession
            self._coach.commit_call(
                offense_side,
                *arguments,
                observation=observe_game(before, offense_side),
            )
        return result

    def snap(self, play: str, formation: str) -> PlayReport:
        return self._run("snap", [play, formation])

    def kick(self, action: str) -> PlayReport:
        return self._run("kick", [action])

    def decide(self, choice: str) -> PlayReport | None:
        return self._run("decide", [choice])

    def action(self, action: str) -> PlayReport | None:
        return self._run("action", [action])


def dumps_game(game: SavedGame) -> str:
    """Return a private JSON document without changing dice, decisions or live state."""
    with game._lock:
        return _dumps_game(game)


def _dumps_game(game: SavedGame) -> str:
    if len(game._commands) > MAX_COMMANDS or len(game._tape.rolls) > MAX_ROLLS:
        raise SaveFormatError("This game exceeds the supported save size; gameplay is unchanged.")
    if any(command["error"] == "DiceSequenceError" for command in game._commands):
        raise SaveFormatError("Cannot save after an invalid or exhausted synthetic dice script.")
    data = {
        "schema_version": SCHEMA_VERSION,
        "engine_profile": ENGINE_PROFILE,
        "python": [sys.version_info.major, sys.version_info.minor],
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "teams": game._teams,
        "config": game._config,
        "commands": game._commands,
        "rolls": [_roll_data(r) for r in game._tape.rolls],
        "random_state": _source_data(game._tape.future),
        "state_digest": _view_digest(game.view()),
    }
    data["integrity"] = _digest(data)
    text = _json(data)
    if len(text.encode("utf-8")) > MAX_SAVE_BYTES:
        raise SaveFormatError("This game exceeds the supported save size; gameplay is unchanged.")
    return text


def _validate_config(config: Any) -> None:
    optional = (
        {"coach_seed", "coach_policy", "advanced_ii"} & config.keys()
        if isinstance(config, dict)
        else set()
    )
    _keys(config, {"seed", "mode", "start_yards_to_goal", "game_type", "clock"} | optional)
    if "coach_seed" in optional and (
        type(config["coach_seed"]) is not int or not 0 <= config["coach_seed"] <= 2**63 - 1
    ):
        _fail()
    if "advanced_ii" in optional and type(config["advanced_ii"]) is not bool:
        _fail()
    if "coach_policy" in optional and (
        type(config["coach_policy"]) is not str
        or config["coach_policy"]
        not in {
            "baseline",
            "baseline-v2",
            "baseline-v8",
            "chart-v1",
            "chart-v2",
            "easy-v1",
            "medium-v1",
            "hard-v1",
            "easy-v2",
            "medium-v2",
            "hard-v2",
            "easy-v3",
            "medium-v3",
            "hard-v3",
            "chart-v3",
            "easy-v4",
            "medium-v4",
            "hard-v4",
            "chart-v4",
            "easy-v5",
            "medium-v5",
            "hard-v5",
            "chart-v5",
            "easy-v6",
            "medium-v6",
            "hard-v6",
            "chart-v6",
            "easy-v7",
            "medium-v7",
            "hard-v7",
            "chart-v7",
            "easy-v8",
            "medium-v8",
            "hard-v8",
            "chart-v8",
        }
    ):
        _fail()
    if (
        type(config["seed"]) is not int
        or not 0 <= config["seed"] <= 2**63 - 1
        or config["mode"] not in {"drive", "regulation"}
        or config["game_type"] not in {"regular", "postseason"}
        or type(config["start_yards_to_goal"]) is not int
        or not 1 <= config["start_yards_to_goal"] <= 99
    ):
        _fail()
    clock = config["clock"]
    _keys(clock, {"quarter", "remaining", "timeouts"})
    if not isinstance(clock["timeouts"], list):
        _fail()
    Clock(clock["quarter"], clock["remaining"], tuple(clock["timeouts"]))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in pairs:
        if key in data:
            _fail()
        data[key] = value
    return data


def _constant(_: str) -> None:
    _fail()


def _validate(data: Any) -> None:
    _keys(
        data,
        {
            "schema_version",
            "engine_profile",
            "python",
            "saved_at",
            "teams",
            "config",
            "commands",
            "rolls",
            "random_state",
            "state_digest",
            "integrity",
        },
    )
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != SCHEMA_VERSION
        or data["engine_profile"] not in _SUPPORTED_ENGINE_PROFILES
        or data["python"] != [sys.version_info.major, sys.version_info.minor]
        or not isinstance(data["saved_at"], str)
        or len(data["saved_at"]) > 64
    ):
        _fail()
    _validate_config(data["config"])
    _keys(data["teams"], {"home", "away"})
    if data["engine_profile"] == "bowl-bound-m21-v1" and (
        "advanced_ii" in data["config"]
        or any("privileges" in team for team in data["teams"].values())
    ):
        _fail()
    for team in data["teams"].values():
        if not isinstance(team, dict) or set(team) not in (
            {"id", "fingerprint"},
            {"id", "fingerprint", "privileges"},
        ):
            _fail()
        if (
            not isinstance(team["id"], str)
            or len(team["id"]) > TEAM_ID_MAX_LENGTH
            or not TEAM_ID_RE.fullmatch(team["id"])
            or not isinstance(team["fingerprint"], str)
        ):
            _fail()
        if "privileges" in team:
            values = team["privileges"]
            if (
                type(values) is not list
                or len(set(values)) != len(values)
                or any(type(value) is not str or value not in TEAM_PRIVILEGES for value in values)
            ):
                _fail()
    if not isinstance(data["commands"], list) or len(data["commands"]) > MAX_COMMANDS:
        _fail()
    for record in data["commands"]:
        _keys(record, {"operation", "arguments", "error"})
        operation, arguments = record["operation"], record["arguments"]
        if (
            not isinstance(operation, str)
            or operation not in {"snap", "kick", "decide", "action"}
            or not isinstance(arguments, list)
            or len(arguments) != (2 if operation == "snap" else 1)
            or any(not isinstance(arg, str) or not 1 <= len(arg) <= 100 for arg in arguments)
            or record["error"] not in _ERROR_NAMES | {None}
        ):
            _fail()
    if not isinstance(data["rolls"], list) or len(data["rolls"]) > MAX_ROLLS:
        _fail()
    if data["integrity"] != _digest({k: v for k, v in data.items() if k != "integrity"}):
        _fail()


def loads_game(
    text: str,
    load_team: Callable[[str], TeamChart | tuple[TeamChart, TeamFileMetadata]],
) -> SavedGame:
    """Validate and reconstruct a separate game, using only matching local teams.

    The caller installs the returned game only after this function succeeds. Errors
    never echo save contents, chart values, filesystem paths or supplied code names.
    """
    try:
        if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_SAVE_BYTES:
            _fail()
        data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
        _validate(data)
        source = _read_source(data["random_state"])
        tape = _Tape(source, [_read_roll(r) for r in data["rolls"]])
        loaded_teams = {side: load_team(data["teams"][side]["id"]) for side in ("home", "away")}
        charts: dict[str, TeamChart] = {}
        privileges: dict[str, tuple[str, ...]] = {}
        for side, loaded in loaded_teams.items():
            metadata: TeamFileMetadata | None = None
            if isinstance(loaded, tuple) and len(loaded) == 2:
                chart, metadata = loaded
                if not isinstance(metadata, TeamFileMetadata):
                    _fail()
            else:
                chart = loaded
            if not isinstance(chart, TeamChart):
                _fail()
            stored = tuple(data["teams"][side].get("privileges", ()))
            if "privileges" in data["teams"][side]:
                if metadata is None or metadata.privileges != stored:
                    raise SaveFormatError(
                        "Saved team rules privileges do not match the installed team."
                    )
            elif (
                data["config"].get("advanced_ii", False)
                and metadata is not None
                and "W" in metadata.privileges
            ):
                _fail()
            charts[side] = chart
            privileges[side] = stored
        home, away = charts["home"], charts["away"]
        if any(
            _fingerprint(chart) != data["teams"][side]["fingerprint"]
            for chart, side in ((home, "home"), (away, "away"))
        ):
            raise SaveFormatError(
                "Saved teams do not match the installed teams; current game unchanged."
            )
        game = SavedGame(
            home,
            away,
            data["teams"]["home"]["id"],
            data["teams"]["away"]["id"],
            data["config"],
            tape,
            home_privileges=privileges["home"],
            away_privileges=privileges["away"],
        )
        for record in data["commands"]:
            try:
                game._run(record["operation"], record["arguments"])
            except SaveFormatError:
                raise
            except _ERRORS:
                pass  # Match the recorded error class, never infer a new outcome.
            if game._commands[-1] != record:
                _fail()
        if tape.position != len(tape.rolls):
            _fail()
        view = game.view()
        legacy_halftime = getattr(game._engine, "_legacy_halftime_view", None)
        valid_digests = {
            _view_digest(view),
            _legacy_m27_view_digest(view, getattr(game._engine, "_pending_timing_seconds", None)),
        }
        if legacy_halftime is not None:
            valid_digests.update(
                {
                    _view_digest(legacy_halftime),
                    _legacy_m27_view_digest(legacy_halftime, None),
                }
            )
        if data["state_digest"] not in valid_digests:
            _fail()
        tape.replaying = False
        return game
    except SaveFormatError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        RecursionError,
        OSError,
    ) as error:
        raise SaveFormatError(
            "Save is invalid or incompatible; the current game was not replaced."
        ) from error


def _view_digest(view: SessionView | RegulationView) -> str:
    """Keep the m19 semantic digest stable when adding derived presentation facts."""
    return _semantic_view_digest(asdict(view))


def _legacy_m27_view_digest(
    view: SessionView | RegulationView, pending_timing_seconds: int | None
) -> str:
    """Recreate the pre-M27 digest for a state replayed with implicit timing."""
    data = asdict(view)
    data["actions"]["offense"] = [
        action for action in data["actions"]["offense"] if action["key"] != "Q"
    ]
    data["actions"]["defense"] = [
        action for action in data["actions"]["defense"] if action["key"] != "WCSNEAK"
    ]
    for charge in data.get("timing_log", []):
        if charge["method"] == "standard" and charge["seconds"] > 10:
            charge["method"] = "clock:runoff"
    if data.get("phase") == "clock_choice" and pending_timing_seconds is not None:
        runoff_modifier = {
            "id": "clock:runoff",
            "label": "None",
            "enabled": True,
            "reason": None,
        }
        data["clock_modifiers"] = [runoff_modifier, *data["clock_modifiers"]]
        if data.get("pending") is not None:
            data["pending"]["choices"] = [
                {
                    **runoff_modifier,
                    "label": f"Run {pending_timing_seconds} seconds off the clock",
                },
                *data["pending"]["choices"],
            ]
    return _semantic_view_digest(data)


def _semantic_view_digest(data: dict[str, Any]) -> str:
    """Hash semantic state while excluding view-only diagnostics and labels."""
    presentation_keys = {
        "dice",
        "dice_label",
        "chooser_side",
        "toss_dice",
        "overtime_toss_dice",
        "play_modifiers",
        "defense_name",
        "home_timeouts",
        "away_timeouts",
        "can_kneel_out_game",
        "decision_outcomes",
    }
    legacy_defenses = {
        f"{defense.value} {label}": f"Formation {defense.value}"
        for defense, label in DEFENSE_LABELS.items()
    }

    def semantic(value: Any) -> Any:
        if isinstance(value, dict):
            # Preserve legacy report digests without ignoring the selected defense.
            if (
                isinstance(value.get("defense"), str)
                and value["defense"] in legacy_defenses
                and "description" in value
            ):
                friendly = value["defense"]
                legacy = legacy_defenses[friendly]
                value = {
                    **value,
                    "defense": legacy,
                    "description": value["description"].replace(
                        f"vs {friendly}", f"vs {legacy}", 1
                    ),
                }
            canonical: dict[str, Any] = {}
            for key, item in value.items():
                if key in presentation_keys:
                    continue
                if key == "bounds_declaration" and item is None:
                    continue
                if key == "guaranteed_out_of_bounds" and item is False:
                    continue
                if key == "game_actions" and isinstance(item, (list, tuple)):
                    item = [
                        action for action in item if not action.get("key", "").startswith("bounds:")
                    ]
                canonical[key] = semantic(item)
            return canonical
        if isinstance(value, (list, tuple)):
            return [semantic(item) for item in value]
        return value

    # Selector wording is presentation; retain m19 labels in the semantic digest.
    # Canonicalize only selector/decline wording, not choice IDs or enabled state.
    for action in data["actions"]["defense"]:
        action["label"] = f"Formation {action['key']}"
    if data["pending"] is not None:
        for choice in data["pending"]["choices"]:
            if choice["id"] in {"decline", "kick:decline"}:
                choice["label"] = "Decline penalties and take the result"
    return _digest(semantic(data))
