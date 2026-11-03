"""Original fictional fixtures for the bounded historical calibration slate."""

from dataclasses import replace

import pytest

from tools.chartgen.evidence import Event
from tools.chartgen.scope import (
    HistoricalGame,
    TeamSeason,
    build_slate,
    qualified_games,
    slate_targets,
)


def members() -> dict[str, TeamSeason]:
    return {
        "a": TeamSeason("a", "Cedar Valley", "alpha", "fbs"),
        "b": TeamSeason("b", "Harbor Tech", "alpha", "fbs"),
        "c": TeamSeason("c", "Prairie College", "beta", "fbs"),
        "x": TeamSeason("x", "Pine College", "small", "fcs"),
    }


def game(identity: str, home: str, away: str, **kwargs: object) -> HistoricalGame:
    return HistoricalGame(identity, 2007, home, away, **kwargs)


def events(identity: str, home: str, away: str, gain: int = 4) -> list[Event]:
    return [
        Event(
            2007,
            identity,
            f"{side}-{period}-{index}",
            side,
            away if side == home else home,
            side,
            away if side == home else home,
            "rush" if index % 2 else "complete",
            gain,
            fumble=False,
            period=period,
            clock="0:20" if period == 4 else "5:00",
        )
        for side in (home, away)
        for period in range(1, 5)
        for index in range(10)
    ]


def test_slate_uses_only_actual_same_year_qualified_fixtures() -> None:
    schedule = [
        game("conference", "a", "b"),
        game("major", "c", "a", neutral_site=True),
        game("bowl", "b", "c", postseason=True, neutral_site=True),
        game("external", "a", "x"),
        game("missing-evidence", "b", "a"),
    ]
    evidence = {g.game_id: {"qualified": g.game_id != "missing-evidence"} for g in schedule}
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b", "c"},
        game_evidence=evidence,
        season=2007,
        major_conferences={"alpha", "beta"},
    )
    assert [g.game_id for g in slate.games] == ["bowl", "conference", "major"]
    assert slate.games[0].postseason and slate.games[0].neutral_site
    assert {x["game_id"] for x in slate.excluded} == {"external", "missing-evidence"}
    assert slate.team_games["a"] == ("conference", "major")
    assert slate.team_games["b"] == ("bowl", "conference")
    assert not any({g.home, g.away} == {"c", "x"} for g in slate.games)
    with pytest.raises(ValueError, match="season"):
        build_slate(
            [replace(schedule[0], season=2008)],
            members(),
            generated_teams={"a", "b"},
            game_evidence=evidence,
            season=2007,
        )


def test_presence_is_not_qualification_and_identity_mismatch_fails_closed() -> None:
    scheduled = game("g1", "a", "b")
    good = events("g1", "a", "b")
    assert qualified_games(good, [scheduled])["g1"]["qualified"]
    partial = qualified_games(good[:1], [scheduled])["g1"]
    assert not partial["qualified"] and "missing_regulation_periods" in partial["reasons"]
    missing = qualified_games([], [scheduled])["g1"]
    assert not missing["qualified"] and "missing_pbp" in missing["reasons"]
    bad = [replace(good[0], opponent="c"), *good[1:]]
    with pytest.raises(ValueError, match="opponent"):
        qualified_games(bad, [scheduled])


def test_administrative_end_marker_can_confirm_terminal_sequence() -> None:
    source = [replace(e, clock="2:00") for e in events("g", "a", "b")]
    source.append(replace(source[-1], event_id="end", kind="other", clock="0:00"))
    assert qualified_games(source, [game("g", "a", "b")])["g"]["qualified"]


def test_stale_snap_clocks_are_explicit_uncertainty_not_proof_of_missing_plays() -> None:
    source = [replace(e, clock="1:13") for e in events("g", "a", "b")]
    report = qualified_games(source, [game("g", "a", "b")])["g"]
    assert report["qualified"]
    assert "terminal_clock_stale_or_incomplete" in report["warnings"]
    assert not report["historical_completeness_claim"]


def test_targets_use_exact_selected_game_ids_for_offense_and_defense() -> None:
    schedule = [game("selected", "a", "b"), game("omitted", "a", "c")]
    source = events("selected", "a", "b", 4) + events("omitted", "a", "c", 40)
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha", "beta"},
    )
    targets = slate_targets(source, slate)
    assert targets["a"]["game_ids"] == ["selected"]
    assert targets["a"]["offense"]["rush_yards_per_attempt"] == 4
    assert targets["a"]["defense"]["rush_yards_per_attempt"] == 4
    assert targets["a"]["full_season_descriptive"]["rush_yards_per_attempt"] == 22
    assert targets["c"]["state"] == "no_eligible_games"


def test_chart_qualified_boundary_does_not_require_recursive_opponents() -> None:
    schedule = [game("ab", "a", "b"), game("bx", "b", "x")]
    source = events("ab", "a", "b") + events("bx", "b", "x")
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha"},
    )
    assert [g.game_id for g in slate.games] == ["ab"]
    assert slate.excluded[0]["game_id"] == "bx"
    assert "missing_chart:x" in slate.excluded[0]["reasons"]


def test_unknown_core_source_fact_remains_explicit_and_not_zero() -> None:
    source = [replace(e, fumble=None) for e in events("ab", "a", "b")]
    schedule = [game("ab", "a", "b")]
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha"},
    )
    target = slate_targets(source, slate)["a"]
    assert target["state"] == "partially_identifiable_targets"
    assert target["unidentifiable_source_metrics"] == {"offense": ["fumble"], "defense": ["fumble"]}
    assert "fumble" not in target["offense"] and "fumble" not in target["defense"]


def test_unidentified_offense_does_not_discard_identifiable_defense() -> None:
    source = [replace(e, kind="rush") if e.team == "a" else e for e in events("ab", "a", "b")]
    schedule = [game("ab", "a", "b")]
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha"},
    )
    target = slate_targets(source, slate)["a"]
    assert target["offense"] == {}
    assert target["defense"]["completion"] == 1.0
    assert target["unidentifiable_source_metrics"]["defense"] == []
    assert "offense" in target["source_target_limitations"]
