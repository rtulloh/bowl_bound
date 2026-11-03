"""UI-055: timeout budgets stay on the scoreboard, outside action labels."""

import pytest

from tests.test_regulation import kickoff, new_game


@pytest.mark.parametrize("side,name", [("home", "Home"), ("away", "Away")])
@pytest.mark.parametrize("prefix", ["timeout", "timeout_after"])
def test_timeout_action_labels_omit_duplicate_budget(side: str, name: str, prefix: str) -> None:
    game = new_game(gain=2)
    kickoff(game)
    before = game.view()
    key = f"{prefix}:{side}"
    assert next(action.label for action in before.game_actions if action.key == key) == (
        f"Use {name} timeout on next play"
    )
    game.action(key)
    selected = game.view()
    assert next(action.label for action in selected.game_actions if action.key == key) == (
        f"Cancel {name} timeout"
    )
    assert selected.clock == before.clock
    assert (selected.home_timeouts, selected.away_timeouts) == (3, 3)
    game.action(key)
    assert game.view() == before
