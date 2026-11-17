"""Reproducible actual-fixture replay through the production engine audit harness."""

from __future__ import annotations

import json
import math
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bowl_bound.models import TeamChart
from bowl_bound.team_csv import TeamFileMetadata, team_to_files
from tools.chartgen.research_runner import GameSpec, _play_one, stable_seed

from .artifacts import (
    ArtifactCompression,
    check_capacity,
    game_artifact_path,
    read_artifact,
    storage_policy,
    write_artifact,
)
from .batch import write_json_new
from .cohort_report import canonical_hash, validate_simulation_fixtures
from .current_runtime import reference_options
from .primary_fumbles import observe_primary_results
from .private_io import private_destination
from .readiness import compare_run_inventory, qualification_status
from .refine import aggregate_games, assess_metrics, engine_identity, observe_chart_draws
from .research_inputs import (
    FrozenResearchInputs,
    InputConsistencyError,
    require_catalog_inputs,
    require_team_inputs,
)
from .runtime_identity import require_runtime_identity
from .scope import CORE_METRICS, HistoricalGame

AuditTeams = dict[str, tuple[TeamChart, TeamFileMetadata]]
_WORKER_TEAMS: AuditTeams = {}
_WORKER_RUNTIME_SHA256 = ""
_WORKER_RESEARCH_INPUTS = b""


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


def _initialize_worker(
    teams: AuditTeams,
    reviewed_runtime: Mapping[str, Any] | None = None,
    reviewed_inputs: dict[str, Any] | None = None,
) -> None:
    global _WORKER_TEAMS, _WORKER_RUNTIME_SHA256, _WORKER_RESEARCH_INPUTS
    # Spawned workers import independently of the parent contract process.
    identity = engine_identity()
    if reviewed_runtime is not None:
        require_runtime_identity(reviewed_runtime, identity)
    _WORKER_RUNTIME_SHA256 = canonical_hash(
        {key: value for key, value in identity.items() if key != "git_commit"}
    )
    snapshot = FrozenResearchInputs.capture(teams=teams, manifest={}, catalog={}, targets={})
    expected = reviewed_inputs if reviewed_inputs is not None else snapshot.identity
    require_team_inputs(snapshot.values["teams"], expected)
    _WORKER_TEAMS = snapshot.values["teams"]
    _WORKER_RESEARCH_INPUTS = json.dumps(
        {"identity": expected, "complete": reviewed_inputs is not None}, sort_keys=True
    ).encode()


def _execute_run(task: tuple[FixtureRun, Mapping[str, str], bool]) -> dict[str, Any]:
    run, catalog, verify_replay = task
    bound = json.loads(_WORKER_RESEARCH_INPUTS)
    expected = bound["identity"]
    if bound["complete"]:
        require_catalog_inputs(catalog, expected, "worker catalog")
    names = (catalog[run.game.away], catalog[run.game.home])
    # Both observers build lookups from every supplied chart, including unused teams.
    verified = require_team_inputs(_WORKER_TEAMS, expected)
    consumed = {key: verified[key] for key in names}
    spec = GameSpec(
        run.number,
        run.game.season,
        catalog[run.game.away],
        catalog[run.game.home],
        run.seed,
        game_type="postseason" if run.game.postseason else "regular",
    )
    try:
        result = _play_one(
            spec,
            _WORKER_TEAMS,
            verify_replay=verify_replay,
            **reference_options(),
        )
    finally:
        require_team_inputs(_WORKER_TEAMS, expected)
        if bound["complete"]:
            require_catalog_inputs(catalog, expected, "worker catalog after game")
    try:
        result["normalized_chart_draws"] = observe_chart_draws(result, _WORKER_TEAMS)
        result["normalized_primary_results"] = observe_primary_results(result, _WORKER_TEAMS)
    finally:
        require_team_inputs(_WORKER_TEAMS, expected)
        if bound["complete"]:
            require_catalog_inputs(catalog, expected, "worker catalog after observers")
    result["research_runtime_sha256"] = _WORKER_RUNTIME_SHA256
    result["research_inputs_sha256"] = expected["sha256"] if bound["complete"] else None
    result["consumed_chart_sha256"] = consumed
    result["fixture_run"] = asdict(run)
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


def _publish(
    path: Path, payload: Any, *, compression: ArtifactCompression = ArtifactCompression.JSON
) -> None:
    """Retain the existing atomic publication boundary for summaries and games."""
    write_artifact(path, payload, compression=compression)


def compact_metric_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Keep sufficient metric facts in memory; retain full validated logs on disk."""
    return {
        "spec": result.get("spec"),
        "fixture_run": result.get("fixture_run"),
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
        "normalized_primary_results": result.get("normalized_primary_results"),
        "engine_log": [
            {
                "number": row.get("number"),
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
                "normalized_primary_results": [
                    {
                        **row,
                        "offense_id": "selected" if selected[row["offense_side"]] else "excluded",
                    }
                    for row in result["normalized_primary_results"]
                ]
                if result.get("normalized_primary_results") is not None
                else None,
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


def assess_team_metrics(
    measured: Mapping[str, Mapping[str, Any]],
    targets: Mapping[str, float],
    *,
    minimum_samples: int,
    historical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Unknown required source facts cannot become omitted passing fit gates."""
    assessment = assess_metrics(dict(measured), dict(targets), minimum_samples=minimum_samples)
    unknown = sorted(CORE_METRICS - set(targets))
    assessment["unidentifiable_source_metrics"] = unknown
    assessment["historical_exposure"] = (
        dict(historical)
        if historical
        else {"qualified": False, "state": "missing_historical_exposure"}
    )
    historical_metrics = assessment["historical_exposure"].get("metrics", {})
    assessment["historically_sparse_metrics"] = sorted(
        name for name in targets if historical_metrics.get(name, {}).get("qualified") is not True
    )
    assessment["passed"] = (
        assessment["passed"]
        and not unknown
        and assessment["historical_exposure"].get("qualified") is True
        and not assessment["historically_sparse_metrics"]
    )
    return assessment


def summarize_cohort(
    results: Sequence[dict[str, Any]],
    report: Mapping[str, Any],
    catalog: Mapping[str, str],
    targets: Mapping[str, Mapping[str, Any]],
    *,
    minimum_samples: int,
    expected_runs: Sequence[FixtureRun] | None = None,
) -> dict[str, Any]:
    """Assess per-team OFF/DEF first; pooled outcomes are supplemental diagnostics."""
    summary = aggregate_games(results)
    per_team = {}
    for team, entry in report["teams"].items():
        if not entry["offensive_game_ids"]:
            per_team[team] = {"state": "no_eligible_games", "game_ids": []}
            continue
        if team not in catalog:
            per_team[team] = {"state": "missing_chart", "game_ids": entry["offensive_game_ids"]}
            continue
        if team not in targets or any(role not in targets[team] for role in ("offense", "defense")):
            per_team[team] = {
                "state": "missing_source_targets",
                "game_ids": entry["offensive_game_ids"],
            }
            continue
        own = _group_summary(results, {catalog[team]})
        defense = _group_summary(results, {catalog[team]}, defense=True)
        off_assessment = assess_team_metrics(
            own["metrics"],
            dict(targets[team]["offense"]),
            minimum_samples=minimum_samples,
            historical=targets[team].get("historical_exposure", {}).get("offense"),
        )
        def_assessment = assess_team_metrics(
            defense["metrics"],
            dict(targets[team]["defense"]),
            minimum_samples=minimum_samples,
            historical=targets[team].get("historical_exposure", {}).get("defense"),
        )
        insufficient = any(
            m["insufficient_samples"]
            for a in (off_assessment, def_assessment)
            for m in a["metrics"].values()
        )
        historically_sparse = any(
            assessment["historical_exposure"].get("qualified") is not True
            or bool(assessment["historically_sparse_metrics"])
            for assessment in (off_assessment, def_assessment)
        )
        per_team[team] = {
            "state": "unidentifiable_source_targets"
            if off_assessment["unidentifiable_source_metrics"]
            or def_assessment["unidentifiable_source_metrics"]
            else "sparse_historical_exposure"
            if historically_sparse
            else "sparse_exposure"
            if insufficient
            else "fit"
            if off_assessment["passed"] and def_assessment["passed"]
            else "not_fit",
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
    expected = None
    if expected_runs is not None:
        expected = [
            {
                "fixture_run": asdict(run),
                "spec": asdict(
                    GameSpec(
                        run.number,
                        run.game.season,
                        catalog.get(run.game.away),
                        catalog.get(run.game.home),
                        run.seed,
                        game_type="postseason" if run.game.postseason else "regular",
                    )
                ),
            }
            for run in expected_runs
        ]
    coverage = compare_run_inventory(
        expected,
        [{"fixture_run": row.get("fixture_run"), "spec": row.get("spec")} for row in results],
    )
    qualification = qualification_status(
        failed_games=summary["failed_games"],
        per_team=per_team,
        coverage=coverage,
        expected_teams=tuple(report["teams"]),
    )
    summary.update(
        per_source_team=per_team,
        conferences=conferences,
        source_holdout_claim=False,
        coverage=coverage,
        qualification=qualification,
        team_inventory=qualification["team_inventory"],
    )
    return _finite_assessment(summary)


def _require_result_inputs(
    result: Mapping[str, Any], run: FixtureRun, catalog: Mapping[str, str], identity: dict[str, Any]
) -> None:
    expected = {
        catalog[team]: identity["team_sha256"][catalog[team]]
        for team in (run.game.away, run.game.home)
    }
    if (
        result.get("research_inputs_sha256") != identity["sha256"]
        or result.get("consumed_chart_sha256") != expected
    ):
        expected_identity = {**identity, "team_sha256": expected}
        observed_identity = {
            **identity,
            "sha256": result.get("research_inputs_sha256"),
            "team_sha256": result.get("consumed_chart_sha256"),
        }
        raise InputConsistencyError("game receipt", "worker", expected_identity, observed_identity)


def _retain_input_rejection(
    output: Path, error: InputConsistencyError, *, prior_summary: bool
) -> None:
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    index = 1
    while True:
        path = output / f"rejected-inputs-{index:06d}.json"
        if (output / f"rejected-summary-{index:06d}.json").exists():
            index += 1
            continue
        try:
            write_json_new(path, error.evidence)
            break
        except FileExistsError:
            index += 1
    summary = output / "summary.json"
    if not prior_summary and summary.exists():
        summary.rename(output / f"rejected-summary-{index:06d}.json")


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
    compression: ArtifactCompression = ArtifactCompression.JSON,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Compute from detached complete inputs, checking original and snapshot boundaries."""
    output = private_destination(output)
    prior_summary = (output / "summary.json").exists()
    try:
        frozen = FrozenResearchInputs.capture(
            teams=teams, manifest=report, catalog=catalog, targets=targets
        )
        values = frozen.values
        summary = _run_frozen_batch(
            values["manifest"],
            values["teams"],
            values["catalog"],
            values["targets"],
            output,
            repetitions=repetitions,
            master_seed=master_seed,
            domain=domain,
            workers=workers,
            resume=resume,
            verify_replay=verify_replay,
            compression=compression,
            progress=progress,
            frozen_inputs=frozen,
        )
        frozen.check("before return")
        return summary
    except InputConsistencyError as error:
        _retain_input_rejection(output, error, prior_summary=prior_summary)
        raise


def _run_frozen_batch(
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
    compression: ArtifactCompression = ArtifactCompression.JSON,
    progress: Callable[[int, int, str], None] | None = None,
    frozen_inputs: FrozenResearchInputs,
) -> dict[str, Any]:
    """Replay only frozen actual fixtures; verify every retained result on resume."""
    output = private_destination(output)
    compression = ArtifactCompression(compression)
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
        "schema_version": 2,
        "research_inputs": frozen_inputs.identity,
        "manifest_sha256": report["manifest_sha256"],
        "engine": engine_identity(),
        "runs": [asdict(run) for run in runs],
        "catalog": dict(catalog),
        "targets_sha256": canonical_hash(targets),
        "chart_sha256": {
            key: canonical_hash(team_to_files(*value)) for key, value in teams.items()
        },
        "verify_replay": verify_replay,
        "artifact_storage_policy": storage_policy(compression),
    }
    contract_hash = canonical_hash(contract)
    runtime_hash = canonical_hash(
        {key: value for key, value in contract["engine"].items() if key != "git_commit"}
    )
    existing_output = output.exists()
    if existing_output:
        if not resume:
            raise ValueError("simulation output exists; choose a new path or explicit resume")
        if json.loads((output / "run-contract.json").read_text()) != contract:
            raise ValueError("resume contract differs from source/engine/charts/targets/seeds")
    retained, missing = {}, []
    for run in runs:
        path = game_artifact_path(output, run.number, compression)
        if path.exists():
            value = read_artifact(path)
            if (
                not isinstance(value, dict)
                or value.get("contract_sha256") != contract_hash
                or value.get("run") != asdict(run)
            ):
                raise ValueError("retained fixture contract differs")
            if canonical_hash(value["result"]) != value.get("result_sha256"):
                raise ValueError("retained game checksum differs; preserve and investigate")
            if value["result"].get("research_runtime_sha256") != runtime_hash:
                raise ValueError("retained game runtime identity differs from reviewed contract")
            _require_result_inputs(value["result"], run, catalog, frozen_inputs.identity)
            retained[run.number] = compact_metric_result(value["result"])
        else:
            missing.append(run)
    capacity = check_capacity(output, len(missing), compression=compression)
    if not existing_output:
        output.mkdir(parents=True, mode=0o700)
        write_json_new(output / "run-contract.json", contract)
        write_json_new(output / "storage-preflight.json", capacity)
    frozen_inputs.check("before workers")
    _initialize_worker(teams, contract["engine"], frozen_inputs.identity)
    executor = (
        ProcessPoolExecutor(
            max_workers=workers,
            initializer=_initialize_worker,
            initargs=(teams, contract["engine"], frozen_inputs.identity),
        )
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
            if result.get("research_runtime_sha256") != runtime_hash:
                raise ValueError("worker runtime identity differs from reviewed contract")
            _require_result_inputs(result, run, catalog, frozen_inputs.identity)
            payload = {
                "contract_sha256": contract_hash,
                "run": asdict(run),
                "result": result,
                "result_sha256": canonical_hash(result),
            }
            _publish(
                game_artifact_path(output, run.number, compression),
                payload,
                compression=compression,
            )
            retained[run.number] = compact_metric_result(result)
            if progress:
                progress(len(retained), len(runs), result["status"])
                frozen_inputs.check("after progress", include_teams=False)
    finally:
        if executor:
            executor.shutdown(wait=True, cancel_futures=True)
    frozen_inputs.check("after games")
    require_runtime_identity(contract["engine"], engine_identity())
    ordered = [retained[run.number] for run in runs]
    summary = summarize_cohort(
        ordered,
        report,
        catalog,
        targets,
        minimum_samples=2000 if domain == "heldout" else 1000,
        expected_runs=runs,
    )
    frozen_inputs.check("after summary computation")
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
        research_inputs_sha256=frozen_inputs.identity["sha256"],
        engine_sha256=contract["engine"]["engine_sha256"],
        manifest_sha256=report["manifest_sha256"],
        actual_fixture_ids=[run.game.game_id for run in runs],
        domain=domain,
        repetitions=repetitions,
        completed_runs=len(ordered),
        failures_retained=sum(r["status"] != "passed" for r in ordered),
        artifact_storage={
            "compression": compression.value,
            "complete_artifact_count": len(runs),
            "complete_artifact_bytes": sum(
                game_artifact_path(output, run.number, compression).stat().st_size for run in runs
            ),
        },
    )
    frozen_inputs.check("before summary publication")
    summary_path = output / "summary.json"
    if summary_path.exists():
        if json.loads(summary_path.read_text()) != summary:
            raise ValueError("retained summary differs from checked engine results")
    else:
        _publish(summary_path, summary)
    return summary
