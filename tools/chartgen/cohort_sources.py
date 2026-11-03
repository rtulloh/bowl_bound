"""Source-neutral historical contracts from versioned SDV metadata snapshots."""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scope import HistoricalGame, TeamSeason


@dataclass(frozen=True)
class HistoricalContracts:
    members: Mapping[str, TeamSeason]
    games: tuple[HistoricalGame, ...]
    provenance: Mapping[str, Any]
    independent_membership_confirmation: bool = False


def _rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".csv":
        with path.open(newline="") as stream:
            return list(csv.DictReader(stream))
    if path.suffix != ".parquet":
        raise ValueError("historical metadata must be CSV or Parquet")
    try:
        import duckdb
    except ImportError as error:
        raise ValueError("Parquet metadata requires the optional generator dependency") from error
    relation = duckdb.read_parquet(str(path))
    return [dict(zip(relation.columns, row, strict=True)) for row in relation.fetchall()]


def _flag(value: Any, name: str) -> bool:
    if type(value) is bool:
        return value
    if str(value).lower() in {"true", "1"}:
        return True
    if str(value).lower() in {"false", "0"}:
        return False
    raise ValueError(f"historical {name} flag is unknown; do not invent a fixture")


def load_contracts(
    membership: Path,
    schedules: Path,
    groups: Path,
    *,
    season: int,
    source_urls: Mapping[str, str] | None = None,
) -> HistoricalContracts:
    """Resolve historical names/IDs; retain all FBS-involved expected fixtures."""
    names = {
        str(row["group_id"]): str(row["name"])
        for row in _rows(groups)
        if int(row["season"]) == season
    }
    members = {}
    for row in _rows(membership):
        if int(row["season"]) != season:
            raise ValueError("membership snapshot contains a different season")
        if str(row["team_id_source"]).lower() != "espn":
            raise ValueError("membership identity requires an explicit ESPN-ID crosswalk")
        identity = str(row["team_id"])
        if identity in members:
            raise ValueError("ambiguous duplicate historical team membership")
        conference = row.get("conference_id") or None
        members[identity] = TeamSeason(
            identity,
            str(row["team_name"]),
            conference,
            str(row.get("subdivision_id") or "unknown").removeprefix("cfb:"),
            names.get(conference),
        )
    games, ignored = [], 0
    for row in _rows(schedules):
        if int(row["season"]) != season:
            raise ValueError("schedule snapshot contains a different season")
        home, away = str(row["home_id"]), str(row["away_id"])
        if not any(t in members and members[t].subdivision == "fbs" for t in (home, away)):
            ignored += 1
            continue
        neutral = _flag(row["neutral_site"], "neutral_site")
        completed = _flag(row["completed"], "completed")
        postseason = str(row["season_type"]).lower() == "postseason"
        note = str(row.get("playoff_bowl_name") or row.get("notes") or "")
        classification = "regular"
        evidence = "source season_type and historical conference membership"
        if postseason:
            classification = "BCS" if "bcs" in note.lower() else "bowl"
            evidence = note or "source postseason flag; bowl name/BCS status unverified"
        elif (
            neutral
            and str(row.get("start_date") or "")[5:7] == "12"
            and home in members
            and away in members
            and members[home].conference == members[away].conference
            and "independent" not in (members[home].conference or "")
        ):
            classification = "conference_championship_unverified"
            evidence = "neutral December same-conference fixture; primary title label pending"
        games.append(
            HistoricalGame(
                str(row["game_id"]),
                season,
                home,
                away,
                neutral,
                postseason,
                completed,
                str(row.get("start_date") or ""),
                int(row["week"]) if row.get("week") not in {None, ""} else None,
                classification,
                evidence,
            )
        )
    if len({g.game_id for g in games}) != len(games):
        raise ValueError("schedule has duplicate game IDs")
    provenance: dict[str, Any] = {
        label: {
            "filename": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "url": (source_urls or {}).get(label),
        }
        for label, path in (("membership", membership), ("schedule", schedules), ("groups", groups))
    }
    provenance.update(
        independent_membership_confirmation=False,
        ignored_non_fbs_involved_fixtures=ignored,
        classification_limit="BCS/title labels require explicit primary corroboration",
    )
    return HistoricalContracts(
        members, tuple(sorted(games, key=lambda g: (g.date, g.game_id))), provenance
    )


def audit_espn_headers(
    raw: Path, contracts: HistoricalContracts, *, expected_raw_sha256: str
) -> dict[str, Any]:
    """Verify canonical home/away headers against the exact normalized raw snapshot.

    Header/final-score consistency is same-provider corroboration, not proof of
    event completeness. Absent headers stay unknown and cannot verify a fixture.
    """
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    if digest != expected_raw_sha256:
        raise ValueError("raw source hash differs from normalized provenance")
    columns = ["game_id", "season", "homeTeamId", "awayTeamId", "homeFinalScore", "awayFinalScore"]
    if raw.suffix == ".csv":
        rows = _rows(raw)
        if any(not set(columns) <= set(row) for row in rows):
            raise ValueError("raw header fields unavailable")
    elif raw.suffix == ".parquet":
        try:
            import duckdb
        except ImportError as error:
            raise ValueError("Parquet headers require optional generator dependency") from error
        relation = duckdb.read_parquet(str(raw))
        if not set(columns) <= set(relation.columns):
            raise ValueError("raw header fields unavailable")
        relation = relation.project(",".join('"' + name + '"' for name in columns)).distinct()
        rows = [dict(zip(columns, row, strict=True)) for row in relation.fetchall()]
    else:
        raise ValueError("raw header audit supports CSV or Parquet")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["game_id"])].append(row)
    result = {}
    for game in contracts.games:
        observed = grouped[game.game_id]
        known = [
            r
            for r in observed
            if r["homeTeamId"] not in {None, ""} and r["awayTeamId"] not in {None, ""}
        ]
        for row in known:
            if (str(row["homeTeamId"]), str(row["awayTeamId"]), int(row["season"])) != (
                game.home,
                game.away,
                game.season,
            ):
                raise ValueError("raw PBP canonical home/away/season differs from schedule")
        finals = sorted(
            {
                (int(r["homeFinalScore"]), int(r["awayFinalScore"]))
                for r in known
                if r["homeFinalScore"] not in {None, ""} and r["awayFinalScore"] not in {None, ""}
            }
        )
        if len(finals) > 1:
            raise ValueError("raw PBP final score headers disagree within one game")
        result[game.game_id] = {
            "canonical_sides_verified": bool(known),
            "final_score_headers": finals,
            "neutral_site": "not available in this PBP header contract",
        }
    return {
        "raw_sha256": digest,
        "games": result,
        "independent_official_confirmation": False,
        "event_completeness_claim": False,
    }
