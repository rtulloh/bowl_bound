"""Complete synthetic games reconcile narrated and generic football streams."""

import json
from pathlib import Path
from random import getstate

import pytest

from bowl_bound.sample_teams import install_samples, sample_teams
from bowl_bound.save_game import SavedGame, dumps_game


@pytest.mark.parametrize("human", ["home", "away"])
def test_complete_game_full_partial_and_missing_rosters_have_identical_facts(
    tmp_path: Path,
    human: str,
) -> None:
    teams = sample_teams()
    ids = install_samples(tmp_path)
    games = [
        SavedGame.new(
            *teams,
            home_id=ids[0],
            away_id=ids[1],
            seed=7,
            coach_seed=31,
            coach_policy="medium-v1",
            mode="regulation",
        )
        for _ in range(3)
    ]
    for index, team_id in enumerate(ids):
        (tmp_path / team_id / "roster.json").write_text(
            json.dumps(
                {role: [f"Invented {index} {role}"] for role in ("qb", "rb", "wr", "k", "p", "kr")}
            )
        )
    games[1].load_rosters(tmp_path)
    (tmp_path / ids[0] / "roster.json").write_text('{"qb":["Partial Quill"]}')
    (tmp_path / ids[1] / "roster.json").unlink()
    games[2].load_rosters(tmp_path)
    named = False
    for step in range(1400):
        view, turn = games[0].coach_view(human)
        assert all(game.coach_view(human) == (view, turn) for game in games[1:])
        rng = getstate()
        for game in games:
            for value in view.log[-2:]:
                rendered = game.commentary(value)
                named |= "Invented" in rendered
        assert getstate() == rng
        if view.finished:
            assert named and len(view.log) > 50
            assert view.score.home == sum(e.points for e in view.scoring if e.team == view.home)
            assert view.score.away == sum(e.points for e in view.scoring if e.team == view.away)
            for quarter in range(1, 5):
                assert (
                    sum(t.before - t.after for t in view.timing_log if t.quarter == quarter) == 900
                )
            return
        if turn.human_role == "decision":
            choices = [c.id for c in turn.pending.choices if c.enabled]
            choice = next(
                (c for c in ("clock:runoff", "conversion:kick", "kick:touchback") if c in choices),
                choices[0],
            )
            results = [game.decide(choice) for game in games]
        elif turn.human_role == "offense" and not turn.actions.offense:
            results = [game.kick(turn.actions.special[0].key) for game in games]
        else:
            call = (
                None
                if turn.automatic
                else (str(step % 9 + 1) if turn.human_role == "offense" else "ABCDEF"[step % 6])
            )
            results = [game.coach_step(human, call) for game in games]
        assert results[0] == results[1] == results[2]
        saves = [json.loads(dumps_game(game)) for game in games]
        for key in ("commands", "rolls", "random_state", "state_digest"):
            assert saves[0][key] == saves[1][key] == saves[2][key]
    pytest.fail("Paired synthetic games did not finish")
