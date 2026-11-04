"""Journaled fictional two-point selection for real-engine browser checks."""

import sys
from pathlib import Path

from bowl_bound.save_game import SavedGame, dumps_game
from bowl_bound.team_catalog import TeamCatalog


def two_point_save(seasons: Path, human: str, result: str) -> str:
    catalog = TeamCatalog(seasons)
    ids = tuple(f"2002/try-{result}-{side}" for side in ("home", "away"))
    charts = [catalog.load_with_metadata(team_id)[0] for team_id in ids]
    game = SavedGame.new(
        *charts, home_id=ids[0], away_id=ids[1], seed=7, mode="regulation", coach_policy="baseline"
    )
    scorer = "away" if human == "home" else "home"
    game.decide("toss:receive" if game.view().pending.chooser_side == scorer else "toss:kick")
    game.kick("kickoff")
    game.snap("2", "A")
    game.decide("conversion:two")
    assert game.view().phase == "two_point_try"
    return dumps_game(game)


if __name__ == "__main__":
    print(two_point_save(Path(sys.argv[1]), sys.argv[2], sys.argv[3]))
