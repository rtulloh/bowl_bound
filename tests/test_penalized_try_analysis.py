"""AI-039: evaluate engine-enforced try positions without moving live state."""

from dataclasses import replace

import pytest

from bowl_bound.coaching_evaluation import evaluate_action
from bowl_bound.coaching_session import observe_game
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PlaySession, SessionPhase
from tests.synthetic_teams import team_chart
from tests.test_models import provenance


@pytest.mark.parametrize("side", [Possession.HOME, Possession.AWAY])
@pytest.mark.parametrize("spot", [1, 3, 7, 12, 17])
def test_analysis_accepts_current_first_and_goal_try_spot(side: Possession, spot: int) -> None:
    field = FieldState(side, spot, 1, spot)
    session = PlaySession.for_analysis(
        team_chart("Home"), team_chart("Away"), field, phase=SessionPhase.TWO_POINT_TRY
    )
    state = session.view().state
    assert (state.possession, state.yards_to_goal, state.down, state.yards_to_go) == (
        side.value,
        spot,
        1,
        spot,
    )
    assert session.view().phase == "two_point_try"


@pytest.mark.parametrize("side", [Possession.HOME, Possession.AWAY])
@pytest.mark.parametrize("offensive", [True, False])
def test_hard_coaching_analyzes_engine_enforced_try_penalty_for_both_roles(
    side: Possession, offensive: bool
) -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(
            PenaltyTeam.OFFENSE if offensive else PenaltyTeam.DEFENSE,
            PenaltyCode.FIXED if offensive else PenaltyCode.PI,
            5 if offensive else 1,
        ),
    )
    charts = [team_chart(name, offense=20, defense=0) for name in ("Home", "Away")]
    charts = [
        replace(
            chart,
            offense=tuple(
                replace(row, cell=foul) if row.play is Play.EIGHT and row.roll == 10 else row
                for row in chart.offense
            ),
        )
        for chart in charts
    ]
    session = PlaySession.for_analysis(*charts, FieldState(side, 2, 1, 2))

    def dice() -> ScriptedDice:
        return ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])

    session.snap("1", "A", dice=dice())
    session.decide("conversion:two")
    session.snap("8", "A", dice=dice())
    session.decide("accept:0:previous")
    before = session.view()
    assert before.phase == "two_point_try"
    assert (before.state.down, before.state.yards_to_goal, before.state.yards_to_go) == (
        1,
        7 if offensive else 1,
        7 if offensive else 1,
    )
    coach = DifficultyCoach(31, *charts, "hard", version=15)
    for role, observer in (("offense", side), ("defense", side.other)):
        obs = replace(observe_game(before, observer.value), offense=("1",), defense=("A",))
        estimates = coach.estimates(obs, role)
        assert estimates and all(estimate.complete for estimate in estimates)
        assert all(
            estimate.mean_points == (2 if role == "offense" else -2) for estimate in estimates
        )
        assert session.view() == before
    session.snap("1", "A", dice=dice())
    assert session.view().finished
    assert (session.view().score.home, session.view().score.away) == (
        (8, 0) if side is Possession.HOME else (0, 8)
    )


def test_bounded_try_penalty_analysis_retains_explicit_failure_and_legal_fallback() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 1),
    )
    home, away = team_chart("Home", plays={Play.EIGHT: foul}), team_chart("Away", defense=0)
    session = PlaySession.for_analysis(
        home, away, FieldState(Possession.HOME, 2, 1, 2), phase=SessionPhase.TWO_POINT_TRY
    )
    before = session.view()
    obs = replace(observe_game(before, "home"), offense=("8",), defense=("A",))
    estimate = evaluate_action(
        home, away, obs, "8", role="offense", samples=8, utility_policy="hard-v1"
    )
    assert estimate.failed_samples == 8 and not estimate.complete
    assert estimate.mean_points is None and estimate.mean_utility is None
    coach = DifficultyCoach(31, home, away, "hard", version=15)
    assert coach.offense(obs) == "8" and coach.analysis_fallback
    assert session.view() == before


def test_unchanged_two_yard_try_retains_analysis_and_strict_save_replay() -> None:
    home, away = team_chart("Home", offense=2, defense=0), team_chart("Away", defense=0)
    game = SavedGame.new(
        home,
        away,
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        start_yards_to_goal=2,
        difficulty="hard",
    )
    game.snap("1", "A")
    game.decide("conversion:two")
    before = game.view()
    obs = replace(observe_game(before, "home"), offense=("1",), defense=("A",))
    result = evaluate_action(
        home, away, obs, "1", role="offense", samples=8, utility_policy="hard-v1"
    )
    assert (result.complete, result.mean_points, result.mean_utility) == (True, 2, 2)
    assert result == evaluate_action(
        home, away, obs, "1", role="offense", samples=8, utility_policy="hard-v1"
    )
    restored = loads_game(dumps_game(game), {"2026/home": home, "2026/away": away}.__getitem__)
    assert restored.view() == before
    game.coach_step("home", "1")
    restored.coach_step("home", "1")
    assert restored.view() == game.view()
    assert (
        loads_game(dumps_game(game), {"2026/home": home, "2026/away": away}.__getitem__).view()
        == game.view()
    )
