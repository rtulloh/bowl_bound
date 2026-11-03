"""Regularized per-team residual profiles and separate source-game diagnostics."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bowl_bound.team_csv import load_team

from .artifacts import ArtifactCompression, check_capacity, storage_policy
from .batch import bundle_hash, generate_cohort, write_json_new
from .cohort_report import canonical_hash, validate_simulation_fixtures
from .cohort_run_report import write_matchup_usage
from .cohort_simulation import run_historical_batch
from .evidence import Event
from .generate import CalibrationProfile, DefensiveProfile, EvidenceModel
from .private_io import private_destination
from .refine import TOLERANCES, engine_identity, propose_profile
from .scope import CORE_METRICS
from .tactics import TacticalProfile

MINIMUM_UPDATE_SAMPLES = 250
SHRINKAGE_PSEUDO_SAMPLES = 1000
JOINT_STEP = 0.5


def profile_bounds() -> dict[str, dict[str, list[float]]]:
    """JSON-ready bounds recorded before any historical candidate observations."""
    offensive = {
        name: [-0.15, 0.15] if name.endswith("shift") else [0.6, 1.4]
        for name in asdict(CalibrationProfile())
    }
    defensive = {}
    for name in asdict(DefensiveProfile()):
        bound = 2.0 if name.endswith("offset") else 0.08 if name == "completion_shift" else 0.03
        defensive[name] = [-bound, bound]
    return {"offense": offensive, "defense": defensive}


def source_game_partition(
    events: Sequence[Event], withheld_game_ids: set[str]
) -> tuple[tuple[Event, ...], tuple[Event, ...]]:
    """Exclude whole games globally, including rows where a team was the opponent."""
    if not withheld_game_ids or not withheld_game_ids <= {e.game_id for e in events}:
        raise ValueError("source holdout requires explicitly observed whole game IDs")
    train = tuple(e for e in events if e.game_id not in withheld_game_ids)
    heldout = tuple(e for e in events if e.game_id in withheld_game_ids)
    if not train:
        raise ValueError("source holdout leaves no training evidence")
    return train, heldout


def propose_team_profiles(
    offense: CalibrationProfile,
    defense: DefensiveProfile,
    measured_offense: Mapping[str, Mapping[str, Any]],
    measured_defense: Mapping[str, Mapping[str, Any]],
    target_offense: Mapping[str, float],
    target_defense: Mapping[str, float],
) -> tuple[CalibrationProfile, DefensiveProfile, dict[str, Any]]:
    """Half-step OFF/DEF updates with explicit source anchoring and sample shrinkage.

    These knobs are empirical residual corrections, not identified formations.
    A selected global candidate is assessed jointly; teams cannot independently
    cherry-pick opponents' profiles or use held-out outcomes to choose updates.
    """
    skipped = [
        f"{role}/source:{metric}"
        for role, target in (("offense", target_offense), ("defense", target_defense))
        for metric in sorted(CORE_METRICS - set(target))
    ]
    weights = {}
    usable = {}
    for role, measurements in (("offense", measured_offense), ("defense", measured_defense)):
        for metric, observation in measurements.items():
            source_targets = target_offense if role == "offense" else target_defense
            if metric not in source_targets:
                skipped.append(f"{role}/source:{metric}")
                continue
            n, value = observation.get("n", 0), observation.get("value")
            if n < MINIMUM_UPDATE_SAMPLES or value is None:
                skipped.append(f"{role}/{metric}")
                continue
            weights[role, metric] = JOINT_STEP * n / (n + SHRINKAGE_PSEUDO_SAMPLES)
            if role == "offense":
                usable[metric] = value
    candidate = propose_profile(offense, usable, dict(target_offense))
    values = asdict(offense)
    offense_knobs = {
        "run_yards_scale": "rush_yards_per_attempt",
        "pass_yards_scale": "pass_yards_per_attempt",
        "completion_shift": "completion",
        "interception_scale": "interception",
        "sack_scale": "sack",
        "fumble_scale": "fumble",
    }
    for knob, metric in offense_knobs.items():
        if ("offense", metric) in weights:
            values[knob] += weights["offense", metric] * (getattr(candidate, knob) - values[knob])
    returns = [
        (metric, observation)
        for metric, observation in measured_offense.items()
        if metric in target_offense
        and metric
        in {
            "drawn_punt_return_yards",
            "drawn_kickoff_return_yards",
            "drawn_interception_return_yards",
        }
        and ("offense", metric) in weights
        and observation["value"] > 0
    ]
    if returns:
        # One shared return knob cannot force independently incompatible return columns.
        ratio = sum(target_offense[m] / row["value"] for m, row in returns) / len(returns)
        weight = min(weights["offense", m] for m, _ in returns)
        proposal = max(0.6, min(1.4, values["return_yards_scale"] * max(0.5, min(2, ratio)) ** 0.5))
        values["return_yards_scale"] += weight * (proposal - values["return_yards_scale"])
    defense_values = asdict(defense)
    defense_knobs = {
        "rush_yards_per_attempt": ("run_yards_offset", 2.0, 0.5),
        "pass_yards_per_attempt": ("pass_yards_offset", 2.0, 0.5),
        "completion": ("completion_shift", 0.08, 0.5),
        "interception": ("interception_shift", 0.03, 0.5),
        "sack": ("sack_shift", 0.03, 0.5),
    }
    for metric, (knob, bound, gain) in defense_knobs.items():
        if metric in target_defense and ("defense", metric) in weights:
            residual = target_defense[metric] - measured_defense[metric]["value"]
            defense_values[knob] = max(
                -bound,
                min(bound, defense_values[knob] + gain * weights["defense", metric] * residual),
            )
    return (
        CalibrationProfile(**values),
        DefensiveProfile(**defense_values),
        {
            "minimum_update_samples": MINIMUM_UPDATE_SAMPLES,
            "shrinkage_pseudo_samples": SHRINKAGE_PSEUDO_SAMPLES,
            "joint_offense_defense_step": JOINT_STEP,
            "unidentifiable_or_sparse_metrics": sorted(set(skipped)),
            "update_weights": {"/".join(k): v for k, v in weights.items()},
            "limits": (
                "finite dice can leave bounded residuals unfit; "
                "no chart changes conceal engine defects"
            ),
        },
    )


def _candidate_charts(
    model: EvidenceModel,
    names: Mapping[str, str],
    season: int,
    destination: Path,
    offense: Mapping[str, CalibrationProfile],
    defense: Mapping[str, DefensiveProfile],
    tactics: TacticalProfile,
    generation_seed: int,
) -> tuple[dict[str, Any], dict[str, str], str]:
    """Generate once or verify every resumed chart against recorded source/profiles."""
    record_path = destination / "cohort-generation.json"
    if record_path.exists():
        generated = json.loads(record_path.read_text())
    else:
        generated = generate_cohort(
            model.events,
            names,
            season,
            destination,
            profiles=offense,
            defensive_profiles=defense,
            tactics=tactics,
            seed=generation_seed,
            model=model,
        )
    if (generated["source_sha256"], generated["season"], generated["seed"]) != (
        model.source_hash,
        season,
        generation_seed,
    ):
        raise ValueError("candidate generation source/season/seed differs")
    if set(generated["teams"]) != set(names):
        raise ValueError("candidate team set differs from the selected historical endpoints")
    teams, catalog, fingerprints = {}, {}, {}
    for identity, record in generated["teams"].items():
        if record["state"] != "generated":
            raise ValueError("historical candidate retains an unidentifiable required chart")
        if record["profile"] != asdict(offense[identity]) or record["defensive_profile"] != asdict(
            defense[identity]
        ):
            raise ValueError("candidate profiles differ from the deterministic refinement history")
        key = record["catalog_id"]
        team = load_team(destination / str(season), key.split("/", 1)[1])
        fingerprint = bundle_hash(*team)
        if fingerprint != record["bundle_sha256"]:
            raise ValueError("candidate chart checksum differs; preserve evidence and investigate")
        teams[key], catalog[identity], fingerprints[identity] = team, key, fingerprint
    return teams, catalog, canonical_hash(fingerprints)


def _joint_assessment(summary: Mapping[str, Any]) -> tuple[bool, float]:
    records = [v for v in summary["per_source_team"].values() if v["game_ids"]]
    losses = [
        sum(
            v[role]["loss"] / max(1, len(v[role]["metrics"]))
            + 100 * len(v[role]["unidentifiable_source_metrics"])
            for role in ("offense_assessment", "defense_assessment")
        )
        / 2
        for v in records
    ]
    passed = bool(records) and all(
        v[role]["passed"] for v in records for role in ("offense_assessment", "defense_assessment")
    )
    return passed, sum(losses) / len(losses) if losses else 10000.0


def run_cohort_refinement(
    events: Sequence[Event],
    report: Mapping[str, Any],
    targets: Mapping[str, Mapping[str, Any]],
    output: Path,
    *,
    reviewed_manifest_sha256: str,
    training_repetitions: int = 4,
    validation_repetitions: int = 8,
    coaching_repetitions: int = 1,
    iterations: int = 3,
    master_seed: int = 20081103,
    generation_seed: int = 1,
    workers: int = 1,
    compression: ArtifactCompression = ArtifactCompression.JSON,
    tactics: TacticalProfile | None = None,
    resume: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Select a globally coherent training candidate, then validate without retuning.

    Exact fixture review is an owner-requested checkpoint. Matching the supplied
    hash makes the concrete operator choice reviewable; it is not inferred from
    elapsed time or merely possessing a report file.
    """
    from .scope import HistoricalGame

    output = private_destination(output)
    compression = ArtifactCompression(compression)
    if reviewed_manifest_sha256 != report["manifest_sha256"]:
        raise ValueError("reviewed manifest hash differs from concrete proposed slate")
    if canonical_hash(targets) != report.get("targets_sha256"):
        raise ValueError("restricted target hash differs from frozen review manifest")
    games = [HistoricalGame(**g) for g in report["games"]]
    validate_simulation_fixtures(report, games, repetitions=1)
    if not games:
        raise ValueError("no selected historical fixtures; review coverage/exclusions first")
    if any(
        type(v) is not int or v < 1
        for v in (training_repetitions, validation_repetitions, coaching_repetitions)
    ):
        raise ValueError("all cohort repetition counts must be positive integers")
    if type(iterations) is not int or not 1 <= iterations <= 8:
        raise ValueError("cohort iteration bound must be within [1, 8]")
    if type(workers) is not int or not 1 <= workers <= 2:
        raise ValueError("cohort workers must be within [1, 2]")
    identity = engine_identity()
    if report["engine"].get("engine_sha256") != identity["engine_sha256"]:
        raise ValueError("review slate engine differs; regenerate/review before calibration")
    conditioning_ids = set(report["source"]["strength_model_game_ids"])
    evidence = tuple(e for e in events if e.game_id in conditioning_ids)
    model = EvidenceModel.from_events(evidence)
    if model.source_hash != report["source"]["strength_model_source_sha256"]:
        raise ValueError("source model hash differs from historical review contract")
    tactics = tactics or TacticalProfile.neutral()
    if tactics.to_dict() != report["source"]["tactics"]:
        raise ValueError("tactical prior differs from baseline review contract")
    names = {
        team: entry["name"]
        for team, entry in report["teams"].items()
        if entry["offensive_game_ids"]
    }
    config = {
        "manifest_sha256": report["manifest_sha256"],
        "engine": identity,
        "source_sha256": model.source_hash,
        "targets_sha256": canonical_hash(targets),
        "training_repetitions": training_repetitions,
        "validation_repetitions": validation_repetitions,
        "coaching_repetitions": coaching_repetitions,
        "iterations": iterations,
        "master_seed": master_seed,
        "generation_seed": generation_seed,
        "tactics_sha256": tactics.sha256,
        "artifact_storage_policy": storage_policy(compression),
        "tolerances": TOLERANCES,
        "profile_bounds": profile_bounds(),
        "statistical_gate_scope": (
            "six identified core OFF/DEF metrics plus source-available special-team targets; "
            "aggregate field-goal opportunity mix and designed tactical calls are not identified"
        ),
        "engine_rules_scope": (
            "current approved Bowl Bound; source years identify evidence, "
            "not historical NCAA rule emulation"
        ),
        "minimum_training_samples": 1000,
        "minimum_validation_samples": 2000,
        "minimum_update_samples": MINIMUM_UPDATE_SAMPLES,
        "shrinkage_pseudo_samples": SHRINKAGE_PSEUDO_SAMPLES,
    }
    if output.exists():
        if not resume or json.loads((output / "cohort-run-config.json").read_text()) != config:
            raise ValueError("cohort resume configuration differs or output already exists")
    else:
        capacity = check_capacity(
            output,
            len(games)
            * (iterations * training_repetitions + validation_repetitions + coaching_repetitions),
            compression=compression,
        )
        output.mkdir(parents=True, mode=0o700)
        write_json_new(output / "cohort-run-config.json", config)
        write_json_new(output / "cohort-storage-preflight.json", capacity)
    offense = {t: CalibrationProfile() for t in names}
    defense = {t: DefensiveProfile() for t in names}
    history, best, previous_fingerprint = [], None, None
    stopping = "predeclared iteration bound"
    for index in range(iterations):
        path = output / f"candidate-{index:02d}"
        teams, catalog, fingerprint = _candidate_charts(
            model,
            names,
            report["season"],
            path / "charts",
            offense,
            defense,
            tactics,
            generation_seed,
        )
        if fingerprint == previous_fingerprint:
            stopping = "unchanged finite-dice chart response"
            break
        summary = run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            path / "training",
            domain="training",
            repetitions=training_repetitions,
            master_seed=master_seed,
            workers=workers,
            compression=compression,
            resume=resume,
            progress=progress,
        )
        passed, loss = _joint_assessment(summary)
        profiles = {
            "offense": {t: asdict(v) for t, v in offense.items()},
            "defense": {t: asdict(v) for t, v in defense.items()},
        }
        history.append(
            {
                "candidate": index,
                "profiles": profiles,
                "summary": summary,
                "equal_team_joint_loss": loss,
                "all_team_gates_passed": passed,
                "chart_fingerprint": fingerprint,
            }
        )
        rank = (summary["failed_games"], loss)
        if best is None or rank < best[0]:
            best = (rank, index, dict(offense), dict(defense), fingerprint)
        if passed and not summary["failed_games"]:
            stopping = "all predeclared per-team training gates passed"
            break
        if summary["failed_games"]:
            stopping = "engine audit failure retained; do not compensate with chart strengths"
            break
        updated_offense, updated_defense, diagnostics = {}, {}, {}
        for team in names:
            observation = summary["per_source_team"][team]
            new_offense, new_defense, diagnostic = propose_team_profiles(
                offense[team],
                defense[team],
                observation["offense"]["metrics"],
                observation["defense"]["metrics"],
                targets[team]["offense"],
                targets[team]["defense"],
            )
            updated_offense[team], updated_defense[team], diagnostics[team] = (
                new_offense,
                new_defense,
                diagnostic,
            )
        history[-1]["proposal_diagnostics"] = diagnostics
        if updated_offense == offense and updated_defense == defense:
            stopping = "unchanged bounded profiles; sparse or unidentifiable residuals retained"
            break
        offense, defense, previous_fingerprint = updated_offense, updated_defense, fingerprint
    assert best is not None
    _, selected, offense, defense, fingerprint = best
    teams, catalog, _ = _candidate_charts(
        model,
        names,
        report["season"],
        output / f"candidate-{selected:02d}" / "charts",
        offense,
        defense,
        tactics,
        generation_seed,
    )
    heldout = run_historical_batch(
        report,
        teams,
        catalog,
        targets,
        output / "heldout",
        domain="heldout",
        repetitions=validation_repetitions,
        master_seed=master_seed,
        workers=workers,
        compression=compression,
        resume=resume,
        verify_replay=True,
        progress=progress,
    )
    coaching = run_historical_batch(
        report,
        teams,
        catalog,
        targets,
        output / "coaching-assessment",
        domain="coaching",
        repetitions=coaching_repetitions,
        master_seed=master_seed,
        workers=workers,
        compression=compression,
        resume=resume,
        progress=progress,
    )
    _, _, regenerated = _candidate_charts(
        model,
        names,
        report["season"],
        output / "playtest-charts",
        offense,
        defense,
        tactics,
        generation_seed,
    )
    identical = regenerated == fingerprint
    all_gates, heldout_loss = _joint_assessment(heldout)
    result = {
        "config": config,
        "training_history": history,
        "selected_candidate": selected,
        "selected_profiles": {
            "offense": {t: asdict(v) for t, v in offense.items()},
            "defense": {t: asdict(v) for t, v in defense.items()},
        },
        "heldout": heldout,
        "heldout_equal_team_joint_loss": heldout_loss,
        "coaching_assessment": coaching,
        "selected_regeneration_identical": identical,
        "mechanics_ready": not any(h["summary"]["failed_games"] for h in history)
        and not heldout["failed_games"]
        and not coaching["failed_games"]
        and identical,
        "all_team_statistical_gates_passed": all_gates,
        "historical_full_season_fit_claim": False,
        "source_holdout_claim": False,
        "stopping_rule": stopping,
        "scope": "reviewed actual restricted fixtures; fresh held-out simulation seeds only",
        "actual_used_fixture_ids": report["target_game_ids"],
        "total_completed_engine_runs": sum(h["summary"]["completed_runs"] for h in history)
        + heldout["completed_runs"]
        + coaching["completed_runs"],
    }
    result["matchup_usage"] = write_matchup_usage(
        output,
        report,
        [h["summary"] for h in history],
        heldout,
        coaching,
        selected_profiles=result["selected_profiles"],
    )
    destination = output / "cohort-refinement-report.json"
    if destination.exists():
        if json.loads(destination.read_text()) != result:
            raise ValueError("retained final refinement report differs from verified results")
    else:
        write_json_new(destination, result)
    return result
