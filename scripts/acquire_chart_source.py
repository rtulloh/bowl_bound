"""Fetch an ESPN core snapshot for local chart research; never a runtime service."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from tools.chartgen.espn_core import normalize_game, source_receipt
from tools.chartgen.private_io import private_destination
from tools.chartgen.source import write_normalized

BASE = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def acquire_source(
    season: int,
    output: Path,
    *,
    fetch: Callable[[str], bytes] = _fetch,
    workers: int = 4,
) -> dict[str, Any]:
    """Retain exact source bytes, normalized evidence and schedule coverage.

    Missing play feeds remain explicit gaps. Completion means every listed game
    was checked, not that every game's play-by-play exists or has been qualified.
    Every run requires a new destination and preserves partial evidence on error.
    """
    if season not in {2002, 2007} or not 1 <= workers <= 8:
        raise ValueError("choose season 2002/2007 and between one and eight workers")
    destination = private_destination(output)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    raw_directory = destination / "raw"
    raw_directory.mkdir(mode=0o700)
    report: dict[str, Any] = {"status": "incomplete", "season": season, "files": {}, "games": {}}

    def capture(url: str, filename: str) -> tuple[dict[str, Any], dict[str, Any]]:
        raw = fetch(url)
        document = json.loads(raw)
        with (raw_directory / filename).open("xb") as stream:
            stream.write(raw)
        return document, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    try:
        names: dict[str, str] = {}
        home_teams: dict[str, str] = {}
        expected: dict[str, set[str]] = defaultdict(set)
        for calendar_year in (season, season + 1):
            name = f"scoreboard-{calendar_year}.json"
            board, report["files"][name] = capture(
                f"{SCOREBOARD}?dates={calendar_year}&limit=1000", name
            )
            for game in board["events"]:
                for competitor in game["competitions"][0]["competitors"]:
                    team = competitor["team"]
                    if competitor.get("homeAway") == "home":
                        home_teams[game["id"]] = team["id"]
                    names[team["id"]] = (
                        team.get("location") or team.get("displayName") or team["id"]
                    )
                    if game.get("season", {}).get("year") == season:
                        expected[team["id"]].add(game["id"])
        games: set[str] = set()
        for season_type in (2, 3):
            name = f"events-{season_type}.json"
            inventory, report["files"][name] = capture(
                f"{BASE}/seasons/{season}/types/{season_type}/events?limit=1000", name
            )
            if inventory["pageCount"] != 1 or len(inventory["items"]) != inventory["count"]:
                raise ValueError("event inventory is truncated; pagination support is required")
            for item in inventory["items"]:
                game_id = item["$ref"].split("/events/")[-1].split("?")[0]
                if not game_id.isdecimal():
                    raise ValueError("source game identity must be numeric")
                games.add(game_id)

        def retrieve(game_id: str) -> tuple[str, dict[str, Any] | None, dict[str, Any]]:
            url = f"{BASE}/events/{game_id}/competitions/{game_id}/plays?limit=1000"
            try:
                document, receipt = capture(url, f"plays-{game_id}.json")
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                return game_id, None, {"url": url, "status": 404}
            if document["pageCount"] > 1 or len(document["items"]) != document["count"]:
                raise ValueError("play feed is truncated; pagination support is required")
            return game_id, document, {**receipt, "status": 200}

        events, hashes = [], {}
        observed: dict[str, set[str]] = defaultdict(set)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for game_id, document, receipt in pool.map(retrieve, sorted(games)):
                report["games"][game_id] = receipt
                if document is None or not document["items"]:
                    continue
                ids = {
                    p["id"] for row in document["items"] for p in row.get("teamParticipants", [])
                }
                if len(ids) != 2 or not ids <= names.keys():
                    raise ValueError("play feed requires two teams present in the schedule")
                normalized, receipt["normalization"] = normalize_game(
                    document["items"],
                    season=season,
                    game_id=game_id,
                    teams={team: names[team] for team in ids},
                    source_sha256=receipt["sha256"],
                    home_team=home_teams.get(game_id),
                )
                if normalized:
                    events.extend(normalized)
                    hashes[game_id] = receipt["sha256"]
                for event in normalized:
                    if event.kind in {"rush", "complete", "incomplete", "interception", "sack"}:
                        observed[event.team].add(game_id)
        write_normalized(destination / "normalized.json", events, source_receipt(events, hashes))
        participants = {team for event in events for team in (event.team, event.opponent)}
        coverage = {
            team: {
                "name": names[team],
                "observed_games": sorted(games),
                "expected_games": sorted(expected[team]),
                "missing_games": sorted(expected[team] - games),
            }
            for team, games in ((team, observed[team]) for team in sorted(participants))
        }
        teams = {team: names[team] for team in sorted(participants)}
        (destination / "teams.json").write_text(json.dumps(teams, indent=2) + "\n")
        (destination / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
        report.update(
            status="complete",
            games_checked=len(games),
            games_with_plays=len(hashes),
            normalized_events=len(events),
            publication_authorized=False,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.update(status="failed", error=type(error).__name__)
        raise
    finally:
        (destination / "acquisition.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    """Acquire an operator-requested source snapshot into ignored storage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, choices=(2002, 2007), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    result = acquire_source(args.season, args.output, workers=args.workers)
    print(
        f"Checked {result['games_checked']} games; {result['games_with_plays']} have play records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
