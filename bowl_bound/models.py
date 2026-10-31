"""Immutable normalized Bowl Bound chart schema version 1."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
from math import isfinite


class Play(IntEnum):
    """The nine callable offensive play columns."""

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9


class Defense(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class SupplementalColumn(str, Enum):
    """Non-callable supplemental chart columns."""

    BREAKAWAY = "B"
    QUARTERBACK_RUN = "QR"
    QUARTERBACK_TRAPPED = "QT"


class SpecialTeamsColumn(str, Enum):
    KICKOFF = "kickoff"
    KICKOFF_RETURN = "kickoff_return"
    PUNT = "punt"
    PUNT_RETURN = "punt_return"
    FIELD_GOAL = "field_goal"
    INTERCEPTION_RETURN = "interception_return"


class Priority(str, Enum):
    NORMAL = "normal"
    PARENTHESIZED = "parenthesized"
    BRACKETED = "bracketed"


class VariableReference(str, Enum):
    DS = "DS"
    X = "X"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class PenaltyTeam(str, Enum):
    OFFENSE = "offense"
    DEFENSE = "defense"


class PenaltyCode(str, Enum):
    FIXED = "fixed"
    S = "S"
    R = "R"
    PI = "PI"
    FIVE_YARDS = "5Y"
    FIVE_YARDS_X = "5X"


class ResultKind(str, Enum):
    YARDS = "yards"
    NO_CHANGE = "no_change"
    INCOMPLETE = "incomplete"
    TOUCHDOWN = "touchdown"
    VARIABLE_DS = "variable_ds"
    VARIABLE_X = "variable_x"
    VARIABLE_T1 = "variable_t1"
    VARIABLE_T2 = "variable_t2"
    VARIABLE_T3 = "variable_t3"
    BREAKAWAY = "B"
    QUARTERBACK_RUN = "QR"
    QUARTERBACK_TRAPPED = "QT"
    SPRINT_OUT_PASS = "SOP"
    BOOTLEG_PASS = "BLP"
    PENALTY = "penalty"
    FUMBLE = "fumble"
    INTERCEPTION = "interception"
    BLOCKED_KICK = "blocked_kick"
    PUNT_REFERENCE = "punt_reference"
    FIELD_GOAL_REFERENCE = "field_goal_reference"
    KICKOFF_REFERENCE = "kickoff_reference"
    NO_GOOD_FIELD_GOAL = "NG"


_VARIABLE_KINDS = {
    ResultKind.VARIABLE_DS: VariableReference.DS,
    ResultKind.VARIABLE_X: VariableReference.X,
    ResultKind.VARIABLE_T1: VariableReference.T1,
    ResultKind.VARIABLE_T2: VariableReference.T2,
    ResultKind.VARIABLE_T3: VariableReference.T3,
}
_LOCATION_KINDS = {ResultKind.FUMBLE, ResultKind.INTERCEPTION, ResultKind.BLOCKED_KICK}
_PUNT_COLUMN_REDIRECTS = {ResultKind.FIELD_GOAL_REFERENCE, ResultKind.KICKOFF_REFERENCE}
_LOWERCASE_HEX = "0123456789abcdef"


@dataclass(frozen=True)
class BoundingBox:
    left: float
    bottom: float
    right: float
    top: float

    def __post_init__(self) -> None:
        values = (self.left, self.bottom, self.right, self.top)
        if any(type(value) not in (int, float) for value in values):
            raise TypeError("bounding-box coordinates must be finite numeric values")
        try:
            finite = all(isfinite(value) for value in values)
        except OverflowError as error:
            raise ValueError("bounding-box coordinates are too large") from error
        if not finite:
            raise TypeError("bounding-box coordinates must be finite numeric values")
        if self.left >= self.right or self.bottom >= self.top:
            raise ValueError("bounding box must have positive width and height")


@dataclass(frozen=True)
class Provenance:
    """PDF evidence; ``rgb_color=None`` denotes no measured metadata fill."""

    source_sha256: str
    filename: str
    page: int
    bounding_box: BoundingBox
    original_text: str
    rgb_color: tuple[int, int, int] | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_sha256, str)
            or len(self.source_sha256) != 64
            or any(character not in _LOWERCASE_HEX for character in self.source_sha256)
        ):
            raise ValueError("source_sha256 must be exactly 64 hexadecimal characters")
        if not isinstance(self.filename, str) or not self.filename:
            raise ValueError("filename must be a non-empty string")
        if type(self.page) is not int or self.page < 1:
            raise ValueError("page must be a one-based integer")
        if not isinstance(self.bounding_box, BoundingBox):
            raise TypeError("bounding_box must be a BoundingBox")
        if not isinstance(self.original_text, str):
            raise TypeError("original_text must be a string")
        if self.rgb_color is not None:
            if type(self.rgb_color) is not tuple or len(self.rgb_color) != 3:
                raise TypeError("rgb_color must be a three-channel tuple or None")
            if any(
                type(channel) is not int or not 0 <= channel <= 255 for channel in self.rgb_color
            ):
                raise ValueError("rgb_color channels must be integers from 0 through 255")


@dataclass(frozen=True)
class PenaltyData:
    team: PenaltyTeam
    code: PenaltyCode
    yards: int | None = None
    variable: VariableReference | None = None
    variable_multiplier: int | None = None

    def __post_init__(self) -> None:
        if type(self.team) is not PenaltyTeam:
            raise TypeError("penalty team must be a PenaltyTeam")
        if type(self.code) is not PenaltyCode:
            raise TypeError("penalty code must be a PenaltyCode")
        if self.yards is not None and type(self.yards) is not int:
            raise TypeError("penalty yards must be an integer")
        if self.variable is not None and type(self.variable) is not VariableReference:
            raise TypeError("penalty variable must be a VariableReference")
        if self.variable_multiplier is not None and type(self.variable_multiplier) is not int:
            raise TypeError("penalty variable_multiplier must be an integer")
        if (self.variable is None) != (self.variable_multiplier is None):
            raise ValueError("a variable distance needs both a reference and a multiplier")
        if self.variable_multiplier == 0:
            raise ValueError("penalty variable multiplier must be signed and non-zero")
        if self.code in {PenaltyCode.FIXED, PenaltyCode.PI}:
            if (self.yards is None) == (self.variable is None):
                raise ValueError("fixed/PI penalties require exactly one distance")
            if self.code is PenaltyCode.FIXED and (self.yards is None or self.yards <= 0):
                raise ValueError("fixed penalties require positive integer yards")
            if self.code is PenaltyCode.PI and self.team is not PenaltyTeam.DEFENSE:
                raise ValueError("PI chart tokens are defensive pass interference")
        elif self.yards is not None or self.variable is not None:
            raise ValueError("S/R/5Y/5X codes cannot carry another distance")


@dataclass(frozen=True)
class NormalizedCell:
    """One normalized fact; this model performs neither parsing nor resolution."""

    kind: ResultKind
    provenance: Provenance
    yards: int | None = None
    variable: VariableReference | None = None
    variable_multiplier: int | None = None
    priority: Priority = Priority.NORMAL
    out_of_bounds: bool = False
    penalty: PenaltyData | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ResultKind:
            raise TypeError("kind must be a ResultKind")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be Provenance")
        if self.provenance.rgb_color is None:
            raise ValueError("normalized chart cells require measured RGB provenance")
        if type(self.priority) is not Priority or type(self.out_of_bounds) is not bool:
            raise TypeError("priority and out_of_bounds must have their declared types")
        if self.yards is not None and type(self.yards) is not int:
            raise TypeError("yards must be an integer")
        has_variable = self.variable is not None or self.variable_multiplier is not None
        if has_variable:
            if (
                type(self.variable) is not VariableReference
                or type(self.variable_multiplier) is not int
            ):
                raise TypeError("variable location requires a reference and integer multiplier")
            if self.variable_multiplier == 0:
                raise ValueError("variable multiplier must be signed and non-zero")
        if self.kind in _VARIABLE_KINDS:
            if self.variable is not _VARIABLE_KINDS[self.kind]:
                raise ValueError("variable result kind requires its matching variable reference")
            if self.yards is not None:
                raise ValueError("variable result kinds do not also carry fixed yards")
        elif self.kind in _LOCATION_KINDS:
            if (self.yards is None) == (not has_variable):
                raise ValueError("turnover and blocked-kick results require exactly one location")
        elif self.kind is ResultKind.YARDS:
            if self.yards is None or has_variable:
                raise ValueError("yards results require fixed integer yards only")
        elif self.kind is ResultKind.PENALTY:
            if not isinstance(self.penalty, PenaltyData):
                raise ValueError("penalty results require penalty data")
            if self.yards is not None or has_variable:
                raise ValueError("penalty results cannot carry yards or variable locations")
        elif self.yards is not None or has_variable:
            raise ValueError("this result kind cannot carry yards or variable locations")
        if self.kind is not ResultKind.PENALTY and self.penalty is not None:
            raise ValueError("only penalty results may carry penalty data")
        if self.out_of_bounds and self.kind not in {
            ResultKind.YARDS,
            ResultKind.NO_CHANGE,
            *_VARIABLE_KINDS,
            *_PUNT_COLUMN_REDIRECTS,
        }:
            raise ValueError(
                "out_of_bounds requires numeric, variable, no-change, or punt-redirect results"
            )


@dataclass(frozen=True)
class OffensiveCell:
    play: Play
    roll: int
    cell: NormalizedCell

    def __post_init__(self) -> None:
        _validate_play(self.play)
        _validate_roll(self.roll, 10, 39)
        _validate_cell(self.cell)
        _validate_placement(self.cell, "offense", self.play)


@dataclass(frozen=True)
class SupplementalCell:
    column: SupplementalColumn
    roll: int
    cell: NormalizedCell

    def __post_init__(self) -> None:
        if type(self.column) is not SupplementalColumn:
            raise TypeError("column must be a SupplementalColumn")
        _validate_roll(self.roll, 10, 39)
        _validate_cell(self.cell)
        _validate_placement(self.cell, "supplemental", self.column)


@dataclass(frozen=True)
class DefensiveCell:
    defense: Defense
    play: Play
    roll: int
    cell: NormalizedCell

    def __post_init__(self) -> None:
        if type(self.defense) is not Defense:
            raise TypeError("defense must be a Defense")
        _validate_play(self.play)
        _validate_roll(self.roll, 1, 5)
        _validate_cell(self.cell)
        _validate_placement(self.cell, "defense", self.play)


@dataclass(frozen=True)
class SpecialTeamsCell:
    column: SpecialTeamsColumn
    roll: int
    cell: NormalizedCell

    def __post_init__(self) -> None:
        if type(self.column) is not SpecialTeamsColumn:
            raise TypeError("column must be a SpecialTeamsColumn")
        _validate_roll(self.roll, 10, 39)
        _validate_cell(self.cell)
        _validate_placement(self.cell, "special_teams", self.column)


@dataclass(frozen=True)
class PatOutcome:
    roll: int
    good: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        _validate_roll(self.roll, 10, 39)
        if type(self.good) is not bool:
            raise TypeError("good must be a bool")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be Provenance")
        if self.provenance.rgb_color is None:
            raise ValueError("PAT outcomes require measured RGB provenance")


@dataclass(frozen=True)
class TeamChart:
    """A complete v1 team chart with 810 chart records plus 30 PAT outcomes."""

    schema_version: int
    name: str
    season: int
    offense: tuple[OffensiveCell, ...]
    supplemental: tuple[SupplementalCell, ...]
    defense: tuple[DefensiveCell, ...]
    special_teams: tuple[SpecialTeamsCell, ...]
    pat_outcomes: tuple[PatOutcome, ...]
    recovery_range: range

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("only integer schema version 1 is supported")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be non-empty")
        if type(self.season) is not int or self.season < 1:
            raise ValueError("season must be a positive integer")
        _validate_records(
            self.offense,
            OffensiveCell,
            {(play, roll) for play in Play for roll in range(10, 40)},
            lambda record: (record.play, record.roll),
            "offense",
        )
        _validate_records(
            self.supplemental,
            SupplementalCell,
            {(column, roll) for column in SupplementalColumn for roll in range(10, 40)},
            lambda record: (record.column, record.roll),
            "supplemental",
        )
        _validate_records(
            self.defense,
            DefensiveCell,
            {(defense, play, roll) for defense in Defense for play in Play for roll in range(1, 6)},
            lambda record: (record.defense, record.play, record.roll),
            "defense",
        )
        _validate_records(
            self.special_teams,
            SpecialTeamsCell,
            {(column, roll) for column in SpecialTeamsColumn for roll in range(10, 40)},
            lambda record: (record.column, record.roll),
            "special_teams",
        )
        _validate_records(
            self.pat_outcomes,
            PatOutcome,
            set(range(10, 40)),
            lambda record: record.roll,
            "pat_outcomes",
        )
        if type(self.recovery_range) is not range:
            raise TypeError("recovery_range must be a range")
        valid_recovery_range = (
            self.recovery_range.step == 1
            and 10 <= self.recovery_range.start < self.recovery_range.stop <= 40
        )
        if not valid_recovery_range:
            raise ValueError("recovery_range must be a non-empty ascending range within 10..39")


def _validate_play(play: Play) -> None:
    if type(play) is not Play:
        raise TypeError("play must be a Play")


def _validate_roll(roll: int, minimum: int, maximum: int) -> None:
    if type(roll) is not int:
        raise TypeError("roll must be an integer")
    if not minimum <= roll <= maximum:
        raise ValueError(f"roll must be within {minimum}..{maximum}")


def _validate_cell(cell: NormalizedCell) -> None:
    if not isinstance(cell, NormalizedCell):
        raise TypeError("cell must be a NormalizedCell")


def _validate_placement(cell: NormalizedCell, container: str, key: object) -> None:
    """Reject result kinds that can never legally appear in this chart column."""
    kind = cell.kind
    in_field_goal = container == "special_teams" and key is SpecialTeamsColumn.FIELD_GOAL
    in_punt = container == "special_teams" and key is SpecialTeamsColumn.PUNT
    in_play_five = container == "offense" and key is Play.FIVE
    if kind is ResultKind.BREAKAWAY and cell.priority is not Priority.NORMAL:
        if container != "defense" or cell.priority is not Priority.PARENTHESIZED:
            raise ValueError("parenthesized Breakaway results belong only in defensive charts")
    if kind is ResultKind.NO_GOOD_FIELD_GOAL and not in_field_goal:
        raise ValueError("NG results belong only in the field-goal column")
    if kind in _PUNT_COLUMN_REDIRECTS and not in_punt:
        raise ValueError("FG/KO redirects belong only in the punt column")
    if kind in {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS} and not in_play_five:
        raise ValueError("SOP/BLP results belong only in offensive play 5")


def _validate_records(
    records: tuple[object, ...],
    record_type: type,
    expected_keys: set[object],
    key_for_record: Callable[[object], object],
    label: str,
) -> None:
    if type(records) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    if any(type(record) is not record_type for record in records):
        raise TypeError(f"{label} contains an invalid record type")
    keys = {key_for_record(record) for record in records}
    if len(keys) != len(records) or keys != expected_keys:
        raise ValueError(f"{label} must contain every chart position exactly once")
