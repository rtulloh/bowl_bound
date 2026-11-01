"""Shared field coordinates and recovery rolls for live return procedures."""

from dataclasses import dataclass

from .dice import DiceSource, OffensiveRoll
from .game_state import FieldState

GOAL_LINE = 100
END_LINE = 110
END_ZONE_DEPTH_TRIGGER = 10
MAX_END_ZONE_DEPTH = 9
MAX_FIELD_SPOT = 99
TOUCHBACK_SPOT = 80


@dataclass(frozen=True)
class ReturnOrigin:
    """Live return coordinate in yards to the opponent's goal, including end zones."""

    yards_to_goal: int

    def __post_init__(self) -> None:
        if type(self.yards_to_goal) is not int or self.yards_to_goal < 1:
            raise ValueError("return origin must be a positive field-relative coordinate")


@dataclass(frozen=True)
class ReturnStart:
    """Representable field state paired with the actual live-ball coordinate."""

    state: FieldState
    origin: ReturnOrigin

    def __post_init__(self) -> None:
        if type(self.state) is not FieldState:
            raise TypeError("return start state must be FieldState")
        if type(self.origin) is not ReturnOrigin:
            raise TypeError("return start origin must be ReturnOrigin")
        if self.state.yards_to_goal != min(MAX_FIELD_SPOT, self.origin.yards_to_goal):
            raise ValueError("return origin does not match the representable spot")


@dataclass(frozen=True)
class RecoveryFacts:
    """Observed location and rolls for one recovery attempt."""

    spot: int
    depth_roll: OffensiveRoll | None
    recovery_roll: OffensiveRoll | None
    retained: bool | None

    @property
    def safety(self) -> bool:
        """Whether the location passed the end line before a recovery roll."""
        return self.recovery_roll is None


def resolve_recovery(
    origin: ReturnOrigin,
    location: int,
    recovery_range: range,
    dice: DiceSource,
) -> RecoveryFacts:
    """Resolve shared end-line, depth and recovery facts without choosing outcomes."""
    if type(origin) is not ReturnOrigin:
        raise TypeError("origin must be ReturnOrigin")
    if type(location) is not int:
        raise TypeError("location must be an integer")
    if type(recovery_range) is not range:
        raise TypeError("recovery_range must be a range")

    spot = origin.yards_to_goal - location
    if spot >= END_LINE:
        return RecoveryFacts(spot, None, None, None)
    depth_roll = None
    if spot <= -END_ZONE_DEPTH_TRIGGER:
        depth_roll = dice.offensive()
        spot = -(depth_roll.white_one + depth_roll.white_two)
    recovery_roll = dice.offensive()
    return RecoveryFacts(
        spot,
        depth_roll,
        recovery_roll,
        recovery_roll.total in recovery_range,
    )
