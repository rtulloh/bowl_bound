"""RULE-044: distinguish prior-play timing from an unresolved selected play."""

import io
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.coaching import BaselineCoach
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.save_game import SavedGame, dumps_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, write_team
from tests.test_armed_timeouts import saved_after_kickoff
from tests.test_models import provenance
from tests.test_regulation import kickoff, new_game, snap


@pytest.mark.parametrize("quarter,remaining", [(1, 900), (2, 41), (4, 41)])
def test_web_selected_play_timeout_matches_cli_at_on_same_normal_state(
    monkeypatch: pytest.MonkeyPatch, quarter: int, remaining: int
) -> None:
    from bowl_bound.cli import TerminalGame
    from bowl_bound.save_game import loads_game

    base = saved_after_kickoff()
    saved = SavedGame.new(
        *base._charts.values(),
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        mode="regulation",
        clock=Clock(quarter, remaining),
        coach_policy="baseline-v10",
    )
    saved.decide("toss:kick")
    saved.kick("kickoff")
    saved.decide("kick:touchback")
    saved.snap("1", "A")

    def load(key: str) -> TeamChart:
        return saved._charts["home" if key.endswith("home") else "away"]

    cli_game = loads_game(dumps_game(saved), load)
    web_game = loads_game(dumps_game(saved), load)
    monkeypatch.setattr(BaselineCoach, "offense", lambda self, observation: "1")
    cli = TerminalGame(cli_game, load, human_side="away", output=io.StringIO())
    assert cli.command("AT")
    web_game.coach_execute("away", "action", "timeout:away")
    web_game.coach_step("away", "A")
    web_view, cli_view = web_game.view(), cli_game.view()
    assert replace(web_view, timing_log=()) == replace(cli_view, timing_log=())
    assert [replace(charge, method="") for charge in web_view.timing_log] == [
        replace(charge, method="") for charge in cli_view.timing_log
    ]
    assert cli_view.timing_log[-1].method == "clock:timeout:away"
    view = web_game.view()
    assert view.clock.remaining == remaining - 40
    assert view.clock.timeouts == (3, 2)
    assert [(charge.seconds, charge.method) for charge in view.timing_log[-2:]] == [
        (30, "standard"),
        (10, "timeout:away"),
    ]
    assert view.armed_timeout is None


@pytest.mark.parametrize("quarter,remaining", [(1, 900), (2, 41), (4, 41)])
@pytest.mark.parametrize("choice", ["interception:return", "interception:decline"])
@pytest.mark.parametrize("conditional", [False, True])
def test_timeout_waits_for_cpu_owned_continuation_after_prior_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    quarter: int,
    remaining: int,
    choice: str,
    conditional: bool,
) -> None:
    charts = saved_after_kickoff()._charts
    home = charts["home"]
    charts["home"] = replace(
        home,
        offense=team_chart(
            "Home",
            season=2002,
            offense=0,
            defense=0,
            plays={Play.EIGHT: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15)},
        ).offense,
    )
    saved = SavedGame.new(
        *charts.values(),
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        mode="regulation",
        clock=Clock(quarter, remaining),
        coach_policy="baseline-v10",
    )
    saved.decide("toss:kick")
    saved.kick("kickoff")
    saved.decide("kick:touchback")
    saved.snap("1", "A")
    assert saved.view().clock_optional
    root = tmp_path / "seasons"
    for chart in charts.values():
        write_team(root, chart)
    # Force a legal pending CPU call, retaining real coordinator/rules/dice.
    monkeypatch.setattr(BaselineCoach, "offense", lambda self, observation: "8")
    client = TestClient(create_app(root))
    loaded = client.post(
        "/api/games/load?human_side=away",
        content=dumps_game(saved),
        headers={"content-type": "application/json"},
    )
    assert loaded.status_code == 200, loaded.text
    before = loaded.json()
    key = before["game_id"]
    selected = client.post(
        f"/api/games/{key}/action?human_side=away",
        json={"action": "timeout_after:away" if conditional else "timeout:away"},
    )
    assert selected.status_code == 200, selected.text
    selected_data = selected.json()
    assert selected_data["view"]["clock"] == before["view"]["clock"]
    assert selected_data["turn"]["human_role"] == "defense"
    played = client.post(
        f"/api/games/{key}/coach",
        json={
            "human_side": "away",
            "human_call": "A",
            "expected_revision": selected_data["revision"],
        },
    )
    assert played.status_code == 200, played.text
    data = played.json()
    assert data["report"]["pending"]
    assert data["report"]["timing_label"] is None
    assert data["turn"]["human_role"] == "decision"
    assert not data["turn"]["automatic"]
    pending = data["view"]
    assert pending["armed_timeout"] == "away"
    assert pending["conditional_timeout"] is conditional
    assert pending["clock"]["remaining"] == remaining - 30
    assert pending["clock"]["timeouts"] == [3, 3]
    prior_number = before["view"]["log"][-1]["number"]
    assert pending["timing_log"][-1]["play_number"] == prior_number
    assert pending["timing_log"][-1]["seconds"] == 30
    pending_text = client.get(f"/api/games/{key}/save").text
    resumed = client.post(
        "/api/games/load?human_side=away",
        content=pending_text,
        headers={"content-type": "application/json"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["view"] == pending
    resumed_key = resumed.json()["game_id"]
    finished = client.post(f"/api/games/{key}/decision?human_side=away", json={"choice": choice})
    assert finished.status_code == 200, finished.text
    final = finished.json()
    assert not final["report"]["pending"]
    resumed_final = client.post(
        f"/api/games/{resumed_key}/decision?human_side=away", json={"choice": choice}
    )
    assert resumed_final.status_code == 200, resumed_final.text
    assert resumed_final.json()["view"] == final["view"]
    view = final["view"]
    assert view["clock"]["quarter"] == quarter
    assert view["clock"]["remaining"] == remaining - 40
    assert view["clock"]["timeouts"] == ([3, 3] if conditional else [3, 2])
    assert view["armed_timeout"] is None and view["armed_timeout_label"] is None
    assert view["timing_log"][-1]["play_number"] == final["report"]["number"]
    assert view["timing_log"][-1]["seconds"] == 10
    assert view["timing_log"][-1]["method"] == ("standard" if conditional else "timeout:away")
    assert "armed" not in pending["armed_timeout_label"].lower()
    assert "this play" in pending["armed_timeout_label"]
    assert "previous play" in selected_data["view"]["clock_timing_label"].lower()
    assert "30 seconds" in selected_data["view"]["clock_timing_label"]
    assert final["report"]["timing_label"] == (
        None if conditional else "Away timeout used; this play took 10 seconds."
    )
    assert view["log"][-1]["timing_label"] == final["report"]["timing_label"]
    stable = client.get(f"/api/games/{key}?human_side=away").json()
    assert stable["view"]["clock"] == view["clock"]
    assert stable["view"]["timing_log"] == view["timing_log"]
    exported = client.get(f"/api/games/{key}/save").text
    restored = client.post(
        "/api/games/load?human_side=away",
        content=exported,
        headers={"content-type": "application/json"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["view"] == view


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
def test_completed_selected_play_uses_timeout_before_period_can_expire(quarter: int) -> None:
    game = new_game(clock=Clock(quarter, 11), gain=2)
    kickoff(game)
    game.action("timeout:away")
    report = snap(game)
    view = game.view()
    assert not report.pending
    assert view.clock.quarter == quarter and view.clock.remaining == 1
    assert view.clock.timeouts == (3, 2)
    assert view.armed_timeout is None and view.armed_timeout_label is None
    assert view.timing_log[-1].play_number == report.number
    assert (view.timing_log[-1].seconds, view.timing_log[-1].method) == (10, "timeout:away")


def test_pending_choice_does_not_take_timeout_until_actual_play_completes() -> None:
    game = new_game(gain=2)
    kickoff(game)
    snap(game)
    game.action("timeout:away")
    report = game.snap(
        "RZDZ",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 3, 5),
                OffensiveRoll(1, 2, 3),
                DefensiveRoll(1, 0),
            ]
        ),
    )
    assert report.pending
    assert game.view().pending.chooser_side == "home"
    assert game.view().clock.remaining == 870
    report = game.decide("razzle:1:15", dice=ScriptedDice([DefensiveRoll(1, 0)]))
    assert not report.pending
    assert game.view().clock.remaining == 860
    assert game.view().clock.timeouts == (3, 2)
    assert game.view().armed_timeout is None
