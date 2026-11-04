"""Engine-owned two-point announcements and review, with fictional charts."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import InvalidDecisionError
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def conversion_game(
    scorer: str, good: bool = True, clock: Clock | None = None, *, interception: bool = False
) -> SavedGame:
    charts = [
        replace(
            team_chart(
                label,
                season=2002,
                offense=100,
                defense=0,
                plays={
                    Play.TWO: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=0)
                    if interception
                    else yards(100 if good else 0)
                },
            ),
            special_teams=special_chart(
                label, kickoff=yards(40), kickoff_return=yards(10)
            ).special_teams,
        )
        for label in ("Home", "Away")
    ]
    game = SavedGame.new(
        *charts, home_id="2002/home", away_id="2002/away", seed=7, mode="regulation", clock=clock
    )
    winner = game.view().pending.chooser_side
    game.decide("toss:receive" if winner == scorer else "toss:kick")
    game.kick("kickoff")
    game.snap("1", "A")
    assert game.view().phase == "conversion_choice"
    return game


@pytest.mark.parametrize("scorer", ["home", "away"])
def test_attempt_is_announced_before_human_defense_and_retained(scorer: str) -> None:
    game = conversion_game(scorer)
    human = "away" if scorer == "home" else "home"
    game.decide("conversion:two")
    view, turn = game.coach_view(human)
    name = view.home if scorer == "home" else view.away
    assert turn.human_role == "defense" and not turn.automatic
    assert (
        turn.status
        == f"{name} is going for two. Choose your defense; the computer play stays hidden."
    )
    assert view.log[-1].announcements == (f"{name} is going for two.",)
    assert all(not key for key in (turn.actions.offense, turn.actions.special))


@pytest.mark.parametrize("scorer", ["home", "away"])
@pytest.mark.parametrize("good", [False, True])
def test_try_result_is_reviewable_before_automatic_kick_and_ack_is_pure(
    scorer: str, good: bool
) -> None:
    game = conversion_game(scorer, good)
    game.decide("conversion:two")
    report = game.snap("2", "A")
    before = game.view()
    assert report.outcome == ("two_point_good" if good else "two_point_failed")
    assert before.review.kind == "conversion"
    assert before.review.lines == (report.commentary,)
    assert before.review.action.key == "review:continue"
    tape = len(game._tape.rolls)
    charts = game._charts
    pending = loads_game(dumps_game(game), lambda key: charts[key.rsplit("/", 1)[-1]])
    assert pending.view().review == before.review
    game.action("review:continue")
    after = game.view()
    assert after.review is None
    assert (after.clock, after.log, after.score, after.statistics, after.scoring) == (
        before.clock,
        before.log,
        before.score,
        before.statistics,
        before.scoring,
    )
    assert len(game._tape.rolls) == tape
    text = dumps_game(game)
    charts = game._charts
    loaded = loads_game(text, lambda key: charts[key.rsplit("/", 1)[-1]])
    assert loaded.view() == after
    game.kick("kickoff")
    assert game.view().log[-2].outcome == report.outcome
    assert game.view().log[-3].announcements


@pytest.mark.parametrize("human", ["home", "away"])
def test_api_offers_same_review_facts_and_acknowledges_without_running_kick(
    tmp_path: Path, human: str
) -> None:
    scorer = "away" if human == "home" else "home"
    game = conversion_game(scorer)
    for chart in game._charts.values():
        write_team(tmp_path, chart)
    game.decide("conversion:two")
    game.snap("2", "A")
    client = TestClient(create_app(tmp_path))
    response = client.post("/api/games/load?human_side=" + human, content=dumps_game(game))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["turn"]["automatic"]
    assert body["view"]["review"]["kind"] == "conversion"
    before = body["view"]
    response = client.post(
        "/api/games/" + body["game_id"] + "/action?human_side=" + human,
        json={"action": "review:continue"},
    )
    assert response.status_code == 200, response.text
    after = response.json()["view"]
    assert after["review"] is None
    assert (after["log"], after["clock"], after["score"]) == (
        before["log"],
        before["clock"],
        before["score"],
    )


def test_invalid_review_ack_preserves_state_and_legacy_direct_kick_dismisses_review() -> None:
    game = conversion_game("home")
    before = (game.view(), game.revision, len(game._tape.rolls))
    with pytest.raises(InvalidDecisionError):
        game.action("review:continue")
    assert (game.view(), game.revision, len(game._tape.rolls)) == before
    game.decide("conversion:two")
    game.snap("2", "A")
    assert game.view().review is not None
    game.kick("kickoff")  # Existing controller/save journals need no new command.
    assert game.view().review is None


def test_final_try_result_remains_reviewable_without_creating_a_kickoff() -> None:
    game = conversion_game("home", clock=Clock(4, 20))
    game.decide("conversion:two")
    report = game.snap("2", "A")
    assert game.view().finished
    assert game.view().review.lines == (report.commentary,)
    game.coach_execute("away", "action", "review:continue")
    assert game.view().finished and game.view().review is None
    assert not game.view().actions.special


def test_pending_interception_does_not_claim_a_finished_try_result() -> None:
    game = conversion_game("home", interception=True)
    game.decide("conversion:two")
    report = game.snap("2", "A")
    assert report.pending and game.view().review is None
    report = game.decide("interception:decline")
    assert not report.pending
    assert game.view().review.lines == (report.commentary,)
