"""RULE-001: rare return boundaries with synthetic cells and exact dice."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, PenaltyTeam, Play, ResultKind, SpecialTeamsColumn
from bowl_bound.session import PlaySession
from bowl_bound.turnovers import resolve_interception
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_penalties import foul


def returning(*cells: NormalizedCell):
    base = team_chart("Away", season=2002)
    mapping = dict(zip((10, 20, 30, 39), cells, strict=False))
    return replace(
        base,
        special_teams=tuple(
            replace(r, cell=mapping[r.roll])
            if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN and r.roll in mapping
            else r
            for r in base.special_teams
        ),
    )


def intercept(away, rolls):
    return resolve_interception(
        FieldState(Possession.HOME, 60, 2, 8),
        location=20,
        interceptor=away,
        opponent=team_chart("Home"),
        choice="return",
        dice=ScriptedDice(rolls),
    )


def test_consecutive_return_fouls_offer_separate_alternatives() -> None:
    away = returning(foul(PenaltyTeam.OFFENSE), foul(PenaltyTeam.OFFENSE, distance=15), yards(12))
    result = intercept(
        away, [OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0), OffensiveRoll(3, 0, 0)]
    )
    assert [p.yards for p in result.return_penalties] == [5, 15]
    assert result.return_yards == 12 and len(result.trace) == 3


def test_penalty_then_literal_td_retains_numeric_endpoint_for_acceptance() -> None:
    away = returning(foul(PenaltyTeam.OFFENSE), NormalizedCell(ResultKind.TOUCHDOWN, provenance()))
    result = intercept(away, [OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)])
    assert result.return_yards == 60 and result.return_start.yards_to_goal == 60
    assert result.points == (0, 6)


def test_blank_is_explicit_no_change_not_an_unresolved_or_missing_cell() -> None:
    result = intercept(
        returning(NormalizedCell(ResultKind.NO_CHANGE, provenance())), [OffensiveRoll(1, 0, 0)]
    )
    assert result.state == FieldState(Possession.AWAY, 60, 1, 10)
    assert len(result.trace) == 1 and result.points == (0, 0)


def test_return_fumble_chain_limit_is_propagated() -> None:
    import bowl_bound.turnovers as module

    # Both charts always recover and return at total 17. Cap temporarily proves
    # that nested recovery context is propagated, rather than Python recursion.
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=0)
    away = replace(
        returning(fumble),
        special_teams=tuple(
            replace(r, cell=fumble) if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN else r
            for r in returning(fumble).special_teams
        ),
        recovery_range=range(10, 40),
    )
    original = module.MAX_TURNOVER_CHAIN
    module.MAX_TURNOVER_CHAIN = 3
    try:
        with pytest.raises(ValueError, match="return-fumble limit"):
            intercept(away, [OffensiveRoll(1, 4, 3)] * 20)
    finally:
        module.MAX_TURNOVER_CHAIN = original


def test_pending_return_penalty_does_not_duplicate_trace_when_declined() -> None:
    home = team_chart(
        "Home",
        season=2002,
        plays={Play.ONE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)},
    )
    away = returning(foul(PenaltyTeam.OFFENSE), yards(12))
    game = PlaySession.new(home, away, seed=1, start_yards_to_goal=60)
    game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    pending = game.decide("interception:return")
    assert pending.pending and len(pending.trace) == 4
    result = game.decide("return:decline")
    assert len(result.trace) == 4
    assert [e.section for e in result.trace] == [
        "offense",
        "defense",
        "turnover_return",
        "turnover_return_reroll",
    ]


def test_accepting_return_foul_does_not_roll_a_cancelled_fumble_recovery() -> None:
    home = team_chart(
        "Home",
        season=2002,
        plays={Play.ONE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)},
    )
    away = returning(
        foul(PenaltyTeam.OFFENSE), NormalizedCell(ResultKind.FUMBLE, provenance(), yards=12)
    )
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(2, 0, 0),
            sentinel,
        ]
    )
    game = PlaySession.new(home, away, seed=1, start_yards_to_goal=60)
    game.snap("1", "A", dice=dice)
    pending = game.decide("interception:return")
    assert pending.pending and len(pending.trace) == 4
    result = game.decide("return:accept")
    assert result.state_after.yards_to_goal == 53 and game.view().score.away == 0
    assert dice.offensive() == sentinel and len(result.trace) == 4


@pytest.mark.parametrize("conversion", [False, True])
def test_literal_td_after_return_penalty_can_be_accepted_without_scoring(conversion: bool) -> None:
    home = team_chart(
        "Home",
        season=2002,
        offense=100,
        plays={Play.ONE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=0)},
    )
    away = returning(foul(PenaltyTeam.OFFENSE), NormalizedCell(ResultKind.TOUCHDOWN, provenance()))
    game = PlaySession.new(home, away, seed=1, start_yards_to_goal=60)
    if conversion:
        game.snap("2", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))
        game.decide("conversion:two")
    game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    pending = game.decide("interception:return")
    assert pending.pending
    game.decide("return:accept")
    assert game.view().score.away == 0
    assert game.view().score.home == (6 if conversion else 0)
    assert game.view().pending is None
    assert len(game.view().log[-1].trace) == 4


def test_end_zone_recovery_return_with_penalties_is_available_and_touchback_needs_no_roll() -> None:
    home = team_chart(
        "Home",
        season=2002,
        plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=8)},
    )
    away = returning(foul(PenaltyTeam.OFFENSE))
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(3, 4, 5)])
    game = PlaySession.new(home, away, seed=1, start_yards_to_goal=5)
    game.snap("1", "A", dice=dice)
    before = game.view()
    choice = next(c for c in before.pending.choices if c.id == "end_zone:return")
    assert choice.enabled and choice.reason is None
    assert game.view() == before
    completed = game.decide("end_zone:touchback")
    assert completed.state_after.yards_to_goal == 80 and len(completed.trace) == 3


def test_nested_end_zone_recovery_preserves_actual_recovery_team() -> None:
    home = team_chart(
        "Home",
        season=2002,
        plays={Play.ONE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)},
    )
    away = returning(NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70))
    game = PlaySession.new(home, away, seed=1, start_yards_to_goal=60)
    game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 2, 3),  # White faces place the live fumble five deep.
                OffensiveRoll(3, 4, 5),
            ]
        ),
    )
    game.decide("interception:return")
    assert game.view().pending.chooser == "Home"
    result = game.decide("end_zone:touchback")
    assert result.state_after.possession == "home" and result.state_after.yards_to_goal == 80
    assert len(result.trace) == 5
    assert result.trace[-2].section == "end_zone_depth"
