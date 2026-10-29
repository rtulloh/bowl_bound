"""Immutable scoring awards and dedicated Bowl Bound PAT resolution (Basic VI-7)."""

from dataclasses import dataclass
from enum import Enum

from .dice import DiceSource, OffensiveRoll
from .game_state import Possession
from .models import PatOutcome, TeamChart


class ScoreKind(str, Enum):
    """Scoring values are rules, never presentation-layer arithmetic."""

    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    SAFETY = "safety"
    PAT = "pat"
    TWO_POINT = "two_point"
    CONVERSION_RETURN = "conversion_return"

    @property
    def points(self) -> int:
        return {
            self.TOUCHDOWN: 6,
            self.FIELD_GOAL: 3,
            self.SAFETY: 2,
            self.PAT: 1,
            self.TWO_POINT: 2,
            self.CONVERSION_RETURN: 2,
        }[self]


@dataclass(frozen=True)
class ScoreEvent:
    """One committed award, linked to exactly one committed play report."""

    number: int
    play_number: int
    scorer: Possession
    kind: ScoreKind
    points: int


@dataclass(frozen=True)
class ScoreLedger:
    """Append-only score history; totals are derived from the recorded awards."""

    events: tuple[ScoreEvent, ...] = ()

    @property
    def totals(self) -> tuple[int, int]:
        return (
            sum(e.points for e in self.events if e.scorer is Possession.HOME),
            sum(e.points for e in self.events if e.scorer is Possession.AWAY),
        )

    def award(self, scorer: Possession, kind: ScoreKind, *, play_number: int) -> "ScoreLedger":
        """Return a new ledger, refusing a duplicate/out-of-order play award."""
        if type(scorer) is not Possession or type(kind) is not ScoreKind:
            raise TypeError("a score needs a Possession and ScoreKind")
        if type(play_number) is not int or play_number <= 0:
            raise ValueError("scoring play number must be a positive integer")
        if self.events and play_number <= self.events[-1].play_number:
            raise ValueError("scoring awards must be in strictly increasing play order")
        event = ScoreEvent(len(self.events) + 1, play_number, scorer, kind, kind.points)
        return ScoreLedger((*self.events, event))


@dataclass(frozen=True)
class PatResolution:
    """The actual PAT roll and the dedicated source outcome consulted."""

    roll: OffensiveRoll
    outcome: PatOutcome

    @property
    def good(self) -> bool:
        return self.outcome.good

    @property
    def points(self) -> int:
        return int(self.good)


def resolve_pat(chart: TeamChart, dice: DiceSource) -> PatResolution:
    """Consult dedicated PAT data once; never reinterpret the field-goal column."""
    roll = dice.offensive()
    return PatResolution(
        roll, next(outcome for outcome in chart.pat_outcomes if outcome.roll == roll.total)
    )
