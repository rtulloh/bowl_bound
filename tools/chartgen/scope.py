"""Historical fixtures and exactly matched target scopes, without invented opponents."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any

from .evidence import Event
from .refine import source_targets

MAJOR_CONFERENCES = frozenset(
    {
        "cfb:acc",
        "cfb:big-12",
        "cfb:big-east",
        "cfb:big-ten",
        "cfb:pac-12",
        "cfb:sec",
        "cfb:fbs-independents",
    }
)
CORE_METRICS = frozenset(
    {
        "completion",
        "interception",
        "sack",
        "fumble",
        "rush_yards_per_attempt",
        "pass_yards_per_attempt",
    }
)
LIVE_KINDS = frozenset({"rush", "complete", "incomplete", "interception", "sack"})


@dataclass(frozen=True)
class TeamSeason:
    identity: str
    name: str
    conference: str | None
    subdivision: str
    conference_name: str | None = None
    independently_corroborated: bool = False


@dataclass(frozen=True)
class HistoricalGame:
    game_id: str
    season: int
    home: str
    away: str
    neutral_site: bool = False
    postseason: bool = False
    completed: bool = True
    date: str = ""
    week: int | None = None
    classification: str = "regular"
    classification_evidence: str = "declared source contract"

    def __post_init__(self) -> None:
        if not self.game_id or not self.home or not self.away or self.home == self.away:
            raise ValueError("historical fixture requires distinct opponent identities")
        if type(self.season) is not int:
            raise ValueError("historical fixture season must be an integer")
        if any(type(v) is not bool for v in (self.neutral_site, self.postseason, self.completed)):
            raise ValueError(
                "historical fixture neutral/postseason/completed flags must be booleans"
            )


@dataclass(frozen=True)
class Slate:
    season: int
    games: tuple[HistoricalGame, ...]
    excluded: tuple[dict[str, Any], ...]
    members: Mapping[str, TeamSeason]
    team_games: Mapping[str, tuple[str, ...]]
    inclusion: Mapping[str, str]
    evidence: Mapping[str, Mapping[str, Any]]


def qualified_games(
    events: Sequence[Event], schedule: Sequence[HistoricalGame]
) -> dict[str, dict[str, Any]]:
    """Screen sequences; never equate this with official event completeness."""
    contracts = {g.game_id: g for g in schedule}
    if len(contracts) != len(schedule):
        raise ValueError("duplicate historical game identity")
    grouped: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        game = contracts.get(event.game_id)
        if game is None:
            continue
        if event.season != game.season:
            raise ValueError("source game season differs from historical schedule")
        if {event.team, event.opponent} != {game.home, game.away}:
            raise ValueError(f"source opponent identity differs from schedule for {game.game_id}")
        grouped[event.game_id].append(event)
    report = {}
    for game in schedule:
        rows = grouped[game.game_id]
        live = [e for e in rows if e.kind in LIVE_KINDS and not e.no_play]
        periods = sorted({e.period for e in live if e.period is not None})
        sides = {t: sum(e.team == t for e in live) for t in (game.home, game.away)}
        reasons, warnings = [], ["official_event_completeness_unverified"]
        if not rows:
            reasons.append("missing_pbp")
        if not {1, 2, 3, 4} <= set(periods):
            reasons.append("missing_regulation_periods")
        if any(n < 20 for n in sides.values()):
            reasons.append("sparse_live_play_sequence")
        missing = sum(e.kind in {"rush", "complete", "sack"} and e.yards is None for e in live)
        if missing:
            reasons.append("missing_primary_yardage")
        seconds = []
        for e in rows:
            if e.period is None or e.period < 4 or not e.clock:
                continue
            try:
                minute, second = e.clock.split(":")
                seconds.append(60 * int(minute) + int(second))
            except (ValueError, TypeError):
                warnings.append("unparsed_terminal_clock")
        if seconds and min(seconds) > 60:
            warnings.append("terminal_clock_stale_or_incomplete")
        elif not seconds:
            warnings.append("terminal_clock_unverified")
        report[game.game_id] = {
            "qualified": not reasons,
            "qualification": "sequence_screen_only" if not reasons else "insufficient_evidence",
            "reasons": reasons,
            "warnings": sorted(set(warnings)),
            "events": len(rows),
            "live_plays": len(live),
            "periods": periods,
            "live_plays_by_team": sides,
            "missing_primary_yardage": missing,
            "historical_completeness_claim": False,
        }
    return report


def build_slate(
    schedule: Sequence[HistoricalGame],
    members: Mapping[str, TeamSeason],
    *,
    generated_teams: set[str],
    game_evidence: Mapping[str, Mapping[str, Any]],
    season: int,
    major_conferences: set[str] | frozenset[str] = MAJOR_CONFERENCES,
) -> Slate:
    """Select actual conference/major/bowl fixtures with qualified chart endpoints."""
    seen, selected, excluded, inclusion = set(), [], [], {}
    team_games: dict[str, list[str]] = {t: [] for t in members}
    for game in sorted(schedule, key=lambda g: (g.date, g.game_id)):
        if game.season != season:
            raise ValueError("historical schedule contains a different season")
        if game.game_id in seen:
            raise ValueError("duplicate historical game identity")
        seen.add(game.game_id)
        reasons = []
        for identity in (game.home, game.away):
            if identity not in members:
                reasons.append(f"unknown_membership:{identity}")
            if identity not in generated_teams:
                reasons.append(f"missing_chart:{identity}")
        if not game.completed:
            reasons.append("not_completed")
        evidence = game_evidence.get(game.game_id, {})
        if not evidence.get("qualified"):
            reasons.extend(evidence.get("reasons", ["unqualified_pbp"]))
        reason = None
        if game.home in members and game.away in members:
            home, away = members[game.home], members[game.away]
            major = all(t.conference in major_conferences for t in (home, away))
            same = home.conference == away.conference and home.conference is not None
            independent = bool(home.conference and "independent" in home.conference)
            if game.postseason and all(t.subdivision == "fbs" for t in (home, away)):
                reason = "actual_bowl_or_bcs_with_qualified_charts"
            elif major and same and not independent:
                reason = "actual_historical_conference_matchup"
            elif major:
                reason = "actual_major_interconference_matchup"
        if reason is None:
            reasons.append("outside_requested_matchup_scope")
        if reasons:
            excluded.append({**asdict(game), "reasons": sorted(set(reasons))})
        else:
            selected.append(game)
            inclusion[game.game_id] = reason
            for team in (game.home, game.away):
                team_games[team].append(game.game_id)
    return Slate(
        season,
        tuple(selected),
        tuple(excluded),
        dict(members),
        {t: tuple(sorted(ids)) for t, ids in team_games.items()},
        inclusion,
        game_evidence,
    )


def slate_targets(events: Sequence[Event], slate: Slate) -> dict[str, dict[str, Any]]:
    """Use the identical selected fixture IDs for each team's OFF and DEF targets."""
    expected = {g.game_id: g for g in slate.games}
    by_team: dict[str, list[Event]] = defaultdict(list)
    selected: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        if event.season != slate.season:
            raise ValueError("source season differs from slate")
        by_team[event.team].append(event)
        by_team[event.opponent].append(event)
        if event.game_id in expected:
            game = expected[event.game_id]
            if {event.team, event.opponent} != {game.home, game.away}:
                raise ValueError("source opponent differs from selected fixture")
            selected[event.team].append(event)
            selected[event.opponent].append(event)
    targets = {}
    for team in slate.members:
        rows = selected[team]
        ids = sorted({e.game_id for e in rows})
        if ids != list(slate.team_games[team]):
            raise ValueError("target source game IDs differ from selected simulation slate")
        record: dict[str, Any] = {
            "game_ids": ids,
            "state": "no_eligible_games",
            "offense": {},
            "defense": {},
            "full_season_descriptive": {},
            "full_source_game_ids": sorted({e.game_id for e in by_team[team]}),
        }
        try:
            record["full_season_descriptive"] = source_targets(by_team[team], [team])
        except ValueError as error:
            record["full_season_limitation"] = str(error)
        if rows:
            try:
                record["offense"] = source_targets(rows, [team])
                reversed_rows = [replace(e, team=e.opponent, opponent=e.team) for e in rows]
                record["defense"] = {
                    k: v
                    for k, v in source_targets(reversed_rows, [team]).items()
                    if k in CORE_METRICS
                }
                record["state"] = "restricted_source_targets"
            except ValueError as error:
                record["state"], record["limitation"] = "unidentifiable_targets", str(error)
        targets[team] = record
    return targets
