"""Easy-player numeric chart estimates, deliberately not football outcome odds.

No defense, resolver, live session, source text or randomness is consulted.
Excluded chart mass remains visible as missing coverage, never zero-yard plays.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from .coaching import CoachObservation
from .dice import BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES
from .models import OffensiveCell, Play, Priority, ResultKind, TeamChart

_ROLL_WEIGHTS = Counter(
    10 * black + first + second
    for black, first, second in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
)
_PHYSICAL_ROLLS = sum(_ROLL_WEIGHTS.values())


@dataclass(frozen=True)
class NumericEstimate:
    """Conditional numeric rates with explicit evaluated probability coverage."""

    key: str
    target: int
    coverage: Fraction
    target_rate: Fraction | None
    positive_rate: Fraction | None
    average_yards: Fraction | None

    @property
    def limited(self) -> bool:
        return self.coverage < Fraction(1, 2)


def target_yards(down: int, distance: int) -> int:
    """Round the Easy helper target upward using integers, with a one-yard floor."""
    if type(down) is not int or not 1 <= down <= 4:
        raise ValueError("down must be an integer within 1..4")
    if type(distance) is not int or distance < 1:
        raise ValueError("distance must be a positive integer")
    if down == 1:
        return max(1, (distance + 1) // 2)
    if down == 2:
        return max(1, (7 * distance + 9) // 10)
    return distance


def estimate_plays(
    rows: Iterable[OffensiveCell],
    callable_plays: tuple[str, ...],
    *,
    down: int,
    distance: int,
) -> tuple[NumericEstimate, ...]:
    """Rank up to three offered plays using only normalized fixed numeric yards.

    Missing, non-YARDS, priority-annotated and out-of-bounds rows add no evaluated
    mass: only plain numeric facts qualify, matching the Paydirt helper boundary.
    No source text or background color is parsed. Rank supported coverage first,
    then conditional target rate, positive rate, mean yards and coverage. Exact
    ties use ascending play ID, independent of menu or row order. Zero coverage
    produces absent rates rather than a zero average or guaranteed outcome.
    """
    target = target_yards(down, distance)
    valid = {str(play.value) for play in Play}
    if any(key not in valid for key in callable_plays):
        raise ValueError("callable plays must be offered offensive IDs 1..9")
    requested = set(callable_plays)
    mass = {key: [0, 0, 0, 0] for key in requested}
    seen: set[tuple[Play, int]] = set()
    for row in rows:
        identity = (row.play, row.roll)
        if identity in seen:
            raise ValueError("duplicate offensive chart row")
        seen.add(identity)
        key = str(row.play.value)
        cell = row.cell
        if (
            key not in requested
            or cell.kind is not ResultKind.YARDS
            or cell.priority is not Priority.NORMAL
            or cell.out_of_bounds
        ):
            continue
        assert cell.yards is not None  # Guaranteed by the normalized YARDS model.
        weight = _ROLL_WEIGHTS[row.roll]
        counts = mass[key]
        counts[0] += weight
        counts[1] += weight * (cell.yards >= target)
        counts[2] += weight * (cell.yards > 0)
        counts[3] += weight * cell.yards
    estimates = []
    for key in sorted(requested):
        evaluated, target_mass, positive_mass, yards_mass = mass[key]
        estimates.append(
            NumericEstimate(
                key,
                target,
                Fraction(evaluated, _PHYSICAL_ROLLS),
                Fraction(target_mass, evaluated) if evaluated else None,
                Fraction(positive_mass, evaluated) if evaluated else None,
                Fraction(yards_mass, evaluated) if evaluated else None,
            )
        )

    def rank(
        item: NumericEstimate,
    ) -> tuple[bool, bool, Fraction, Fraction, Fraction, Fraction, int]:
        return (
            item.limited,
            not bool(item.coverage),
            -(item.target_rate or Fraction(0)),
            -(item.positive_rate or Fraction(0)),
            -(item.average_yards or Fraction(0)),
            -item.coverage,
            int(item.key),
        )

    return tuple(sorted(estimates, key=rank)[:3])


def advice_lines(
    chart: "TeamChart", observation: "CoachObservation", role: str, labels: dict[str, str]
) -> tuple[str, ...]:
    """Describe public-only Easy assistance, separately from situation/clock tips."""
    lines: list[str] = []
    if role == "offense":
        estimates = estimate_plays(
            chart.offense, observation.offense, down=observation.down, distance=observation.distance
        )
        lines.append(f"Target: {target_yards(observation.down, observation.distance)} yards")
        lines.append(
            "Numeric offensive cells only; conditional rates, not full-engine conversion odds."
        )
        for estimate in estimates:

            def percent(value: Fraction | None) -> str:
                return "unavailable" if value is None else f"{float(value):.0%}"

            average = (
                "unavailable"
                if estimate.average_yards is None
                else f"{float(estimate.average_yards):+.1f} yards"
            )
            limited = " — limited (<50% coverage)" if estimate.limited else ""
            lines.append(
                f"  {estimate.key}/{labels[estimate.key]}: target {percent(estimate.target_rate)}, "
                f"positive {percent(estimate.positive_rate)}, average {average}, "
                f"coverage {percent(estimate.coverage)}{limited}"
            )
    elif role == "defense":
        lines.append("Situational defense; not learned CPU tendencies.")
        lines.append(
            "  Short yardage favors tighter coverage."
            if observation.distance <= 3
            else "  Longer passing downs call for considering pass coverage; mix legal formations."
        )
    else:
        return ()
    if role == "defense":
        lines.append(
            "Situation: Mix formations for the down and distance; no concealed call is known."
        )
    else:
        lines.append(
            "Situation: Later downs need the full distance; weigh the offered kick options."
            if observation.down >= 3
            else "Situation: Build manageable later downs; "
            "the target is a helper heuristic, not a rule."
        )
    if observation.overtime:
        lines.append(
            "Clock: Overtime uses the engine's possession rules, not the regulation clock."
        )
    elif observation.quarter in {2, 4} and observation.remaining <= 120:
        lines.append(
            "Clock: Time is short; review legal clock controls "
            "and your own timeout before snapping."
        )
    else:
        lines.append(
            "Clock: Review the engine clock and legal controls; advice does not predict runoff."
        )
    return tuple(lines)
