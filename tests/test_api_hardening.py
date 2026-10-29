"""Rejected requests stay bounded and response snapshots share one game lock."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PendingDecisionError
from tests.synthetic_teams import default_teams, write_team


def test_rejected_noop_commands_do_not_fill_save_journal() -> None:
    home, away = default_teams()
    game = SavedGame.new(home, away, home_id="2026/alpha-tech", away_id="2026/beta-state", seed=7)
    for _ in range(30):
        with pytest.raises(PendingDecisionError):
            game.decide("not-a-choice")
    assert json.loads(dumps_game(game))["commands"] == []
    restored = loads_game(dumps_game(game), lambda key: home if "alpha" in key else away)
    assert restored.view() == game.view()


def test_parallel_requests_return_matching_report_and_view(tmp_path: Path) -> None:
    ids = [write_team(tmp_path, chart) for chart in default_teams()]
    client = TestClient(create_app(tmp_path))
    created = client.post("/api/games", json={"home": ids[0], "away": ids[1]}).json()
    path = "/api/games/" + created["game_id"]

    def snap(_: int) -> dict:
        response = client.post(path + "/snap", json={"play": "1", "defense": "A"})
        assert response.status_code in (200, 409)
        return response.json()

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(snap, range(12)))
    for result in responses:
        if "report" in result:
            assert result["report"]["state_after"] == result["view"]["state"]


def test_action_snapshot_holds_lock_across_view(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ids = [write_team(tmp_path, chart) for chart in default_teams()]
    client = TestClient(create_app(tmp_path))
    created = client.post("/api/games", json={"home": ids[0], "away": ids[1]}).json()
    original = SavedGame.view

    def checked_view(self: SavedGame):
        assert self._lock._is_owned(), "report/view must share the command lock"
        return original(self)

    monkeypatch.setattr(SavedGame, "view", checked_view)
    response = client.post(
        "/api/games/" + created["game_id"] + "/snap", json={"play": "1", "defense": "A"}
    )
    assert response.status_code == 200


def test_recently_used_game_survives_registry_eviction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import backend.app as api

    monkeypatch.setattr(api, "MAX_GAMES", 2)
    ids = [write_team(tmp_path, chart) for chart in default_teams()]
    client = TestClient(create_app(tmp_path))

    def create(seed: int) -> str:
        result = client.post("/api/games", json={"home": ids[0], "away": ids[1], "seed": seed})
        assert result.status_code == 200
        return "/api/games/" + result.json()["game_id"]

    first, second = create(1), create(2)
    assert client.get(first).json()["seed"] == 1
    create(3)
    assert client.get(first).status_code == 200
    assert client.get(second).status_code == 404


def test_team_identifier_rejects_trailing_newline(tmp_path: Path) -> None:
    ids = [write_team(tmp_path, chart) for chart in default_teams()]
    client = TestClient(create_app(tmp_path))
    result = client.post("/api/games", json={"home": ids[0] + "\n", "away": ids[1]})
    assert result.status_code == 422


@pytest.mark.parametrize("component", ["root", "season", "team"])
def test_direct_team_load_refuses_symlinked_directories(tmp_path: Path, component: str) -> None:
    original = tmp_path / "original"
    ids = [write_team(original, chart) for chart in default_teams()]
    root = tmp_path / "linked"
    season, slug = ids[0].split("/")
    if component == "root":
        root.symlink_to(original, target_is_directory=True)
    elif component == "season":
        root.mkdir()
        (root / season).symlink_to(original / season, target_is_directory=True)
    else:
        (root / season).mkdir(parents=True)
        (root / season / slug).symlink_to(original / season / slug, target_is_directory=True)
    client = TestClient(create_app(root))
    result = client.post("/api/games", json={"home": ids[0], "away": ids[0]})
    assert result.status_code == 422


def test_eviction_after_lookup_keeps_captured_game_and_seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from threading import Event, Thread

    import backend.app as api

    monkeypatch.setattr(api, "MAX_GAMES", 1)
    ids = [write_team(tmp_path, chart) for chart in default_teams()]
    client = TestClient(create_app(tmp_path))
    path = (
        "/api/games/"
        + client.post("/api/games", json={"home": ids[0], "away": ids[1], "seed": 12}).json()[
            "game_id"
        ]
    )
    entered, release = Event(), Event()
    original = SavedGame.view

    def paused_view(self: SavedGame):
        if self.seed == 12:
            entered.set()
            assert release.wait(10)
        return original(self)

    monkeypatch.setattr(SavedGame, "view", paused_view)
    results = []
    worker = Thread(target=lambda: results.append(client.get(path)))
    worker.start()
    try:
        assert entered.wait(10)
        assert (
            client.post("/api/games", json={"home": ids[0], "away": ids[1], "seed": 13}).status_code
            == 200
        )
    finally:
        release.set()
        worker.join(10)
    assert not worker.is_alive()
    assert results[0].status_code == 200 and results[0].json()["seed"] == 12
    assert client.get(path).status_code == 404


def test_replay_preserves_previously_journaled_noop_rejections() -> None:
    from tests.test_save_game import seal

    home, away = default_teams()
    game = SavedGame.new(home, away, home_id="2026/alpha-tech", away_id="2026/beta-state", seed=7)
    data = json.loads(dumps_game(game))
    data["commands"].append(
        {"operation": "decide", "arguments": ["not-a-choice"], "error": "PendingDecisionError"}
    )
    restored = loads_game(seal(data), lambda key: home if "alpha" in key else away)
    assert restored.view() == game.view()
    assert json.loads(dumps_game(restored))["commands"] == data["commands"]


@pytest.mark.parametrize("endpoint", ["/api/games", "/api/games/unknown/snap"])
def test_regular_api_body_size_is_bounded_before_validation(tmp_path: Path, endpoint: str) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.post(endpoint, content=b" " * (16 * 1024 + 1))
    assert response.status_code == 413


def test_chunked_request_body_is_bounded_without_content_length(tmp_path: Path) -> None:
    import asyncio

    app = create_app(tmp_path)
    messages = iter(
        [
            {"type": "http.request", "body": b" " * 9000, "more_body": True},
            {"type": "http.request", "body": b" " * 9000, "more_body": True},
        ]
    )
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/games",
        "raw_path": b"/api/games",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("test", 1),
    }
    asyncio.run(app(scope, receive, send))
    assert sent[0]["status"] == 413
