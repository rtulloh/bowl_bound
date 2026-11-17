"""Fictional distributions exercise coupled encoding, not historical targets."""

from collections import Counter
from fractions import Fraction
from itertools import product

import pytest

from tools.chartgen.coupled_depths import balance_pair, quantize_depths, split_depths


def test_nonconstant_pool_is_not_replaced_by_repeated_midpoint() -> None:
    result = quantize_depths((1,) * 8, ((-4, 1), (4, 1), (12, 1), (28, 1)))
    assert result.status == "represented"
    assert Counter(result.locations) == Counter({-4: 2, 4: 2, 12: 2, 28: 2})
    assert result.wasserstein == result.cdf_error == 0


def test_split_preserves_boundary_atom_proportionally() -> None:
    lower, upper = split_depths(((3, 1), (9, 3), (24, 2)), Fraction(1, 3))
    assert lower == ((3, Fraction(1)), (9, Fraction(1)))
    assert upper == ((9, Fraction(2)), (24, Fraction(2)))
    assert dict(Counter(dict(lower)) + Counter(dict(upper))) == {3: 1, 9: 3, 24: 2}


def test_weighted_slots_and_tails_are_exact() -> None:
    result = quantize_depths((3, 1, 3, 1), ((2, 1), (30, 1)))
    assert result.histogram == ((2, 4), (30, 4))
    assert result.wasserstein == result.cdf_error == 0


def test_constant_support_stays_constant() -> None:
    result = quantize_depths((12, 3, 1), ((7, 2),))
    assert result.locations == (7, 7, 7)
    assert result.wasserstein == 0


def test_exchangeable_call_pair_balances_instead_of_canonical_shallow_deep_order() -> None:
    weights = (1,) * 8
    labels = (0,) * 4 + (1,) * 4
    values, error = balance_pair(
        weights, (-4, -4, 4, 4, 12, 12, 28, 28), labels, ((-4, 1), (4, 1), (12, 1), (28, 1))
    )
    assert Counter(values[:4]) == Counter(values[4:]) == Counter((-4, 4, 12, 28))
    assert error == 0


def test_pair_balance_preserves_complete_weight_class_distribution() -> None:
    weights = (3, 1, 3, 1)
    locations = (2, 2, 30, 30)
    values, _ = balance_pair(weights, locations, (0, 0, 1, 1), ((2, 1), (30, 1)))
    for w in set(weights):
        assert Counter(
            x for x, weight in zip(values, weights, strict=True) if weight == w
        ) == Counter(x for x, weight in zip(locations, weights, strict=True) if weight == w)


def test_insufficient_slots_cannot_claim_both_tails() -> None:
    assert quantize_depths((3,), ((2, 1), (20, 1))).status == "infeasible-tails"


def test_empty_slots_are_dormant_without_invented_depth() -> None:
    result = quantize_depths((), ((2, 1), (20, 1)))
    assert result.status == "dormant"
    assert result.locations == result.histogram == ()
    assert result.wasserstein is None
    assert quantize_depths((), ()).status == "dormant"


def test_small_complete_oracle_matches_constrained_optimum() -> None:
    points = ((-2, 1), (5, 2), (18, 1))
    weights = (3, 1, 1)
    result = quantize_depths(weights, points)
    scores = []
    for values in product((-2, 5, 18), repeat=3):
        if min(values) != -2 or max(values) != 18:
            continue
        actual = Fraction()
        expected = Fraction()
        errors = []
        for x, count in points:
            actual += Fraction(sum(w for w, v in zip(weights, values, strict=True) if v == x), 5)
            expected += Fraction(count, 4)
            errors.append(abs(actual - expected))
        scores.append((errors[0] * 7 + errors[1] * 13, max(errors)))
    assert (result.wasserstein, result.cdf_error) == min(scores)


def test_scale_and_order_do_not_change_depth_histogram() -> None:
    a = quantize_depths((3, 1, 3, 1), ((2, 2), (10, 1), (25, 3)))
    b = quantize_depths(
        (1, 3, 1, 3), ((25, Fraction(3, 11)), (2, Fraction(2, 11)), (10, Fraction(1, 11)))
    )
    assert a.histogram == b.histogram
    assert (a.wasserstein, a.cdf_error) == (b.wasserstein, b.cdf_error)


@pytest.mark.parametrize(
    "weights,support",
    [
        ((True,), ((2, 1),)),
        ((0,), ((2, 1),)),
        ((1,), ()),
        ((1,), ((True, 1),)),
        ((1,), ((2, 0),)),
        ((1,), ((2, 1.0),)),
    ],
)
def test_invalid_or_unknown_support_is_not_zero(weights: tuple, support: tuple) -> None:
    with pytest.raises(ValueError):
        quantize_depths(weights, support)
