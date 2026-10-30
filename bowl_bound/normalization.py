"""Convert classified chart color and source text into semantic facts, never rules."""

import re
from dataclasses import dataclass
from enum import Enum

from .models import (
    BoundingBox,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Priority,
    Provenance,
    ResultKind,
    VariableReference,
)


class ChartColor(str, Enum):
    """Importer-classified backgrounds; RGB matching is a layout concern."""

    RED = "red"
    GREEN = "green"
    WHITE = "white"
    BLACK = "black"
    YELLOW = "yellow"


@dataclass(frozen=True)
class ColorLegend:
    """One chart color's source tokens, CSV spelling, and PDF RGB evidence."""

    rgb_color: tuple[int, int, int]
    named_tokens: tuple[tuple[str, ResultKind], ...] = ()
    csv_marker: tuple[str, ResultKind] | None = None
    csv_aliases: tuple[str, ...] = ()
    token_patterns: tuple[re.Pattern[str], ...] = ()
    yardage_sign: int | None = None


class NormalizationError(ValueError):
    """Missing, ambiguous, or unsupported source evidence.

    The message names only the page and the reason, so console output and logs never
    contain historical chart text or filenames. The page and bounding box stay on the
    exception for local triage.
    """

    def __init__(self, message: str, page: int, bounding_box: BoundingBox) -> None:
        super().__init__(message)
        self.page = page
        self.bounding_box = bounding_box


_VARIABLES = {reference.value: reference for reference in VariableReference}
_VARIABLES["T0"] = VariableReference.X
_VARIABLE_KINDS = {
    VariableReference.DS: ResultKind.VARIABLE_DS,
    VariableReference.X: ResultKind.VARIABLE_X,
    VariableReference.T1: ResultKind.VARIABLE_T1,
    VariableReference.T2: ResultKind.VARIABLE_T2,
    VariableReference.T3: ResultKind.VARIABLE_T3,
}
_DISTANCE = re.compile(r"([+-]?)([0-9]+|DS|X|T[0-3])")
_EVENT_TOKEN = re.compile(r"(?:INT|BK|F)(?:\s*[+-]?\s*(?:[0-9]+|DS|X|T[0-3]))?")
_PENALTY_TOKEN = re.compile(r"(?:OFF|DEF|PI)\s+(?:[0-9]+|S|R|5Y|5X|[+-]?(?:DS|X|T[0-3]))")

# Single source for token meaning, serialized spelling, and exact PDF fill RGB.
CELL_LEGEND: dict[ChartColor, ColorLegend] = {
    ChartColor.RED: ColorLegend(
        (255, 0, 0),
        named_tokens=(
            ("QT", ResultKind.QUARTERBACK_TRAPPED),
            ("FG", ResultKind.FIELD_GOAL_REFERENCE),
            ("NG", ResultKind.NO_GOOD_FIELD_GOAL),
        ),
        token_patterns=(_EVENT_TOKEN,),
        yardage_sign=-1,
    ),
    ChartColor.GREEN: ColorLegend(
        (0, 255, 0),
        named_tokens=(
            ("B", ResultKind.BREAKAWAY),
            ("TD", ResultKind.TOUCHDOWN),
            ("KO", ResultKind.KICKOFF_REFERENCE),
        ),
        yardage_sign=1,
    ),
    ChartColor.WHITE: ColorLegend(
        (255, 255, 255),
        named_tokens=(
            ("QR", ResultKind.QUARTERBACK_RUN),
            ("SOP", ResultKind.SPRINT_OUT_PASS),
            ("BLP", ResultKind.BOOTLEG_PASS),
        ),
        csv_marker=("", ResultKind.NO_CHANGE),
        csv_aliases=("*",),
    ),
    ChartColor.BLACK: ColorLegend(
        (0, 0, 0),
        named_tokens=(("INC", ResultKind.INCOMPLETE),),
        csv_marker=("BLACK", ResultKind.INCOMPLETE),
    ),
    ChartColor.YELLOW: ColorLegend(
        (255, 255, 0),
        token_patterns=(_PENALTY_TOKEN,),
    ),
}

_NAMED = {
    token: (kind, color)
    for color, legend in CELL_LEGEND.items()
    for token, kind in legend.named_tokens
}
_CSV_NAMED = {kind: token for legend in CELL_LEGEND.values() for token, kind in legend.named_tokens}
_CSV_NAMED.update(
    {
        kind: token
        for legend in CELL_LEGEND.values()
        if legend.csv_marker
        for token, kind in (legend.csv_marker,)
    }
)


def chart_color_for_csv_token(token: str) -> ChartColor:
    """Return the legend color implied by a canonical serialized chart cell."""
    bare = token.translate(str.maketrans("", "", "*()[]"))
    for color, legend in CELL_LEGEND.items():
        if legend.csv_marker is not None and token == legend.csv_marker[0]:
            return color
        if token in legend.csv_aliases:
            return color
        if any(bare == named for named, _ in legend.named_tokens):
            return color
        if any(
            pattern.fullmatch(token) or pattern.fullmatch(bare) for pattern in legend.token_patterns
        ):
            return color
        if legend.yardage_sign is not None and _DISTANCE.fullmatch(bare):
            sign = -1 if bare.startswith("-") else 1
            if sign == legend.yardage_sign:
                return color
            return next(
                candidate for candidate, other in CELL_LEGEND.items() if other.yardage_sign == sign
            )
    raise ValueError("unsupported serialized chart token")


def canonical_csv_token(kind: ResultKind) -> str:
    """Return the canonical fixed CSV token for a named result kind."""
    for legend in CELL_LEGEND.values():
        if legend.csv_marker is not None and legend.csv_marker[1] is kind:
            return legend.csv_marker[0]
    try:
        return _CSV_NAMED[kind]
    except KeyError as error:
        raise ValueError("result kind has no fixed chart token") from error


def _distance(text: str) -> tuple[int | None, VariableReference | None, int | None]:
    match = _DISTANCE.fullmatch(text)
    if match is None:
        raise ValueError("unsupported distance token")
    sign, token = match.groups()
    multiplier = -1 if sign == "-" else 1
    if token.isdigit():
        return multiplier * int(token), None, None
    return None, _VARIABLES[token], multiplier


def normalize_cell(provenance: Provenance, color: ChartColor) -> NormalizedCell:
    """Normalize a cell using a known background class and unmodified evidence.

    Unknown forms and color conflicts fail with source location; neither blank
    detection nor a parser fallback may invent a zero-yard result.
    """
    if not isinstance(provenance, Provenance):
        raise TypeError("provenance must be Provenance")
    try:
        if type(color) is not ChartColor:
            raise ValueError("background must be an explicitly classified ChartColor")
        return _normalize(provenance, color)
    except ValueError as error:
        raise NormalizationError(
            f"page {provenance.page}: {error}", provenance.page, provenance.bounding_box
        ) from error


def _normalize(provenance: Provenance, color: ChartColor) -> NormalizedCell:
    # Preserve token boundaries: never turn fragmented digits/letters into a value.
    text = provenance.original_text.upper().strip()
    text = text.replace("−", "-").replace("–", "-")
    text = re.sub(r"^(OFF|DEF|PI|INT|BK|F)\s+", lambda match: match[1], text)
    text = re.sub(r"([+-])\s+", lambda match: match[1], text)
    if re.search(r"\s", text):
        raise ValueError("unsupported internal whitespace; fragmented tokens require review")
    out_of_bounds = text.endswith(("*", "†"))
    if out_of_bounds:
        text = text[:-1]
    priority = Priority.NORMAL
    if text.startswith("(") and text.endswith(")"):
        priority, text = Priority.PARENTHESIZED, text[1:-1]
    elif text.startswith("[") and text.endswith("]"):
        priority, text = Priority.BRACKETED, text[1:-1]
    if any(character in text for character in "()[]*†"):
        raise ValueError("malformed priority decoration or out-of-bounds marker")

    def build(kind: ResultKind, **facts: object) -> NormalizedCell:
        return NormalizedCell(
            kind, provenance, priority=priority, out_of_bounds=out_of_bounds, **facts
        )

    if not text:
        if priority is not Priority.NORMAL:
            raise ValueError("empty priority decoration")
        if color is ChartColor.WHITE:
            return build(ResultKind.NO_CHANGE)
        if color is ChartColor.BLACK:
            return build(ResultKind.INCOMPLETE)
        raise ValueError("blank is supported only on white or black backgrounds")

    penalty_match = re.fullmatch(r"(OFF|DEF|PI)([0-9]+|S|R|5Y|5X|[+-]?(?:DS|X|T[0-3]))", text)
    if penalty_match is not None:
        if color is not ChartColor.YELLOW or priority is not Priority.NORMAL or out_of_bounds:
            raise ValueError("penalties require undecorated yellow cells")
        team_token, distance = penalty_match.groups()
        team = PenaltyTeam.OFFENSE if team_token == "OFF" else PenaltyTeam.DEFENSE
        if team_token == "PI":
            yards, variable, multiplier = _distance(distance)
            penalty = PenaltyData(team, PenaltyCode.PI, yards, variable, multiplier)
        elif distance in {"S", "R", "5Y", "5X"}:
            if distance in {"5Y", "5X"} and team is not PenaltyTeam.DEFENSE:
                raise ValueError("5Y/5X tokens are defensive penalties")
            penalty = PenaltyData(team, PenaltyCode(distance))
        elif distance.isdigit():
            penalty = PenaltyData(team, PenaltyCode.FIXED, yards=int(distance))
        else:
            raise ValueError("variable fixed penalties are unsupported")
        return build(ResultKind.PENALTY, penalty=penalty)

    event_match = re.fullmatch(r"(INT|BK|F)([+-]?(?:[0-9]+|DS|X|T[0-3]))?", text)
    if event_match is not None:
        if color is not ChartColor.RED or priority is not Priority.NORMAL:
            raise ValueError("event locations require undecorated red cells")
        event, location = event_match.groups()
        if location is None and event == "F":
            location = "0"  # Approved chart shorthand: bare F explicitly means F+0.
        if location is None:
            raise ValueError("event location is missing")
        yards, variable, multiplier = _distance(location)
        kind = {
            "F": ResultKind.FUMBLE,
            "INT": ResultKind.INTERCEPTION,
            "BK": ResultKind.BLOCKED_KICK,
        }[event]
        return build(kind, yards=yards, variable=variable, variable_multiplier=multiplier)

    if text in _NAMED:
        kind, expected_color = _NAMED[text]
        if color is not expected_color:
            raise ValueError(f"named result requires a {expected_color.value} background")
        if priority is not Priority.NORMAL and kind is not ResultKind.TOUCHDOWN:
            raise ValueError("priority decoration is unsupported on this named result")
        return build(kind)

    if _DISTANCE.fullmatch(text):
        if color not in {ChartColor.RED, ChartColor.GREEN}:
            raise ValueError("yardage requires red or green background")
        if (text.startswith("-") and color is ChartColor.GREEN) or (
            text.startswith("+") and color is ChartColor.RED
        ):
            raise ValueError("explicit sign conflicts with background color")
        yards, variable, _ = _distance(text)
        sign = -1 if color is ChartColor.RED else 1
        if yards is not None:
            return build(ResultKind.YARDS, yards=sign * abs(yards))
        return build(_VARIABLE_KINDS[variable], variable=variable, variable_multiplier=sign)
    raise ValueError("unknown chart token")
