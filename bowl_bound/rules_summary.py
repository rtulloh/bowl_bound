"""Engine-owned descriptions of the home-season rules shown before kickoff."""

from dataclasses import dataclass

from .overtime import GameType, overtime_profile
from .special_teams import free_kick_touchback_spot, kickoff_spot


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
        return RulesSummary(
            season,
            game_type,
            False,
            "These home-season rules are not supported.",
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
