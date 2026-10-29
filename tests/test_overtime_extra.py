"""Additional synthetic overtime scoring, recovery, and profile regressions."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import Possession
from bowl_bound.overtime import GameType, OvertimeState, overtime_profile
from bowl_bound.regulation import RegulationGame
from tests.synthetic_teams import team_chart
from tests.test_overtime import miss_series, overtime_game, start_overtime
from tests.test_regulation import snap


def test_paired_try_win_waits_for_both_attempts_and_reconciles_ledger() -> None:
    game = overtime_game(2021)
    start_overtime(game)
    for _ in range(4):
        miss_series(game)
    snap(game)
    assert not game.view().finished and game.view().overtime.series_number == 2
    assert game.view().score.home == 2
    snap(game, "3")
    final = game.view()
    assert final.finished and final.phase == "final" and "overtime" in final.status
    assert final.score.home == sum(e.points for e in final.scoring if e.team == "Home")
    assert final.score.away == sum(e.points for e in final.scoring if e.team == "Away")
    assert not final.actions.offense and not final.actions.special and not final.game_actions
    assert len(final.log) > len(final.timing_log)


def test_defensive_safety_finishes_normal_series_without_a_free_kick() -> None:
    game = overtime_game()
    start_overtime(game)
    snap(game, "6")
    assert game.view().finished and game.view().score.away == 2
    assert not game.view().actions.special


@pytest.mark.parametrize("recovery", [OffensiveRoll(1, 0, 0), OffensiveRoll(3, 0, 0)])
def test_fumble_retention_versus_loss_ends_only_the_lost_series(recovery: OffensiveRoll) -> None:
    game = overtime_game()
    start_overtime(game)
    report = game.snap(
        "5",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 1),
                recovery,
            ]
        ),
    )
    assert not report.pending
    view = game.view()
    retained = recovery.total == 10
    assert view.overtime.series_number == (1 if retained else 2)
    assert view.state.possession == ("home" if retained else "away")
    assert view.state.yards_to_goal == 25
    assert view.state.down == (2 if retained else 1)


def test_equal_field_goals_advance_round_instead_of_finishing() -> None:
    game = overtime_game()
    start_overtime(game)
    for _ in range(2):
        game.kick("field_goal", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert not game.view().finished and game.view().overtime.round_number == 2
    assert game.view().score.home == game.view().score.away == 3


def test_profile_is_frozen_from_home_not_newer_away_season() -> None:
    game = RegulationGame.new(
        team_chart("Home", season=1995), team_chart("Away", season=2021), seed=1
    )
    assert game.view().rules_season == 1995
    assert not game._ot_profile.enabled
    game = RegulationGame.new(
        team_chart("Home", season=2021), team_chart("Away", season=1995), seed=1
    )
    assert game.view().rules_season == 2021
    assert game._ot_profile == overtime_profile(2021, GameType.REGULAR)


@pytest.mark.parametrize("season", [1939, 2024, None, True])
def test_unsupported_profile_has_no_fallback(season: int) -> None:
    with pytest.raises(ValueError, match="supported home season"):
        overtime_profile(season, GameType.REGULAR)


def test_overtime_timeout_bookkeeping_is_immutable_and_does_not_carry_over() -> None:
    initial = OvertimeState(Possession.HOME)
    spent = initial.timeout(Possession.HOME)
    assert initial.timeouts == (1, 1) and spent.timeouts == (0, 1)
    with pytest.raises(ValueError, match="no overtime timeout"):
        spent.timeout(Possession.HOME)
    assert spent.next_series().timeouts == (0, 1)
    assert spent.next_series().next_series().timeouts == (1, 1)


def test_invalid_game_type_fails_at_creation() -> None:
    with pytest.raises(ValueError):
        RegulationGame.new(
            team_chart("Home", season=2002),
            replace(team_chart("Away"), season=2002),
            seed=1,
            game_type="bowl",
        )


@pytest.mark.parametrize("paired", [False, True])
def test_successful_try_carry_penalty_relocates_next_series_not_a_nonexistent_kickoff(
    paired: bool,
) -> None:
    game = overtime_game(2021 if paired else 2002)
    start_overtime(game)
    if paired:
        for _ in range(4):
            miss_series(game)
    else:
        snap(game)
        game.decide("conversion:two")
    game.snap(
        "4",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 1),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    choice = next(c for c in game.view().pending.choices if c.id == "accept:0:kickoff")
    assert "next overtime series" in choice.label
    assert "kickoff" not in choice.label
    report = game.decide(choice.id)
    assert "next overtime series" in report.description
    view = game.view()
    assert view.overtime.series_number == 2 and not view.finished
    assert view.state.possession == "away"
    assert view.state.yards_to_goal == (7 if paired else 30)
    assert not view.kickoff_penalties
