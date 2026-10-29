"""Start the real Bowl Bound API for browser tests on a synthetic season folder.

Usage: python e2e/serve_backend.py <seasons-dir> <port>
The folder is filled with two invented teams, so no historical data is involved.
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app import create_app  # noqa: E402
from bowl_bound.sample_teams import install_samples  # noqa: E402
from tests.synthetic_teams import default_teams, write_team  # noqa: E402
from tests.test_special_teams import special_chart, yards  # noqa: E402


def main() -> None:
    seasons = Path(sys.argv[1])
    port = int(sys.argv[2])
    for chart in default_teams():
        chart = replace(
            chart,
            season=2002,
            special_teams=special_chart(
                chart.name, kickoff=yards(40), kickoff_return=yards(10)
            ).special_teams,
            pat_outcomes=tuple(replace(row, good=True) for row in chart.pat_outcomes),
        )
        write_team(seasons, chart)
    for label in ("Home", "Away"):
        base = default_teams()[0]
        chart = replace(
            base,
            name="Roster " + label,
            season=2002,
            special_teams=special_chart(
                label, kickoff=yards(40), kickoff_return=yards(10)
            ).special_teams,
        )
        team_id = write_team(seasons, chart)
        (seasons / team_id / "roster.json").write_text(
            json.dumps({"rb": [label + " Fictional " + "Q" * 80], "qb": [label + " Passer"]}),
            encoding="utf-8",
        )
    install_samples(seasons)
    uvicorn.run(
        create_app(seasons, ROOT / "frontend" / "dist"),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
