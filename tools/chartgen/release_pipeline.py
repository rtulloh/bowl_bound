"""Public, reproducible development pipeline; source evidence stays local."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bowl_bound.models import TeamChart
from bowl_bound.team_csv import TeamFileMetadata, load_team, team_folder_name, team_from_files
from scripts import audit_generated_charts as audit

from ..chart_depth_pipeline import finalize_depth_files
from .alpha_export import encode_standard_cohort
from .cohort_model import SUPPORTED_SEASONS, TOOL_VERSION, apply_cohort_model, model_identity
from .evidence import Event
from .generate import EvidenceModel, generate_team
from .private_io import private_destination
from .research_inputs import semantic_sha256
from .tactics import APPROVED_YARDAGE_POLICY_SHA256, TacticalProfile


def _write_files(root: Path, key: str, files: Mapping[str, str]) -> dict[str, str]:
    pins = {}
    season, slug = key.split("/")
    for name, text in sorted(files.items()):
        relative = (
            f"seasons/{season}/provenance/{slug}.csv"
            if name == "provenance.csv"
            else f"seasons/{key}/{name}"
        )
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = text.encode("utf-8")
        with destination.open("xb") as stream:
            stream.write(payload)
        pins[relative] = hashlib.sha256(payload).hexdigest()
    return pins


def _baseline_files(chart: TeamChart, metadata: TeamFileMetadata) -> dict[str, str]:
    from bowl_bound.team_csv import provenance_to_csv, team_to_files

    return {**team_to_files(chart, metadata), "provenance.csv": provenance_to_csv(chart, metadata)}


def generate_release_cohort(
    events: Sequence[Event],
    teams: Mapping[str, str],
    season: int,
    output: Path,
    *,
    seed: int = 1,
) -> dict[str, Any]:
    """Generate a new candidate and verify it without granting release approval.

    Source membership/coverage, source rights, independent source qualification,
    game panels and final release acceptance remain separate. A failure preserves
    partial files and a failure receipt; it never reports a partial cohort green.
    """
    destination = private_destination(output)
    if destination.exists():
        raise FileExistsError("generation requires a new output directory")
    if type(season) is not int or season not in SUPPORTED_SEASONS:
        raise ValueError("supported generation seasons are 2002 and 2007")
    if not teams or any(type(k) is not str or not k for k in teams):
        raise ValueError("supply at least one stable source team ID")
    slugs = []
    for name in teams.values():
        if type(name) is not str or not name.strip() or any(c in name for c in "/\\\0"):
            raise ValueError("team name must be a nonempty display name without path separators")
        slug = team_folder_name(name)
        if not slug or not slug[0].isalnum():
            raise ValueError("team name must produce a safe chart directory")
        slugs.append(slug)
    if len(set(slugs)) != len(slugs):
        raise ValueError("team names must produce unique chart directories")
    snapshot = tuple(events)
    model = EvidenceModel.from_events(snapshot)
    if model.seasons != {season}:
        raise ValueError("source season differs from requested cohort season")
    if not set(teams) <= set(model.by_team):
        raise ValueError("requested team has no source events")
    source_identity = semantic_sha256(tuple(asdict(event) for event in snapshot))
    identity = model_identity()
    compact_identity = {k: v for k, v in identity.items() if k != "contract"}
    compact_identity.update(tool_version=TOOL_VERSION, source_sha256=source_identity)
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "incomplete",
        "season": season,
        "seed": seed,
        "source_sha256": source_identity,
        "model_identity": compact_identity,
        "compiled_model": identity,
        "teams": {},
        "output_pins": {},
        "baseline_pins": {},
        "historical_fit": "UNVERIFIED",
        "source_truth_revalidated": False,
        "publication_authorized": False,
    }
    destination.mkdir(parents=True)
    try:
        for team, name in sorted(teams.items()):
            key = f"{season}/{team_folder_name(name)}"
            baseline, metadata, generation = generate_team(
                snapshot,
                team,
                name,
                season,
                seed=seed,
                model=model,
                tactics=TacticalProfile.for_corrected_release(APPROVED_YARDAGE_POLICY_SHA256),
            )
            baseline_files = _baseline_files(baseline, metadata)
            report["baseline_pins"].update(
                _write_files(destination / "baseline", key, baseline_files)
            )
            defensive_events = tuple(e for e in model.live if e.opponent == team)
            interceptions = tuple(e for e in defensive_events if e.kind == "interception")
            known = Counter(
                e.interception_yards if e.interception_yards is not None else e.air_yards
                for e in interceptions
                if e.interception_yards is not None or e.air_yards is not None
            )
            candidate, producer = apply_cohort_model(
                baseline,
                known_depths=tuple(sorted(known.items())),
                unknown_locations=len(interceptions) - sum(known.values()),
                source_identity=source_identity,
            )
            if producer["status"] != "represented":
                raise ValueError(f"allocation refused {key}; inspect retained generation receipt")
            files, export = encode_standard_cohort(
                candidate,
                metadata,
                producer,
                expected_baseline_sha256=semantic_sha256(baseline),
                source_sha256=source_identity,
            )
            files, depth = finalize_depth_files(
                files,
                tuple(e for e in model.live if e.team == team),
                defensive_events,
                source_sha256=source_identity,
                parent_model_sha256=str(identity["sha256"]),
            )
            final, final_metadata = team_from_files(
                {k: v for k, v in files.items() if k != "provenance.csv"}, files["provenance.csv"]
            )
            semantic_audit = audit._audit_budget(
                final,
                final_metadata,
                audit._budget_record(baseline, metadata, ignore_int_depths=True),
                key,
                ignore_int_depths=True,
            )
            report["output_pins"].update(_write_files(destination, key, files))
            loaded, actual_metadata = load_team(
                destination / "seasons" / str(season), key.split("/")[1]
            )
            if (loaded, actual_metadata) != (final, final_metadata):
                raise ValueError("ordinary file load differs from qualified candidate")
            report["teams"][key] = {
                "source_team_id": team,
                "baseline": {
                    "tactical_policy_sha256": APPROVED_YARDAGE_POLICY_SHA256,
                    "generation": generation,
                },
                "allocation": producer,
                "export": export,
                "depth": depth,
                "semantic_audit": semantic_audit,
                "loaded_chart_sha256": semantic_sha256(loaded),
                "loaded_metadata_sha256": semantic_sha256(actual_metadata),
            }
        if semantic_sha256(tuple(asdict(event) for event in events)) != source_identity:
            raise ValueError("source changed during generation")
        for root, pins in (
            (destination, report["output_pins"]),
            (destination / "baseline", report["baseline_pins"]),
        ):
            release = root / "release"
            release.mkdir()
            (release / "manifest.json").write_text(
                json.dumps({"generated_sha256": pins}, indent=2) + "\n"
            )
            audit._catalog(root)
        report["status"] = "complete"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        # JSON normalization also makes in-memory and retained receipts identical.
        receipt = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (destination / "generation-receipt.json").write_text(receipt)
    return json.loads(receipt)
