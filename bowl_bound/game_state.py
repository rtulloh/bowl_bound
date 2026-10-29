"""Basic game-state transitions: possession, spot, downs and distance (Milestone 9).

Pure functions only. Field position is measured as yards from the goal the
possessing team is attacking (1..99). No clock, score, or statistics here.
Pending results are refused instead of being treated as zero yards.
"""

from dataclasses import dataclass
from enum import Enum

from .models import ResultKind
from .resolution import PriorityResult

MIN_SPOT = 1
MAX_SPOT = 99
MIDFIELD = 50
FOURTH_DOWN = 4
FIRST_DOWN_DISTANCE = 10


class Possession(Enum):
    HOME = "home"
    AWAY = "away"

    @property
    def other(self) -> "Possession":
        return Possession.AWAY if self is Possession.HOME else Possession.HOME


class Outcome(Enum):
    ADVANCE = "advance"
    FIRST_DOWN = "first_down"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    TOUCHDOWN = "touchdown"


class EndZonePending(ValueError):
    """A result would leave the ball in or past the defender's end zone; not guessed."""


class PendingOutcomeError(ValueError):
    """A pending branch reached state transition before its later milestone resolves it."""


@dataclass(frozen=True)
class FieldState:
    possession: Possession
    yards_to_goal: int
    down: int
    yards_to_go: int

    def __post_init__(self) -> None:
        if type(self.possession) is not Possession:
            raise TypeError("possession must be a Possession")
        for name, value in (
            ("yards_to_goal", self.yards_to_goal),
            ("down", self.down),
            ("yards_to_go", self.yards_to_go),
        ):
            if type(value) is not int:
                raise TypeError(f"{name} must be an integer")
        if not MIN_SPOT <= self.yards_to_goal <= MAX_SPOT:
            raise ValueError("yards_to_goal must be within 1..99")
        if not 1 <= self.down <= FOURTH_DOWN:
            raise ValueError("down must be within 1..4")
        if not 1 <= self.yards_to_go <= self.yards_to_goal:
            raise ValueError("yards_to_go must be within 1..yards_to_goal")


@dataclass(frozen=True)
class Transition:
    outcome: Outcome
    state: FieldState | None
    description: str | None = None


def start_drive(possession: Possession, yards_to_goal: int) -> FieldState:
    """Begin a drive at the given spot with first-and-ten, or goal-to-go when closer."""
    distance = min(FIRST_DOWN_DISTANCE, yards_to_goal)
    return FieldState(possession, yards_to_goal, 1, distance)


def apply_gain(state: FieldState, gain: int) -> Transition:
    """Move the ball by a final signed gain and update down and distance."""
    if type(gain) is not int:
        raise TypeError("gain must be an integer")
    new_goal = state.yards_to_goal - gain
    if new_goal <= 0:
        return Transition(Outcome.TOUCHDOWN, None, f"Touchdown for {state.possession.value}")
    if new_goal > MAX_SPOT:
        raise EndZonePending("gain would leave the ball past the own end zone; not resolved here")
    if gain >= state.yards_to_go:
        return _first_down(state, new_goal)
    if state.down == FOURTH_DOWN:
        return _turnover_on_downs(state, new_goal)
    remaining = state.yards_to_go - gain
    distance = min(remaining, new_goal)
    return Transition(
        Outcome.ADVANCE,
        FieldState(state.possession, new_goal, state.down + 1, distance),
    )


def apply_incomplete(state: FieldState) -> Transition:
    """An incomplete pass keeps the spot and consumes a down."""
    if state.down == FOURTH_DOWN:
        return _turnover_on_downs(state, state.yards_to_goal)
    return Transition(
        Outcome.ADVANCE,
        FieldState(state.possession, state.yards_to_goal, state.down + 1, state.yards_to_go),
    )


def apply_result(state: FieldState, result: PriorityResult) -> Transition:
    """Map a Milestone 7/8 priority result onto a state transition."""
    if result.pending:
        raise PendingOutcomeError(
            f"{result.kind.value if result.kind else 'unknown'} result is pending"
        )
    if result.kind is ResultKind.TOUCHDOWN:
        return Transition(Outcome.TOUCHDOWN, None, f"Touchdown for {state.possession.value}")
    if result.kind is ResultKind.INCOMPLETE:
        return apply_incomplete(state)
    if result.kind is ResultKind.YARDS and result.yards is not None:
        return apply_gain(state, result.yards)
    if result.kind is ResultKind.NO_CHANGE:
        return apply_gain(state, 0)
    raise PendingOutcomeError(f"{result.kind} is not a final ordinary outcome")


def spot_label(state: FieldState) -> str:
    """Engine-owned spot wording: 'own 35', 'midfield', or 'opponent 7'."""
    if state.yards_to_goal == MIDFIELD:
        return "midfield"
    if state.yards_to_goal > MIDFIELD:
        return f"own {100 - state.yards_to_goal}"
    return f"opponent {state.yards_to_goal}"


def situation_label(state: FieldState) -> str:
    """Engine-owned down-and-distance wording: '3rd and 4' or '1st and Goal'."""
    ordinal = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}[state.down]
    distance = "Goal" if state.yards_to_go == state.yards_to_goal else str(state.yards_to_go)
    return f"{ordinal} and {distance}"


def describe(state: FieldState) -> str:
    """Engine-owned wording for the current situation."""
    return f"{state.possession.value}: {situation_label(state)} at {spot_label(state)}"


def _first_down(state: FieldState, new_goal: int) -> Transition:
    return Transition(
        Outcome.FIRST_DOWN,
        FieldState(state.possession, new_goal, 1, min(FIRST_DOWN_DISTANCE, new_goal)),
    )


def _turnover_on_downs(state: FieldState, spot: int) -> Transition:
    """The other team takes over at the same spot, measured from its own goal line."""
    other = state.possession.other
    new_goal = MAX_SPOT + 1 - spot
    return Transition(
        Outcome.TURNOVER_ON_DOWNS,
        FieldState(other, new_goal, 1, min(FIRST_DOWN_DISTANCE, new_goal)),
    )
