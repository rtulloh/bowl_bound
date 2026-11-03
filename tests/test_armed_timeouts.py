"""RULE-042: side-owned next-play timeouts are engine modifiers, not plays."""

from pathlib import Path

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.regulation import RegulationGame
from bowl_bound.save_game import SavedGame
from bowl_bound.session import InvalidDecisionError
from bowl_bound.timing import Clock
from tests.test_regulation import kickoff, new_game, snap


def actions(game: RegulationGame) -> set[str]:
    return {a.key for a in game.view().game_actions}


@pytest.mark.parametrize("side,index", [("home", 0), ("away", 1)])
def test_timeout_after_kickoff_is_armed_without_consuming_clock_or_play(
    side: str, index: int
) -> None:
    game = new_game(gain=0)
    kickoff(game)
    before = game.view()
    assert {"timeout:home", "timeout:away"} <= actions(game)
    assert game.action(f"timeout:{side}") is None
    armed = game.view()
    assert armed.armed_timeout == side
    assert armed.armed_timeout_label
    assert armed.clock == before.clock
    assert armed.state == before.state and armed.log == before.log
    assert armed.score == before.score and armed.timing_log == before.timing_log
    assert {a for a in actions(game) if a.startswith("timeout:")} == {f"timeout:{side}"}
    report = snap(game)
    after = game.view()
    assert report.supported and not report.pending
    assert after.clock.remaining == before.clock.remaining - 10
    assert after.clock.timeouts[index] == before.clock.timeouts[index] - 1
    assert after.clock.timeouts[1 - index] == before.clock.timeouts[1 - index]
    assert after.armed_timeout is None and after.armed_timeout_label is None
    assert after.timing_log[-1].method == f"timeout:{side}"
    assert after.timing_log[-1].seconds == 10
    snap(game)
    assert game.view().clock_optional
    assert game.view().clock.timeouts == after.clock.timeouts


def test_arm_and_cancel_do_not_commit_a_prior_plays_pending_timing() -> None:
    game = new_game(gain=0)
    kickoff(game)
    snap(game)
    before = game.view()
    assert before.clock_optional
    game.action("timeout:away")
    assert game.view().clock == before.clock
    assert game.view().timing_log == before.timing_log
    game.action("timeout:away")
    assert game.view() == before
    game.action("timeout:away")
    snap(game)
    after = game.view()
    assert after.clock.remaining == before.clock.remaining - 40
    assert [(t.seconds, t.method) for t in after.timing_log[-2:]] == [
        (30, "standard"),
        (10, "timeout:away"),
    ]


@pytest.mark.parametrize("invalid", ["play", "defense", "kick", "other_timeout", "unknown_action"])
def test_invalid_action_preserves_armed_timeout_and_dice(invalid: str) -> None:
    game = new_game(gain=0)
    kickoff(game)
    game.action("timeout:home")
    before = game.view()
    source = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(3, 4, 5)])
    with pytest.raises((InvalidDecisionError, ValueError)):
        if invalid == "play":
            game.snap("bad", "A", dice=source)
        elif invalid == "defense":
            game.snap("1", "bad", dice=source)
        elif invalid == "kick":
            game.kick("kickoff", dice=source)
        else:
            game.action("timeout:away" if invalid == "other_timeout" else "bad", dice=source)
    assert game.view() == before
    game.snap("1", "A", dice=source)
    assert source.offensive() == OffensiveRoll(3, 4, 5)
    assert game.view().clock.timeouts == (2, 3)


@pytest.mark.parametrize("kind", ["punt", "field_goal", "kneel"])
def test_next_legal_special_or_automatic_play_consumes_timeout_once(kind: str) -> None:
    game = new_game(gain=0)
    kickoff(game)
    game.action("timeout:away")
    if kind in {"punt", "field_goal"}:
        game.kick(kind, dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)]))
        if kind == "punt":
            assert game.view().armed_timeout == "away"
            assert game.view().clock.timeouts == (3, 3)
            game.decide("kick:fair_catch")
    else:
        game.action(kind)
    view = game.view()
    assert view.armed_timeout is None
    assert view.clock.timeouts == (3, 2)
    assert view.timing_log[-1].seconds == 10
    assert view.timing_log[-1].method == "timeout:away"


@pytest.mark.parametrize("gain", [100, -100])
def test_scoring_play_clears_timeout_before_conversion_or_kickoff(gain: int) -> None:
    game = new_game(gain=gain)
    kickoff(game)
    game.action("timeout:away")
    snap(game)
    view = game.view()
    assert view.armed_timeout is None and view.clock.timeouts == (3, 2)
    assert view.timing_log[-1].method == "timeout:away"
    assert not any(a.startswith("timeout:") for a in actions(game))


def test_fourth_down_turnover_clears_armed_side_instead_of_following_possession() -> None:
    game = new_game(gain=0)
    kickoff(game)
    for _ in range(3):
        snap(game)
        game.decide("clock:runoff")
    assert game.view().state.down == 4
    game.action("timeout:home")
    snap(game)
    assert game.view().state.possession == "away"
    assert game.view().armed_timeout is None
    assert game.view().clock.timeouts == (2, 3)


@pytest.mark.parametrize(
    "counts,expected", [((0, 0), set()), ((3, 0), {"timeout:home"}), ((0, 2), {"timeout:away"})]
)
def test_only_sides_with_remaining_timeouts_can_arm(
    counts: tuple[int, int], expected: set[str]
) -> None:
    game = new_game(clock=Clock(1, 900, counts))
    assert not any(a.startswith("timeout:") for a in actions(game))
    kickoff(game)
    assert {a for a in actions(game) if a.startswith("timeout:")} == expected


def test_prior_normal_timing_ending_period_keeps_postplay_timeout_without_arming() -> None:
    game = new_game(clock=Clock(2, 20), gain=0)
    kickoff(game)
    snap(game)
    view = game.view()
    assert view.clock_optional
    assert not any(a.startswith("timeout:") for a in actions(game))
    assert "clock:timeout:away" in {c.id for c in view.pending.choices}
    game.decide("clock:timeout:away")
    assert game.view().clock.remaining == 10
    assert game.view().clock.timeouts == (3, 2)


def test_kneel_out_query_counts_an_armed_offensive_timeout() -> None:
    from tests.test_kneel_safety import regulation_game

    game = regulation_game(remaining=90, home_timeouts=3, away_timeouts=0)
    assert game.can_kneel_out_game()
    game.action("timeout:home")
    assert not game.can_kneel_out_game()
    game.action("timeout:home")
    assert game.can_kneel_out_game()


@pytest.mark.parametrize("choice", ["accept:0:previous", "decline"])
def test_armed_timeout_waits_for_the_final_penalty_choice(choice: str) -> None:
    from bowl_bound.models import (
        NormalizedCell,
        PenaltyCode,
        PenaltyData,
        PenaltyTeam,
        Play,
        ResultKind,
    )
    from tests.test_models import provenance

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8),
    )
    game = new_game(plays={Play.EIGHT: foul})
    kickoff(game)
    game.action("timeout:away")
    before = game.view()
    report = snap(game, "8")
    assert report.pending
    pending = game.view()
    assert pending.armed_timeout == "away" and pending.clock == before.clock
    assert pending.timing_log == before.timing_log
    assert not any(a.startswith("timeout:") for a in actions(game))
    game.decide(choice)
    assert game.view().armed_timeout is None
    assert game.view().clock.timeouts == (3, 2)
    assert game.view().timing_log[-1].seconds == 10


def test_postplay_timeout_coexists_and_exhaustion_clears_unavailable_arm() -> None:
    game = new_game(clock=Clock(1, 900, (1, 3)), gain=0)
    kickoff(game)
    snap(game)
    game.action("timeout:home")
    game.decide("clock:timeout:home")
    assert game.view().clock.timeouts == (0, 3)
    assert game.view().armed_timeout is None
    assert "timeout:home" not in actions(game)
    snap(game)
    assert game.view().clock.timeouts == (0, 3)


def test_unsupported_play_keeps_arm_for_the_next_completed_play(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    probe = new_game(gain=0)
    kickoff(probe)
    unsupported = replace(snap(probe), supported=False, unsupported_reason="synthetic unsupported")
    game = new_game(gain=0)
    kickoff(game)
    game.action("timeout:away")
    before = game.view()
    with monkeypatch.context() as pending:
        pending.setattr(game._session, "snap", lambda *args, **kwargs: unsupported)
        assert not snap(game, "8").supported
    assert game.view().armed_timeout == "away"
    assert game.view().clock == before.clock
    snap(game)
    assert game.view().armed_timeout is None and game.view().clock.timeouts == (3, 2)


def saved_after_kickoff(tier: str = "medium") -> SavedGame:
    from dataclasses import replace

    from bowl_bound.save_game import SavedGame
    from tests.synthetic_teams import team_chart, yards
    from tests.test_special_teams import special_chart

    charts = tuple(
        replace(
            team_chart(name, season=2002, offense=0, defense=0),
            special_teams=special_chart(name, kickoff=yards(70)).special_teams,
        )
        for name in ("Home", "Away")
    )
    saved = SavedGame.new(
        *charts,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        mode="regulation",
        difficulty=tier,
    )
    saved.decide("toss:receive")
    saved.kick("kickoff")
    saved.decide("kick:touchback")
    return saved


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_arm_save_load_and_coached_owner_controls(side: str, tier: str) -> None:
    from bowl_bound.save_game import dumps_game, loads_game
    from tests.test_cli import saved_facts

    saved = saved_after_kickoff(tier)
    before = saved.view()
    saved.coach_execute(side, "action", f"timeout:{side}")
    armed = saved.view()
    assert armed.clock == before.clock and armed.log == before.log
    other = "away" if side == "home" else "home"
    with pytest.raises(InvalidDecisionError):
        saved.coach_execute(side, "action", f"timeout:{other}")
    assert saved.view() == armed
    restored = loads_game(
        dumps_game(saved), lambda key: saved._charts["home" if key.endswith("home") else "away"]
    )
    assert restored.view() == armed
    assert saved_facts(restored) == saved_facts(saved)
    role = saved.coach_view(side)[1].human_role
    call = "1" if role == "offense" else "A"
    report, view, _ = saved.coach_step(side, call)
    assert restored.coach_step(side, call)[0] == report
    assert restored.view() == view
    for _ in range(4):
        if not report.pending:
            break
        assert view.armed_timeout == side and view.clock == armed.clock
        resumed = loads_game(
            dumps_game(saved), lambda key: saved._charts["home" if key.endswith("home") else "away"]
        )
        assert resumed.view() == view
        assert saved.coach_view(side)[1].automatic
        report, view, _ = saved.coach_step(side)
        assert restored.coach_step(side)[0] == report
        assert restored.view() == resumed.coach_step(side)[1] == view
    assert not report.pending
    assert view.armed_timeout is None
    assert view.clock.timeouts == ((2, 3) if side == "home" else (3, 2))
    assert saved_after_kickoff(tier).view().armed_timeout is None


@pytest.mark.parametrize("side", ["home", "away"])
def test_cli_timeout_key_arms_then_the_play_consumes_it(side: str) -> None:
    import io

    from bowl_bound.cli import TerminalGame

    saved = saved_after_kickoff()
    output = io.StringIO()
    cli = TerminalGame(
        saved,
        lambda key: saved._charts["home" if key.endswith("home") else "away"],
        human_side=side,
        output=output,
    )
    before = saved.view()
    assert cli.command("T")
    armed = saved.view()
    assert armed.armed_timeout == side
    assert armed.clock == before.clock
    cli.display()
    assert armed.armed_timeout_label in output.getvalue()
    role = cli.public_view()[1].human_role
    assert cli.command("1" if role == "offense" else "A")
    assert saved.view().armed_timeout is None
    assert saved.view().clock.timeouts == ((2, 3) if side == "home" else (3, 2))


@pytest.mark.parametrize("side", ["home", "away"])
def test_api_armed_timeout_is_side_owned_and_survives_load(tmp_path: Path, side: str) -> None:
    from fastapi.testclient import TestClient

    from backend.app import create_app
    from bowl_bound.save_game import dumps_game
    from tests.synthetic_teams import write_team

    saved = saved_after_kickoff()
    root = tmp_path / "seasons"
    for chart in saved._charts.values():
        write_team(root, chart)
    client = TestClient(create_app(root))
    loaded = client.post(
        f"/api/games/load?human_side={side}",
        content=dumps_game(saved),
        headers={"content-type": "application/json"},
    ).json()
    key = loaded["game_id"]
    armed = client.post(
        f"/api/games/{key}/action?human_side={side}", json={"action": f"timeout:{side}"}
    )
    assert armed.status_code == 200, armed.text
    data = armed.json()
    assert data["report"] is None and data["view"]["armed_timeout"] == side
    assert data["view"]["clock"] == loaded["view"]["clock"]
    other = "away" if side == "home" else "home"
    denied = client.post(
        f"/api/games/{key}/action?human_side={side}", json={"action": f"timeout:{other}"}
    )
    assert denied.status_code == 422
    assert client.get(f"/api/games/{key}?human_side={side}").json()["view"] == data["view"]
    text = client.get(f"/api/games/{key}/save").text
    restored = client.post(
        f"/api/games/load?human_side={side}",
        content=text,
        headers={"content-type": "application/json"},
    ).json()
    assert restored["view"] == data["view"]
    role = data["turn"]["human_role"]
    played = client.post(
        f"/api/games/{key}/coach",
        json={
            "human_side": side,
            "human_call": "1" if role == "offense" else "A",
            "expected_revision": data["revision"],
        },
    )
    assert played.status_code == 200, played.text
    after = played.json()["view"]
    assert after["armed_timeout"] is None
    assert after["clock"]["remaining"] == loaded["view"]["clock"]["remaining"] - 10
    assert after["timing_log"][-1]["method"] == f"timeout:{side}"


def test_save_rejects_forged_armed_side_digest() -> None:
    import json

    from bowl_bound.save_game import SaveFormatError, _digest, dumps_game, loads_game

    saved = saved_after_kickoff()
    unarmed = json.loads(dumps_game(saved))
    saved.coach_execute("home", "action", "timeout:home")
    armed = json.loads(dumps_game(saved))
    armed["state_digest"] = unarmed["state_digest"]
    armed["integrity"] = _digest({k: v for k, v in armed.items() if k != "integrity"})
    with pytest.raises(SaveFormatError):
        loads_game(
            json.dumps(armed), lambda key: saved._charts["home" if key.endswith("home") else "away"]
        )


def test_prior_delay_ending_a_quarter_clears_arm_without_spending_it() -> None:
    game = new_game(clock=Clock(1, 40), gain=0)
    kickoff(game)
    snap(game)
    game.action("timeout:home")
    game.decide("clock:delay")
    view = game.view()
    assert view.clock.quarter == 2 and view.clock.remaining == 900
    assert view.clock.timeouts == (3, 3)
    assert view.armed_timeout is None


def test_no_time_elected_safety_clears_an_unused_arm_without_spending_it() -> None:
    game = new_game(gain=0)
    kickoff(game)
    game.action("timeout:away")
    before = game.view()
    report = game.action("elect_safety")
    view = game.view()
    assert report.timing.no_elapsed_time
    assert view.armed_timeout is None
    assert view.clock == before.clock
    assert view.timing_log[-1].seconds == 0
    assert view.timing_log[-1].method == "standard"


def test_cancel_arm_before_choosing_combined_next_spike_timing() -> None:
    game = new_game(gain=0)
    kickoff(game)
    snap(game)
    assert "clock:spike" in {c.id for c in game.view().pending.choices}
    game.action("timeout:home")
    armed = game.view()
    assert "clock:spike" not in {c.id for c in armed.pending.choices}
    with pytest.raises(InvalidDecisionError):
        game.decide("clock:spike")
    assert game.view() == armed
    game.action("timeout:home")
    assert "clock:spike" in {c.id for c in game.view().pending.choices}
