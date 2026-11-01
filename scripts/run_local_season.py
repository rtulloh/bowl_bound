"""Play deterministic local seasons and save private engine/AI audit logs.

Run with ``python -m scripts.run_local_season`` from the repository root. Imported
historical teams and detailed reports are private; the runner is never used by CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from bowl_bound.cli import TeamCatalog, TeamEntry
from bowl_bound.coaching import BaselineCoach, CoachChoice, CoachObservation, safe_choice
from bowl_bound.coaching_audit import reconcile_period_scores
from bowl_bound.coaching_session import GameView, observe_game
from bowl_bound.models import TeamChart
from bowl_bound.save_game import SavedGame
from bowl_bound.statistics import summarize
from bowl_bound.timing import QUARTER_SECONDS

DEFAULT_GAMES_PER_TEAM = 12
DEFAULT_MASTER_SEED = 20311031
MAX_GAME_ACTIONS = 1500
DEFAULT_OUTPUT = Path("private-data/local-season-audits")


@dataclass(frozen=True)
class GameSpec:
    """One reproducible game in a generated season, not a historical fixture."""

    number: int
    season: int
    away_id: str
    home_id: str
    seed: int


def stable_seed(master_seed: int, identity: str) -> int:
    """Derive an order-independent seed without Python's randomized hash()."""
    digest = hashlib.sha256(
        f"bowl-bound-local-season-v1:{master_seed}:{identity}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big") & (2**63 - 1)


def _partial_regular_pairs(teams: tuple[str, ...], degree: int) -> list[tuple[str, str]]:
    """Build a simple degree-regular circulant graph for the remaining games."""
    count = len(teams)
    if degree == 0:
        return []
    pairs: set[tuple[str, str]] = set()
    for offset in range(1, degree // 2 + 1):
        for index, team in enumerate(teams):
            other = teams[(index + offset) % count]
            pairs.add(tuple(sorted((team, other))))
    if degree % 2:
        if count % 2:
            raise ValueError("team count and remaining games cannot form a balanced schedule")
        half = count // 2
        for index, team in enumerate(teams[:half]):
            pairs.add(tuple(sorted((team, teams[index + half]))))
    if len(pairs) * 2 != count * degree:
        raise ValueError("could not construct a balanced round-robin schedule")
    return sorted(pairs)


def _orient_even_degree_edges(
    teams: tuple[str, ...], edges: list[tuple[str, str]]
) -> dict[int, tuple[str, str]]:
    """Orient each even-degree multigraph component with equal home/away counts."""
    adjacent: dict[str, list[tuple[int, str]]] = {team: [] for team in teams}
    for number, (left, right) in enumerate(edges):
        adjacent[left].append((number, right))
        adjacent[right].append((number, left))
    for entries in adjacent.values():
        entries.sort(reverse=True)

    used: set[int] = set()
    oriented: dict[int, tuple[str, str]] = {}
    while len(used) < len(edges):
        start = next(team for team in teams if any(edge not in used for edge, _ in adjacent[team]))
        stack = [(start, None)]
        circuit_teams: list[str] = []
        circuit_edges: list[int] = []
        while stack:
            team = stack[-1][0]
            while adjacent[team] and adjacent[team][-1][0] in used:
                adjacent[team].pop()
            if adjacent[team]:
                edge, other = adjacent[team].pop()
                used.add(edge)
                stack.append((other, edge))
            else:
                visited, incoming = stack.pop()
                circuit_teams.append(visited)
                if incoming is not None:
                    circuit_edges.append(incoming)
        path = list(reversed(circuit_teams))
        route_edges = list(reversed(circuit_edges))
        if len(path) != len(route_edges) + 1:
            raise ValueError("generated schedule orientation is inconsistent")
        for index, edge in enumerate(route_edges):
            oriented[edge] = (path[index], path[index + 1])
    return oriented


def build_schedule(
    entries: Iterable[TeamEntry], *, games_per_team: int, master_seed: int
) -> tuple[GameSpec, ...]:
    """Build an even home/away schedule for one season with stable game seeds."""
    teams = tuple(sorted(entries, key=lambda entry: entry.key))
    if (
        len(teams) < 2
        or len({entry.key for entry in teams}) != len(teams)
        or len({entry.season for entry in teams}) != 1
    ):
        raise ValueError("schedule requires at least two distinct teams from one season")
    if type(games_per_team) is not int or games_per_team < 2 or games_per_team % 2:
        raise ValueError("games per team must be a positive even number")
    if type(master_seed) is not int:
        raise TypeError("master seed must be an integer")

    keys = tuple(entry.key for entry in teams)
    cycles, remainder = divmod(games_per_team, len(keys) - 1)
    all_pairs = [(left, right) for index, left in enumerate(keys) for right in keys[index + 1 :]]
    edges = all_pairs * cycles + _partial_regular_pairs(keys, remainder)
    if len(edges) * 2 != len(keys) * games_per_team:
        raise ValueError("schedule does not contain the requested number of games")
    orientation = _orient_even_degree_edges(keys, edges)
    season = teams[0].season
    return tuple(
        GameSpec(
            number=index + 1,
            season=season,
            away_id=orientation[index][0],
            home_id=orientation[index][1],
            seed=stable_seed(
                master_seed,
                f"season={season}:game={index + 1}:{orientation[index][0]}@{orientation[index][1]}",
            ),
        )
        for index in range(len(edges))
    )


def validate_game(view: GameView, period_scores: tuple[tuple[int, int], ...]) -> None:
    """Reject unfinished games and reconcile scoring, statistics, and timing."""
    if not view.finished or view.phase != "final":
        raise ValueError("game did not reach the engine's final phase")
    if view.pending is not None or getattr(view, "untimed_down", False):
        raise ValueError("game ended with a pending decision or untimed down")
    if not view.log:
        raise ValueError("final game has no engine reports")
    if view.home == view.away:
        raise ValueError("home and away names must differ for score reconciliation")

    for number, report in enumerate(view.log, start=1):
        if report.number != number:
            raise ValueError("engine report numbering is not sequential")
        if not report.supported or report.pending:
            raise ValueError("engine log contains an unsupported or pending report")
        for entry in report.trace:
            if (
                entry.team not in {view.home, view.away}
                or not entry.section
                or not _valid_trace_roll(entry.roll)
                or not isinstance(entry.cell, str)
            ):
                raise ValueError("engine trace entry is incomplete")

    totals = {view.home: 0, view.away: 0}
    for event in view.scoring:
        if event.team not in totals or type(event.points) is not int or event.points < 0:
            raise ValueError("scoring ledger contains an invalid event")
        totals[event.team] += event.points
    if totals[view.home] != view.score.home or totals[view.away] != view.score.away:
        raise ValueError("scoring ledger does not reconcile to the final score")
    if view.statistics != summarize(report.statistics for report in view.log):
        raise ValueError("statistics do not reconcile to engine reports")
    reconcile_period_scores(period_scores, (view.score.home, view.score.away))

    timing_log = getattr(view, "timing_log", ())
    regulation_seconds = {quarter: 0 for quarter in range(1, 5)}
    for charge in timing_log:
        if (
            charge.before - charge.after != min(charge.before, charge.seconds)
            or charge.after < 0
            or charge.seconds < 0
        ):
            raise ValueError("timing log contains an invalid clock transition")
        if charge.quarter in regulation_seconds:
            regulation_seconds[charge.quarter] += charge.before - charge.after
    if tuple(regulation_seconds.values()) != (QUARTER_SECONDS,) * 4:
        raise ValueError("regulation clock does not reconcile to four complete quarters")


def _valid_trace_roll(roll: object) -> bool:
    """Check that structured faces and labeled dice reproduce the recorded total."""
    if not isinstance(roll, dict):
        return False
    faces, dice, total = roll.get("faces"), roll.get("dice"), roll.get("total")
    if (
        not isinstance(faces, list)
        or not faces
        or any(type(face) is not int for face in faces)
        or not isinstance(dice, list)
        or any(not isinstance(die, dict) for die in dice)
        or [die.get("face") for die in dice] != faces
        or type(total) is not int
    ):
        return False
    roles = [die.get("role") for die in dice]
    if roles == ["black", "white_one", "white_two"]:
        expected = faces[0] * 10 + faces[1] + faces[2]
    elif roles == ["red", "green"]:
        expected = faces[0] + faces[1]
    else:
        return False
    return expected == total


def run_games(
    schedule: Iterable[GameSpec],
    play_game: Callable[[GameSpec], dict[str, Any]],
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Run every independent matchup and retain failure records."""
    results = []
    specifications = tuple(schedule)
    for index, spec in enumerate(specifications, start=1):
        try:
            result = play_game(spec)
        except Exception as error:
            result = {"status": "failed", "error": type(error).__name__}
        result.setdefault("spec", asdict(spec))
        if result.get("status") not in {"passed", "failed"}:
            result["status"] = "failed"
            result.setdefault("error", "InvalidResult")
        results.append(result)
        if progress is not None:
            progress(index, len(specifications), result)
    return results


def _json_value(value: Any) -> Any:
    """Convert engine dataclasses and enums into structured JSON values."""
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise TypeError("engine audit contains an unsupported value")


def _role(view: GameView, side: str, key: str) -> str:
    if view.pending is not None:
        return "decision"
    if view.phase == "clock_choice" or key.startswith("clock:"):
        return "clock"
    if view.state is not None and view.state.possession == side:
        if key in {action.key for action in view.actions.offense}:
            return "offense"
        if key in {action.key for action in view.actions.special}:
            return "special"
        return "action"
    if key in {action.key for action in view.actions.defense}:
        return "defense"
    return "special"


def _period_number(view: GameView) -> int:
    overtime = getattr(view, "overtime", None)
    if overtime is not None:
        return 4 + overtime.round_number
    clock = getattr(view, "clock", None)
    return clock.quarter if clock is not None else 1


def _call_record(
    view: GameView,
    side: str,
    role: str,
    choice: CoachChoice,
    team_ids: dict[str, str],
) -> dict[str, Any]:
    observation = observe_game(view, side)
    return {
        "team_side": side,
        "team_id": team_ids[side],
        "role": role,
        "observation": asdict(observation),
        "choice": choice.key,
        "fallback": choice.fallback,
    }


def _offense_choice(observation: CoachObservation, coach: BaselineCoach) -> CoachChoice:
    """Keep punts and other offered actions in the offense coach's legal menu."""
    legal = observation.offense + observation.special + observation.game_actions
    return safe_choice(coach.offense(observation), legal)


def _submit_offense_choice(
    game: SavedGame,
    side: str,
    observation: CoachObservation,
    choice: CoachChoice,
) -> CoachChoice | None:
    """Submit a scrimmage call, kick, or action through its engine-owned path."""
    if choice.key in observation.offense:
        _, _, _, computer_choice = game._coach_step_with_choice(side, choice.key)
        return computer_choice
    operation = "kick" if choice.key in observation.special else "action"
    game.coach_execute(side, operation, choice.key)
    return None


def _play_one(spec: GameSpec, charts: dict[str, TeamChart]) -> dict[str, Any]:
    """Play a complete regulation game through SavedGame's engine/coaching API."""
    away = charts[spec.away_id]
    home = charts[spec.home_id]
    team_ids = {"home": spec.home_id, "away": spec.away_id}
    coaches = {
        "home": BaselineCoach(stable_seed(spec.seed, "home-coach")),
        "away": BaselineCoach(stable_seed(spec.seed, "away-coach")),
    }
    game = SavedGame.new(
        home,
        away,
        home_id=spec.home_id,
        away_id=spec.away_id,
        seed=spec.seed,
        mode="regulation",
        coach_seed=stable_seed(spec.seed, "engine-coach"),
    )
    calls: list[dict[str, Any]] = []
    period_totals: dict[int, list[int]] = {quarter: [0, 0] for quarter in range(1, 5)}
    failure: str | None = None
    try:
        for _ in range(MAX_GAME_ACTIONS):
            view = game.view()
            if view.finished:
                break
            advanced = False
            for side in ("home", "away"):
                _, turn = game.coach_view(side)
                if turn.automatic:
                    cpu_side = "away" if side == "home" else "home"
                    _, _, _, choice = game._coach_step_with_choice(side)
                    if choice is not None:
                        calls.append(
                            _call_record(
                                view,
                                cpu_side,
                                _role(view, cpu_side, choice.key),
                                choice,
                                team_ids,
                            )
                        )
                    advanced = True
                    break
                if turn.human_role == "decision":
                    continue
                if turn.human_role in {"offense", "defense"}:
                    role = turn.human_role
                    observation: CoachObservation = observe_game(view, side)
                    if role == "offense":
                        choice = _offense_choice(observation, coaches[side])
                        cpu_choice = _submit_offense_choice(game, side, observation, choice)
                        call_role = _role(view, side, choice.key)
                    else:
                        if not observation.defense:
                            continue
                        choice = safe_choice(
                            coaches[side].defense(observation), observation.defense
                        )
                        _, _, _, cpu_choice = game._coach_step_with_choice(side, choice.key)
                        call_role = role
                    calls.append(_call_record(view, side, call_role, choice, team_ids))
                    if cpu_choice is not None:
                        cpu_side = "away" if side == "home" else "home"
                        calls.append(
                            _call_record(
                                view,
                                cpu_side,
                                _role(view, cpu_side, cpu_choice.key),
                                cpu_choice,
                                team_ids,
                            )
                        )
                    advanced = True
                    break

                observation = observe_game(view, side)
                legal = observation.special + observation.game_actions
                if not legal:
                    continue
                choice = safe_choice(coaches[side].decision(observation), legal)
                operation = "kick" if choice.key in observation.special else "action"
                game.coach_execute(side, operation, choice.key)
                calls.append(_call_record(view, side, "special", choice, team_ids))
                advanced = True
                break
            if not advanced:
                raise ValueError("neither team has a legal automated action")
            after = game.view()
            score_delta = (
                after.score.home - view.score.home,
                after.score.away - view.score.away,
            )
            if any(points < 0 for points in score_delta):
                raise ValueError("score decreased during a period")
            period = period_totals.setdefault(_period_number(view), [0, 0])
            period[0] += score_delta[0]
            period[1] += score_delta[1]
        else:
            raise TimeoutError("game action limit reached")
        view = game.view()
        period_scores = tuple(tuple(period_totals[key]) for key in sorted(period_totals))
        validate_game(view, period_scores)
    except Exception as error:
        failure = type(error).__name__
        view = game.view()

    return {
        "status": "failed" if failure else "passed",
        "error": failure,
        "spec": asdict(spec),
        "teams": {"home": spec.home_id, "away": spec.away_id},
        "final": {
            "finished": view.finished,
            "phase": view.phase,
            "home_score": view.score.home,
            "away_score": view.score.away,
            "report_count": len(view.log),
            "statistics": _json_value(view.statistics),
            "scoring": _json_value(view.scoring),
            "clock": _json_value(view.clock) if hasattr(view, "clock") else None,
            "timing_log": _json_value(getattr(view, "timing_log", ())),
        },
        "period_scores": [
            {"period": period, "home": scores[0], "away": scores[1]}
            for period, scores in sorted(period_totals.items())
        ],
        "coaching_calls": calls,
        "engine_log": _json_value(view.log),
    }


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    standings: dict[str, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "losses": 0, "ties": 0, "points_for": 0, "points_against": 0}
    )
    calls: dict[tuple[str, str, int, str], Counter[str]] = defaultdict(Counter)
    fallbacks: Counter[tuple[str, str, int, str]] = Counter()
    for result in results:
        if result["status"] != "passed":
            continue
        home, away = result["teams"]["home"], result["teams"]["away"]
        home_score, away_score = result["final"]["home_score"], result["final"]["away_score"]
        for team, scored, allowed in (
            (home, home_score, away_score),
            (away, away_score, home_score),
        ):
            standing = standings[team]
            standing["points_for"] += scored
            standing["points_against"] += allowed
        if home_score == away_score:
            standings[home]["ties"] += 1
            standings[away]["ties"] += 1
        else:
            winner, loser = (home, away) if home_score > away_score else (away, home)
            standings[winner]["wins"] += 1
            standings[loser]["losses"] += 1
        for call in result["coaching_calls"]:
            obs = call["observation"]
            distance = obs["distance"]
            distance_band = (
                "1-3"
                if distance <= 3
                else "4-6"
                if distance <= 6
                else "7-10"
                if distance <= 10
                else "11+"
            )
            key = (call["team_id"], call["role"], obs["down"], distance_band)
            calls[key][call["choice"]] += 1
            fallbacks[key] += bool(call.get("fallback", False))
    return {
        "games": len(results),
        "passed": sum(result["status"] == "passed" for result in results),
        "failed": sum(result["status"] != "passed" for result in results),
        "fallbacks": sum(fallbacks.values()),
        "standings": {team: standings[team] for team in sorted(standings)},
        "coaching_calls": [
            {
                "team_id": key[0],
                "role": key[1],
                "down": key[2],
                "distance_band": key[3],
                "calls": sum(choices.values()),
                "fallbacks": fallbacks[key],
                "choice_counts": dict(sorted(choices.items())),
            }
            for key, choices in sorted(calls.items())
        ],
        "note": (
            "Generated games and play choices are audit evidence, not historical results "
            "or balance verdicts."
        ),
    }


def _private_run_dir(output_root: Path, master_seed: int) -> Path:
    private_root = (Path.cwd() / "private-data").absolute()
    output_root = output_root.absolute()
    if private_root not in output_root.parents:
        raise ValueError("audit output must remain below private-data/")
    if any(path.is_symlink() for path in (output_root, *output_root.parents)):
        raise ValueError("audit output paths must not use symlinks")
    output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / f"season-{stamp}-{time.time_ns() % 1_000_000:06d}-seed-{master_seed}"
    run_dir.mkdir(mode=0o700)
    return run_dir


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True, ensure_ascii=False)
        output.write("\n")


def run_local_season(
    seasons_root: Path,
    *,
    games_per_team: int = DEFAULT_GAMES_PER_TEAM,
    master_seed: int = DEFAULT_MASTER_SEED,
    output_root: Path = DEFAULT_OUTPUT,
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Play every readable same-season team group and write private full-game logs."""
    catalog = TeamCatalog(seasons_root)
    entries = catalog.teams()
    if catalog.problems:
        raise ValueError("one or more local team bundles could not be loaded")
    groups: dict[int, list[TeamEntry]] = defaultdict(list)
    for entry in entries:
        groups[entry.season].append(entry)
    scheduled = [
        spec
        for season in sorted(groups)
        if len(groups[season]) >= 2
        for spec in build_schedule(
            groups[season], games_per_team=games_per_team, master_seed=master_seed
        )
    ]
    if not scheduled:
        raise ValueError("no season contains at least two readable local teams")
    charts = {entry.key: catalog.load(entry.key) for entry in entries}
    results = run_games(scheduled, lambda spec: _play_one(spec, charts), progress)
    summary = _summary(results)
    run_dir = _private_run_dir(output_root, master_seed)
    for result in results:
        spec = result["spec"]
        path = run_dir / f"game-{spec['season']}-{spec['number']:04d}.json"
        _write_json(path, result)
    manifest = {
        "schema_version": 1,
        "master_seed": master_seed,
        "games_per_team": games_per_team,
        "team_ids": [entry.key for entry in entries],
        "seasons": sorted(groups),
        "summary": summary,
        "game_logs": [
            f"game-{result['spec']['season']}-{result['spec']['number']:04d}.json"
            for result in results
        ],
    }
    _write_json(run_dir / "summary.json", manifest)
    return run_dir, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=Path, default=Path("seasons"))
    parser.add_argument("--games-per-team", type=int, default=DEFAULT_GAMES_PER_TEAM)
    parser.add_argument("--seed", type=int, default=DEFAULT_MASTER_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    def show_progress(index: int, total: int, result: dict[str, Any]) -> None:
        spec = result["spec"]
        final = result.get("final", {})
        print(
            f"[{index}/{total}] {result['status']} {spec['season']}: "
            f"{spec['away_id']} @ {spec['home_id']} "
            f"({final.get('away_score', '?')}-{final.get('home_score', '?')})",
            flush=True,
        )

    try:
        run_dir, summary = run_local_season(
            args.seasons,
            games_per_team=args.games_per_team,
            master_seed=args.seed,
            output_root=args.output,
            progress=show_progress,
        )
    except (OSError, ValueError) as error:
        print(f"Local season audit failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Local season audit: {summary['passed']}/{summary['games']} games passed; "
        f"{summary['failed']} failed. Private logs: {run_dir}"
    )
    for result in summary["standings"]:
        record = summary["standings"][result]
        print(
            f"  {result}: {record['wins']}-{record['losses']}-{record['ties']} "
            f"PF {record['points_for']} PA {record['points_against']}"
        )
    return int(summary["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
