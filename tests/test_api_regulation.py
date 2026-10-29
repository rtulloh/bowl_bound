"""API transports regulation decisions and clock, without implementing rules."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import default_teams, write_team
from tests.test_special_teams import special_chart, yards


def test_regulation_creation_toss_kick_and_clock_action(tmp_path: Path) -> None:
    for chart in default_teams():
        kicks = special_chart(chart.name, kickoff=yards(70))
        write_team(tmp_path, replace(chart, season=2002, special_teams=kicks.special_teams))
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/api/games",
        json={
            "home": "2002/alpha-tech",
            "away": "2002/beta-state",
            "seed": 7,
            "mode": "regulation",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    path = f"/api/games/{data['game_id']}"
    assert data["view"]["phase"] == "opening_choice"
    assert data["view"]["clock"]["label"] == "15:00"
    assert client.post(path + "/snap", json={"play": "1", "defense": "A"}).status_code == 409
    toss = client.post(path + "/decision", json={"choice": "toss:receive"})
    assert toss.status_code == 200 and toss.json()["report"] is None
    kicked = client.post(path + "/kick", json={"action": "kickoff"})
    assert kicked.status_code == 200
    received = client.post(path + "/decision", json={"choice": "kick:touchback"})
    assert received.status_code == 200
    result = client.post(path + "/action", json={"action": "kneel"})
    assert result.status_code == 200 and result.json()["view"]["phase"] == "clock_choice"
    assert result.json()["report"]["yards"] == -2
    clock_view = result.json()["view"]
    assert clock_view["clock_optional"]
    assert clock_view["clock_modifiers"][0]["label"] == "None"
    timed = client.post(path + "/decision", json={"choice": "clock:timeout:home"})
    assert timed.status_code == 200
    assert timed.json()["view"]["clock"]["remaining"] == 890
    assert timed.json()["view"]["clock"]["timeouts"] == [2, 3]
    assert client.post(path + "/action", json={"action": "spike"}).status_code == 422
    assert client.post(path + "/action", json={"action": "sneak"}).status_code == 422
    # No clock decision request is required between successive ordinary plays.
    assert client.post(path + "/action", json={"action": "kneel"}).status_code == 200
    continued = client.post(path + "/snap", json={"play": "1", "defense": "A"})
    assert continued.status_code == 200
    view = continued.json()["view"]
    assert view["timing_log"][2]["seconds"] == 30
    assert view["timing_log"][2]["method"] == "clock:runoff"
    assert view["clock"]["timeouts"] == [2, 3]


def test_unsupported_regulation_season_is_actionable_not_a_server_error(tmp_path: Path) -> None:
    for chart in default_teams():
        write_team(tmp_path, chart)
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/api/games",
        json={"home": "2026/alpha-tech", "away": "2026/beta-state", "mode": "regulation"},
    )
    assert response.status_code == 422 and "season" in response.json()["detail"]


def test_overtime_api_transports_choices_timeouts_and_game_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bowl_bound.regulation import RegulationGame
    from tests.test_overtime import overtime_game

    game = overtime_game(1995, game_type="postseason")
    for chart in default_teams():
        write_team(tmp_path, replace(chart, season=1995))
    received: dict[str, object] = {}

    def ready_game(*args: object, **kwargs: object) -> RegulationGame:
        received.update(kwargs)
        return game

    monkeypatch.setattr(RegulationGame, "new", ready_game)
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/api/games",
        json={
            "home": "1995/alpha-tech",
            "away": "1995/beta-state",
            "mode": "regulation",
            "game_type": "postseason",
            "seed": 1,
        },
    )
    assert response.status_code == 200, response.text
    assert received["game_type"] == "postseason"
    path = "/api/games/" + response.json()["game_id"]
    assert response.json()["view"]["phase"] == "overtime_choice"
    result = client.post(path + "/decision", json={"choice": "ot:offense"})
    assert result.status_code == 200
    assert result.json()["view"]["clock"]["label"] == "Untimed"
    result = client.post(path + "/action", json={"action": "timeout:home"})
    assert result.status_code == 200
    assert result.json()["view"]["clock"]["timeouts"] == [0, 1]
    assert client.post(path + "/action", json={"action": "timeout:home"}).status_code == 422
    assert client.post(path + "/kick", json={"action": "kickoff"}).status_code == 422
