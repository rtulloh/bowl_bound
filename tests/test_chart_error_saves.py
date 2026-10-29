"""AI-006: named chart rejections remain replayable, not arbitrary exceptions."""

import json
from dataclasses import replace

import pytest

from bowl_bound.models import Play, Priority
from bowl_bound.resolution import ChartResolutionError
from bowl_bound.save_game import SavedGame, SaveFormatError, dumps_game, loads_game
from tests.synthetic_teams import team_chart, yards
from tests.test_save_game import seal


def test_named_chart_rejection_replays_and_preserves_next_dice() -> None:
    home = team_chart("Home", plays={Play.ONE: replace(yards(4), priority=Priority.BRACKETED)})
    away = team_chart("Away", defense=0)
    game = SavedGame.new(home, away, home_id="2026/home", away_id="2026/away", seed=7)
    with pytest.raises(ChartResolutionError):
        game.snap("1", "A")
    text = dumps_game(game)
    assert json.loads(text)["commands"] == [
        {"operation": "snap", "arguments": ["1", "A"], "error": "ChartResolutionError"}
    ]
    restored = loads_game(text, lambda key: home if key.endswith("home") else away)
    assert restored.view() == game.view()
    assert restored.snap("2", "A") == game.snap("2", "A")
    assert restored.view() == game.view()


def test_unrecognized_error_name_is_rejected_before_team_lookup() -> None:
    game = SavedGame.new(
        team_chart("Home"), team_chart("Away"), seed=7, home_id="2026/home", away_id="2026/away"
    )
    data = json.loads(dumps_game(game))
    data["commands"] = [
        {"operation": "snap", "arguments": ["1", "A"], "error": "SyntheticProgrammingError"}
    ]
    with pytest.raises(SaveFormatError):
        loads_game(seal(data), lambda _: pytest.fail("invalid save must not load teams"))
