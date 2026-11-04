"""CLI-071: full-time recap uses committed synthetic game facts exactly once."""

import io
import json
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame
from bowl_bound.models import NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_conversion_presentation import conversion_game
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def new_game(*, season: int = 1994, quarter: int = 1, remaining: int = 20) -> SavedGame:
    charts = [
        replace(
            team_chart(
                name,
                season=season,
                offense=0,
                defense=0,
                plays={
                    Play.TWO: yards(100),
                    Play.THREE: NormalizedCell(ResultKind.INCOMPLETE, provenance()),
                },
            ),
            special_teams=special_chart(
                name, kickoff=yards(100), field_goal=yards(40)
            ).special_teams,
            pat_outcomes=tuple(replace(row, good=True) for row in team_chart(name).pat_outcomes),
        )
        for name in ("Fictional Home University", "Fictional Away College")
    ]
    game = SavedGame.new(
        *charts,
        home_id=f"{season}/home",
        away_id=f"{season}/away",
        seed=7,
        coach_seed=31,
        difficulty="hard",
        mode="regulation",
        clock=Clock(quarter, remaining),
    )
    winner = game.view().pending.chooser_side
    game.decide("toss:receive" if winner == "home" else "toss:kick")
    return game


def loader(game: SavedGame) -> Callable[[str], TeamChart]:
    return lambda key: game._charts[key.rsplit("/", 1)[-1]]


def regulation_final() -> tuple[SavedGame, dict[str, list[int]]]:
    game = new_game()
    expected = {side: [0] * 4 for side in ("home", "away")}
    scored: set[int] = set()
    for _ in range(250):
        view = game.view()
        if view.finished:
            return game, expected
        if view.review:
            game.action("review:continue")
        elif view.pending and view.pending.choices[0].id.startswith("kick:"):
            game.decide("kick:touchback")
        elif view.phase == "kickoff":
            game.kick("kickoff")
        elif view.phase == "clock_choice":
            game.decide("clock:runoff")
        elif view.phase == "conversion_choice":
            quarter = view.clock.quarter
            side = view.pending.chooser_side
            if quarter == 4:
                game.decide("conversion:two")
                game.snap("3", "A")
            else:
                game.decide("conversion:kick")
                expected[side][quarter - 1] += 1
        else:
            quarter = view.clock.quarter
            if quarter not in scored:
                expected[view.state.possession][quarter - 1] += 6
                scored.add(quarter)
                game.snap("2", "A")
            else:
                game.snap("1", "A")
    pytest.fail("synthetic regulation did not finish")


def overtime_final() -> SavedGame:
    game = new_game(season=2002, quarter=4)
    game.kick("kickoff")
    game.snap("1", "A")
    game.decide("clock:runoff")
    winner = game.view().pending.chooser_side
    game.decide("ot:offense" if winner == "home" else "ot:defense")
    for _ in range(8):
        game.snap("3", "A")
    assert game.view().overtime.round_number == 2
    assert game.view().state.possession == "away"
    game.kick("field_goal")
    for _ in range(4):
        game.snap("3", "A")
    assert game.view().finished
    return game


def assert_box(text: str, game: SavedGame, expected: dict[str, list[int]]) -> None:
    view = game.view()
    assert re.search(r"\|\s+FINAL STATS\s+\|", text)
    periods = "Q1 Q2 Q3 Q4" + (" OT1 OT2" if view.overtime else "")
    header = r"\|\s+TEAM\s+\|\s+" + r"\s+".join(periods.split())
    assert re.search(header + r"\s+\|\s+TOTAL\s+\|", text)
    for side, name in (("away", view.away), ("home", view.home)):
        values = expected[side]
        row = r"\|\s+" + re.escape(name) + r"\s+\|\s+"
        row += r"\s+".join(map(str, values))
        assert re.search(row + rf"\s+\|\s+{sum(values)}\s+\|", text)
    assert text.index(view.away) < text.index(view.home)
    assert text.index("FINAL STATS") < text.index("SCORING SUMMARY") < text.index("TEAM STATISTICS")
    for event in view.scoring:
        assert f"Play {event.play_number}: {event.team}" in text
    for row in view.statistics.rows:
        pattern = r"\|\s+" + re.escape(row.label) + r"\s+\|\s+"
        pattern += re.escape(row.away) + r"\s+\|\s+" + re.escape(row.home) + r"\s+\|"
        assert re.search(pattern, text)
    boxed = [line for line in text.splitlines() if line.startswith(("+", "|"))]
    assert len({len(line) for line in boxed}) == 1
    assert "start the second half" not in text


@pytest.mark.parametrize("compact", [False, True])
def test_final_prints_complete_box_once_without_changing_game(compact: bool) -> None:
    game, expected = regulation_final()
    before = json.loads(dumps_game(game))
    output = io.StringIO()
    terminal = TerminalGame(game, loader(game), compact=compact, trace=True, output=output)
    terminal.advance_computer()
    terminal.display()
    assert_box(output.getvalue(), game, expected)
    assert "two-point conversion +2" not in output.getvalue()
    terminal.display()
    terminal.command("status")
    terminal.command("/")
    terminal.command("?")
    assert output.getvalue().count("FINAL STATS") == 1
    assert output.getvalue().count("Hard coach learned these committed calls") == 1
    after = json.loads(dumps_game(game))
    # Each export stamps its own time and integrity; all game facts must match.
    for data in (before, after):
        data.pop("saved_at")
        data.pop("integrity")
    assert after == before


def test_loading_final_preserves_all_periods_and_includes_overtime_rounds() -> None:
    game = overtime_final()
    restored = loads_game(dumps_game(game), loader(game))
    expected = {"home": [0, 0, 0, 0, 0, 0], "away": [0, 0, 0, 0, 0, 3]}
    output = io.StringIO()
    terminal = TerminalGame(restored, loader(game), output=output)
    terminal.display()
    assert_box(output.getvalue(), restored, expected)
    assert "field goal +3" in output.getvalue()
    assert restored.final_recap() == game.final_recap()


def test_successful_load_resets_automatic_recap_for_the_replacement_game(tmp_path: Path) -> None:
    game, expected = regulation_final()
    output = io.StringIO()
    terminal = TerminalGame(game, loader(game), output=output)
    terminal.display()
    path = tmp_path / "finished.json"
    assert not terminal.command(f"save {path}")
    terminal.display()
    assert output.getvalue().count("FINAL STATS") == 1
    assert terminal.command(f"load {path}")
    terminal.display()
    assert output.getvalue().count("FINAL STATS") == 2
    assert output.getvalue().count("Hard coach learned these committed calls") == 2
    assert_box(output.getvalue(), terminal.game, expected)


def test_live_and_pending_final_conversion_do_not_print_final_summary() -> None:
    game = new_game(quarter=4, remaining=10)
    output = io.StringIO()
    terminal = TerminalGame(game, loader(game), output=output)
    terminal.display()
    game.kick("kickoff")
    game.snap("2", "A")
    assert game.view().clock.remaining == 0
    assert game.view().phase == "conversion_choice"
    terminal.display()
    assert "FINAL STATS" not in output.getvalue()
    assert game.final_recap() is None


@pytest.mark.parametrize("good", [False, True])
def test_final_includes_the_last_untimed_conversion(good: bool) -> None:
    game = conversion_game("away", good=good, clock=Clock(4, 20))
    assert game.view().clock.remaining == 0 and not game.view().finished
    game.decide("conversion:two")
    game.snap("2", "A")
    assert game.view().finished
    recap = game.final_recap()
    assert recap.away.periods == (0, 0, 0, 8 if good else 6)
    assert recap.away.total == (8 if good else 6)
    assert any("two-point conversion +2" in line for line in recap.scoring) is good


def test_scoreless_final_has_explicit_no_scoring_text() -> None:
    game = new_game(quarter=4)
    game.kick("kickoff")
    game.snap("1", "A")
    game.decide("clock:runoff")
    output = io.StringIO()
    terminal = TerminalGame(game, loader(game), output=output)
    terminal.display()
    assert_box(output.getvalue(), game, {"home": [0] * 4, "away": [0] * 4})
    assert "No scoring in the game." in output.getvalue()
