"""Elected safeties follow Advanced Rule I-5 using synthetic games only."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, Play, ResultKind
from bowl_bound.regulation import RegulationGame
from bowl_bound.session import InvalidDecisionError
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def new_game(*, gain: int = 3, plays: dict | None = None) -> RegulationGame:
    charts = []
    for name in ("Home", "Away"):
        special = special_chart(
            name, kickoff=yards(70), kickoff_return=yards(10), punt=yards(40), field_goal=yards(40)
        )
        ordinary = team_chart(name, season=2002, offense=gain, defense=0, plays=plays)
        charts.append(replace(ordinary, special_teams=special.special_teams))
    return RegulationGame.new(
        *charts,
        seed=1,
        clock=Clock(),
        dice=ScriptedDice([OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]),
    )


def start_scrimmage(game: RegulationGame) -> None:
    game.decide("toss:receive")
    game.kick("kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    game.decide("kick:touchback")


def test_elected_safety_scores_and_schedules_a_free_kick_from_own_twenty() -> None:
    game = new_game()
    start_scrimmage(game)
    before = game.view()

    assert "elect_safety" in {action.key for action in before.game_actions}
    report = game.action("elect_safety")
    view = game.view()

    assert report is not None
    assert report.outcome == "safety"
    assert report.called_play == "Elected safety"
    assert report.trace == ()
    assert view.score.home == 0 and view.score.away == 2
    assert view.phase == "kickoff"
    assert view.state.possession == "home" and view.state.yards_to_goal == 80
    assert [action.key for action in view.actions.special] == ["kickoff"]
    assert view.clock.remaining == before.clock.remaining
    assert view.statistics.home.total_plays == view.statistics.away.total_plays == 0


def test_elected_safety_can_be_elected_before_a_fourth_down_play() -> None:
    game = new_game(gain=0)
    start_scrimmage(game)
    for _ in range(3):
        game.snap(
            "1",
            "A",
            dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]),
        )

    view = game.view()
    assert view.state.down == 4
    assert "elect_safety" in {action.key for action in view.game_actions}
    assert game.action("elect_safety").outcome == "safety"


def test_elected_safety_is_unavailable_while_the_ball_is_free() -> None:
    interception = NormalizedCell(
        ResultKind.INTERCEPTION,
        provenance(),
        yards=20,
    )
    game = new_game(plays={Play.ONE: interception})
    start_scrimmage(game)
    report = game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(1, 0, 0),
            ]
        ),
    )

    assert report.pending
    assert game.view().pending is not None
    assert "elect_safety" not in {action.key for action in game.view().game_actions}
    with pytest.raises(InvalidDecisionError):
        game.action("elect_safety")
