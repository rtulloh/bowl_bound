"""Thin API conversion flow and scoring reconciliation with synthetic charts."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import team_chart, write_team


@pytest.mark.parametrize("choice", ["conversion:kick", "conversion:two"])
def test_conversion_end_to_end_and_duplicate_refusal(tmp_path: Path, choice: str) -> None:
    home = team_chart("Home", offense=3)
    home = replace(home, pat_outcomes=tuple(replace(row, good=True) for row in home.pat_outcomes))
    for chart in (home, team_chart("Away", defense=0)):
        write_team(tmp_path, chart)
    client = TestClient(create_app(tmp_path))
    game = client.post(
        "/api/games",
        json={"home": "2026/home", "away": "2026/away", "seed": 1, "start_yards_to_goal": 2},
    ).json()
    path = f"/api/games/{game['game_id']}"
    touchdown = client.post(path + "/snap", json={"play": "1", "defense": "A"}).json()
    assert touchdown["view"]["score"] == {"home": 6, "away": 0}
    assert touchdown["view"]["pending"]["chooser"] == "Home"
    before = client.get(path).json()["view"]
    assert client.post(path + "/decision", json={"choice": "invalid"}).status_code == 422
    assert client.post(path + "/snap", json={"play": "1", "defense": "A"}).status_code == 409
    assert client.get(path).json()["view"] == before
    response = client.post(path + "/decision", json={"choice": choice})
    assert response.status_code == 200
    if choice == "conversion:two":
        assert response.json()["view"]["state"]["yards_to_goal"] == 2
        assert response.json()["view"]["actions"]["special"] == []
        response = client.post(path + "/snap", json={"play": "1", "defense": "A"})
    view = response.json()["view"]
    expected = 7 if choice == "conversion:kick" else 8
    assert view["score"] == {"home": expected, "away": 0}
    assert view["phase"] == "complete" and view["finished"] and view["pending"] is None
    assert sum(e["points"] for e in view["scoring"]) == expected
    assert [e["play_number"] for e in view["scoring"]] == [1, 2]
    assert len(view["log"]) == 2
    assert client.post(path + "/decision", json={"choice": choice}).status_code == 409
    assert client.get(path).json()["view"] == view
