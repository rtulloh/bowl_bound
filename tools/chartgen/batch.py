"""Cached, deterministic phase-one generation with explicit per-team failures."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bowl_bound.models import TeamChart
from bowl_bound.team_csv import TeamFileMetadata, team_folder_name, team_to_files

from .evidence import Event
from .generate import (
    CalibrationProfile,
    DefensiveProfile,
    EvidenceModel,
    generate_team,
    write_bundle,
)
from .private_io import private_destination
from .tactics import TacticalProfile


def bundle_hash(chart: TeamChart, metadata: TeamFileMetadata) -> str:
    """Hash normalized reloadable chart content independently of artifact ordering."""
    return hashlib.sha256(
        json.dumps(team_to_files(chart, metadata), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_json_new(path: Path, payload: Any) -> None:
    """Exclusively write an owner-only artifact; never replace an earlier record."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def generate_cohort(
    events: Sequence[Event],
    teams: Mapping[str, str],
    season: int,
    output: Path,
    *,
    seed: int = 1,
    profiles: Mapping[str, CalibrationProfile] | None = None,
    defensive_profiles: Mapping[str, DefensiveProfile] | None = None,
    tactics: TacticalProfile | None = None,
    model: EvidenceModel | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Fit source once, preserve individual errors, and load no external team charts."""
    output = private_destination(output)
    if output.exists():
        raise ValueError("cohort generation requires a new output path")
    slugs = [team_folder_name(name) for name in teams.values()]
    if len(set(slugs)) != len(slugs):
        raise ValueError("cohort team names collide in the catalog")
    model = model or EvidenceModel.from_events(events)
    if model.events is not events and model.events != tuple(events):
        raise ValueError("cached model differs from supplied evidence")
    output.mkdir(parents=True, mode=0o700)
    records = {}
    for index, (team, name) in enumerate(sorted(teams.items())):
        profile = (profiles or {}).get(team, CalibrationProfile())
        defense = (defensive_profiles or {}).get(team, DefensiveProfile())
        record = {
            "name": name,
            "catalog_id": f"{season}/{team_folder_name(name)}",
            "profile": asdict(profile),
            "defensive_profile": asdict(defense),
        }
        try:
            bundle = generate_team(
                model.events,
                team,
                name,
                season,
                seed=seed,
                profile=profile,
                defensive_profile=defense,
                tactics=tactics,
                model=model,
            )
            write_bundle(output, bundle)
            record.update(
                state="generated",
                source_summary=bundle[2]["source_summary"],
                source_sha256=bundle[2]["source_sha256"],
                bundle_sha256=bundle_hash(*bundle[:2]),
            )
        except ValueError as error:
            record.update(state="unidentifiable", reason=str(error))
        records[team] = record
        if progress:
            progress(index + 1, len(teams), team)
    result = {
        "season": season,
        "seed": seed,
        "source_sha256": model.source_hash,
        "teams": records,
        "source_context": "all supplied observed historical events",
    }
    write_json_new(output / "cohort-generation.json", result)
    return result
