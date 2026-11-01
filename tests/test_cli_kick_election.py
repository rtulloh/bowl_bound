"""Kick election assigns a team; the assigned kicker chooses normal or onside."""

import io
import json
from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame
from bowl_bound.save_game import dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.test_cli import saved_facts
from tests.test_cli_shortcuts import live, regulation


@pytest.mark.parametrize("seed", [7, 39])
@pytest.mark.parametrize("command", ["k", "2", "choose toss:kick"])
@pytest.mark.parametrize("kick_action", ["kickoff", "onside_kickoff"])
def test_kick_election_leaves_kick_type_to_assigned_kicker(
    seed: int,
    command: str,
    kick_action: str,
) -> None:
    app = regulation(seed=seed)
    owner = app.game.view().pending.chooser_side
    assert owner == ("away" if seed == 7 else "home")
    app.human_side = owner
    reference = loads_game(dumps_game(app.game), app.load_team)
    assert app.command(command)
    reference.coach_execute(owner, "decide", "toss:kick")
    assert saved_facts(app.game) == saved_facts(reference)
    assert app.game.view().phase == "kickoff"
    assert {action.key for action in app.game.view().actions.special} == {
        "kickoff",
        "onside_kickoff",
    }
    shortcut = "o" if kick_action == "onside_kickoff" else "k"
    assert app.command(shortcut)
    reference.coach_execute(owner, "kick", kick_action)
    assert saved_facts(app.game) == saved_facts(reference)
    if kick_action == "kickoff":
        assert app.game.view().pending is not None
        assert "kick:touchback" in {choice.id for choice in app.game.view().pending.choices}
    else:
        assert app.game.view().pending is None
    document = json.loads(dumps_game(app.game))
    assert [record["operation"] for record in document["commands"]] == ["decide", "kick"]
    assert loads_game(dumps_game(app.game), app.load_team).view() == app.game.view()


@pytest.mark.parametrize("seed", [7, 39])
def test_human_kicker_gets_a_kick_type_choice_after_electing_to_kick(seed: int) -> None:
    app = regulation(seed=seed)
    app.human_side = app.game.view().pending.chooser_side
    seen = []

    def read_line(_prompt: str) -> str:
        view, turn = app.public_view()
        seen.append((view, turn))
        assert len(seen) <= 3, "unexpected additional terminal input"
        return "k" if len(seen) < 3 else "quit"

    assert app.run(read_line) == 0
    assert len(seen) == 3
    assert seen[0][0].phase == "opening_choice"
    assert seen[1][0].phase == "kickoff"
    assert seen[1][1].human_role == "offense" and not seen[1][1].automatic
    assert "onside_kickoff" in {action.key for action in seen[1][1].actions.special}
    assert seen[2][0].phase != "kickoff"
    assert "Not applied:" not in app.output.getvalue()
    assert (
        sum(
            record["operation"] == "kick" for record in json.loads(dumps_game(app.game))["commands"]
        )
        == 1
    )


@pytest.mark.parametrize("seed", [7, 39])
def test_halftime_schedules_reciprocal_kicker_with_both_kick_types(seed: int) -> None:
    app = regulation(Clock(2, 10), seed=seed)
    live(app)
    app.game.snap("1", "A")
    app.game.decide("clock:runoff")
    view = app.game.view()
    assert view.phase == "kickoff" and view.pending is None
    assert view.clock.quarter == 3 and view.clock.remaining == 900
    assert view.state.possession == ("away" if view.opening_kicker == "home" else "home")
    assert {action.key for action in view.actions.special} == {"kickoff", "onside_kickoff"}
    before = saved_facts(app.game)
    assert not app.command("choose half:kick")
    assert saved_facts(app.game) == before
    assert "Not applied:" in app.output.getvalue()


def test_receive_and_inspection_do_not_submit_a_human_kickoff() -> None:
    app = regulation()
    assert app.command("r")
    app.human_side = app.game.view().state.possession
    assert [record["operation"] for record in json.loads(dumps_game(app.game))["commands"]] == [
        "decide",
    ]
    before = saved_facts(app.game)
    for command in ("?", "status", "trace", ""):
        assert not app.command(command)
        assert saved_facts(app.game) == before
    assert app.game.view().phase == "kickoff"


def test_loading_an_existing_kickoff_state_does_not_replay_the_election(tmp_path: Path) -> None:
    app = regulation()
    app.game.execute_with_view("decide", ["toss:kick"])
    path = tmp_path / "awaiting-kick.json"
    path.write_text(dumps_game(app.game))
    before = saved_facts(app.game)
    restored = TerminalGame(
        regulation().game, app.load_team, human_side=app.human_side, output=io.StringIO()
    )
    assert restored.command(f'load "{path}"')
    assert restored.run(lambda _: "quit") == 0
    assert saved_facts(restored.game) == before
    assert restored.game.view().phase == "kickoff"


def test_failed_kick_type_choice_waits_for_explicit_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = regulation()
    original = app.game.coach_execute
    attempts = 0

    def fail_kick(human_side: str, operation: str, value: str):
        nonlocal attempts
        if operation == "kick":
            attempts += 1
            raise ValueError("synthetic kickoff failure")
        return original(human_side, operation, value)

    monkeypatch.setattr(app.game, "coach_execute", fail_kick)
    assert app.command("choose toss:kick")
    assert attempts == 0
    assert not app.command("k")
    assert attempts == 1
    assert app.game.view().phase == "kickoff"
    assert "Not applied:" in app.output.getvalue()
    before = saved_facts(app.game)
    for command in ("?", "status", "trace"):
        assert not app.command(command)
        assert saved_facts(app.game) == before and attempts == 1
    monkeypatch.setattr(app.game, "coach_execute", original)
    assert app.command("k")
    assert (
        sum(
            record["operation"] == "kick" for record in json.loads(dumps_game(app.game))["commands"]
        )
        == 1
    )
