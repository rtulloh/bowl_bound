"""Optional per-team roster files used only to name players in commentary (Milestone 9b).

A roster is Paydirt's positional-list format: a JSON object mapping a position key to a
list of player names. It never affects results, state, statistics, or traces, and
choosing a name consumes no randomness: callers pass an explicit index.

Rosters are private by default and are not packaged. Errors never echo file contents.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .team_csv import team_folder_name

ROSTER_FILE = "roster.json"
POSITIONS = ("qb", "rb", "wr", "te", "ol", "dl", "lb", "db", "k", "p", "kr")
MAX_FILE_BYTES = 100_000
MAX_NAME_LENGTH = 100
MAX_PLAYERS_PER_POSITION = 60

_GENERIC = {
    "qb": "the quarterback",
    "rb": "the running back",
    "wr": "the receiver",
    "te": "the tight end",
    "ol": "the offensive lineman",
    "dl": "the defensive lineman",
    "lb": "the linebacker",
    "db": "the defensive back",
    "k": "the kicker",
    "p": "the punter",
    "kr": "the kick returner",
}


class RosterFormatError(ValueError):
    """A roster file is malformed. Messages name the problem, never the value."""


@dataclass(frozen=True)
class Roster:
    """Player names by position; every position is present, possibly empty."""

    players: dict[str, tuple[str, ...]]


def parse_roster(text: str) -> Roster:
    """Parse and strictly validate roster JSON text."""
    if type(text) is not str:
        raise RosterFormatError("roster: input must be text")
    try:
        data = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except RosterFormatError:
        raise
    except (ValueError, RecursionError) as error:
        raise RosterFormatError("roster: not valid JSON") from error
    if type(data) is not dict:
        raise RosterFormatError("roster: top level must be an object")
    unknown = set(data) - set(POSITIONS)
    if unknown:
        raise RosterFormatError("roster: unknown position key")
    players: dict[str, tuple[str, ...]] = {}
    for position in POSITIONS:
        players[position] = _names(data.get(position, []))
    return Roster(players)


def roster_to_json(roster: Roster) -> str:
    """Write a roster canonically, omitting empty positions."""
    data = {p: list(roster.players[p]) for p in POSITIONS if roster.players[p]}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def load_roster(season_dir: Path, folder_name: str) -> Roster | None:
    """Load ``<season>/<folder_name>/roster.json``; a missing file returns ``None``."""
    if not isinstance(folder_name, str) or _slug_or_none(folder_name) != folder_name:
        raise RosterFormatError("roster: not a canonical team folder name")
    season = season_dir.name
    if not (season.isascii() and season.isdecimal()) or str(int(season)) != season:
        raise RosterFormatError("roster: invalid season directory")
    if int(season) < 1:
        raise RosterFormatError("roster: invalid season directory")
    path = season_dir / folder_name / ROSTER_FILE
    if path.is_symlink() or path.parent.is_symlink() or season_dir.is_symlink():
        raise RosterFormatError("roster: symlinked path")
    if not path.exists():
        return None
    if not path.is_file():
        raise RosterFormatError("roster: not a regular file")
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise RosterFormatError("roster: file too large")
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise RosterFormatError("roster: unreadable") from error
    if text.startswith("\ufeff"):
        raise RosterFormatError("roster: byte order mark")
    return parse_roster(text)


def player_name(roster: Roster | None, position: str, index: int = 0) -> str:
    """Return a player's name, or generic wording when there is no roster entry.

    The index wraps around the position's list. No randomness is used, so naming
    cannot perturb the gameplay random stream.
    """
    if type(position) is not str or position not in _GENERIC:
        raise ValueError("unknown roster position")
    if type(index) is not int or index < 0:
        raise ValueError("index must be a non-negative integer")
    names = roster.players.get(position, ()) if roster is not None else ()
    if not names:
        return _GENERIC[position]
    return names[index % len(names)]


def _slug_or_none(name: str) -> str | None:
    try:
        return team_folder_name(name)
    except ValueError:
        return None


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RosterFormatError("roster: duplicate key")
        result[key] = value
    return result


def _reject_constant(_name: str) -> object:
    raise RosterFormatError("roster: non-finite number")


_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _names(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        raise RosterFormatError("roster: each position must be a list")
    if len(value) > MAX_PLAYERS_PER_POSITION:
        raise RosterFormatError("roster: too many players for one position")
    names: list[str] = []
    for item in value:
        if type(item) is not str:
            raise RosterFormatError("roster: player names must be strings")
        if not item.strip() or item != item.strip():
            raise RosterFormatError("roster: blank or padded player name")
        if len(item) > MAX_NAME_LENGTH or _CONTROL.search(item):
            raise RosterFormatError("roster: invalid player name")
        if item in names:
            raise RosterFormatError("roster: duplicate player name in a position")
        names.append(item)
    return tuple(names)
