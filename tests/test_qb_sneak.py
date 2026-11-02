"""Synthetic coverage for Advanced I-2 QB Sneak and its Wild Card interaction."""

from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    TeamChart,
)
from bowl_bound.normalization import chart_color_for_rgb
from bowl_bound.resolution import ChartResolutionError
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PlaySession
from bowl_bound.timing import Clock, duration
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_models import provenance


def colored_chart(color: tuple[int, int, int], *, cell: NormalizedCell | None = None) -> TeamChart:
    """Set only the selected Play 1 box color, keeping all fixtures synthetic."""
    source = cell or yards(9)
    chart = team_chart("Alpha Tech", plays={Play.ONE: source})
    return replace(
        chart,
        offense=tuple(
            replace(
                row,
                cell=replace(
                    row.cell,
                    provenance=replace(row.cell.provenance, rgb_color=color),
                    chart_color=chart_color_for_rgb(color),
                ),
            )
            if row.play is Play.ONE
            else row
            for row in chart.offense
        ),
    )


@pytest.mark.parametrize(
    ("color", "expected_yards", "expected_outcome"),
    [
        ((0, 255, 0), 1, "advance"),
        ((255, 255, 255), 0, "advance"),
        ((239, 255, 1), 0, "advance"),
    ],
)
def test_qb_sneak_uses_only_the_play_one_box_color_and_no_defensive_dice(
    color: tuple[int, int, int], expected_yards: int, expected_outcome: str
) -> None:
    home, away = default_teams()
    home = colored_chart(color)
    dice = ScriptedDice([OffensiveRoll(1, 2, 3)])
    session = PlaySession.new(home, away, seed=1)

    report = session.snap("Q", "A", dice=dice)

    assert report.supported and report.outcome == expected_outcome
    assert report.yards == expected_yards
    assert report.called_play == report.resolved_play == "QB Sneak"
    assert [(entry.section, entry.play, entry.cell) for entry in report.trace] == [
        ("offense", "Line Plunge", "9")
    ]
    assert session.view().state is not None
    assert session.view().state.yards_to_goal == 65 - expected_yards


def test_qb_sneak_ignores_the_chart_symbol_when_color_is_green() -> None:
    home, away = default_teams()
    home = colored_chart(
        (0, 255, 0), cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=30)
    )
    session = PlaySession.new(home, away, seed=1)

    report = session.snap("Q", "A", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.outcome == "advance" and report.yards == 1
    assert session.view().state is not None
    assert session.view().state.possession == "home"


def test_yellow_qb_sneak_penalty_token_is_source_evidence_not_a_timing_penalty() -> None:
    """A yellow box is a color-only Sneak result even when its imported token is PEN."""
    home, away = default_teams()
    token = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = colored_chart((239, 255, 1), cell=token)
    session = PlaySession.new(home, away, seed=1)

    report = session.snap("Q", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))

    assert report.outcome == "advance" and report.yards == 0
    assert report.timing.penalty is False
    assert duration(report.timing, Clock()) == 30
    assert report.state_after is not None and report.state_after.down == 2
    assert [entry.section for entry in report.trace] == ["offense"]


def test_qb_sneak_uses_normalized_color_without_reading_rgb_provenance() -> None:
    home, away = default_teams()
    home = colored_chart((0, 255, 0))
    home = replace(
        home,
        offense=tuple(
            replace(
                row,
                cell=replace(
                    row.cell,
                    provenance=replace(row.cell.provenance, rgb_color=(255, 0, 0)),
                ),
            )
            if row.play is Play.ONE
            else row
            for row in home.offense
        ),
    )
    session = PlaySession.new(home, away, seed=1)

    report = session.snap("Q", "A", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.supported and report.yards == 1


def test_qb_sneak_red_box_fumbles_at_the_line_and_uses_normal_recovery() -> None:
    home, away = default_teams()
    fumble_token = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=8)
    home = colored_chart((255, 0, 0), cell=fumble_token)
    home = replace(home, recovery_range=range(10, 20))
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([OffensiveRoll(1, 2, 3), OffensiveRoll(1, 2, 2)])

    report = session.snap("Q", "A", dice=dice)

    assert report.outcome == "offensive_recovery"
    assert report.yards == 0
    assert report.state_after is not None
    assert report.state_after.yards_to_goal == 65
    assert [entry.section for entry in report.trace] == ["offense", "fumble_recovery"]


def test_green_qb_sneak_can_score_at_the_goal_line() -> None:
    home, away = default_teams()
    home = colored_chart((0, 255, 0))
    session = PlaySession.new(home, away, seed=1, start_yards_to_goal=1)

    report = session.snap("Q", "A", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.outcome == "touchdown" and report.yards == 1
    assert session.view().score.home == 6
    assert session.view().pending is not None
    assert session.view().pending.chooser == "Alpha Tech"


def test_white_qb_sneak_on_fourth_and_one_turns_over_on_downs() -> None:
    home, away = default_teams()
    home = colored_chart((255, 255, 255))
    session = PlaySession.for_analysis(home, away, FieldState(Possession.HOME, 50, 4, 1))

    report = session.snap("Q", "A", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.outcome == "turnover_on_downs"
    assert report.state_after is not None and report.state_after.possession == "away"


def test_unrecognized_qb_sneak_box_color_fails_without_changing_state() -> None:
    home, away = default_teams()
    home = colored_chart((6, 8, 8))
    session = PlaySession.new(home, away, seed=1)
    before = session.view().state

    with pytest.raises(ChartResolutionError, match="recognized green, white, yellow, or red"):
        session.snap("Q", "A", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert session.view().state == before and session.view().log == ()


def test_correct_qb_sneak_wild_card_stops_the_play_without_any_dice() -> None:
    home, away = default_teams()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)

    report = session.snap("Q", "WCSNEAK", dice=ScriptedDice([]))

    assert report.supported and report.yards == 0
    assert report.outcome == "advance"
    assert report.called_play == report.resolved_play == "QB Sneak"
    assert report.trace == ()


def test_conditional_mismatched_wild_card_doubles_green_sneak_yardage() -> None:
    home, away = default_teams()
    home = colored_chart((0, 255, 0))
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)

    report = session.snap("Q", "WC1", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.supported and report.yards == 2
    assert report.trace[0].section == "offense"


def test_free_mismatched_wild_card_does_not_double_green_sneak_yardage() -> None:
    home, away = default_teams()
    home = colored_chart((0, 255, 0))
    session = PlaySession.new(home, away, seed=1, advanced_ii=True, away_privileges=("W",))

    report = session.snap("Q", "WC1", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.supported and report.yards == 1


def test_wrong_sneak_wild_card_against_play_one_uses_blank_defense_and_no_defensive_dice() -> None:
    home, away = default_teams()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)
    dice = ScriptedDice([OffensiveRoll(1, 2, 3)])

    report = session.snap("1", "WCSNEAK", dice=dice)

    assert report.supported and report.trace[0].section == "offense"
    assert report.yards == 8
    assert not any(entry.section == "defense" for entry in report.trace)


def test_advanced_ii_offers_qb_sneak_and_a_specific_sneak_wild_card() -> None:
    session = PlaySession.new(*default_teams(), seed=1, advanced_ii=True)

    view = session.view()

    assert any((action.key, action.label) == ("Q", "QB Sneak") for action in view.actions.offense)
    assert any(action.key == "WCSNEAK" for action in view.actions.defense)


def test_qb_sneak_save_replays_and_keeps_future_coached_calls_stable() -> None:
    home, away = default_teams()
    game = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=19,
        coach_seed=23,
        advanced_ii=True,
    )
    game.snap("Q", "A")
    text = dumps_game(game)
    charts = {"2026/alpha-tech": home, "2026/beta-state": away}

    restored = loads_game(text, charts.__getitem__)

    assert restored.view() == game.view()
    assert restored.snap("2", "A") == game.snap("2", "A")
