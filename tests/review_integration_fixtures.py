"""Original fictional saves for React-to-real-API presentation integration tests."""

import json
import sys
from dataclasses import replace
from pathlib import Path

from bowl_bound.save_game import SavedGame, dumps_game
from tests.history_fixtures import scoring_history_save
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_halftime_presentation import half_end
from tests.test_special_teams import special_chart


def review_saves(seasons: Path) -> dict[str, str]:
    """Create journaled states; never edit save state, chart hashes or checksums."""
    charts = [
        replace(
            team_chart("Review " + side.title(), season=2002, offense=0, defense=0),
            special_teams=special_chart(
                side, kickoff=yards(65), kickoff_return=yards(100)
            ).special_teams,
        )
        for side in ("home", "away")
    ]
    ids = [write_team(seasons, chart) for chart in charts]
    saves = {}
    for human in ("home", "away"):
        scorer = "away" if human == "home" else "home"
        game = SavedGame.new(*charts, home_id=ids[0], away_id=ids[1], seed=7, mode="regulation")
        winner = game.view().pending.chooser_side
        game.decide("toss:receive" if winner == scorer else "toss:kick")
        assert game.kick("kickoff").pending
        game.decide("kick:return")
        assert game.view().phase == "conversion_choice"
        game.decide("conversion:two")
        saves["two_" + human] = dumps_game(game)
    half = half_end()
    for chart in half._charts.values():
        write_team(seasons, chart)
    saves["halftime"] = dumps_game(half)
    for side in ("Home", "Away"):
        write_team(
            seasons,
            replace(
                team_chart("History " + side, season=2002, offense=100, defense=0, pat_good=True),
                special_teams=special_chart(
                    side, kickoff=yards(40), kickoff_return=yards(10)
                ).special_teams,
            ),
        )
    saves["history"] = scoring_history_save(seasons)
    return saves


if __name__ == "__main__":
    print(json.dumps(review_saves(Path(sys.argv[1]))))
