"""RULE-044: an AT-style request spends only an engine-eligible timeout."""

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.session import InvalidDecisionError
from bowl_bound.timing import Clock
from tests.test_models import provenance
from tests.test_regulation import kickoff, new_game, snap


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("gain", [2, 15])
def test_conditional_timeout_shortens_eligible_play_once_at_period_boundary(
    quarter: int, gain: int
) -> None:
    game = new_game(clock=Clock(quarter, 11), gain=gain)
    kickoff(game)
    before = game.view()
    game.action("timeout_after:away")
    selected = game.view()
    assert selected.conditional_timeout and selected.armed_timeout == "away"
    assert selected.clock == before.clock and selected.log == before.log
    assert "if eligible" in selected.armed_timeout_label
    snap(game)
    view = game.view()
    assert view.clock.quarter == quarter and view.clock.remaining == 1
    assert view.clock.timeouts == (3, 2)
    assert view.armed_timeout is None and not view.conditional_timeout
    assert view.timing_log[-1].method == "timeout:away"
    assert view.timing_label(view.log[-1].number) == (
        "Away timeout used; this play took 10 seconds."
    )


@pytest.mark.parametrize("kind", ["incomplete", "touchdown", "safety", "turnover_on_downs"])
def test_natural_ten_second_play_does_not_spend_conditional_timeout(kind: str) -> None:
    gain = 100 if kind == "touchdown" else -100 if kind == "safety" else 0
    plays = (
        {Play.EIGHT: NormalizedCell(ResultKind.INCOMPLETE, provenance())}
        if kind == "incomplete"
        else None
    )
    game = new_game(gain=gain, plays=plays)
    kickoff(game)
    if kind == "turnover_on_downs":
        for _ in range(3):
            snap(game)
            game.decide("clock:runoff")
    before = game.view()
    game.action("timeout_after:home")
    report = snap(game, "8" if kind == "incomplete" else "1")
    view = game.view()
    assert not report.pending
    assert view.clock.remaining == before.clock.remaining - 10
    assert view.clock.timeouts == before.clock.timeouts
    assert view.armed_timeout is None and not view.conditional_timeout
    assert view.timing_log[-1].method == "standard"
    assert view.timing_label(report.number) is None


def test_conditional_cancel_invalid_and_other_side_preserve_intent() -> None:
    game = new_game(gain=2)
    kickoff(game)
    before = game.view()
    game.action("timeout_after:home")
    selected = game.view()
    for invalid in ["timeout_after:away", "timeout:away", "bad"]:
        with pytest.raises(InvalidDecisionError):
            game.action(invalid)
        assert game.view() == selected
    with pytest.raises((InvalidDecisionError, ValueError)):
        game.snap("bad", "A")
    assert game.view() == selected
    game.action("timeout_after:home")
    assert game.view() == before


def test_conditional_no_time_safety_does_not_spend_or_persist() -> None:
    game = new_game(gain=0)
    kickoff(game)
    before = game.view()
    game.action("timeout_after:away")
    report = game.action("elect_safety")
    assert report.timing.no_elapsed_time
    view = game.view()
    assert view.clock == before.clock
    assert view.armed_timeout is None and not view.conditional_timeout


def test_conditional_pending_cpu_razzle_choice_uses_same_play_only() -> None:
    game = new_game(gain=2)
    kickoff(game)
    game.action("timeout_after:away")
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 3, 5),
            OffensiveRoll(1, 2, 3),
            DefensiveRoll(1, 0),
        ]
    )
    report = game.snap("RZDZ", "A", dice=dice)
    assert report.pending
    pending = game.view()
    assert pending.conditional_timeout and pending.armed_timeout == "away"
    assert pending.clock.remaining == 900 and pending.clock.timeouts == (3, 3)
    assert pending.timing_label(report.number) is None
    report = game.decide("razzle:1:15")
    assert not report.pending
    assert game.view().clock.remaining == 890
    assert game.view().clock.timeouts == (3, 2)
    assert not game.view().conditional_timeout


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_conditional_saved_coached_controls_are_owned_and_replayable(side: str, tier: str) -> None:
    from bowl_bound.coaching_session import observe_game
    from bowl_bound.save_game import dumps_game, loads_game
    from tests.test_armed_timeouts import saved_after_kickoff

    saved = saved_after_kickoff(tier)
    before = saved.view()
    dice_before = (len(saved._tape.rolls), saved._tape.position)
    saved.coach_execute(side, "action", f"timeout_after:{side}")
    selected = saved.view()
    assert selected.clock == before.clock and selected.log == before.log
    assert (len(saved._tape.rolls), saved._tape.position) == dice_before
    other = "home" if side == "away" else "away"
    with pytest.raises(InvalidDecisionError):
        saved.coach_execute(side, "action", f"timeout_after:{other}")
    assert saved.view() == selected
    assert all(
        not key.startswith("timeout_after:") for key in observe_game(selected, other).game_actions
    )
    restored = loads_game(
        dumps_game(saved), lambda key: saved._charts["home" if key.endswith("home") else "away"]
    )
    assert restored.view() == selected
    role = saved.coach_view(side)[1].human_role
    call = "1" if role == "offense" else "A"
    report, view, _ = saved.coach_step(side, call)
    assert restored.coach_step(side, call)[0] == report
    while report.pending:
        assert view.conditional_timeout and view.armed_timeout == side
        report, view, _ = saved.coach_step(side)
        assert restored.coach_step(side)[0] == report
    assert restored.view() == view
    assert view.clock.timeouts == ((2, 3) if side == "home" else (3, 2))
    assert not view.conditional_timeout and view.armed_timeout is None


def test_conditional_intent_is_semantic_but_labels_and_false_default_are_not() -> None:
    import json

    from bowl_bound.save_game import SaveFormatError, _digest, dumps_game, loads_game
    from tests.test_armed_timeouts import saved_after_kickoff

    saved = saved_after_kickoff()
    saved.action("timeout:home")
    legacy = json.loads(dumps_game(saved))
    saved.action("timeout:home")
    saved.action("timeout_after:home")
    conditional = json.loads(dumps_game(saved))
    assert conditional["state_digest"] != legacy["state_digest"]
    conditional["state_digest"] = legacy["state_digest"]
    conditional["integrity"] = _digest({k: v for k, v in conditional.items() if k != "integrity"})
    with pytest.raises(SaveFormatError):
        loads_game(
            json.dumps(conditional),
            lambda key: saved._charts["home" if key.endswith("home") else "away"],
        )


def test_conditional_is_unavailable_for_tries_and_prior_period_expiration() -> None:
    game = new_game(gain=100)
    kickoff(game)
    snap(game)
    before = game.view()
    with pytest.raises(InvalidDecisionError):
        game.action("timeout_after:home")
    assert game.view() == before
    game = new_game(clock=Clock(2, 20), gain=2)
    kickoff(game)
    snap(game)
    before = game.view()
    assert not any(action.key.startswith("timeout_after:") for action in before.game_actions)
    with pytest.raises(InvalidDecisionError):
        game.action("timeout_after:away")
    assert game.view() == before


def test_unsupported_play_preserves_conditional_for_actual_supported_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    probe = new_game(gain=2)
    kickoff(probe)
    unsupported = replace(snap(probe), supported=False, unsupported_reason="synthetic unsupported")
    game = new_game(gain=2)
    kickoff(game)
    game.action("timeout_after:away")
    before = game.view()
    with monkeypatch.context() as patch:
        patch.setattr(game._session, "snap", lambda *args, **kwargs: unsupported)
        assert not snap(game).supported
    assert game.view().clock == before.clock
    assert game.view().conditional_timeout
    snap(game)
    assert not game.view().conditional_timeout
    assert game.view().clock.timeouts == (3, 2)


def test_cli_menu_keeps_conditional_web_intent_out_of_special_plays() -> None:
    import io

    from bowl_bound.cli import TerminalGame
    from tests.test_armed_timeouts import saved_after_kickoff

    saved = saved_after_kickoff()
    output = io.StringIO()
    cli = TerminalGame(
        saved,
        lambda key: saved._charts["home" if key.endswith("home") else "away"],
        human_side="home",
        output=output,
    )
    cli.display()
    assert "timeout_after:" not in output.getvalue()
    assert cli._shortcuts(*cli.public_view())["T"] == ("action", "timeout:home")
    assert cli.command("T")
    assert not saved.view().conditional_timeout  # Historical CLI binding stays unchanged.
