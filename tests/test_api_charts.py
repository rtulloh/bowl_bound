"""Chart inspection uses frozen matchup charts and never changes gameplay."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import default_teams, write_team


@pytest.fixture(autouse=True)
def fixed_save_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    # Downloads include a timestamp and its integrity hash; freeze time to compare all bytes.
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return datetime(2026, 11, 5, tzinfo=timezone.utc)

    monkeypatch.setattr("bowl_bound.save_game.datetime", FixedDateTime)


@pytest.mark.parametrize("human_side", [None, "home", "away"])
def test_chart_reads_preserve_save_and_revision(tmp_path: Path, human_side: str | None) -> None:
    for chart in default_teams():
        write_team(tmp_path, chart)
    client = TestClient(create_app(tmp_path))
    control = "" if human_side is None else f"?human_side={human_side}"
    game = client.post(
        "/api/games" + control,
        json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7},
    ).json()
    path = "/api/games/" + game["game_id"]
    before = client.get(path + "/save").content
    # A game's already loaded charts remain authoritative if local files disappear.
    for file in tmp_path.rglob("*.csv"):
        file.unlink()
    for side, name in [("home", "Alpha Tech"), ("away", "Beta State")]:
        response = client.get(path + "/charts?side=" + side)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["team"] == name
        assert len(data["offense"]["rows"]) == len(data["defense"]["rows"]) == 30
        assert "provenance" not in response.text
    assert client.get(path + "/save").content == before
    assert client.get(path + control).json() == game
    assert client.get(path + "/charts?side=../private-data").status_code == 422
    assert client.get("/api/games/missing/charts?side=home").status_code == 404


def test_pending_interception_is_preserved_while_reading_charts(tmp_path: Path) -> None:
    for chart in default_teams():
        write_team(tmp_path, chart)
    client = TestClient(create_app(tmp_path))
    game = client.post(
        "/api/games", json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7}
    ).json()
    path = "/api/games/" + game["game_id"]
    result = client.post(path + "/snap", json={"play": "9", "defense": "A"}).json()
    assert result["view"]["pending"] is not None
    before = client.get(path + "/save").content
    assert client.get(path + "/charts?side=away").status_code == 200
    assert client.get(path + "/save").content == before
