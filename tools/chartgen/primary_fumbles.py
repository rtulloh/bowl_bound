"""Observe primary snap facts by reproducing retained production-engine lookups.

This development observer uses recorded physical dice and immutable charts. It
neither samples new outcomes nor interprets display tokens or final possession.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import Defense, Play, ResultKind, TeamChart
from bowl_bound.penalties import PreparedPlay, prepare_play, prepare_resolution
from bowl_bound.resolution import resolve_qb_sneak, resolve_razzle_dazzle_result
from bowl_bound.return_recovery import ReturnOrigin, resolve_recovery
from bowl_bound.session import (
    PLAY_LABELS,
    _resolved_turnover_location,
    _trace_entry,
    _turnover_trace_entry,
)
from bowl_bound.team_csv import TeamFileMetadata
from bowl_bound.turnovers import TurnoverTrace
from tools.chartgen.research_runner import _json_value

from .evidence import Event

AuditTeams = Mapping[str, tuple[TeamChart, TeamFileMetadata]]
_PLAY_BY_LABEL = {label: play for play, label in PLAY_LABELS.items()}
_FORMATION_BY_LABEL = {f"Formation {formation.value}": formation for formation in Defense}


def _physical_roll(entry: Mapping[str, Any]) -> OffensiveRoll | DefensiveRoll:
    faces = entry["roll"]["faces"]
    if not isinstance(faces, list) or not all(type(face) is int for face in faces):
        raise ValueError("retained physical roll requires integer faces")
    if len(faces) == 3:
        return OffensiveRoll(*faces)
    if len(faces) == 2:
        return DefensiveRoll(*faces)
    raise ValueError("retained roll is not an offensive or defensive physical roll")


def _prepare(
    row: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    offense: TeamChart,
    defense: TeamChart,
    *,
    hurried: bool,
) -> tuple[PreparedPlay, ScriptedDice]:
    if trace[0]["section"] == "razzle_dazzle:defense_roll":
        if (
            len(trace) < 3
            or trace[1]["section"] != "razzle_dazzle:offense_roll"
            or trace[2]["section"] != "offense"
        ):
            raise ValueError("invalid retained Razzle-Dazzle comparison prefix")
        choice = trace[2]
        play = _PLAY_BY_LABEL[choice["play"]]
        formation = _FORMATION_BY_LABEL[
            next(entry["formation"] for entry in trace if entry["section"] == "defense")
        ]
        comparisons = (_physical_roll(trace[0]), _physical_roll(trace[1]))
        if not all(isinstance(roll, OffensiveRoll) for roll in comparisons):
            raise ValueError("Razzle-Dazzle requires offensive comparison rolls")
        # The selected offense row echoes one comparison. It is not a third draw.
        dice = ScriptedDice([_physical_roll(entry) for entry in trace[3:]])
        initial = resolve_razzle_dazzle_result(
            offense,
            defense,
            play,
            choice["roll"]["total"],
            comparisons,
            formation,
            dice,
            advanced_call=None,
            free_wildcard=False,
        )
        prepared = prepare_resolution(offense, defense, play, initial, dice, hurried=hurried)
    elif row["called_play"] == "QB Sneak":
        dice = ScriptedDice([_physical_roll(entry) for entry in trace])
        initial = resolve_qb_sneak(offense, None, dice, free_wildcard=False)
        prepared = prepare_resolution(offense, defense, Play.ONE, initial, dice, hurried=hurried)
    elif trace[0]["section"] == "hail_mary":
        dice = ScriptedDice([_physical_roll(entry) for entry in trace])
        prepared = prepare_play(
            offense, defense, Play.EIGHT, Defense.A, dice, hurried=hurried, hail_mary=True
        )
    else:
        if len(trace) < 2 or trace[0]["section"] != "offense" or trace[1]["section"] != "defense":
            raise ValueError("unidentified retained primary lookup prefix")
        play = _PLAY_BY_LABEL[trace[0]["play"]]
        formation = _FORMATION_BY_LABEL[trace[1]["formation"]]
        dice = ScriptedDice([_physical_roll(entry) for entry in trace])
        prepared = prepare_play(offense, defense, play, formation, dice, hurried=hurried)
    return prepared, dice


def _observe_row(
    row: Mapping[str, Any], result: Mapping[str, Any], teams: AuditTeams
) -> dict[str, Any]:
    calls = [
        call
        for call in result["coaching_calls"]
        if call["observation"]["play_number"] == row["number"] - 1
    ]
    if not calls or type(calls[-1]["observation"]["hurried"]) is not bool:
        raise ValueError("missing retained pre-commit hurried context")
    hurried = calls[-1]["observation"]["hurried"]
    side = row["state_before"]["possession"]
    if side not in {"home", "away"}:
        raise ValueError("invalid retained primary possession side")
    other = "away" if side == "home" else "home"
    offense = teams[result["teams"][side]][0]
    defense = teams[result["teams"][other]][0]
    trace = row["trace"]
    observed = {
        "report_number": row["number"],
        "offense_side": side,
        "offense_id": result["teams"][side],
        "primary_fumble": False,
        "first_recovery_retained": None,
        "bad_snap": False,
    }
    if not trace:
        fixed_actions = {"kneel": "Kneel", "clock:spike": "Spike"}
        if fixed_actions.get(calls[-1]["choice"]) != row["called_play"]:
            raise ValueError("unidentified primary snap without lookup evidence")
        return {**observed, "kind": "fixed_no_fumble"}
    prepared, dice = _prepare(row, trace, offense, defense, hurried=hurried)
    rebuilt = [_json_value(_trace_entry(entry)) for entry in prepared.resolution.trace]
    if rebuilt != trace[: len(rebuilt)]:
        raise ValueError("production-engine preparer trace prefix differs")
    resolution = prepared.resolution
    if resolution.result.kind is None:
        raise ValueError("primary result remains unidentified after engine preparation")
    observed.update(
        primary_fumble=resolution.result.kind is ResultKind.FUMBLE,
        kind=resolution.result.kind.value,
        bad_snap=resolution.bad_snap,
    )
    if observed["primary_fumble"]:
        location, location_trace = _resolved_turnover_location(resolution, offense, defense, dice)
        recovery = resolve_recovery(
            ReturnOrigin(row["state_before"]["yards_to_goal"]),
            location,
            offense.recovery_range,
            dice,
        )
        continuation = list(location_trace)
        if recovery.depth_roll is not None:
            continuation.append(TurnoverTrace("end_zone_depth", offense.name, recovery.depth_roll))
        if recovery.recovery_roll is not None:
            continuation.append(
                TurnoverTrace("fumble_recovery", offense.name, recovery.recovery_roll)
            )
        rebuilt_recovery = [_json_value(_turnover_trace_entry(entry)) for entry in continuation]
        if rebuilt_recovery != trace[len(rebuilt) : len(rebuilt) + len(rebuilt_recovery)]:
            raise ValueError("production-engine first recovery trace prefix differs")
        observed["first_recovery_retained"] = recovery.retained
    return observed


def observe_primary_results(result: Mapping[str, Any], teams: AuditTeams) -> list[dict[str, Any]]:
    """Reobserve qualified primary snaps without attributing return fumbles to offense.

    Recovery is the first physical recovery, independently of subsequent returns,
    another fumble, scoring or final possession. A dead ball can have no recovery.
    Missing or inconsistent evidence raises; failed games supply no observations.
    """
    if result.get("status") != "passed":
        return []
    if result.get("configuration", {}).get("advanced_ii") is not False:
        raise ValueError("primary observer requires recorded disabled Advanced II")
    observations = []
    previous = 0
    for row in result["engine_log"]:
        number = row["number"]
        if type(number) is not int or number <= previous:
            raise ValueError("invalid retained report ordering")
        previous = number
        if row["statistics"]["kind"] == "excluded":
            continue
        try:
            observations.append(_observe_row(row, result, teams))
        except (ValueError, KeyError, IndexError, StopIteration, RuntimeError, TypeError) as error:
            raise ValueError(f"primary observation failed at report {number}: {error}") from error
    return observations


def primary_source_fumble(event: Event) -> bool | None:
    """Classify primary F incidence without borrowing a return-holder fumble.

    For a rush/completion/sack, an unidentified holder can be inferred from the
    primary event, as in baseline generation. A known other holder on an
    interception is a return fumble. Other ambiguous ownership stays unknown.
    Net possession, recovery and scoring do not decide whether a fumble occurred.
    """
    if event.fumble is False:
        return False
    if event.fumble is None:
        return None
    if event.kind in {"rush", "complete", "sack"} and event.fumble_team in {
        None,
        event.team,
    }:
        return True
    if event.kind == "interception" and event.fumble_team == event.opponent:
        return False
    return None


def primary_source_coverage(events: Sequence[Event]) -> dict[str, Any]:
    """Count known and unknown eligible primary observations, including inference."""
    eligible = [
        event
        for event in events
        if not event.no_play
        and event.event_phase != "try"
        and event.kind in {"rush", "complete", "incomplete", "interception", "sack"}
    ]
    states = [primary_source_fumble(event) for event in eligible]
    return {
        "eligible_snaps": len(eligible),
        "known_primary_fumble": sum(value is True for value in states),
        "known_no_primary_fumble": sum(value is False for value in states),
        "unknown_primary_fumble": sum(value is None for value in states),
        "inferred_primary_holder": sum(
            primary_source_fumble(event) is True and event.fumble_team is None for event in eligible
        ),
        "known_return_holder_excluded_from_primary": sum(
            event.fumble is True
            and event.kind == "interception"
            and event.fumble_team == event.opponent
            for event in eligible
        ),
        "policy": (
            "primary-context holder inference disclosed; return F and unknown ownership separated"
        ),
    }
