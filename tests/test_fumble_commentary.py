"""Fumble commentary comes from structured engine facts, not terminal prose parsing."""

import io
from dataclasses import asdict, replace

import pytest

from bowl_bound.cli import TerminalGame
from bowl_bound.dice import DefensiveRoll, DiceSequenceError, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, team_chart
from tests.test_models import provenance


@pytest.mark.parametrize(
    "recovery,team,spot,outcome",
    [
        (OffensiveRoll(3, 0, 0), "Beta State", "own 17", "defensive_recovery"),
        (OffensiveRoll(1, 2, 2), "Alpha Tech", "opponent 17", "offensive_recovery"),
    ],
)
def test_option_fumble_commentary_names_fumbler_recoverer_and_true_recovery_spot(
    recovery: OffensiveRoll,
    team: str,
    spot: str,
    outcome: str,
) -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=-4)
    home = replace(
        team_chart("Alpha Tech", plays={Play.FIVE: fumble}), recovery_range=range(10, 20)
    )
    away = team_chart("Beta State", defense=0)
    session = PlaySession.new(home, away, seed=1, start_yards_to_goal=13)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), recovery])
    report = session.snap("5", "B", dice=dice)
    assert report.outcome == outcome
    assert report.state_after.spot == spot
    assert report.yards == -4
    assert report.commentary.startswith(report.description)
    assert "Fumble by Alpha Tech!" in report.commentary
    assert f"{team} recovers at {spot}." in report.commentary
    before = asdict(session.view())
    commentary = report.commentary
    assert report.commentary == commentary
    assert ("★ TURNOVER!" in commentary) == (outcome == "defensive_recovery")
    assert asdict(session.view()) == before
    assert "commentary" not in asdict(report)
    assert [e.section for e in report.trace] == ["offense", "defense", "fumble_recovery"]
    with pytest.raises(DiceSequenceError):
        dice.offensive()  # No invented extra recovery roll.


def test_an_interception_return_is_not_falsely_described_as_a_fumble() -> None:
    home, away = default_teams()
    session = PlaySession.new(home, away, seed=1)
    dice = ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)])
    session.snap("9", "A", dice=dice)
    report = session.decide("interception:return")
    assert report.outcome == "defensive_recovery"
    assert not any(e.section == "fumble_recovery" for e in report.trace)
    assert "INTERCEPTED!" in report.commentary
    assert (
        f"{report.state_after.possession_name} ball at {report.state_after.spot}."
        in report.commentary
    )
    assert "TURNOVER!" in report.commentary
    assert "fumble" not in report.commentary.lower()


def test_terminal_result_and_log_use_engine_commentary_without_altering_saved_reports() -> None:
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=-4)
    home = replace(
        team_chart("Alpha Tech", plays={Play.FIVE: fumble}), recovery_range=range(10, 20)
    )
    away = team_chart("Beta State", defense=0)
    game = SavedGame.new(
        home, away, seed=7, mode="drive", home_id="2026/alpha-tech", away_id="2026/beta-state"
    )

    def loader(key: str) -> TeamChart:
        return home if key == "2026/alpha-tech" else away

    app = TerminalGame(game, loader, human_side="home", output=io.StringIO())
    assert app.command("5")
    report = game.view().log[-1]
    assert any(e.section == "fumble_recovery" for e in report.trace)
    assert "Fumble by Alpha Tech!" in app.output.getvalue()
    stored = asdict(report)
    assert "Fumble by Alpha Tech!" not in stored["description"]
    saved = dumps_game(game)
    restored = loads_game(saved, loader)
    assert asdict(restored.view()) == asdict(game.view())
    app.output = io.StringIO()
    assert not app.command("log")
    assert "Fumble by Alpha Tech!" in app.output.getvalue()
    assert asdict(report) == stored


def test_end_zone_fumble_decision_and_return_do_not_invent_a_recovery_spot() -> None:
    from tests.test_session_turnovers import return_chart

    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=70)
    home = replace(team_chart("Alpha Tech", plays={Play.ONE: fumble}), recovery_range=range(10, 20))
    away = return_chart("Beta State", NormalizedCell(ResultKind.YARDS, provenance(), yards=12))
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(3, 4, 3),
            OffensiveRoll(1, 1, 0),
        ]
    )
    session = PlaySession.new(home, away, seed=1)
    pending = session.snap("1", "A", dice=dice)
    assert pending.pending and "Fumble by Alpha Tech!" in pending.commentary
    assert "recovers at" not in pending.commentary and "TURNOVER!" not in pending.commentary
    returned = session.decide("end_zone:return")
    assert returned.state_after.spot == "own 7"
    assert "Fumble by Alpha Tech!" in returned.commentary
    assert "Beta State ball at own 7." in returned.commentary
    assert "recovers at own 7" not in returned.commentary
    assert "★ TURNOVER!" in returned.commentary
