"""Synthetic tests for per-play guaranteed in/out-of-bounds declarations."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_session import plan_turn
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import InvalidDecisionError, PendingDecisionError, PlaySession
from bowl_bound.timing import Clock
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_models import provenance
from tests.test_regulation import kickoff, new_game
from tests.test_special_teams import special_chart


def play_dice() -> ScriptedDice:
    return ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])


def test_out_of_bounds_declaration_costs_five_and_guarantees_ten_seconds() -> None:
    game = new_game(clock=Clock(1, 900), plays={Play.ONE: yards(12)})
    kickoff(game)

    offered = {choice.id for choice in game.view().play_modifiers}
    assert offered == {"bounds:oob", "bounds:ib"}
    game.action("bounds:oob")
    report = game.snap("1", "A", dice=play_dice())

    assert report.yards == 7
    assert report.statistics.yards == 7
    assert report.timing.out_of_bounds
    assert report.trace[0].cell == "12"
    assert game.view().timing_log[-1].seconds == 10
    assert game.view().clock.remaining == 890
    assert game.view().bounds_declaration is None


def test_in_bounds_declaration_costs_five_only_for_an_oob_result() -> None:
    marked = replace(yards(12), out_of_bounds=True)
    game = new_game(clock=Clock(2, 120), plays={Play.ONE: marked})
    kickoff(game)
    game.action("bounds:ib")

    report = game.snap("1", "A", dice=play_dice())
    assert report.yards == 7
    assert report.statistics.yards == 7
    assert not report.timing.out_of_bounds
    assert report.trace[0].cell == "12*"
    assert game.view().phase == "clock_choice"
    game.action("bounds:oob")
    assert game.view().timing_log[-1].seconds == 30
    assert game.view().clock.remaining == 90
    assert game.view().bounds_declaration == "out_of_bounds"


def test_a_natural_oob_result_has_no_oob_declaration_yardage_cost() -> None:
    marked = replace(yards(12), out_of_bounds=True)
    game = new_game(clock=Clock(1, 900), plays={Play.ONE: marked})
    kickoff(game)
    game.action("bounds:oob")

    report = game.snap("1", "A", dice=play_dice())

    assert report.yards == 12
    assert report.timing.out_of_bounds
    assert game.view().timing_log[-1].seconds == 10


def test_bounds_selection_is_one_mutually_exclusive_toggle_and_resets_after_a_play() -> None:
    game = new_game()
    kickoff(game)

    game.action("bounds:oob")
    assert game.view().bounds_declaration == "out_of_bounds"
    game.action("bounds:ib")
    assert game.view().bounds_declaration == "in_bounds"
    game.action("bounds:ib")
    assert game.view().bounds_declaration is None


def test_bounds_declaration_is_not_applied_to_a_punt_or_carried_past_it() -> None:
    game = new_game()
    kickoff(game)
    game.action("bounds:oob")

    report = game.kick(
        "punt",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]),
    )

    assert report.supported
    assert game.view().bounds_declaration is None
    assert not report.timing.guaranteed_out_of_bounds


def test_bounds_declaration_is_consumed_when_it_changes_possession() -> None:
    game = new_game(gain=0)
    kickoff(game)
    for _ in range(3):
        game.snap("1", "A", dice=play_dice())
    game.action("bounds:oob")

    report = game.snap("1", "A", dice=play_dice())

    assert report.outcome == "turnover_on_downs"
    assert report.yards == -5
    assert report.state_after.possession == "away"
    assert game.view().bounds_declaration is None


def test_coached_controls_offer_bounds_declarations_only_to_the_offense() -> None:
    game = new_game()
    kickoff(game)
    view = game.view()
    offense = view.state.possession
    defense = "away" if offense == "home" else "home"
    coach = BaselineCoach(seed=11)

    offensive_turn = plan_turn(view, offense, coach).turn
    defensive_turn = plan_turn(view, defense, coach).turn

    assert offensive_turn.human_role == "offense"
    assert {action.key for action in offensive_turn.game_actions} >= {"bounds:oob", "bounds:ib"}
    assert defensive_turn.human_role == "defense"
    assert not any(action.key.startswith("bounds:") for action in defensive_turn.game_actions)

    game.action("bounds:oob")
    game.snap("1", "A", dice=play_dice())
    assert game.view().bounds_declaration is None


def test_unavailable_declaration_actions_are_rejected_without_changing_state() -> None:
    game = new_game()
    before = game.view()

    with pytest.raises(PendingDecisionError, match="pending"):
        game.action("bounds:oob")

    assert game.view() == before


def test_in_bounds_declaration_has_no_cost_for_a_result_already_in_bounds() -> None:
    session = PlaySession.new(team_chart("Home", offense=12), team_chart("Away", defense=0), seed=1)

    report = session.snap("1", "A", dice=play_dice(), bounds_declaration="in_bounds")

    assert report.yards == 12
    assert not report.timing.out_of_bounds
    assert report.statistics.yards == 12


@pytest.mark.parametrize(
    "cell",
    [
        NormalizedCell(ResultKind.INCOMPLETE, provenance()),
        NormalizedCell(ResultKind.TOUCHDOWN, provenance()),
    ],
    ids=["incomplete", "touchdown"],
)
def test_out_of_bounds_declaration_exceptions_do_not_lose_five_yards(
    cell: NormalizedCell,
) -> None:
    start = 5 if cell.kind is ResultKind.TOUCHDOWN else 65
    session = PlaySession.new(
        team_chart("Home", plays={Play.ONE: cell}),
        team_chart("Away", defense=0),
        seed=1,
        start_yards_to_goal=start,
    )

    report = session.snap("1", "A", dice=play_dice(), bounds_declaration="out_of_bounds")

    assert report.yards == 0
    assert report.statistics.yards == (5 if cell.kind is ResultKind.TOUCHDOWN else 0)
    assert report.timing.incomplete is (cell.kind is ResultKind.INCOMPLETE)
    assert report.timing.scoring is (cell.kind is ResultKind.TOUCHDOWN)
    assert not report.timing.guaranteed_out_of_bounds


def _penalty_session() -> PlaySession:
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 5),
    )
    home = team_chart("Home", plays={Play.ONE: penalty})
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=yards(12)) if row.play is Play.ONE and row.roll == 20 else row
            for row in home.offense
        ),
    )
    return PlaySession.new(home, team_chart("Away", defense=0), seed=1)


def _penalty_dice() -> ScriptedDice:
    return ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])


def test_declining_a_penalty_applies_the_pending_out_of_bounds_declaration() -> None:
    session = _penalty_session()
    pending = session.snap("1", "A", dice=_penalty_dice(), bounds_declaration="out_of_bounds")
    assert pending.pending

    decision = session.view().pending
    assert decision is not None
    decline = next(item for item in decision.decision_outcomes if item.choice_id == "decline")
    assert (decline.possession, decline.yards_to_goal, decline.down, decline.yards_to_go) == (
        "home",
        58,
        2,
        3,
    )

    report = session.decide("decline")

    assert report.yards == 7
    assert report.statistics.yards == 7
    assert report.timing.guaranteed_out_of_bounds


def test_accepting_a_penalty_does_not_apply_the_declaration_cost() -> None:
    session = _penalty_session()
    pending = session.snap("1", "A", dice=_penalty_dice(), bounds_declaration="out_of_bounds")
    assert pending.pending

    report = session.decide("accept:0:previous")

    assert report.outcome == "penalty_accepted"
    assert report.timing.penalty
    assert not report.timing.guaranteed_out_of_bounds
    assert report.state_after.yards_to_goal == 60


def test_declaration_does_not_change_an_interception_during_its_pending_resolution() -> None:
    home, away = default_teams()
    session = PlaySession.new(home, away, seed=1)
    pending = session.snap("9", "A", bounds_declaration="out_of_bounds")
    assert pending.pending

    report = session.decide("interception:return")

    assert report.outcome == "defensive_recovery"
    assert report.statistics.kind.value == "interception"
    assert report.description.endswith("Out-of-bounds declaration: no yardage cost applies.")


def test_invalid_bounds_declaration_is_rejected_before_consuming_dice() -> None:
    session = PlaySession.new(team_chart("Home"), team_chart("Away"), seed=1)
    dice = play_dice()
    before = session.view()

    with pytest.raises(InvalidDecisionError, match="bounds declaration"):
        session.snap("1", "A", dice=dice, bounds_declaration="both")

    assert dice._position == 0
    assert session.view() == before


def test_selected_declaration_survives_exact_save_resume_and_next_play() -> None:
    home, away = (
        replace(
            team_chart(name, season=2002),
            special_teams=special_chart(
                name, kickoff=yards(70), kickoff_return=yards(10)
            ).special_teams,
        )
        for name in ("Home", "Away")
    )
    charts = {"2002/home": home, "2002/away": away}
    game = SavedGame.new(
        home,
        away,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        mode="regulation",
        clock=Clock(1, 900),
        coach_seed=3,
    )
    game.decide("toss:receive")
    game.kick("kickoff")
    if game.view().pending:
        game.decide("kick:touchback")
    game.action("bounds:oob")

    restored = loads_game(dumps_game(game), charts.__getitem__)
    assert restored.view() == game.view()

    original_report = game.snap("1", "A")
    restored_report = restored.snap("1", "A")
    assert restored_report == original_report
    assert restored.view() == game.view()
    assert restored_report.timing.guaranteed_out_of_bounds
    assert restored_report.yards == original_report.yards
