"""Finite payload-only balancing under an authored exchangeable-depth prior."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from itertools import product
from math import lcm

from .coupled_depths import DepthSupport, Histogram, _support


@dataclass(frozen=True)
class ConditionalBalance:
    status: str
    locations: tuple[int, ...] = ()
    formation_w1: Fraction | None = None
    call_w1: Fraction | None = None
    worst_cdf: Fraction | None = None
    edits: int = 0
    assignments_evaluated: int = 0
    active_formations: tuple[str, ...] = ()
    active_calls: tuple[int, ...] = ()


def _permutations(values: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Yield each multiset permutation once, including constant support."""
    counts = Counter(values)
    keys = tuple(sorted(counts))
    prefix: list[int] = []

    def visit() -> Iterator[tuple[int, ...]]:
        if len(prefix) == len(values):
            yield tuple(prefix)
            return
        for x in keys:
            if counts[x]:
                counts[x] -= 1
                prefix.append(x)
                yield from visit()
                prefix.pop()
                counts[x] += 1

    yield from visit()


def _errors(
    weights: tuple[int, ...], values: tuple[int, ...], indices: tuple[int, ...], support: Histogram
) -> tuple[Fraction, Fraction]:
    total = sum(weights[i] for i in indices)
    source_total = sum((w for _, w in support), Fraction())
    actual = expected = distance = worst = Fraction()
    for j, (x, weight) in enumerate(support):
        actual += Fraction(sum(weights[i] for i in indices if values[i] == x), total)
        expected += weight / source_total
        error = abs(actual - expected)
        worst = max(worst, error)
        if j + 1 < len(support):
            distance += error * (support[j + 1][0] - x)
    return distance, worst


def _paired_equalweight(
    locations: tuple[int, ...],
    formations: tuple[str, ...],
    calls: tuple[int, ...],
    support: Histogram,
) -> ConditionalBalance:
    """Solve the two-slot-per-formation shape with an exact admissible bound.

    Common-denominator integer costs are identical to the Fraction objective.
    Remaining minimum pair cost ignores call constraints, so it is a lower
    bound. Pruning uses only a strictly worse first cost: worst-CDF, edit and
    addressed canonical ties remain fully eligible.
    """
    forms, call_labels = tuple(sorted(set(formations))), tuple(sorted(set(calls)))
    n = len(forms)
    atoms = tuple(x for x, _ in support)
    source_total = sum((w for _, w in support), Fraction())
    cumulative = Fraction()
    cdf = []
    for _, weight in support:
        cumulative += weight / source_total
        cdf.append(cumulative)
    scale = lcm(2, n, *(x.denominator for x in cdf))
    expected = tuple(int(x * scale) for x in cdf)
    gaps = tuple(atoms[i + 1] - x if i + 1 < len(atoms) else 0 for i, x in enumerate(atoms))

    @cache
    def cost(values: tuple[int, ...]) -> tuple[int, int]:
        actual = distance = worst = 0
        for x, target, gap in zip(atoms, expected, gaps, strict=True):
            actual += values.count(x)
            error = abs(actual * (scale // len(values)) - target)
            distance += error * gap
            worst = max(worst, error)
        return distance, worst

    inventory = Counter(locations)
    initial = tuple(inventory[x] for x in atoms)

    @cache
    def remaining_pair_cost(counts: tuple[int, ...]) -> int:
        if not any(counts):
            return 0
        left = next(i for i, count in enumerate(counts) if count)
        rest = list(counts)
        rest[left] -= 1
        best = None
        for right, count in enumerate(rest):
            if count:
                rest[right] -= 1
                candidate = cost(tuple(sorted((atoms[left], atoms[right]))))[
                    0
                ] + remaining_pair_cost(tuple(rest))
                best = candidate if best is None else min(best, candidate)
                rest[right] += 1
        assert best is not None
        return best

    coordinates = tuple(
        tuple(
            next(
                i
                for i, (f, c) in enumerate(zip(formations, calls, strict=True))
                if f == form and c == call
            )
            for call in call_labels
        )
        for form in forms
    )

    def score(values: tuple[int, ...]) -> tuple[tuple[int, int, int, tuple[int, ...]], int, int]:
        form_costs = tuple(cost(tuple(sorted(values[i] for i in pair))) for pair in coordinates)
        call_costs = tuple(
            cost(tuple(sorted(x for x, c in zip(values, calls, strict=True) if c == call)))
            for call in call_labels
        )
        form_sum, call_sum = sum(x[0] for x in form_costs), sum(x[0] for x in call_costs)
        return (
            (
                form_sum + call_sum,
                max(x[1] for x in (*form_costs, *call_costs)),
                sum(a != b for a, b in zip(values, locations, strict=True)),
                values,
            ),
            form_sum,
            call_sum,
        )

    best, best_form, best_call = score(locations)
    counts = list(initial)
    values = list(locations)
    call_cumulative = [[0] * len(atoms) for _ in call_labels]
    evaluated = 1

    def call_lower_bound(missing: int) -> int:
        bound = below = 0
        for j, (target, gap) in enumerate(zip(expected, gaps, strict=True)):
            below += counts[j]
            minimum = max(0, missing - (2 * missing - below))
            maximum = min(missing, below)
            for sample in call_cumulative:
                low, high = (
                    (sample[j] + minimum) * (scale // n),
                    (sample[j] + maximum) * (scale // n),
                )
                bound += max(low - target, target - high, 0) * gap
        return bound

    def visit(index: int, form_sum: int) -> None:
        nonlocal best, best_form, best_call, evaluated
        if form_sum + remaining_pair_cost(tuple(counts)) + call_lower_bound(n - index) > best[0]:
            return
        if index == n:
            candidate, form, call = score(tuple(values))
            evaluated += 1
            if candidate < best:
                best, best_form, best_call = candidate, form, call
            return
        first, second = coordinates[index]
        for left, count in enumerate(counts):
            if not count:
                continue
            counts[left] -= 1
            values[first] = atoms[left]
            for j in range(left, len(atoms)):
                call_cumulative[0][j] += 1
            for right, remaining in enumerate(counts):
                if not remaining:
                    continue
                counts[right] -= 1
                values[second] = atoms[right]
                for j in range(right, len(atoms)):
                    call_cumulative[1][j] += 1
                visit(index + 1, form_sum + cost(tuple(sorted((atoms[left], atoms[right]))))[0])
                for j in range(right, len(atoms)):
                    call_cumulative[1][j] -= 1
                counts[right] += 1
            for j in range(left, len(atoms)):
                call_cumulative[0][j] -= 1
            counts[left] += 1

    visit(0, 0)
    return ConditionalBalance(
        "represented",
        best[3],
        Fraction(best_form, scale),
        Fraction(best_call, scale),
        Fraction(best[1], scale),
        best[2],
        evaluated,
        forms,
        call_labels,
    )


def balance_conditionals(
    weights: tuple[int, ...],
    locations: tuple[int, ...],
    formations: tuple[str, ...],
    calls: tuple[int, ...],
    support: DepthSupport,
) -> ConditionalBalance:
    """Balance active formation and call CDFs without changing weight/atom counts.

    Every active formation and call contributes one conditional W1 term,
    regardless of its occurrence mass. Zero-population terms are undefined and
    excluded. The objective then minimizes worst conditional CDF error, edits
    versus the supplied frozen witness, and the addressed value tuple. The
    caller pins coordinate order; this does not establish historical exposure.
    """
    if (
        any(type(v) is not tuple for v in (weights, locations, formations, calls))
        or len({len(v) for v in (weights, locations, formations, calls)}) != 1
        or any(type(w) is not int or w <= 0 for w in weights)
        or any(type(x) is not int for x in locations)
        or any(type(f) is not str or not f for f in formations)
        or any(type(c) is not int or not 6 <= c <= 9 for c in calls)
        or not (set(calls) <= {6, 7} or set(calls) <= {8, 9})
    ):
        raise ValueError("conditional balance requires complete typed slots of one passing pair")
    if not weights:
        return ConditionalBalance("dormant")
    points = _support(support)
    if not set(locations) <= {x for x, _ in points}:
        raise ValueError("conditional balance cannot add unsupported source locations")
    active_forms, active_calls = tuple(sorted(set(formations))), tuple(sorted(set(calls)))
    if (
        len(set(weights)) == 1
        and len(active_forms) >= 2
        and len(active_calls) == 2
        and Counter(zip(formations, calls, strict=True))
        == Counter((f, c) for f in active_forms for c in active_calls)
    ):
        return _paired_equalweight(locations, formations, calls, points)
    form_indices = tuple(
        tuple(i for i, f in enumerate(formations) if f == label) for label in active_forms
    )
    call_indices = tuple(
        tuple(i for i, c in enumerate(calls) if c == label) for label in active_calls
    )
    classes = tuple(sorted(set(weights)))
    groups = tuple(tuple(i for i, w in enumerate(weights) if w == value) for value in classes)
    choices = tuple(
        tuple(_permutations(tuple(locations[i] for i in indices))) for indices in groups
    )
    best: tuple[Fraction, Fraction, int, tuple[int, ...]] | None = None
    best_parts = (Fraction(), Fraction())
    count = 0
    for assignments in product(*choices):
        candidate = list(locations)
        for indices, values in zip(groups, assignments, strict=True):
            for i, x in zip(indices, values, strict=True):
                candidate[i] = x
        values = tuple(candidate)
        form_errors = tuple(_errors(weights, values, indices, points) for indices in form_indices)
        call_errors = tuple(_errors(weights, values, indices, points) for indices in call_indices)
        form_w1 = sum((e[0] for e in form_errors), Fraction())
        call_w1 = sum((e[0] for e in call_errors), Fraction())
        worst = max(e[1] for e in (*form_errors, *call_errors))
        edits = sum(a != b for a, b in zip(values, locations, strict=True))
        score = form_w1 + call_w1, worst, edits, values
        count += 1
        if best is None or score < best:
            best, best_parts = score, (form_w1, call_w1)
    assert best is not None
    return ConditionalBalance(
        "represented", best[3], *best_parts, best[1], best[2], count, active_forms, active_calls
    )
