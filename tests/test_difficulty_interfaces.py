"""Public new-game tiers and defaults use the current player-facing coach."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame, main
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.sample_teams import install_samples
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import default_teams


@pytest.mark.parametrize("mode", [None, "easy", "medium", "hard"])
def test_cli_selects_real_tiers_with_medium_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str | None
) -> None:
    install_samples(tmp_path)
    seen = []
    monkeypatch.setattr(TerminalGame, "run", lambda self: seen.append(self.game.difficulty) or 0)
    arguments = ["--seasons", str(tmp_path)] + (["-d", mode] if mode else [])
    assert main(arguments) == 0
    assert seen == [mode or "medium"]


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
    difficulty = mode or "medium"
    assert body["difficulty"] == difficulty
    assert "estimates" not in body and "computer_choice" not in body["turn"]
    saved = client.get(f"/api/games/{body['game_id']}/save").json()
    assert saved["config"]["difficulty"] == difficulty
    loaded = client.post("/api/games/load", json=saved).json()
    assert loaded["difficulty"] == difficulty


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


def test_legacy_difficulty_save_uses_current_coach_on_load() -> None:
    """AI-026: normal saves retain the tier, not an obsolete AI implementation."""
    home, away = default_teams()
    legacy = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=7,
        coach_seed=31,
        coach_policy="medium-v9",
    )
    restored = loads_game(
        dumps_game(legacy), lambda key: home if key.endswith("alpha-tech") else away
    )

    assert restored.difficulty == "medium"
    assert restored.coach_policy == f"medium-v{CURRENT_DIFFICULTY_VERSION}"
    assert restored._coach.version == CURRENT_DIFFICULTY_VERSION


def test_new_difficulty_save_persists_the_tier_without_a_policy_revision() -> None:
    home, away = default_teams()
    game = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=7,
        difficulty="medium",
    )

    config = json.loads(dumps_game(game))["config"]
    assert config["difficulty"] == "medium"
    assert "coach_policy" not in config
