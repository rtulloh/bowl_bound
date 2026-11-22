"""Persistent played-season fixtures and aggregates from finalized engine boxes."""

from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from datetime import date as calendar_date
from fractions import Fraction
from typing import Any

from .statistics import TeamStatistics

SCHEMA_VERSION = 1
STAT_FIELDS = tuple(item.name for item in fields(TeamStatistics))
STAT_INPUTS = tuple(item.name for item in fields(TeamStatistics) if item.init)
SIGNED_FIELDS = {"rushing_yards", "passing_yards", "total_yards"}


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be nonempty text without surrounding whitespace")


def _require_integer(value: int, label: str, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer of at least {minimum}")


def _decode_statistics(payload: dict[str, Any]) -> TeamStatistics:
    if set(payload) not in (set(STAT_INPUTS), set(STAT_FIELDS)):
        raise ValueError("A result requires a complete engine statistics box")
    statistics = TeamStatistics(**{name: payload[name] for name in STAT_INPUTS})
    if any(payload[name] != getattr(statistics, name) for name in payload):
        raise ValueError("Game statistics totals are inconsistent")
    return statistics


@dataclass(frozen=True)
class SeasonTeam:
    """One chart edition and its conference in this competition."""

    id: str
    name: str
    year: int
    conference: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.id, "Team ID")
        _require_text(self.name, "Team name")
        _require_integer(self.year, "Chart year", 1)
        if self.conference is not None:
            _require_text(self.conference, "Conference")


@dataclass(frozen=True)
class SeasonFixture:
    """Scheduled opponents and whether their meeting counts in conference standings."""

    id: str
    week: int
    away: str
    home: str
    conference_game: bool = False
    date: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.id, "Fixture ID")
        _require_integer(self.week, "Fixture week", 1)
        _require_text(self.away, "Away team")
        _require_text(self.home, "Home team")
        if self.date is not None:
            _require_text(self.date, "Fixture date")
            if calendar_date.fromisoformat(self.date).isoformat() != self.date:
                raise ValueError("Fixture date must use YYYY-MM-DD")
        if self.away == self.home:
            raise ValueError("A fixture requires two different teams")
        if type(self.conference_game) is not bool:
            raise ValueError("Conference game must be a boolean")


@dataclass(frozen=True)
class SeasonResult:
    """Final engine score and complete statistical box for each team."""

    game_id: str
    away_score: int
    home_score: int
    away_statistics: TeamStatistics
    home_statistics: TeamStatistics

    def __post_init__(self) -> None:
        _require_text(self.game_id, "Game ID")
        _require_integer(self.away_score, "Away score")
        _require_integer(self.home_score, "Home score")
        for statistics in (self.away_statistics, self.home_statistics):
            if not isinstance(statistics, TeamStatistics):
                raise ValueError("A result requires an engine statistics box for each team")
            for name in STAT_FIELDS:
                value = getattr(statistics, name)
                if type(value) is not int or (name not in SIGNED_FIELDS and value < 0):
                    raise ValueError(f"Invalid game statistics field {name}")


@dataclass
class _TeamRecord:
    wins: int = 0
    losses: int = 0
    ties: int = 0

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def percentage(self) -> Fraction | None:
        if self.games:
            return Fraction(2 * self.wins + self.ties, 2 * self.games)
        return None

    def observe(self, scored: int, allowed: int) -> None:
        if scored > allowed:
            self.wins += 1
        elif scored < allowed:
            self.losses += 1
        else:
            self.ties += 1


@dataclass
class _TeamTotals:
    record: _TeamRecord = field(default_factory=_TeamRecord)
    conference: _TeamRecord = field(default_factory=_TeamRecord)
    points_for: int = 0
    points_against: int = 0
    offense: dict[str, int] = field(default_factory=lambda: dict.fromkeys(STAT_FIELDS, 0))
    defense: dict[str, int] = field(default_factory=lambda: dict.fromkeys(STAT_FIELDS, 0))

    def observe(
        self,
        scored: int,
        allowed: int,
        offense: TeamStatistics,
        defense: TeamStatistics,
        conference_game: bool,
    ) -> None:
        self.record.observe(scored, allowed)
        if conference_game:
            self.conference.observe(scored, allowed)
        self.points_for += scored
        self.points_against += allowed
        for name in STAT_FIELDS:
            self.offense[name] += getattr(offense, name)
            self.defense[name] += getattr(defense, name)

    def view(self, team: SeasonTeam) -> dict[str, Any]:
        games = self.record.games
        percentage = self.record.percentage
        conference_percentage = self.conference.percentage
        return {
            "team_id": team.id,
            "name": team.name,
            "year": team.year,
            "conference": team.conference,
            **asdict(self.record),
            "games_played": games,
            "win_percentage": None if percentage is None else float(percentage),
            "points_for": self.points_for,
            "points_against": self.points_against,
            "conference_wins": self.conference.wins,
            "conference_losses": self.conference.losses,
            "conference_ties": self.conference.ties,
            "conference_win_percentage": (
                None if conference_percentage is None else float(conference_percentage)
            ),
            "totals": self.offense,
            "per_game": {k: v / games if games else None for k, v in self.offense.items()},
            "allowed_totals": self.defense,
            "allowed_per_game": {k: v / games if games else None for k, v in self.defense.items()},
        }


@dataclass
class PlayedSeason:
    """A separately named competition with one accepted final box per fixture."""

    id: str
    name: str
    teams: tuple[SeasonTeam, ...]
    fixtures: tuple[SeasonFixture, ...]
    source_year: int | None = None
    results: dict[str, SeasonResult] = field(default_factory=dict)
    _fixtures: dict[str, SeasonFixture] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_text(self.id, "Season ID")
        _require_text(self.name, "Season name")
        if self.source_year is not None:
            _require_integer(self.source_year, "Source year", 1)
        teams = {item.id: item for item in self.teams}
        if len(teams) != len(self.teams):
            raise ValueError("Season contains a duplicate team ID")
        if len(teams) < 2:
            raise ValueError("A season requires at least two teams")
        if not self.fixtures:
            raise ValueError("A season requires at least one scheduled fixture")
        self._fixtures = {item.id: item for item in self.fixtures}
        if len(self._fixtures) != len(self.fixtures):
            raise ValueError("Season contains a duplicate fixture ID")
        appearances: set[tuple[int, str]] = set()
        for fixture in self.fixtures:
            sides = (fixture.away, fixture.home)
            if any(side not in teams for side in sides):
                raise ValueError("Fixture references a team outside this season")
            if fixture.conference_game:
                away, home = (teams[side].conference for side in sides)
                if away is None or away != home:
                    raise ValueError("A conference fixture requires teams in the same conference")
            for side in sides:
                appearance = (fixture.week, side)
                if appearance in appearances:
                    raise ValueError(f"Team {side} appears twice in week {fixture.week}")
                appearances.add(appearance)
        existing = self.results
        self.results = {}
        for fixture_id, result in existing.items():
            self.record(fixture_id, result)

    def record(self, fixture_id: str, result: SeasonResult) -> None:
        """Accept a final box once and reject accidental replacement or double posting."""
        if fixture_id not in self._fixtures:
            raise ValueError("Unknown fixture")
        if not isinstance(result, SeasonResult):
            raise ValueError("Expected a finalized game result")
        current = self.results.get(fixture_id)
        if current == result:
            return
        if current is not None:
            raise ValueError("Fixture is completed. Remove its result before replaying it")
        if any(existing.game_id == result.game_id for existing in self.results.values()):
            raise ValueError("Game is already recorded for another fixture")
        self.results[fixture_id] = result

    def remove_result(self, fixture_id: str, game_id: str) -> None:
        """Reopen a fixture only if its completed result still matches the request."""
        current = self.results.get(fixture_id)
        if current is None or current.game_id != game_id:
            raise ValueError("Completed fixture result has changed")
        del self.results[fixture_id]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical ledger, with aggregates rebuilt on demand."""
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "name": self.name,
            "source_year": self.source_year,
            "teams": [asdict(team) for team in self.teams],
            "fixtures": [asdict(fixture) for fixture in self.fixtures],
            "results": {fixture: asdict(result) for fixture, result in self.results.items()},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlayedSeason":
        """Restore and validate a portable played-season ledger."""
        if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
            raise ValueError("Unsupported played-season schema version")
        try:
            results = {}
            for fixture_id, item in payload["results"].items():
                results[fixture_id] = SeasonResult(
                    **{
                        **item,
                        "away_statistics": _decode_statistics(item["away_statistics"]),
                        "home_statistics": _decode_statistics(item["home_statistics"]),
                    }
                )
            return cls(
                id=payload["id"],
                name=payload["name"],
                source_year=payload["source_year"],
                teams=tuple(SeasonTeam(**item) for item in payload["teams"]),
                fixtures=tuple(SeasonFixture(**item) for item in payload["fixtures"]),
                results=results,
            )
        except (AttributeError, KeyError, TypeError) as exc:
            raise ValueError("Invalid played-season ledger") from exc

    def summary(self) -> dict[str, Any]:
        """Fold final boxes into overall/conference records, statistics and rankings."""
        totals = {team.id: _TeamTotals() for team in self.teams}
        conference_teams: dict[str, list[str]] = defaultdict(list)
        head_to_head: dict[str, dict[str, _TeamRecord]] = {
            team.id: defaultdict(_TeamRecord) for team in self.teams
        }
        for fixture in self.fixtures:
            result = self.results.get(fixture.id)
            if result is None:
                continue
            for team, opponent, scored, allowed, offense, defense in (
                (
                    fixture.away,
                    fixture.home,
                    result.away_score,
                    result.home_score,
                    result.away_statistics,
                    result.home_statistics,
                ),
                (
                    fixture.home,
                    fixture.away,
                    result.home_score,
                    result.away_score,
                    result.home_statistics,
                    result.away_statistics,
                ),
            ):
                totals[team].observe(scored, allowed, offense, defense, fixture.conference_game)
                head_to_head[team][opponent].observe(scored, allowed)
        for team in self.teams:
            if team.conference is not None:
                conference_teams[team.conference].append(team.id)
        team_order = {team.id: (team.name.casefold(), team.year, team.id) for team in self.teams}
        return {
            "teams": [totals[team.id].view(team) for team in self.teams],
            "conferences": [
                {
                    "name": name,
                    "team_ids": sorted(
                        members,
                        key=lambda team: (
                            -(
                                totals[team].conference.percentage
                                if totals[team].conference.games
                                else Fraction(-1)
                            ),
                            -totals[team].conference.wins,
                            -(totals[team].record.percentage or Fraction(0)),
                            team_order[team],
                        ),
                    ),
                }
                for name, members in sorted(
                    conference_teams.items(), key=lambda item: item[0].casefold()
                )
            ],
            "rankings": _rankings(totals, head_to_head, team_order),
        }


def _rankings(
    totals: dict[str, _TeamTotals],
    head_to_head: dict[str, dict[str, _TeamRecord]],
    team_order: dict[str, tuple[str, int, str]],
) -> list[dict[str, Any]]:
    # Every completed matchup weights that opponent's record outside the pairing.
    # Neutral .500 estimates opponents with no other results, including early weeks.
    ratings = []
    for team, opponents in head_to_head.items():
        own = totals[team].record
        if not own.games:
            continue
        weighted_strength = Fraction(0)
        for opponent, meetings in opponents.items():
            other = totals[opponent].record
            against_us = head_to_head[opponent][team]
            other_games = other.games - against_us.games
            other_points = 2 * (other.wins - against_us.wins) + other.ties - against_us.ties
            strength = Fraction(other_points, 2 * other_games) if other_games else Fraction(1, 2)
            weighted_strength += meetings.games * strength
        schedule = weighted_strength / own.games
        record = Fraction(2 * own.wins + own.ties, 2 * own.games)
        rating = (2 * record + schedule) / 3
        ratings.append((rating, record, schedule, team))

    def poll_order(
        item: tuple[Fraction, Fraction, Fraction, str],
    ) -> tuple[Fraction, Fraction, Fraction, Fraction, Fraction, Fraction, tuple[str, int, str]]:
        rating, record, schedule, team = item
        box = totals[team]
        games = box.record.games
        return (
            -rating,
            -record,
            -schedule,
            -Fraction(box.offense["total_yards"], games),
            -Fraction(box.points_for, games),
            Fraction(box.defense["total_yards"], games),
            team_order[team],
        )

    ordered = sorted(ratings, key=poll_order)[:25]
    return [
        {
            "team_id": team,
            "rank": rank,
            "strength_of_schedule": float(schedule),
            "rating": float(rating),
        }
        for rank, (rating, _, schedule, team) in enumerate(ordered, start=1)
    ]
