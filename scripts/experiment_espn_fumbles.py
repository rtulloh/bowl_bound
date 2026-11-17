"""Evaluate disclosed ESPN attribution assumptions without editing source facts.

This experiment supplies a modeled fitting view, not a normalized source snapshot.
Its negative flags describe linked narrative incidence, not independently observed
absence. Every recovery row stays in the retained input and experiment ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from scripts.audit_espn_fumbles import audit_game
from tools.chartgen.espn_core import enrich_primary_fumbles, enrich_return_fumbles
from tools.chartgen.evidence import Event
from tools.chartgen.optional_flags import AUTHORED_FLAG_POLICY
from tools.chartgen.primary_fumbles import primary_source_coverage
from tools.chartgen.private_io import private_destination
from tools.chartgen.release_pipeline import generate_release_cohort
from tools.chartgen.source import read_normalized

POLICY = "bb-espn-separate-fumble-experiment-v5"
_PRIMARY = {"rush", "complete", "sack", "incomplete"}
_RETURN = {"punt", "kickoff", "interception"}


def _modeled(event: Event, **changes: Any) -> Event:
    return replace(
        event,
        **changes,
        optional_flag_policy=AUTHORED_FLAG_POLICY,
        optional_flag_observations=(),
        optional_flag_source_sha256=None,
        optional_flag_evidence=(
            *event.optional_flag_evidence,
            "experimental-modeled-view:" + POLICY,
        ),
    )


def _possible_return_predecessors(
    recovery: Mapping[str, Any], plays: Sequence[Mapping[str, Any]], events: Mapping[str, Event]
) -> set[str]:
    """Protect possible return origins of an unresolved recovery from modeled absence.

    Ordering may identify an ambiguous predecessor without proving attribution.
    When ordering is missing, protect every return in the recovery's period (or
    game if the period is missing), rather than treating uncertainty as absence.
    """
    drive = recovery.get("drive", {}).get("$ref")
    sequence = recovery.get("sequenceNumber")
    candidates = []
    if drive and isinstance(sequence, str) and sequence.isdigit():
        if int(sequence) > 1:
            candidates = [
                play
                for play in plays
                if play.get("drive", {}).get("$ref") == drive
                and play.get("sequenceNumber") == str(int(sequence) - 1)
            ]
        elif sequence == "1":
            match = re.fullmatch(r"(.*/drives/)(\d+)(?:\?.*)?", drive)
            if match:
                previous = [
                    play
                    for play in plays
                    if re.fullmatch(
                        re.escape(match[1]) + str(int(match[2]) - 1) + r"(?:\?.*)?",
                        play.get("drive", {}).get("$ref", ""),
                    )
                ]
                if previous and all(
                    isinstance(play.get("sequenceNumber"), str) and play["sequenceNumber"].isdigit()
                    for play in previous
                ):
                    final = max(int(play["sequenceNumber"]) for play in previous)
                    candidates = [play for play in previous if int(play["sequenceNumber"]) == final]
    if candidates and all(play["id"] in events for play in candidates):
        return {
            play["id"]
            for play in candidates
            if play["id"] in events and events[play["id"]].kind in _RETURN
        }
    period = recovery.get("period", {}).get("number")
    return {
        event.event_id
        for event in events.values()
        if event.kind in _RETURN
        and (type(period) is not int or period < 1 or event.period == period)
    }


def project_game(
    events: Sequence[Event],
    plays: Sequence[Mapping[str, Any]],
    *,
    relax_clock: bool = False,
    model_return_denominator: bool = False,
) -> tuple[list[Event], dict[str, Any]]:
    """Project source links and optional same-carrier clock-disagreement links.

    Unlinked recovery rows are omitted from fitting. Potential primary predecessors
    of unresolved rows retain unknown presence. Other ordinary primary rows use an
    explicitly modeled narrative-incidence denominator, never a source truth claim.
    The return denominator is separately opt-in and protects possible unresolved
    return origins. Known standalone primary facts remain available for fitting.
    """
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("duplicate normalized event identifier")
    if len({(event.season, event.game_id) for event in events}) > 1:
        raise ValueError("supply normalized events for exactly one game")
    events, return_report = enrich_return_fumbles(events, plays)
    events, primary_report = enrich_primary_fumbles(events, plays)
    source = {event.event_id: event for event in events}
    raw = {str(row["id"]): row for row in plays}
    diagnosis = audit_game(plays)
    links = [dict(link, basis="strict-source-link") for link in diagnosis["candidate_links"]]
    by_sequence: dict[tuple[str | None, str | None], list[Mapping[str, Any]]] = defaultdict(list)
    for row in plays:
        by_sequence[(row.get("drive", {}).get("$ref"), row.get("sequenceNumber"))].append(row)
    uncertain = set()
    uncertain_returns = set()
    unresolved = []
    for issue in diagnosis["unresolved"]:
        recovery = raw[issue["recovery"]]
        number = recovery.get("sequenceNumber", "")
        previous = (
            by_sequence.get((recovery.get("drive", {}).get("$ref"), str(int(number) - 1)), [])
            if isinstance(number, str) and number.isdigit()
            else []
        )
        predecessor = source.get(previous[0]["id"]) if len(previous) == 1 else None
        paired = False
        if predecessor is not None and predecessor.kind in {"rush", "complete", "sack"}:
            # Preserve ambiguity even when the carrier cannot be safely associated.
            uncertain.add(predecessor.event_id)
            fumbler = re.search(r"fumble by (.+?) \([^)]+\)", recovery.get("text") or "", re.I)
            pattern = (
                r"complete to (.+?) \([^)]+\)"
                if predecessor.kind == "complete"
                else r"^(.+?) \([^)]+\) (?:rushed|sacked)"
            )
            carrier = re.search(pattern, predecessor.source_text, re.I)
            recovering = source.get(issue["recovery"])
            if (
                relax_clock
                and issue["reason"] == "clock_or_period_disagreement"
                and predecessor.yards is not None
                and recovering is not None
                and recovering.period is not None
                and recovering.period == predecessor.period
                and recovering.team == predecessor.team
                and fumbler is not None
                and carrier is not None
                and fumbler[1].casefold() == carrier[1].casefold()
            ):
                links.append(
                    {
                        "primary": predecessor.event_id,
                        "recovery": issue["recovery"],
                        "kind": previous[0]["type"]["text"],
                        "basis": "modeled-clock-disagreement",
                    }
                )
                paired = True
        if not paired:
            unresolved.append(issue)
            recovering = source.get(issue["recovery"])
            if recovering is None or recovering.kind not in {"rush", "complete", "sack"}:
                uncertain_returns.update(_possible_return_predecessors(recovery, plays, source))
    if len({link["primary"] for link in links}) != len(links):
        raise ValueError("multiple recovery links cannot share a modeled primary event")
    projections = {}
    for link in links:
        primary = source.get(link["primary"])
        recovery = source.get(link["recovery"])
        if primary is None or recovery is None:
            raise ValueError("source link has no corresponding normalized event")
        projections[primary.event_id] = _modeled(
            primary,
            fumble=True,
            fumble_count=1,
            fumble_team=primary.team,
            recovery_team=recovery.recovery_team,
            fumble_lost=(recovery.recovery_team != primary.team)
            if recovery.recovery_team is not None
            else None,
            recovery_policy=recovery.recovery_policy,
            provider_recovery_team=recovery.provider_recovery_team,
            recovery_confidence=recovery.recovery_confidence,
            recovery_evidence=(*recovery.recovery_evidence, link["basis"], link["recovery"]),
        )
    recovery_ids = (
        {link["recovery"] for link in links}
        | {issue["recovery"] for issue in unresolved}
        | {link["recovery"] for link in diagnosis["return_links"]}
    )
    modeled = []
    negatives = []
    negative_returns = []
    retained_standalone = []
    omitted_recoveries = []
    for event in events:
        if event.event_id in projections:
            modeled.append(projections[event.event_id])
        elif event.event_id in recovery_ids:
            if (
                event.kind in {"rush", "complete", "sack"}
                and event.fumble is True
                and event.yards is not None
                and not event.no_play
                and not event.penalty
                and event.event_phase != "try"
            ):
                modeled.append(event)
                retained_standalone.append(event.event_id)
            else:
                modeled.append(_modeled(event, no_play=True))
                omitted_recoveries.append(event.event_id)
        elif (
            model_return_denominator
            and event.kind in _RETURN
            and event.return_yards is not None
            and not event.no_play
            and not event.penalty
            and event.event_phase != "try"
            and event.fumble is None
            and event.event_id not in uncertain_returns
        ):
            modeled.append(_modeled(event, fumble=False, fumble_count=0))
            negative_returns.append(event.event_id)
        elif (
            event.kind in _PRIMARY
            and not event.no_play
            and event.event_phase != "try"
            and event.fumble is None
            and event.event_id not in uncertain
        ):
            modeled.append(_modeled(event, fumble=False, fumble_count=0))
            negatives.append(event.event_id)
        else:
            modeled.append(event)
    return modeled, {
        "policy": POLICY,
        "relax_clock": relax_clock,
        "strict_links": len(diagnosis["candidate_links"]),
        "cross_drive_primary_links": len(primary_report["links"]),
        "fallback_links": len(links) - len(diagnosis["candidate_links"]),
        "special_teams_links": sum(
            link["family"] in {"punt_return", "kickoff_return"} for link in return_report["links"]
        ),
        "interception_return_links": sum(
            link["family"] == "interception_return" for link in return_report["links"]
        ),
        "return_fumble_links": len(return_report["links"]),
        "return_links": return_report["links"],
        "links": links,
        "unresolved_recoveries": len(unresolved),
        "unresolved": unresolved,
        "modeled_negative_primary_rows": len(negatives),
        "modeled_negative_primary_ids": negatives,
        "model_return_denominator": model_return_denominator,
        "modeled_negative_return_rows": len(negative_returns),
        "modeled_negative_return_ids": negative_returns,
        "uncertain_return_ids": sorted(uncertain_returns),
        "retained_standalone_primary_rows": len(retained_standalone),
        "retained_standalone_primary_ids": retained_standalone,
        "omitted_recovery_rows": len(omitted_recoveries),
        "denominator_policy": "modeled-linked-narrative-incidence; unresolved predecessors unknown",
        "return_denominator_policy": (
            "modeled-linked-narrative-incidence; possible unresolved return origins unknown"
            if model_return_denominator
            else "disabled; preserve source return presence"
        ),
        "source_negative_observations_established": False,
        "source_truth_verified": False,
        "publication_authorized": False,
    }


def main() -> int:
    """Compare strict and modeled-clock fitting views and optional candidate builds."""
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("source", "plays", "teams", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument(
        "--model-return-denominator",
        action="store_true",
        help="opt in to a fitting-only modeled return narrative-incidence denominator",
    )
    args = parser.parse_args()
    destination = private_destination(args.output)
    destination.mkdir(parents=True, exist_ok=False)
    source_bytes = args.source.read_bytes()
    events, provenance = read_normalized(args.source)
    teams = json.loads(args.teams.read_text())
    grouped: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        grouped[event.game_id].append(event)
    raw_games = {}
    for game in grouped:
        path = args.plays / f"plays-{game}.json"
        if not path.exists():
            path = args.plays / f"{game}.json"
        raw_bytes = path.read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest() != provenance["game_source_sha256"][game]:
            raise ValueError("raw play response differs from normalized source receipt")
        raw_games[game] = json.loads(raw_bytes)["items"]
    result = {
        "policy": POLICY,
        "source_file_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_primary_coverage": primary_source_coverage(events),
        "generator_model_changed": False,
        "historical_fit": "UNVERIFIED",
        "publication_authorized": False,
        "model_return_denominator": args.model_return_denominator,
        "known_source_disagreement_games": ["222710194"] if "222710194" in grouped else [],
        "variants": {},
    }
    for name, relaxed in (("strict-links", False), ("clock-fallback", True)):
        modeled, game_reports = [], {}
        for game, source_events in grouped.items():
            projected, receipt = project_game(
                source_events,
                raw_games[game],
                relax_clock=relaxed,
                model_return_denominator=args.model_return_denominator,
            )
            modeled.extend(projected)
            game_reports[game] = receipt
        counts: Counter[str] = Counter()
        for receipt in game_reports.values():
            for key in (
                "strict_links",
                "cross_drive_primary_links",
                "fallback_links",
                "special_teams_links",
                "interception_return_links",
                "return_fumble_links",
                "unresolved_recoveries",
                "modeled_negative_primary_rows",
                "modeled_negative_return_rows",
                "retained_standalone_primary_rows",
                "omitted_recovery_rows",
            ):
                counts[key] += receipt[key]
        report = {
            "counts": dict(counts),
            "primary_coverage": primary_source_coverage(modeled),
            "team_primary_coverage": {
                team: primary_source_coverage([event for event in modeled if event.team == team])
                for team in teams
            },
            "games": game_reports,
        }
        if args.generate:
            try:
                generation = generate_release_cohort(
                    modeled, teams, 2002, destination / name, seed=1
                )
                report["generation"] = {
                    "status": generation["status"],
                    "completed_teams": len(generation["teams"]),
                }
            except (ValueError, OSError, TypeError, RuntimeError) as error:
                report["generation"] = {"status": "failed", "error": str(error)}
        result["variants"][name] = report
        (destination / "experiment.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            name,
            json.dumps({"counts": report["counts"], "generation": report.get("generation")}),
            flush=True,
        )
    if args.source.read_bytes() != source_bytes:
        raise ValueError("normalized source changed during experiment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
