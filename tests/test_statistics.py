"""College offensive statistics from synthetic, real engine sequences."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    VariableReference,
)
from bowl_bound.session import PlaySession
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_overtime import miss_series, overtime_game, start_overtime
from tests.test_regulation import snap
from tests.test_special_teams import special_chart


def dice(*extra: OffensiveRoll) -> ScriptedDice:
    return ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 1), *extra])


def session_for(
    cell: NormalizedCell,
    play: Play = Play.ONE,
    *,
    spot: int = 65,
    supplemental: NormalizedCell | None = None,
) -> PlaySession:
    home = team_chart("Home", season=2002, offense=0, defense=0, plays={play: cell})
    if supplemental:
        home = replace(
            home, supplemental=tuple(replace(r, cell=supplemental) for r in home.supplemental)
        )
    away = team_chart("Away", season=2002, defense=0)
    away = replace(
        away, special_teams=special_chart("Away", interception_return=yards(20)).special_teams
    )
    return PlaySession.new(home, away, seed=1, start_yards_to_goal=spot)


@pytest.mark.parametrize("play", list(Play))
def test_plain_yardage_uses_resolved_run_or_pass(play: Play) -> None:
    game = session_for(yards(6), play)
    report = game.snap(str(play.value), "A", dice=dice())
    stats = game.view().statistics.home
    assert stats.rushing_attempts == (1 if play.value <= 5 else 0)
    assert stats.rushing_yards == (6 if play.value <= 5 else 0)
    assert stats.passing_attempts == stats.completions == (1 if play.value >= 6 else 0)
    assert stats.passing_yards == (6 if play.value >= 6 else 0)
    assert stats.total_plays == 1 and stats.total_yards == 6
    assert report.statistics.yards == 6
    assert game.view().statistics.away.total_plays == 0


@pytest.mark.parametrize("kind", [ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED])
def test_qr_and_qt_losses_are_college_rushing_not_passing(kind: ResultKind) -> None:
    game = session_for(NormalizedCell(kind, provenance()), Play.NINE, supplemental=yards(-7))
    report = game.snap("9", "A", dice=dice(OffensiveRoll(2, 0, 0)))
    stats = game.view().statistics.home
    assert stats.rushing_attempts == 1 and stats.rushing_yards == -7
    assert stats.passing_attempts == stats.passing_yards == stats.completions == 0
    assert stats.sacks_taken == (1 if kind is ResultKind.QUARTERBACK_TRAPPED else 0)
    assert stats.sack_yards_lost == (7 if kind is ResultKind.QUARTERBACK_TRAPPED else 0)
    assert report.called_play == report.resolved_play == "Drop Back"


def test_negative_numeric_pass_is_a_completion_not_an_invented_sack() -> None:
    game = session_for(yards(-4), Play.SIX)
    game.snap("6", "A", dice=dice())
    stats = game.view().statistics.home
    assert stats.completions == stats.passing_attempts == 1
    assert stats.passing_yards == -4 and stats.sacks_taken == stats.rushing_attempts == 0


@pytest.mark.parametrize("kind", [ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS])
def test_option_to_pass_and_breakaway_preserve_statistical_classification(kind: ResultKind) -> None:
    game = session_for(NormalizedCell(kind, provenance()), Play.FIVE)
    home = game._charts[next(iter(game._charts))]
    game._charts[next(iter(game._charts))] = replace(
        home,
        offense=tuple(
            replace(r, cell=NormalizedCell(ResultKind.BREAKAWAY, provenance()))
            if r.play in {Play.SEVEN, Play.EIGHT}
            else r
            for r in home.offense
        ),
        supplemental=tuple(replace(r, cell=yards(12)) for r in home.supplemental),
    )
    report = game.snap("5", "A", dice=dice(OffensiveRoll(2, 0, 0), OffensiveRoll(2, 0, 0)))
    stats = game.view().statistics.home
    assert report.called_play == "Option" and report.resolved_play != "Option"
    assert stats.passing_attempts == stats.completions == 1 and stats.passing_yards == 12
    assert stats.rushing_attempts == 0


@pytest.mark.parametrize("gain,spot,expected", [(50, 8, 8), (-100, 95, -5), (0, 65, 0)])
def test_yards_are_clipped_at_goal_lines_not_chart_overshoot(
    gain: int, spot: int, expected: int
) -> None:
    game = session_for(yards(gain), spot=spot)
    game.snap("1", "A", dice=dice())
    stats = game.view().statistics.home
    assert stats.rushing_yards == expected and stats.total_yards == expected
    assert stats.rushing_touchdowns == (1 if gain > 0 else 0)


def test_pending_interception_does_not_count_until_decided_and_return_is_not_offense() -> None:
    game = session_for(NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15), Play.NINE)
    game.snap("9", "A", dice=dice(OffensiveRoll(1, 0, 0)))
    assert game.view().statistics.home.total_plays == 0
    game.decide("interception:return")
    stats = game.view().statistics
    assert stats.home.passing_attempts == stats.home.interceptions == 1
    assert stats.home.completions == stats.home.passing_yards == 0
    assert stats.away.total_yards == stats.away.total_plays == 0
    assert game.view().statistics == stats  # Viewing cannot double-count.


def test_declined_interception_counts_an_incomplete_pass() -> None:
    game = session_for(NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15), Play.NINE)
    game.snap("9", "A", dice=dice())
    game.decide("interception:decline")
    stats = game.view().statistics.home
    assert stats.passing_attempts == 1 and stats.interceptions == stats.completions == 0


@pytest.mark.parametrize(
    "choice,counted", [("accept:0:previous", False), ("accept:0:end", True), ("decline", True)]
)
def test_penalty_enforcement_not_penalty_presence_controls_offensive_credit(
    choice: str, counted: bool
) -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
    )
    game = session_for(foul)
    home = game._charts[next(iter(game._charts))]
    game._charts[next(iter(game._charts))] = replace(
        home, offense=tuple(replace(r, cell=yards(8)) if r.roll != 10 else r for r in home.offense)
    )
    game.snap("1", "A", dice=dice(OffensiveRoll(2, 0, 0)))
    assert game.view().statistics.home.total_plays == 0
    game.decide(choice)
    stats = game.view().statistics.home
    assert stats.rushing_attempts == int(counted)
    assert stats.rushing_yards == (8 if counted else 0)
    assert game.view().state.yards_to_goal != 57 or choice == "decline"


def test_spike_and_kneel_are_team_attempts_without_sacks() -> None:
    game = session_for(yards(0))
    game.automatic("kneel")
    game.automatic("spike")
    stats = game.view().statistics.home
    assert stats.rushing_attempts == stats.passing_attempts == 1
    assert stats.rushing_yards == -2 and stats.passing_yards == 0
    assert stats.completions == stats.sacks_taken == 0
    assert stats.total_plays == 2 and stats.total_yards == -2


@pytest.mark.parametrize("variable", [False, True])
def test_fumble_credits_scrimmage_gain_not_defensive_return(variable: bool) -> None:
    cell = (
        NormalizedCell(
            ResultKind.FUMBLE, provenance(), variable=VariableReference.DS, variable_multiplier=1
        )
        if variable
        else NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5)
    )
    game = session_for(cell)
    extra = [OffensiveRoll(1, 0, 4)] if variable else []  # direct sum = 5
    report = game.snap("1", "A", dice=dice(*extra, OffensiveRoll(3, 3, 4), OffensiveRoll(1, 0, 0)))
    assert any(entry.section == "turnover_return" for entry in report.trace)
    stats = game.view().statistics
    assert stats.home.rushing_attempts == 1 and stats.home.rushing_yards == 5
    assert stats.away.total_yards == stats.away.total_plays == 0


def test_own_fumble_advance_remains_in_original_play_category() -> None:
    game = session_for(NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5), Play.SIX)
    home = game._charts[next(iter(game._charts))]
    game._charts[next(iter(game._charts))] = replace(
        home, special_teams=special_chart("Home", interception_return=yards(10)).special_teams
    )
    game.snap("6", "A", dice=dice(OffensiveRoll(1, 3, 4), OffensiveRoll(1, 0, 0)))
    stats = game.view().statistics.home
    assert stats.completions == stats.passing_attempts == 1
    assert stats.passing_yards == 15 and stats.total_yards == 15


def test_conversions_including_paired_overtime_tries_are_not_offensive_stats() -> None:
    game = overtime_game(2021)
    start_overtime(game)
    for _ in range(4):
        miss_series(game)
    before = game.view().statistics
    snap(game)
    snap(game, "3")
    assert game.view().finished and game.view().statistics == before


def test_full_series_overtime_counts_but_pat_and_two_point_try_do_not() -> None:
    game = overtime_game()
    before = game.view().statistics
    start_overtime(game)
    snap(game)
    after = game.view().statistics
    assert after.home.total_plays == before.home.total_plays + 1
    assert after.home.rushing_yards == before.home.rushing_yards + 25
    game.decide("conversion:two")
    snap(game)
    assert game.view().statistics == after


def test_complete_regulation_reconciles_independent_scripted_team_totals() -> None:
    from tests.test_regulation import kickoff, new_game

    game = new_game(gain=0, season=1994)
    kickoff(game)
    snaps = 0
    for _ in range(400):
        view = game.view()
        if view.finished:
            break
        if view.pending:
            game.decide("clock:runoff")
        elif view.phase == "kickoff":
            game.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
            game.decide("kick:touchback")
        else:
            snap(game, "1" if view.state.down <= 2 else "6")
            snaps += 1
    else:
        pytest.fail("scripted regulation did not finish")
    final = game.view()
    assert snaps == 144  # Each four-down drive is two 30-second runs and two 20-second passes.
    for team in (final.statistics.home, final.statistics.away):
        assert team.rushing_attempts == 36 and team.rushing_yards == 0
        assert team.passing_attempts == team.completions == 36
        assert team.passing_yards == team.interceptions == team.sacks_taken == 0
        assert team.total_plays == 72 and team.total_yards == 0
    assert len(final.log) == 146  # 144 snaps plus two kickoffs, not 146 offensive plays.
    assert final.score.home == final.score.away == 0
    for quarter in range(1, 5):
        charges = [charge for charge in final.timing_log if charge.quarter == quarter]
        assert sum(c.before - c.after for c in charges) == 900


def test_full_feature_variable_play_contributes_resolved_credit() -> None:
    game = session_for(
        NormalizedCell(
            ResultKind.VARIABLE_DS,
            provenance(),
            variable=VariableReference.DS,
            variable_multiplier=1,
        )
    )
    report = game.snap("1", "A", dice=dice(OffensiveRoll(3, 2, 4)))
    assert report.supported and report.statistics.yards == 9
    assert game.view().statistics.home.total_plays == 1
    assert game.view().statistics.home.rushing_yards == 9


def test_pat_and_special_teams_do_not_contribute_offensive_credit() -> None:
    game = session_for(yards(100))
    game.snap("1", "A", dice=dice())
    before = game.view().statistics
    game.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert game.view().statistics == before
    game = session_for(yards(0))
    before = game.view().statistics
    game.kick("punt", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    if game.view().pending:
        game.decide("kick:fair_catch")
    assert game.view().statistics == before


def test_double_turnover_does_not_turn_returns_into_original_offensive_yards() -> None:
    game = session_for(NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5))
    away = game._charts[list(game._charts)[1]]
    game._charts[list(game._charts)[1]] = replace(
        away,
        special_teams=special_chart(
            "Away", interception_return=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=8)
        ).special_teams,
    )
    game.snap(
        "1", "A", dice=dice(OffensiveRoll(3, 3, 4), OffensiveRoll(1, 0, 0), OffensiveRoll(3, 0, 0))
    )
    assert game.view().state.possession == "home"
    assert game.view().statistics.home.rushing_yards == 5
    assert game.view().statistics.home.total_plays == 1
    assert game.view().statistics.away.total_plays == 0


@pytest.mark.parametrize(
    "choice,advance,expected",
    [
        ("return:accept", 10, 15),
        ("return:decline", 10, 15),
        ("return:accept", 40, 35),
        ("return:decline", 40, 45),
    ],
)
def test_own_recovery_return_penalty_does_not_become_scrimmage_yards(
    choice: str, advance: int, expected: int
) -> None:
    game = session_for(NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5))
    home = game._charts[next(iter(game._charts))]
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    kicks = special_chart("Home", interception_return=yards(advance))
    game._charts[next(iter(game._charts))] = replace(
        home,
        special_teams=tuple(
            replace(r, cell=foul) if r.column.value == "interception_return" and r.roll == 10 else r
            for r in kicks.special_teams
        ),
    )
    game.snap(
        "1", "A", dice=dice(OffensiveRoll(1, 3, 4), OffensiveRoll(1, 0, 0), OffensiveRoll(2, 0, 0))
    )
    assert game.view().statistics.home.total_plays == 0
    game.decide(choice)
    assert game.view().statistics.home.rushing_yards == expected
    assert game.view().statistics.home.rushing_attempts == 1


def test_hurried_bad_snap_on_called_pass_is_team_rush_not_completion_or_sack() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S)
    )
    game = session_for(foul, Play.NINE)
    game.snap("9", "A", hurried=True, dice=dice(OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)))
    stats = game.view().statistics.home
    assert stats.rushing_attempts == 1 and stats.rushing_yards == -2
    assert stats.passing_attempts == stats.completions == stats.sacks_taken == 0


@pytest.mark.parametrize("gain", [0, 6])
def test_qt_without_loss_is_a_rush_not_a_sack(gain: int) -> None:
    game = session_for(
        NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()),
        Play.NINE,
        supplemental=yards(gain),
    )
    game.snap("9", "A", dice=dice(OffensiveRoll(2, 0, 0)))
    stats = game.view().statistics.home
    assert stats.rushing_attempts == 1 and stats.rushing_yards == gain
    assert stats.sacks_taken == stats.passing_attempts == 0


@pytest.mark.parametrize("printed", [False, True])
def test_passing_touchdown_measures_to_goal_and_preserves_unconsumed_dice(printed: bool) -> None:
    cell = NormalizedCell(ResultKind.TOUCHDOWN, provenance()) if printed else yards(100)
    game = session_for(cell, Play.SIX, spot=8)
    sentinel = OffensiveRoll(3, 4, 5)
    source = dice(sentinel)
    game.snap("6", "A", dice=source)
    stats = game.view().statistics.home
    assert stats.passing_touchdowns == stats.completions == stats.passing_attempts == 1
    assert stats.passing_yards == stats.total_yards == 8
    assert source.offensive() == sentinel


def test_own_fumble_advance_touchdown_retains_offensive_credit() -> None:
    game = session_for(NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5), spot=20)
    home = game._charts[next(iter(game._charts))]
    game._charts[next(iter(game._charts))] = replace(
        home,
        special_teams=special_chart(
            "Home", interception_return=NormalizedCell(ResultKind.TOUCHDOWN, provenance())
        ).special_teams,
    )
    game.snap("1", "A", dice=dice(OffensiveRoll(1, 3, 4), OffensiveRoll(1, 0, 0)))
    stats = game.view().statistics.home
    assert stats.rushing_yards == 20 and stats.rushing_touchdowns == 1


def test_reacquisition_touchdown_is_not_an_offensive_touchdown() -> None:
    game = session_for(NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5))
    home, away = game._charts.values()
    game._charts = {
        team: replace(
            chart, special_teams=special_chart(chart.name, interception_return=cell).special_teams
        )
        for team, chart, cell in (
            (next(iter(game._charts)), home, NormalizedCell(ResultKind.TOUCHDOWN, provenance())),
            (list(game._charts)[1], away, NormalizedCell(ResultKind.FUMBLE, provenance(), yards=8)),
        )
    }
    game.snap(
        "1",
        "A",
        dice=dice(
            OffensiveRoll(3, 3, 4),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(3, 3, 4),
            OffensiveRoll(1, 0, 0),
        ),
    )
    assert game.view().score.home == 6
    stats = game.view().statistics.home
    assert stats.total_plays == 1 and stats.rushing_yards == 5
    assert stats.rushing_touchdowns == 0


def test_complete_scoring_game_reconciles_nonzero_offense_and_conversion_exclusions() -> None:
    from tests.test_regulation import kickoff, new_game

    game = new_game(season=1994, plays={Play.ONE: yards(3), Play.SIX: yards(100)})
    kickoff(game)
    counts = {"home": [0, 0], "away": [0, 0]}
    for _ in range(2000):
        view = game.view()
        if view.finished:
            break
        if view.phase == "conversion_choice":
            game.decide("conversion:kick", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
        elif view.pending:
            game.decide("clock:runoff")
        elif view.phase == "kickoff":
            game.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
            game.decide("kick:touchback")
        else:
            team = view.state.possession
            if view.state.yards_to_goal == 77:
                snap(game, "6")
                counts[team][1] += 1
            else:
                assert view.state.yards_to_goal == 80
                snap(game, "1")
                counts[team][0] += 1
    else:
        pytest.fail("scripted scoring regulation did not finish")
    final = game.view()
    for name in ("home", "away"):
        rushes, passes = counts[name]
        assert rushes > 0 and passes > 0
        stats = getattr(final.statistics, name)
        assert stats.rushing_attempts == rushes and stats.rushing_yards == 3 * rushes
        assert stats.completions == stats.passing_attempts == stats.passing_touchdowns == passes
        assert stats.passing_yards == 77 * passes
        assert stats.total_plays == rushes + passes
        assert stats.total_yards == 3 * rushes + 77 * passes
        assert getattr(final.score, name) == 7 * passes
        assert stats.rushing_touchdowns == stats.sacks_taken == stats.interceptions == 0
    for quarter in range(1, 5):
        assert sum(c.before - c.after for c in final.timing_log if c.quarter == quarter) == 900


def test_penalty_reroll_does_not_inherit_discarded_qt_branch() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
    )
    game = session_for(
        NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()), Play.NINE, supplemental=foul
    )
    home = game._charts[next(iter(game._charts))]
    game._charts[next(iter(game._charts))] = replace(
        home, offense=tuple(replace(r, cell=yards(-4)) if r.roll != 10 else r for r in home.offense)
    )
    game.snap("9", "A", dice=dice(OffensiveRoll(2, 0, 0), OffensiveRoll(3, 0, 0)))
    game.decide("decline")
    stats = game.view().statistics.home
    assert stats.passing_attempts == stats.completions == 1
    assert stats.passing_yards == -4
    assert stats.rushing_attempts == stats.sacks_taken == 0
