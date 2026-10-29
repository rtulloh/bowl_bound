"""AI-005: a post-snap history failure cannot erase a completed engine command."""

import json

import pytest

from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import default_teams


def new(policy: str) -> SavedGame:
    return SavedGame.new(
        *default_teams(),
        home_id="2026/a",
        away_id="2026/b",
        seed=7,
        coach_seed=31,
        coach_policy=policy,
    )


@pytest.mark.parametrize("policy", ["easy-v1", "medium-v1", "hard-v1"])
@pytest.mark.parametrize("after_update", [False, True])
def test_history_failure_keeps_successful_snap_journaled_and_replayable(
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
    after_update: bool,
) -> None:
    game = new(policy)
    reference = new(policy)
    before = json.loads(dumps_game(game))
    commit = game._coach.commit_call

    def fail(side: str, play: str, defense: str) -> None:
        if after_update:
            commit(side, play, defense)
        raise RuntimeError("synthetic history failure")

    monkeypatch.setattr(game._coach, "commit_call", fail)
    with pytest.raises(RuntimeError, match="synthetic history failure"):
        game.snap("1", "A")
    reference.snap("1", "A")
    assert game.view() == reference.view()
    data = json.loads(dumps_game(game))
    assert data["rolls"] != before["rolls"]
    assert data["commands"] == [{"operation": "snap", "arguments": ["1", "A"], "error": None}]
    assert data["commands"] == json.loads(dumps_game(reference))["commands"]
    teams = default_teams()
    restored = loads_game(dumps_game(game), lambda key: teams[0 if key.endswith("/a") else 1])
    assert restored.view() == reference.view()
    assert restored.coach_step("home", "2") == reference.coach_step("home", "2")
    assert restored.view() == reference.view()
