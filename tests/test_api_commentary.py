"""API transports engine narration; semantic fields/saves remain unchanged."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.save_game import SavedGame, dumps_game
from tests.test_commentary_lifecycle import setup_game, write_rosters


@pytest.mark.parametrize("named", [False, True])
def test_live_log_get_and_reload_serialize_same_engine_narration(
    tmp_path: Path, named: bool
) -> None:
    setup_game(tmp_path)
    if named:
        write_rosters(tmp_path)
    client = TestClient(create_app(tmp_path))
    created = client.post(
        "/api/games", json={"home": "2007/home", "away": "2007/away", "seed": 7}
    ).json()
    path = "/api/games/" + created["game_id"]
    response = client.post(path + "/snap", json={"play": "1", "defense": "A"})
    assert response.status_code == 200
    data = response.json()
    report = data["report"]
    assert report["commentary"] == data["view"]["log"][-1]["commentary"]
    assert ("H Runner" in report["commentary"]) is named
    direct, _ = setup_game(tmp_path)
    if named:
        direct.load_rosters(tmp_path)
    expected = direct.snap("1", "A")
    assert report["commentary"] == direct.commentary(expected)
    actual_save = client.get(path + "/save").json()
    direct_save = json.loads(dumps_game(direct))
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert actual_save[key] == direct_save[key]
    assert "H Runner" not in report["description"]
    before = client.get(path + "/save").json()
    for _ in range(4):
        assert client.get(path).json()["view"] == data["view"]
    after = client.get(path + "/save").json()
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert after[key] == before[key]
    assert "H Runner" not in json.dumps(before)
    restored = client.post("/api/games/load", json=before)
    assert restored.status_code == 200 and restored.json()["view"] == data["view"]
    assert "rosters" not in json.dumps(data) and "coach_seed" not in json.dumps(data)


def test_api_uses_engine_text_for_coached_reports_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup_game(tmp_path)
    monkeypatch.setattr(
        SavedGame, "commentary", lambda self, report: "ENGINE TEXT " + str(report.number)
    )
    client = TestClient(create_app(tmp_path))
    created = client.post(
        "/api/games?human_side=home", json={"home": "2007/home", "away": "2007/away", "seed": 7}
    ).json()
    path = "/api/games/" + created["game_id"]
    data = client.post(path + "/coach", json={"human_side": "home", "human_call": "1"}).json()
    assert data["report"]["commentary"] == "ENGINE TEXT 1"
    assert data["view"]["log"][-1]["commentary"] == "ENGINE TEXT 1"
    assert client.get(path + "?human_side=home").json()["view"] == data["view"]
