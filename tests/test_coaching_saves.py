"""Computer execution shares game locks and survives save/replay without hidden-input leaks."""

import json

import pytest

from bowl_bound.sample_teams import sample_teams
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import InvalidDecisionError, PendingDecisionError
from tests.synthetic_teams import default_teams


def new(**kwargs) -> SavedGame:
    return SavedGame.new(
        *default_teams(), home_id="2026/a", away_id="2026/b", seed=7, coach_seed=31, **kwargs
    )


@pytest.mark.parametrize("human,calls", [("home", ("1", "9")), ("away", ("A", "F"))])
def test_computer_call_does_not_depend_on_the_hidden_human_call(human, calls) -> None:
    results = [new().coach_step(human, call) for call in calls]
    assert results[0][3] == results[1][3]
    assert results[0][0].supported and results[1][0].supported


def test_preview_and_invalid_requests_do_not_consume_dice_or_journal() -> None:
    game = new()
    before = json.loads(dumps_game(game))
    for _ in range(10):
        game.coach_view("home")
    with pytest.raises(InvalidDecisionError):
        game.coach_step("home", "F")
    after = json.loads(dumps_game(game))
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert after[key] == before[key]


def test_a_human_required_decision_cannot_be_automated() -> None:
    teams = sample_teams()
    game = SavedGame.new(
        *teams, home_id="2007/a", away_id="2007/b", seed=39, coach_seed=31, mode="regulation"
    )
    _, turn = game.coach_view("home")
    assert turn.human_role == "decision"
    with pytest.raises(PendingDecisionError):
        game.coach_step("home")


@pytest.mark.parametrize("human", ["home", "away"])
@pytest.mark.parametrize("seed", [7, 39, 101])
def test_complete_computer_games_and_saved_continuation(human: str, seed: int) -> None:
    teams = sample_teams()
    game = SavedGame.new(
        *teams, home_id="2007/a", away_id="2007/b", seed=seed, coach_seed=31, mode="regulation"
    )
    restored = loads_game(
        dumps_game(game), lambda key: teams[0] if key.endswith("/a") else teams[1]
    )
    calls = set()
    for step in range(1400):
        view, turn = game.coach_view(human)
        assert restored.coach_view(human) == (view, turn)
        if view.finished:
            assert len(calls) >= 6
            for quarter in range(1, 5):
                assert (
                    sum(c.before - c.after for c in view.timing_log if c.quarter == quarter) == 900
                )
            assert view.score.home == sum(e.points for e in view.scoring if e.team == view.home)
            assert view.score.away == sum(e.points for e in view.scoring if e.team == view.away)
            return
        if turn.human_role == "decision":
            choices = [c.id for c in turn.pending.choices if c.enabled]
            choice = next(
                (c for c in ("clock:runoff", "conversion:kick", "kick:touchback") if c in choices),
                choices[0],
            )
            assert game.decide(choice) == restored.decide(choice)
        elif turn.human_role == "offense" and not turn.actions.offense:
            assert game.kick(turn.actions.special[0].key) == restored.kick(
                turn.actions.special[0].key
            )
        else:
            call = (
                None
                if turn.automatic
                else (str(step % 9 + 1) if turn.human_role == "offense" else "ABCDEF"[step % 6])
            )
            result = game.coach_step(human, call)
            assert result == restored.coach_step(human, call)
            report, _, _, selected = result
            if (
                selected
                and report
                and report.called_play not in {"Kickoff", "Punt", "Field goal attempt"}
            ):
                calls.add(selected.key)
            assert not selected or not selected.fallback
            assert report is None or report.supported
        if step == 50:
            restored = loads_game(
                dumps_game(restored), lambda key: teams[0] if key.endswith("/a") else teams[1]
            )
    pytest.fail("computer game did not finish")
