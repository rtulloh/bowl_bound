"""Canonical optional roster contexts are private, stable and transactional."""

import json
from io import StringIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TeamCatalog, TerminalGame, write_save
from bowl_bound.roster import RosterFormatError
from bowl_bound.save_game import SavedGame, dumps_game
from tests.synthetic_teams import team_chart, write_team


def setup_game(root: Path, *, mode: str = "drive") -> tuple[SavedGame, TeamCatalog]:
    home, away = team_chart("Home", season=2007), team_chart("Away", season=2007, defense=0)
    home_id, away_id = write_team(root, home), write_team(root, away)
    return SavedGame.new(
        home, away, home_id=home_id, away_id=away_id, seed=7, coach_seed=31, mode=mode
    ), TeamCatalog(root)


def write_rosters(root: Path, name: str = "H Runner") -> None:
    (root / "2007/home/roster.json").write_text(json.dumps({"rb": [name], "qb": ["H Passer"]}))
    (root / "2007/away/roster.json").write_text(
        json.dumps({"rb": ["A Runner"], "qb": ["A Passer"]})
    )


def test_loaded_context_is_stable_private_and_does_not_change_save(tmp_path: Path) -> None:
    game, _ = setup_game(tmp_path)
    write_rosters(tmp_path)
    value = game.snap("1", "A")
    before = json.loads(dumps_game(game))
    game.load_rosters(tmp_path)
    assert "H Runner" in game.commentary(value)
    write_rosters(tmp_path, "Changed Runner")
    assert "H Runner" in game.commentary(value)
    after = json.loads(dumps_game(game))
    for key in ("saved_at", "integrity"):
        before.pop(key)
        after.pop(key)
    assert after == before and "H Runner" not in dumps_game(game)
    game.load_rosters(tmp_path)
    assert "Changed Runner" in game.commentary(value)


def test_missing_rosters_and_empty_positions_are_generic(tmp_path: Path) -> None:
    game, _ = setup_game(tmp_path)
    value = game.snap("1", "A")
    game.load_rosters(tmp_path)
    expected = "The running back picks up 4 yards on the ground."
    assert game.commentary(value) == expected
    (tmp_path / "2007/home/roster.json").write_text("{}")
    game.load_rosters(tmp_path)
    assert game.commentary(value) == expected


@pytest.mark.parametrize("fault", ["malformed", "symlink_root", "symlink_file"])
def test_bad_roster_does_not_replace_existing_context_or_leak_values(
    tmp_path: Path, fault: str
) -> None:
    game, _ = setup_game(tmp_path)
    write_rosters(tmp_path)
    game.load_rosters(tmp_path)
    value = game.snap("1", "A")
    write_rosters(tmp_path, "New Runner")
    root = tmp_path
    if fault == "malformed":
        (tmp_path / "2007/away/roster.json").write_text('{"secret-name":[] }')
    elif fault == "symlink_root":
        root = tmp_path / "alias"
        root.symlink_to(tmp_path, target_is_directory=True)
    else:
        path = tmp_path / "2007/away/roster.json"
        path.rename(path.with_suffix(".backup"))
        path.symlink_to(path.with_suffix(".backup"))
    with pytest.raises(RosterFormatError) as raised:
        game.load_rosters(root)
    assert "secret-name" not in str(raised.value)
    assert "H Runner" in game.commentary(value)


def test_terminal_create_and_load_attach_current_rosters_atomically(tmp_path: Path) -> None:
    game, catalog = setup_game(tmp_path)
    write_rosters(tmp_path)
    value = game.snap("1", "A")
    path = tmp_path / "game.json"
    write_save(path, game)
    terminal = TerminalGame(game, catalog.load, roster_root=tmp_path, output=StringIO())
    assert "H Runner" in terminal.game.commentary(value)
    write_rosters(tmp_path, "Reload Runner")
    assert terminal.command("load " + str(path))
    assert "Reload Runner" in terminal.game.commentary(terminal.game.view().log[0])
    current = terminal.game
    (tmp_path / "2007/home/roster.json").write_text('{"private-name":[] }')
    assert not terminal.command("load " + str(path))
    assert terminal.game is current
    assert "private-name" not in terminal.output.getvalue()


@pytest.mark.parametrize("mode", ["drive", "regulation"])
def test_api_create_and_load_validate_rosters_before_registration(
    tmp_path: Path,
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.MAX_GAMES", 1)
    _, _ = setup_game(tmp_path)
    write_rosters(tmp_path)
    client = TestClient(create_app(tmp_path))
    body = {"home": "2007/home", "away": "2007/away", "seed": 7, "mode": mode}
    created = client.post("/api/games", json=body)
    assert created.status_code == 200
    game_id = created.json()["game_id"]
    saved = client.get("/api/games/" + game_id + "/save").json()
    (tmp_path / "2007/home/roster.json").write_text('{"private-name":[] }')
    rejected = client.post("/api/games", json=body)
    assert rejected.status_code == 422 and "private-name" not in rejected.text
    rejected_load = client.post("/api/games/load", json=saved)
    assert rejected_load.status_code == 422 and "private-name" not in rejected_load.text
    assert client.get("/api/games/" + game_id).status_code == 200
