"""Public new-game tiers and defaults must not reinterpret saved legacy policies."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame, main
from bowl_bound.sample_teams import install_samples


@pytest.mark.parametrize("mode", [None, "easy", "medium", "hard"])
def test_cli_selects_real_tiers_with_medium_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str | None
) -> None:
    install_samples(tmp_path)
    seen = []
    monkeypatch.setattr(TerminalGame, "run", lambda self: seen.append(self.game.coach_policy) or 0)
    arguments = ["--seasons", str(tmp_path)] + (["-d", mode] if mode else [])
    assert main(arguments) == 0
    assert seen == [f"{mode or 'medium'}-v1"]


@pytest.mark.parametrize("mode", [None, "easy", "medium", "hard"])
def test_api_selects_real_tiers_with_medium_default_and_reports_policy(
    tmp_path: Path, mode: str | None
) -> None:
    home, away = install_samples(tmp_path)
    client = TestClient(create_app(tmp_path))
    payload = {"home": home, "away": away, "seed": 7}
    if mode:
        payload["difficulty"] = mode
    response = client.post("/api/games?human_side=home", json=payload)
    assert response.status_code == 200
    body = response.json()
    policy = f"{mode or 'medium'}-v1"
    assert body["coach_policy"] == policy
    assert "estimates" not in body and "computer_choice" not in body["turn"]
    saved = client.get(f"/api/games/{body['game_id']}/save").json()
    assert saved["config"]["coach_policy"] == policy
    loaded = client.post("/api/games/load", json=saved).json()
    assert loaded["coach_policy"] == policy


@pytest.mark.parametrize(
    "payload", [{"difficulty": "unknown"}, {"difficulty": "hard", "coach_policy": "baseline"}]
)
def test_api_rejects_ambiguous_or_unknown_difficulty(
    tmp_path: Path, payload: dict[str, str]
) -> None:
    home, away = install_samples(tmp_path)
    client = TestClient(create_app(tmp_path))
    assert (
        client.post("/api/games", json={"home": home, "away": away, **payload}).status_code == 422
    )
