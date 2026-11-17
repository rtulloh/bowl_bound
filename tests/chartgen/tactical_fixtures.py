"""Synthetic exact physical-dice outcome diagnostics; no historical chart data."""

from collections import Counter
from itertools import product

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
)
from bowl_bound.models import Defense, Play, ResultKind, TeamChart
from bowl_bound.resolution import resolve_cells
from tests.synthetic_teams import yards

OFFENSIVE_ROLLS = tuple(
    OffensiveRoll(*f) for f in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
)
DEFENSIVE_ROLLS = tuple(DefensiveRoll(*f) for f in product(RED_FACES, GREEN_FACES))


def outcomes(
    chart: TeamChart, play: Play, formation: Defense, gain: int
) -> Counter[tuple[str, int]]:
    """Enumerate 216×36 pairs; QT=-6, INT credits no retained offensive yards.

    Interception probability remains separate. This is not expected points or
    turnover utility, and does not simulate the later return/decline decision.
    """
    ordinary = yards(gain)
    records = {r.roll: r.cell for r in chart.defense if r.play is play and r.defense is formation}
    counts: Counter[tuple[str, int]] = Counter()
    for _offensive in OFFENSIVE_ROLLS:
        for defensive in DEFENSIVE_ROLLS:
            result = resolve_cells(ordinary, records[defensive.total])
            if result.kind is ResultKind.QUARTERBACK_TRAPPED:
                outcome = ("sack", -6)
            elif result.kind is ResultKind.INCOMPLETE:
                outcome = ("incomplete", 0)
            elif result.kind is ResultKind.INTERCEPTION:
                outcome = ("interception", 0)
            else:
                assert result.kind is ResultKind.YARDS and result.yards is not None
                outcome = ("yards", result.yards)
            counts[outcome] += 1
    assert sum(counts.values()) == 216 * 36
    return counts


def mean(counts: Counter[tuple[str, int]]) -> float:
    return sum(gain * count for (_, gain), count in counts.items()) / sum(counts.values())
