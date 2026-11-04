"""One engine-owned halftime recap across CLI, API and save boundaries."""

import io
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


def half_end(quarter: int = 2, choice: str = "toss:receive") -> SavedGame:
    charts = [
        replace(
            team_chart(name, season=2002, offense=0, defense=0),
            special_teams=special_chart(
                name, kickoff=yards(40), kickoff_return=yards(10)
            ).special_teams,
        )
        for name in ("Home", "Away")
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
    assert view.review.action.label == "Start second half"
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
    assert "Home — Q1 0, Q2 0, Half 0." in text
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
