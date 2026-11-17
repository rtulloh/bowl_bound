"""Exact paired optimization must retain every lexicographic objective stage."""

from collections import Counter
from fractions import Fraction
from itertools import permutations
from typing import cast

import pytest

from tools.chartgen import conditional_depth_balance as module


def oracle(values, forms, calls, support):
    total = sum(Fraction(w) for _, w in support)
    scores = []
    for candidate in set(permutations(values)):
        distance, worst = Fraction(), Fraction()
        for labels in (forms, calls):
            for label in set(labels):
                sample = [x for x, k in zip(candidate, labels, strict=True) if k == label]
                actual = expected = Fraction()
                for i, (x, w) in enumerate(support):
                    actual += Fraction(sample.count(x), len(sample))
                    expected += Fraction(w) / total
                    error = abs(actual - expected)
                    worst = max(worst, error)
                    if i + 1 < len(support):
                        distance += error * (support[i + 1][0] - x)
        scores.append(
            (
                distance,
                worst,
                sum(a != b for a, b in zip(values, candidate, strict=True)),
                candidate,
            )
        )
    return min(scores)


@pytest.mark.parametrize(
    "values", [(0, 5, 0, 5), (0, 5, 10, 0, 5, 10), (0, 0, 0, 5, 10, 10), (7, 7, 7, 7)]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_paired_equalweight_matches_independent_complete_objective(values, reverse):
    n = len(values) // 2
    forms = tuple(chr(65 + i) for i in range(n)) * 2
    calls = (6,) * n + (7,) * n
    support = tuple((x, Fraction(i + 1, 3)) for i, x in enumerate(sorted(set(values))))
    if reverse:
        values, forms, calls = (
            tuple(reversed(values)),
            tuple(reversed(forms)),
            tuple(reversed(calls)),
        )
    result = module.balance_conditionals((3,) * len(values), values, forms, calls, support)
    assert (
        cast(Fraction, result.formation_w1) + cast(Fraction, result.call_w1),
        result.worst_cdf,
        result.edits,
        result.locations,
    ) == oracle(values, forms, calls, support)
    assert Counter(result.locations) == Counter(values)


def test_paired_shape_does_not_materialize_factorial_permutations(monkeypatch):
    def forbidden(values):
        raise AssertionError("factorial permutation materialization")

    monkeypatch.setattr(module, "_permutations", forbidden)
    values = (0, 5, 10, 15, 20, 25) * 2
    result = module.balance_conditionals(
        (1,) * 12,
        values,
        tuple("ABCDEF") * 2,
        (6,) * 6 + (7,) * 6,
        tuple((x, 1) for x in sorted(set(values))),
    )
    assert result.status == "represented"
    assert Counter(result.locations) == Counter(values)
