"""Standard Bowl Bound timing facts and immutable regulation clock (Timing Chart p.34)."""

from dataclasses import dataclass, replace

from .game_state import Possession

QUARTER_SECONDS = 900


@dataclass(frozen=True)
class TimingFacts:
    """Semantic facts about one completed play, including all of its returns."""

    first_down: bool = False
    change_of_possession: bool = False
    penalty: bool = False
    incomplete: bool = False
    scoring: bool = False
    touchback: bool = False
    out_of_bounds: bool = False
    unreturned_kickoff: bool = False
    conversion: bool = False
    no_elapsed_time: bool = False


@dataclass(frozen=True)
class Clock:
    """One quarter clock; expiration is resolved separately from play completion."""

    quarter: int = 1
    remaining: int = QUARTER_SECONDS
    timeouts: tuple[int, int] = (3, 3)

    def __post_init__(self) -> None:
        if type(self.quarter) is not int or not 1 <= self.quarter <= 4:
            raise ValueError("quarter must be 1..4")
        if type(self.remaining) is not int or not 0 <= self.remaining <= QUARTER_SECONDS:
            raise ValueError("quarter seconds must be 0..900")
        if (
            not isinstance(self.timeouts, tuple)
            or len(self.timeouts) != 2
            or any(type(n) is not int or not 0 <= n <= 3 for n in self.timeouts)
        ):
            raise ValueError("each team must have 0..3 timeouts")

    @property
    def label(self) -> str:
        return f"{self.remaining // 60}:{self.remaining % 60:02d}"

    @property
    def quarter_label(self) -> str:
        return f"Q{self.quarter}"

    def elapse(self, seconds: int) -> "Clock":
        if type(seconds) is not int or seconds < 0:
            raise ValueError("elapsed seconds must be a non-negative integer")
        return replace(self, remaining=max(0, self.remaining - seconds))

    def timeout(self, team: Possession) -> "Clock":
        if not isinstance(team, Possession):
            raise ValueError("timeout team must be home or away")
        index = 0 if team is Possession.HOME else 1
        if not self.timeouts[index]:
            raise ValueError("team has no timeouts remaining")
        counts = list(self.timeouts)
        counts[index] -= 1
        return replace(self, timeouts=tuple(counts))

    def next_quarter(self) -> "Clock":
        if self.remaining or self.quarter == 4:
            raise ValueError("only expired quarters 1..3 can advance")
        return Clock(
            self.quarter + 1, QUARTER_SECONDS, (3, 3) if self.quarter == 2 else self.timeouts
        )


def duration(facts: TimingFacts, clock: Clock) -> int:
    """Shortest applicable standard-chart category; never inspect a description."""
    if facts.conversion or facts.no_elapsed_time:
        return 0
    if facts.unreturned_kickoff:
        return 0
    late_half = (clock.quarter == 2 and clock.remaining <= 120) or (
        clock.quarter == 4 and clock.remaining <= 300
    )
    if (
        facts.change_of_possession
        or facts.penalty
        or facts.incomplete
        or facts.scoring
        or facts.touchback
        or (facts.out_of_bounds and late_half)
    ):
        return 10
    return 20 if facts.first_down else 30
