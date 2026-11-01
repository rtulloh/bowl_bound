"""AI-019: Hard's postgame call history includes committed calls only."""

import io
from dataclasses import replace

from bowl_bound.cli import TerminalGame
from bowl_bound.models import Play, TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import SessionPhase
from tests.synthetic_teams import default_teams


def _game() -> tuple[SavedGame, dict[str, TeamChart]]:
    home, away = (replace(chart, season=2002) for chart in default_teams())
    game = SavedGame.new(
        home,
        away,
        home_id="2002/alpha-tech",
        away_id="2002/beta-state",
        seed=7,
        coach_seed=31,
        coach_policy="hard-v8",
    )
    return game, {"2002/alpha-tech": home, "2002/beta-state": away}


def _history_by_role(game: SavedGame) -> dict[tuple[str, str], dict[str, int]]:
    return {(side, role): dict(calls) for side, role, calls in game._coach.call_history()}


def test_hard_call_history_ignores_previews_and_is_rendered_only_after_final() -> None:
    game, charts = _game()
    _, turn = game.coach_view("home")
    assert not turn.automatic
    assert game._coach.call_history() == ()
    assert game.postgame_call_summary() is None

    game.coach_step("home", str(Play.ONE))
    history = _history_by_role(game)
    assert history["home", "offense"] == {"1": 1}
    assert sum(history["away", "defense"].values()) == 1
    assert game.postgame_call_summary() is None

    save = dumps_game(game)
    assert "call_history" not in save and "postgame_call_summary" not in save
    restored = loads_game(save, charts.__getitem__)
    assert _history_by_role(restored) == history

    game._engine._phase = SessionPhase.COMPLETE
    summary = game.postgame_call_summary()
    assert summary is not None
    terminal = TerminalGame(
        game,
        lambda key: charts[key],
        output=io.StringIO(),
    )
    terminal.display()
    terminal.display()
    output = terminal.output.getvalue()
    assert "Hard coach learned these committed calls" in output
    assert "Line Plunge: 1" in output
    assert output.count("Hard coach learned these committed calls") == 1
