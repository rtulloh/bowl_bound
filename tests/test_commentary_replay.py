"""Roster presentation preserves pre-commentary semantics and future streams."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.save_game import ENGINE_PROFILE, _view_digest, dumps_game, loads_game
from tests.test_commentary_lifecycle import setup_game, write_rosters

# Independently measured with unchanged 2004a21 in a detached temporary worktree.
LEGACY_DIGEST = "46f4b00853bff74f597720ecc45464e12963eddfe851b7a4f0b6b612247f23c1"


def test_pre_commentary_semantic_digest_and_save_shape_remain_compatible(tmp_path: Path) -> None:
    game, catalog = setup_game(tmp_path)
    value = game.snap("1", "A")
    text = dumps_game(game)
    saved = json.loads(text)
    assert saved["engine_profile"] == ENGINE_PROFILE == "bowl-bound-m21-v1"
    assert saved["state_digest"] == LEGACY_DIGEST
    write_rosters(tmp_path)
    restored = loads_game(text, catalog.load)
    restored.load_rosters(tmp_path)
    assert "H Runner" in restored.commentary(restored.view().log[0])
    assert restored.view() == game.view()
    view = game.view()
    altered = replace(view, log=(replace(value, description="Altered semantic result."),))
    assert _view_digest(altered) != _view_digest(view)


@pytest.mark.parametrize("human", ["home", "away"])
@pytest.mark.parametrize("rosters", ["present", "missing", "changed"])
def test_hard_history_and_future_commands_are_identical_with_narration(
    tmp_path: Path,
    human: str,
    rosters: str,
) -> None:
    from bowl_bound.save_game import SavedGame

    _, catalog = setup_game(tmp_path)
    game = SavedGame.new(
        catalog.load("2007/home"),
        catalog.load("2007/away"),
        home_id="2007/home",
        away_id="2007/away",
        seed=7,
        coach_seed=31,
        coach_policy="hard-v1",
    )
    game.coach_step(human, "1" if human == "home" else "A")
    write_rosters(tmp_path)
    game.load_rosters(tmp_path)
    text = dumps_game(game)
    if rosters == "missing":
        (tmp_path / "2007/home/roster.json").unlink()
        (tmp_path / "2007/away/roster.json").unlink()
    elif rosters == "changed":
        write_rosters(tmp_path, "New Illustrative Runner")
    resumed = loads_game(text, catalog.load)
    resumed.load_rosters(tmp_path)
    for _ in range(12):
        view, turn = game.coach_view(human)
        assert resumed.coach_view(human) == (view, turn)
        for report in view.log:
            game.commentary(report)
            resumed.commentary(report)
        if view.finished:
            break
        if turn.human_role == "decision":
            choice = next(c.id for c in turn.pending.choices if c.enabled)
            assert game.decide(choice) == resumed.decide(choice)
        else:
            call = None if turn.automatic else ("1" if turn.human_role == "offense" else "A")
            assert game.coach_step(human, call) == resumed.coach_step(human, call)
        left, right = json.loads(dumps_game(game)), json.loads(dumps_game(resumed))
        for key in ("commands", "rolls", "random_state", "state_digest"):
            assert left[key] == right[key]
    assert len(game.view().log) > 1


def test_pending_regulation_replay_is_independent_of_rosters(tmp_path: Path) -> None:
    game, catalog = setup_game(tmp_path, mode="regulation")
    assert game.view().pending is not None
    write_rosters(tmp_path)
    game.load_rosters(tmp_path)
    restored = loads_game(dumps_game(game), catalog.load)
    restored.load_rosters(tmp_path)
    choice = next(c.id for c in game.view().pending.choices if c.enabled)
    assert game.decide(choice) == restored.decide(choice)
    assert game.view() == restored.view()
