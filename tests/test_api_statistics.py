"""The API serializes committed engine credits and team summary numbers."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import default_teams, write_team


def test_statistics_transport_and_pending_choice_do_not_double_count(tmp_path: Path) -> None:
    for chart in default_teams():
        write_team(tmp_path, chart)
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/api/games",
        json={
            "home": "2026/alpha-tech",
            "away": "2026/beta-state",
            "seed": 1,
        },
    )
    data = response.json()
    path = "/api/games/" + data["game_id"]
    assert data["view"]["statistics"]["home"]["total_plays"] == 0
    result = client.post(path + "/snap", json={"play": "1", "defense": "A"}).json()
    assert result["report"]["statistics"] == {
        "kind": "rush",
        "team": "home",
        "yards": 6,
        "touchdown": False,
    }
    expected = result["view"]["statistics"]
    assert expected["home"]["rushing_yards"] == expected["home"]["total_yards"] == 6
    assert expected["home"]["total_plays"] == 1
    assert expected["rows"]
    pending = client.post(path + "/snap", json={"play": "9", "defense": "A"}).json()
    assert pending["view"]["statistics"] == expected
    finished = client.post(path + "/decision", json={"choice": "interception:decline"}).json()
    assert finished["view"]["statistics"]["home"]["passing_attempts"] == 1
    assert finished["view"]["statistics"]["home"]["total_plays"] == 2
    assert client.get(path).json()["view"]["statistics"] == finished["view"]["statistics"]
