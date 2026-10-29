"""Synthetic Basic VI-5/VI-6 special-teams rules coverage."""

from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    ResultKind,
    SpecialTeamsCell,
    TeamChart,
)
from bowl_bound.special_teams import (
    SpecialTeamsOutcome,
    SpecialTeamsPlay,
    free_kick_touchback_spot,
    kickoff_spot,
    resolve_field_goal,
    resolve_kickoff,
    resolve_punt,
)
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


@pytest.mark.parametrize(
    ("season", "expected"),
    [
        (1940, 40),
        (1985, 40),
        (1986, 35),
        (2006, 35),
        (2007, 30),
        (2011, 30),
        (2012, 35),
        (2023, 35),
    ],
)
def test_home_season_selects_the_kickoff_spot(season: int, expected: int) -> None:
    assert kickoff_spot(season) == expected


@pytest.mark.parametrize(("season", "expected"), [(2011, 20), (2012, 25), (2023, 25)])
def test_free_kick_touchback_spot_uses_the_home_season(season: int, expected: int) -> None:
    assert free_kick_touchback_spot(season) == expected


@pytest.mark.parametrize("season", [1939, 2024, True, "2012"])
def test_special_teams_season_policy_rejects_unsupported_values(season: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        kickoff_spot(season)


def special_chart(name: str, **cells: NormalizedCell) -> object:
    chart = team_chart(name)
    return replace(
        chart,
        special_teams=tuple(
            SpecialTeamsCell(
                record.column, record.roll, cells.get(record.column.value, record.cell)
            )
            for record in chart.special_teams
        ),
    )


def test_kickoff_return_uses_home_season_spot_and_both_real_chart_rolls() -> None:
    kicking = special_chart("Home", kickoff=yards(45))
    receiving = special_chart("Away", kickoff_return=yards(12))

    result = resolve_kickoff(
        kicking,
        receiving,
        home_season=2007,
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]),
    )

    assert result.outcome is SpecialTeamsOutcome.KICKOFF_RETURN
    assert result.state == FieldState(Possession.AWAY, 63, 1, 10)
    assert [entry.section for entry in result.trace] == ["kickoff", "kickoff_return"]


def test_kickoff_into_the_end_zone_uses_the_season_touchback_spot_without_return_roll() -> None:
    kicking = special_chart("Home", kickoff=yards(70))
    receiving = special_chart("Away", kickoff_return=yards(12))

    result = resolve_kickoff(
        kicking, receiving, home_season=2012, dice=ScriptedDice([OffensiveRoll(1, 0, 0)])
    )

    assert result.outcome is SpecialTeamsOutcome.TOUCHBACK
    assert result.state == FieldState(Possession.AWAY, 75, 1, 10)


def test_field_goal_uses_line_of_scrimmage_distance_not_statistical_length() -> None:
    kicking = special_chart("Home", field_goal=yards(30))

    result = resolve_field_goal(
        FieldState(Possession.HOME, 30, 4, 4),
        kicking,
        ScriptedDice([OffensiveRoll(1, 0, 0)]),
        receiving=special_chart("Away"),
    )

    assert result.outcome is SpecialTeamsOutcome.FIELD_GOAL_GOOD
    assert result.state is None and result.points == (3, 0)


def test_missed_field_goal_gives_defense_its_20_or_the_spot_of_hold_whichever_is_better() -> None:
    kicking = special_chart("Home", field_goal=yards(0))

    result = resolve_field_goal(
        FieldState(Possession.HOME, 1, 4, 1),
        kicking,
        ScriptedDice([OffensiveRoll(1, 0, 0)]),
        receiving=special_chart("Away"),
    )

    assert result.outcome is SpecialTeamsOutcome.FIELD_GOAL_MISSED
    assert result.state == FieldState(Possession.AWAY, 80, 1, 10)


def test_punt_fair_catch_uses_the_punt_landing_spot_without_a_return_roll() -> None:
    kicking = special_chart("Home", punt=yards(40))
    receiving = special_chart("Away", punt_return=yards(10))

    result = resolve_punt(
        FieldState(Possession.HOME, 65, 4, 8),
        kicking,
        receiving,
        choice="fair_catch",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0)]),
    )

    assert result.outcome is SpecialTeamsOutcome.PUNT_FAIR_CATCH
    assert result.state == FieldState(Possession.AWAY, 75, 1, 10)
    assert [entry.section for entry in result.trace] == ["punt"]


def test_punt_return_uses_the_receiving_chart_and_changes_possession() -> None:
    kicking = special_chart("Home", punt=yards(40))
    receiving = special_chart("Away", punt_return=yards(10))

    result = resolve_punt(
        FieldState(Possession.HOME, 65, 4, 8),
        kicking,
        receiving,
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]),
    )

    assert result.outcome is SpecialTeamsOutcome.PUNT_RETURN
    assert result.state == FieldState(Possession.AWAY, 65, 1, 10)
    assert [entry.section for entry in result.trace] == ["punt", "punt_return"]


def test_kickoff_return_reaching_the_goal_line_awards_the_receiving_team_six_points() -> None:
    kicking = special_chart("Home", kickoff=yards(45))
    receiving = special_chart("Away", kickoff_return=yards(75))

    result = resolve_kickoff(
        kicking,
        receiving,
        home_season=2007,
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]),
    )

    assert result.outcome is SpecialTeamsOutcome.RETURN_TOUCHDOWN
    assert result.state is None and result.points == (0, 6)


def test_missed_field_goal_from_farther_out_uses_the_hold_not_the_20() -> None:
    kicking = special_chart("Home", field_goal=yards(0))
    result = resolve_field_goal(
        FieldState(Possession.HOME, 30, 4, 4),
        kicking,
        ScriptedDice([OffensiveRoll(1, 0, 0)]),
        receiving=special_chart("Away"),
    )
    assert result.state == FieldState(Possession.AWAY, 63, 1, 10)


def test_punt_marker_suppresses_the_return_roll() -> None:
    kicking = special_chart("Home", punt=replace(yards(40), out_of_bounds=True))
    receiving = special_chart("Away", punt_return=yards(10))
    result = resolve_punt(
        FieldState(Possession.HOME, 65, 4, 8),
        kicking,
        receiving,
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0)]),
    )
    assert result.state == FieldState(Possession.AWAY, 75, 1, 10)
    assert len(result.trace) == 1


def procedure(
    action: str,
    home: TeamChart,
    away: TeamChart,
    rolls: list[OffensiveRoll],
    *,
    spot: int = 65,
    possession: Possession = Possession.HOME,
    season: int = 2002,
) -> SpecialTeamsPlay:
    return SpecialTeamsPlay(
        action,
        FieldState(possession, spot, 4, min(8, spot)),
        home,
        away,
        ScriptedDice(rolls),
        home_season=season,
    )


def test_punt_choice_is_after_the_kick_and_is_applied_once() -> None:
    play = procedure(
        "punt",
        special_chart("H", punt=yards(40)),
        special_chart("A", punt_return=yards(10)),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
    )
    pending = play.begin()
    assert pending.chooser is Possession.AWAY
    assert [choice.id for choice in pending.choices] == ["kick:fair_catch", "kick:return"]
    with pytest.raises(ValueError, match="stale"):
        play.decide("invalid")
    result = play.decide("kick:return")
    assert result.state == FieldState(Possession.AWAY, 65, 1, 10)
    assert [entry.roll.total for entry in result.trace] == [10, 11]
    with pytest.raises(ValueError, match="stale"):
        play.decide("kick:return")


@pytest.mark.parametrize("possession", list(Possession))
def test_kickoff_orientation_and_mixed_season_uses_designated_home_policy(
    possession: Possession,
) -> None:
    play = procedure(
        "kickoff",
        special_chart("K", kickoff=yards(45)),
        special_chart("R", kickoff_return=yards(12)),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
        possession=possession,
        season=2007,
    )
    result = play.begin()
    assert result.state == FieldState(possession.other, 63, 1, 10)


@pytest.mark.parametrize(("return_yards", "expected"), [(4, 75), (6, 99), (105, None)])
def test_end_zone_kickoff_return_counts_the_depth_before_crossing_the_goal(
    return_yards: int,
    expected: int | None,
) -> None:
    play = procedure(
        "kickoff",
        special_chart("K", kickoff=yards(70)),
        special_chart("R", kickoff_return=yards(return_yards)),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
        season=2012,
    )
    pending = play.begin()
    assert [choice.id for choice in pending.choices] == ["kick:touchback", "kick:return"]
    result = play.decide("kick:return")
    if expected is None:
        assert result.points == (0, 6) and result.state is None
    else:
        assert result.state == FieldState(Possession.AWAY, expected, 1, 10)


@pytest.mark.parametrize(
    "redirect", [ResultKind.FIELD_GOAL_REFERENCE, ResultKind.KICKOFF_REFERENCE]
)
def test_punt_redirect_is_a_distance_lookup_not_a_field_goal_or_new_kickoff(
    redirect: ResultKind,
) -> None:
    home = special_chart(
        "H",
        punt=NormalizedCell(redirect, provenance(), out_of_bounds=True),
        field_goal=yards(12),
        kickoff=yards(12),
    )
    play = procedure(
        "punt", home, special_chart("A"), [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]
    )
    result = play.begin()
    assert result.outcome is SpecialTeamsOutcome.PUNT_DEAD
    assert result.state == FieldState(Possession.AWAY, 47, 1, 10)
    assert result.points == (0, 0) and len(result.trace) == 2


def penalty(team: PenaltyTeam, yards: int = 10) -> NormalizedCell:
    return NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(team, PenaltyCode.FIXED, yards)
    )


def with_roll(chart: TeamChart, column: str, roll: int, cell: NormalizedCell) -> TeamChart:
    return replace(
        chart,
        special_teams=tuple(
            replace(row, cell=cell) if row.column.value == column and row.roll == roll else row
            for row in chart.special_teams
        ),
    )


@pytest.mark.parametrize("choice", ["kick:accept:0", "kick:decline"])
def test_punt_penalty_acceptance_cancels_kick_while_decline_offers_reception(choice: str) -> None:
    home = with_roll(special_chart("H", punt=yards(40)), "punt", 10, penalty(PenaltyTeam.OFFENSE))
    play = procedure(
        "punt", home, special_chart("A"), [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]
    )
    pending = play.begin()
    assert pending.chooser is Possession.AWAY
    assert pending.points == (0, 0)
    result = play.decide(choice)
    if choice == "kick:accept:0":
        assert result.state == FieldState(Possession.HOME, 75, 4, 18)
    else:
        assert result.choices and len(result.trace) == 2
        assert play.decide("kick:fair_catch").state == FieldState(Possession.AWAY, 75, 1, 10)


def test_return_penalty_uses_midpoint_and_starts_first_and_ten() -> None:
    away = with_roll(
        special_chart("A", kickoff_return=yards(52)),
        "kickoff_return",
        10,
        penalty(PenaltyTeam.OFFENSE),
    )
    play = procedure(
        "kickoff",
        special_chart("H", kickoff=yards(52)),
        away,
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
    )
    assert play.begin().chooser is Possession.HOME
    accepted = play.decide("kick:accept:0")
    assert accepted.state == FieldState(Possession.AWAY, 54, 1, 10)
    assert [entry.section for entry in accepted.trace] == [
        "kickoff",
        "kickoff_return",
        "kickoff_return",
    ]


def test_kickoff_out_of_bounds_off_s_provides_receivers_two_choices_without_reroll() -> None:
    off_s = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S)
    )
    play = procedure(
        "kickoff",
        special_chart("H", kickoff=off_s),
        special_chart("A"),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)],
    )
    pending = play.begin()
    assert [choice.id for choice in pending.choices] == [
        "kick:out_of_bounds:spot",
        "kick:out_of_bounds:rekick",
    ]
    assert play.decide("kick:out_of_bounds:spot").state == FieldState(Possession.AWAY, 65, 1, 10)


@pytest.mark.parametrize("roll", [OffensiveRoll(3, 0, 0), OffensiveRoll(3, 4, 5)])
def test_every_lost_blocked_kick_is_returnable_and_39_scores_without_return_roll(
    roll: OffensiveRoll,
) -> None:
    home = replace(
        special_chart("H", punt=NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=-5)),
        recovery_range=range(10, 20),
    )
    away = special_chart("A", interception_return=yards(7))
    rolls = [OffensiveRoll(1, 0, 0), roll]
    if roll.total != 39:
        rolls.append(OffensiveRoll(1, 1, 0))
    result = procedure("punt", home, away, rolls).begin()
    if roll.total == 39:
        assert result.points == (0, 6) and result.state is None
    else:
        assert result.state == FieldState(Possession.AWAY, 23, 1, 10)
        assert [entry.section for entry in result.trace] == [
            "punt",
            "blocked_kick_recovery",
            "interception_return",
        ]


def test_return_fumble_followed_by_defensive_recovery_and_return_is_not_suppressed() -> None:
    away = replace(
        special_chart(
            "A", kickoff_return=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=10)
        ),
        recovery_range=range(10, 20),
    )
    home = special_chart("H", kickoff=yards(45), interception_return=yards(7))
    result = procedure(
        "kickoff",
        home,
        away,
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(3, 4, 3),
            OffensiveRoll(1, 2, 0),
        ],
    ).begin()
    assert result.state == FieldState(Possession.HOME, 23, 1, 10)
    assert [entry.section for entry in result.trace] == [
        "kickoff",
        "kickoff_return",
        "fumble_recovery",
        "interception_return",
    ]


def test_marked_punt_in_end_zone_is_dead_not_returnable() -> None:
    play = procedure(
        "punt",
        special_chart("H", punt=replace(yards(67), out_of_bounds=True)),
        special_chart("A"),
        [OffensiveRoll(1, 0, 0)],
    )
    result = play.begin()
    assert result.outcome is SpecialTeamsOutcome.TOUCHBACK
    assert result.state == FieldState(Possession.AWAY, 80, 1, 10)
    assert not result.choices


def test_accepted_kickoff_penalty_rekicks_from_enforced_spot() -> None:
    home = with_roll(
        special_chart("H", kickoff=yards(45)), "kickoff", 10, penalty(PenaltyTeam.OFFENSE)
    )
    play = procedure(
        "kickoff",
        home,
        special_chart("A", kickoff_return=yards(0)),
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(1, 2, 0),
            OffensiveRoll(1, 3, 0),
        ],
    )
    assert play.begin().chooser is Possession.AWAY
    accepted = play.decide("kick:accept:0")
    assert accepted.state == FieldState(Possession.AWAY, 70, 1, 10)
    assert [entry.section for entry in accepted.trace] == [
        "kickoff",
        "kickoff",
        "kickoff",
        "kickoff_return",
    ]


def test_kicking_team_retaining_kickoff_fumble_begins_first_and_ten() -> None:
    home = replace(
        special_chart("H", kickoff=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5)),
        recovery_range=range(10, 27),
    )
    result = procedure(
        "kickoff", home, special_chart("A"), [OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)]
    ).begin()
    assert result.state == FieldState(Possession.HOME, 60, 1, 10)


def test_recovered_end_zone_return_touchback_is_not_free_kick_25() -> None:
    home = replace(
        special_chart("H", kickoff=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70)),
        recovery_range=range(10, 27),
    )
    play = procedure(
        "kickoff",
        home,
        special_chart("A", interception_return=yards(2)),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(3, 0, 0), OffensiveRoll(1, 1, 0)],
        season=2012,
    )
    assert play.begin().choices
    result = play.decide("kick:return")
    assert result.state == FieldState(Possession.AWAY, 80, 1, 10)


@pytest.mark.parametrize("possession", list(Possession))
def test_field_goal_ng_and_good_both_orient_points_and_hold_spot(possession: Possession) -> None:
    chart = special_chart(
        "K", field_goal=NormalizedCell(ResultKind.NO_GOOD_FIELD_GOAL, provenance())
    )
    result = procedure(
        "field_goal",
        chart,
        special_chart("R"),
        [OffensiveRoll(1, 0, 0)],
        spot=40,
        possession=possession,
    ).begin()
    assert result.state == FieldState(possession.other, 53, 1, 10)
    good = procedure(
        "field_goal",
        special_chart("K", field_goal=yards(40)),
        special_chart("R"),
        [OffensiveRoll(1, 0, 0)],
        spot=40,
        possession=possession,
    ).begin()
    assert good.points == ((3, 0) if possession is Possession.HOME else (0, 3))


def test_blank_return_is_no_change_with_a_real_trace_not_a_missing_roll() -> None:
    result = procedure(
        "kickoff",
        special_chart("H", kickoff=yards(45)),
        special_chart("A", kickoff_return=NormalizedCell(ResultKind.NO_CHANGE, provenance())),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
    ).begin()
    assert result.state == FieldState(Possession.AWAY, 80, 1, 10)
    assert result.trace[-1].cell.kind is ResultKind.NO_CHANGE


def test_retained_blocked_kick_return_fumble_still_obeys_original_fourth_down_line() -> None:
    home = replace(
        special_chart("H", punt=NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=-5)),
        recovery_range=range(10, 27),
    )
    home = with_roll(
        home, "interception_return", 10, NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2)
    )
    play = procedure(
        "punt",
        home,
        special_chart("A"),
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 3, 4),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(2, 0, 0),
        ],
    )
    result = play.begin()
    # Recovered at own 32: still short of the original fourth-and-eight line.
    assert result.state == FieldState(Possession.AWAY, 32, 1, 10)
    assert len(result.trace) == 4


@pytest.mark.parametrize(
    ("reference", "kind", "rolls", "distance"),
    [
        ("DS", "variable_ds", [(2, 3, 4)], 9),
        ("X", "variable_x", [(2, 3, 4)], 13),
        ("T1", "variable_t1", [(2, 3, 4)], 27),
        ("T2", "variable_t2", [(1, 1, 0), (1, 2, 0)], 23),
        ("T3", "variable_t3", [(1, 0, 0), (1, 0, 0), (1, 0, 0)], 30),
    ],
)
def test_variable_punt_distance_keeps_each_consulted_roll(
    reference: str,
    kind: str,
    rolls: list[tuple[int, int, int]],
    distance: int,
) -> None:
    from bowl_bound.models import VariableReference

    cell = NormalizedCell(
        ResultKind(kind), provenance(), variable=VariableReference(reference), variable_multiplier=1
    )
    play = procedure(
        "punt",
        special_chart("H", punt=cell),
        special_chart("A"),
        [OffensiveRoll(1, 0, 0)] + [OffensiveRoll(*faces) for faces in rolls],
    )
    assert play.begin().choices
    result = play.decide("kick:fair_catch")
    assert result.state == FieldState(Possession.AWAY, 35 + distance, 1, 10)
    assert len(result.trace) == 1 + len(rolls)


@pytest.mark.parametrize(
    ("recovery", "expected_points"), [((2, 0, 0), (0, 2)), ((3, 0, 0), (0, 6))]
)
def test_blocked_kick_in_own_end_zone_requires_recovery_to_distinguish_score(
    recovery: tuple[int, int, int],
    expected_points: tuple[int, int],
) -> None:
    home = replace(
        special_chart("H", punt=NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=-6)),
        recovery_range=range(10, 27),
    )
    result = procedure(
        "punt",
        home,
        special_chart("A"),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(*recovery)],
        spot=95,
    ).begin()
    assert result.state is None and result.points == expected_points
    assert len(result.trace) == 2


def test_fumble_beyond_own_end_line_is_safety_without_recovery_roll() -> None:
    home = special_chart("H", punt=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=-15))
    result = procedure("punt", home, special_chart("A"), [OffensiveRoll(1, 0, 0)], spot=95).begin()
    assert result.points == (0, 2) and len(result.trace) == 1


def test_fumble_beyond_defensive_end_line_uses_white_faces_for_live_depth() -> None:
    home = replace(
        special_chart("H", punt=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=30)),
        recovery_range=range(10, 27),
    )
    play = procedure(
        "punt",
        home,
        special_chart("A", interception_return=yards(4)),
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(3, 2, 3),
            OffensiveRoll(3, 0, 0),
            OffensiveRoll(1, 0, 0),
        ],
        spot=10,
    )
    pending = play.begin()
    assert [t.section for t in pending.trace] == [
        "punt",
        "recovery_end_zone_depth",
        "fumble_recovery",
    ]
    assert play.decide("kick:return").state == FieldState(Possession.AWAY, 80, 1, 10)


def test_safety_free_punt_uses_own_20_and_home_season_free_kick_touchback() -> None:
    play = SpecialTeamsPlay(
        "punt",
        FieldState(Possession.AWAY, 60, 1, 10),
        special_chart("K", punt=yards(95)),
        special_chart("R"),
        ScriptedDice([OffensiveRoll(1, 0, 0)]),
        home_season=2012,
        safety_free_kick=True,
    )
    assert play.begin().state == FieldState(Possession.HOME, 75, 1, 10)


def test_offsetting_kick_fouls_cancel_before_any_supplemental_distance_roll() -> None:
    from bowl_bound.models import VariableReference

    variable = NormalizedCell(
        ResultKind.VARIABLE_T2, provenance(), variable=VariableReference.T2, variable_multiplier=1
    )
    home = special_chart("H", punt=variable)
    home = with_roll(home, "punt", 10, penalty(PenaltyTeam.OFFENSE))
    home = with_roll(home, "punt", 11, penalty(PenaltyTeam.DEFENSE))
    result = procedure(
        "punt",
        home,
        special_chart("A"),
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(1, 2, 0),
        ],
    ).begin()
    assert result.outcome is SpecialTeamsOutcome.REPLAY
    assert result.state == FieldState(Possession.HOME, 65, 4, 8)
    assert len(result.trace) == 3


def test_multiple_return_penalties_are_not_added_and_declining_preserves_blank_result() -> None:
    away = special_chart("A", kickoff_return=NormalizedCell(ResultKind.NO_CHANGE, provenance()))
    away = with_roll(away, "kickoff_return", 10, penalty(PenaltyTeam.OFFENSE, 5))
    away = with_roll(away, "kickoff_return", 11, penalty(PenaltyTeam.OFFENSE, 10))
    play = procedure(
        "kickoff",
        special_chart("H", kickoff=yards(45)),
        away,
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(1, 2, 0),
        ],
    )
    pending = play.begin()
    assert [c.id for c in pending.choices] == ["kick:accept:0", "kick:accept:1", "kick:decline"]
    assert play.decide("kick:accept:1").state == FieldState(Possession.AWAY, 90, 1, 10)


def test_pre_snap_kick_penalty_is_not_optional_and_does_not_roll_a_kick_result() -> None:
    off_s = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S)
    )
    result = procedure(
        "punt",
        special_chart("H", punt=off_s),
        special_chart("A"),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0)],
    ).begin()
    assert not result.choices
    assert result.state == FieldState(Possession.HOME, 70, 4, 13)
    assert [t.section for t in result.trace] == ["punt", "kick_penalty_yardage"]


def test_punt_return_touchdown_has_six_points_and_touchdown_outcome() -> None:
    result = resolve_punt(
        FieldState(Possession.AWAY, 65, 4, 8),
        special_chart("K", punt=yards(40)),
        special_chart("R", punt_return=yards(75)),
        choice="return",
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)]),
    )
    assert result.outcome is SpecialTeamsOutcome.RETURN_TOUCHDOWN
    assert result.points == (6, 0) and result.state is None


def test_return_retreating_into_own_end_zone_is_a_safety() -> None:
    result = procedure(
        "kickoff",
        special_chart("K", kickoff=yards(60)),
        special_chart("R", kickoff_return=yards(-5)),
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 1, 0)],
    ).begin()
    assert result.outcome is SpecialTeamsOutcome.SAFETY and result.points == (2, 0)


def test_accepted_offensive_return_penalty_does_not_rescue_a_safety_at_own_goal() -> None:
    away = with_roll(
        special_chart("R", kickoff_return=yards(-5)),
        "kickoff_return",
        10,
        penalty(PenaltyTeam.OFFENSE),
    )
    play = procedure(
        "kickoff",
        special_chart("K", kickoff=yards(60)),
        away,
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
        ],
    )
    assert play.begin().choices
    result = play.decide("kick:accept:0")
    assert result.outcome is SpecialTeamsOutcome.SAFETY
    assert result.points == (2, 0) and result.state is None


def test_declining_defensive_return_penalty_preserves_the_return_touchdown() -> None:
    away = with_roll(
        special_chart("R", kickoff_return=yards(80)),
        "kickoff_return",
        10,
        penalty(PenaltyTeam.DEFENSE),
    )
    play = procedure(
        "kickoff",
        special_chart("K", kickoff=yards(45)),
        away,
        [
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
        ],
    )
    assert play.begin().points == (0, 0)
    # Basic VI-4(A): choose the result, rather than accepting penalty yardage.
    result = play.decide("kick:decline")
    assert result.points == (0, 6) and result.state is None


def test_field_goal_wrapper_uses_the_opponents_return_chart_after_a_block() -> None:
    kicking = replace(
        special_chart(
            "K", field_goal=NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=-5)
        ),
        recovery_range=range(10, 27),
    )
    result = resolve_field_goal(
        FieldState(Possession.HOME, 40, 4, 8),
        kicking,
        ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(3, 0, 0), OffensiveRoll(1, 1, 0)]),
        receiving=special_chart("R", interception_return=yards(9)),
    )
    assert result.state == FieldState(Possession.AWAY, 46, 1, 10)
    assert result.trace[-1].team_name == "R"
