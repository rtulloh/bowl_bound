"""Solitaire terminal displays engine narration, without affecting saved facts."""

import json
from io import StringIO
from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame, write_save
from bowl_bound.save_game import SavedGame, dumps_game
from tests.test_commentary_lifecycle import setup_game, write_rosters


@pytest.mark.parametrize("human", ["home", "away"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("named", [False, True])
def test_solitaire_live_log_and_reload_use_engine_narration(
    tmp_path: Path,
    human: str,
    reverse: bool,
    named: bool,
) -> None:
    _, catalog = setup_game(tmp_path)
    if named:
        write_rosters(tmp_path)
    home_id, away_id = ("2007/away", "2007/home") if reverse else ("2007/home", "2007/away")
    game = SavedGame.new(
        catalog.load(home_id),
        catalog.load(away_id),
        home_id=home_id,
        away_id=away_id,
        seed=7,
        coach_seed=31,
        coach_policy="easy-v1",
    )
    output = StringIO()
    app = TerminalGame(game, catalog.load, human_side=human, roster_root=tmp_path, output=output)
    assert app.command("1" if human == "home" else "A")
    value = app.last_report
    assert value is not None
    expected = game.commentary(value)
    assert expected in output.getvalue()
    if named:
        assert ("A " if reverse else "H ") in expected
    else:
        assert expected == value.commentary
    before = json.loads(dumps_game(game))
    for command in ("help", "stats"):
        app.command(command)
    app.output = StringIO()
    app.command("log")
    assert f"1. {expected}" in app.output.getvalue()
    app.command("Z")
    assert not app.helper_enabled
    app.command("Z")
    assert app.helper_enabled and "Not applied" not in app.output.getvalue()
    after = json.loads(dumps_game(game))
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert after[key] == before[key]
    path = tmp_path / "resume.json"
    write_save(path, game)
    assert app.command("load " + str(path))
    app.output = StringIO()
    app.command("log")
    assert expected in app.output.getvalue()


def test_cli_live_and_log_transport_engine_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, catalog = setup_game(tmp_path)
    monkeypatch.setattr(SavedGame, "commentary", lambda self, report: "ENGINE-ONLY NARRATION")
    app = TerminalGame(game, catalog.load, output=StringIO())
    app.command("1")
    assert "► ENGINE-ONLY NARRATION" in app.output.getvalue()
    app.output = StringIO()
    app.command("log")
    assert "1. ENGINE-ONLY NARRATION" in app.output.getvalue()
