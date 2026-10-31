"""Synthetic regressions for the post-review engine hardening milestone."""

from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, ResultKind, SpecialTeamsColumn, TeamChart
from bowl_bound.turnovers import (
    TurnoverOutcome,
    resolve_fumble,
    resolve_interception,
)
from tests.synthetic_teams import team_chart, yards


def return_team(name: str, gain: int = 0, *, cell: NormalizedCell | None = None) -> TeamChart:
    team = team_chart(name, defense=0)
    return replace(
        team,
        special_teams=tuple(
            replace(row, cell=cell or yards(gain))
            if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN
            else row
            for row in team.special_teams
        ),
    )


@pytest.mark.parametrize("possession", list(Possession))
@pytest.mark.parametrize("depth", [0, 1, 9, 10, 20])
def test_interception_in_defenders_end_zone_waits_without_awarding_points(
    possession: Possession, depth: int
) -> None:
    result = resolve_interception(
        FieldState(possession, 10, 2, 8),
        location=10 + depth,
        interceptor=return_team("Defender"),
        choice="return",
        dice=ScriptedDice([]),
    )
    assert result.outcome is TurnoverOutcome.END_ZONE_RETURN_PENDING
    assert result.recovery_possession is possession.other
    assert result.end_zone_depth == min(depth, 9)
    assert result.points == (0, 0) and result.trace == ()


@pytest.mark.parametrize("possession", list(Possession))
@pytest.mark.parametrize("spot", [100, 101, 109, 110, 120])
def test_interception_in_offenses_end_zone_distinguishes_goal_and_end_lines(
    possession: Possession, spot: int
) -> None:
    result = resolve_interception(
        FieldState(possession, 97, 3, 8),
        location=97 - spot,
        interceptor=return_team("Defender"),
        choice="return",
        dice=ScriptedDice([]),
    )
    points = 6 if spot < 110 else 2
    assert result.outcome is (
        TurnoverOutcome.DEFENSIVE_TOUCHDOWN if spot < 110 else TurnoverOutcome.SAFETY
    )
    assert result.points == ((0, points) if possession is Possession.HOME else (points, 0))
    assert result.trace == ()


@pytest.mark.parametrize("possession", list(Possession))
@pytest.mark.parametrize("spot", [100, 103, 109, 110])
@pytest.mark.parametrize("retained", [False, True])
def test_own_end_zone_fumble_uses_recovery_only_before_end_line(
    possession: Possession, spot: int, retained: bool
) -> None:
    roll = OffensiveRoll(1, 0, 0) if retained else OffensiveRoll(3, 4, 5)
    result = resolve_fumble(
        FieldState(possession, 97, 3, 8),
        location=97 - spot,
        fumbler=return_team("Fumbler"),
        opponent=return_team("Opponent"),
        dice=ScriptedDice([roll] if spot < 110 else []),
    )
    safety = retained or spot >= 110
    assert result.outcome is (
        TurnoverOutcome.SAFETY if safety else TurnoverOutcome.DEFENSIVE_TOUCHDOWN
    )
    points = 2 if safety else 6
    assert result.points == ((0, points) if possession is Possession.HOME else (points, 0))
    assert len(result.trace) == (1 if spot < 110 else 0)


def test_own_fumble_recovery_returning_back_into_own_end_zone_is_a_safety() -> None:
    result = resolve_fumble(
        FieldState(Possession.HOME, 94, 3, 8),
        location=-2,
        fumbler=return_team("Home", -10),
        opponent=return_team("Away"),
        dice=ScriptedDice([OffensiveRoll(1, 4, 3), OffensiveRoll(1, 0, 0)]),
    )
    assert result.outcome is TurnoverOutcome.SAFETY
    assert result.points == (0, 2) and result.state is None


@pytest.mark.parametrize("gain,spot", [(0, 80), (-2, 80), (5, 80), (6, 99), (12, 93)])
def test_end_zone_return_counts_depth_and_touchbacks_when_not_across_goal(
    gain: int, spot: int
) -> None:
    from bowl_bound.turnovers import resolve_end_zone_recovery_return

    result = resolve_end_zone_recovery_return(
        return_team("Away", gain),
        return_team("Home"),
        Possession.AWAY,
        ScriptedDice([OffensiveRoll(1, 0, 0)]),
        end_zone_depth=5,
    )
    assert result.state == FieldState(Possession.AWAY, spot, 1, 10)
    assert result.points == (0, 0)
    assert result.outcome is (
        TurnoverOutcome.TOUCHBACK if gain <= 5 else TurnoverOutcome.DEFENSIVE_RECOVERY
    )


def test_fumble_beyond_opponents_end_line_uses_white_faces_for_live_recovery_depth() -> None:
    result = resolve_fumble(
        FieldState(Possession.HOME, 10, 1, 10),
        location=25,
        fumbler=return_team("Home"),
        opponent=return_team("Away"),
        dice=ScriptedDice([OffensiveRoll(3, 2, 4), OffensiveRoll(3, 4, 5)]),
    )
    assert result.outcome is TurnoverOutcome.END_ZONE_RETURN_PENDING
    assert result.end_zone_depth == 6
    assert [(e.section, e.roll) for e in result.trace] == [
        ("end_zone_depth", OffensiveRoll(3, 2, 4)),
        ("fumble_recovery", OffensiveRoll(3, 4, 5)),
    ]


def test_end_zone_return_no_change_is_supported() -> None:
    from bowl_bound.turnovers import resolve_end_zone_recovery_return
    from tests.test_models import provenance

    result = resolve_end_zone_recovery_return(
        return_team("Away", cell=NormalizedCell(ResultKind.NO_CHANGE, provenance())),
        return_team("Home"),
        Possession.AWAY,
        ScriptedDice([OffensiveRoll(1, 0, 0)]),
    )
    assert result.outcome is TurnoverOutcome.TOUCHBACK
    assert result.state == FieldState(Possession.AWAY, 80, 1, 10)


@pytest.mark.parametrize("kind", [ResultKind.INTERCEPTION, ResultKind.FUMBLE])
def test_declining_scrimmage_foul_continues_prepared_turnover_without_fresh_lookup(
    kind: ResultKind,
) -> None:
    from bowl_bound.dice import DefensiveRoll
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam, Play
    from bowl_bound.session import PlaySession
    from tests.test_models import provenance

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = team_chart("Home", plays={Play.ONE: NormalizedCell(kind, provenance(), yards=10)})
    home = replace(
        home,
        offense=tuple(
            replace(r, cell=foul) if r.roll == 20 and r.play is Play.ONE else r
            for r in home.offense
        ),
    )
    game = PlaySession.new(home, return_team("Away", 0), seed=1)
    source = ScriptedDice(
        [
            OffensiveRoll(2, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 0),
        ]
    )
    game.snap("1", "A", dice=source)
    decline = next(c for c in game.view().pending.choices if c.id == "decline")
    assert decline.enabled, decline.reason
    result = game.decide("decline")
    if kind is ResultKind.INTERCEPTION:
        assert result.outcome == "interception_pending"
        result = game.decide("interception:return")
    assert not result.pending and result.supported
    assert [e.section for e in result.trace][:3] == ["offense", "defense", "penalty_reroll"]
    assert game.view().state.yards_to_goal == (45 if kind is ResultKind.INTERCEPTION else 55)
    assert len(game.view().log) == 1


@pytest.mark.parametrize("choice", ["return:accept", "return:decline"])
@pytest.mark.parametrize(
    "location,return_gain,expected,credit", [(0, 4, (3, 9, 64), 4), (9, 0, (3, 4, 59), 9)]
)
def test_accepted_own_recovery_return_foul_preserves_down_and_line_to_gain(
    location: int, return_gain: int, expected: tuple[int, int, int], credit: int, choice: str
) -> None:
    from bowl_bound.dice import DefensiveRoll
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam, Play
    from bowl_bound.session import PlaySession
    from tests.test_models import provenance

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = return_team("Home", return_gain)
    home = replace(
        home,
        offense=team_chart(
            "Home",
            offense=1,
            plays={Play.TWO: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=location)},
        ).offense,
        special_teams=tuple(
            replace(r, cell=foul)
            if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN and r.roll == 10
            else r
            for r in home.special_teams
        ),
    )
    game = PlaySession.new(home, return_team("Away"), seed=1)
    for _ in range(2):
        game.snap("1", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))
    assert game.view().state.down == 3 and game.view().state.yards_to_go == 8
    game.snap(
        "2",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 4, 3),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 0, 1),
            ]
        ),
    )
    report = game.decide(choice)
    if choice == "return:decline":
        expected = (4, 4, 59) if location == 0 else (1, 10, 54)
    assert report.outcome == "offensive_recovery"
    assert (
        report.state_after.down,
        report.state_after.yards_to_go,
        report.state_after.yards_to_goal,
    ) == expected
    assert report.statistics.yards == credit


def test_end_zone_return_penalty_uses_actual_origin_for_enforcement() -> None:
    from bowl_bound.dice import DefensiveRoll
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam, Play
    from bowl_bound.session import PlaySession
    from tests.test_models import provenance

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = team_chart(
        "Home", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70)}
    )
    away = return_team("Away", 12)
    away = replace(
        away,
        special_teams=tuple(
            replace(r, cell=foul)
            if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN and r.roll == 10
            else r
            for r in away.special_teams
        ),
    )
    game = PlaySession.new(home, away, seed=1)
    source = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(3, 4, 5),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 1),
        ]
    )
    game.snap("1", "A", dice=source)
    assert all(c.enabled for c in game.view().pending.choices)
    game.decide("end_zone:return")
    choice = next(c for c in game.view().pending.choices if c.id.startswith("return:accept"))
    assert choice.enabled, choice.reason
    result = game.decide(choice.id)
    # Five yards is limited to half the distance from own 7: three yards.
    assert result.state_after.yards_to_goal == 96


def test_field_goal_is_not_offered_when_the_hold_would_be_outside_the_field() -> None:
    from bowl_bound.session import InvalidDecisionError, PlaySession

    game = PlaySession.new(return_team("Home"), return_team("Away"), seed=1, start_yards_to_goal=95)
    assert "field_goal" not in {a.key for a in game.view().actions.special}
    with pytest.raises(InvalidDecisionError):
        game.kick("field_goal", dice=ScriptedDice([]))


def test_fourth_down_does_not_offer_a_spike_but_can_still_hurry() -> None:
    from tests.test_regulation import kickoff, new_game, snap

    game = new_game(gain=0)
    kickoff(game)
    for _ in range(3):
        snap(game)
    assert game.view().state.down == 4
    choices = {c.id for c in game.view().pending.choices}
    assert "clock:spike" not in choices
    assert "clock:hurry" in choices


def test_period_ending_timing_returns_a_boundary_event_not_the_previous_play() -> None:
    from bowl_bound.statistics import StatKind
    from bowl_bound.timing import Clock
    from tests.test_regulation import kickoff, new_game, snap

    game = new_game(clock=Clock(2, 20), gain=0)
    kickoff(game)
    prior = snap(game)
    before = game.view().log
    report = game.snap("1", "A", dice=ScriptedDice([]))
    assert report.outcome == "period_boundary"
    assert report.called_play == "Period end"
    assert "prior play's normal timing" in report.description.lower()
    assert report.trace == () and report.statistics.kind is StatKind.EXCLUDED
    assert report.number == prior.number
    assert game.view().clock.quarter == 2 and game.view().clock.remaining == 0
    assert game.view().log == before and before[-1] == prior


def test_in_field_interception_return_back_into_own_end_zone_is_not_a_touchback() -> None:
    result = resolve_interception(
        FieldState(Possession.HOME, 20, 1, 10),
        location=15,
        interceptor=return_team("Away", -8),
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0)]),
    )
    assert result.outcome is TurnoverOutcome.SAFETY and result.points == (2, 0)


def test_own_recovery_return_touchdown_keeps_offensive_classification() -> None:
    result = resolve_fumble(
        FieldState(Possession.HOME, 10, 1, 10),
        location=5,
        fumbler=return_team("Home", 10),
        opponent=return_team("Away"),
        dice=ScriptedDice([OffensiveRoll(1, 4, 3), OffensiveRoll(1, 0, 0)]),
    )
    assert result.outcome is TurnoverOutcome.OFFENSIVE_TOUCHDOWN
    assert result.points == (6, 0)


@pytest.mark.parametrize(
    "recovery,expected,points",
    [
        (OffensiveRoll(1, 0, 0), TurnoverOutcome.SAFETY, (2, 0)),
        (OffensiveRoll(3, 4, 4), TurnoverOutcome.DEFENSIVE_TOUCHDOWN, (6, 0)),
    ],
)
def test_fumble_on_an_elected_end_zone_return_uses_actual_fumble_spot(
    recovery: OffensiveRoll, expected: TurnoverOutcome, points: tuple[int, int]
) -> None:
    from bowl_bound.turnovers import resolve_end_zone_recovery_return
    from tests.test_models import provenance

    result = resolve_end_zone_recovery_return(
        return_team("Away", cell=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2)),
        return_team("Home"),
        Possession.AWAY,
        ScriptedDice([OffensiveRoll(1, 0, 0), recovery]),
        end_zone_depth=5,
    )
    assert result.outcome is expected and result.points == points
    assert [e.section for e in result.trace] == ["end_zone_recovery_return", "fumble_recovery"]


def test_declined_scrimmage_penalty_can_continue_into_end_zone_recovery_choice() -> None:
    from bowl_bound.dice import DefensiveRoll
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam, Play
    from bowl_bound.session import PlaySession
    from tests.test_models import provenance

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = team_chart(
        "Home", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=8)}
    )
    home = replace(
        home,
        offense=tuple(
            replace(r, cell=foul) if r.roll == 20 and r.play is Play.ONE else r
            for r in home.offense
        ),
    )
    game = PlaySession.new(home, return_team("Away"), seed=1, start_yards_to_goal=5)
    game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(2, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(3, 4, 5),
            ]
        ),
    )
    assert game.decide("decline").outcome == "end_zone_recovery_pending"
    report = game.decide("end_zone:touchback")
    assert report.state_after.yards_to_goal == 80
    assert [e.section for e in report.trace] == [
        "offense",
        "defense",
        "penalty_reroll",
        "fumble_recovery",
    ]
    assert len(game.view().log) == 1


def test_own_fumble_advance_then_retreat_does_not_earn_a_premature_first_down() -> None:
    result = resolve_fumble(
        FieldState(Possession.HOME, 63, 3, 8),
        location=9,
        fumbler=return_team("Home", -4),
        opponent=return_team("Away"),
        dice=ScriptedDice([OffensiveRoll(1, 4, 3), OffensiveRoll(1, 0, 0)]),
    )
    assert result.state == FieldState(Possession.HOME, 58, 4, 3)
