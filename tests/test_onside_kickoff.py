"""Basic Bowl Bound onside kickoff mechanics and legal action flow."""

from itertools import product

import pytest

from bowl_bound.coaching import BaselineCoach, CoachObservation
from bowl_bound.dice import (
    BLACK_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import InvalidDecisionError, PlaySession
from bowl_bound.special_teams import SpecialTeamsOutcome, SpecialTeamsPlay
from bowl_bound.statistics import PlayStatistics
from tests.synthetic_teams import team_chart


def roll_for(total: int) -> OffensiveRoll:
    """Create a synthetic physical-face roll for an offensive total."""
    black, remainder = divmod(total, 10)
    return OffensiveRoll(black, 0, remainder)


def test_onside_kickoff_uses_inclusive_recovery_range_and_fixed_twelve_yards() -> None:
    home = team_chart("Home", season=2007)
    away = team_chart("Away", season=2007)

    for total, recovery in (
        (12, Possession.AWAY),
        (13, Possession.HOME),
        (20, Possession.HOME),
        (21, Possession.AWAY),
    ):
        procedure = SpecialTeamsPlay(
            "onside_kickoff",
            FieldState(Possession.HOME, 65, 1, 10),
            home,
            away,
            ScriptedDice([roll_for(total)]),
            home_season=2007,
        )
        result = procedure.begin()

        assert result.outcome is SpecialTeamsOutcome.RECOVERY
        assert result.state is not None and result.state.possession is recovery
        assert result.state.yards_to_goal == (58 if recovery is Possession.HOME else 42)
        assert len(result.trace) == 1
        assert result.trace[0].section == "onside_kickoff"
        assert result.trace[0].roll.total == total and result.trace[0].cell is None


def test_onside_kickoff_recovery_matches_all_216_offensive_dice_combinations() -> None:
    home = team_chart("Home", season=2007)
    away = team_chart("Away", season=2007)
    recoveries = {Possession.HOME: 0, Possession.AWAY: 0}

    for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        procedure = SpecialTeamsPlay(
            "onside_kickoff",
            FieldState(Possession.HOME, 65, 1, 10),
            home,
            away,
            ScriptedDice([OffensiveRoll(*faces)]),
            home_season=2007,
        )
        result = procedure.begin()
        assert result.state is not None
        recoveries[result.state.possession] += 1

    assert recoveries == {Possession.HOME: 31, Possession.AWAY: 185}


def test_onside_kickoff_is_offered_and_regular_cpu_kicker_keeps_normal_default() -> None:
    home = team_chart("Home", season=2007)
    away = team_chart("Away", season=2007)
    game = PlaySession.new(home, away, seed=12)

    assert {action.key for action in game.view().actions.special} >= {
        "kickoff",
        "onside_kickoff",
    }
    coach = BaselineCoach(7, version=9)
    choice = coach.offense(
        CoachObservation(
            side="home",
            possession="home",
            down=0,
            distance=0,
            yards_to_goal=70,
            quarter=1,
            remaining=900,
            score_difference=0,
            play_number=0,
            offense=(),
            defense=(),
            special=("kickoff", "onside_kickoff"),
            game_actions=(),
            choices=(),
        )
    )
    assert choice == "kickoff"

    report = game.kick("onside_kickoff", dice=ScriptedDice([roll_for(13)]))
    assert report.supported and report.outcome == "kick_recovery"
    assert report.state_after is not None and report.state_after.possession == "home"
    assert [entry.section for entry in report.trace] == ["onside_kickoff"]
    assert report.statistics == PlayStatistics()
    assert game.view().score.home == game.view().score.away == 0


def test_onside_kickoff_save_replay_preserves_roll_and_recovery() -> None:
    home = team_chart("Home", season=2007)
    away = team_chart("Away", season=2007)
    game = SavedGame.new(
        home,
        away,
        home_id="2007/home",
        away_id="2007/away",
        seed=12,
        mode="drive",
        dice=ScriptedDice([roll_for(20)]),
    )

    report = game.kick("onside_kickoff")
    restored = loads_game(
        dumps_game(game),
        lambda key: home if key.endswith("home") else away,
    )

    assert report.outcome == "kick_recovery"
    assert restored.view() == game.view()


def test_safety_free_kick_does_not_offer_onside_action() -> None:
    home = team_chart("Home", season=2007)
    away = team_chart("Away", season=2007)
    game = PlaySession.new(home, away, seed=12)
    game.prepare_kickoff(Possession.HOME, safety=True)

    assert [action.key for action in game.view().actions.special] == ["kickoff"]
    with pytest.raises(InvalidDecisionError, match="unavailable"):
        game.kick("onside_kickoff", dice=ScriptedDice([roll_for(13)]))


def test_safety_free_kick_cannot_start_an_onside_procedure() -> None:
    home = team_chart("Home", season=2007)
    away = team_chart("Away", season=2007)

    with pytest.raises(ValueError, match="safety free kick"):
        SpecialTeamsPlay(
            "onside_kickoff",
            FieldState(Possession.HOME, 65, 1, 10),
            home,
            away,
            ScriptedDice([roll_for(13)]),
            home_season=2007,
            safety_free_kick=True,
        )
