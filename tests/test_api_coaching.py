"""Only public controls precede simultaneous coached resolution."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import default_teams, write_team


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("bowl_bound.save_game.randbits", lambda _: 31)
    for team in default_teams():
        write_team(tmp_path, team)
    return TestClient(create_app(tmp_path))


@pytest.mark.parametrize("human,role,call", [("home", "offense", "1"), ("away", "defense", "A")])
def test_preview_masks_computer_controls_and_resolution_reveals_calls(
    client, human, role, call
) -> None:
    created = client.post(
        f"/api/games?human_side={human}",
        json={
            "home": "2026/alpha-tech",
            "away": "2026/beta-state",
            "seed": 7,
        },
    ).json()
    path = f"/api/games/{created['game_id']}"
    turn = created["turn"]
    assert turn["human_role"] == role and not turn["automatic"]
    assert bool(turn["actions"]["offense"]) == (role == "offense")
    assert bool(turn["actions"]["defense"]) == (role == "defense")
    assert "computer_choice" not in str(created) and "coach_seed" not in str(created)
    assert client.get(path + f"?human_side={human}").json()["turn"] == turn
    rejected = client.post(path + "/coach", json={"human_side": human, "human_call": "Z"})
    assert rejected.status_code == 422
    assert client.get(path).json()["view"]["log"] == []
    result = client.post(path + "/coach", json={"human_side": human, "human_call": call})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["report"]["called_play"] and data["report"]["defense"]
    assert len(data["view"]["log"]) == 1
    assert "computer_choice" not in data


def test_coached_human_decisions_validate_offered_controls(client) -> None:
    created = client.post(
        "/api/games?human_side=home",
        json={
            "home": "2026/alpha-tech",
            "away": "2026/beta-state",
            "seed": 7,
            "start_yards_to_goal": 5,
        },
    ).json()
    path = f"/api/games/{created['game_id']}"
    result = client.post(path + "/coach", json={"human_side": "home", "human_call": "1"}).json()
    assert result["turn"]["human_role"] == "decision"
    assert client.post(path + "/coach", json={"human_side": "home"}).status_code == 409
    denied = client.post(path + "/decision?human_side=away", json={"choice": "conversion:kick"})
    assert denied.status_code == 422
    done = client.post(path + "/decision?human_side=home", json={"choice": "conversion:kick"})
    assert done.status_code == 200, done.text
    assert done.json()["turn"]["human_role"] == "final"


@pytest.mark.parametrize(
    "body", [{}, {"human_side": "third"}, {"human_side": "home", "human_call": "1", "defense": "A"}]
)
def test_bad_coaching_contract_is_rejected(client, body) -> None:
    assert client.post("/api/games/missing/coach", json=body).status_code == 422
