"""Convert classified chart color and source text into semantic facts, never rules."""

import re
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
_NAMED = {
    "B": (ResultKind.BREAKAWAY, ChartColor.GREEN),
    "QR": (ResultKind.QUARTERBACK_RUN, ChartColor.WHITE),
    "QT": (ResultKind.QUARTERBACK_TRAPPED, ChartColor.RED),
    "SOP": (ResultKind.SPRINT_OUT_PASS, ChartColor.WHITE),
    "BLP": (ResultKind.BOOTLEG_PASS, ChartColor.WHITE),
    "TD": (ResultKind.TOUCHDOWN, ChartColor.GREEN),
    "FG": (ResultKind.FIELD_GOAL_REFERENCE, ChartColor.RED),
    "KO": (ResultKind.KICKOFF_REFERENCE, ChartColor.GREEN),
    "NG": (ResultKind.NO_GOOD_FIELD_GOAL, ChartColor.RED),
    "INC": (ResultKind.INCOMPLETE, ChartColor.BLACK),
}
_DISTANCE = re.compile(r"([+-]?)([0-9]+|DS|X|T[0-3])")


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
