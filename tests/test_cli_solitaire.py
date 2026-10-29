"""The player controls one team; only the engine may submit both concealed calls."""

import io
from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame, main
from tests.test_cli import new_game, saved_facts, terminal


def test_manual_startup_is_rejected_before_loading_teams(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--seasons", str(tmp_path), "--human", "manual"])
    assert error.value.code == 2


def test_terminal_rejects_two_sided_control() -> None:
    game = new_game()
    before = saved_facts(game)
    with pytest.raises(ValueError, match="home or away"):
        TerminalGame(game, lambda key: None, human_side="manual", output=io.StringIO())
    assert saved_facts(game) == before


@pytest.mark.parametrize("human", ["home", "away"])
def test_help_and_bad_paired_calls_preserve_solitaire_privacy(human: str) -> None:
    app = terminal(new_game(), human)
    before = saved_facts(app.game)
    _, original = app.game.coach_view(human)
    for command in ("commands", "?", "snap 1 A", "1 A", "TO", "TD", "TH", "TA"):
        assert not app.command(command)
        assert saved_facts(app.game) == before
        assert app.game.coach_view(human)[1] == original
    output = app.output.getvalue()
    assert "Manual" not in output and "manual" not in output
    assert "snap PLAY" not in output and "Pair fresh" not in output
    assert ("[1] Line Plunge" in output) == (human == "home")
    assert ("[A] Standard" in output) == (human == "away")
    reference = new_game()
    call = "1" if human == "home" else "A"
    reference.coach_step(human, call)
    assert app.command(call)
    assert saved_facts(app.game) == saved_facts(reference)


def test_startup_help_offers_only_single_human_sides(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "{home,away}" in help_text and "manual" not in help_text.lower()
