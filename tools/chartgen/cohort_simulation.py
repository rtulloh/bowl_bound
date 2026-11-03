"""Reproducible actual-fixture replay through the production engine audit harness."""

from __future__ import annotations

import json
import math
import os
import tempfile
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bowl_bound.models import TeamChart
from bowl_bound.team_csv import TeamFileMetadata, team_to_files
from scripts.run_local_season import GameSpec, _play_one, stable_seed

from .batch import write_json_new
from .cohort_report import canonical_hash, validate_simulation_fixtures
from .private_io import private_destination
from .refine import aggregate_games, assess_metrics, engine_identity, observe_chart_draws
from .scope import CORE_METRICS, HistoricalGame

AuditTeams = dict[str, tuple[TeamChart, TeamFileMetadata]]
_WORKER_TEAMS: AuditTeams = {}


@dataclass(frozen=True)
class FixtureRun:
    number: int
    game: HistoricalGame
    repetition: int
    domain: str
    seed: int


def fixture_runs(
    report: Mapping[str, Any], *, repetitions: int, master_seed: int, domain: str
) -> tuple[FixtureRun, ...]:
    """Pair candidates on the same actual fixtures/seeds, independent of profiles."""
    if domain not in {"training", "heldout", "replay", "coaching"}:
        raise ValueError("unknown predeclared simulation seed domain")
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("fixture repetitions must be positive")
    games = tuple(HistoricalGame(**row) for row in report["games"])
    if not games:
        raise ValueError("no selected historical fixtures; review coverage/exclusions first")
    validate_simulation_fixtures(report, list(games) * repetitions, repetitions=repetitions)
    return tuple(
        FixtureRun(
            rep * len(games) + index + 1,
            game,
            rep,
            domain,
            stable_seed(master_seed, f"cohort-v1/{domain}/{game.season}/{game.game_id}/{rep}"),
        )
        for rep in range(repetitions)
        for index, game in enumerate(games)
    )


def _initialize_worker(teams: AuditTeams) -> None:
    global _WORKER_TEAMS
    _WORKER_TEAMS = teams


def _execute_run(task: tuple[FixtureRun, Mapping[str, str], bool]) -> dict[str, Any]:
    run, catalog, verify_replay = task
    spec = GameSpec(
        run.number,
        run.game.season,
        catalog[run.game.away],
        catalog[run.game.home],
        run.seed,
        game_type="postseason" if run.game.postseason else "regular",
    )
    result = _play_one(
        spec,
        _WORKER_TEAMS,
        verify_replay=verify_replay,
        coach_policy="chart-v10" if run.domain == "coaching" else "baseline",
        decision_coach_version=None if run.domain == "coaching" else 10,
        simulation_coach_version=10 if run.domain == "coaching" else 1,
    )
    result["normalized_chart_draws"] = observe_chart_draws(result, _WORKER_TEAMS)
    return result


def _bounded_results(
    executor: ProcessPoolExecutor,
    tasks: Iterable[tuple[FixtureRun, Mapping[str, str], bool]],
    workers: int,
) -> Iterator[dict[str, Any]]:
    """Keep at most workers submitted tasks on supported Python 3.10+ APIs."""
    iterator = iter(tasks)
    pending = deque()
    for _ in range(workers):
        task = next(iterator, None)
        if task is not None:
            pending.append(executor.submit(_execute_run, task))
    while pending:
        yield pending.popleft().result()
        task = next(iterator, None)
        if task is not None:
            pending.append(executor.submit(_execute_run, task))


def _publish(path: Path, payload: Any) -> None:
    """Publish complete bytes atomically without overwriting any prior artifact."""
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    pending = Path(temporary)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(payload, stream, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def compact_metric_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Keep sufficient metric facts in memory; retain full validated logs on disk."""
    return {
        "status": result["status"],
        "error": result["error"],
        "teams": result["teams"],
        "final": {key: result["final"][key] for key in ("home_score", "away_score", "statistics")},
        "coaching_calls": [
            {key: row[key] for key in ("team_id", "role", "choice")}
            for row in result["coaching_calls"]
        ],
        "normalized_chart_draws": [
            {key: row[key] for key in ("team_id", "column", "yards")}
            for row in result.get("normalized_chart_draws", ())
        ],
        "engine_log": [
            {
                "state_before": {"possession": row["state_before"]["possession"]},
                "statistics": {"kind": row["statistics"]["kind"]},
                "outcome": row["outcome"],
                "trace": [
                    {"section": entry["section"]}
                    for entry in row["trace"]
                    if entry["section"] == "fumble_recovery"
                ],
            }
            for row in result["engine_log"]
        ],
    }


def _group_summary(
    results: Sequence[dict[str, Any]], identities: set[str], *, defense: bool = False
) -> dict[str, Any]:
    """Preserve full-game clusters when pooling both sides of a conference fixture."""
    grouped = []
    for result in results:
        sides = result["teams"]
        selected = {
            side: (sides["away" if side == "home" else "home"] if defense else identity)
            in identities
            for side, identity in sides.items()
        }
        if not any(selected.values()):
            continue
        mapping = {
            identity: "selected" if identity in identities else "excluded"
            for identity in sides.values()
        }
        grouped.append(
            {
                **result,
                "teams": {
                    side: "selected" if yes else "excluded" for side, yes in selected.items()
                },
                "coaching_calls": [
                    {**r, "team_id": mapping[r["team_id"]]} for r in result["coaching_calls"]
                ],
                "normalized_chart_draws": [
                    {**r, "team_id": mapping[r["team_id"]]}
                    for r in result.get("normalized_chart_draws", ())
                ],
            }
        )
    summary = aggregate_games(grouped, team_filter="selected")
    if defense:
        summary["metrics"] = {k: v for k, v in summary["metrics"].items() if k in CORE_METRICS}
    return summary


def _finite_assessment(value: Any) -> Any:
    """Missing observations remain null/failed rather than nonstandard JSON Infinity."""
    if isinstance(value, dict):
        return {k: _finite_assessment(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite_assessment(v) for v in value]
    return None if isinstance(value, float) and not math.isfinite(value) else value


def summarize_cohort(
    results: Sequence[dict[str, Any]],
    report: Mapping[str, Any],
    catalog: Mapping[str, str],
    targets: Mapping[str, Mapping[str, Any]],
    *,
    minimum_samples: int,
) -> dict[str, Any]:
    """Assess per-team OFF/DEF first; pooled outcomes are supplemental diagnostics."""
    summary = aggregate_games(results)
    per_team = {}
    for team, entry in report["teams"].items():
        if not entry["offensive_game_ids"]:
            per_team[team] = {"state": "no_eligible_games", "game_ids": []}
            continue
        own = _group_summary(results, {catalog[team]})
        defense = _group_summary(results, {catalog[team]}, defense=True)
        off_assessment = assess_metrics(
            own["metrics"], dict(targets[team]["offense"]), minimum_samples=minimum_samples
        )
        def_assessment = assess_metrics(
            defense["metrics"], dict(targets[team]["defense"]), minimum_samples=minimum_samples
        )
        insufficient = any(
            m["insufficient_samples"]
            for a in (off_assessment, def_assessment)
            for m in a["metrics"].values()
        )
        per_team[team] = {
            "state": "sparse_exposure" if insufficient else "assessed",
            "game_ids": entry["offensive_game_ids"],
            "offense": own,
            "defense": defense,
            "offense_assessment": off_assessment,
            "defense_assessment": def_assessment,
        }
    conferences = {}
    for conference in sorted(
        {v["conference"] for v in report["teams"].values() if v["conference"]}
    ):
        identities = {
            catalog[t]
            for t, v in report["teams"].items()
            if v["conference"] == conference and t in catalog
        }
        conferences[conference] = {
            "offense": _group_summary(results, identities),
            "defense": _group_summary(results, identities, defense=True),
            "assessment_scope": "supplemental; per-team OFF/DEF gates remain authoritative",
        }
    summary.update(per_source_team=per_team, conferences=conferences, source_holdout_claim=False)
    return _finite_assessment(summary)


def run_historical_batch(
    report: Mapping[str, Any],
    teams: AuditTeams,
    catalog: Mapping[str, str],
    targets: Mapping[str, Mapping[str, Any]],
    output: Path,
    *,
    repetitions: int,
    master_seed: int,
    domain: str,
    workers: int = 1,
    resume: bool = False,
    verify_replay: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Replay only frozen actual fixtures; verify every retained result on resume."""
    output = private_destination(output)
    if type(workers) is not int or not 1 <= workers <= 2:
        raise ValueError("cohort workers must be within [1, 2]")
    if canonical_hash(targets) != report.get("targets_sha256"):
        raise ValueError("simulation target values hash differs from frozen manifest")
    runs = fixture_runs(report, repetitions=repetitions, master_seed=master_seed, domain=domain)
    for team, entry in report["teams"].items():
        if targets.get(team, {}).get("game_ids") != entry["offensive_game_ids"]:
            raise ValueError("simulation target IDs differ from frozen historical manifest")
        if entry["offensive_game_ids"] and (team not in catalog or catalog[team] not in teams):
            raise ValueError("selected historical fixture has no supplied chart")
    contract = {
        "schema_version": 1,
        "manifest_sha256": report["manifest_sha256"],
        "engine": engine_identity(),
        "runs": [asdict(run) for run in runs],
        "catalog": dict(catalog),
        "targets_sha256": canonical_hash(targets),
        "chart_sha256": {
            key: canonical_hash(team_to_files(*value)) for key, value in teams.items()
        },
        "verify_replay": verify_replay,
    }
    contract_hash = canonical_hash(contract)
    if output.exists():
        if not resume:
            raise ValueError("simulation output exists; choose a new path or explicit resume")
        if json.loads((output / "run-contract.json").read_text()) != contract:
            raise ValueError("resume contract differs from source/engine/charts/targets/seeds")
    else:
        output.mkdir(parents=True, mode=0o700)
        write_json_new(output / "run-contract.json", contract)
    retained, missing = {}, []
    for run in runs:
        path = output / f"game-{run.number:06d}.json"
        if path.exists():
            value = json.loads(path.read_text())
            if value.get("contract_sha256") != contract_hash or value.get("run") != asdict(run):
                raise ValueError("retained fixture contract differs")
            if canonical_hash(value["result"]) != value.get("result_sha256"):
                raise ValueError("retained game checksum differs; preserve and investigate")
            retained[run.number] = compact_metric_result(value["result"])
        else:
            missing.append(run)
    _initialize_worker(teams)
    executor = (
        ProcessPoolExecutor(max_workers=workers, initializer=_initialize_worker, initargs=(teams,))
        if workers > 1
        else None
    )
    try:
        # At most two submitted engine tasks; publish in fixture order so
        # scheduling changes cannot change artifacts.
        tasks = ((run, catalog, verify_replay) for run in missing)
        results = (
            _bounded_results(executor, tasks, workers) if executor else map(_execute_run, tasks)
        )
        for run, result in zip(missing, results, strict=True):
            payload = {
                "contract_sha256": contract_hash,
                "run": asdict(run),
                "result": result,
                "result_sha256": canonical_hash(result),
            }
            _publish(output / f"game-{run.number:06d}.json", payload)
            retained[run.number] = compact_metric_result(result)
            if progress:
                progress(len(retained), len(runs), result["status"])
    finally:
        if executor:
            executor.shutdown(wait=True, cancel_futures=True)
    ordered = [retained[run.number] for run in runs]
    summary = summarize_cohort(
        ordered, report, catalog, targets, minimum_samples=2000 if domain == "heldout" else 1000
    )
    exposure = {}
    for run in runs:
        result = retained[run.number]
        entry = exposure.setdefault(run.game.game_id, {"attempted": 0, "passed": 0, "failed": 0})
        entry["attempted"] += 1
        entry["passed" if result["status"] == "passed" else "failed"] += 1
    summary["fixture_exposure"] = exposure
    summary["failed_fixture_runs"] = [
        {
            "game_id": run.game.game_id,
            "seed": run.seed,
            "number": run.number,
            "domain": run.domain,
            "error": retained[run.number]["error"],
        }
        for run in runs
        if retained[run.number]["status"] != "passed"
    ]
    summary.update(
        contract_sha256=contract_hash,
        engine_sha256=contract["engine"]["engine_sha256"],
        manifest_sha256=report["manifest_sha256"],
        actual_fixture_ids=[run.game.game_id for run in runs],
        domain=domain,
        repetitions=repetitions,
        completed_runs=len(ordered),
        failures_retained=sum(r["status"] != "passed" for r in ordered),
    )
    summary_path = output / "summary.json"
    if summary_path.exists():
        if json.loads(summary_path.read_text()) != summary:
            raise ValueError("retained summary differs from checked engine results")
    else:
        _publish(summary_path, summary)
    return summary
