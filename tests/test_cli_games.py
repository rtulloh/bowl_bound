"""Scripted terminal games reconcile with the unchanged engine, API and save codec."""

import io
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame, main
from bowl_bound.coaching_session import CoachingTurn, GameView
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.sample_teams import install_samples, sample_teams
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import default_teams, team_chart, write_team
from tests.test_models import provenance


def next_command(view: GameView, turn: CoachingTurn | None, step: int) -> str:
    if view.finished:
        return "quit"
    pending = turn.pending if turn else view.pending
    if pending and not getattr(view, "clock_optional", False):
        choices = [choice.id for choice in pending.choices if choice.enabled]
        preferred = (
            "clock:runoff",
            "ot:offense",
            "conversion:kick",
            "kick:touchback",
            "end_zone:touchback",
            "interception:return",
        )
        return "choose " + next((key for key in preferred if key in choices), choices[0])
    actions = turn.actions if turn else view.actions
    if turn and turn.human_role in {"offense", "defense"}:
        calls = actions.offense + actions.defense
        if calls:
            return "call " + calls[step % len(calls)].key
    if actions.special and not actions.offense:
        return "kick " + actions.special[0].key
    raise AssertionError("automatic CPU turns must be handled without terminal input")


@pytest.mark.parametrize("human", ["home", "away"])
def test_scripted_terminal_complete_games_match_direct_engine_and_saved_state(human: str) -> None:
    teams = sample_teams()

    def new() -> SavedGame:
        return SavedGame.new(
            *teams,
            home_id="2007/cedar-valley",
            away_id="2007/harbor-tech",
            seed=39,
            coach_seed=31,
            mode="regulation",
        )

    def loader(key: str) -> TeamChart:
        return teams[0] if key.endswith("cedar-valley") else teams[1]

    app = TerminalGame(
        new(),
        loader,
        human_side=human,
        output=io.StringIO(),
        compact=True,
        trace=True,
    )
    steps = 0
    phases: set[str] = set()
    choice_families: set[str] = set()

    def choose(_prompt: str) -> str:
        nonlocal steps
        steps += 1
        assert steps < 1600, "terminal game failed to finish"
        view, turn = app.public_view()
        phases.add(view.phase)
        command = next_command(view, turn, steps)
        if command.startswith("choose "):
            choice_families.add(command.split(":")[0])
        return command

    assert app.run(choose) == 0
    final = app.game.view()
    assert final.finished and not app.automatic_paused
    assert "Not applied:" not in app.output.getvalue()
    assert final.score.home == sum(
        event.points for event in final.scoring if event.team == final.home
    )
    assert final.score.away == sum(
        event.points for event in final.scoring if event.team == final.away
    )
    for quarter in range(1, 5):
        assert (
            sum(item.before - item.after for item in final.timing_log if item.quarter == quarter)
            == 900
        )
    assert phases and choice_families  # Human-owned choices are exercised in both arrangements.
    reference = new()
    document = json.loads(dumps_game(app.game))
    for record in document["commands"]:
        assert record["error"] is None
        reference.execute_with_view(record["operation"], record["arguments"])
    assert reference.view() == final  # Includes every scoring/statistics/timing/trace field.
    restored = loads_game(dumps_game(app.game), loader)
    assert restored.view() == reference.view()
    replay = json.loads(dumps_game(reference))
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert document[key] == replay[key]
    assert "Inspect, save or quit; gameplay is finished." in app.output.getvalue()


@pytest.mark.parametrize("human", ["home", "away"])
def test_terminal_pending_interception_resume_matches_api_exact_future(
    tmp_path: Path,
    human: str,
) -> None:
    teams = tuple(replace(team, season=2002) for team in default_teams())
    for chart in teams:
        write_team(tmp_path, chart)
    game = SavedGame.new(
        *teams, home_id="2002/alpha-tech", away_id="2002/beta-state", seed=7, coach_seed=31
    )
    game.snap("9", "A")

    def loader(key: str) -> TeamChart:
        return teams[0] if key.endswith("alpha-tech") else teams[1]

    save_path = tmp_path / "pending.json"
    app = TerminalGame(game, loader, human_side=human, output=io.StringIO())
    before = app.game.view()
    assert not app.command(f'save "{save_path}"')
    app.command("choose interception:return")
    assert app.command(f'load "{save_path}"')
    assert app.game.view() == before
    assert app.human_side == human
    client = TestClient(create_app(tmp_path))
    loaded = client.post("/api/games/load", content=save_path.read_bytes())
    assert loaded.status_code == 200
    path = "/api/games/" + loaded.json()["game_id"]

    def expected_api_view() -> dict:
        view = app.game.view()
        expected = jsonable_encoder(view)
        for item, report in zip(expected["log"], view.log, strict=True):
            item["commentary"] = app.game.commentary(report)
        return expected

    assert expected_api_view() == loaded.json()["view"]
    # Select the pending decision owner; the other team remains computer-controlled.
    app.human_side = app.game.view().pending.chooser_side
    assert app.command("choose interception:return")
    response = client.post(path + "/decision", json={"choice": "interception:return"})
    assert response.status_code == 200
    assert expected_api_view() == response.json()["view"]
    call = "1" if app.game.view().state.possession == app.human_side else "A"
    assert app.command(call)
    response = client.post(path + "/coach", json={"human_side": app.human_side, "human_call": call})
    assert response.status_code == 200
    assert expected_api_view() == response.json()["view"]


def test_terminal_fumble_recovery_keeps_existing_end_zone_decision_and_rolls() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2)
    home = replace(
        team_chart("Alpha Tech", season=2002, plays={Play.ONE: fumble}),
        recovery_range=range(10, 20),
    )
    away = team_chart("Beta State", season=2002, defense=0)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(3, 0), OffensiveRoll(2, 4, 4)])
    game = SavedGame.new(
        home,
        away,
        home_id="2002/alpha-tech",
        away_id="2002/beta-state",
        seed=7,
        coach_seed=31,
        start_yards_to_goal=2,
        dice=dice,
    )
    app = TerminalGame(
        game,
        lambda key: home if key.endswith("alpha-tech") else away,
        human_side="home",
        output=io.StringIO(),
        trace=True,
    )
    assert app.command("1")
    pending = app.game.view().pending
    assert pending is not None and pending.chooser == "Beta State"
    assert any(choice.id == "end_zone:touchback" and choice.enabled for choice in pending.choices)
    app.human_side = pending.chooser_side
    assert app.command("choose end_zone:touchback")
    report = app.game.view().log[-1]
    assert report.outcome == "touchback"
    assert [entry.section for entry in report.trace] == ["offense", "defense", "fumble_recovery"]
    assert "fumble_recovery" in app.output.getvalue()
    assert len(json.loads(dumps_game(app.game))["rolls"]) == 3


def test_module_invocation_needs_no_web_server_or_private_teams(tmp_path: Path) -> None:
    install_samples(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bowl_bound",
            "--play",
            "-d",
            "medium",
            "--seasons",
            str(tmp_path),
            "--away",
            "2007/harbor-tech",
            "--home",
            "2007/cedar-valley",
            "--human",
            "home",
            "--compact",
            "--seed",
            "39",
        ],
        input="status\nquit\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Cedar Valley" in completed.stdout and "Harbor Tech" in completed.stdout
    assert "choose toss:" in completed.stdout
    assert "not saved automatically" in completed.stdout


def test_main_new_and_loaded_postseason_keep_explicit_human_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_samples(tmp_path)
    path = tmp_path / "postseason.json"
    commands = iter([f'save "{path}"', "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))
    assert main(["--seasons", str(tmp_path), "--human", "home", "--game-type", "postseason"]) == 0
    document = json.loads(path.read_text())
    assert document["config"]["game_type"] == "postseason"
    monkeypatch.setattr("builtins.input", lambda _: "quit")
    assert main(["--seasons", str(tmp_path), "--load", str(path), "--human", "away"]) == 0


def test_terminal_overtime_pending_choice_keeps_engine_authority() -> None:
    from tests.synthetic_teams import yards
    from tests.test_special_teams import special_chart

    teams = tuple(
        replace(
            team_chart(name, season=2002, offense=3, defense=0),
            special_teams=special_chart(name, kickoff=yards(70)).special_teams,
        )
        for name in ("Home", "Away")
    )
    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        mode="regulation",
        clock=Clock(4, 10),
    )
    app = TerminalGame(
        game,
        lambda key: teams[key.endswith("away")],
        human_side="home",
        output=io.StringIO(),
        trace=True,
    )
    # Engine setup reaches overtime without pretending both teams are human.
    for operation, arguments in (
        ("decide", ["toss:receive"]),
        ("kick", ["kickoff"]),
        ("decide", ["kick:touchback"]),
        ("snap", ["1", "A"]),
        ("decide", ["clock:runoff"]),
    ):
        game.execute_with_view(operation, arguments)
    app.human_side = game.view().pending.chooser_side
    assert game.view().phase == "overtime_choice"
    before = dumps_game(game)
    app.display()
    assert not app.command("choose ot:unknown")
    after = json.loads(dumps_game(game))
    expected = json.loads(before)
    for key in ("saved_at", "integrity"):
        after.pop(key)
        expected.pop(key)
    assert after == expected
    pending = game.view().pending
    for choice in pending.choices:
        if not choice.enabled:
            assert not app.command("choose " + choice.id)
    choice = next(choice for choice in pending.choices if choice.enabled)
    assert app.command("choose " + choice.id)
    assert game.view().phase != "overtime_choice"
    assert "overtime_toss" in app.output.getvalue()


def test_standalone_play_does_not_import_web_pdf_or_paydirt_dependencies(tmp_path: Path) -> None:
    install_samples(tmp_path)
    script = """
import importlib.abc
import runpy
import sys
class CoreOnly(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'backend', 'fastapi', 'uvicorn', 'pdfplumber', 'paydirt'}:
            raise AssertionError('CLI imported optional dependency: ' + fullname)
sys.meta_path.insert(0, CoreOnly())
sys.argv[0] = 'bowl_bound'
runpy.run_module('bowl_bound', run_name='__main__')
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, "--seasons", str(tmp_path), "--human", "home"],
        input="status\nquit\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Bowl Bound" in completed.stdout
