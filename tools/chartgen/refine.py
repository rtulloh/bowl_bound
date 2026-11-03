"""Phase 2: bounded profiles assessed through the real engine, with held-out seeds.

The local-season audit supplies situation-aware, team-independent legal baseline
coaching and independent score/clock/state/statistics/trace reconciliation. This
module aggregates its structured facts; it contains no football simulation rules.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, variance
from typing import Any

from bowl_bound.models import TeamChart
from bowl_bound.team_csv import TeamFileMetadata, team_folder_name
from scripts.run_local_season import GameSpec, _play_one, stable_seed

from .evidence import Event, summarize_events
from .generate import CalibrationProfile, generate_team, write_bundle
from .private_io import private_destination
from .tactics import TacticalProfile

# Declared before pilot outcomes. These are experimental play-test tolerances,
# not evidence that the source is complete or an exact historical schedule fit.
TOLERANCES = {
    "completion": 0.035,
    "interception": 0.012,
    "sack": 0.015,
    "fumble": 0.01,
    "rush_yards_per_attempt": 0.5,
    "pass_yards_per_attempt": 0.7,
    "drawn_punt_yards": 3.0,
    "drawn_kickoff_yards": 3.0,
    "drawn_kickoff_return_yards": 3.0,
    "drawn_punt_return_yards": 3.0,
    "drawn_interception_return_yards": 5.0,
    "field_goal": 0.08,
    "pat": 0.04,
}


@dataclass(frozen=True)
class SeedPlan:
    master: int
    training_games: int
    validation_games: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value <= 0
            for value in (self.training_games, self.validation_games)
        ):
            raise ValueError("training and validation exposure must be positive integers")

    @property
    def training(self) -> tuple[int, ...]:
        return tuple(
            stable_seed(self.master, f"chart-training/{i}") for i in range(self.training_games)
        )

    @property
    def validation(self) -> tuple[int, ...]:
        return tuple(
            stable_seed(self.master, f"chart-heldout/{i}") for i in range(self.validation_games)
        )


def engine_identity() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for path in sorted((root / "bowl_bound").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()
    tool_digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        tool_digest.update(path.name.encode())
        tool_digest.update(path.read_bytes())
    tool_digest.update((root / "scripts" / "run_local_season.py").read_bytes())
    return {
        "git_commit": commit,
        "engine_sha256": digest.hexdigest(),
        "tool_sha256": tool_digest.hexdigest(),
        "rules_profile": "approved current Bowl Bound; Advanced II disabled",
        "training_policy": (
            "baseline-v1 calls/clock; baseline-v10 non-clock decisions; public observation only"
        ),
        "audit_runner": "scripts.run_local_season._play_one",
    }


def aggregate_games(
    results: Sequence[dict[str, Any]],
    *,
    team_filter: str | None = None,
) -> dict[str, Any]:
    """Retain failures and aggregate actual event denominators with game variance."""
    passed = [result for result in results if result["status"] == "passed"]
    counters: dict[str, list[tuple[float, int]]] = defaultdict(list)
    team_games: Counter[str] = Counter()
    calls: Counter[str] = Counter()
    scores, plays = [], []
    for result in passed:
        game_counters: dict[str, list[tuple[float, int]]] = defaultdict(list)
        for side, identity in result["teams"].items():
            if team_filter is not None and identity != team_filter:
                continue
            team_games[identity] += 1
            stat = result["final"]["statistics"][side]
            attempts = stat["passing_attempts"]
            rushing = stat["rushing_attempts"]
            for name, numerator, denominator in (
                ("completion", stat["completions"], attempts),
                ("interception", stat["interceptions"], attempts),
                ("sack", stat["sacks_taken"], attempts + stat["sacks_taken"]),
                ("rush_yards_per_attempt", stat["rushing_yards"], rushing),
                ("pass_yards_per_attempt", stat["passing_yards"], attempts),
            ):
                if denominator:
                    game_counters[name].append((numerator, denominator))
            logs = [
                row for row in result["engine_log"] if row["state_before"]["possession"] == side
            ]
            fumbles = sum(
                any(entry["section"] == "fumble_recovery" for entry in row["trace"])
                for row in logs
                if row["statistics"]["kind"] != "excluded"
            )
            if attempts + rushing:
                game_counters["fumble"].append((fumbles, attempts + rushing))
            scores.append(result["final"][f"{side}_score"])
            plays.append(attempts + rushing)
        for call in result["coaching_calls"]:
            if team_filter is not None and call["team_id"] != team_filter:
                continue
            calls[f"{call['role']}/{call['choice']}"] += 1
        for draw in result.get("normalized_chart_draws", ()):
            if team_filter is not None and draw["team_id"] != team_filter:
                continue
            if draw["yards"] is not None and draw["column"] in {
                "punt",
                "kickoff",
                "kickoff_return",
                "punt_return",
                "interception_return",
            }:
                game_counters[f"drawn_{draw['column']}_yards"].append((draw["yards"], 1))
        for row in result["engine_log"]:
            if (
                team_filter is not None
                and result["teams"][row["state_before"]["possession"]] != team_filter
            ):
                continue
            # Kicks and makes use engine-provided semantic outcomes and traces.
            if row["outcome"] in {"field_goal_good", "field_goal_missed"}:
                game_counters["field_goal"].append((row["outcome"] == "field_goal_good", 1))
            if row["outcome"] in {"pat_good", "pat_missed"}:
                game_counters["pat"].append((row["outcome"] == "pat_good", 1))
        # Both possessions and every return/kick in this game share one cluster.
        for name, samples in game_counters.items():
            counters[name].append((sum(n for n, _ in samples), sum(d for _, d in samples)))
    metrics = {}
    for name, samples in counters.items():
        numerator, denominator = sum(n for n, _ in samples), sum(d for _, d in samples)
        game_values = [n / d for n, d in samples]
        ratio = numerator / denominator
        clusters = len(samples)
        ratio_variance = (
            clusters
            / (clusters - 1)
            * sum((n - ratio * d) ** 2 for n, d in samples)
            / denominator**2
            if clusters > 1
            else None
        )
        metrics[name] = {
            "value": ratio,
            "n": denominator,
            "numerator": numerator,
            "clusters": clusters,
            "effective_sample_size": denominator**2 / sum(d**2 for _, d in samples),
            "variance": variance(game_values) if len(game_values) > 1 else 0.0,
            "standard_error": math.sqrt(ratio_variance) if ratio_variance is not None else None,
            "uncertainty_method": "independent-game cluster-robust ratio; Kish exposure",
        }
    output = {
        "passed_games": len(passed),
        "failed_games": len(results) - len(passed),
        "failure_types": dict(
            Counter(result.get("error") for result in results if result["status"] != "passed")
        ),
        "team_games": dict(team_games),
        "metrics": metrics,
        "call_distribution": dict(calls),
        "points_per_team_game": mean(scores) if scores else None,
        "offensive_plays_per_team_game": mean(plays) if plays else None,
    }
    if team_filter is None:
        output["per_team"] = {
            identity: aggregate_games(results, team_filter=identity) for identity in team_games
        }
    return output


def source_targets(events: Sequence[Event], teams: Sequence[str]) -> dict[str, float]:
    if any(
        e.team in teams
        and not e.no_play
        and e.kind in {"rush", "sack", "complete"}
        and e.yards is None
        for e in events
    ):
        raise ValueError(
            "calibration requires known primary-play yardage; reconcile evidence first"
        )
    summaries = [summarize_events(events, team) for team in teams]
    totals = {
        key: sum(summary[key] for summary in summaries)
        for key in (
            "rush_attempts",
            "rush_yards",
            "pass_attempts",
            "completions",
            "interceptions",
            "sacks",
            "pass_yards",
            "scrimmage_fumbles",
        )
    }
    attempts, rushes, sacks = totals["pass_attempts"], totals["rush_attempts"], totals["sacks"]
    if not attempts or not rushes:
        raise ValueError("calibration requires observed rushing and passing attempts")
    targets = {
        "completion": totals["completions"] / attempts,
        "interception": totals["interceptions"] / attempts,
        "sack": sacks / (attempts + sacks),
        "rush_yards_per_attempt": totals["rush_yards"] / rushes,
        "pass_yards_per_attempt": totals["pass_yards"] / attempts,
    }
    fumble_sample = [
        e
        for e in events
        if e.team in teams
        and not e.no_play
        and e.kind in {"rush", "complete", "incomplete", "interception", "sack"}
        and e.fumble is not None
    ]
    if fumble_sample:
        targets["fumble"] = sum(e.fumble is True for e in fumble_sample) / len(fumble_sample)
    for kind in ("punt", "kickoff"):
        values = [
            e.yards
            for e in events
            if e.team in teams and e.kind == kind and e.yards is not None and not e.no_play
        ]
        if values:
            targets[f"drawn_{kind}_yards"] = mean(values)
    for kind, column in (
        ("punt", "punt_return"),
        ("kickoff", "kickoff_return"),
        ("interception", "interception_return"),
    ):
        values = [
            e.return_yards
            for e in events
            if e.opponent in teams
            and e.kind == kind
            and e.return_yards is not None
            and not e.no_play
        ]
        if values:
            targets[f"drawn_{column}_yards"] = mean(values)
    pats = [
        e
        for e in events
        if e.team in teams and e.kind == "pat" and e.kick_good is not None and not e.no_play
    ]
    if pats:
        targets["pat"] = mean(e.kick_good for e in pats)
    return targets


def assess_metrics(
    measured: dict[str, dict[str, Any]],
    targets: dict[str, float],
    *,
    minimum_samples: int,
) -> dict[str, Any]:
    assessments = {}
    for name, target in targets.items():
        observation = measured.get(name, {})
        value = observation.get("value")
        required_samples = (
            min(100, minimum_samples)
            if name.startswith("drawn_") or name == "pat"
            else minimum_samples
        )
        insufficient = observation.get("n", 0) < required_samples
        error = abs(value - target) if value is not None else math.inf
        tolerance = TOLERANCES[name]
        assessments[name] = {
            "target": target,
            "observed": value,
            "absolute_error": error,
            "tolerance": tolerance,
            "insufficient_samples": insufficient,
            "required_samples": required_samples,
            "passed": not insufficient and error <= tolerance,
            "standard_error": observation.get("standard_error"),
            "effective_sample_size": observation.get("effective_sample_size", 0),
            "independent_game_clusters": observation.get("clusters", 0),
            "raw_sample_size": observation.get("n", 0),
        }
    return {
        "passed": bool(assessments) and all(metric["passed"] for metric in assessments.values()),
        "loss": sum(
            min(100, metric["absolute_error"] / metric["tolerance"]) ** 2
            for metric in assessments.values()
        ),
        "metrics": assessments,
    }


def propose_profile(
    profile: CalibrationProfile,
    measured: dict[str, float],
    targets: dict[str, float],
) -> CalibrationProfile:
    values = asdict(profile)
    mapping = {
        "rush_yards_per_attempt": "run_yards_scale",
        "pass_yards_per_attempt": "pass_yards_scale",
        "interception": "interception_scale",
        "sack": "sack_scale",
        "fumble": "fumble_scale",
    }
    for metric, knob in mapping.items():
        if metric in measured and metric in targets and measured[metric] > 0:
            ratio = max(0.5, min(2, targets[metric] / measured[metric]))
            values[knob] = max(0.6, min(1.4, values[knob] * math.sqrt(ratio)))
    if "completion" in measured:
        values["completion_shift"] = max(
            -0.15,
            min(
                0.15,
                values["completion_shift"] + 0.5 * (targets["completion"] - measured["completion"]),
            ),
        )
    return CalibrationProfile(**values)


def observe_chart_draws(
    result: dict[str, Any], teams: dict[str, tuple[TeamChart, TeamFileMetadata]]
) -> list[dict[str, Any]]:
    """Observe actual normalized consultations using production engine section names.

    Turnover and end-zone return routines use the interception-return column for
    their first draw and subsequent rerolls. This map follows those engine APIs;
    it interprets neither display tokens nor football results.
    """
    aliases = {
        "turnover_return": "interception_return",
        "turnover_return_reroll": "interception_return",
        "end_zone_recovery_return": "interception_return",
    }
    lookup = {
        (chart.name, record.column.value, record.roll): (identity, record.cell)
        for identity, (chart, _) in teams.items()
        for record in chart.special_teams
    }
    draws = []
    for row in result["engine_log"]:
        for entry in row["trace"]:
            column = aliases.get(entry["section"], entry["section"])
            key = (entry["team"], column, entry["roll"].get("total"))
            if key in lookup:
                identity, cell = lookup[key]
                draws.append(
                    {
                        "team_id": identity,
                        "column": column,
                        "kind": cell.kind.value,
                        "yards": cell.yards,
                    }
                )
    return draws


def run_batch(
    teams: dict[str, tuple[TeamChart, TeamFileMetadata]],
    seeds: Sequence[int],
    output: Path,
    *,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Balanced two-team mechanics study; explicitly not a historical schedule fit."""
    if len(teams) != 2:
        raise ValueError("initial refinement runner requires exactly two declared pilot teams")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    identities = sorted(teams)
    season = teams[identities[0]][0].season
    results = []
    for index, seed in enumerate(seeds):
        away, home = identities if index % 2 == 0 else identities[::-1]
        spec = GameSpec(index + 1, season, away, home, seed)
        result = _play_one(spec, teams, decision_coach_version=10)
        result["normalized_chart_draws"] = observe_chart_draws(result, teams)
        (output / f"game-{index + 1:05d}.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        if progress:
            progress(index + 1, len(seeds), result["status"])
    summary = aggregate_games(results)
    summary.update(
        {
            "scope": "balanced two-team mechanics study; not historical-schedule calibration",
            "engine": engine_identity(),
            "seeds": list(seeds),
        }
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def run_refinement(
    events: Sequence[Event],
    pilot: dict[str, str],
    season: int,
    output: Path,
    *,
    seed_plan: SeedPlan,
    generation_seed: int = 1,
    iterations: int = 3,
    tactics: TacticalProfile | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Preserve every candidate, select by training only, then validate once."""
    output = private_destination(output)
    if output.exists():
        raise ValueError("refinement output must be a new path without symlinks")
    if not 1 <= iterations <= 8:
        raise ValueError("iterations must be within [1, 8]")
    output.mkdir(parents=True, mode=0o700)
    targets = source_targets(events, list(pilot))
    profile = CalibrationProfile()
    history = []
    best = None
    for iteration in range(iterations):
        candidate = output / f"candidate-{iteration:02d}"
        teams = {}
        for identity, name in pilot.items():
            from .audit import audit_chart

            bundle = generate_team(
                events,
                identity,
                name,
                season,
                seed=generation_seed,
                profile=profile,
                tactics=tactics,
            )
            write_bundle(candidate, bundle)
            probability_dir = candidate / "probability-audits"
            probability_dir.mkdir(exist_ok=True)
            (probability_dir / f"{team_folder_name(name)}.json").write_text(
                json.dumps(audit_chart(bundle[0]), indent=2) + "\n"
            )
            teams[f"{season}/{team_folder_name(name)}"] = bundle[:2]
        summary = run_batch(teams, seed_plan.training, candidate / "training", progress=progress)
        assessment = assess_metrics(summary["metrics"], targets, minimum_samples=1000)
        record = {
            "iteration": iteration,
            "profile": asdict(profile),
            "assessment": assessment,
            "summary": summary,
            "candidate": str(candidate),
        }
        history.append(record)
        if best is None or (summary["failed_games"], assessment["loss"]) < best[0]:
            best = ((summary["failed_games"], assessment["loss"]), candidate, profile, teams)
        if assessment["passed"] and not summary["failed_games"]:
            break
        proposed = propose_profile(
            profile, {k: v["value"] for k, v in summary["metrics"].items()}, targets
        )
        if proposed == profile:
            break
        profile = proposed
    assert best is not None
    _, selected_path, selected_profile, teams = best
    # Never use validation observations to select or update the profile.
    validation = run_batch(teams, seed_plan.validation, output / "heldout", progress=progress)
    assessment = assess_metrics(validation["metrics"], targets, minimum_samples=2000)
    replay = []
    identities = sorted(teams)
    for index, seed in enumerate(seed_plan.validation[:4]):
        away, home = identities if index % 2 == 0 else identities[::-1]
        result = _play_one(
            GameSpec(index + 1, season, away, home, seed),
            teams,
            verify_replay=True,
            decision_coach_version=10,
        )
        (output / f"save-replay-{index + 1}.json").write_text(json.dumps(result, indent=2) + "\n")
        replay.append(
            {
                "seed": seed,
                "finished": result["final"]["finished"],
                "save_continuation_verified": result["status"] == "passed"
                and result["save_replay"]["checkpoint_verified"]
                and result["save_replay"]["final_replay_verified"],
                "error": result["error"],
            }
        )
    coaching_assessments = []
    for index, seed in enumerate(seed_plan.validation[:4]):
        away, home = identities if index % 2 == 0 else identities[::-1]
        result = _play_one(
            GameSpec(index + 1, season, away, home, seed),
            teams,
            coach_policy="chart-v10",
            simulation_coach_version=10,
        )
        (output / f"coaching-assessment-{index + 1}.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        coaching_assessments.append(result)
    report = {
        "engine": engine_identity(),
        "scope": "two-team mechanics study; not historical schedule fit",
        "predeclared_tolerances": TOLERANCES,
        "seed_plan": asdict(seed_plan),
        "actual_training_games_per_team": seed_plan.training_games,
        "actual_validation_games_per_team": seed_plan.validation_games,
        "generation_seed": generation_seed,
        "targets": targets,
        "tactical_profile": None
        if tactics is None
        else {"sha256": tactics.sha256, "origin": tactics.origin},
        "training_history": history,
        "selected_candidate": str(selected_path),
        "selected_profile": asdict(selected_profile),
        "heldout": validation,
        "heldout_assessment": assessment,
        "save_replay_audits": replay,
        "coaching_assessment": aggregate_games(coaching_assessments),
        "mechanics_ready": best[0][0] == 0
        and not validation["failed_games"]
        and all(r["save_continuation_verified"] for r in replay)
        and not any(r["status"] != "passed" for r in coaching_assessments),
        "historical_fit_claim": False,
        "stopping_rule": (
            "training tolerance, unchanged bounded profile, or predeclared iteration limit"
        ),
    }
    (output / "selected-profile.json").write_text(
        json.dumps(asdict(selected_profile), indent=2) + "\n"
    )
    (output / "refinement-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
