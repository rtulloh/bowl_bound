"""Easy terminal advice is optional, public-only, and never affects saved game state."""

import io
import json
from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame
from bowl_bound.sample_teams import sample_teams
from bowl_bound.save_game import SavedGame, dumps_game


def saved_facts(game: SavedGame) -> dict[str, object]:
    data = json.loads(dumps_game(game))
    # Wall-clock export metadata is deliberately regenerated on every save.
    data.pop("saved_at")
    data.pop("integrity")
    return data


def terminal(mode: str = "easy", human: str = "home") -> TerminalGame:
    teams = sample_teams()
    game = SavedGame.new(
        *teams,
        seed=7,
        coach_seed=31,
        coach_policy=f"{mode}-v1",
        home_id="2007/home",
        away_id="2007/away",
    )
    return TerminalGame(
        game,
        lambda key: teams[0] if key.endswith("home") else teams[1],
        human_side=human,
        output=io.StringIO(),
        compact=True,
    )


def test_easy_helper_defaults_on_and_toggle_preserves_every_saved_fact() -> None:
    app = terminal()
    before = saved_facts(app.game)
    app.display()
    text = app.output.getvalue()
    assert "Easy helper" in text and "[Z]" in text
    assert "Target: 5 yards" in text
    assert "coverage" in text and "positive" in text and "average" in text
    assert "not full-engine conversion odds" in text
    assert "Situation:" in text and "Clock:" in text
    app.output = io.StringIO()
    assert not app.command("Z")
    app.display()
    assert "Easy helper: off" in app.output.getvalue()
    assert "Target: 5 yards" not in app.output.getvalue()
    assert not app.command("z")
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("mode", ["medium", "hard"])
def test_other_modes_have_no_helper_or_z_control(mode: str) -> None:
    app = terminal(mode)
    before = saved_facts(app.game)
    app.display()
    assert "Easy helper" not in app.output.getvalue() and "[Z]" not in app.output.getvalue()
    assert not app.command("Z")
    assert "only available on Easy" in app.output.getvalue()
    assert saved_facts(app.game) == before


def test_easy_defensive_advice_is_situational_not_cpu_learning() -> None:
    app = terminal(human="away")
    app.display()
    text = app.output.getvalue()
    assert "Easy helper" in text and "Situational defense" in text
    assert "not learned CPU tendencies" in text
    assert "Situation: Mix formations" in text
    assert "Build manageable later downs" not in text
    assert "Target:" not in text and ", coverage " not in text and "average" not in text


def test_easy_helper_resets_on_load_without_persisting_preference(tmp_path: Path) -> None:
    app = terminal()
    path = tmp_path / "save.json"
    path.write_text(dumps_game(app.game))
    app.command("Z")
    app.command(f"load {path}")
    app.output = io.StringIO()
    app.display()
    assert "Target: 5 yards" in app.output.getvalue()


def test_expanded_easy_help_identifies_z_without_changing_play() -> None:
    app = terminal()
    before = saved_facts(app.game)
    app.command("?")
    assert "[Z]" in app.output.getvalue()
    assert saved_facts(app.game) == before
