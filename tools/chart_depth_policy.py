"""Call-specific catch-depth modeling for generated charts (development only).

Unknown designed calls are diagnostic evidence, never conditional observations.
Numerical priors are explicit authored assumptions, not historical estimates.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product
from typing import Any, Protocol, TypeVar

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
)
from bowl_bound.models import DefensiveCell, OffensiveCell, ResultKind, TeamChart

# Sprint Out and Bootleg have the same prior: movement alone establishes no depth.
PRIORS = {
    6: ((-3, 1), (0, 2), (3, 1)),
    7: ((0, 1), (5, 1), (10, 2), (15, 1), (20, 1)),
    8: ((0, 1), (5, 1), (10, 2), (15, 1), (20, 1)),
    9: ((0, 1), (10, 1), (20, 2), (30, 1), (45, 1)),
}
CONTRACT = {
    "origin": "authored-bb-call-depth-v1",
    "priors": PRIORS,
    "prior_equivalent_observations": 4,
    "observed": "same-side-team;explicit-designed-call-marker;known-catch-depth",
    "unknown": "unidentified/missing-location counts retained;never conditional support",
    "allocation": "exact-W1-then-CDF;whole-fixed-INT-slots;canonical;no-forced-tail",
    "preserve": "every-slot-kind-priority-flag;all-nondepth-facts;incidence-budgets",
    "authority": "authored-experimental;not-historical-conditional-fit",
}
POLICY_SHA256 = hashlib.sha256(
    json.dumps(CONTRACT, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


class DepthEvent(Protocol):
    @property
    def kind(self) -> str: ...

    @property
    def called_family(self) -> int | None: ...

    @property
    def family_confidence(self) -> str: ...

    @property
    def interception_yards(self) -> int | None: ...

    @property
    def air_yards(self) -> int | None: ...

    @property
    def no_play(self) -> bool: ...

    @property
    def family_evidence(self) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class DepthDistribution:
    """Normalized rational modeled support and separately labeled evidence."""

    support: tuple[tuple[int, Fraction], ...]
    evidence: dict[str, Any]


def execution_identity(prior_strength: int = 4) -> dict[str, Any]:
    """Bind every executed numerical assumption, including prior strength."""
    if type(prior_strength) is not int or prior_strength <= 0:
        raise ValueError("prior strength must be a positive integer")
    contract = deepcopy(CONTRACT)
    contract["prior_equivalent_observations"] = prior_strength
    digest = hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "origin": contract["origin"],
        "sha256": digest,
        "authored_experimental": True,
        "contract": contract,
    }


def location_distribution(
    events: Sequence[DepthEvent], play: int, *, prior_strength: int = 4
) -> DepthDistribution:
    """Blend only explicit conditional observations with a declared authored prior."""
    if type(play) is not int or play not in PRIORS:
        raise ValueError("catch-depth policy requires a passing call 6 through 9")
    if type(prior_strength) is not int or prior_strength <= 0:
        raise ValueError("prior strength must be a positive integer")
    live = [event for event in events if event.kind == "interception" and not event.no_play]
    known: list[int] = []
    unknown = 0
    unmatched = 0
    conditional_unknown = 0
    for event in live:
        depth = event.interception_yards
        if depth is None:
            depth = event.air_yards
        marker = {6: "text:screen", 7: "text:sprint-out", 8: "text:bootleg", 9: "text:drop-back"}[
            play
        ]
        conditional = (
            event.called_family == play
            and event.family_confidence == "narrative"
            and marker in event.family_evidence
        )
        if depth is None:
            unknown += 1
            conditional_unknown += conditional
        elif type(depth) is not int:
            raise ValueError("known catch depth must be an integer")
        elif conditional:
            known.append(depth)
        else:
            unmatched += 1
    weights = Counter(
        {x: Fraction(w * prior_strength, sum(v for _, v in PRIORS[play])) for x, w in PRIORS[play]}
    )
    weights.update(known)
    total = sum(weights.values())
    support = tuple((x, Fraction(w, total)) for x, w in sorted(weights.items()))
    return DepthDistribution(
        support,
        {
            "method": "observed-conditional-plus-authored-prior" if known else "authored-prior",
            "observed_conditional_samples": len(known),
            "observed_conditional_histogram": dict(sorted(Counter(known).items())),
            "unknown_location_samples": unknown,
            "conditional_unknown_location_samples": conditional_unknown,
            "known_unmatched_call_samples": unmatched,
            "prior_equivalent_observations": prior_strength,
            "source_conditional_truth": "UNKNOWN" if not known else "SPARSE-observed-support",
            "policy_sha256": execution_identity(prior_strength)["sha256"],
            "modeled_support": tuple((x, str(w)) for x, w in support),
        },
    )


def encode_depths(
    weights: tuple[int, ...], support: tuple[tuple[int, Fraction], ...]
) -> tuple[tuple[int, ...], dict[str, Any]]:
    """Minimize exact W1 and worst CDF error over indivisible physical slots.

    Tails are not fabricated into a one-slot chart. Omitted support and finite
    encoding residuals remain explicit rather than claiming exact reproduction.
    """
    if any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError("depth slots require positive physical integer weights")
    if not weights:
        return (), {
            "status": "dormant",
            "wasserstein": None,
            "cdf_error": None,
            "omitted_support": tuple(x for x, _ in support),
        }
    if not support or any(type(x) is not int or w <= 0 for x, w in support):
        raise ValueError("depth support requires integer atoms and positive mass")
    if tuple(sorted(dict(support))) != tuple(x for x, _ in support):
        raise ValueError("depth support must have sorted unique atoms")
    classes = tuple(sorted(set(weights)))
    limits = tuple(weights.count(w) for w in classes)
    total = sum(weights)
    source_total = sum(w for _, w in support)

    def solve(
        cdf_limit: Fraction | None,
    ) -> tuple[Fraction, Fraction, tuple[tuple[int, ...], ...]]:
        states = {(0,) * len(classes): (Fraction(), Fraction(), ())}
        source_cdf = Fraction()
        for index, (x, mass) in enumerate(support):
            source_cdf += mass / source_total
            next_states = {}
            for used, (distance, worst, witness) in states.items():
                remaining = tuple(n - u for n, u in zip(limits, used, strict=True))
                choices = (
                    (remaining,)
                    if index == len(support) - 1
                    else product(*(range(n + 1) for n in remaining))
                )
                for chosen in choices:
                    after = tuple(u + c for u, c in zip(used, chosen, strict=True))
                    cdf = Fraction(sum(w * n for w, n in zip(classes, after, strict=True)), total)
                    error = abs(cdf - source_cdf)
                    if cdf_limit is not None and error > cdf_limit:
                        continue
                    interval = support[index + 1][0] - x if index + 1 < len(support) else 0
                    candidate = (
                        distance + error * interval,
                        max(worst, error),
                        witness + (tuple(chosen),),
                    )
                    previous = next_states.get(after)
                    if previous is None or (
                        candidate < previous
                        if cdf_limit is None
                        else (candidate[0], candidate[2]) < (previous[0], previous[2])
                    ):
                        next_states[after] = candidate
            states = next_states
        return states[limits]

    # The first pass finds optimal W1 and worst CDF. With that global CDF
    # bound fixed, a second pass minimizes W1 and the complete count witness.
    # A prefix's smaller worst error cannot discard a smaller witness which
    # would tie after a later error equalizes the final maxima.
    optimum_distance, optimum_worst, _ = solve(None)
    distance, worst, witness = solve(optimum_worst)
    if (distance, worst) != (optimum_distance, optimum_worst):
        raise RuntimeError("canonical depth allocation changed the optimal numerical objective")
    by_weight = {w: [] for w in classes}
    for (x, _), counts in zip(support, witness, strict=True):
        for w, count in zip(classes, counts, strict=True):
            by_weight[w].extend([x] * count)
    offsets = dict.fromkeys(classes, 0)
    values = []
    for weight in weights:
        values.append(by_weight[weight][offsets[weight]])
        offsets[weight] += 1
    histogram = Counter()
    for x, w in zip(values, weights, strict=True):
        histogram[x] += w
    return tuple(values), {
        "status": "represented",
        "wasserstein": str(distance),
        "cdf_error": str(worst),
        "represented_histogram": tuple(sorted(histogram.items())),
        "omitted_support": tuple(x for x, _ in support if x not in histogram),
    }


_Row = TypeVar("_Row", OffensiveCell, DefensiveCell)


def apply_depth_policy(
    chart: TeamChart,
    offense_events: Sequence[DepthEvent],
    defense_events: Sequence[DepthEvent],
    *,
    prior_strength: int = 4,
) -> tuple[TeamChart, dict[str, Any]]:
    """Replace fixed INT catch depths after allocation without moving any slots."""
    identity = execution_identity(prior_strength)
    reports: dict[str, Any] = {}
    offense_weights = Counter(
        10 * b + w1 + w2 for b, w1, w2 in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    defense_weights = Counter(r + g for r, g in product(RED_FACES, GREEN_FACES))

    def encode_rows(
        original: tuple[_Row, ...],
        side: str,
        events: Sequence[DepthEvent],
        physical: Mapping[int, int],
    ) -> tuple[_Row, ...]:
        rows = list(original)
        reports[side] = {}
        for play in PRIORS:
            distribution = location_distribution(events, play, prior_strength=prior_strength)
            groups = ("offense",) if side == "offense" else tuple("ABCDEF")
            report = {"evidence": distribution.evidence, "groups": {}}
            for group in groups:
                indexes = [
                    i
                    for i, row in enumerate(rows)
                    if row.play.value == play
                    and row.cell.kind is ResultKind.INTERCEPTION
                    and (
                        side == "offense"
                        or isinstance(row, DefensiveCell)
                        and row.defense.value == group
                    )
                ]
                if any(rows[i].cell.variable is not None for i in indexes):
                    raise ValueError("variable INT catch-depth encoding requires explicit policy")
                values, encoding = encode_depths(
                    tuple(physical[rows[i].roll] for i in indexes), distribution.support
                )
                report["groups"][group] = encoding
                for i, value in zip(indexes, values, strict=True):
                    cell = rows[i].cell
                    provenance = (
                        replace(cell.provenance, original_text=f"INT {value}")
                        if cell.provenance is not None
                        else None
                    )
                    rows[i] = replace(
                        rows[i], cell=replace(cell, yards=value, provenance=provenance)
                    )
            reports[side][str(play)] = report
        return tuple(rows)

    offense = encode_rows(chart.offense, "offense", offense_events, offense_weights)
    defense = encode_rows(chart.defense, "defense", defense_events, defense_weights)
    return replace(chart, offense=offense, defense=defense), {
        "model_identity": identity,
        "prior_strength": prior_strength,
        "columns": reports,
        "source_fit": "UNVERIFIED;unknown-calls-not-observed-conditional-support",
    }
