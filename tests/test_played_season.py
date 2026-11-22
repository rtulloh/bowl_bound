"""Season records use synthetic games and finalized engine boxes."""

from dataclasses import replace

import pytest

from bowl_bound.played_season import PlayedSeason, SeasonFixture, SeasonResult, SeasonTeam
from bowl_bound.statistics import TeamStatistics


def campaign() -> PlayedSeason:
    return PlayedSeason(
        "fall",
        "Fall league",
        (
            SeasonTeam("a", "A", 2007, "Big Eight"),
            SeasonTeam("b", "B", 2007, "Big Eight"),
            SeasonTeam("c", "C", 2002, "SEC"),
        ),
        (
            SeasonFixture("one", 1, "a", "b", True),
            SeasonFixture("two", 2, "c", "a"),
            SeasonFixture("three", 3, "b", "c"),
        ),
    )


def box(game: str, away: int, home: int) -> SeasonResult:
    return SeasonResult(
        game,
        away,
        home,
        TeamStatistics(rushing_attempts=1, rushing_yards=-5, sacks_taken=1, sack_yards_lost=5),
        TeamStatistics(passing_attempts=1, completions=1, passing_yards=20),
    )


def test_round_trip_and_reconcile_both_home_and_away_totals() -> None:
    season = campaign()
    first = box("g1", 14, 7)
    season.record("one", first)
    season.record("one", first)
    season.record("two", box("g2", 21, 21))
    restored = PlayedSeason.from_dict(season.to_dict())
    assert restored.to_dict() == season.to_dict()
    rows = {row["team_id"]: row for row in restored.summary()["teams"]}
    a = rows["a"]
    assert (a["wins"], a["losses"], a["ties"], a["games_played"]) == (1, 0, 1, 2)
    assert (a["points_for"], a["points_against"]) == (35, 28)
    assert (a["conference_wins"], a["conference_losses"], a["conference_ties"]) == (1, 0, 0)
    assert a["totals"]["rushing_yards"] == -5
    assert a["totals"]["passing_yards"] == 20
    assert a["totals"]["total_yards"] == 15
    assert a["per_game"]["total_yards"] == 7.5
    assert a["allowed_totals"]["sacks_taken"] == 1
    assert rows["c"]["conference_win_percentage"] is None


def test_completion_conflicts_and_explicit_correction() -> None:
    season = campaign()
    season.record("one", box("g1", 14, 7))
    with pytest.raises(ValueError, match="completed"):
        season.record("one", box("g1", 0, 7))
    with pytest.raises(ValueError, match="already"):
        season.record("two", box("g1", 0, 7))
    with pytest.raises(ValueError, match="changed"):
        season.remove_result("one", "different")
    season.remove_result("one", "g1")
    assert all(row["games_played"] == 0 for row in season.summary()["teams"])
    season.record("one", box("g2", 0, 7))
    assert not campaign().to_dict()["results"]


def test_rankings_use_opponents_other_results_and_tie_unplayed() -> None:
    season = campaign()
    assert season.summary()["rankings"] == []
    season.record("one", box("g1", 14, 7))
    season.record("two", box("g2", 0, 7))
    season.record("three", box("g3", 14, 7))
    rankings = season.summary()["rankings"]
    assert [row["team_id"] for row in rankings] == ["a", "b", "c"]
    assert rankings[0]["strength_of_schedule"] == 0.5
    assert rankings[1]["strength_of_schedule"] == 0.5
    assert rankings[2]["strength_of_schedule"] == 0.5


def test_rejects_bad_fixtures() -> None:
    season = campaign()
    with pytest.raises(ValueError, match="week"):
        replace(season, fixtures=(*season.fixtures, SeasonFixture("four", 1, "a", "c")))
    with pytest.raises(ValueError, match="different"):
        replace(season, fixtures=(SeasonFixture("one", 1, "a", "a"),))
    with pytest.raises(ValueError, match="conference"):
        replace(season, fixtures=(SeasonFixture("two", 2, "c", "a", True),))
    with pytest.raises(ValueError, match="duplicate"):
        replace(season, teams=(*season.teams, SeasonTeam("a", "A", 2007)))


def test_strength_of_schedule_changes_order_for_identical_records() -> None:
    season = PlayedSeason(
        "league",
        "League",
        tuple(SeasonTeam(team, team, 2007) for team in "abcdef"),
        (
            SeasonFixture("one", 1, "a", "c"),
            SeasonFixture("two", 1, "b", "d"),
            SeasonFixture("three", 2, "c", "e"),
            SeasonFixture("four", 2, "d", "f"),
        ),
    )
    for fixture, away, home in (("one", 14, 7), ("two", 14, 7), ("three", 14, 7), ("four", 7, 14)):
        season.record(fixture, box(fixture, away, home))
    rankings = {row["team_id"]: row for row in season.summary()["rankings"]}
    assert rankings["a"]["strength_of_schedule"] == 1
    assert rankings["b"]["strength_of_schedule"] == 0
    assert rankings["a"]["rank"] < rankings["b"]["rank"]


def test_incomplete_or_inconsistent_box_cannot_be_imported() -> None:
    season = campaign()
    season.record("one", box("g1", 14, 7))
    ledger = season.to_dict()
    ledger["results"]["one"]["home_statistics"]["total_yards"] = 45
    with pytest.raises(ValueError, match="inconsistent"):
        PlayedSeason.from_dict(ledger)
    del ledger["results"]["one"]["home_statistics"]["passing_yards"]
    with pytest.raises(ValueError, match="complete"):
        PlayedSeason.from_dict(ledger)
