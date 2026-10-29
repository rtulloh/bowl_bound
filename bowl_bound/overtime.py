"""Home-season college overtime profiles and immutable round bookkeeping."""

from dataclasses import dataclass, replace
from enum import Enum

from .game_state import Possession


class GameType(str, Enum):
    REGULAR = "regular"
    POSTSEASON = "postseason"


@dataclass(frozen=True)
class OvertimeProfile:
    enabled: bool
    mandatory_two_from: int | None = None
    paired_tries_from: int | None = None

    def mandatory_two(self, round_number: int) -> bool:
        return self.mandatory_two_from is not None and round_number >= self.mandatory_two_from

    def paired_tries(self, round_number: int) -> bool:
        return self.paired_tries_from is not None and round_number >= self.paired_tries_from


def overtime_profile(season: int, game_type: GameType) -> OvertimeProfile:
    """Select the approved major-college era, never infer the newer team's rules."""
    if type(season) is not int or not 1940 <= season <= 2023:
        raise ValueError("overtime requires a supported home season (1940–2023)")
    if season < 1995 or (season == 1995 and game_type is GameType.REGULAR):
        return OvertimeProfile(False)
    if season <= 1996:
        return OvertimeProfile(True)
    if season <= 2018:
        return OvertimeProfile(True, 3)
    if season <= 2020:
        return OvertimeProfile(True, 3, 5)
    return OvertimeProfile(True, 2, 3)


@dataclass(frozen=True)
class OvertimeState:
    first: Possession
    round_number: int = 1
    series_number: int = 1
    timeouts: tuple[int, int] = (1, 1)

    @property
    def offense(self) -> Possession:
        return self.first if self.series_number == 1 else self.first.other

    def next_series(self) -> "OvertimeState":
        """Advance after a tied pair, alternating who goes first without a fixed cap."""
        if self.series_number == 1:
            return replace(self, series_number=2)
        return OvertimeState(self.first.other, self.round_number + 1)

    def timeout(self, team: Possession) -> "OvertimeState":
        index = 0 if team is Possession.HOME else 1
        if not self.timeouts[index]:
            raise ValueError("no overtime timeout remains for that team this round")
        values = list(self.timeouts)
        values[index] -= 1
        return replace(self, timeouts=tuple(values))


@dataclass(frozen=True)
class OvertimeView:
    round_number: int
    series_number: int
    first_possession: str
    possession: str
    paired_tries: bool
    mandatory_two: bool
