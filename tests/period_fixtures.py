"""Synthetic, journaled near-period-end saves for real-engine browser tests."""

import sys
from pathlib import Path

from bowl_bound.save_game import SavedGame, dumps_game
from bowl_bound.team_catalog import TeamCatalog
from bowl_bound.timing import Clock


def period_end_save(seasons: Path, quarter: int, opening_choice: str) -> str:
    """Leave a completed run's normal timing pending with ten seconds displayed.

    The next ordinary call expires the period before rolling another play. Build
    this through engine commands, without editing saved state or its checksums.
    Guidance teams are invented zero-yard charts installed by the browser server.
    """
    catalog = TeamCatalog(seasons)
    home_id, away_id = "2002/guidance-home", "2002/guidance-away"
    home, _ = catalog.load_with_metadata(home_id)
    away, _ = catalog.load_with_metadata(away_id)
    game = SavedGame.new(
        home,
        away,
        home_id=home_id,
        away_id=away_id,
        seed=7,
        coach_seed=1,
        mode="regulation",
        clock=Clock(quarter, 20, (1, 2)),
        difficulty="medium",
    )
    game.decide(opening_choice)
    game.kick("kickoff")
    game.snap("1", "A")
    assert game.view().phase == "clock_choice"
    assert game.view().clock.remaining == 10
    return dumps_game(game)


if __name__ == "__main__":
    print(period_end_save(Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]))
