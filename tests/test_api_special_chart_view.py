"""Special Teams chart reads use frozen CSV facts and never change a game."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from tests.synthetic_teams import default_teams, write_team
from tests.test_special_chart_view import SPECIAL_COLUMNS, special_view_chart


@pytest.fixture(autouse=True)
def fixed_download_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return datetime(2026, 11, 5, tzinfo=timezone.utc)

    monkeypatch.setattr("bowl_bound.save_game.datetime", FixedDateTime)


@pytest.mark.parametrize("human_side", [None, "home", "away"])
def test_special_api_reads_both_frozen_csv_tables_without_game_changes(
    tmp_path: Path, human_side: str | None
) -> None:
    for name, base in [("Alpha Tech", 0), ("Beta State", 1000)]:
        write_team(tmp_path, special_view_chart(name, base))
    client = TestClient(create_app(tmp_path))
    control = "" if human_side is None else f"?human_side={human_side}"
    game = client.post(
        "/api/games" + control,
        json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7},
    ).json()
    path = "/api/games/" + game["game_id"]
    before = client.get(path + "/save").content
    for file in tmp_path.rglob("*.csv"):
        file.unlink()
    for side, name, base in [("home", "Alpha Tech", 0), ("away", "Beta State", 1000)]:
        response = client.get(path + "/charts?side=" + side)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["team"] == name
        table = data["special_teams"]
        assert [column["key"] for column in table["columns"]] == [
            *(column.value for column, _ in SPECIAL_COLUMNS),
            "pat",
        ]
        assert len(table["rows"]) == 30
        for row, roll in zip(table["rows"], range(10, 40), strict=True):
            assert row["label"] == str(roll)
            assert [(cell["label"], cell["color"]) for cell in row["cells"][:6]] == [
                (str(base + index * 100 + roll), "green") for index in range(6)
            ]
            good = (roll + base) % 3 != 1
            assert (row["cells"][6]["label"], row["cells"][6]["color"]) == (
                ("GOOD", "green") if good else ("NG", "red")
            )
        assert all(
            forbidden not in response.text
            for forbidden in ("provenance", "source_sha256", "filename", "rgb_color")
        )
    assert client.get(path + "/save").content == before
    assert client.get(path + control).json() == game


def test_special_api_read_preserves_a_pending_interception(tmp_path: Path) -> None:
    home, away = default_teams()
    special = special_view_chart(home.name)
    write_team(
        tmp_path,
        replace(home, special_teams=special.special_teams, pat_outcomes=special.pat_outcomes),
    )
    write_team(tmp_path, away)
    client = TestClient(create_app(tmp_path))
    game = client.post(
        "/api/games", json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7}
    ).json()
    path = "/api/games/" + game["game_id"]
    result = client.post(path + "/snap", json={"play": "9", "defense": "A"}).json()
    assert result["view"]["pending"] is not None
    before = client.get(path + "/save").content
    response = client.get(path + "/charts?side=home")
    assert response.status_code == 200
    assert len(response.json()["special_teams"]["rows"]) == 30
    assert client.get(path + "/save").content == before
