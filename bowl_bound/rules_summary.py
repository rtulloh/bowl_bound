"""Engine-owned descriptions of the home-season rules shown before kickoff."""

from dataclasses import dataclass

from .overtime import GameType, overtime_profile
from .special_teams import (
    MAX_SUPPORTED_SEASON,
    MIN_SUPPORTED_SEASON,
    free_kick_touchback_spot,
    kickoff_spot,
)


@dataclass(frozen=True)
class RulesSummary:
    """A supported or unsupported home-season rules summary for presentation."""

    season: int
    game_type: str
    supported: bool
    summary: str
    details: tuple[str, ...]


def rules_summary(season: int, game_type: str) -> RulesSummary:
    """Describe the engine's selected rules without duplicating them in the API."""
    try:
        game = GameType(game_type)
        profile = overtime_profile(season, game)
        spot = kickoff_spot(season)
        touchback = free_kick_touchback_spot(season)
    except ValueError:
        if game_type not in {member.value for member in GameType}:
            message = f"{game_type!r} is not a supported game type."
        elif not MIN_SUPPORTED_SEASON <= season <= MAX_SUPPORTED_SEASON:
            message = (
                f"{season} home-season rules are not supported; "
                f"choose a season between {MIN_SUPPORTED_SEASON} and {MAX_SUPPORTED_SEASON}."
            )
        else:
            message = "These home-season rules are not supported."
        return RulesSummary(
            season,
            game_type,
            False,
            message,
            (),
        )
    if not profile.enabled:
        overtime = "No overtime; regulation ties are final"
    elif profile.paired_tries_from is not None:
        overtime = (
            f"Overtime with two-point tries from OT{profile.mandatory_two_from} "
            f"and paired tries from OT{profile.paired_tries_from}"
        )
    elif profile.mandatory_two_from is not None:
        overtime = f"Overtime with two-point tries from OT{profile.mandatory_two_from}"
    else:
        overtime = "Overtime from the opponent 25"
    return RulesSummary(
        season,
        game.value,
        True,
        f"{season} home-season rules govern this game.",
        (
            f"Kickoffs from the {spot}",
            f"Free-kick touchback to the {touchback}",
            overtime,
            "Postseason" if game is GameType.POSTSEASON else "Regular season",
        ),
    )
