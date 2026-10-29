"""Penalty-table assessment and accepted-penalty field enforcement.

This module deliberately does not resolve clock, score, safety, or touchdown outcomes.
A caller must resolve those outcomes before asking this module to enforce a penalty.
"""

from dataclasses import dataclass

from .dice import DiceSource, OffensiveRoll
from .game_state import FIRST_DOWN_DISTANCE, MAX_SPOT, FieldState
from .models import PenaltyCode, PenaltyData, PenaltyTeam
from .variable_yardage import roll_variable


@dataclass(frozen=True)
class AssessedPenalty:
    """A chart penalty after its table distance and enforcement flags are known."""

    source: PenaltyData
    yards: int
    automatic_first_down: bool = False
    from_end_of_gain: bool = False
    pre_snap: bool = False
    roll: OffensiveRoll | None = None
    distance_rolls: tuple[OffensiveRoll, ...] = ()
    pi_as_def10: bool = False
    bad_snap: bool = False
    no_elapsed_time: bool = False
    no_foul: bool = False

    def __post_init__(self) -> None:
        if type(self.source) is not PenaltyData:
            raise TypeError("source must be PenaltyData")
        if type(self.yards) is not int or self.yards < 0:
            raise ValueError("yards must be a non-negative integer")
        for name, value in (
            ("automatic_first_down", self.automatic_first_down),
            ("from_end_of_gain", self.from_end_of_gain),
            ("pre_snap", self.pre_snap),
            ("pi_as_def10", self.pi_as_def10),
            ("bad_snap", self.bad_snap),
            ("no_elapsed_time", self.no_elapsed_time),
            ("no_foul", self.no_foul),
        ):
            if type(value) is not bool:
                raise TypeError(f"{name} must be a bool")
        if self.roll is not None and type(self.roll) is not OffensiveRoll:
            raise TypeError("roll must be an OffensiveRoll or None")
        if type(self.distance_rolls) is not tuple or any(
            type(roll) is not OffensiveRoll for roll in self.distance_rolls
        ):
            raise TypeError("distance_rolls must be a tuple of OffensiveRoll instances")


def assess_penalty(
    data: PenaltyData, dice: DiceSource, *, hurried: bool = False
) -> AssessedPenalty:
    """Resolve an imported penalty token without consuming an unnecessary roll."""
    if type(data) is not PenaltyData:
        raise TypeError("data must be PenaltyData")
    if data.code in {PenaltyCode.S, PenaltyCode.R}:
        roll = dice.offensive()
        return _assess_hurry_table(data, roll) if hurried else _assess_table(data, roll)
    if data.code in {PenaltyCode.FIVE_YARDS, PenaltyCode.FIVE_YARDS_X}:
        if data.team is PenaltyTeam.OFFENSE:
            raise ValueError("5Y and 5X are not valid offensive penalties")
        return AssessedPenalty(data, 5, from_end_of_gain=True)
    if data.code is PenaltyCode.PI:
        if data.variable is not None:
            distance, rolls = roll_variable(data.variable, data.variable_multiplier, dice)
            yards = min(15, max(0, distance))
            return AssessedPenalty(data, yards, automatic_first_down=True, distance_rolls=rolls)
        assert data.yards is not None
        return AssessedPenalty(data, min(15, max(0, data.yards)), automatic_first_down=True)
    assert data.code is PenaltyCode.FIXED
    assert data.yards is not None
    if data.team is PenaltyTeam.DEFENSE and data.yards == 15:
        return AssessedPenalty(data, 15, automatic_first_down=True, from_end_of_gain=True)
    return AssessedPenalty(data, data.yards)


def _assess_table(data: PenaltyData, roll: OffensiveRoll) -> AssessedPenalty:
    total = roll.total
    if data.code is PenaltyCode.S:
        if data.team is PenaltyTeam.OFFENSE:
            if total <= 19:
                return AssessedPenalty(data, 5, roll=roll)
            if total <= 32:
                return AssessedPenalty(data, 5, pre_snap=True, roll=roll)
            if total <= 36:
                return AssessedPenalty(data, 10, roll=roll)
            return AssessedPenalty(data, 15, roll=roll)
        if total <= 24 or 30 <= total <= 32:
            return AssessedPenalty(data, 5, roll=roll)
        if total <= 29:
            return AssessedPenalty(data, 5, from_end_of_gain=True, roll=roll)
        if total == 33:
            return AssessedPenalty(data, 10, roll=roll)
        return AssessedPenalty(
            data, 15, automatic_first_down=True, from_end_of_gain=True, roll=roll
        )
    if data.team is PenaltyTeam.OFFENSE:
        if total <= 19:
            return AssessedPenalty(data, 5, roll=roll)
        if total <= 29:
            return AssessedPenalty(data, 15, roll=roll)
        return AssessedPenalty(data, 10, roll=roll)
    if total <= 19:
        return AssessedPenalty(data, 10, roll=roll)
    if total <= 29:
        return AssessedPenalty(data, 5, from_end_of_gain=True, roll=roll)
    return AssessedPenalty(data, 15, automatic_first_down=True, from_end_of_gain=True, roll=roll)


def enforce_penalty(
    state: FieldState, penalty: AssessedPenalty, *, gain: int = 0, from_end: bool = False
) -> FieldState:
    """Apply an accepted penalty, retaining the current down unless it earns a first down.

    A penalty cancels the play, so the play's gain matters only when the offended team
    chooses end-of-gain enforcement. That choice needs a positive, in-field gain; a
    touchdown or safety gain is rejected for the later scoring rules. Enforcement from
    the previous spot ignores the gain entirely.
    """
    if type(state) is not FieldState:
        raise TypeError("state must be FieldState")
    if type(penalty) is not AssessedPenalty:
        raise TypeError("penalty must be AssessedPenalty")
    if type(gain) is not int:
        raise TypeError("gain must be an integer")
    if type(from_end) is not bool:
        raise TypeError("from_end must be a bool")

    spot = state.yards_to_goal
    if from_end and penalty.from_end_of_gain and gain > 0:
        # Only a positive gain is marked from its end, so the end spot is always closer to
        # the goal than the snap. A gain that reaches the goal is a touchdown (scoring rules).
        end_spot = state.yards_to_goal - gain
        if end_spot <= 0:
            raise ValueError("touchdown gain must be resolved before penalty enforcement")
        spot = end_spot
    new_spot = _enforced_spot(spot, penalty)

    if penalty.automatic_first_down:
        return FieldState(state.possession, new_spot, 1, min(FIRST_DOWN_DISTANCE, new_spot))

    line_to_gain = state.yards_to_goal - state.yards_to_go
    if new_spot <= line_to_gain:
        return FieldState(state.possession, new_spot, 1, min(FIRST_DOWN_DISTANCE, new_spot))
    return FieldState(state.possession, new_spot, state.down, new_spot - line_to_gain)


def enforce_return_penalty(
    return_start: FieldState,
    penalty: AssessedPenalty,
    *,
    return_yards: int,
    origin: int | None = None,
    continues_original_play: bool = False,
    scrimmage_start: FieldState | None = None,
) -> FieldState:
    """Enforce a return foul under Basic VI-4(C)(vi).

    Return fouls are marked from the end of the return.  An offensive foul after a
    return that passes its halfway point is instead marked from that midpoint.
    A new possessing team starts first-and-ten. An own-recovery return instead
    retains the original down and line to gain unless enforcement earns a first down.
    """
    if type(return_start) is not FieldState:
        raise TypeError("return_start must be FieldState")
    if type(penalty) is not AssessedPenalty:
        raise TypeError("penalty must be AssessedPenalty")
    if type(return_yards) is not int:
        raise TypeError("return_yards must be an integer")
    start = return_start.yards_to_goal if origin is None else origin
    if type(start) is not int or not 1 <= start <= 109:
        raise ValueError("return origin must lie in the field or live end zone")
    end_spot = start - return_yards
    spot = end_spot
    if penalty.source.team is PenaltyTeam.OFFENSE and return_yards * 2 > start:
        # A half-yard marker is placed toward midfield, per VI-4(C)(vii).
        spot = (start + 1) // 2
    if not 1 <= spot <= MAX_SPOT:
        raise ValueError("return penalty needs an in-field enforcement spot")
    new_spot = _enforced_spot(spot, penalty)
    if continues_original_play and not penalty.automatic_first_down:
        original = scrimmage_start or return_start
        line_to_gain = original.yards_to_goal - original.yards_to_go
        if new_spot > line_to_gain:
            return FieldState(
                return_start.possession, new_spot, original.down, new_spot - line_to_gain
            )
    return FieldState(return_start.possession, new_spot, 1, min(FIRST_DOWN_DISTANCE, new_spot))


def _enforced_spot(spot: int, penalty: AssessedPenalty) -> int:
    if penalty.source.team is PenaltyTeam.OFFENSE:
        own_distance = MAX_SPOT + 1 - spot
        return spot + min(penalty.yards, own_distance // 2)
    if penalty.source.code is PenaltyCode.PI and not penalty.pi_as_def10:
        if spot > 2:
            return max(2, spot - penalty.yards)
        return (spot + 1) // 2
    return spot - min(penalty.yards, spot // 2)


def _assess_hurry_table(data: PenaltyData, roll: OffensiveRoll) -> AssessedPenalty:
    """Advanced I-4(A); printed fixed/PI tokens keep chart-mode semantics."""
    total = roll.total
    if data.code is PenaltyCode.S:
        if data.team is PenaltyTeam.OFFENSE:
            if total <= 11:
                return AssessedPenalty(data, 0, roll=roll, bad_snap=True)
            return AssessedPenalty(data, 5 if total <= 29 else 10 if total <= 36 else 15, roll=roll)
        if total <= 14:
            false_start = PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, yards=5)
            return AssessedPenalty(false_start, 5, pre_snap=True, roll=roll, no_elapsed_time=True)
        if total <= 24:
            return AssessedPenalty(data, 5, roll=roll)
        if total <= 35:
            return AssessedPenalty(data, 5, from_end_of_gain=True, roll=roll)
        return AssessedPenalty(
            data, 15, automatic_first_down=True, from_end_of_gain=True, roll=roll
        )
    if data.team is PenaltyTeam.OFFENSE:
        return AssessedPenalty(data, 5 if total == 10 else 10 if total <= 34 else 15, roll=roll)
    if total == 10:
        return AssessedPenalty(data, 0, roll=roll, no_foul=True)
    if total <= 19:
        return AssessedPenalty(data, 5, from_end_of_gain=True, roll=roll)
    return AssessedPenalty(data, 15, automatic_first_down=True, from_end_of_gain=True, roll=roll)
