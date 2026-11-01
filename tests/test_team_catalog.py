"""Shared team discovery uses canonical IDs and excludes provenance folders."""

import shutil
from dataclasses import replace
from pathlib import Path

from bowl_bound.team_catalog import TeamCatalog
from tests.synthetic_teams import default_teams, write_team


def test_catalog_skips_noncanonical_folders_and_provenance(tmp_path: Path) -> None:
    charts = tuple(replace(chart, season=2002) for chart in default_teams())
    for chart in charts:
        write_team(tmp_path, chart)

    valid_folder = tmp_path / "2002" / "alpha-tech"
    shutil.copytree(valid_folder, tmp_path / "2002" / ("a" * 101))
    shutil.copytree(valid_folder, tmp_path / "2002" / "provenance", dirs_exist_ok=True)

    catalog = TeamCatalog(tmp_path)

    assert [entry.key for entry in catalog.teams()] == [
        "2002/alpha-tech",
        "2002/beta-state",
    ]
    assert catalog.problems == ()
