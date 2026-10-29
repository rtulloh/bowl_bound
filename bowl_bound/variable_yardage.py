"""Full-feature Basic VI-3 distances shared by every chart procedure."""

from .dice import DiceSource, OffensiveRoll
from .models import VariableReference


def roll_variable(
    reference: VariableReference, multiplier: int, dice: DiceSource
) -> tuple[int, tuple[OffensiveRoll, ...]]:
    """Return signed distance and exactly the physical rolls used to compute it."""
    if type(reference) is not VariableReference or type(multiplier) is not int:
        raise ValueError("variable yardage requires a reference and integer multiplier")
    count = (
        3 if reference is VariableReference.T3 else 2 if reference is VariableReference.T2 else 1
    )
    rolls = tuple(dice.offensive() for _ in range(count))
    distance = (
        rolls[0].direct_sum
        if reference is VariableReference.DS
        else 40 - rolls[0].total
        if reference is VariableReference.X
        else sum(roll.total for roll in rolls)
    )
    return distance * multiplier, rolls
