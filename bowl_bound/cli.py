"""Standalone terminal presentation over public saved-game/coaching interfaces."""

import argparse
import os
import re
import shlex
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from secrets import randbits, token_hex
from typing import TextIO

from .coaching_session import CoachingTurn, GameView, recommend_call
from .dice import DiceSequenceError
from .models import TeamChart
from .save_game import MAX_SAVE_BYTES, SavedGame, dumps_game, loads_game
from .session import PendingDecisionError, PlayReport, SessionFinishedError
from .team_csv import TeamFormatError, load_team

_TEAM_ID = re.compile(r"[1-9][0-9]{0,5}/[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_AUTOMATIC_STEPS = 100
_COMMAND_ERRORS = (
    ValueError,
    OSError,
    UnicodeError,
    PendingDecisionError,
    SessionFinishedError,
    DiceSequenceError,
)
_SELECTION_BOILERPLATE = {
    "Choose an offensive play and defensive formation.",
    "Choose your offensive play; the computer defense stays hidden.",
    "Choose your defensive formation; the computer offense stays hidden.",
}
_PLAY_HELP = {
    "1": "Inside running play",
    "2": "Counter running play",
    "3": "Reverse running play",
    "4": "Delayed running play",
    "5": "Option call; follow the resolved branch",
    "6": "Screen passing play",
    "7": "Sprint-out passing play",
    "8": "Boot-leg passing play",
    "9": "Drop-back passing play",
    "A": "Balanced defensive formation",
    "B": "Short-yardage gaps formation",
    "C": "Short-yardage wide formation",
    "D": "Short-pass prevent formation",
    "E": "Long-pass prevent formation",
    "F": "Blitz formation",
}
_KICK_KEYS = {"punt": "P", "field_goal": "F", "kickoff": "K"}
_ACTION_KEYS = {"kneel": "K", "hail_mary": "H"}
_CHOICE_KEYS = {
    "receive": "R",
    "kick": "K",
    "offense": "O",
    "defense": "D",
    "return": "R",
    "touchback": "TB",
    "fair_catch": "FC",
    "runoff": "C",
    "hurry": "N",
    "spike": "S",
}
HELP = (
    "Shortcuts: use the bracketed keys in the current menu (case-insensitive).\n"
    "Solitaire vs computer: 1-9 offense, A-F defense; control one team only.\n"
    "When offered: P punt, F field goal, K kickoff/kneel, H Hail Mary; R receive.\n"
    "Full commands still work: call KEY; choose ID; kick KEY; action KEY.\n"
    "Inspect: status, stats (/), log, trace, help (?). Enter submits a displayed default only.\n"
    "Files: save PATH (private, new file only); load PATH (same local charts required).\n"
    "retry resumes a stopped computer turn; quit exits without an automatic save.\n"
    "Quote paths containing spaces. Saves and terminal chart traces are private."
)


@dataclass(frozen=True)
class TeamEntry:
    """One locally installed team, with its canonical catalog identifier."""

    key: str
    name: str
    season: int


class TeamCatalog:
    """Discover the ordinary YAML/CSV catalog without importing the web application."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.problems: tuple[str, ...] = ()

    def load(self, key: str) -> TeamChart:
        """Load an exact season/team ID, rejecting traversal and symlinked team paths."""
        if len(key) > 120 or not _TEAM_ID.fullmatch(key):
            raise ValueError("Team ID must be a canonical season/team, e.g. 2007/cedar-valley.")
        season, folder = key.split("/")
        directory = self.root / season
        if any(path.is_symlink() for path in (self.root, directory, directory / folder)):
            raise ValueError("Team folders must not use symlinks.")
        try:
            chart, _ = load_team(directory, folder)
        except (TeamFormatError, OSError) as error:
            raise ValueError("Team could not be read; check --seasons and --list-teams.") from error
        return chart

    def teams(self) -> tuple[TeamEntry, ...]:
        """List readable teams, reporting unreadable entries without echoing chart data."""
        entries: list[TeamEntry] = []
        problems: list[str] = []
        if not self.root.is_dir() or self.root.is_symlink():
            raise ValueError("Seasons directory is missing or symlinked; check --seasons.")
        for metadata in sorted(self.root.glob("*/*/team.yaml")):
            folder = metadata.parent
            key = folder.parent.name + "/" + folder.name
            if not _TEAM_ID.fullmatch(key) or any(
                path.is_symlink() for path in (folder.parent, folder, metadata)
            ):
                continue
            try:
                chart = self.load(key)
            except ValueError:
                problems.append(f"{key}: could not be read")
            else:
                entries.append(TeamEntry(key, chart.name, chart.season))
        self.problems = tuple(problems)
        return tuple(entries)


def read_save(path: Path, loader: Callable[[str], TeamChart]) -> SavedGame:
    """Bound file reads before invoking the unchanged validated save codec."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Load requires a regular, non-symlinked save file.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("Load requires a regular save file.")
        data = source.read(MAX_SAVE_BYTES + 1)
    if len(data) > MAX_SAVE_BYTES:
        raise ValueError("Save exceeds the 2 MiB limit; current game unchanged.")
    return loads_game(data.decode("utf-8"), loader)


def write_save(path: Path, game: SavedGame) -> None:
    """Create a private file without replacing an existing file or following a symlink."""
    text = dumps_game(game)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError(
            "Save already exists; choose a new filename (nothing overwritten)."
        ) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(text)
    except (OSError, KeyboardInterrupt):
        path.unlink(missing_ok=True)  # Only the new file exclusively created above.
        raise


class TerminalGame:
    """Adapt public engine views and legal IDs to an inspectable terminal session."""

    def __init__(
        self,
        game: SavedGame,
        load_team: Callable[[str], TeamChart],
        *,
        human_side: str = "home",
        output: TextIO | None = None,
        compact: bool = False,
        trace: bool = False,
        roster_root: Path | None = None,
    ) -> None:
        if human_side not in {"home", "away"}:
            raise ValueError(
                "Human side must be home or away; the opponent is computer-controlled."
            )
        if roster_root is not None:
            game.load_rosters(roster_root)
        self.roster_root = roster_root
        self.game = game
        self.load_team = load_team
        self.human_side = human_side
        self.output = output if output is not None else sys.stdout
        self.compact = compact
        self.trace = trace
        self.helper_enabled = True
        self.stopped = False
        self.automatic_paused = False
        self.last_report: PlayReport | None = None

    def _print(self, text: str) -> None:
        print(text, file=self.output)

    def public_view(self) -> tuple[GameView, CoachingTurn | None]:
        """Inspect public state without asking the coordinator for private selections."""
        return self.game.coach_view(self.human_side)

    def display(self) -> None:
        """Display engine state, labels and public legal controls, never derived results."""
        view, turn = self.public_view()
        clock = getattr(view, "clock", None)
        away_timeout = f" ({clock.timeouts[1]})" if clock else ""
        home_timeout = f" ({clock.timeouts[0]})" if clock else ""
        parts = [f"{clock.quarter_label} {clock.label}"] if clock else []
        parts.append(
            f"{view.away} {view.score.away}{away_timeout} - "
            f"{view.home} {view.score.home}{home_timeout}"
        )
        if view.state:
            parts.extend(
                (
                    f"{view.state.situation} @ {view.state.spot}",
                    f"{view.state.possession_name} ball",
                )
            )
        self._print("\n" + " | ".join(parts))
        if self.trace and view.phase in {"opening_choice", "overtime_choice"}:
            self._toss_trace(view)
        for status in dict.fromkeys((view.status, turn.status) if turn else (view.status,)):
            if status not in _SELECTION_BOILERPLATE:
                self._print(status)
        if self.automatic_paused:
            self._print("Computer stopped. Inspect/save, then use retry to resume.")
        if view.finished:
            self._print("Inspect, save or quit; gameplay is finished.")
            return
        self._controls(view, turn, compact=self.compact)
        if self.game.player_advice_available(self.human_side):
            self._print("Easy helper: " + ("on" if self.helper_enabled else "off") + " [Z] toggle")
            if self.helper_enabled:
                for line in self.game.player_advice(self.human_side):
                    self._print(line)

    def _shortcuts(
        self,
        view: GameView,
        turn: CoachingTurn | None,
    ) -> dict[str, tuple[str, str]]:
        """Bind keys to currently offered public IDs, never to football interpretations."""
        bindings: dict[str, tuple[str, str]] = {}
        if view.finished:
            return bindings
        actions = turn.actions if turn else view.actions
        if turn:
            for action in actions.offense + actions.defense:
                bindings[action.key.upper()] = ("call", action.key)
        for action in actions.special:
            if key := _KICK_KEYS.get(action.key):
                bindings.setdefault(key, ("kick", action.key))
        game_actions = turn.game_actions if turn else getattr(view, "game_actions", ())
        for action in game_actions:
            if key := _ACTION_KEYS.get(action.key):
                bindings.setdefault(key, ("action", action.key))
        pending = turn.pending if turn else view.pending
        if pending:
            for index, choice in enumerate(pending.choices, 1):
                if not choice.enabled:
                    continue
                target = ("choose", choice.id)
                if key := _CHOICE_KEYS.get(choice.id.rsplit(":", 1)[-1]):
                    bindings.setdefault(key, target)
                if not getattr(view, "clock_optional", False):
                    bindings.setdefault(str(index), target)
        for side, key in ((self.human_side, "T"),):
            for verb, controls in (
                ("action", game_actions),
                ("choose", pending.choices if pending else ()),
            ):
                target_id = f"timeout:{side}" if verb == "action" else f"clock:timeout:{side}"
                if any(
                    (c.key if verb == "action" else c.id) == target_id
                    and getattr(c, "enabled", True)
                    for c in controls
                ):
                    bindings.setdefault(key, (verb, target_id))
        return bindings

    def _controls(
        self,
        view: GameView,
        turn: CoachingTurn | None,
        *,
        compact: bool,
    ) -> None:
        """Render full or compact controls using the same bindings as command dispatch."""
        if view.finished:
            self._print("Gameplay is finished; inspect, save or quit.")
            return
        bindings = self._shortcuts(view, turn)

        def label(verb: str, key: str, text: str) -> str:
            shortcuts = " ".join(
                f"[{alias}]" for alias, target in bindings.items() if target == (verb, key)
            )
            command = f" ({verb} {key})" if verb == "choose" or not shortcuts else ""
            return f"{shortcuts} {text}{command}".lstrip()

        actions = turn.actions if turn else view.actions
        if compact and (actions.offense or actions.defense):
            parts = []
            for role, calls, complete, span in (
                ("OFF", actions.offense, "123456789", "1-9"),
                ("DEF", actions.defense, "ABCDEF", "A-F"),
            ):
                if calls:
                    keys = tuple(a.key for a in calls)
                    summary = span if keys == tuple(complete) else ",".join(keys)
                    parts.append(f"{role}: {summary}")
            aliases = {target: alias for alias, target in bindings.items() if target[0] != "call"}
            if aliases:
                parts.append(",".join(aliases.values()))
            parts.append("W=save | /=stats | ?=help")
            default = None if self.automatic_paused else recommend_call(view, turn)
            suffix = f" (Default={default.key}/{default.label})" if default else ""
            self._print("  " + " | ".join(parts) + suffix)
            return

        def heading(title: str) -> None:
            self._print("\n" + title)
            self._print("  " + "-" * 40)

        if actions.offense:
            heading("OFFENSIVE PLAY CALL")
            for group, keys in (("RUNNING / OPTION PLAYS:", "12345"), ("PASSING PLAYS:", "6789")):
                calls = tuple(a for a in actions.offense if a.key in keys)
                if calls:
                    self._print("\n  " + group)
                    for action in calls:
                        text = f"[{action.key}] {action.label}"
                        self._print(f"    {text:<30} - {_PLAY_HELP.get(action.key, '')}")
        if actions.defense:
            heading("DEFENSIVE FORMATION")
            for action in actions.defense:
                text = f"[{action.key}] {action.label}"
                self._print(f"    {text:<30} - {_PLAY_HELP.get(action.key, '')}")
        game_actions = turn.game_actions if turn else getattr(view, "game_actions", ())
        special_plays = tuple(a for a in game_actions if not a.key.startswith("timeout:"))
        if special_plays:
            self._print("\n  SPECIAL PLAYS:")
            for action in special_plays:
                self._print("    " + label("action", action.key, action.label))
        if actions.special:
            self._print("\n  SPECIAL TEAMS:")
            for action in actions.special:
                self._print("    " + label("kick", action.key, action.label))
        pending = turn.pending if turn else view.pending
        optional_clock = getattr(view, "clock_optional", False)
        if pending and not optional_clock:
            heading(f"{pending.chooser} chooses:")
            for choice in pending.choices:
                unavailable = "" if choice.enabled else f" [unavailable: {choice.reason}]"
                self._print("    " + label("choose", choice.id, choice.label) + unavailable)
        self._print("\n  OPTIONS:")
        for action in game_actions:
            if action.key.startswith("timeout:"):
                self._print("    " + label("action", action.key, action.label))
        if pending and optional_clock:
            for choice in pending.choices:
                unavailable = "" if choice.enabled else f" [unavailable: {choice.reason}]"
                self._print("    " + label("choose", choice.id, choice.label) + unavailable)
        if self.game.player_advice_available(self.human_side):
            self._print("    [Z] Easy helper                - Toggle coaching (terminal-local)")
        self._print("    [W] Save Game                  - New private save file")
        self._print("    [/] Stats                      - View current game statistics")
        self._print("    [?] Help                       - Redisplay this menu")
        self._print("    commands                       - Full commands, saves and traces")
        default = None if self.automatic_paused else recommend_call(view, turn)
        if default:
            self._print(f"    [Enter] Default={default.key}/{default.label}")
        self._print("")

    @staticmethod
    def _roll_text(roll: dict[str, object]) -> str:
        dice = roll.get("dice", ())
        faces = ", ".join(f"{die['label']}={die['face']}" for die in dice)
        return f"{roll.get('dice_label', 'Recorded dice')}: [{faces}] -> {roll['total']}"

    def _toss_trace(self, view: GameView) -> None:
        for section, rolls in (
            ("opening_toss", getattr(view, "toss_dice", ())),
            ("overtime_toss", getattr(view, "overtime_toss_dice", ())),
        ):
            for roll in rolls:
                self._print(f"  {section} | {self._roll_text(roll)}")

    def _trace(self, report: PlayReport) -> None:
        for entry in report.trace:
            self._print(
                f"  {entry.section} | {entry.team} | {entry.play} | "
                f"{entry.formation or 'No formation'} | {self._roll_text(entry.roll)} "
                f"| cell {entry.cell}"
            )

    def _report(self, report: PlayReport | None) -> None:
        if report is not None and report != self.last_report:
            self.last_report = report
            self._print("")
            if report.called_play:
                self._print(f"  Offense: {report.called_play}")
            if report.defense:
                self._print(f"  Defense: {report.defense}")
            self._print(f"► {self.game.commentary(report)}")
            if not report.supported:
                self._print(f"Not applied: {report.unsupported_reason}")
            if self.trace:
                self._trace(report)
            elif self.compact and report.trace:
                entries = (f"{e.section}:{e.roll['total']}→{e.cell!r}" for e in report.trace)
                self._print("  (" + " | ".join(entries) + ")")

    def advance_computer(self) -> None:
        """Advance only computer-owned turns; errors/guard require an explicit retry."""
        if self.automatic_paused:
            return
        for _ in range(MAX_AUTOMATIC_STEPS):
            _, turn = self.public_view()
            if turn is None or not turn.automatic:
                return
            try:
                report, _, _, _ = self.game.coach_step(self.human_side)
                self._report(report)
                if report is not None and not report.supported:
                    self.automatic_paused = True
                    self._print("Computer stopped on unsupported result; inspect/save, then retry.")
                    return
            except _COMMAND_ERRORS as error:
                self.automatic_paused = True
                self._print(f"Computer stopped: {error}. Use retry when ready.")
                return
        self.automatic_paused = True
        self._print("Computer safety limit reached; inspect/save, then retry to resume.")

    def command(self, line: str) -> bool:
        """Handle one command; return whether gameplay/resume should advance the loop."""
        try:
            return self._command(shlex.split(line))
        except _COMMAND_ERRORS as error:
            self._print(f"Not applied: {error}")
            return False

    def _command(self, words: list[str]) -> bool:
        if not words:
            view, turn = self.public_view()
            default = None if self.automatic_paused else recommend_call(view, turn)
            if default is None:
                return False
            words = ["call", default.key]
        verb, *args = words
        verb = {"?": "help", "/": "stats"}.get(verb, verb)
        if not args and verb.lower() == "z":
            if self.game.coach_policy != "easy-v1":
                raise ValueError("The helper is only available on Easy.")
            if not self.game.player_advice_available(self.human_side):
                raise ValueError("Toggle the Easy helper at play selection.")
            self.helper_enabled = not self.helper_enabled
            self._print("Easy helper: " + ("on" if self.helper_enabled else "off"))
            return False
        if not args and verb in {"quit", "exit"}:
            self.stopped = True
            self._print("Exited; game not saved automatically. Use save PATH before quitting.")
            return False
        if not args and verb in {"help", "commands", "status", "stats", "log", "trace"}:
            view = self.game.view()
            if verb == "help":
                self._controls(*self.public_view(), compact=False)
            elif verb == "commands":
                self._print(HELP)
            elif verb == "status":
                self.display()
            elif verb == "stats":
                self._print(f"Statistics: {view.home} | {view.away}")
                for row in view.statistics.rows:
                    self._print(f"{row.label}: {row.home} | {row.away}")
            elif verb == "log":
                for report in view.log:
                    self._print(f"{report.number}. {self.game.commentary(report)}")
            else:
                self._toss_trace(view)
                report = self.last_report or (view.log[-1] if view.log else None)
                if report:
                    self._trace(report)
                else:
                    self._print("No play trace recorded.")
            return False
        if verb.lower() == "w":
            verb = "save"
            if not args:
                root = Path("private-data")
                directory = root / "saves"
                if root.is_symlink() or directory.is_symlink():
                    raise ValueError("Default save folders must not be symlinks; use save PATH.")
                root.mkdir(mode=0o700, exist_ok=True)
                directory.mkdir(mode=0o700, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                args = [str(directory / f"bowl-bound-{stamp}-{token_hex(4)}.json")]
        if len(args) == 1 and verb in {"save", "load"}:
            path = Path(args[0]).expanduser()
            if verb == "save":
                write_save(path, self.game)
                self._print(f"Saved privately to {path}; existing files are never overwritten.")
                resume = [
                    sys.executable,
                    "-m",
                    "bowl_bound",
                    "--load",
                    str(path),
                    "--human",
                    self.human_side,
                ]
                if self.compact:
                    resume.append("--compact")
                if self.trace:
                    resume.append("--trace")
                self._print("Resume: " + shlex.join(resume))
                return False
            candidate = read_save(path, self.load_team)
            candidate.coach_view(self.human_side)  # Validate before replacing live game.
            if self.roster_root is not None:
                candidate.load_rosters(self.roster_root)
            self.game = candidate
            self.helper_enabled = True
            self.last_report = None
            self.automatic_paused = False
            self._print("Loaded; terminal control mode unchanged.")
            return True
        if verb == "retry" and not args:
            if not self.automatic_paused:
                raise ValueError("There is no stopped computer turn to retry.")
            self.automatic_paused = False
            return True
        view, turn = self.public_view()
        actions = turn.actions if turn else view.actions
        pending = turn.pending if turn else view.pending
        if not args and (target := self._shortcuts(view, turn).get(verb.upper())):
            verb, value = target
            args = [value]
        if verb == "call" and len(args) == 1 and turn is not None:
            key = args[0].upper()
            if key in {a.key for a in actions.offense + actions.defense}:
                self._report(self.game.coach_step(self.human_side, key)[0])
                return True
        game_actions = turn.game_actions if turn else getattr(view, "game_actions", ())
        legal = {
            "choose": {c.id for c in pending.choices if c.enabled} if pending else set(),
            "kick": {a.key for a in actions.special},
            "action": {a.key for a in game_actions},
        }
        if len(args) == 1 and args[0] in legal.get(verb, set()):
            operation = "decide" if verb == "choose" else verb
            report = self.game.coach_execute(self.human_side, operation, args[0])[0]
            self._report(report)
            if verb == "choose" and args[0] in {"toss:kick", "half:kick"}:
                next_view, next_turn = self.public_view()
                next_actions = next_turn.actions if next_turn else next_view.actions
                if any(a.key == "kickoff" for a in next_actions.special):
                    try:
                        report = self.game.coach_execute(self.human_side, "kick", "kickoff")[0]
                        self._report(report)
                    except _COMMAND_ERRORS as error:
                        self.automatic_paused = True
                        self._print(
                            f"Kick election applied; kickoff not applied: {error}. "
                            "Inspect, then use kick kickoff to retry."
                        )
                        return False
            return True
        raise ValueError("Use an offered command/ID, or status/help to inspect legal controls.")

    def run(self, read_line: Callable[[str], str] | None = None) -> int:
        """Run interactively; EOF/interrupt never choose, auto-save or restart errors."""
        read_line = read_line or input
        try:
            self._print("Bowl Bound terminal — help for commands; saves/traces are private.")
            self.advance_computer()
            self.display()
            while not self.stopped:
                if self.command(read_line("bb> ")):
                    self.advance_computer()
                    self.display()
        except (EOFError, KeyboardInterrupt) as error:
            self._print("Exited; game not saved automatically. Use save PATH before quitting.")
            return 130 if isinstance(error, KeyboardInterrupt) else 0
        return 0


def _seed(value: str) -> int:
    result = int(value)
    if not 0 <= result <= 2**63 - 1:
        raise argparse.ArgumentTypeError("Seed must be between 0 and 2^63-1.")
    return result


def main(argv: list[str] | None = None) -> int:
    """Launch terminal play without importing a web server or optional dependencies."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Example: python -m bowl_bound --play -d medium "
        "--away 2007/harbor-tech --home 2007/cedar-valley --compact",
    )
    parser.add_argument("--play", action="store_true", help="Play interactively (default).")
    parser.add_argument(
        "--seasons",
        type=Path,
        default=Path("seasons"),
        help="Local team catalog root (default: seasons).",
    )
    parser.add_argument(
        "--list-teams", action="store_true", help="List installed team IDs and exit."
    )
    parser.add_argument("--home", help="Home season/team ID (default: 2007/cedar-valley).")
    parser.add_argument("--away", help="Away season/team ID (default: 2007/harbor-tech).")
    parser.add_argument(
        "--human",
        choices=("home", "away"),
        default="home",
        help="Human-controlled team; the opponent is computer-controlled (default: home).",
    )
    parser.add_argument("--game-type", choices=("regular", "postseason"))
    parser.add_argument("--seed", type=_seed)
    parser.add_argument("--coach-seed", type=_seed)
    parser.add_argument(
        "-d",
        "--difficulty",
        choices=("easy", "medium", "hard"),
        default=None,
        help=(
            "Computer difficulty: easy (0.3), medium (0.5, default), hard (0.7); "
            "dice odds never change."
        ),
    )
    parser.add_argument(
        "--load", type=Path, help="Resume a private save with unchanged local charts."
    )
    parser.add_argument("--compact", action="store_true", help="Compact legal play labels.")
    parser.add_argument("--trace", action="store_true", help="Show observed dice/chart audits.")
    args = parser.parse_args(argv)
    catalog = TeamCatalog(args.seasons)
    try:
        if args.list_teams:
            for entry in catalog.teams():
                print(f"{entry.key}: {entry.season} {entry.name}")
            for problem in catalog.problems:
                print(problem, file=sys.stderr)
            return 0
        if args.load:
            if args.difficulty is not None:
                raise ValueError("--load restores its saved coaching policy; omit -d/--difficulty.")
            if any(
                value is not None
                for value in (
                    args.home,
                    args.away,
                    args.seed,
                    args.coach_seed,
                    args.game_type,
                )
            ):
                raise ValueError("--load uses saved teams/seeds/game type; omit new-game options.")
            game = read_save(args.load.expanduser(), catalog.load)
        else:
            home_id = args.home or "2007/cedar-valley"
            away_id = args.away or "2007/harbor-tech"
            game = SavedGame.new(
                catalog.load(home_id),
                catalog.load(away_id),
                home_id=home_id,
                away_id=away_id,
                seed=args.seed if args.seed is not None else randbits(63),
                coach_seed=args.coach_seed,
                coach_policy=f"{args.difficulty or 'medium'}-v1",
                mode="regulation",
                game_type=args.game_type or "regular",
            )
        return TerminalGame(
            game,
            catalog.load,
            human_side=args.human,
            roster_root=args.seasons,
            compact=args.compact,
            trace=args.trace,
        ).run()
    except _COMMAND_ERRORS as error:
        print(f"Cannot start terminal game: {error}", file=sys.stderr)
        return 1
