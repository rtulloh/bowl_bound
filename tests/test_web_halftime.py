"""Validate the browser's synthetic boundary saves through the real API/engine."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from tests.period_fixtures import period_end_save
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_special_teams import special_chart


@pytest.fixture
def seasons(tmp_path: Path) -> Path:
    for side in ("Home", "Away"):
        chart = replace(
            team_chart("Guidance " + side, season=2002, offense=0, defense=0),
            special_teams=special_chart(
                side, kickoff=yards(40), kickoff_return=yards(10)
            ).special_teams,
        )
        write_team(tmp_path, chart)
    return tmp_path


@pytest.mark.parametrize("opening_choice", ["toss:receive", "toss:kick"])
@pytest.mark.parametrize("control", ["manual", "home", "away"])
def test_browser_halftime_fixture_crosses_into_one_reciprocal_kickoff(
    seasons: Path, opening_choice: str, control: str
) -> None:
    client = TestClient(create_app(seasons))
    suffix = "" if control == "manual" else "?human_side=" + control
    loaded = client.post(
        "/api/games/load" + suffix,
        content=period_end_save(seasons, 2, opening_choice),
        headers={"Content-Type": "application/json"},
    )
    assert loaded.status_code == 200
    initial = loaded.json()
    path = "/api/games/" + initial["game_id"]
    if control == "manual":
        response = client.post(path + "/snap", json={"play": "1", "defense": "A"})
    else:
        response = client.post(
            path + "/coach",
            json={
                "human_side": control,
                "human_call": (
                    None
                    if initial["turn"]["automatic"]
                    else "1"
                    if initial["turn"]["human_role"] == "offense"
                    else "A"
                ),
                "expected_revision": initial["revision"],
            },
        )
    assert response.status_code == 200, response.text
    boundary = response.json()
    view = boundary["view"]
    receiver = initial["view"]["opening_kicker"]
    kicker = "away" if receiver == "home" else "home"
    assert view["phase"] == "kickoff"
    assert view["clock"]["quarter"] == 3 and view["clock"]["remaining"] == 900
    assert view["clock"]["timeouts"] == [3, 3]
    assert view["state"]["possession"] == kicker
    # The completed run's pending-clock explanation clears when timing commits.
    for before, after_report in zip(initial["view"]["log"], view["log"], strict=True):
        assert {k: v for k, v in before.items() if k != "timing_label"} == {
            k: v for k, v in after_report.items() if k != "timing_label"
        }
    assert initial["view"]["log"][-1]["timing_label"]
    assert view["log"][-1]["timing_label"] is None

    if control != "manual" and control != kicker:
        assert boundary["turn"]["automatic"]
        response = client.post(
            path + "/coach",
            json={"human_side": control, "expected_revision": boundary["revision"]},
        )
    else:
        response = client.post(path + "/kick" + suffix, json={"action": "kickoff"})
    assert response.status_code == 200
    after = response.json()["view"]
    assert after["phase"] == "scrimmage"
    assert after["state"]["possession"] == receiver
    assert after["clock"]["quarter"] == 3 and after["clock"]["remaining"] == 890
    assert len(after["log"]) == len(initial["view"]["log"]) + 1
    recorded = after["log"][-1]
    assert recorded["outcome"] == "kickoff_return"
    assert recorded["state_before"]["possession"] == kicker
    assert recorded["state_after"]["possession"] == receiver
    assert [step["section"] for step in recorded["trace"]] == ["kickoff", "kickoff_return"]
    assert [step["cell"] for step in recorded["trace"]] == ["40", "10"]

    saved = client.get(path + "/save")
    resumed = client.post(
        "/api/games/load" + suffix,
        content=saved.content,
        headers={"Content-Type": "application/json"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["view"] == after


@pytest.mark.parametrize("opening_choice", ["toss:receive", "toss:kick"])
def test_browser_q1_fixture_preserves_possession_without_kickoff(
    seasons: Path, opening_choice: str
) -> None:
    client = TestClient(create_app(seasons))
    response = client.post("/api/games/load", content=period_end_save(seasons, 1, opening_choice))
    assert response.status_code == 200
    initial = response.json()
    response = client.post(
        "/api/games/" + initial["game_id"] + "/snap", json={"play": "1", "defense": "A"}
    )
    assert response.status_code == 200
    view = response.json()["view"]
    assert view["clock"]["quarter"] == 2 and view["clock"]["remaining"] == 900
    assert view["clock"]["timeouts"] == [1, 2]
    assert view["phase"] == "clock_choice"
    assert view["state"]["possession"] == initial["view"]["state"]["possession"]
    assert view["state"]["yards_to_goal"] == initial["view"]["state"]["yards_to_goal"]
    assert view["state"]["down"] == initial["view"]["state"]["down"] + 1
    assert len(view["log"]) == len(initial["view"]["log"]) + 1
    assert view["log"][-1]["called_play"] == "Line Plunge"
    assert "kickoff" not in [step["section"] for step in view["log"][-1]["trace"]]
