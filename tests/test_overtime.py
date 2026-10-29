"""Historical college overtime exercised with synthetic charts and real play resolution."""

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
from bowl_bound.session import InvalidDecisionError, PlayReport, SessionFinishedError
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_regulation import kickoff, snap
from tests.test_special_teams import special_chart


def interception(game: RegulationGame) -> PlayReport:
    return game.snap(
        "9",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 1), OffensiveRoll(1, 0, 0)]),
    )


def overtime_game(
    season: int = 2002,
    *,
    game_type: str = "regular",
    return_yards: int = 0,
    home_gain: int = 30,
    away_gain: int = 30,
) -> RegulationGame:
    charts = []
    for name, gain in (("Home", home_gain), ("Away", away_gain)):
        chart = team_chart(
            name,
            season=season,
            offense=0,
            defense=0,
            plays={
                Play.ONE: yards(gain),
                Play.THREE: NormalizedCell(ResultKind.INCOMPLETE, provenance()),
                Play.FIVE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=0),
                Play.SIX: yards(-100),
                Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=0),
                Play.EIGHT: NormalizedCell(
                    ResultKind.PENALTY,
                    provenance(),
                    penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8),
                ),
            },
        )
        carry_foul = NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
        )
        chart = replace(
            chart,
            offense=tuple(
                replace(row, cell=carry_foul if row.roll == 10 else yards(30))
                if row.play is Play.FOUR
                else row
                for row in chart.offense
            ),
        )
        kick_spot = 40 if season <= 1985 else (30 if 2007 <= season <= 2011 else 35)
        kicks = special_chart(
            name,
            kickoff=yards(100 - kick_spot),
            interception_return=yards(return_yards),
            field_goal=yards(40),
        )
        charts.append(
            replace(
                chart,
                special_teams=kicks.special_teams,
                pat_outcomes=tuple(replace(r, good=True) for r in chart.pat_outcomes),
            )
        )
    game = RegulationGame.new(
        *charts,
        seed=1,
        clock=Clock(4, 10),
        game_type=game_type,
        dice=ScriptedDice([OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]),
    )
    kickoff(game)
    snap(game, "2")
    game.decide("clock:runoff")
    return game


def start_overtime(game: RegulationGame, first: str = "home") -> None:
    view = game.view()
    assert view.phase == "overtime_choice" and not view.finished
    assert view.actions.offense == ()
    winner = "home" if view.pending.chooser == "Home" else "away"
    game.decide("ot:offense" if winner == first else "ot:defense")


def miss_series(game: RegulationGame) -> None:
    for _ in range(4):
        snap(game, "3")


def touchdown_and_try(game: RegulationGame, *, two: bool = False) -> None:
    snap(game)
    game.decide(
        "conversion:two" if two else "conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)])
    )
    if two:
        snap(game)


@pytest.mark.parametrize(
    ("season", "game_type", "enabled"),
    [
        (1940, "postseason", False),
        (1994, "postseason", False),
        (1995, "regular", False),
        (1995, "postseason", True),
        (1996, "regular", True),
        (2023, "regular", True),
    ],
)
def test_historical_tie_boundary(season: int, game_type: str, enabled: bool) -> None:
    game = overtime_game(season, game_type=game_type)
    assert game.view().finished is not enabled
    assert game.view().game_type == game_type
    assert game.view().phase == ("overtime_choice" if enabled else "final")


def test_toss_series_spot_untimed_rounds_alternating_first_and_timeouts() -> None:
    game = overtime_game()
    assert len(game.view().overtime_toss_rolls) >= 2
    start_overtime(game)
    view = game.view()
    assert view.overtime.round_number == 1 and view.overtime.series_number == 1
    assert view.clock.quarter_label == "OT1" and view.clock.label == "Untimed"
    assert view.clock.timeouts == (1, 1)
    assert (view.state.possession, view.state.yards_to_goal, view.state.down) == ("home", 25, 1)
    assert {a.key for a in view.game_actions} == {"timeout:home", "timeout:away", "kneel"}
    game.action("timeout:home")
    assert game.view().clock.timeouts == (0, 1)
    before = game.view()
    with pytest.raises(InvalidDecisionError):
        game.action("timeout:home")
    assert game.view() == before
    charges = view.timing_log
    miss_series(game)
    assert game.view().state.possession == "away"
    assert game.view().state.yards_to_goal == 25
    assert game.view().overtime.series_number == 2
    assert game.view().clock.timeouts == (0, 1)
    miss_series(game)
    assert game.view().overtime.round_number == 2
    assert game.view().state.possession == "away"
    assert game.view().clock.timeouts == (1, 1)
    assert game.view().timing_log == charges
    assert not game.view().clock_optional and not game.view().clock_modifiers


@pytest.mark.parametrize(
    ("season", "mandatory_round", "paired_round"),
    [
        (1995, None, None),
        (1996, None, None),
        (1997, 3, None),
        (2018, 3, None),
        (2019, 3, 5),
        (2020, 3, 5),
        (2021, 2, 3),
        (2023, 2, 3),
    ],
)
def test_era_conversion_and_paired_try_boundaries(
    season: int,
    mandatory_round: int | None,
    paired_round: int | None,
) -> None:
    game = overtime_game(season, game_type="postseason")
    start_overtime(game)
    for period in range(1, 7):
        paired = paired_round is not None and period >= paired_round
        assert game.view().overtime.round_number == period
        assert game.view().overtime.paired_tries is paired
        if paired:
            assert game.view().phase == "two_point_try"
            assert game.view().state.yards_to_goal == 2
            assert not game.view().actions.special and not game.view().game_actions[2:]
            for _ in range(2):
                snap(game, "3")
        else:
            for _ in range(2):
                snap(game)
                mandatory = mandatory_round is not None and period >= mandatory_round
                choices = {c.id for c in game.view().pending.choices if c.enabled}
                assert ("conversion:kick" in choices) is not mandatory
                if mandatory:
                    before = game.view()
                    with pytest.raises(InvalidDecisionError):
                        game.decide("conversion:kick", dice=ScriptedDice([]))
                    assert game.view() == before
                game.decide(
                    "conversion:two" if mandatory else "conversion:kick",
                    dice=ScriptedDice([OffensiveRoll(1, 0, 0)]),
                )
                if mandatory:
                    snap(game)
    assert not game.view().finished


def test_second_team_can_win_with_field_goal_without_kickoff() -> None:
    game = overtime_game()
    start_overtime(game)
    miss_series(game)
    game.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    view = game.view()
    assert view.finished and view.phase == "final" and view.score.away == 3
    assert view.pending is None and not view.actions.special
    for operation in (
        lambda: snap(game),
        lambda: game.kick("punt"),
        lambda: game.action("timeout:home"),
        lambda: game.decide("ot:offense"),
    ):
        with pytest.raises(SessionFinishedError):
            operation()
        assert game.view() == view


def test_first_team_score_does_not_win_before_opponents_series() -> None:
    game = overtime_game()
    start_overtime(game)
    touchdown_and_try(game)
    assert not game.view().finished and game.view().state.possession == "away"
    miss_series(game)
    assert game.view().finished and game.view().score.home == 7


def test_winning_second_touchdown_has_no_unnecessary_conversion() -> None:
    game = overtime_game()
    start_overtime(game)
    game.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    snap(game)
    assert game.view().finished and game.view().score.away == 6
    assert game.view().pending is None
    assert [e.kind for e in game.view().scoring] == ["field_goal", "touchdown"]


def test_interception_return_finishes_before_series_switch_and_defensive_td_ends_game() -> None:
    for return_yards in (0, 100):
        game = overtime_game(return_yards=return_yards)
        start_overtime(game)
        report = interception(game)
        assert report.pending and game.view().overtime.series_number == 1
        report = game.decide("interception:return", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
        assert len(report.trace) == 3
        if return_yards:
            assert game.view().finished and game.view().score.away == 6
            assert game.view().pending is None
        else:
            assert game.view().state.possession == "away"
            assert game.view().state.yards_to_goal == 25


def test_conversion_defensive_return_does_not_erase_opponents_unplayed_series() -> None:
    game = overtime_game(return_yards=100)
    start_overtime(game)
    snap(game)
    game.decide("conversion:two")
    interception(game)
    game.decide("interception:return", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert game.view().score.home == 6 and game.view().score.away == 2
    assert not game.view().finished and game.view().state.possession == "away"
    assert game.view().state.yards_to_goal == 25


def test_paired_defensive_return_still_allows_second_try_and_can_be_tied() -> None:
    game = overtime_game(2021, return_yards=100)
    start_overtime(game)
    for _ in range(4):
        miss_series(game)
    assert game.view().overtime.round_number == 3
    for series in (1, 2):
        assert game.view().overtime.series_number == series
        interception(game)
        game.decide("interception:return", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert not game.view().finished and game.view().overtime.round_number == 4
    assert game.view().score.home == game.view().score.away == 2


def test_defensive_penalty_replays_try_without_advancing_ot_series() -> None:
    game = overtime_game(2021)
    start_overtime(game)
    for _ in range(4):
        miss_series(game)
    snap(game, "8")
    game.decide("accept:0:previous")
    assert game.view().overtime.round_number == 3
    assert game.view().overtime.series_number == 1 and game.view().phase == "two_point_try"
    assert game.view().state.yards_to_goal == 1
    snap(game, "3")
    assert game.view().overtime.series_number == 2


def test_no_clock_adjustments_hail_mary_or_kickoffs_in_overtime() -> None:
    game = overtime_game()
    start_overtime(game)
    before = game.view()
    for choice in ("clock:runoff", "clock:hurry", "clock:spike", "clock:timeout:home"):
        with pytest.raises((InvalidDecisionError, RuntimeError)):
            game.decide(choice)
        assert game.view() == before
    for action in ("hail_mary", "spike"):
        with pytest.raises(InvalidDecisionError):
            game.action(action)
        assert game.view() == before
    with pytest.raises(InvalidDecisionError):
        game.kick("kickoff")
    assert game.view() == before
