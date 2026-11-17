"""Exact known-source CDF transport for an authored private experiment.

Support weights are conditional evidence mass, never independent sample counts.
Unknown locations and incidence authority belong to the caller's frozen inputs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

DepthSupport = tuple[tuple[int, int | Fraction], ...]
Histogram = tuple[tuple[int, Fraction], ...]


def _support(support: DepthSupport) -> Histogram:
    if type(support) is not tuple or not support:
        raise ValueError("known depth support must be a nonempty immutable distribution")
    merged: dict[int, Fraction] = {}
    for point in support:
        if (
            type(point) is not tuple
            or len(point) != 2
            or type(point[0]) is not int
            or type(point[1]) not in {int, Fraction}
            or point[1] <= 0
        ):
            raise ValueError("depth atoms require integer locations and positive exact weights")
        merged[point[0]] = merged.get(point[0], Fraction()) + point[1]
    return tuple(sorted(merged.items()))


def split_depths(support: DepthSupport, lower_share: Fraction) -> tuple[Histogram, Histogram]:
    """Split an empirical CDF, dividing a boundary atom without selecting records."""
    if type(lower_share) is not Fraction or not 0 <= lower_share <= 1:
        raise ValueError("CDF split requires an exact share within 0..1")
    points = _support(support)
    remaining = sum((w for _, w in points), Fraction()) * lower_share
    lower, upper = [], []
    for x, weight in points:
        selected = min(remaining, weight)
        if selected:
            lower.append((x, selected))
        if weight > selected:
            upper.append((x, weight - selected))
        remaining -= selected
    return tuple(lower), tuple(upper)


@dataclass(frozen=True)
class DepthAllocation:
    """A constrained finite encoding; undefined errors stay explicit."""

    status: str
    locations: tuple[int, ...] = ()
    histogram: tuple[tuple[int, int], ...] = ()
    wasserstein: Fraction | None = None
    cdf_error: Fraction | None = None


def quantize_depths(weights: tuple[int, ...], support: DepthSupport) -> DepthAllocation:
    """Minimize exact W1 then CDF error over whole slots with retained tails.

    A count-state DP enumerates all distributions of indivisible slot weight
    classes onto the original atoms. The canonical witness is deterministic;
    no optimality for a subsequent coordinate-balancing stage is implied.
    """
    if type(weights) is not tuple or any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError("depth slots require immutable positive integer physical weights")
    if not weights:
        return DepthAllocation("dormant")
    points = _support(support)
    if len(weights) == 1 and len(points) > 1:
        return DepthAllocation("infeasible-tails")
    classes = tuple(sorted(set(weights)))
    limits = tuple(weights.count(w) for w in classes)
    zero = (0,) * len(classes)
    total = sum(weights)
    source_total = sum((w for _, w in points), Fraction())
    # Used counts -> (W1 so far, largest CDF deviation, per-atom count witness).
    states: dict[tuple[int, ...], tuple[Fraction, Fraction, tuple[tuple[int, ...], ...]]] = {
        zero: (Fraction(), Fraction(), ())
    }
    source_cdf = Fraction()
    for index, (x, source_weight) in enumerate(points):
        source_cdf += source_weight / source_total
        next_states = {}
        for used, (distance, worst, witness) in states.items():
            remaining = tuple(limit - count for limit, count in zip(limits, used, strict=True))
            choices = (
                (remaining,)
                if index == len(points) - 1
                else product(*(range(n + 1) for n in remaining))
            )
            for selected in choices:
                if index in {0, len(points) - 1} and not any(selected):
                    continue
                after = tuple(a + b for a, b in zip(used, selected, strict=True))
                mass = sum(w * n for w, n in zip(classes, after, strict=True))
                error = abs(Fraction(mass, total) - source_cdf)
                interval = points[index + 1][0] - x if index + 1 < len(points) else 0
                candidate = (
                    distance + error * interval,
                    max(worst, error),
                    witness + (tuple(selected),),
                )
                if after not in next_states or candidate < next_states[after]:
                    next_states[after] = candidate
        states = next_states
    if limits not in states:
        return DepthAllocation("infeasible-tails")
    distance, worst, witness = states[limits]
    by_weight = {w: [] for w in classes}
    for (x, _), counts in zip(points, witness, strict=True):
        for w, count in zip(classes, counts, strict=True):
            by_weight[w].extend([x] * count)
    # Input coordinates retain their order; equal-weight slots are exchangeable
    # at this stage. The producer separately balances calls within each group.
    offsets = dict.fromkeys(classes, 0)
    values = []
    histogram: Counter[int] = Counter()
    for w in weights:
        x = by_weight[w][offsets[w]]
        offsets[w] += 1
        values.append(x)
        histogram[x] += w
    return DepthAllocation(
        "represented", tuple(values), tuple(sorted(histogram.items())), distance, worst
    )


def balance_pair(
    weights: tuple[int, ...],
    locations: tuple[int, ...],
    labels: tuple[int, ...],
    support: DepthSupport,
) -> tuple[tuple[int, ...], Fraction | None]:
    """Balance two exchangeable calls, preserving each selected weight/atom count.

    This conditional DP follows the aggregate W1/CDF stage. It minimizes the sum
    of the two call-conditional W1 errors, then maximum CDF error. No additional
    within-pair depth order or historical call exposure is invented.
    """
    if len(weights) != len(locations) or len(weights) != len(labels):
        raise ValueError("pair balance requires equal addressed slot inventories")
    if (
        any(type(w) is not int or w <= 0 for w in weights)
        or any(type(x) is not int for x in locations)
        or any(type(label) is not int or label not in (0, 1) for label in labels)
    ):
        raise ValueError("pair balance requires exact integer slots/locations and labels0/1")
    if not weights:
        return (), None
    points = _support(support)
    if not set(locations) <= {x for x, _ in points}:
        raise ValueError("pair balance cannot introduce unsupported locations")
    totals = tuple(
        sum(w for w, label in zip(weights, labels, strict=True) if label == k) for k in (0, 1)
    )
    if not all(totals):
        return locations, None
    classes = tuple(sorted(set(weights)))
    limits = tuple(
        sum(w == c and label == 0 for w, label in zip(weights, labels, strict=True))
        for c in classes
    )
    states = {(0,) * len(classes): (Fraction(), Fraction(), ())}
    source_cdf = Fraction()
    selected_cumulative = 0
    source_total = sum((n for _, n in points), Fraction())
    for i, (x, n) in enumerate(points):
        source_cdf += n / source_total
        counts = tuple(
            sum(w == c and v == x for w, v in zip(weights, locations, strict=True)) for c in classes
        )
        selected_cumulative += sum(c * count for c, count in zip(classes, counts, strict=True))
        nxt = {}
        for used, (distance, worst, witness) in states.items():
            for chosen in product(
                *(
                    range(min(count, limit - already) + 1)
                    for count, limit, already in zip(counts, limits, used, strict=True)
                )
            ):
                after = tuple(a + b for a, b in zip(used, chosen, strict=True))
                first_mass = sum(w * count for w, count in zip(classes, after, strict=True))
                errors = (
                    abs(Fraction(first_mass, totals[0]) - source_cdf),
                    abs(Fraction(selected_cumulative - first_mass, totals[1]) - source_cdf),
                )
                interval = points[i + 1][0] - x if i + 1 < len(points) else 0
                candidate = (
                    distance + sum(errors) * interval,
                    max(worst, *errors),
                    witness + (chosen,),
                )
                if after not in nxt or candidate < nxt[after]:
                    nxt[after] = candidate
        states = nxt
    if limits not in states:
        raise ValueError("pair balance lost a feasible original weight-class assignment")
    distance, _, witness = states[limits]
    queues = {(label, w): [] for label in (0, 1) for w in classes}
    for (x, _), first in zip(points, witness, strict=True):
        for w, count in zip(classes, first, strict=True):
            available = sum(
                weight == w and value == x for weight, value in zip(weights, locations, strict=True)
            )
            queues[0, w].extend([x] * count)
            queues[1, w].extend([x] * (available - count))
    offsets = dict.fromkeys(queues, 0)
    result = []
    for w, label in zip(weights, labels, strict=True):
        key = label, w
        result.append(queues[key][offsets[key]])
        offsets[key] += 1
    return tuple(result), distance
