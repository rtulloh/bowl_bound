"""One engine-owned halftime recap across CLI, API and save boundaries."""

import io
import re
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_conversion_presentation import conversion_game
from tests.test_special_teams import special_chart


def half_end(
    quarter: int = 2,
    choice: str = "toss:receive",
    names: tuple[str, str] = ("Home", "Away"),
) -> SavedGame:
    charts = [
        replace(
            team_chart(name, season=2002, offense=0, defense=0),
            special_teams=special_chart(
                name, kickoff=yards(40), kickoff_return=yards(10)
            ).special_teams,
        )
        for name in names
    ]
    game = SavedGame.new(
        *charts,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        mode="regulation",
        clock=Clock(quarter, 30),
    )
    game.decide(choice)
    game.kick("kickoff")
    game.snap("1", "A")
    game.decide("clock:runoff")
    return game


def test_halftime_provides_structured_box_score_without_parsing_recap_prose() -> None:
    game = half_end()
    view = game.view()
    recap = view.review.halftime
    assert recap.home.name == "Home"
    assert (recap.home.first, recap.home.second, recap.home.total) == (0, 0, 0)
    assert recap.away.name == "Away"
    assert (recap.away.first, recap.away.second, recap.away.total) == (0, 0, 0)
    assert recap.statistics == view.statistics.rows
    assert recap.scoring == ("No scoring in the first half.",)
    assert recap.summary == "Game is tied"
    assert recap.kickoff == view.review.lines[-1]
    restored = loads_game(dumps_game(game), lambda key: game._charts[key.rsplit("/", 1)[-1]])
    assert restored.view().review.halftime == recap


def test_cli_uses_paydirt_boxed_sections_and_aligned_team_columns() -> None:
    game = half_end()
    output = io.StringIO()
    cli = TerminalGame(game, lambda key: game._charts[key.rsplit("/", 1)[-1]], output=output)
    cli.display()
    text = output.getvalue()
    assert "+" + "-" * 70 + "+" in text
    assert re.search(r"\|\s+HALFTIME STATS\s+\|", text)
    assert re.search(r"\|\s+TEAM\s+\|\s+Q1\s+Q2\s+\|\s+TOTAL\s+\|", text)
    assert re.search(r"\|\s+Away\s+\|\s+0\s+0\s+\|\s+0\s+\|", text)
    assert re.search(r"\|\s+Home\s+\|\s+0\s+0\s+\|\s+0\s+\|", text)
    assert text.index("Away") < text.index("Home")
    assert "SCORING SUMMARY" in text and "TEAM STATISTICS" in text
    assert re.search(r"\|\s+Statistic\s+\|\s+Away\s+\|\s+Home\s+\|", text)
    recap = half_end().view().review
    for row in recap.halftime.statistics:
        assert re.search(
            r"\|\s+"
            + re.escape(row.label)
            + r"\s+\|\s+"
            + re.escape(row.away)
            + r"\s+\|\s+"
            + re.escape(row.home)
            + r"\s+\|",
            text,
        )
    assert "No scoring in the first half." in text
    assert recap.halftime.kickoff in text
    assert "Home — Q1" not in text


def test_cli_box_score_preserves_long_team_names_and_equal_width_borders() -> None:
    names = ("A Very Long Fictional Home Team Name", "Another Long Fictional Away Team")
    game = half_end(names=names)
    output = io.StringIO()
    cli = TerminalGame(game, lambda key: game._charts[key.rsplit("/", 1)[-1]], output=output)
    cli._present_halftime()
    text = output.getvalue()
    assert all(name in text for name in names)
    boxed = [line for line in text.splitlines() if line.startswith(("+", "|"))]
    assert len({len(line) for line in boxed}) == 1
    assert "Total offense yards" in text


def test_halftime_box_score_keeps_scoring_events_and_engine_leader() -> None:
    game = conversion_game("home", clock=Clock(2, 20))
    game.decide("conversion:kick")
    recap = game.view().review.halftime
    assert recap.home.total == 7 and recap.away.total == 0
    assert recap.summary == "Home leads"
    assert any("Home touchdown +6" in line for line in recap.scoring)
    assert any("Home PAT +1" in line for line in recap.scoring)


@pytest.mark.parametrize("good", [False, True])
def test_boxed_halftime_retains_the_final_two_point_result(good: bool) -> None:
    game = conversion_game("away", good=good, clock=Clock(2, 20))
    game.decide("conversion:two")
    report = game.snap("2", "A")
    recap = game.view().review.halftime
    assert recap.result == report.commentary
    assert recap.summary == "Away leads"
    assert recap.away.total == (8 if good else 6)
    output = io.StringIO()
    cli = TerminalGame(game, lambda key: game._charts[key.rsplit("/", 1)[-1]], output=output)
    cli._present_halftime()
    assert report.commentary in output.getvalue()


@pytest.mark.parametrize("choice", ["toss:receive", "toss:kick"])
def test_engine_halftime_review_precedes_reciprocal_kick_without_new_football(choice: str) -> None:
    game = half_end(choice=choice)
    view = game.view()
    assert view.review.kind == "halftime"
    assert view.review.title == "HALFTIME"
    assert "Home — Q1 0, Q2 0, Half 0." in view.review.lines
    assert "Away — Q1 0, Q2 0, Half 0." in view.review.lines
    assert "First-half scoring: none." in view.review.lines
    assert any(line.startswith("Total offensive plays:") for line in view.review.lines)
    assert view.review.action.label == "START 2ND HALF"
    kicker = view.state.possession_name
    receiver = view.home if kicker == view.away else view.away
    assert view.review.lines[-1] == f"{kicker} kicks to {receiver} to start the second half."
    assert view.clock.quarter == 3 and view.clock.remaining == 900
    before = (view.log, view.clock, view.score, view.statistics, len(game._tape.rolls))
    restored = loads_game(dumps_game(game), lambda key: game._charts[key.rsplit("/", 1)[-1]])
    assert restored.view().review == view.review
    game.action(view.review.action.key)
    assert game.view().review is None
    assert (
        game.view().log,
        game.view().clock,
        game.view().score,
        game.view().statistics,
        len(game._tape.rolls),
    ) == before
    restored = loads_game(dumps_game(game), lambda key: game._charts[key.rsplit("/", 1)[-1]])
    assert restored.view().review is None


def test_q1_break_is_not_a_halftime_recap() -> None:
    game = half_end(1)
    assert game.view().clock.quarter == 2
    assert game.view().review is None


@pytest.mark.parametrize("two", [False, True])
def test_half_waits_for_conversion_then_includes_scoring_and_result(two: bool) -> None:
    game = conversion_game("home", clock=Clock(2, 20))
    assert game.view().clock.remaining == 0 and game.view().review is None
    game.decide("conversion:two" if two else "conversion:kick")
    if two:
        assert game.view().review is None
        report = game.snap("2", "A")
    view = game.view()
    assert view.review.kind == "halftime"
    assert any("Home touchdown +6" in line for line in view.review.lines)
    assert any(
        "Home " + ("two-point conversion +2" if two else "PAT +1") in line
        for line in view.review.lines
    )
    assert any(f"Half {8 if two else 7}." in line for line in view.review.lines)
    if two:
        assert view.review.lines[0] == report.commentary


@pytest.mark.parametrize("human", ["home", "away"])
def test_cli_prints_recap_once_before_automatic_kick_and_resume(human: str) -> None:
    game = half_end()
    output = io.StringIO()
    cli = TerminalGame(
        game, lambda key: game._charts[key.rsplit("/", 1)[-1]], human_side=human, output=output
    )
    cli.advance_computer()
    cli.display()
    text = output.getvalue()
    assert text.count("HALFTIME") == 1
    assert re.search(r"\|\s+Home\s+\|\s+0\s+0\s+\|\s+0\s+\|", text)
    if "Kickoff" in text:
        assert text.index("HALFTIME") < text.index("Kickoff")
    assert game.view().review is None
    cli.display()
    assert output.getvalue().count("HALFTIME") == 1


@pytest.mark.parametrize("human", [None, "home", "away"])
def test_api_serializes_shared_review_for_manual_or_computer_kick(
    tmp_path: Path, human: str | None
) -> None:
    game = half_end()
    for chart in game._charts.values():
        write_team(tmp_path, chart)
    suffix = "?human_side=" + human if human else ""
    client = TestClient(create_app(tmp_path))
    response = client.post("/api/games/load" + suffix, content=dumps_game(game))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["view"]["review"]["lines"] == list(game.view().review.lines)
    recap = body["view"]["review"]["halftime"]
    assert recap["home"] == {"name": "Home", "first": 0, "second": 0, "total": 0}
    assert recap["away"] == {"name": "Away", "first": 0, "second": 0, "total": 0}
    assert recap["statistics"] == body["view"]["statistics"]["rows"]
    response = client.post(
        "/api/games/" + body["game_id"] + "/action" + suffix, json={"action": "review:continue"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["view"]["review"] is None


def test_first_quarter_points_are_not_misattributed_to_second_quarter() -> None:
    game = conversion_game("home", clock=Clock(1, 20))
    game.decide("conversion:kick")
    assert game.view().clock.quarter == 2 and game.view().review is None
    for _ in range(200):
        view = game.view()
        if view.review is not None:
            break
        if view.phase == "clock_choice":
            game.decide("clock:runoff")
        elif view.phase == "kickoff":
            game.kick("kickoff")
        elif view.phase == "conversion_choice":
            game.decide("conversion:kick")
        else:
            game.snap("1", "A")
    else:
        pytest.fail("synthetic second quarter did not reach halftime")
    view = game.view()
    assert view.review.kind == "halftime"
    assert f"Home — Q1 7, Q2 {view.score.home - 7}, Half {view.score.home}." in view.review.lines
    assert f"Away — Q1 0, Q2 {view.score.away}, Half {view.score.away}." in view.review.lines
    assert view.review.halftime.home.first == 7
    assert view.review.halftime.home.second == view.score.home - 7
    assert view.review.halftime.away.first == 0
    assert view.review.halftime.away.second == view.score.away


def test_pending_defensive_penalty_and_untimed_down_finish_before_recap() -> None:
    from bowl_bound.models import (
        NormalizedCell,
        PenaltyCode,
        PenaltyData,
        PenaltyTeam,
        Play,
        ResultKind,
    )
    from tests.test_models import provenance
    from tests.test_regulation import kickoff, new_game, snap

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8),
    )
    game = new_game(clock=Clock(2, 10), plays={Play.EIGHT: foul})
    kickoff(game)
    snap(game, "8")
    assert game.view().pending is not None and game.view().review is None
    game.decide("accept:0:previous")
    assert game.view().untimed_down and game.view().review is None
    snap(game)
    assert game.view().clock.quarter == 3
    assert game.view().review.kind == "halftime"
