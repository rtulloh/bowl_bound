"""Easy helper estimates only numeric chart mass, never full-engine odds."""

from collections import Counter
from dataclasses import replace
from fractions import Fraction
from itertools import product
from random import getstate

import pytest

from bowl_bound.dice import BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES
from bowl_bound.models import NormalizedCell, OffensiveCell, Play, ResultKind
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


@pytest.mark.parametrize(
    "down,distance,target",
    [(1, 7, 4), (2, 7, 5), (3, 7, 7), (4, 7, 7), (1, 1, 1), (2, 1, 1), (2, 10, 7)],
)
def test_targets_round_up_using_exact_down_distance(down: int, distance: int, target: int) -> None:
    from bowl_bound.player_coaching import target_yards

    assert target_yards(down, distance) == target


@pytest.mark.parametrize(
    "down,distance", [(0, 7), (5, 7), (True, 7), (2, 0), (2, -1), (2, 7.1), (2, True)]
)
def test_invalid_situation_is_not_silently_rounded(down: int, distance: int) -> None:
    from bowl_bound.player_coaching import target_yards

    with pytest.raises(ValueError, match="down|distance"):
        target_yards(down, distance)


def test_estimates_match_all_216_physical_faces_and_condition_on_numeric_mass() -> None:
    from bowl_bound.player_coaching import estimate_plays

    weights = Counter(
        10 * b + a + c for b, a, c in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    cells = {10: -2, 11: 0, 12: 2, 13: 5, 14: 8, 30: 7, 31: 9, 39: 50}
    rows = tuple(OffensiveCell(Play.ONE, roll, yards(value)) for roll, value in cells.items())
    (result,) = estimate_plays(rows, ("1",), down=2, distance=7)
    evaluated = sum(weights[roll] for roll in cells)
    assert result.target == 5
    assert result.coverage == Fraction(evaluated, 216)
    assert result.target_rate == Fraction(
        sum(weights[r] for r, value in cells.items() if value >= 5), evaluated
    )
    assert result.positive_rate == Fraction(
        sum(weights[r] for r, value in cells.items() if value > 0), evaluated
    )
    assert result.average_yards == Fraction(
        sum(weights[r] * value for r, value in cells.items()), evaluated
    )


@pytest.mark.parametrize(
    "kind",
    [
        ResultKind.INCOMPLETE,
        ResultKind.BREAKAWAY,
        ResultKind.QUARTERBACK_RUN,
        ResultKind.QUARTERBACK_TRAPPED,
        ResultKind.SPRINT_OUT_PASS,
        ResultKind.BOOTLEG_PASS,
        ResultKind.TOUCHDOWN,
    ],
)
def test_symbolic_rows_are_excluded_not_zero_or_guaranteed_gains(kind: ResultKind) -> None:
    from bowl_bound.player_coaching import estimate_plays

    rows = (
        OffensiveCell(Play.FIVE, 10, yards(5)),
        OffensiveCell(Play.FIVE, 30, NormalizedCell(kind, provenance())),
    )
    (result,) = estimate_plays(rows, ("5",), down=3, distance=5)
    assert result.coverage == Fraction(1, 108)
    assert result.limited and result.target_rate == 1 and result.positive_rate == 1
    assert result.average_yards == 5


def test_turnover_penalty_variable_and_missing_rows_do_not_add_evaluated_mass() -> None:
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam, VariableReference
    from bowl_bound.player_coaching import estimate_plays

    symbolic = (
        NormalizedCell(ResultKind.FUMBLE, provenance(), yards=20),
        NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20),
        NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
        ),
        NormalizedCell(
            ResultKind.VARIABLE_DS,
            provenance(),
            variable=VariableReference.DS,
            variable_multiplier=1,
        ),
    )
    rows = tuple(OffensiveCell(Play.ONE, 10 + index, cell) for index, cell in enumerate(symbolic))
    (result,) = estimate_plays(rows, ("1",), down=1, distance=10)
    assert result.coverage == 0 and result.limited
    assert result.target_rate is result.positive_rate is result.average_yards is None


def test_supported_estimates_rank_ahead_of_sparse_perfection_with_stable_ties() -> None:
    from bowl_bound.player_coaching import estimate_plays

    rows = tuple(row for row in team_chart("Synthetic", offense=4).offense if row.play != Play.ONE)
    rows += (OffensiveCell(Play.ONE, 10, yards(100)),)
    result = estimate_plays(rows, ("1", "4", "3", "2"), down=3, distance=5)
    assert tuple(item.key for item in result) == ("2", "3", "4")
    assert all(item.coverage == 1 and not item.limited and item.target_rate == 0 for item in result)


def test_half_coverage_is_not_limited_and_unoffered_plays_are_never_recommended() -> None:
    from bowl_bound.player_coaching import estimate_plays

    rows = tuple(row for row in team_chart("Synthetic").offense if row.roll < 30)
    result = estimate_plays(rows, ("9", "8"), down=1, distance=10)
    assert {item.key for item in result} == {"8", "9"}
    assert all(item.coverage == Fraction(1, 2) and not item.limited for item in result)
    assert estimate_plays(rows, (), down=1, distance=10) == ()


def test_numeric_analysis_uses_facts_not_provenance_or_live_dice() -> None:
    from bowl_bound.player_coaching import estimate_plays

    chart = team_chart("Synthetic", offense=5)
    rows = tuple(
        replace(
            row,
            cell=replace(
                row.cell,
                provenance=replace(
                    row.cell.provenance, original_text="PRIVATE symbolic-looking text"
                ),
            ),
        )
        for row in chart.offense
    )
    before = getstate()
    assert estimate_plays(rows, ("1",), down=2, distance=7) == estimate_plays(
        chart.offense, ("1",), down=2, distance=7
    )
    assert getstate() == before


def test_duplicate_rows_cannot_create_overstated_coverage_and_invalid_calls_fail() -> None:
    from bowl_bound.player_coaching import estimate_plays

    row = OffensiveCell(Play.ONE, 10, yards(5))
    with pytest.raises(ValueError, match="duplicate"):
        estimate_plays((row, row), ("1",), down=1, distance=10)
    with pytest.raises(ValueError, match="callable"):
        estimate_plays((row,), ("punt",), down=1, distance=10)


@pytest.mark.parametrize("annotation", ["parenthesized", "bracketed", "out_of_bounds"])
def test_annotated_numeric_cells_are_not_plain_numeric_helper_evidence(annotation: str) -> None:
    from bowl_bound.models import Priority
    from bowl_bound.player_coaching import estimate_plays

    cell = (
        replace(yards(20), out_of_bounds=True)
        if annotation == "out_of_bounds"
        else replace(yards(20), priority=Priority(annotation))
    )
    (result,) = estimate_plays((OffensiveCell(Play.ONE, 10, cell),), ("1",), down=1, distance=10)
    assert result.coverage == 0 and result.average_yards is None
