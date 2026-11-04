"""Pending interception locations use synthetic engine facts, never trace parsing."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.save_game import dumps_game, loads_game
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, team_chart, write_team
from tests.test_cli import new_game, saved_facts, terminal
from tests.test_models import provenance


@pytest.mark.parametrize("possession", [Possession.HOME, Possession.AWAY])
@pytest.mark.parametrize("call", ["9", "RZDZ"])
@pytest.mark.parametrize(
    "yards_to_goal,location,spot",
    [
        (68, 19, "{defender} own 49"),
        (68, 0, "{defender} opponent 32"),
        (20, 20, "{defender} goal line"),
        (20, 24, "{defender} end zone (4 yards deep)"),
        (65, -35, "{offense} goal line"),
        (65, -39, "{offense} end zone (4 yards deep)"),
    ],
)
def test_pending_context_shows_known_interception_spot_without_resolving_return(
    possession: Possession, call: str, yards_to_goal: int, location: int, spot: str
) -> None:
    interception = NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=location)
    home, away = (
        team_chart(name, plays={Play.NINE: interception}) for name in ("Alpha Tech", "Beta State")
    )
    session = PlaySession.for_analysis(home, away, FieldState(possession, yards_to_goal, 2, 7))
    before = session.view()
    roll = OffensiveRoll(1, 2, 3)
    dice = ScriptedDice(
        [roll, DefensiveRoll(1, 0)] if call == "9" else [roll, roll, DefensiveRoll(1, 0)]
    )
    report = session.snap(call, "A", dice=dice)
    if call == "RZDZ":
        report = session.decide("razzle:9:15", dice=dice)
    view = session.view()
    defender, offense = (
        (away.name, home.name) if possession is Possession.HOME else (home.name, away.name)
    )
    assert spot.format(defender=defender, offense=offense) in view.pending.decision_context
    assert "pending" in view.pending.decision_context.lower()
    assert report.pending and report.outcome == "interception_pending"
    assert view.state == before.state and view.score == before.score
    assert view.log == before.log == ()
    assert [choice.id for choice in view.pending.choices] == [
        "interception:return",
        "interception:decline",
    ]
    assert session.view() == view


@pytest.mark.parametrize("compact", [False, True])
def test_cli_puts_engine_interception_context_above_the_choices(compact: bool) -> None:
    game = new_game()
    game.execute_with_view("snap", ["9", "A"])
    app = terminal(game, "away", compact=compact)
    before = saved_facts(game)
    assert not app.command("?")
    text = app.output.getvalue()
    assert "Beta State own 45" in text
    assert text.index("Beta State own 45") < text.index("Return the interception")
    assert saved_facts(game) == before


def test_pre_context_interception_save_loads_without_changing_replay() -> None:
    app = terminal(new_game(), "away")
    raw = (Path(__file__).parent / "fixtures" / "cli067-pending-interception.json").read_text()
    restored = loads_game(raw, app.load_team)
    assert "Beta State own 45" in restored.view().pending.decision_context
    before = saved_facts(restored)
    assert saved_facts(loads_game(dumps_game(restored), app.load_team)) == before
    restored.execute_with_view("decide", ["interception:return"])
    reference = new_game()
    reference.execute_with_view("snap", ["9", "A"])
    reference.execute_with_view("decide", ["interception:return"])
    assert restored.view() == reference.view()


def test_api_transports_known_spot_while_committed_field_stays_unchanged(tmp_path: Path) -> None:
    for chart in default_teams():
        write_team(tmp_path, chart)
    client = TestClient(create_app(tmp_path))
    started = client.post(
        "/api/games", json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7}
    ).json()
    path = f"/api/games/{started['game_id']}"
    response = client.post(path + "/snap", json={"play": "9", "defense": "A"})
    assert response.status_code == 200
    pending = response.json()
    assert "Beta State own 45" in pending["view"]["pending"]["decision_context"]
    assert pending["view"]["state"] == started["view"]["state"]
    assert client.get(path).json()["view"] == pending["view"]
