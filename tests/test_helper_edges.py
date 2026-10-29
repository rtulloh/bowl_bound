"""CLI-043: helper work is bounded and terminal-only across public phases."""

import io
from dataclasses import replace
from fractions import Fraction
from itertools import product

import pytest

from bowl_bound.cli import TerminalGame
from bowl_bound.dice import BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.player_coaching import estimate_plays
from bowl_bound.sample_teams import sample_teams
from bowl_bound.save_game import SavedGame
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_cli_easy_helper import saved_facts
from tests.test_models import provenance


def terminal(
    *, mode: str = "drive", human: str = "home", clock: Clock | None = None, away_gain: int = 9
) -> TerminalGame:
    samples = sample_teams()
    home = replace(
        team_chart(
            "Home",
            season=2007,
            offense=-4,
            defense=0,
            plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=10)},
        ),
        special_teams=samples[0].special_teams,
    )
    away = replace(
        team_chart("Away", season=2007, offense=away_gain, defense=0),
        special_teams=samples[1].special_teams,
    )
    game = SavedGame.new(
        home,
        away,
        home_id="2007/home",
        away_id="2007/away",
        seed=7,
        coach_policy="easy-v1",
        mode=mode,
        clock=clock,
    )
    return TerminalGame(
        game,
        lambda key: home if key.endswith("home") else away,
        human_side=human,
        output=io.StringIO(),
    )


@pytest.mark.parametrize("enabled,expected", [(True, 1), (False, 0)])
def test_display_computes_advice_once_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
    expected: int,
) -> None:
    app = terminal()
    app.helper_enabled = enabled
    before = saved_facts(app.game)
    original = app.game.player_advice
    calls = []

    def advice(side: str) -> tuple[str, ...]:
        calls.append(side)
        return original(side)

    monkeypatch.setattr(app.game, "player_advice", advice)
    app.display()
    assert calls == ["home"] * expected
    assert "[Z]" in app.output.getvalue()
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("phase", ["opening", "kickoff", "required", "finished"])
def test_z_is_unavailable_outside_play_selection_without_analysis_or_saved_changes(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    app = terminal(mode="regulation" if phase in {"opening", "kickoff"} else "drive")
    if phase == "kickoff":
        app.game.decide("toss:receive")
    elif phase == "required":
        app.game.snap("9", "A")
        assert app.game.view().pending
    elif phase == "finished":
        app = terminal(mode="regulation", clock=Clock(4, 11), away_gain=100)
        app.game.decide("toss:receive")
        app.game.kick("kickoff")
        app.game.snap("1", "A")
        app.game.decide("conversion:kick")
        assert app.game.view().finished
    before = saved_facts(app.game)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("unavailable helper must not analyze charts")

    monkeypatch.setattr(app.game, "player_advice", forbidden)
    assert not app.command("Z")
    assert "play selection" in app.output.getvalue()
    app.display()
    assert "[Z]" not in app.output.getvalue()
    assert saved_facts(app.game) == before


def test_helper_remains_available_in_optional_runoff_window() -> None:
    app = terminal(mode="regulation", human="away")
    app.game.decide("toss:receive")
    app.game.kick("kickoff")
    app.game.snap("1", "A")
    assert app.game.view().clock_optional
    before = saved_facts(app.game)
    app.display()
    text = app.output.getvalue()
    assert "[Z]" in text and "Target:" in text
    assert not app.command("Z")
    assert saved_facts(app.game) == before


def test_human_away_offense_uses_away_chart_and_negative_home_mean_is_explicit() -> None:
    app = terminal(mode="regulation", human="away")
    app.game.decide("toss:receive")
    app.game.kick("kickoff")
    assert app.game.view().state.possession == "away"
    before = saved_facts(app.game)
    app.display()
    assert "average +9.0 yards" in app.output.getvalue()
    assert saved_facts(app.game) == before
    home = terminal()
    before = saved_facts(home.game)
    home.display()
    text = home.output.getvalue()
    assert "average -4.0 yards" in text
    assert "Numeric offensive cells only; conditional rates" in text
    assert "not full-engine conversion odds" in text and "success" not in text.lower()
    assert saved_facts(home.game) == before


def test_all_symbolic_rates_are_absent_and_sort_by_id_before_truncating() -> None:
    chart = team_chart(
        "Symbolic", plays={p: NormalizedCell(ResultKind.INCOMPLETE, provenance()) for p in Play}
    )
    estimates = estimate_plays(chart.offense, tuple("987654321"), down=1, distance=10)
    assert tuple(e.key for e in estimates) == ("1", "2", "3")
    assert all(
        e.coverage == 0
        and e.limited
        and e.average_yards is e.target_rate is e.positive_rate is None
        for e in estimates
    )


def test_more_than_three_numeric_plays_truncate_after_sorting_not_menu_order() -> None:
    chart = team_chart("Sorted", plays={p: yards(p.value) for p in Play})
    estimates = estimate_plays(chart.offense, tuple("123456789"), down=1, distance=10)
    assert tuple(e.key for e in estimates) == ("9", "8", "7")


@pytest.mark.parametrize("play", list(Play))
@pytest.mark.parametrize("down,target", [(1, 4), (2, 5), (3, 7), (4, 7)])
def test_every_play_target_and_positive_rate_matches_216_physical_faces(
    play: Play,
    down: int,
    target: int,
) -> None:
    chart = team_chart("Physical")
    rows = tuple(
        replace(row, cell=yards((row.roll + play.value) % 16 - 5))
        for row in chart.offense
        if row.play == play
    )
    values = [
        ((10 * b + a + c + play.value) % 16 - 5)
        for b, a, c in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    ]
    assert len(values) == 216
    (estimate,) = estimate_plays(rows, (str(play.value),), down=down, distance=7)
    assert estimate.coverage == 1 and estimate.target == target
    assert estimate.target_rate == Fraction(sum(v >= target for v in values), 216)
    assert estimate.positive_rate == Fraction(sum(v > 0 for v in values), 216)
    assert estimate.average_yards == Fraction(sum(values), 216)


@pytest.mark.parametrize(
    "run,passing,expected", [(100, -100, 0.2), (-100, 100, -0.2), (4, 4, 0.0), (6, 4, 0.1)]
)
def test_medium_category_bias_is_clamped(run: int, passing: int, expected: float) -> None:
    chart = team_chart("Bias", plays={p: yards(run if p.value <= 5 else passing) for p in Play})
    assert DifficultyCoach._run_bias(chart) == pytest.approx(expected)


@pytest.mark.parametrize(
    "symbolic",
    [tuple(Play), tuple(p for p in Play if p.value <= 5), tuple(p for p in Play if p.value >= 6)],
)
def test_medium_no_bias_when_either_category_has_no_numeric_evidence(
    symbolic: tuple[Play, ...],
) -> None:
    chart = team_chart(
        "Missing", plays={p: NormalizedCell(ResultKind.INCOMPLETE, provenance()) for p in symbolic}
    )
    assert DifficultyCoach._run_bias(chart) == 0.0
