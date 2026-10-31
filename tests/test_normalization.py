"""Synthetic legend examples: text and color become explicit facts."""

import pytest

from bowl_bound.models import (
    BoundingBox,
    PenaltyCode,
    PenaltyTeam,
    Priority,
    Provenance,
    ResultKind,
    VariableReference,
)
from bowl_bound.normalization import (
    ChartColor,
    NormalizationError,
    chart_color_for_rgb,
    normalize_cell,
)


def source(text: str) -> Provenance:
    return Provenance("a" * 64, "synthetic.pdf", 1, BoundingBox(0, 0, 1, 1), text, (1, 2, 3))


@pytest.mark.parametrize(
    ("rgb", "color"),
    [
        ((255, 2, 0), ChartColor.RED),
        ((95, 255, 0), ChartColor.GREEN),
        ((239, 255, 1), ChartColor.YELLOW),
        ((6, 8, 8), ChartColor.BLACK),
    ],
)
def test_verified_cmyk_rgb_signatures_map_to_chart_legend(
    rgb: tuple[int, int, int], color: ChartColor
) -> None:
    assert chart_color_for_rgb(rgb) is color


@pytest.mark.parametrize(
    ("text", "color", "yards", "priority", "ob"),
    [
        ("5", ChartColor.GREEN, 5, Priority.NORMAL, False),
        ("5", ChartColor.RED, -5, Priority.NORMAL, False),
        ("-5", ChartColor.RED, -5, Priority.NORMAL, False),
        ("(-5)*", ChartColor.RED, -5, Priority.PARENTHESIZED, True),
        ("[4]", ChartColor.GREEN, 4, Priority.BRACKETED, False),
        ("(4)†", ChartColor.GREEN, 4, Priority.PARENTHESIZED, True),
        ("0", ChartColor.RED, 0, Priority.NORMAL, False),
    ],
)
def test_numeric_color_priority_and_markers(
    text: str, color: ChartColor, yards: int, priority: Priority, ob: bool
) -> None:
    evidence = source(text)
    cell = normalize_cell(evidence, color)
    assert cell.kind is ResultKind.YARDS
    assert (cell.yards, cell.priority, cell.out_of_bounds) == (yards, priority, ob)
    assert cell.provenance is evidence


@pytest.mark.parametrize(
    ("text", "color", "kind"),
    [
        ("", ChartColor.WHITE, ResultKind.NO_CHANGE),
        (" ", ChartColor.BLACK, ResultKind.INCOMPLETE),
        ("*", ChartColor.WHITE, ResultKind.NO_CHANGE),
        ("INC", ChartColor.BLACK, ResultKind.INCOMPLETE),
    ],
)
def test_blanks_are_color_dependent(text: str, color: ChartColor, kind: ResultKind) -> None:
    cell = normalize_cell(source(text), color)
    assert cell.kind is kind
    assert cell.out_of_bounds is (text == "*")


@pytest.mark.parametrize(
    ("text", "color", "reference", "sign"),
    [
        ("DS", ChartColor.GREEN, VariableReference.DS, 1),
        ("X", ChartColor.RED, VariableReference.X, -1),
        ("-T1", ChartColor.RED, VariableReference.T1, -1),
        ("T0", ChartColor.GREEN, VariableReference.X, 1),
        ("T2*", ChartColor.GREEN, VariableReference.T2, 1),
        ("T3", ChartColor.GREEN, VariableReference.T3, 1),
    ],
)
def test_variable_references(
    text: str, color: ChartColor, reference: VariableReference, sign: int
) -> None:
    cell = normalize_cell(source(text), color)
    assert cell.variable is reference
    assert cell.variable_multiplier == sign
    assert cell.yards is None
    assert cell.out_of_bounds is text.endswith("*")


@pytest.mark.parametrize(
    ("text", "kind", "yards"),
    [
        ("F +6", ResultKind.FUMBLE, 6),
        ("F -2", ResultKind.FUMBLE, -2),
        ("F 0", ResultKind.FUMBLE, 0),
        ("F", ResultKind.FUMBLE, 0),
        ("F+0", ResultKind.FUMBLE, 0),
        ("INT 28", ResultKind.INTERCEPTION, 28),
        ("INT -2", ResultKind.INTERCEPTION, -2),
        ("BK -7", ResultKind.BLOCKED_KICK, -7),
    ],
)
def test_red_does_not_negate_event_locations(text: str, kind: ResultKind, yards: int) -> None:
    cell = normalize_cell(source(text), ChartColor.RED)
    assert (cell.kind, cell.yards) == (kind, yards)
    assert cell.provenance.original_text == text


@pytest.mark.parametrize("text", ["F +T1", "F -DS", "INT X", "BK -X"])
def test_variable_event_locations(text: str) -> None:
    cell = normalize_cell(source(text), ChartColor.RED)
    assert cell.variable_multiplier == (-1 if "-" in text else 1)
    assert cell.variable is not None


@pytest.mark.parametrize(
    ("text", "team", "code", "yards"),
    [
        ("OFF 10", PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 10),
        ("DEF5", PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 5),
        ("Off S", PenaltyTeam.OFFENSE, PenaltyCode.S, None),
        ("DEF R", PenaltyTeam.DEFENSE, PenaltyCode.R, None),
        ("DEF5X", PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS_X, None),
        ("DEF 5Y", PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS, None),
        ("PI 12", PenaltyTeam.DEFENSE, PenaltyCode.PI, 12),
    ],
)
def test_penalty_facts_not_enforcement(
    text: str, team: PenaltyTeam, code: PenaltyCode, yards: int | None
) -> None:
    cell = normalize_cell(source(text), ChartColor.YELLOW)
    assert cell.kind is ResultKind.PENALTY
    assert cell.penalty is not None
    assert (cell.penalty.team, cell.penalty.code, cell.penalty.yards) == (team, code, yards)
    assert cell.provenance.original_text == text


def test_variable_pi_is_not_negated_by_color() -> None:
    penalty = normalize_cell(source("PI X"), ChartColor.YELLOW).penalty
    assert penalty is not None
    assert (penalty.variable, penalty.variable_multiplier) == (VariableReference.X, 1)


@pytest.mark.parametrize(
    ("text", "color", "kind"),
    [
        ("B", ChartColor.GREEN, ResultKind.BREAKAWAY),
        ("QR", ChartColor.WHITE, ResultKind.QUARTERBACK_RUN),
        ("QT", ChartColor.RED, ResultKind.QUARTERBACK_TRAPPED),
        ("SOP", ChartColor.WHITE, ResultKind.SPRINT_OUT_PASS),
        ("BLP", ChartColor.WHITE, ResultKind.BOOTLEG_PASS),
        ("FG*", ChartColor.RED, ResultKind.FIELD_GOAL_REFERENCE),
        ("KO†", ChartColor.GREEN, ResultKind.KICKOFF_REFERENCE),
        ("NG", ChartColor.RED, ResultKind.NO_GOOD_FIELD_GOAL),
        ("(B)", ChartColor.GREEN, ResultKind.BREAKAWAY),
        ("[TD]", ChartColor.GREEN, ResultKind.TOUCHDOWN),
    ],
)
def test_named_results(text: str, color: ChartColor, kind: ResultKind) -> None:
    cell = normalize_cell(source(text), color)
    assert cell.kind is kind
    assert cell.out_of_bounds is (text[-1] in "*†")


@pytest.mark.parametrize(
    ("text", "color"),
    [
        ("", ChartColor.RED),
        ("", ChartColor.GREEN),
        ("", ChartColor.YELLOW),
        ("5", ChartColor.WHITE),
        ("5", ChartColor.BLACK),
        ("-5", ChartColor.GREEN),
        ("+5", ChartColor.RED),
        ("OFF5", ChartColor.GREEN),
        ("F +6", ChartColor.GREEN),
        ("mystery", ChartColor.WHITE),
        ("(5]", ChartColor.GREEN),
        ("((5))", ChartColor.GREEN),
        ("F +6*", ChartColor.RED),
        ("5**", ChartColor.GREEN),
        ("INT", ChartColor.RED),
        ("BK", ChartColor.RED),
        ("OFF 0", ChartColor.YELLOW),
        ("OFF 5Y", ChartColor.YELLOW),
    ],
)
def test_ambiguous_missing_and_unknown_forms_fail(text: str, color: ChartColor) -> None:
    with pytest.raises(NormalizationError, match="page 1"):
        normalize_cell(source(text), color)


def test_unknown_color_is_not_guessed_from_rgb() -> None:
    with pytest.raises(NormalizationError):
        normalize_cell(source("5"), "green")


@pytest.mark.parametrize("text", ["INT", "BK", "1 0", "F 1 2", "O FF 5", "D S", "T 1"])
def test_missing_locations_and_fragmented_tokens_are_not_repaired(text: str) -> None:
    color = ChartColor.YELLOW if "FF" in text else ChartColor.RED
    with pytest.raises(NormalizationError):
        normalize_cell(source(text), color)


@pytest.mark.parametrize(
    ("text", "color"),
    [
        ("B", ChartColor.RED),
        ("QR", ChartColor.RED),
        ("QT", ChartColor.WHITE),
        ("FG", ChartColor.GREEN),
        ("KO", ChartColor.RED),
        ("NG", ChartColor.GREEN),
        ("INC", ChartColor.WHITE),
        ("5", ChartColor.YELLOW),
        ("DS", ChartColor.YELLOW),
        ("*", ChartColor.BLACK),
        ("INC*", ChartColor.BLACK),
        ("QR*", ChartColor.WHITE),
        ("TD*", ChartColor.GREEN),
        ("(QR)", ChartColor.WHITE),
        ("DEF R*", ChartColor.YELLOW),
        ("(DEF 5)", ChartColor.YELLOW),
        ("OFF 5X", ChartColor.YELLOW),
        ("PI S", ChartColor.YELLOW),
        ("PI R", ChartColor.YELLOW),
        ("OFF+DS", ChartColor.YELLOW),
        ("()", ChartColor.WHITE),
        ("[]", ChartColor.WHITE),
        ("(*)", ChartColor.WHITE),
        ("*5", ChartColor.GREEN),
        ("5†*", ChartColor.GREEN),
    ],
)
def test_review_negative_cases(text: str, color: ChartColor) -> None:
    with pytest.raises(NormalizationError):
        normalize_cell(source(text), color)


@pytest.mark.parametrize("text", [" f + 6 ", "F\u00a0+6", "F+6"])
def test_legal_spacing_and_case_preserve_evidence(text: str) -> None:
    evidence = source(text)
    cell = normalize_cell(evidence, ChartColor.RED)
    assert cell.kind is ResultKind.FUMBLE
    assert cell.yards == 6
    assert cell.provenance is evidence


def test_invalid_provenance_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        normalize_cell(None, ChartColor.RED)
