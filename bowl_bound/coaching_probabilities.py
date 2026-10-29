"""Bounded exact chart-resolution probabilities for coaching, not game outcomes.

All chart semantics stay in resolution.resolve_play. Pending penalties/turnovers
remain pending; this module never predicts their completed football outcomes.
Analysis accepts no live game, dice source, hidden call or random seed.
"""

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import cast

from .dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
)
from .models import Defense, PenaltyData, Play, ResultKind, TeamChart
from .resolution import Operation, PlayResolution, Source, resolve_play

Roll = OffensiveRoll | DefensiveRoll


@dataclass(frozen=True)
class ChartOutcome:
    """Resolver facts only; pending INT/F is not a committed possession change."""

    called_play: Play
    resolved_play: Play
    kind: ResultKind | None
    yards: int | None
    pending: bool
    out_of_bounds: bool
    operation: Operation
    source: Source
    penalty: PenaltyData | None
    defensive_end_zone_depth: int | None


@dataclass(frozen=True)
class OutcomeProbability:
    outcome: ChartOutcome
    probability: Fraction


@dataclass(frozen=True)
class ChartDistribution:
    """Partial or complete rational distribution with no lost probability mass.

    Complete means chart analysis finished successfully, not that pending football
    procedures were executed. Failed mass records resolver-rejected branches;
    unexplored mass records work left after the deterministic evaluation budget.
    """

    outcomes: tuple[OutcomeProbability, ...]
    unexplored_probability: Fraction
    failed_probability: Fraction
    evaluations: int

    @property
    def complete(self) -> bool:
        return self.unexplored_probability == 0 and self.failed_probability == 0

    @property
    def pending_probability(self) -> Fraction:
        return sum(
            (entry.probability for entry in self.outcomes if entry.outcome.pending), Fraction()
        )


class _NeedRoll(Exception):
    def __init__(self, offensive: bool) -> None:
        self.offensive = offensive


class _PrefixDice:
    """Replay a hypothetical prefix and request branching at the next fresh roll."""

    def __init__(self, prefix: tuple[Roll, ...]) -> None:
        self._prefix = prefix
        self._position = 0

    def _next(self, offensive: bool) -> Roll:
        if self._position == len(self._prefix):
            raise _NeedRoll(offensive)
        roll = self._prefix[self._position]
        self._position += 1
        expected = OffensiveRoll if offensive else DefensiveRoll
        if not isinstance(roll, expected):
            raise TypeError("analysis dice prefix has an inconsistent roll type")
        return roll

    def offensive(self) -> OffensiveRoll:
        return cast(OffensiveRoll, self._next(True))

    def defensive(self) -> DefensiveRoll:
        return cast(DefensiveRoll, self._next(False))


def _roll_groups(offensive: bool) -> tuple[tuple[Roll, Fraction], ...]:
    """Weight representatives by physical multiplicity, not uniformly by total.

    resolve_play observes offensive total/direct_sum and defensive total only.
    Group by both offensive values explicitly; do not reuse this aggregation for
    procedures inspecting individual die faces (for example hurried bad snaps).
    """
    physical: list[Roll] = (
        [OffensiveRoll(*faces) for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)]
        if offensive
        else [DefensiveRoll(*faces) for faces in product(RED_FACES, GREEN_FACES)]
    )
    representatives: dict[tuple[int, ...], Roll] = {}
    counts: Counter[tuple[int, ...]] = Counter()
    for roll in physical:
        key = (roll.total, roll.direct_sum) if isinstance(roll, OffensiveRoll) else (roll.total,)
        representatives.setdefault(key, roll)
        counts[key] += 1
    return tuple(
        (representatives[key], Fraction(count, len(physical))) for key, count in counts.items()
    )


_OFFENSIVE_GROUPS = _roll_groups(True)
_DEFENSIVE_GROUPS = _roll_groups(False)


def _outcome(resolution: PlayResolution) -> ChartOutcome:
    result = resolution.result
    return ChartOutcome(
        resolution.called_play,
        resolution.resolved_play,
        result.kind,
        result.yards,
        result.pending,
        result.out_of_bounds,
        result.operation,
        result.source,
        result.penalty,
        result.defensive_end_zone_depth,
    )


def analyze_play(
    offense: TeamChart,
    defense: TeamChart,
    play: Play,
    formation: Defense,
    *,
    max_evaluations: int = 10_000,
) -> ChartDistribution:
    """Enumerate the resolver tree with exact independent dice probabilities.

    Each evaluation restarts the pure resolver against a hypothetical dice
    prefix. A new dice request expands that prefix with correctly weighted
    physical possibilities. The budget includes partial-prefix evaluations, so
    branching charts cannot trigger unbounded work. No branch is renormalized or
    silently treated as a zero-yard result when work or engine limits are hit.
    Resolver ValueError branches retain their mass without exposing chart text.
    Invalid API argument types are rejected before any analysis.
    """
    if not isinstance(offense, TeamChart) or not isinstance(defense, TeamChart):
        raise TypeError("chart analysis requires two TeamChart instances")
    if type(play) is not Play or type(formation) is not Defense:
        raise TypeError("chart analysis requires Play and Defense members")
    if type(max_evaluations) is not int or max_evaluations <= 0:
        raise ValueError("analysis budget must be a positive integer")
    frontier: list[tuple[tuple[Roll, ...], Fraction]] = [((), Fraction(1))]
    outcomes: Counter[ChartOutcome] = Counter()
    failed = Fraction()
    evaluations = 0
    while frontier and evaluations < max_evaluations:
        prefix, probability = frontier.pop()
        evaluations += 1
        try:
            resolution = resolve_play(offense, defense, play, formation, _PrefixDice(prefix))
        except _NeedRoll as request:
            groups = _OFFENSIVE_GROUPS if request.offensive else _DEFENSIVE_GROUPS
            frontier.extend(((*prefix, roll), probability * weight) for roll, weight in groups)
        except ValueError:
            failed += probability
        else:
            outcomes[_outcome(resolution)] += probability
    return ChartDistribution(
        tuple(
            OutcomeProbability(outcome, probability) for outcome, probability in outcomes.items()
        ),
        sum((probability for _, probability in frontier), Fraction()),
        failed,
        evaluations,
    )
