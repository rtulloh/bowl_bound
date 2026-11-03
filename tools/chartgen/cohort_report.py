"""Private human and machine-readable reports of the exact historical slate."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .batch import write_json_new
from .private_io import private_destination
from .scope import HistoricalGame, Slate


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_simulation_fixtures(
    report: Mapping[str, Any], fixtures: Sequence[HistoricalGame], *, repetitions: int
) -> None:
    """Reject invented, mutated or missing fixtures and unequal replay exposure."""
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("fixture repetitions must be positive")
    body = {k: v for k, v in report.items() if k != "manifest_sha256"}
    if canonical_hash(body) != report.get("manifest_sha256"):
        raise ValueError("historical manifest hash differs from frozen content")
    expected = {g["game_id"]: g for g in report["games"]}
    counts: Counter[str] = Counter()
    for game in fixtures:
        if expected.get(game.game_id) != asdict(game):
            raise ValueError("simulation fixture differs from the frozen historical manifest")
        counts[game.game_id] += 1
    if set(counts) != set(expected) or any(n != repetitions for n in counts.values()):
        raise ValueError("simulation fixture exposure differs from the reviewed slate")


def write_matchup_report(
    output: Path,
    slate: Slate,
    targets: Mapping[str, Mapping[str, Any]],
    *,
    source: Mapping[str, Any],
    engine: Mapping[str, Any],
    profiles_sha256: str,
    chart_qualifications: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Freeze the proposed slate; reports contain no PBP text or reference cells."""
    output = private_destination(output)
    if output.exists():
        raise ValueError("matchup report requires a new output path")
    for team, ids in slate.team_games.items():
        if list(ids) != targets.get(team, {}).get("game_ids"):
            raise ValueError("target IDs differ from reported simulation slate")
    fixtures = []
    for game in slate.games:
        home, away = slate.members[game.home], slate.members[game.away]
        fixtures.append(
            {
                **asdict(game),
                "home_name": home.name,
                "away_name": away.name,
                "home_conference": home.conference_name or home.conference,
                "away_conference": away.conference_name or away.conference,
                "inclusion_reason": slate.inclusion[game.game_id],
                "pbp_qualification": slate.evidence[game.game_id],
                "home_chart": chart_qualifications.get(game.home, {}),
                "away_chart": chart_qualifications.get(game.away, {}),
            }
        )
    team_index = {}
    for team, member in slate.members.items():
        selected = [g for g in slate.games if team in {g.home, g.away}]
        excluded = [g for g in slate.excluded if team in {g["home"], g["away"]}]
        team_index[team] = {
            **asdict(member),
            "offensive_game_ids": list(slate.team_games[team]),
            "defensive_game_ids": list(slate.team_games[team]),
            "opponents": sorted({g.away if g.home == team else g.home for g in selected}),
            "selected_games": len(selected),
            "excluded_actual_games": excluded,
            "full_schedule_games": len(selected) + len(excluded),
            "source_target_state": targets[team]["state"],
            "full_source_game_ids": targets[team]["full_source_game_ids"],
            "benchmark_status": chart_qualifications.get(team, {}).get(
                "benchmark_status", "not_a_reference_benchmark"
            ),
            "chart_qualification": chart_qualifications.get(team, {"state": "not_generated"}),
        }
    payload = {
        "schema_version": 1,
        "season": slate.season,
        "stage": "proposed_pre_run",
        "source": dict(source),
        "engine": dict(engine),
        "profiles_sha256": profiles_sha256,
        "source_sha256": canonical_hash(source),
        "engine_sha256": canonical_hash(engine),
        "games": [asdict(g) for g in slate.games],
        "fixtures": fixtures,
        "teams": team_index,
        "excluded": list(slate.excluded),
        "target_game_ids": sorted(g.game_id for g in slate.games),
        "historical_completeness_claim": False,
        "heldout_definition": "fresh simulation seeds are not source-held-out matchups",
    }
    payload["manifest_sha256"] = canonical_hash(payload)
    output.mkdir(parents=True, mode=0o700)
    write_json_new(output / "manifest.json", payload)
    write_json_new(output / "targets.json", targets)
    columns = [
        "season",
        "date",
        "game_id",
        "away",
        "away_name",
        "away_conference",
        "home",
        "home_name",
        "home_conference",
        "neutral_site",
        "postseason",
        "classification",
        "classification_evidence",
        "inclusion_reason",
        "pbp_qualification",
        "home_chart",
        "away_chart",
        "source_sha256",
        "engine_sha256",
        "profiles_sha256",
        "manifest_sha256",
    ]
    with (output / "matchups.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in fixtures:
            complete_row = {
                **row,
                **{
                    key: payload[key]
                    for key in (
                        "source_sha256",
                        "engine_sha256",
                        "profiles_sha256",
                        "manifest_sha256",
                    )
                },
            }
            writer.writerow(
                {
                    k: json.dumps(complete_row[k], sort_keys=True)
                    if isinstance(complete_row[k], dict)
                    else complete_row[k]
                    for k in columns
                }
            )
    lines = [
        f"# {slate.season} proposed historical calibration matchups",
        "",
        f"Selected physical fixtures: {len(fixtures)}. "
        f"Excluded actual fixtures: {len(slate.excluded)}.",
        f"Manifest SHA256: `{payload['manifest_sha256']}`",
        f"Source-contract SHA256: `{payload['source_sha256']}`",
        f"Engine/tool identity SHA256: `{payload['engine_sha256']}`",
        f"Profiles SHA256: `{profiles_sha256}`",
        "",
        "Review before broad calibration. Fresh simulation seeds are not source-held-out evidence.",
        "Sequence screening does not prove official event completeness. No invented opponents.",
        "",
        "## Team index",
        "",
        "| Team | Conference | Selected | Source-observed | Full schedule | State |",
        "|---|---|---:|---:|---:|---|",
    ]
    for team, entry in sorted(team_index.items(), key=lambda item: item[1]["name"]):
        lines.append(
            f"| [{entry['name']}](#team-{team}) | "
            f"{entry['conference_name'] or entry['conference']} | "
            f"{entry['selected_games']} | {len(entry['full_source_game_ids'])} | "
            f"{entry['full_schedule_games']} | "
            f"{entry['source_target_state']} |"
        )
    grouped = defaultdict(list)
    for fixture in fixtures:
        group = (
            fixture["home_conference"]
            if fixture["home_conference"] == fixture["away_conference"]
            else "Interconference and postseason"
        )
        grouped[str(group)].append(fixture)
    for group, rows in sorted(grouped.items()):
        lines += [
            "",
            f"## {group}",
            "",
            "| Date | Game ID | Away | Home | Neutral | Classification | "
            "Inclusion | PBP live | Warnings | Charts |",
            "|---|---|---|---|---|---|---|---:|---|---|",
        ]
        for row in rows:
            lines.append(
                f"| {row['date']} | {row['game_id']} | [{row['away_name']}](#team-{row['away']}) | "
                f"[{row['home_name']}](#team-{row['home']}) | {row['neutral_site']} | "
                f"{row['classification']} | {row['inclusion_reason']} | "
                f"{row['pbp_qualification'].get('live_plays', 'unknown')} | "
                f"{', '.join(row['pbp_qualification'].get('warnings', []))} | "
                f"{row['away_chart'].get('state', 'unknown')}/"
                f"{row['home_chart'].get('state', 'unknown')} |"
            )
    lines += [
        "",
        "## Excluded actual fixtures",
        "",
        "| Game ID | Away | Home | Reasons |",
        "|---|---|---|---|",
    ]
    for row in slate.excluded:
        away_name = slate.members[row["away"]].name if row["away"] in slate.members else "unknown"
        home_name = slate.members[row["home"]].name if row["home"] in slate.members else "unknown"
        lines.append(
            f"| {row['game_id']} | {away_name} ({row['away']}) | "
            f"{home_name} ({row['home']}) | "
            f"{', '.join(row['reasons'])} |"
        )
    for team, entry in sorted(team_index.items(), key=lambda item: item[1]["name"]):
        opponent_labels = [slate.members[t].name + " (" + t + ")" for t in entry["opponents"]]
        lines += [
            "",
            f'<a id="team-{team}"></a>',
            f"## {entry['name']}",
            "",
            f"OFF and DEF fixture IDs: {', '.join(entry['offensive_game_ids']) or 'none'}.",
            f"Opponents: {', '.join(opponent_labels) or 'none'}.",
            f"Selected/source-observed/full-schedule games: {entry['selected_games']}/"
            f"{len(entry['full_source_game_ids'])}/{entry['full_schedule_games']}.",
            f"Benchmark: {entry['benchmark_status']}.",
            "Excluded actual fixtures: "
            f"{', '.join(g['game_id'] for g in entry['excluded_actual_games']) or 'none'}.",
            f"Qualification: `{json.dumps(entry['chart_qualification'], sort_keys=True)}`",
        ]
    (output / "matchups.md").write_text("\n".join(lines) + "\n")
    for path in output.iterdir():
        path.chmod(0o600)
    return payload
