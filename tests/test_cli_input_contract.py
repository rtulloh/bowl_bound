"""CLI-044: actionable command parsing and safe lifecycle boundaries."""

from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.cli import main, write_save
from bowl_bound.save_game import SavedGame
from bowl_bound.timing import Clock
from tests.synthetic_teams import default_teams, write_team
from tests.test_cli import new_game, saved_facts, terminal
from tests.test_cli_shortcuts import live, regulation


@pytest.mark.parametrize(
    "command,message",
    [
        ("SAVE", "Save requires a path"),
        ("LOAD", "Load requires a path"),
        ("CALL", "Call requires an offered play or formation"),
        ("CHOOSE", "Choose requires an offered choice"),
        ("KICK", "Kick requires an offered special-team action"),
    ],
)
def test_commands_without_required_arguments_explain_what_is_missing(
    command: str, message: str
) -> None:
    app = terminal(new_game())
    before = saved_facts(app.game)

    assert not app.command(command)

    assert message in app.output.getvalue()
    assert saved_facts(app.game) == before


def test_command_words_are_case_insensitive_but_paths_and_ids_are_preserved() -> None:
    app = terminal(new_game())
    before = saved_facts(app.game)

    assert not app.command("STATUS")
    assert "Alpha Tech" in app.output.getvalue()
    assert saved_facts(app.game) == before
    assert app.command("CALL 1")
    reference = new_game()
    reference.coach_step("home", "1")
    assert saved_facts(app.game) == saved_facts(reference)

    choice_app = regulation()
    choice_before = saved_facts(choice_app.game)
    assert not choice_app.command("CHOOSE TOSS:RECEIVE")
    assert saved_facts(choice_app.game) == choice_before
    assert choice_app.command("CHOOSE toss:receive")


def test_quit_during_pending_decision_does_not_write_a_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    game = new_game()
    assert game.snap("9", "A").pending
    app = terminal(game)
    before = saved_facts(game)

    assert not app.command("QUIT")

    assert app.stopped and saved_facts(game) == before
    assert not (tmp_path / "private-data" / "saves").exists()


def test_loading_while_computer_is_paused_clears_pause(tmp_path: Path) -> None:
    save_path = tmp_path / "paused.json"
    saved_game = new_game()
    write_save(save_path, saved_game)
    app = terminal(new_game())
    app.automatic_paused = True

    assert app.command(f"LOAD {save_path}")

    assert not app.automatic_paused
    assert saved_facts(app.game) == saved_facts(saved_game)


def test_timeout_suffix_at_nonoptional_period_end_does_not_spend_timeout() -> None:
    app = regulation(Clock(2, 10))
    live(app)
    view, turn = app.public_view()
    assert turn is not None and turn.actions.offense
    app.game.coach_step(app.human_side, turn.actions.offense[0].key)
    timeouts = app.game.view().clock.timeouts

    assert app.command("7T")

    view = app.game.view()
    assert view.phase == "kickoff" and view.clock.quarter == 3
    assert view.clock.timeouts == timeouts
    assert app.last_report is not None and app.last_report.outcome == "period_boundary"
    assert "Play applied; your timeout was not offered" in app.output.getvalue()


def test_keyboard_interrupt_during_computer_turn_exits_without_partial_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = new_game()
    app = terminal(game, human="away")
    before = saved_facts(game)

    def interrupt(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(game, "coach_step", interrupt)

    assert app.run(lambda _: "") == 130
    assert saved_facts(game) == before
    assert "Exited; game not saved automatically" in app.output.getvalue()


def test_cli_load_rejects_mismatched_local_team_fingerprint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    seasons = tmp_path / "seasons"
    home, away = default_teams()
    for chart in (home, away):
        write_team(seasons, chart)
    save_path = tmp_path / "teams.json"
    game = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=7,
    )
    write_save(save_path, game)
    changed_cell = replace(home.offense[0].cell, yards=home.offense[0].cell.yards + 1)
    changed_home = replace(
        home,
        offense=(replace(home.offense[0], cell=changed_cell), *home.offense[1:]),
    )
    write_team(seasons, changed_home)

    result = main(["--seasons", str(seasons), "--load", str(save_path)])

    captured = capsys.readouterr()
    assert result == 1
    assert "Saved teams do not match the installed teams" in captured.err
