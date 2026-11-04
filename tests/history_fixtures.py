"""Journaled fictional scoring history for real-engine browser visibility checks."""

import sys
from pathlib import Path

from bowl_bound.save_game import SavedGame, dumps_game
from bowl_bound.team_catalog import TeamCatalog


def scoring_history_save(seasons: Path) -> str:
    """Retain repeated TD/PAT/combined kick-return reports without editing a save."""
    catalog = TeamCatalog(seasons)
    ids = ("2002/history-home", "2002/history-away")
    charts = [catalog.load_with_metadata(team_id)[0] for team_id in ids]
    game = SavedGame.new(*charts, home_id=ids[0], away_id=ids[1], seed=7, mode="regulation")
    game.decide("toss:receive")
    game.kick("kickoff")
    for _ in range(14):
        game.snap("1", "A")
        assert game.view().phase == "conversion_choice"
        game.decide("conversion:kick")
        game.kick("kickoff")
    assert len(game.view().log) == 43
    return dumps_game(game)


if __name__ == "__main__":
    print(scoring_history_save(Path(sys.argv[1])))
