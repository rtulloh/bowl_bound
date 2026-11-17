"""Fictional conditional distributions expose coordinate-induced depth bias."""

from collections import Counter
from fractions import Fraction
from itertools import permutations, product

import pytest

from tools.chartgen.conditional_depth_balance import balance_conditionals


def test_balances_both_formations_and_calls_not_only_call_marginals() -> None:
    weights = (1,) * 8
    formations = ("A", "A", "F", "F", "A", "A", "F", "F")
    calls = (6,) * 4 + (7,) * 4
    original = (0, 10, 20, 30, 0, 10, 20, 30)
    result = balance_conditionals(
        weights, original, formations, calls, ((0, 1), (10, 1), (20, 1), (30, 1))
    )
    assert result.formation_w1 == result.call_w1 == result.worst_cdf == 0
    assert Counter(result.locations) == Counter(original)
    for labels in (formations, calls):
        for label in set(labels):
            assert Counter(
                x for x, k in zip(result.locations, labels, strict=True) if k == label
            ) == Counter((0, 10, 20, 30))


def test_weighted_complete_independent_oracle_and_inventory() -> None:
    weights = (3, 1, 3, 1)
    original = (0, 0, 30, 30)
    forms = ("A", "A", "F", "F")
    calls = (6, 7, 6, 7)
    result = balance_conditionals(weights, original, forms, calls, ((0, 1), (30, 1)))
    scores = []
    for threes, ones in product(set(permutations((0, 30))), repeat=2):
        values = (threes[0], ones[0], threes[1], ones[1])
        distance = Fraction()
        worst = Fraction()
        for labels in (forms, calls):
            for label in set(labels):
                total = sum(w for w, k in zip(weights, labels, strict=True) if k == label)
                at_zero = sum(
                    w
                    for w, x, k in zip(weights, values, labels, strict=True)
                    if k == label and x == 0
                )
                error = abs(Fraction(at_zero, total) - Fraction(1, 2))
                distance += 30 * error
                worst = max(worst, error)
        scores.append(
            (distance, worst, sum(a != b for a, b in zip(original, values, strict=True)), values)
        )
    assert (
        result.formation_w1 + result.call_w1,
        result.worst_cdf,
        result.edits,
        result.locations,
    ) == min(scores)
    assert result.assignments_evaluated == 4
    for w in set(weights):
        assert Counter(
            x for x, weight in zip(result.locations, weights, strict=True) if weight == w
        ) == Counter(x for x, weight in zip(original, weights, strict=True) if weight == w)


def test_constant_pool_does_not_get_invented_diversity() -> None:
    result = balance_conditionals((1, 3), (7, 7), ("A", "F"), (6, 7), ((7, 2),))
    assert result.locations == (7, 7)
    assert result.formation_w1 == result.call_w1 == 0
    assert result.assignments_evaluated == 1


def test_absent_formation_is_excluded_not_a_zero_cdf() -> None:
    result = balance_conditionals((1, 1), (0, 30), ("A", "A"), (6, 7), ((0, 1), (30, 1)))
    assert result.active_formations == ("A",)
    assert result.formation_w1 == 0


@pytest.mark.parametrize(
    "weights,locations,forms,calls,support",
    [
        ((True,), (3,), ("A",), (6,), ((3, 1),)),
        ((1,), (3,), ("",), (6,), ((3, 1),)),
        ((1,), (3,), ("A",), (True,), ((3, 1),)),
        ((1,), (3,), ("A",), (6,), ()),
        ((1,), (4,), ("A",), (6,), ((3, 1),)),
    ],
)
def test_invalid_or_unsupported_operands_refuse(
    weights: tuple, locations: tuple, forms: tuple, calls: tuple, support: tuple
) -> None:
    with pytest.raises(ValueError):
        balance_conditionals(weights, locations, forms, calls, support)
