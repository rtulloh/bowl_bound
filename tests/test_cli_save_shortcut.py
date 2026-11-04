"""One-key private saves are explicit, create-only and gameplay-neutral."""

import io
import shlex
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.cli import TeamCatalog, TerminalGame, main
from bowl_bound.save_game import SavedGame, loads_game
from tests.synthetic_teams import default_teams, write_team
from tests.test_cli import new_game, saved_facts, terminal


@pytest.mark.parametrize("human", ["home", "away"])
def test_w_creates_a_private_loadable_save_and_prints_resume_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    human: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    app = terminal(new_game(), human, compact=True)
    before = saved_facts(app.game)
    app.automatic_paused = True
    assert not app.command("w")
    files = tuple((tmp_path / "private-data" / "saves").glob("*.json"))
    assert len(files) == 1
    path = files[0]
    assert path.stat().st_mode & 0o777 == 0o600
    assert saved_facts(loads_game(path.read_text(), app.load_team)) == before
    assert saved_facts(app.game) == before and app.automatic_paused
    output = app.output.getvalue()
    assert str(path.relative_to(tmp_path)) in output
    resume = next(
        line.removeprefix("Resume: ") for line in output.splitlines() if line.startswith("Resume: ")
    )
    words = shlex.split(resume)
    assert words[:3] == [sys.executable, "-m", "bowl_bound"]
    assert "--load" in words and "--compact" in words
    assert words[words.index("--human") + 1] == human
    assert Path(words[words.index("--load") + 1]).resolve() == path.resolve()


def test_repeated_W_never_overwrites_a_previous_save(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    app = terminal(new_game(), "home", compact=True)
    assert not app.command("W")
    directory = tmp_path / "private-data" / "saves"
    original = next(directory.glob("*.json"))
    content = original.read_bytes()
    assert app.command("1")
    assert not app.command("w")
    assert len(tuple(directory.glob("*.json"))) == 2
    assert original.read_bytes() == content


@pytest.mark.parametrize("command", ["W", 'save "save slots/resume game.json"'])
def test_resume_hint_retains_custom_charts_and_loads_after_changing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    monkeypatch.chdir(tmp_path)
    root = Path("generated charts")
    for chart in default_teams():
        write_team(root, replace(chart, season=2002))
    catalog = TeamCatalog(root)
    game = SavedGame.new(
        catalog.load("2002/alpha-tech"),
        catalog.load("2002/beta-state"),
        home_id="2002/alpha-tech",
        away_id="2002/beta-state",
        seed=7,
        difficulty="hard",
    )
    app = TerminalGame(
        game,
        catalog.load,
        human_side="away",
        output=io.StringIO(),
        compact=True,
        trace=True,
        roster_root=root,
    )
    before = saved_facts(game)
    Path("save slots").mkdir()
    assert not app.command(command)
    resume = next(
        line.removeprefix("Resume: ")
        for line in app.output.getvalue().splitlines()
        if line.startswith("Resume: ")
    )
    words = shlex.split(resume)
    assert Path(words[words.index("--seasons") + 1]) == root.resolve()
    save = Path(words[words.index("--load") + 1])
    assert save.is_absolute() and save.is_file()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    def inspect_resumed(resumed: TerminalGame) -> int:
        assert saved_facts(resumed.game) == before
        assert resumed.game.difficulty == "hard"
        assert resumed.human_side == "away" and resumed.compact and resumed.trace
        return 0

    monkeypatch.setattr(TerminalGame, "run", inspect_resumed)
    assert main(words[3:]) == 0


@pytest.mark.parametrize("folder", ["private-data", "private-data/saves"])
def test_w_rejects_symlinked_default_save_folders_without_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    folder: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / folder
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    app = terminal(new_game(), "home")
    before = saved_facts(app.game)
    assert not app.command("w")
    assert "Not applied:" in app.output.getvalue()
    assert not tuple(outside.iterdir())
    assert saved_facts(app.game) == before


def test_w_save_failure_does_not_claim_success_or_restart_computer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    app = terminal(new_game(), "home")
    app.automatic_paused = True
    before = saved_facts(app.game)

    def fail_save(*args: object) -> None:
        raise OSError("synthetic save failure")

    monkeypatch.setattr("bowl_bound.cli.write_save", fail_save)
    assert not app.command("w")
    assert "synthetic save failure" in app.output.getvalue()
    assert "Resume:" not in app.output.getvalue()
    assert saved_facts(app.game) == before and app.automatic_paused


def test_w_is_visible_in_compact_summary_and_contextual_help() -> None:
    app = terminal(new_game(), "home", compact=True)
    app.display()
    assert "W=save" in app.output.getvalue()
    app.output = io.StringIO()
    assert not app.command("?")
    assert "[W] Save Game" in app.output.getvalue()
