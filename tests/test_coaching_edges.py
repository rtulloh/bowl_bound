"""Synthetic forced decisions audit ownership, fairness, and exact observed traces."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_session import plan_turn
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice, roll_view
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_models import provenance
from tests.test_overtime import miss_series, overtime_game, start_overtime, touchdown_and_try
from tests.test_regulation import snap
from tests.test_session_turnovers import return_chart


def test_interception_and_defensive_conversion_belong_to_the_defending_team() -> None:
    home, _ = default_teams()
    away = return_chart("Beta State", NormalizedCell(ResultKind.TOUCHDOWN, provenance()))
    source = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)])
    game = PlaySession.new(home, away, seed=1)
    game.snap("9", "A", dice=source)
    assert game.view().pending.chooser_side == "away"
    plan = plan_turn(game.view(), "home", BaselineCoach(31))
    assert plan.turn.automatic and plan.arguments == ("interception:return",)
    report = game.decide(plan.arguments[0])
    assert report.outcome == "defensive_touchdown"
    assert game.view().pending.chooser_side == "away"
    plan = plan_turn(game.view(), "home", BaselineCoach(31))
    assert plan.turn.automatic and plan.arguments == ("conversion:kick",)
    assert report.trace[-1].roll == roll_view(OffensiveRoll(1, 0, 0))


def test_end_zone_recovery_owner_and_touchback_do_not_invent_a_return_roll() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70)
    home = replace(team_chart("Same", plays={Play.ONE: fumble}), recovery_range=range(10, 20))
    away = return_chart("Same", NormalizedCell(ResultKind.YARDS, provenance(), yards=12))
    source = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(3, 4, 3)])
    game = PlaySession.new(home, away, seed=1)
    report = game.snap("1", "A", dice=source)
    assert game.view().pending.chooser_side == "away"
    plan = plan_turn(game.view(), "home", BaselineCoach(31))
    assert plan.turn.automatic and plan.arguments == ("end_zone:touchback",)
    after = game.decide(plan.arguments[0])
    assert after.outcome == "touchback"
    assert after.trace == report.trace
    assert report.trace[-1].roll == roll_view(OffensiveRoll(3, 4, 3))


@pytest.mark.parametrize(
    "team,owner", [(PenaltyTeam.OFFENSE, "away"), (PenaltyTeam.DEFENSE, "home")]
)
def test_penalty_owner_is_explicit_with_identical_team_names(team, owner) -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(team, PenaltyCode.FIXED, yards=5)
    )
    home = team_chart("Same")
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=foul if row.roll == 10 else yards(4)) if row.play is Play.ONE else row
            for row in home.offense
        ),
    )
    game = PlaySession.new(home, team_chart("Same", defense=0), seed=1)
    game.snap(
        "1",
        "A",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 1, 0)]),
    )
    assert game.view().pending.chooser_side == owner
    assert plan_turn(game.view(), owner, BaselineCoach(31)).turn.human_role == "decision"
    other = "home" if owner == "away" else "away"
    plan = plan_turn(game.view(), other, BaselineCoach(31))
    assert plan.turn.automatic and plan.operation == "decide"
    assert plan.arguments[0] in {c.id for c in game.view().pending.choices if c.enabled}


def test_overtime_toss_and_mandatory_two_are_engine_owned_not_coach_era_rules() -> None:
    game = overtime_game(2021)
    view = game.view()
    assert view.overtime_toss_dice == tuple(roll_view(r) for r in view.overtime_toss_rolls)
    chooser = view.pending.chooser_side
    assert chooser in {"home", "away"}
    assert plan_turn(view, chooser, BaselineCoach(31)).turn.human_role == "decision"
    other = "home" if chooser == "away" else "away"
    assert plan_turn(view, other, BaselineCoach(31)).turn.automatic
    start_overtime(game)
    touchdown_and_try(game)
    touchdown_and_try(game)
    snap(game)
    view = game.view()
    assert {c.id for c in view.pending.choices if c.enabled} == {"conversion:two"}
    plan = plan_turn(
        view, "home" if view.pending.chooser_side == "away" else "away", BaselineCoach(31)
    )
    assert plan.arguments == ("conversion:two",)
    game.decide(plan.arguments[0])
    snap(game)
    # The other series can be played without asking the coach to apply any era rule.
    snap(game)
    game.decide("conversion:two")
    snap(game)
    assert game.view().overtime.round_number == 3
    view = game.view()
    assert view.phase == "two_point_try" and not view.actions.special
    plan = plan_turn(view, "home" if view.state.possession == "away" else "away", BaselineCoach(31))
    assert plan.operation == "snap" and not plan.turn.automatic
    assert not plan.turn.actions.special and not plan.turn.actions.offense


def test_optional_timeouts_are_offered_only_to_the_controlling_human() -> None:
    game = overtime_game(2002)
    # Overtime choices still belong to the toss winner, then timeouts are side-owned.
    start_overtime(game)
    for human in ("home", "away"):
        turn = plan_turn(game.view(), human, BaselineCoach(31)).turn
        assert all(
            not a.key.startswith("timeout:") or a.key == f"timeout:{human}"
            for a in turn.game_actions
        )
    miss_series(game)


def test_untimed_overtime_does_not_trigger_late_regulation_kneel_strategy() -> None:
    game = overtime_game(2002)
    start_overtime(game)
    view = game.view()
    assert view.state.possession == "home" and view.clock.remaining == 0
    view = replace(view, score=replace(view.score, home=7, away=0))
    assert "kneel" in {a.key for a in view.game_actions}
    plan = plan_turn(view, "away", BaselineCoach(31))
    assert plan.operation == "snap"
    assert plan.computer_choice.key in {a.key for a in view.actions.offense}
