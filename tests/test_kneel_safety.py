"""Synthetic engine and policy tests for safe kneel-out decisions."""

from dataclasses import replace

import pytest

from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_session import observe_game
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.overtime import OvertimeState
from bowl_bound.regulation import RegulationGame, RegulationPhase
from bowl_bound.scoring import ScoreKind, ScoreLedger
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation
from tests.test_regulation import new_game


def regulation_game(
    *,
    remaining: int,
    down: int = 1,
    yards_to_goal: int = 65,
    home_timeouts: int = 3,
    away_timeouts: int = 0,
    possession: str = "home",
    home_scored: bool = True,
    away_scored: bool = False,
    quarter: int = 4,
    overtime: bool = False,
) -> RegulationGame:
    """Build a real regulation engine around a fully synthetic public state."""
    game = new_game(clock=Clock(quarter, remaining, (home_timeouts, away_timeouts)))
    game._phase = RegulationPhase.OVERTIME if overtime else RegulationPhase.LIVE
    team = Possession(possession)
    game._session._field = FieldState(team, yards_to_goal, down, min(10, yards_to_goal))
    ledger = ScoreLedger()
    if home_scored:
        ledger = ledger.award(Possession.HOME, ScoreKind.TOUCHDOWN, play_number=1)
    if away_scored:
        ledger = ledger.award(Possession.AWAY, ScoreKind.TOUCHDOWN, play_number=2)
    game._session._ledger = ledger
    if overtime:
        game._overtime = OvertimeState(Possession.HOME)
    return game


@pytest.mark.parametrize(
    "facts,expected",
    [
        ({"remaining": 90}, True),
        ({"remaining": 91}, False),
        ({"remaining": 30, "away_timeouts": 3}, True),
        ({"remaining": 31, "away_timeouts": 3}, False),
        ({"remaining": 10, "down": 3, "away_timeouts": 3}, True),
        ({"remaining": 11, "down": 3, "away_timeouts": 3}, False),
        ({"remaining": 60, "down": 2}, True),
        ({"remaining": 61, "down": 2}, False),
        ({"remaining": 30, "down": 4}, False),
        ({"remaining": 30, "yards_to_goal": 97}, True),
        ({"remaining": 60, "yards_to_goal": 97}, False),
        ({"remaining": 30, "yards_to_goal": 98}, False),
        ({"remaining": 30, "yards_to_goal": 99}, False),
        ({"remaining": 30, "quarter": 3}, False),
        ({"remaining": 0}, False),
        ({"remaining": 30, "overtime": True}, False),
    ],
)
def test_engine_kneel_out_query_accounts_for_timing_downs_timeouts_and_safety(
    facts: dict[str, object], expected: bool
) -> None:
    game = regulation_game(**facts)

    assert game.can_kneel_out_game() is expected
    assert game.view().can_kneel_out_game is expected


@pytest.mark.parametrize(
    "facts",
    [
        {"home_scored": True, "away_scored": True},
        {"home_scored": False, "away_scored": True},
        {"possession": "away", "home_scored": True, "away_scored": False},
    ],
)
def test_engine_kneel_out_query_requires_the_possessing_team_to_lead(
    facts: dict[str, object],
) -> None:
    assert not regulation_game(remaining=30, **facts).can_kneel_out_game()


def test_engine_kneel_out_query_is_symmetric_for_an_away_lead() -> None:
    game = regulation_game(
        remaining=30,
        possession="away",
        home_scored=False,
        away_scored=True,
        home_timeouts=0,
        away_timeouts=3,
    )

    assert game.can_kneel_out_game()


def test_engine_kneel_out_query_uses_clock_after_pending_standard_timing() -> None:
    game = regulation_game(remaining=110)
    game._phase = RegulationPhase.CLOCK
    game._pending_timing_seconds = 30

    assert game.can_kneel_out_game()


def test_engine_kneel_out_query_accounts_for_timeout_before_next_snap() -> None:
    game = regulation_game(remaining=110, away_timeouts=3)
    game._phase = RegulationPhase.CLOCK
    game._pending_timing_seconds = 30

    assert not game.can_kneel_out_game()


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("policy", ["baseline", "chart", "easy", "medium", "hard"])
def test_v2_policies_kneel_only_when_the_engine_confirms_a_safe_runout(
    side: str, policy: str
) -> None:
    home, away = team_chart("Home"), team_chart("Away")
    if policy == "baseline":
        coach = BaselineCoach(31, version=2)
    elif policy == "chart":
        coach = ChartAwareCoach(31, home, away, version=2)
    else:
        coach = DifficultyCoach(31, home, away, policy, version=2)
    obs = observation(
        side=side,
        possession=side,
        quarter=4,
        remaining=30,
        score_difference=7,
        down=3,
        game_actions=("kneel",),
        can_kneel_out_game=False,
    )

    assert coach.offense(obs) != "kneel"
    assert coach.offense(replace(obs, can_kneel_out_game=True)) == "kneel"


def test_legacy_v1_policies_keep_their_existing_kneel_selection() -> None:
    obs = observation(
        quarter=4,
        remaining=30,
        score_difference=7,
        down=3,
        game_actions=("kneel",),
        can_kneel_out_game=False,
    )
    home, away = team_chart("Home"), team_chart("Away")
    legacy_coaches = (
        BaselineCoach(31),
        ChartAwareCoach(31, home, away),
        *(DifficultyCoach(31, home, away, mode) for mode in ("easy", "medium", "hard")),
    )
    assert all(coach.offense(obs) == "kneel" for coach in legacy_coaches)
    assert BaselineCoach(31, version=2).offense(obs) != "kneel"


def test_engine_query_drives_a_real_kneel_through_an_opponent_timeout() -> None:
    game = regulation_game(remaining=10, down=3, away_timeouts=3)
    coach = BaselineCoach(31, version=2)
    view = game.view()
    observation_for_coach = observe_game(view, "home")

    assert observation_for_coach.can_kneel_out_game
    assert coach.offense(observation_for_coach) == "kneel"
    game.action("kneel")
    assert game.view().clock.remaining == 10
    game.decide("clock:timeout:away")

    assert game.view().finished
    assert game.view().clock.remaining == 0
