"""Announcer-style calls derived only from authoritative engine reports.

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


def _call(report: PlayReport, templates: tuple[str, ...], **values: str) -> str:
    """Cycle within a phrase family without state, hashes or any random stream."""
    text = templates[max(report.number - 1, 0) % len(templates)].format(**values)
    return text[0].upper() + text[1:]


def _final_spot(report: PlayReport) -> str:
    after = report.state_after
    if after is None:
        return ""
    return f" {after.possession_name} ball at {after.spot}."


def _scrimmage_call(report: PlayReport, names: dict[str, str]) -> str | None:
    kind, yards = report.statistics.kind, report.statistics.yards
    distance = f"{abs(yards)} {'yard' if abs(yards) == 1 else 'yards'}"
    values = {**names, "distance": distance, "team": report.state_before.possession_name}
    if kind is StatKind.INTERCEPTION:
        if report.outcome not in {
            "defensive_recovery",
            "defensive_touchdown",
            "touchback",
            "safety",
        }:
            return None
        text = _call(
            report,
            (
                "{passer}'s pass is INTERCEPTED!",
                "INTERCEPTED! The defense picks off {passer}'s pass!",
                "{passer} throws... INTERCEPTED!",
            ),
            **values,
        )
        if "returner" in names:
            text += " " + _call(report, ("{returner} returns the interception!",), **names)
        text += {
            "defensive_touchdown": " TOUCHDOWN on the interception return!",
            "touchback": " Touchback.",
            "safety": " SAFETY!",
        }.get(report.outcome, "")
        text += _final_spot(report)
        if (
            report.state_after is not None
            and report.state_after.possession != report.state_before.possession
        ):
            text += " ★ TURNOVER!"
        return text
    if report.outcome not in {
        "advance",
        "first_down",
        "turnover_on_downs",
        "touchdown",
        "safety",
        "declined_interception",
    }:
        return None
    if kind is StatKind.RUSH:
        if report.statistics.touchdown:
            templates = (
                "{runner} takes it in from {distance} out! TOUCHDOWN, {team}!",
                "TOUCHDOWN, {team}! {runner} scores on a run of {distance}!",
                "{runner} reaches the end zone! TOUCHDOWN, {team}, on a run of {distance}!",
            )
        elif yards == 0:
            templates = (
                "{runner} is stopped for no gain!",
                "The defense holds firm! No gain for {runner}.",
                "Nowhere to go for {runner}—no gain on the play!",
                "{runner} gets the call, but the defense says no! No gain.",
            )
        elif yards < 0:
            templates = (
                "{runner} is stopped for a loss of {distance}!",
                "The defense holds {runner} to a loss of {distance}!",
                "No room for {runner}! A loss of {distance} on the play.",
            )
        elif yards >= 15:
            templates = (
                "A big run for {runner}! A gain of {distance}!",
                "{runner} picks up {distance}! What a gain on the ground!",
                "{runner} with a big pickup—{distance} on the run!",
            )
        else:
            templates = (
                "{runner} picks up {distance} on the ground.",
                "A gain of {distance} for {runner}.",
                "{runner} carries for {distance}.",
            )
    elif kind is StatKind.COMPLETE:
        if report.statistics.touchdown:
            templates = (
                "{passer} to {receiver}... TOUCHDOWN, {team}! A scoring pass of {distance}!",
                "TOUCHDOWN! {passer} connects with {receiver} for {distance}!",
                "{receiver} has it! {distance} on the pass from {passer}—TOUCHDOWN, {team}!",
            )
        elif yards == 0:
            templates = (
                "{passer} finds {receiver}, but the defense allows no gain!",
                "Complete from {passer} to {receiver}! No gain on the play.",
                "{receiver} catches the pass from {passer}—no gain!",
            )
        elif yards < 0:
            templates = (
                "{passer} completes to {receiver}, but it is a loss of {distance}!",
                "{receiver} catches the pass from {passer} for a loss of {distance}!",
                "Complete from {passer} to {receiver}—a loss of {distance}!",
            )
        elif yards >= 20:
            templates = (
                "{passer} connects with {receiver} for {distance}! A big play through the air!",
                "{passer} to {receiver}—complete! {distance} on the play!",
                "A big catch for {receiver}! {passer} finds the target for {distance}!",
            )
        else:
            templates = (
                "{passer} finds {receiver} for {distance}.",
                "Complete! {passer} to {receiver} for {distance}.",
                "{receiver} makes the catch! {distance} on the pass from {passer}.",
            )
    elif kind is StatKind.INCOMPLETE:
        templates = (
            "{passer} throws... incomplete!",
            "Incomplete! No completion for {passer} on this play.",
            "{passer}'s pass falls incomplete.",
        )
    elif kind is StatKind.SACK and yards < 0:
        templates = (
            "{quarterback} is SACKED! A loss of {distance}!",
            "Down goes {quarterback}! SACKED for a loss of {distance}!",
            "The defense sacks {quarterback} for a loss of {distance}!",
        )
    else:
        return None
    text = _call(report, templates, **values)
    if report.outcome == "first_down":
        text += " First down!"
    elif report.outcome == "turnover_on_downs":
        text += " Turnover on downs!" + _final_spot(report)
    elif report.outcome == "safety":
        text += " SAFETY!"
    return text


def _kick_call(report: PlayReport, names: dict[str, str]) -> str | None:
    # Actor eligibility already establishes a committed kick and any actual return.
    if "punter" in names:
        lead = f"{names['punter']} punts."
    elif "kicker" in names:
        lead = f"{names['kicker']} kicks off."
    else:
        return None
    outcome = report.outcome
    if outcome in {"field_goal_good", "field_goal_missed", "pat_good", "pat_missed"}:
        label = "field goal" if outcome.startswith("field_goal") else "extra point"
        result = "GOOD!" if outcome.endswith("good") else "NO GOOD!"
        return _call(
            report,
            (
                "{kicker} attempts the {label}... {result}",
                "The {label} attempt from {kicker} is {result}",
                "{kicker}'s {label} attempt—{result}",
            ),
            **names,
            label=label,
            result=result,
        )
    if outcome == "touchback":
        text = lead + " Touchback."
    elif outcome == "punt_fair_catch":
        text = lead + " Fair catch—no return."
    elif outcome == "punt_dead":
        text = lead + " The punt is downed—no return."
    elif "returner" in names:
        text = lead + " " + _call(report, ("{returner} returns the kick!",), **names)
        if outcome == "return_touchdown":
            text += " All the way—TOUCHDOWN on the return!"
        elif outcome == "safety":
            text += " SAFETY!"
    else:
        return None
    return text[0].upper() + text[1:]


def narrate_report(
    report: PlayReport,
    home_roster: Roster | None = None,
    away_roster: Roster | None = None,
) -> str:
    """Render established facts as stable play-by-play, with optional player names.

    Pending, unsupported, penalty and ambiguous recovery reports retain complete
    factual commentary. Names are illustrative, not simulated player identities.
    Stored descriptions, dice, statistics and replay digests never change.
    """
    if (
        report.pending
        or not report.supported
        or report.timing.penalty
        or report.called_play in {"Kneel", "Spike"}
    ):
        return report.commentary
    if any(e.section in {"fumble_recovery", "blocked_kick_recovery"} for e in report.trace):
        return report.commentary
    actors = _actors(report)
    if not actors:
        return report.commentary
    rosters = {"home": home_roster, "away": away_roster}
    index = max(report.number - 1, 0)
    names = {role: player_name(rosters[side], position, index) for role, position, side in actors}
    text = (
        _kick_call(report, names)
        if report.statistics.kind is StatKind.EXCLUDED
        else _scrimmage_call(report, names)
    )
    if text is None:
        return report.commentary
    # Kick distances/enforcement details have no separate structured report fields.
    # Preserve the engine's full factual text rather than parse cells or infer yards.
    if report.statistics.kind is StatKind.EXCLUDED:
        return f"{text} {report.commentary}"
    return text
