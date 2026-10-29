"""Public-safe lifecycle acceptance edges across entry points."""

from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame, main, write_save
from bowl_bound.save_game import SavedGame
from bowl_bound.session import PlaySession
from tests.test_commentary_lifecycle import setup_game, write_rosters


def test_roster_snapshots_are_isolated_between_games(tmp_path: Path) -> None:
    first, _ = setup_game(tmp_path)
    second, _ = setup_game(tmp_path)
    write_rosters(tmp_path)
    first.load_rosters(tmp_path)
    value = first.snap("1", "A")
    write_rosters(tmp_path, "Second Runner")
    second.load_rosters(tmp_path)
    assert "H Runner" in first.commentary(value)
    assert "Second Runner" in second.commentary(value)


@pytest.mark.parametrize("directory", ["2007", "2007/away"])
def test_roster_intermediate_symlinks_rejected(tmp_path: Path, directory: str) -> None:
    game, _ = setup_game(tmp_path)
    write_rosters(tmp_path)
    path = tmp_path / directory
    backup = path.with_name(path.name + "-backup")
    path.rename(backup)
    path.symlink_to(backup, target_is_directory=True)
    from bowl_bound.roster import RosterFormatError

    with pytest.raises(RosterFormatError, match="symlinked"):
        game.load_rosters(tmp_path)


@pytest.mark.parametrize("human", ["home", "away"])
@pytest.mark.parametrize("mode", ["drive", "regulation"])
@pytest.mark.parametrize("reverse", [False, True])
def test_cli_main_creation_and_reload_use_canonical_team_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    human: str,
    mode: str,
    reverse: bool,
) -> None:
    _, catalog = setup_game(tmp_path, mode=mode)
    write_rosters(tmp_path)
    home_id, away_id = ("2007/away", "2007/home") if reverse else ("2007/home", "2007/away")
    game = SavedGame.new(
        catalog.load(home_id),
        catalog.load(away_id),
        home_id=home_id,
        away_id=away_id,
        seed=7,
        coach_seed=31,
        mode=mode,
    )
    path = tmp_path / "resume.json"
    write_save(path, game)
    seen: list[str] = []

    def run(terminal: TerminalGame) -> int:
        assert terminal.human_side == human
        # Synthetic committed report for current home side; not a football mutation.
        value = PlaySession(catalog.load(home_id), catalog.load(away_id), 7, 65).snap("1", "A")
        expected = "A Runner" if reverse else "H Runner"
        assert expected in terminal.game.commentary(value)
        assert terminal.roster_root == tmp_path
        seen.append(expected)
        return 0

    monkeypatch.setattr(TerminalGame, "run", run)
    assert main(["--seasons", str(tmp_path), "--load", str(path), "--human", human]) == 0
    if mode == "regulation":
        assert (
            main(
                ["--seasons", str(tmp_path), "--home", home_id, "--away", away_id, "--human", human]
            )
            == 0
        )
    assert len(seen) == (2 if mode == "regulation" else 1)
