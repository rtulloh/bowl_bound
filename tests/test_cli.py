"""Synthetic CLI tests: public engine interfaces, no server or historical charts."""

import io
import json
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.cli import TeamCatalog, TerminalGame, main
from bowl_bound.models import TeamChart
from bowl_bound.sample_teams import install_samples
from bowl_bound.save_game import SavedGame, dumps_game
from tests.synthetic_teams import default_teams, write_team


def new_game(**kwargs: object) -> SavedGame:
    return SavedGame.new(
        *(replace(chart, season=2002) for chart in default_teams()),
        home_id="2002/alpha-tech",
        away_id="2002/beta-state",
        seed=7,
        coach_seed=31,
        **kwargs,
    )


def saved_facts(game: SavedGame) -> dict[str, object]:
    data = json.loads(dumps_game(game))
    return {key: value for key, value in data.items() if key not in {"saved_at", "integrity"}}


def terminal(game: SavedGame, human: str = "home", **kwargs: object) -> TerminalGame:
    teams = tuple(replace(chart, season=2002) for chart in default_teams())
    return TerminalGame(
        game,
        lambda key: teams[0] if key.endswith("alpha-tech") else teams[1],
        human_side=human,
        output=io.StringIO(),
        **kwargs,
    )


def test_catalog_lists_and_loads_public_samples_without_a_server(tmp_path: Path) -> None:
    install_samples(tmp_path)
    catalog = TeamCatalog(tmp_path)
    assert [entry.key for entry in catalog.teams()] == [
        "2007/cedar-valley",
        "2007/harbor-tech",
    ]
    assert catalog.load("2007/cedar-valley").name == "Cedar Valley"
    with pytest.raises(ValueError, match="season/team"):
        catalog.load("../private")


def test_catalog_skips_symlinks_and_reports_invalid_team_without_raw_contents(
    tmp_path: Path,
) -> None:
    for chart in (replace(chart, season=2002) for chart in default_teams()):
        write_team(tmp_path, chart)
    (tmp_path / "2003").symlink_to(tmp_path / "2002", target_is_directory=True)
    broken = tmp_path / "2002" / "broken"
    broken.mkdir()
    (broken / "team.yaml").write_text("SECRET bad chart")
    catalog = TeamCatalog(tmp_path)
    assert [entry.key for entry in catalog.teams()] == ["2002/alpha-tech", "2002/beta-state"]
    assert catalog.problems == ("2002/broken: could not be read",)
    with pytest.raises(ValueError, match="symlink"):
        catalog.load("2003/alpha-tech")


@pytest.mark.parametrize("human", ["home", "away"])
def test_inspection_and_bad_input_do_not_consume_dice_or_reveal_cpu_call(human: str) -> None:
    game = new_game()
    app = terminal(game, human)
    before = saved_facts(game)
    for command in ["status", "help", "stats", "log", "trace", "call invalid", "snap 1 A"]:
        assert not app.command(command)
    assert saved_facts(game) == before
    output = app.output.getvalue()
    title = "OFFENSIVE PLAY CALL" if human == "home" else "DEFENSIVE FORMATION"
    assert title in output
    assert "secret" not in output.lower() and "coach_seed" not in output
    expected_role = "offense" if human == "home" else "defense"
    assert game.coach_view(human)[1].human_role == expected_role
    assert ("[1] Line Plunge" in output) == (human == "home")
    assert ("[A] Standard" in output) == (human == "away")
    assert "(call " not in output


@pytest.mark.parametrize("human,calls", [("home", ("1", "9")), ("away", ("A", "F"))])
def test_terminal_calls_use_the_same_concealed_coordinator(
    human: str, calls: tuple[str, str]
) -> None:
    games = [new_game() for _ in calls]
    for game, call in zip(games, calls, strict=True):
        app = terminal(game, human)
        assert app.command("call " + call)
        reference = new_game()
        reference.coach_step(human, call)
        assert game.view() == reference.view()
        assert saved_facts(game) == saved_facts(reference)
    journals = [json.loads(dumps_game(game))["commands"] for game in games]
    hidden_index = 1 if human == "home" else 0
    assert journals[0][0]["arguments"][hidden_index] == journals[1][0]["arguments"][hidden_index]


def test_solitaire_call_renders_recorded_faces_not_new_rolls() -> None:
    game = new_game()
    app = terminal(game, trace=True)
    assert app.command("1")
    reference = new_game()
    report = reference.coach_step("home", "1")[0]
    assert saved_facts(game) == saved_facts(reference)
    assert report.description in app.output.getvalue()
    for entry in report.trace:
        assert str(entry.roll["total"]) in app.output.getvalue()
    before = saved_facts(game)
    assert not app.command("snap")
    assert saved_facts(game) == before


def test_private_save_and_bounded_failed_load_keep_the_current_game(tmp_path: Path) -> None:
    app = terminal(new_game())
    path = tmp_path / "private save.json"
    before = saved_facts(app.game)
    assert not app.command(f'save "{path}"')
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert saved_facts(app.game) == before
    original = path.read_bytes()
    app.command(f'save "{path}"')
    assert path.read_bytes() == original
    assert "already exists" in app.output.getvalue()
    assert app.command("1")
    advanced = saved_facts(app.game)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not a save")
    assert not app.command(f'load "{invalid}"')
    assert saved_facts(app.game) == advanced
    assert app.command(f'load "{path}"')
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("signal,code", [(EOFError, 0), (KeyboardInterrupt, 130)])
def test_eof_or_interrupt_does_not_resolve_pending_opening_choice(signal: type, code: int) -> None:
    game = new_game(mode="regulation")
    app = terminal(game, game.view().pending.chooser_side)
    before = saved_facts(game)

    def stop(_prompt: str) -> str:
        raise signal

    assert app.run(stop) == code
    assert saved_facts(game) == before
    assert "not saved automatically" in app.output.getvalue()


def test_module_help_listing_and_main_use_only_base_dependencies(tmp_path: Path, capsys) -> None:
    install_samples(tmp_path)
    assert main(["--seasons", str(tmp_path), "--list-teams"]) == 0
    assert "2007/cedar-valley" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    assert "--human" in capsys.readouterr().out


@pytest.mark.parametrize("human,key", [("home", "1"), ("away", "a")])
def test_bare_call_keys_match_paydirt_style_without_exposing_opposing_calls(
    human: str, key: str
) -> None:
    app = terminal(new_game(), human)
    assert app.command(key)
    reference = new_game()
    reference.coach_step(human, key.upper())
    assert saved_facts(app.game) == saved_facts(reference)
    before = saved_facts(app.game)
    assert not app.command("/")
    assert not app.command("?")
    assert saved_facts(app.game) == before
    assert "Statistics:" in app.output.getvalue()


def test_status_and_trace_show_engine_timeouts_and_recorded_toss_labels() -> None:
    app = terminal(new_game(mode="regulation"))
    before = saved_facts(app.game)
    app.command("status")
    app.command("trace")
    output = app.output.getvalue()
    assert "Beta State 0 (3) - Alpha Tech 0 (3)" in output
    assert "opening_toss" in output
    for die in app.game.view().toss_dice[0]["dice"]:
        assert f"{die['label']}={die['face']}" in output
    assert saved_facts(app.game) == before


def test_automatic_failure_stays_paused_through_inspection_save_and_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = new_game(mode="regulation")
    app = terminal(game, "home")
    count = 0

    def fail(*args: object) -> object:
        nonlocal count
        count += 1
        raise ValueError("synthetic computer error")

    monkeypatch.setattr(game, "coach_step", fail)
    app.advance_computer()
    assert app.automatic_paused and count == 1
    before = saved_facts(game)
    commands = iter(["status", f'save "{tmp_path / "paused.json"}"', "help", "quit"])
    assert app.run(lambda _: next(commands)) == 0
    assert count == 1 and saved_facts(game) == before
    assert app.command("retry")
    app.advance_computer()
    assert count == 2 and app.automatic_paused


def test_automatic_guard_stops_without_silently_selecting_a_human_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bowl_bound.cli as cli

    monkeypatch.setattr(cli, "MAX_AUTOMATIC_STEPS", 1)
    app = terminal(new_game(mode="regulation"), "home")
    app.advance_computer()
    assert app.automatic_paused
    before = saved_facts(app.game)
    app.command("status")
    app.advance_computer()
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("contents", [b"x" * (2 * 1024 * 1024 + 1), b"\xff\xfe"])
def test_bad_save_never_replaces_a_live_game(tmp_path: Path, contents: bytes) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(contents)
    app = terminal(new_game(), "away")
    before = saved_facts(app.game)
    assert not app.command(f'load "{path}"')
    assert saved_facts(app.game) == before and app.human_side == "away"


def test_main_preserves_owner_invocation_shape_and_rejects_legacy_new_game_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_samples(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "quit")
    assert (
        main(
            [
                "--seasons",
                str(tmp_path),
                "--play",
                "-d",
                "hard",
                "--away",
                "2007/harbor-tech",
                "--home",
                "2007/cedar-valley",
                "--compact",
            ]
        )
        == 0
    )
    assert "Bowl Bound" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exit_info:
        main(["--play", "-d", "baseline"])
    assert exit_info.value.code == 2
    assert "easy,medium,hard" in capsys.readouterr().err


def test_load_rejects_new_game_overrides_in_equals_syntax(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--load", str(tmp_path / "missing.json"), "--seed=7"]) == 1
    assert "omit new-game options" in capsys.readouterr().err


@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_failed_save_removes_only_its_new_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[BaseException],
) -> None:
    import bowl_bound.cli as cli

    path = tmp_path / "interrupted.json"
    original = cli.os.fdopen

    class FailingWriter:
        def __enter__(self) -> "FailingWriter":
            return self

        def write(self, text: str) -> None:
            stream.write(text[:10])
            raise failure()

        def __exit__(self, *_args: object) -> None:
            stream.close()

    stream = None

    def broken_writer(descriptor: int, *args: object, **kwargs: object) -> FailingWriter:
        nonlocal stream
        stream = original(descriptor, *args, **kwargs)
        return FailingWriter()

    monkeypatch.setattr(cli.os, "fdopen", broken_writer)
    with pytest.raises(failure):
        cli.write_save(path, new_game())
    assert not path.exists()
    assert stream.closed


def test_load_refuses_symlink_and_directory_without_replacing_live_game(tmp_path: Path) -> None:
    app = terminal(new_game())
    saved = tmp_path / "original.json"
    assert not app.command(f'save "{saved}"')
    link = tmp_path / "link.json"
    link.symlink_to(saved)
    before = saved_facts(app.game)
    for path in (link, tmp_path):
        assert not app.command(f'load "{path}"')
        assert saved_facts(app.game) == before
    assert "regular, non-symlinked" in app.output.getvalue()


def test_compact_solitaire_help_keeps_every_human_legal_call_label() -> None:
    app = terminal(new_game(), compact=True)
    app.display()
    assert "OFF: 1-9" in app.output.getvalue()
    assert "[1] Line Plunge" not in app.output.getvalue()
    assert not app.command("?")
    for action in app.public_view()[1].actions.offense:
        assert f"[{action.key}] {action.label}" in app.output.getvalue()


@pytest.mark.parametrize("human", ["home", "away"])
def test_terminal_save_restores_exact_coached_future(tmp_path: Path, human: str) -> None:
    from bowl_bound.sample_teams import sample_teams
    from tests.test_cli_games import next_command

    teams = sample_teams()

    def loader(key: str) -> TeamChart:
        return teams[0] if key.endswith("cedar-valley") else teams[1]

    app = TerminalGame(
        SavedGame.new(
            *teams,
            home_id="2007/cedar-valley",
            away_id="2007/harbor-tech",
            seed=39,
            coach_seed=31,
            mode="regulation",
        ),
        loader,
        human_side=human,
        output=io.StringIO(),
    )
    app.advance_computer()
    for step in range(1, 8):
        assert app.command(next_command(*app.public_view(), step))
        app.advance_computer()
    path = tmp_path / "coached.json"
    assert not app.command(f'save "{path}"')
    resumed = TerminalGame(new_game(), loader, human_side=human, output=io.StringIO())
    assert resumed.command(f'load "{path}"')
    assert saved_facts(resumed.game) == saved_facts(app.game)
    for step in range(8, 24):
        command = next_command(*app.public_view(), step)
        assert app.command(command) and resumed.command(command)
        app.advance_computer()
        resumed.advance_computer()
        assert saved_facts(resumed.game) == saved_facts(app.game)
        assert not app.automatic_paused and not resumed.automatic_paused


def test_unsupported_computer_report_stops_before_another_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_game = new_game()
    report, _ = report_game.execute_with_view("snap", ["1", "A"])
    unsupported = replace(
        report, supported=False, unsupported_reason="synthetic unsupported result"
    )
    app = terminal(new_game(mode="regulation"), "home")
    count = 0

    def unsupported_step(*_args: object):
        nonlocal count
        count += 1
        return unsupported, *app.game.coach_view("home"), None

    monkeypatch.setattr(app.game, "coach_step", unsupported_step)
    app.advance_computer()
    assert count == 1 and app.automatic_paused
    assert "synthetic unsupported result" in app.output.getvalue()
    app.command("status")
    app.advance_computer()
    assert count == 1


def test_load_rejects_a_file_swapped_to_symlink_during_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = terminal(new_game())
    target = tmp_path / "target.json"
    path = tmp_path / "swapped.json"
    target.write_text(dumps_game(new_game()))
    path.write_text(dumps_game(new_game()))
    original = Path.is_symlink

    def swap(candidate: Path) -> bool:
        result = original(candidate)
        if candidate == path and not result:
            path.unlink()
            path.symlink_to(target)
        return result

    monkeypatch.setattr(Path, "is_symlink", swap)
    before = saved_facts(app.game)
    assert not app.command(f'load "{path}"')
    assert saved_facts(app.game) == before
