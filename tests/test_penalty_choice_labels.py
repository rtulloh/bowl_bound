"""Public-safe decision wording describes already prepared facts, never extra rolls."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.save_game import SavedGame, _view_digest, dumps_game, loads_game
from bowl_bound.session import PlaySession
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_models import provenance
from tests.test_session_penalties import chart, foul
from tests.test_special_teams import penalty, procedure, special_chart, with_roll


@pytest.mark.parametrize(
    "cell,spot,expected",
    [
        (yards(7), 65, "gain of 7 yards"),
        (yards(-1), 65, "loss of 1 yard"),
        (yards(0), 65, "no gain"),
        (yards(40), 20, "touchdown"),
        (yards(-7), 95, "safety"),
        (
            NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20),
            65,
            "interception 20 yards downfield; interception decision next",
        ),
        (
            NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3),
            65,
            "fumble 3 yards downfield; recovery still to be resolved",
        ),
    ],
)
def test_scrimmage_decline_names_prepared_result_without_committing_or_rolling(
    cell: NormalizedCell, spot: int, expected: str
) -> None:
    session = PlaySession.new(
        chart(foul(PenaltyTeam.OFFENSE), cell),
        team_chart("Away", defense=0),
        seed=1,
        start_yards_to_goal=spot,
    )
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0), sentinel]
    )
    before = session.view().state
    session.snap("1", "A", dice=dice)
    for _ in range(2):
        view = session.view()
        assert view.state == before and not view.log
        assert view.pending is not None
        decline = next(c for c in view.pending.choices if c.id == "decline")
        assert decline.label == f"Decline penalties: {expected}"
        assert decline.enabled
    assert dice.offensive() == sentinel


def test_pi_decline_names_incomplete_and_preserves_legacy_semantic_digest() -> None:
    pi = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 12),
    )

    session = PlaySession.new(team_chart("Home", plays={Play.ONE: pi}), team_chart("Away"), seed=1)
    session.snap("1", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))
    view = session.view()
    assert view.pending is not None
    decline = next(c for c in view.pending.choices if c.id == "decline")
    assert decline.label == "Decline penalties: incomplete pass"
    legacy = replace(
        view,
        pending=replace(
            view.pending,
            choices=tuple(
                replace(c, label="Decline penalties and take the result")
                if c.id == "decline"
                else c
                for c in view.pending.choices
            ),
        ),
    )
    assert _view_digest(view) == _view_digest(legacy)
    changed = replace(
        view,
        pending=replace(
            view.pending,
            choices=tuple(
                replace(c, enabled=False) if c.id == "decline" else c for c in view.pending.choices
            ),
        ),
    )
    assert _view_digest(view) != _view_digest(changed)
    assert session.decide("decline").state_after.down == 2


def test_punt_decline_names_distance_and_outstanding_reception_without_rolling() -> None:
    home = with_roll(special_chart("H", punt=yards(40)), "punt", 10, penalty(PenaltyTeam.OFFENSE))
    play = procedure(
        "punt", home, special_chart("A"), [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]
    )
    pending = play.begin()
    decline = next(c for c in pending.choices if c.id == "kick:decline")
    assert decline.label == "Decline penalties: 40-yard punt; reception still to be resolved"
    assert len(pending.trace) == 2
    result = play.decide("kick:decline")
    assert len(result.trace) == 2
    assert "kick:fair_catch" in [c.id for c in result.choices]


@pytest.mark.parametrize(
    "cell,expected",
    [
        (yards(8), "return of 8 yards"),
        (yards(-1), "return loss of 1 yard"),
        (NormalizedCell(ResultKind.NO_CHANGE, provenance()), "no gain on the return"),
        (NormalizedCell(ResultKind.TOUCHDOWN, provenance()), "touchdown"),
        (
            NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3),
            "fumble at +3 yards; recovery still to be resolved",
        ),
    ],
)
def test_return_penalty_names_the_already_rolled_result(
    cell: NormalizedCell, expected: str
) -> None:
    away = with_roll(
        special_chart("A", kickoff_return=cell), "kickoff_return", 10, penalty(PenaltyTeam.OFFENSE)
    )
    play = procedure(
        "kickoff",
        special_chart("H", kickoff=yards(45)),
        away,
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
    )
    pending = play.begin()
    decline = next(c for c in pending.choices if c.id == "kick:decline")
    assert decline.label == f"Decline penalties: {expected}"
    assert len(pending.trace) == 3


def test_api_and_pending_save_keep_result_wording_and_exact_continuation(tmp_path: Path) -> None:

    pi = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 12),
    )
    teams = (team_chart("Home", plays={Play.ONE: pi}), team_chart("Away"))
    for team in teams:
        write_team(tmp_path, team)
    client = TestClient(create_app(tmp_path))
    created = client.post("/api/games", json={"home": "2026/home", "away": "2026/away", "seed": 7})
    assert created.status_code == 200
    response = client.post(
        f"/api/games/{created.json()['game_id']}/snap", json={"play": "1", "defense": "A"}
    )
    assert response.status_code == 200
    choices = response.json()["view"]["pending"]["choices"]
    assert (
        next(c["label"] for c in choices if c["id"] == "decline")
        == "Decline penalties: incomplete pass"
    )

    game = SavedGame.new(*teams, home_id="2026/home", away_id="2026/away", seed=7)
    game.snap("1", "A")
    restored = loads_game(
        dumps_game(game), lambda key: teams[0] if key.endswith("home") else teams[1]
    )
    assert restored.view().pending == game.view().pending
    assert restored.decide("decline") == game.decide("decline")
    assert restored.snap("2", "F") == game.snap("2", "F")
