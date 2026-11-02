"""Synthetic tests for Bowl Bound Advanced I-1 Razzle-Dazzle."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.regulation import RegulationGame
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import InvalidDecisionError, PendingDecisionError, PlaySession
from bowl_bound.timing import Clock, duration
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_models import provenance
from tests.test_special_teams import special_chart

DEFENSIVE_LOW = OffensiveRoll(1, 2, 3)  # 15
OFFENSIVE_HIGH = OffensiveRoll(1, 3, 5)  # 18
TIED = OffensiveRoll(1, 2, 3)  # 15


def _cell_for(chart, play: Play, total: int):
    return next(row.cell for row in chart.offense if row.play is play and row.roll == total)


def _set_cell(chart, play: Play, total: int, cell):
    return replace(
        chart,
        offense=tuple(
            replace(row, cell=cell) if row.play is play and row.roll == total else row
            for row in chart.offense
        ),
    )


def _playtest_charts():
    home, away = default_teams()
    home = team_chart(
        "Alpha Tech",
        plays={
            Play.ONE: yards(2),
            Play.NINE: yards(7),
        },
    )
    return home, away


def test_razzle_dazzle_and_its_wild_card_are_offered_as_legal_actions() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)

    view = session.view()

    assert "RZDZ" in {action.key for action in view.actions.offense}
    assert "WCRZDZ" in {action.key for action in view.actions.defense}


def test_defender_who_rolls_lower_selects_any_nonpenalty_cell_at_either_total() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH])

    pending = session.snap("RZDZ", "A", dice=dice)

    assert pending.pending
    decision = session.view().pending
    assert decision is not None and decision.chooser == away.name
    assert [entry.cell for entry in pending.trace] == [
        "comparison total 15",
        "comparison total 18",
    ]
    assert {choice.id for choice in decision.choices} == {
        f"razzle:{play.value}:{total}" for play in Play for total in (15, 18)
    }


def test_defender_selected_offensive_chart_result_uses_its_play_and_original_roll() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0)])

    pending = session.snap("RZDZ", "A", dice=dice)
    assert pending.pending
    report = session.decide("razzle:9:18", dice=dice)

    assert report.supported and report.outcome == "advance" and report.yards == 9
    assert report.called_play == "Razzle-Dazzle"
    assert report.resolved_play == "Drop Back"
    assert [entry.section for entry in report.trace] == [
        "razzle_dazzle:defense_roll",
        "razzle_dazzle:offense_roll",
        "offense",
        "defense",
    ]
    assert report.trace[2].play == "Drop Back" and report.trace[2].cell == "7"
    assert report.trace[2].roll["total"] == 18
    assert report.trace[3].play == "Drop Back" and report.trace[3].cell == "2"


def test_offense_wins_ties_and_can_choose_only_from_the_lower_total() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([TIED, TIED])

    pending = session.snap("RZDZ", "A", dice=dice)

    assert pending.pending
    decision = session.view().pending
    assert decision is not None and decision.chooser == home.name
    assert {choice.id for choice in decision.choices} == {
        f"razzle:{play.value}:15" for play in Play
    }


def test_razzle_dazzle_labels_a_no_change_choice_as_zero_for_players() -> None:
    home, away = _playtest_charts()
    home = _set_cell(home, Play.TWO, 15, NormalizedCell(ResultKind.NO_CHANGE, provenance()))
    session = PlaySession.new(home, away, seed=1)

    session.snap("RZDZ", "A", dice=ScriptedDice([TIED, TIED]))

    decision = session.view().pending
    assert decision is not None
    choice = next(item for item in decision.choices if item.id == "razzle:2:15")
    assert choice.label == "Play 2, total 15: 0"


def test_exact_razzle_wild_card_ends_incomplete_without_any_dice() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)

    report = session.snap("RZDZ", "WCRZDZ", dice=ScriptedDice([]))

    assert report.supported and not report.pending
    assert report.outcome == "advance" and report.yards == 0
    assert report.statistics.kind.value == "incomplete"
    assert report.called_play == report.resolved_play == "Razzle-Dazzle"
    assert report.trace == ()


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (FieldState(Possession.HOME, 65, 1, 10), FieldState(Possession.HOME, 65, 2, 10)),
        (FieldState(Possession.HOME, 65, 2, 10), FieldState(Possession.HOME, 65, 3, 10)),
        (FieldState(Possession.HOME, 65, 3, 10), FieldState(Possession.HOME, 65, 4, 10)),
        (FieldState(Possession.HOME, 65, 4, 10), FieldState(Possession.AWAY, 35, 1, 10)),
    ],
)
def test_exact_razzle_wild_card_uses_the_normal_incomplete_transition(
    field: FieldState, expected: FieldState
) -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)
    session._field = field

    report = session.snap("RZDZ", "WCRZDZ", dice=ScriptedDice([]))

    assert report.outcome == ("turnover_on_downs" if field.down == 4 else "advance")
    assert session._field == expected
    assert report.state_after is not None
    assert report.state_after.possession == expected.possession.value
    assert report.state_after.down == expected.down
    assert report.statistics.kind.value == "incomplete"


def test_exact_razzle_wild_card_uses_incomplete_timing_in_regulation() -> None:
    home, away = _playtest_charts()
    home_kicks = special_chart("Alpha Tech", kickoff=yards(70), kickoff_return=yards(10))
    away_kicks = special_chart("Beta State", kickoff=yards(70), kickoff_return=yards(10))
    home = replace(home, season=2002, special_teams=home_kicks.special_teams)
    away = replace(away, season=2002, special_teams=away_kicks.special_teams)
    game = RegulationGame.new(home, away, seed=1, clock=Clock(1, 30), advanced_ii=True)
    game.decide("toss:receive")
    game.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    game.decide("kick:touchback")

    report = game.snap("RZDZ", "WCRZDZ", dice=ScriptedDice([]))

    assert report.timing.incomplete
    assert duration(report.timing, Clock(1, 30)) == 10
    assert game.view().state.down == 2


def test_exact_razzle_wild_card_save_replay_preserves_the_incomplete_transition() -> None:
    home, away = _playtest_charts()
    game = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=1,
        advanced_ii=True,
    )
    report = game.snap("RZDZ", "WCRZDZ")
    teams = {"2026/alpha-tech": home, "2026/beta-state": away}

    restored = loads_game(
        dumps_game(game), lambda team_id: teams[team_id], preserve_development_policy=True
    )

    assert report.state_after == game.view().state
    assert restored.view() == game.view()
    assert restored.snap("1", "A") == game.snap("1", "A")


def test_razzle_wild_card_is_incorrect_for_an_ordinary_play() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)

    report = session.snap("1", "WCRZDZ", dice=ScriptedDice([OffensiveRoll(1, 2, 3)]))

    assert report.supported and report.yards == 4
    assert report.defense.startswith("Conditional Wild Card: Razzle-Dazzle")
    assert not any(entry.section == "defense" for entry in report.trace)


def test_other_conditional_wild_card_is_wrong_and_doubles_selected_yards() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH])

    pending = session.snap("RZDZ", "WC1", dice=dice)
    assert pending.pending
    report = session.decide("razzle:1:18", dice=dice)

    assert report.supported and report.yards == 4
    assert not any(entry.section in {"defense", "advanced_defense"} for entry in report.trace)


def test_free_wild_card_is_still_wrong_against_razzle_without_doubling_yards() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True, away_privileges=("W",))
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH])

    pending = session.snap("RZDZ", "WC1", dice=dice)
    assert pending.pending
    report = session.decide("razzle:1:18", dice=dice)

    assert report.supported and report.yards == 2
    assert not any(entry.section in {"defense", "advanced_defense"} for entry in report.trace)


def test_conditional_run_defense_uses_selected_result_classification() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0)])

    pending = session.snap("RZDZ", "RUN", dice=dice)
    assert pending.pending
    report = session.decide("razzle:9:18", dice=dice)

    assert report.supported and report.yards == 14
    advanced = [entry for entry in report.trace if entry.section == "advanced_defense"]
    assert len(advanced) == 1 and advanced[0].play == "Drop Back"


def test_run_defense_treats_a_selected_sprint_out_as_a_pass() -> None:
    home, away = _playtest_charts()
    option = _cell_for(home, Play.FIVE, 18)
    option = replace(option, kind=ResultKind.SPRINT_OUT_PASS, yards=None)
    home = _set_cell(home, Play.FIVE, 18, option)
    session = PlaySession.new(home, away, seed=1, advanced_ii=True)
    option_roll = OffensiveRoll(2, 0, 1)  # 21
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0), option_roll])

    pending = session.snap("RZDZ", "RUN", dice=dice)
    assert pending.pending
    report = session.decide("razzle:5:18", dice=dice)

    assert report.supported and report.yards == 8
    assert report.resolved_play == "Sprint Out"
    assert [entry.cell for entry in report.trace if entry.section == "advanced_defense"] == [
        "blank"
    ]
    assert any(entry.section == "option" and entry.roll["total"] == 21 for entry in report.trace)


@pytest.mark.parametrize(
    ("kind", "section", "expected_yards"),
    [
        (ResultKind.BREAKAWAY, "supplemental:B", 6),
        (ResultKind.QUARTERBACK_RUN, "supplemental:QR", 6),
        (ResultKind.QUARTERBACK_TRAPPED, "supplemental:QT", 4),
    ],
)
def test_selected_breakaway_and_quarterback_results_use_their_supplemental_columns(
    kind: ResultKind, section: str, expected_yards: int
) -> None:
    home, away = _playtest_charts()
    original = _cell_for(home, Play.ONE, 18)
    cell = replace(original, kind=kind, yards=None)
    home = _set_cell(home, Play.ONE, 18, cell)
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice(
        [DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)]
    )

    pending = session.snap("RZDZ", "A", dice=dice)
    assert pending.pending
    report = session.decide("razzle:1:18", dice=dice)

    assert report.supported and report.yards == expected_yards
    assert any(entry.section == section for entry in report.trace)


def test_selected_fumble_uses_the_normal_turnover_recovery_procedure() -> None:
    home, away = _playtest_charts()
    fumble = replace(_cell_for(home, Play.ONE, 18), kind=ResultKind.FUMBLE, yards=3)
    home = _set_cell(home, Play.ONE, 18, fumble)
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice(
        [DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0), OffensiveRoll(1, 2, 3)]
    )

    pending = session.snap("RZDZ", "A", dice=dice)
    assert pending.pending
    report = session.decide("razzle:1:18", dice=dice)

    assert report.supported and report.outcome == "offensive_recovery"
    assert any(entry.section == "fumble_recovery" for entry in report.trace)


def test_only_penalty_cells_are_selectable_when_both_available_rows_are_penalties() -> None:
    home, away = _playtest_charts()
    foul = replace(
        _cell_for(home, Play.ONE, 15),
        kind=ResultKind.PENALTY,
        yards=None,
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    for play in Play:
        for total in (15, 18):
            cell = replace(
                foul,
                provenance=provenance(),
                penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
            )
            home = _set_cell(home, play, total, cell)
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice(
        [
            DEFENSIVE_LOW,
            OFFENSIVE_HIGH,
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),  # The ordinary penalty reroll uses Play 1.
        ]
    )

    pending = session.snap("RZDZ", "A", dice=dice)

    assert pending.pending
    decision = session.view().pending
    assert decision is not None
    assert len(decision.choices) == 18
    assert all(choice.id.startswith("razzle:") for choice in decision.choices)

    penalty = session.decide("razzle:1:15", dice=dice)

    assert penalty.pending and penalty.outcome == "penalty_pending"
    assert any(entry.section == "penalty_reroll" for entry in penalty.trace)


def test_nonpenalty_choices_exclude_penalty_cells_when_any_legal_result_exists() -> None:
    home, away = _playtest_charts()
    foul = replace(
        _cell_for(home, Play.ONE, 15),
        kind=ResultKind.PENALTY,
        yards=None,
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = _set_cell(home, Play.ONE, 15, foul)
    session = PlaySession.new(home, away, seed=1)

    pending = session.snap("RZDZ", "A", dice=ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH]))

    assert pending.pending
    decision = session.view().pending
    assert decision is not None
    assert "razzle:1:15" not in {choice.id for choice in decision.choices}


def test_save_replay_preserves_an_unresolved_razzle_choice() -> None:
    home, away = _playtest_charts()
    game = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/harbor-tech",
        seed=10,
        advanced_ii=True,
        dice=ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0)]),
    )

    report = game.snap("RZDZ", "A")
    assert report.pending
    teams = {"2026/alpha-tech": home, "2026/harbor-tech": away}
    resumed = loads_game(
        dumps_game(game), lambda team_id: teams[team_id], preserve_development_policy=True
    )

    assert resumed.view().pending == game.view().pending
    assert resumed.decide("razzle:9:18") == game.decide("razzle:9:18")


def test_invalid_razzle_choice_keeps_the_pending_choice_available() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH, DefensiveRoll(1, 0)])

    pending = session.snap("RZDZ", "A", dice=dice)
    assert pending.pending
    with pytest.raises(InvalidDecisionError, match="unknown Razzle-Dazzle result"):
        session.decide("razzle:10:18", dice=dice)

    assert session.view().pending is not None
    report = session.decide("razzle:9:18", dice=dice)
    assert report.supported and report.resolved_play == "Drop Back"


def test_pending_razzle_blocks_another_snap_with_a_clear_error() -> None:
    home, away = _playtest_charts()
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([DEFENSIVE_LOW, OFFENSIVE_HIGH])
    pending = session.snap("RZDZ", "A", dice=dice)
    before = session.view()

    assert pending.pending
    with pytest.raises(PendingDecisionError, match="engine decision is required"):
        session.snap("1", "A", dice=dice)

    assert session.view() == before
