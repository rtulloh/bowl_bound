"""Real journaled scoring history stays complete through save/load."""

from collections import Counter
from dataclasses import replace
from pathlib import Path

from bowl_bound.save_game import loads_game
from bowl_bound.team_catalog import TeamCatalog
from tests.history_fixtures import scoring_history_save
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_special_teams import special_chart


def test_scoring_history_retains_pat_and_combined_returns_on_reload(tmp_path: Path) -> None:
    for label in ("Home", "Away"):
        write_team(
            tmp_path,
            replace(
                team_chart("History " + label, season=2002, offense=100, defense=0, pat_good=True),
                special_teams=special_chart(
                    label, kickoff=yards(40), kickoff_return=yards(10)
                ).special_teams,
            ),
        )
    catalog = TeamCatalog(tmp_path)
    game = loads_game(scoring_history_save(tmp_path), catalog.load_with_metadata)
    outcomes = Counter(report.outcome for report in game.view().log)
    assert len(game.view().log) == 43
    assert outcomes == {"touchdown": 14, "pat_good": 14, "kickoff_return": 15}
    assert [report.number for report in game.view().log] == list(range(1, 44))
    for report in game.view().log:
        if report.outcome == "kickoff_return":
            assert [entry.section for entry in report.trace] == ["kickoff", "kickoff_return"]
