"""Browser operations use the same session and replay contracts as HTTP."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.browser_bridge import BrowserBridge
from tests.synthetic_teams import default_teams, write_team


def test_browser_and_http_continue_the_same_pending_save(tmp_path: Path) -> None:
    for team in default_teams():
        write_team(tmp_path, team)
    browser = BrowserBridge(tmp_path)
    http = TestClient(create_app(tmp_path))
    request = {"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 1}
    created = json.loads(browser.request("POST", "/api/games", json.dumps(request)))
    assert created["status"] == 200
    path = "/api/games/" + json.loads(created["body"])["game_id"]
    assert (
        json.loads(browser.request("POST", path + "/snap", '{"play":"9","defense":"A"}'))["status"]
        == 200
    )
    saved = json.loads(browser.request("GET", path + "/save"))
    assert saved["status"] == 200
    restored = http.post("/api/games/load", content=saved["body"])
    assert restored.status_code == 200
    restored_path = "/api/games/" + restored.json()["game_id"]
    native_export = http.get(restored_path + "/save")
    assert native_export.status_code == 200
    reloaded = json.loads(browser.request("POST", "/api/games/load", native_export.text))
    assert reloaded["status"] == 200
    assert json.loads(reloaded["body"])["view"] == restored.json()["view"]

    choice = {"choice": "interception:return"}
    result = json.loads(browser.request("POST", path + "/decision", json.dumps(choice)))
    assert result["status"] == 200
    assert http.post(restored_path + "/decision", json=choice).json() == json.loads(result["body"])


def test_browser_validation_preserves_live_session_and_limits_requests(tmp_path: Path) -> None:
    for team in default_teams():
        write_team(tmp_path, team)
    browser = BrowserBridge(str(tmp_path))
    created = json.loads(
        browser.request(
            "POST",
            "/api/games?human_side=home",
            '{"home":"2026/alpha-tech","away":"2026/beta-state","seed":9223372036854775807}',
        )
    )
    assert created["status"] == 200
    path = "/api/games/" + json.loads(created["body"])["game_id"]
    current = browser.request("GET", path + "?human_side=home")
    assert json.loads(browser.request("GET", path))["status"] == 409
    assert json.loads(browser.request("GET", "/api/rules"))["status"] == 422
    assert json.loads(browser.request("GET", "https://example.org/api/rules"))["status"] == 400
    assert json.loads(browser.request("POST", "/api/games", " " * 16385))["status"] == 413
    invalid = json.loads(browser.request("POST", "/api/games/load", '{"private":"secret"}'))
    assert invalid["status"] == 422
    assert "secret" not in invalid["body"]
    save = json.loads(browser.request("GET", path + "/save"))["body"]
    restored = json.loads(
        BrowserBridge(tmp_path).request(
            "POST",
            "/api/games/load?human_side=home",
            save,
        )
    )
    assert restored["status"] == 200
    assert json.loads(restored["body"])["seed"] == 9223372036854775807
    assert browser.request("GET", path + "?human_side=home") == current
