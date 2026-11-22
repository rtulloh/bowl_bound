"""Historical regular-season fixtures gated on the exact playable cohort."""

from collections.abc import Collection
from csv import reader
from typing import TypedDict

from .season_template_data import (
    BIG_EIGHT_FIXTURES,
    BIG_EIGHT_TEAMS,
    FIXTURES_2002,
    FIXTURES_2007,
    TEAMS_2002,
    TEAMS_2007,
)


class TemplateTeam(TypedDict):
    team_id: str
    conference: str | None


class TemplateFixture(TypedDict):
    week: int
    away_team_id: str
    home_team_id: str
    conference_game: bool
    date: str
    source_id: str | None


class SeasonTemplate(TypedDict):
    id: str
    name: str
    source_year: int
    teams: list[TemplateTeam]
    fixtures: list[TemplateFixture]
    coverage: str


_TEMPLATES = (
    (
        "1972-big-eight",
        "1972 Big Eight",
        1972,
        BIG_EIGHT_TEAMS,
        BIG_EIGHT_FIXTURES,
        "All 28 conference games. Nonconference games and bowls are excluded.",
    ),
    (
        "2002-catalog",
        "2002 NCAA (55 teams)",
        2002,
        TEAMS_2002,
        FIXTURES_2002,
        "Regular-season games between the 55 chart teams. "
        "Games against other teams, conference championships and bowls are excluded.",
    ),
    (
        "2007-catalog",
        "2007 NCAA (116 teams)",
        2007,
        TEAMS_2007,
        FIXTURES_2007,
        "Regular-season games between the 116 chart teams. "
        "Games against other teams, conference championships and bowls are excluded.",
    ),
)


def list_season_templates(available_team_ids: Collection[str]) -> list[SeasonTemplate]:
    """Return historical schedules whose full advertised cohort is installed."""
    available = set(available_team_ids)
    templates: list[SeasonTemplate] = []
    for template_id, name, year, team_rows, fixture_rows, coverage in _TEMPLATES:
        teams: list[TemplateTeam] = [
            {"team_id": f"{year}/{slug}", "conference": conference or None}
            for slug, conference in reader(team_rows.splitlines())
        ]
        if not available.issuperset(team["team_id"] for team in teams):
            continue
        fixtures: list[TemplateFixture] = [
            {
                "week": int(week),
                "away_team_id": f"{year}/{away}",
                "home_team_id": f"{year}/{home}",
                "conference_game": conference_game == "1",
                "date": date,
                "source_id": source_id or None,
            }
            for week, away, home, conference_game, date, source_id in reader(
                fixture_rows.splitlines()
            )
        ]
        templates.append(
            {
                "id": template_id,
                "name": name,
                "source_year": year,
                "teams": teams,
                "fixtures": fixtures,
                "coverage": coverage,
            }
        )
    return templates
