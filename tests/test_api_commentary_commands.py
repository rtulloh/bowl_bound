"""Shared command transport handles pending replacements and null reports."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.save_game import SavedGame
from tests.synthetic_teams import write_team
from tests.test_special_teams import special_chart, yards


def test_shared_kick_decision_and_null_report_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("Home", "Away"):
        write_team(tmp_path, replace(special_chart(name, punt=yards(40)), season=2007))
    monkeypatch.setattr(
        SavedGame, "commentary", lambda self, report: "ENGINE " + str(report.pending)
    )
    client = TestClient(create_app(tmp_path))
    body = {"home": "2007/home", "away": "2007/away", "seed": 7}
    created = client.post("/api/games", json=body).json()
    path = "/api/games/" + created["game_id"]
    pending = client.post(path + "/kick", json={"action": "punt"}).json()
    assert pending["report"]["pending"]
    assert pending["report"]["commentary"] == "ENGINE True"
    settled = client.post(path + "/decision", json={"choice": "kick:fair_catch"}).json()
    assert settled["report"]["commentary"] == "ENGINE False"
    assert settled["view"]["log"][-1]["commentary"] == "ENGINE False"
    body["mode"] = "regulation"
    game = client.post("/api/games", json=body).json()
    path = "/api/games/" + game["game_id"]
    choice = next(c["id"] for c in game["view"]["pending"]["choices"] if c["enabled"])
    data = client.post(path + "/decision", json={"choice": choice}).json()
    assert data["report"] is None
