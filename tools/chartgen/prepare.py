"""Phase-one batch generation and reviewable actual historical fixture contracts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .batch import generate_cohort, write_json_new
from .cohort_report import canonical_hash, write_matchup_report
from .cohort_sources import HistoricalContracts
from .evidence import Event
from .generate import CalibrationProfile, DefensiveProfile, EvidenceModel
from .private_io import private_destination
from .refine import engine_identity
from .scope import LIVE_KINDS, MAJOR_CONFERENCES, build_slate, qualified_games, slate_targets
from .tactics import TacticalProfile


def prepare_cohort(
    events: Sequence[Event],
    contracts: HistoricalContracts,
    season: int,
    output: Path,
    *,
    source_provenance: Mapping[str, Any],
    minimum_source_games: int = 6,
    seed: int = 1,
    tactics: TacticalProfile | None = None,
    benchmark_ids: frozenset[str] = frozenset(),
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Generate evidence-qualified FBS charts; freeze a proposed slate for review.

    Six sequence-screened games is a declared engineering eligibility floor, not
    proof of complete coverage or sufficient calibration exposure. Source effects
    condition on all completed screened fixtures, including observed external
    opponents. Calibration targets condition only on the narrower selected slate.
    """
    output = private_destination(output)
    if output.exists():
        raise ValueError("cohort preparation requires a new output path")
    if type(minimum_source_games) is not int or minimum_source_games < 1:
        raise ValueError("minimum source games must be a positive integer")
    if any(e.season != season for e in events):
        raise ValueError("cohort evidence contains a different season")
    evidence = qualified_games(events, contracts.games)
    conditioning_ids = {
        g.game_id for g in contracts.games if g.completed and evidence[g.game_id]["qualified"]
    }
    model_events = tuple(e for e in events if e.game_id in conditioning_ids)
    if not model_events:
        raise ValueError("no sequence-qualified source games; cannot invent a cohort")
    model = EvidenceModel.from_events(model_events)
    by_team: dict[str, list[Event]] = defaultdict(list)
    team_ids: dict[str, set[str]] = defaultdict(set)
    for event in model_events:
        by_team[event.team].append(event)
        team_ids[event.team].add(event.game_id)
        team_ids[event.opponent].add(event.game_id)
    qualifications, requested = {}, {}
    for team, member in contracts.members.items():
        own = [e for e in by_team[team] if not e.no_play]
        live = [e for e in own if e.kind in LIVE_KINDS]
        rush = sum(e.kind == "rush" and e.yards is not None for e in live)
        complete = sum(e.kind == "complete" and e.yards is not None for e in live)
        passes = sum(e.kind in {"complete", "incomplete", "interception", "sack"} for e in live)
        reasons = []
        if member.subdivision != "fbs":
            reasons.append("external_non_fbs_chart_not_requested")
        if len(team_ids[team]) < minimum_source_games:
            reasons.append("too_few_sequence_screened_source_games")
        if rush < 30 or complete < 30 or passes < 30:
            reasons.append("sparse_primary_play_evidence")
        record = {
            "state": "insufficient_evidence" if reasons else "source_qualified",
            "reasons": reasons,
            "sequence_screened_source_games": len(team_ids[team]),
            "known_rush_samples": rush,
            "known_completion_samples": complete,
            "dropback_samples": passes,
            "minimum_source_games": minimum_source_games,
            "role": "major_core"
            if member.conference in MAJOR_CONFERENCES
            else "eligible_outer_fbs"
            if member.subdivision == "fbs"
            else "external_context",
            "benchmark_status": "authorized_private_reference_available"
            if team in benchmark_ids
            else "not_a_reference_benchmark",
            "historical_completeness_claim": False,
            "independent_official_corroboration": member.independently_corroborated,
        }
        qualifications[team] = record
        if not reasons:
            requested[team] = member.name
    output.mkdir(parents=True, mode=0o700)
    generated = generate_cohort(
        model.events,
        requested,
        season,
        output / "charts",
        seed=seed,
        model=model,
        tactics=tactics,
        progress=progress,
    )
    available = set()
    for team, record in generated["teams"].items():
        qualifications[team].update(record)
        if record["state"] == "generated":
            available.add(team)
    slate = build_slate(
        contracts.games,
        contracts.members,
        generated_teams=available,
        game_evidence=evidence,
        season=season,
    )
    targets = slate_targets(events, slate)
    source = {
        "raw_normalized_provenance": dict(source_provenance),
        "historical_contracts": dict(contracts.provenance),
        "strength_model_source_sha256": model.source_hash,
        "strength_model_game_ids": sorted(conditioning_ids),
        "strength_model_scope": (
            "all completed sequence-screened actual fixtures, including external opponents"
        ),
        "target_scope": "exact selected historical fixtures only; no full-season fit claim",
        "sequence_policy": (
            "four periods, >=20 live plays per side, known primary yards; "
            "terminal clock uncertainty explicit"
        ),
        "qualification_is_official_completeness": False,
        "independent_membership_confirmation": contracts.independent_membership_confirmation,
        "tactics": (tactics or TacticalProfile.neutral()).to_dict(),
    }
    report = write_matchup_report(
        output / "review",
        slate,
        targets,
        source=source,
        engine=engine_identity(),
        profiles_sha256=canonical_hash(
            {
                t: {"offense": asdict(CalibrationProfile()), "defense": asdict(DefensiveProfile())}
                for t in available
            }
        ),
        chart_qualifications=qualifications,
    )
    result = {
        "season": season,
        "generated_teams": len(available),
        "requested_teams": len(requested),
        "selected_fixtures": len(slate.games),
        "excluded_fixtures": len(slate.excluded),
        "teams_with_selected_games": sum(bool(ids) for ids in slate.team_games.values()),
        "strength_model_games": len(conditioning_ids),
        "manifest_sha256": report["manifest_sha256"],
        "report_directory": str(output / "review"),
        "chart_directory": str(output / "charts"),
        "stage": "proposed_slate_requires_owner_review_before_broad_calibration",
        "historical_completeness_claim": False,
    }
    write_json_new(output / "qualification.json", evidence)
    write_json_new(output / "preparation.json", result)
    return result
