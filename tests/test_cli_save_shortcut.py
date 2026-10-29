"""One-key private saves are explicit, create-only and gameplay-neutral."""

import io
import shlex
import sys
from pathlib import Path

import pytest

from bowl_bound.save_game import loads_game
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
