"""Verify historical calendars independently of local chart bytes."""

import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from bowl_bound.season_templates import list_season_templates

BIG_EIGHT = {
    f"1972/{team}"
    for team in (
        "colorado",
        "iowa-state",
        "kansas",
        "kansas-state",
        "missouri",
        "nebraska",
        "oklahoma",
        "oklahoma-state",
    )
}


def test_missing_chart_suppresses_historical_template() -> None:
    assert list_season_templates({"2007/cedar-valley", "2007/harbor-tech"}) == []
    assert list_season_templates(BIG_EIGHT - {"1972/oklahoma"}) == []


def test_big_eight_contains_every_conference_matchup_once() -> None:
    (template,) = list_season_templates(BIG_EIGHT)
    assert template["id"] == "1972-big-eight"
    assert {team["conference"] for team in template["teams"]} == {"Big Eight"}
    fixtures = template["fixtures"]
    assert len(fixtures) == 28
    assert {
        frozenset((fixture["away_team_id"], fixture["home_team_id"])) for fixture in fixtures
    } == {frozenset(pair) for pair in combinations(BIG_EIGHT, 2)}
    assert all(fixture["conference_game"] for fixture in fixtures)
    appearances = Counter(
        (fixture["week"], fixture[side])
        for fixture in fixtures
        for side in ("away_team_id", "home_team_id")
    )
    assert max(appearances.values()) == 1
    assert Counter(team for _, team in appearances) == dict.fromkeys(BIG_EIGHT, 7)
    assert any(
        fixture["away_team_id"] == "1972/oklahoma"
        and fixture["home_team_id"] == "1972/nebraska"
        and fixture["date"] == "1972-11-23"
        for fixture in fixtures
    )


def test_catalog_calendars_preserve_historical_membership_and_venues() -> None:
    manifest = json.loads(
        (Path(__file__).parents[1] / "release/manifest.json").read_text(encoding="utf-8")
    )
    team_ids = {
        path.removeprefix("seasons/").removesuffix("/team.yaml")
        for path in manifest["runtime"]
        if path.startswith("seasons/") and path.endswith("/team.yaml")
    }
    by_year = {template["source_year"]: template for template in list_season_templates(team_ids)}
    for year, team_count, fixture_count in ((2002, 55, 236), (2007, 116, 640)):
        template = by_year[year]
        teams = {team["team_id"]: team["conference"] for team in template["teams"]}
        assert len(teams) == team_count
        assert teams[f"{year}/penn-state"] == "Big Ten"
        assert teams[f"{year}/alabama"] == "SEC"
        assert teams[f"{year}/notre-dame"] is None
        assert teams[f"{year}/miami"] == ("Big East" if year == 2002 else "ACC")
        fixtures = template["fixtures"]
        assert len(fixtures) == fixture_count
        assert len({fixture["source_id"] for fixture in fixtures}) == fixture_count
        assert {
            fixture[side] for fixture in fixtures for side in ("away_team_id", "home_team_id")
        } == teams.keys()
        appearances = Counter(
            (fixture["week"], fixture[side])
            for fixture in fixtures
            for side in ("away_team_id", "home_team_id")
        )
        assert max(appearances.values()) == 1
        assert all(
            not fixture["conference_game"]
            or teams[fixture["away_team_id"]] == teams[fixture["home_team_id"]] is not None
            for fixture in fixtures
        )
        (rivalry,) = (
            fixture
            for fixture in fixtures
            if {fixture["away_team_id"], fixture["home_team_id"]}
            == {f"{year}/ohio-state", f"{year}/michigan"}
        )
        assert rivalry["home_team_id"] == ("2002/ohio-state" if year == 2002 else "2007/michigan")
        assert rivalry["conference_game"]
        assert not {"result", "scores", "home_points", "away_points"} & rivalry.keys()

        (cross_conference,) = (
            fixture
            for fixture in fixtures
            if fixture["away_team_id"] == ("2002/washington" if year == 2002 else "2007/oregon")
            and fixture["home_team_id"] == f"{year}/michigan"
        )
        assert not cross_conference["conference_game"]
