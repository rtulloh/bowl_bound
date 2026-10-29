"""Downloads survive a fresh API process and never replace a live game on failure."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import default_teams, write_team


def client_at(path: Path) -> TestClient:
    for chart in default_teams():
        write_team(path, chart)
    return TestClient(create_app(path))


def create(client: TestClient):
    return client.post(
        "/api/games", json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 1}
    ).json()


def test_pending_game_download_survives_server_restart_and_continues_identically(
    tmp_path: Path,
) -> None:
    client = client_at(tmp_path)
    game = create(client)
    path = "/api/games/" + game["game_id"]
    pending = client.post(path + "/snap", json={"play": "9", "defense": "A"}).json()
    saved = client.get(path + "/save")
    assert saved.status_code == 200
    assert saved.headers["cache-control"] == "no-store"
    assert saved.headers["content-disposition"] == 'attachment; filename="bowl-bound-save.json"'
    assert "offense" not in saved.text and "provenance" not in saved.text
    restarted = TestClient(create_app(tmp_path))
    restored = restarted.post(
        "/api/games/load", content=saved.content, headers={"Content-Type": "application/json"}
    )
    assert restored.status_code == 200
    loaded = restored.json()
    assert loaded["game_id"] != game["game_id"]
    assert loaded["seed"] == 1 and loaded["view"] == pending["view"]
    result = client.post(path + "/decision", json={"choice": "interception:return"})
    continued = restarted.post(
        "/api/games/" + loaded["game_id"] + "/decision", json={"choice": "interception:return"}
    )
    assert continued.status_code == result.status_code == 200
    assert continued.json() == result.json()


def test_invalid_upload_preserves_existing_game_and_does_not_echo_private_input(
    tmp_path: Path,
) -> None:
    client = client_at(tmp_path)
    game = create(client)
    path = "/api/games/" + game["game_id"]
    before = client.get(path).json()
    for text in ('{"private":"SENSITIVE CHART"}', "[]", "{", '{"schema_version":999}'):
        result = client.post("/api/games/load", content=text)
        assert result.status_code == 422
        assert "SENSITIVE" not in result.text
        assert client.get(path).json() == before
    oversized = client.post("/api/games/load", content="x" * (2 * 1024 * 1024 + 1))
    assert oversized.status_code == 413
    assert client.get(path).json() == before


def test_missing_local_team_is_safe_and_unknown_save_is_404(tmp_path: Path) -> None:
    client = client_at(tmp_path)
    game = create(client)
    saved = client.get("/api/games/" + game["game_id"] + "/save")
    assert saved.status_code == 200
    empty = tmp_path / "empty"
    restarted = TestClient(create_app(empty))
    result = restarted.post("/api/games/load", content=saved.content)
    assert result.status_code == 422
    assert str(tmp_path) not in result.text
    assert client.get("/api/games/unknown/save").status_code == 404
    assert json.loads(saved.content)["schema_version"] == 1
