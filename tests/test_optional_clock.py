"""Default clock continuation is an engine operation, not a UI timing shortcut."""

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.session import InvalidDecisionError
from bowl_bound.timing import Clock
from tests.test_regulation import kickoff, new_game, snap


def test_next_snap_commits_normal_runoff_once_without_a_separate_choice() -> None:
    game = new_game()
    kickoff(game)
    snap(game)
    view = game.view()
    assert view.clock_optional and view.actions.offense and view.actions.defense
    assert [c.label for c in view.clock_modifiers][0] == "None"
    snap(game)
    assert game.view().clock.remaining == 870
    assert len(game.view().log) == 3
    assert len(game.view().timing_log) == 2
    assert game.view().timing_log[-1].play_number == 2


@pytest.mark.parametrize("action", ["punt", "field_goal", "kneel"])
def test_other_next_plays_also_commit_prior_runoff(action: str) -> None:
    game = new_game()
    kickoff(game)
    snap(game)
    if action == "kneel":
        game.action(action)
    else:
        game.kick(action, dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert game.view().clock.remaining <= 870
    assert game.view().timing_log[1].seconds == 30


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
def test_expiring_runoff_never_executes_a_requested_next_snap(quarter: int) -> None:
    game = new_game(clock=Clock(quarter, 20))
    kickoff(game)
    report = snap(game)
    assert not game.view().clock_optional and not game.view().actions.offense
    result = game.snap("1", "A", dice=ScriptedDice([]))
    assert result.outcome == "period_boundary" and result.number == report.number
    assert result.trace == () and len(game.view().log) == 2
    assert game.view().log[-1] == report
    assert game.view().clock.remaining == (900 if quarter in {1, 3} else 0)


def test_bad_next_play_does_not_commit_pending_time() -> None:
    game = new_game()
    kickoff(game)
    snap(game)
    before = game.view()
    with pytest.raises(InvalidDecisionError):
        game.snap("1", "Z")
    assert game.view() == before
    with pytest.raises(InvalidDecisionError):
        game.kick("kickoff")
    assert game.view() == before
    with pytest.raises(InvalidDecisionError):
        game.action("sneak")
    assert game.view() == before


def test_hail_mary_eligibility_uses_clock_after_default_runoff() -> None:
    game = new_game(clock=Clock(2, 45))
    kickoff(game)
    snap(game)
    assert "hail_mary" in {a.key for a in game.view().game_actions}
    game.action("hail_mary", dice=ScriptedDice([OffensiveRoll(3, 0, 0)]))
    assert game.view().clock.remaining == 5
    assert game.view().log[-1].called_play == "Hail Mary"


def test_implicit_and_explicit_runoff_produce_identical_engine_results() -> None:
    implicit, explicit = new_game(), new_game()
    for game in (implicit, explicit):
        kickoff(game)
        snap(game)
    explicit.decide("clock:runoff")
    assert snap(implicit) == snap(explicit)
    assert implicit.view() == explicit.view()


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
def test_expiring_runoff_before_a_kick_uses_no_new_dice(quarter: int) -> None:
    game = new_game(clock=Clock(quarter, 20))
    kickoff(game)
    report = snap(game)
    result = game.kick("punt", dice=ScriptedDice([]))
    assert result.outcome == "period_boundary" and result.number == report.number
    assert result.trace == () and game.view().log[-1] == report
    assert len(game.view().log) == 2


def test_optional_modifiers_only_include_available_timeouts() -> None:
    game = new_game(clock=Clock(1, 900, (0, 1)))
    kickoff(game)
    snap(game)
    choices = {c.id: c.label for c in game.view().clock_modifiers}
    assert "clock:timeout:home" not in choices
    assert choices["clock:timeout:away"] == "Away timeout (1)"
    game.decide("clock:timeout:away")
    snap(game)
    assert not any(c.id.startswith("clock:timeout:") for c in game.view().clock_modifiers)
