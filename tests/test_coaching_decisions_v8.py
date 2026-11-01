"""AI-016: decisions use engine projections for prepared penalty choices."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_session import observe_game, plan_turn
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
from bowl_bound.save_game import _view_digest
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_models import provenance


def _penalty_chart(
    name: str, penalty_team: PenaltyTeam, result: NormalizedCell, penalty_yards: int
):
    chart = team_chart(name, offense=0, defense=0)
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(penalty_team, PenaltyCode.FIXED, yards=penalty_yards),
    )
    return replace(
        chart,
        offense=tuple(
            replace(record, cell=penalty)
            if record.play is Play.ONE and record.roll == 10
            else replace(record, cell=result)
            if record.play is Play.ONE and record.roll == 20
            else record
            for record in chart.offense
        ),
    )


def _pending_penalty(
    offense_side: str,
    penalty_team: PenaltyTeam,
    result: NormalizedCell,
    penalty_yards: int = 5,
):
    original_home, original_away = default_teams()
    home = team_chart(original_home.name, offense=0, defense=0)
    away = team_chart(original_away.name, offense=0, defense=0)
    if offense_side == "home":
        home = _penalty_chart(home.name, penalty_team, result, penalty_yards)
    else:
        away = _penalty_chart(away.name, penalty_team, result, penalty_yards)
    game = PlaySession.new(home, away, seed=31)
    game._field = FieldState(Possession[offense_side.upper()], 65, 4, 2)
    game.snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )
    view = game.view()
    assert view.pending is not None
    return game, view


@pytest.mark.parametrize("offense_side", ["home", "away"])
@pytest.mark.parametrize("mode", ["baseline", "easy", "medium", "hard"])
def test_v8_defense_declines_offensive_foul_to_take_fourth_down_turnover(
    offense_side: str, mode: str
) -> None:
    game, view = _pending_penalty(
        offense_side,
        PenaltyTeam.OFFENSE,
        yards(1),
    )
    defense_side = "away" if offense_side == "home" else "home"
    observation = observe_game(view, defense_side)
    coach = (
        BaselineCoach(31, version=8)
        if mode == "baseline"
        else DifficultyCoach(31, *default_teams(), mode, version=8)
    )

    plan = plan_turn(view, offense_side, coach)

    assert plan.turn.automatic
    assert plan.arguments == ("decline",)
    decline = next(item for item in view.pending.decision_outcomes if item.choice_id == "decline")
    accepted = next(
        item for item in view.pending.decision_outcomes if item.choice_id == "accept:0:previous"
    )
    assert decline.possession == defense_side
    assert accepted.possession == offense_side
    assert observation.decision_outcomes == view.pending.decision_outcomes
    game.decide(plan.arguments[0])
    assert game.view().state is not None
    assert game.view().state.possession == defense_side


@pytest.mark.parametrize("offense_side", ["home", "away"])
@pytest.mark.parametrize("mode", ["baseline", "easy", "medium", "hard"])
def test_v8_offense_declines_defensive_foul_to_keep_engine_touchdown(
    offense_side: str, mode: str
) -> None:
    touchdown = NormalizedCell(ResultKind.TOUCHDOWN, provenance())
    _, view = _pending_penalty(offense_side, PenaltyTeam.DEFENSE, touchdown)
    defense_side = "away" if offense_side == "home" else "home"
    coach = (
        BaselineCoach(31, version=8)
        if mode == "baseline"
        else DifficultyCoach(31, *default_teams(), mode, version=8)
    )

    plan = plan_turn(view, defense_side, coach)

    assert plan.turn.automatic
    assert plan.arguments == ("decline",)
    declined = next(item for item in view.pending.decision_outcomes if item.choice_id == "decline")
    assert declined.scoring_side == offense_side


def test_v8_prefers_the_better_legal_enforcement_spot() -> None:
    game, view = _pending_penalty(
        "home",
        PenaltyTeam.DEFENSE,
        yards(1),
        penalty_yards=15,
    )
    assert view.pending is not None
    observation = observe_game(view, "home")

    choice = BaselineCoach(31, version=8).decision(observation)

    assert choice == "accept:0:end"
    assert game.view().pending == view.pending


def test_derived_decision_outcomes_do_not_change_legacy_save_digest() -> None:
    _, view = _pending_penalty("home", PenaltyTeam.OFFENSE, yards(1))
    assert view.pending is not None
    without_projection = replace(view, pending=replace(view.pending, decision_outcomes=()))

    assert view.pending.decision_outcomes
    assert _view_digest(view) == _view_digest(without_projection)
