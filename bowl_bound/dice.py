"""Exact Bowl Bound dice faces and injectable sources (Basic IV-1).

Face tuples retain multiplicities. Sampling totals uniformly would produce incorrect
odds. Rolls retain individual faces because DS uses their direct sum.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from random import Random
from typing import Protocol, TypeVar, cast

BLACK_FACES = (1, 2, 2, 3, 3, 3)
WHITE_ONE_FACES = (0, 0, 1, 2, 3, 4)
WHITE_TWO_FACES = (0, 1, 2, 3, 4, 5)
RED_FACES = (1, 1, 1, 2, 2, 3)
GREEN_FACES = (0, 0, 0, 0, 1, 2)


def _validate_face(name: str, value: int, faces: tuple[int, ...]) -> None:
    if type(value) is not int or value not in faces:
        raise ValueError(f"Invalid {name} face {value!r}; expected one of {sorted(set(faces))}")


@dataclass(frozen=True)
class OffensiveRoll:
    """Three physical offensive faces; white dice are distinct."""

    black: int
    white_one: int
    white_two: int

    def __post_init__(self) -> None:
        _validate_face("black", self.black, BLACK_FACES)
        _validate_face("first white", self.white_one, WHITE_ONE_FACES)
        _validate_face("second white", self.white_two, WHITE_TWO_FACES)

    @property
    def total(self) -> int:
        return 10 * self.black + self.white_one + self.white_two

    @property
    def direct_sum(self) -> int:
        return self.black + self.white_one + self.white_two


@dataclass(frozen=True)
class DefensiveRoll:
    """Two physical defensive faces."""

    red: int
    green: int

    def __post_init__(self) -> None:
        _validate_face("red", self.red, RED_FACES)
        _validate_face("green", self.green, GREEN_FACES)

    @property
    def total(self) -> int:
        return self.red + self.green


class DiceSource(Protocol):
    """Engine-facing dependency; no chart or game logic belongs in a source."""

    def offensive(self) -> OffensiveRoll: ...

    def defensive(self) -> DefensiveRoll: ...


class RandomDice:
    """Roll physical faces using an independently owned or injected generator."""

    def __init__(self, rng: Random | None = None) -> None:
        self._rng = rng if rng is not None else Random()

    def offensive(self) -> OffensiveRoll:
        return OffensiveRoll(
            self._rng.choice(BLACK_FACES),
            self._rng.choice(WHITE_ONE_FACES),
            self._rng.choice(WHITE_TWO_FACES),
        )

    def defensive(self) -> DefensiveRoll:
        return DefensiveRoll(self._rng.choice(RED_FACES), self._rng.choice(GREEN_FACES))


class DiceSequenceError(RuntimeError):
    """A scripted source was exhausted or requested out of order."""


Roll = TypeVar("Roll", OffensiveRoll, DefensiveRoll)


class ScriptedDice:
    """Consume one ordered script, failing rather than inventing extra rolls.

    A wrong-kind request leaves the script position unchanged. Input is copied so
    later mutation of a supplied list cannot alter the simulation.
    """

    def __init__(self, rolls: Iterable[OffensiveRoll | DefensiveRoll]) -> None:
        self._rolls = tuple(rolls)
        if any(not isinstance(roll, (OffensiveRoll, DefensiveRoll)) for roll in self._rolls):
            raise ValueError("Script entries must be offensive or defensive roll instances")
        self._position = 0

    def _next(self, expected: type[Roll]) -> Roll:
        if self._position == len(self._rolls):
            raise DiceSequenceError(f"Dice script exhausted while requesting {expected.__name__}")
        roll = self._rolls[self._position]
        if not isinstance(roll, expected):
            kind = "offensive" if isinstance(roll, OffensiveRoll) else "defensive"
            raise DiceSequenceError(f"Next scripted roll is {kind}; requested {expected.__name__}")
        self._position += 1
        return cast(Roll, roll)

    def offensive(self) -> OffensiveRoll:
        return self._next(OffensiveRoll)

    def defensive(self) -> DefensiveRoll:
        return self._next(DefensiveRoll)


def roll_view(roll: OffensiveRoll | DefensiveRoll) -> dict[str, object]:
    """Describe an already observed roll, preserving its exact order and total."""
    if isinstance(roll, OffensiveRoll):
        facts = (
            ("black", "Black", "black", roll.black),
            ("white_one", "White 1", "white", roll.white_one),
            ("white_two", "White 2", "white", roll.white_two),
        )
        label = "Offensive dice"
    elif isinstance(roll, DefensiveRoll):
        facts = (("red", "Red", "red", roll.red), ("green", "Green", "green", roll.green))
        label = "Defensive dice"
    else:
        raise TypeError("roll presentation requires an observed offensive or defensive roll")
    return {
        "faces": [face for _, _, _, face in facts],
        "total": roll.total,
        "dice_label": label,
        "dice": [
            {"role": role, "label": name, "color": color, "face": face}
            for role, name, color, face in facts
        ],
    }
