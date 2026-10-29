"""Regulation orchestration with complete synthetic teams and exact dice."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.regulation import RegulationGame
from bowl_bound.session import InvalidDecisionError, PendingDecisionError, SessionFinishedError
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def new_game(
    *, clock: Clock | None = None, gain: int = 3, plays: dict | None = None, season: int = 2002
) -> RegulationGame:
    charts = []
    for name in ("Home", "Away"):
        base = special_chart(
            name, kickoff=yards(70), kickoff_return=yards(10), punt=yards(40), field_goal=yards(40)
        )
        ordinary = team_chart(name, season=season, offense=gain, defense=0, plays=plays)
        charts.append(replace(ordinary, special_teams=base.special_teams))
    return RegulationGame.new(
        *charts,
        seed=1,
        clock=clock,
        dice=ScriptedDice([OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]),
    )


def kickoff(game: RegulationGame, choice: str = "toss:receive") -> None:
    game.decide(choice)
    game.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    game.decide("kick:touchback")


def snap(game: RegulationGame, play: str = "1"):
    return game.snap(play, "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))


def test_opening_choice_is_not_a_live_scrimmage_and_records_toss_evidence() -> None:
    game = new_game()
    view = game.view()
    assert view.phase == "opening_choice" and view.pending.chooser == "Home"
    assert view.clock.quarter_label == "Q1" and view.clock.label == "15:00"
    assert [r.total for r in view.toss_rolls] == [39, 10]
    assert view.rules_season == 2002
    with pytest.raises(PendingDecisionError):
        snap(game)
    kickoff(game)
    assert game.view().state.possession_name == "Home"
    assert game.view().state.yards_to_goal == 80
    assert game.view().clock.remaining == 900
    assert game.view().opening_kicker == "away"


def test_clock_management_is_pending_and_reductions_cannot_stack() -> None:
    game = new_game()
    kickoff(game)
    snap(game)
    assert game.view().phase == "clock_choice" and game.view().clock.remaining == 900
    assert game.view().clock_optional and game.view().actions.offense
    game.decide("clock:timeout:away")
    assert game.view().clock.remaining == 890 and game.view().clock.timeouts == (3, 2)
    with pytest.raises(PendingDecisionError):
        game.decide("clock:hurry")
    assert game.view().clock.remaining == 890


def test_hurry_reduces_thirty_to_twenty_and_commits_next_snap() -> None:
    game = new_game()
    kickoff(game)
    snap(game)
    game.decide("clock:hurry")
    assert game.view().clock.remaining == 880 and game.view().hurried
    before = game.view()
    with pytest.raises(InvalidDecisionError):
        game.action("spike")
    assert game.view() == before
    snap(game)
    assert not game.view().hurried
    game.decide("clock:runoff")
    assert game.view().clock.remaining == 850


@pytest.mark.parametrize(("gain", "remaining"), [(3, 880), (12, 890)])
def test_spike_adjusts_prior_play_and_consumes_another_down_without_dice(
    gain: int, remaining: int
) -> None:
    game = new_game(gain=gain)
    kickoff(game)
    snap(game)
    before_down = game.view().state.down
    game.decide("clock:spike")
    assert game.view().clock.remaining == remaining
    assert game.view().state.down == before_down + 1
    assert game.view().log[-1].called_play == "Spike" and game.view().log[-1].trace == ()


def test_kneel_loses_two_and_uses_standard_clock_choices() -> None:
    game = new_game()
    kickoff(game)
    report = game.action("kneel")
    assert report.yards == -2 and report.trace == ()
    assert game.view().state.yards_to_goal == 82
    game.decide("clock:runoff")
    assert game.view().clock.remaining == 870


def test_touchdown_requires_try_then_schedules_scoring_teams_kickoff() -> None:
    game = new_game(gain=100)
    kickoff(game)
    snap(game)
    assert game.view().clock.remaining == 890
    assert game.view().pending.chooser == "Home"
    game.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert game.view().phase == "kickoff" and not game.view().finished
    assert game.view().state.possession_name == "Home"
    assert game.view().state.yards_to_goal == 65
    assert [a.key for a in game.view().actions.special] == ["kickoff"]


def test_first_quarter_expiration_is_once_and_preserves_field_and_timeouts() -> None:
    game = new_game(clock=Clock(1, 10, (2, 1)))
    kickoff(game)
    snap(game)
    game.decide("clock:runoff")
    view = game.view()
    assert view.clock.quarter == 2 and view.clock.remaining == 900
    assert view.clock.timeouts == (2, 1) and view.state.down == 2
    with pytest.raises(PendingDecisionError):
        game.decide("clock:runoff")


def test_halftime_gives_the_other_toss_player_a_choice_and_resets_timeouts() -> None:
    game = new_game(clock=Clock(2, 10, (0, 1)))
    kickoff(game)
    snap(game)
    game.decide("clock:runoff")
    assert game.view().phase == "halftime_choice"
    assert game.view().pending.chooser == "Away"
    assert game.view().clock.quarter == 2 and game.view().clock.remaining == 0
    game.decide("half:receive")
    assert game.view().clock.quarter == 3 and game.view().clock.timeouts == (3, 3)
    assert game.view().state.possession_name == "Home"


def test_expiration_waits_for_conversion_then_has_no_spurious_kickoff() -> None:
    game = new_game(clock=Clock(4, 10), gain=100)
    kickoff(game)
    snap(game)
    assert game.view().clock.remaining == 0 and not game.view().finished
    game.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    final = game.view()
    assert final.finished and final.phase == "final"
    assert final.actions.special == () and final.pending is None
    with pytest.raises(SessionFinishedError):
        snap(game)
    with pytest.raises(SessionFinishedError):
        game.decide("clock:timeout:home")
    assert game.view() == final


def test_tied_regulation_offers_overtime_toss_choice() -> None:
    game = new_game(clock=Clock(4, 10))
    kickoff(game)
    snap(game)
    game.decide("clock:runoff")
    assert game.view().phase == "overtime_choice" and not game.view().finished
    assert "overtime" in game.view().status.lower()


def test_defensive_penalty_at_zero_awards_untimed_down_before_expiration() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8),
    )
    game = new_game(clock=Clock(4, 10), plays={Play.EIGHT: foul})
    kickoff(game)
    snap(game, "8")
    assert game.view().clock.remaining == 10
    game.decide("accept:0:previous")
    assert game.view().clock.remaining == 0 and game.view().untimed_down
    assert not game.view().finished
    assert "hail_mary" not in [a.key for a in game.view().game_actions]
    snap(game)
    assert game.view().phase == "overtime_choice" and game.view().clock.remaining == 0
    assert not game.view().untimed_down


@pytest.mark.parametrize(
    ("quarter", "remaining", "available"),
    [(2, 20, True), (4, 1, True), (1, 10, False), (2, 21, False)],
)
def test_hail_mary_eligibility_is_engine_owned(
    quarter: int, remaining: int, available: bool
) -> None:
    game = new_game(clock=Clock(quarter, remaining))
    kickoff(game)
    assert ("hail_mary" in [a.key for a in game.view().game_actions]) is available


def test_complete_regulation_reconciles_ledger_clock_and_immutable_end() -> None:
    game = new_game(gain=12, season=1994)
    kickoff(game)
    for _ in range(1500):
        view = game.view()
        if view.finished:
            break
        if view.pending:
            ids = {c.id for c in view.pending.choices}
            choice = next(
                (
                    key
                    for key in (
                        "clock:runoff",
                        "half:receive",
                        "conversion:kick",
                        "kick:touchback",
                        "kick:fair_catch",
                    )
                    if key in ids
                ),
                None,
            )
            assert choice is not None, ids
            game.decide(choice, dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
        elif view.phase == "kickoff":
            game.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
        else:
            snap(game)
    else:
        pytest.fail("regulation never ended")
    final = game.view()
    assert final.phase == "final" and final.clock.remaining == 0
    assert sum(e.points for e in final.scoring if e.team == "Home") == final.score.home
    assert sum(e.points for e in final.scoring if e.team == "Away") == final.score.away
    for quarter in range(1, 5):
        charges = [c for c in final.timing_log if c.quarter == quarter]
        assert charges[0].before == 900 and charges[-1].after == 0
        assert sum(c.before - c.after for c in charges) == 900
        assert all(
            left.after == right.before for left, right in zip(charges, charges[1:], strict=False)
        )
    assert len(final.log) == len(final.timing_log)
    for operation in (
        lambda: game.kick("punt"),
        lambda: game.action("kneel"),
        lambda: game.decide("clock:runoff"),
    ):
        with pytest.raises(SessionFinishedError):
            operation()
        assert game.view() == final


def test_hail_mary_action_resolves_without_defensive_dice() -> None:
    game = new_game(clock=Clock(2, 20))
    kickoff(game)
    report = game.action(
        "hail_mary", dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)])
    )
    assert report.called_play == "Hail Mary" and report.yards == 35
    assert game.view().phase == "clock_choice"
    game.decide("clock:runoff")
    assert game.view().phase == "halftime_choice"


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
def test_hurry_requires_time_for_the_committed_next_snap(quarter: int) -> None:
    game = new_game(clock=Clock(quarter, 20))
    kickoff(game)
    snap(game)
    assert "clock:hurry" not in {c.id for c in game.view().pending.choices}


def test_zero_second_hurried_false_start_replays_down_without_runoff() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.S)
    )
    game = new_game(plays={Play.TWO: foul})
    kickoff(game)
    snap(game)
    game.decide("clock:hurry")
    report = game.snap(
        "2",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)]),
    )
    assert report.outcome == "pre_snap" and report.timing.no_elapsed_time
    assert game.view().clock.remaining == 880 and game.view().state.down == 2
    assert game.view().state.yards_to_goal == 82 and not game.view().hurried


def test_safety_schedules_conceding_team_free_kick_from_own_twenty() -> None:
    game = new_game(gain=-100)
    kickoff(game)
    snap(game)
    assert game.view().score.away == 2 and game.view().phase == "kickoff"
    assert game.view().state.possession == "home" and game.view().state.yards_to_goal == 80
    assert game.view().clock.remaining == 890


def test_kneel_from_own_two_is_a_safety_without_dice() -> None:
    game = new_game(gain=-18)
    kickoff(game)
    snap(game)
    game.decide("clock:runoff")
    assert game.view().state.yards_to_goal == 98
    report = game.action("kneel")
    assert report.outcome == "safety" and report.trace == ()
    assert game.view().phase == "kickoff" and game.view().score.away == 2


def test_pre_overtime_era_tie_is_final() -> None:
    game = new_game(clock=Clock(4, 10), season=1987)
    kickoff(game)
    snap(game)
    game.decide("clock:runoff")
    assert game.view().finished and game.view().phase == "final"
