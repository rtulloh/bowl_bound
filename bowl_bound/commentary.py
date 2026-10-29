"""Optional illustrative actor labels derived from authoritative engine reports.

Never changes reports, chooses football outcomes or consumes randomness. Legacy
semantic descriptions and replay digests deliberately remain independent of rosters.
"""

from .roster import Roster, player_name
from .session import PlayReport
from .statistics import StatKind

Actor = tuple[str, str, str]  # label, roster position, canonical side


def _actors(report: PlayReport) -> tuple[Actor, ...]:
    """Use structured credit/stage identifiers, never prose or raw chart tokens."""
    sections: list[str] = []
    for entry in report.trace:
        if entry.section == "penalty_reroll":
            sections.clear()
        else:
            sections.append(entry.section)
    kind, team = report.statistics.kind, report.statistics.team
    if team is not None:
        side = team.value
        if kind is StatKind.RUSH:
            position = (
                "qb" if any(s in {"supplemental:QR", "supplemental:QT"} for s in sections) else "rb"
            )
            return (("runner", position, side),)
        if kind is StatKind.COMPLETE:
            return (("passer", "qb", side), ("receiver", "wr", side))
        if kind in {StatKind.INCOMPLETE, StatKind.INTERCEPTION}:
            actors = (("passer", "qb", side),)
            if (
                kind is StatKind.INTERCEPTION
                and any(s in {"turnover_return", "end_zone_recovery_return"} for s in sections)
                and report.outcome in {"defensive_recovery", "defensive_touchdown", "safety"}
            ):
                actors += (("returner", "kr", team.other.value),)
            return actors
        if kind is StatKind.SACK:
            return (("quarterback", "qb", side),)
        return ()
    side = report.state_before.possession
    if side not in {"home", "away"}:
        return ()
    kick = next((s for s in sections if s in {"punt", "kickoff", "field_goal", "pat"}), None)
    allowed = {
        "punt": {
            "punt_fair_catch",
            "punt_dead",
            "punt_return",
            "touchback",
            "return_touchdown",
            "safety",
        },
        "kickoff": {"kickoff_return", "touchback", "return_touchdown", "safety"},
        "field_goal": {"field_goal_good", "field_goal_missed"},
        "pat": {"pat_good", "pat_missed"},
    }
    if kick is None or report.outcome not in allowed[kick]:
        return ()
    # An aborted kick can score a safety before any recovery roll is recorded.
    if report.outcome == "safety" and not any(
        s in {"punt_return", "kickoff_return"} for s in sections
    ):
        return ()
    actors = (("punter", "p", side),) if kick == "punt" else (("kicker", "k", side),)
    if (
        kick in {"punt", "kickoff"}
        and kick + "_return" in sections
        and report.outcome in {"punt_return", "kickoff_return", "return_touchdown", "safety"}
    ):
        actors += (("returner", "kr", "away" if side == "home" else "home"),)
    return actors


def narrate_report(
    report: PlayReport,
    home_roster: Roster | None = None,
    away_roster: Roster | None = None,
) -> str:
    """Prefix established roles with deterministic, illustrative roster labels.

    Pending/unsupported reports and ambiguous recovery chains retain the existing
    factual generic commentary. Names do not record simulated player identities.
    """
    base = report.commentary
    if report.pending or not report.supported:
        return base
    if any(e.section in {"fumble_recovery", "blocked_kick_recovery"} for e in report.trace):
        return base
    actors = _actors(report)
    rosters = {"home": home_roster, "away": away_roster}
    if not any(
        rosters[side] is not None and rosters[side].players.get(position)
        for _, position, side in actors
    ):
        return base
    index = max(report.number - 1, 0)
    labels = "; ".join(
        f"{role}: {player_name(rosters[side], position, index)}" for role, position, side in actors
    )
    return f"Illustrative players — {labels}. {base}"
