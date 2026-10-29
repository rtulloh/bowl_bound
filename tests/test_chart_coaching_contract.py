"""Opt-in policy configuration preserves saves, private calls and legal fallback."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame, main
from bowl_bound.save_game import SavedGame, SaveFormatError, dumps_game, loads_game
from tests.synthetic_teams import default_teams, write_team


def new(policy: str = "chart-v1") -> SavedGame:
    return SavedGame.new(
        *default_teams(),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=7,
        coach_seed=31,
        coach_policy=policy,
    )


def test_chart_policy_is_saved_and_restores_identical_future_calls_and_dice() -> None:
    teams = default_teams()
    game = new()
    restored = loads_game(
        dumps_game(game), lambda key: teams[0] if key.endswith("alpha-tech") else teams[1]
    )
    assert game.coach_policy == restored.coach_policy == "chart-v1"
    assert json.loads(dumps_game(game))["config"]["coach_policy"] == "chart-v1"
    assert game.coach_step("home", "1") == restored.coach_step("home", "1")
    assert game.view() == restored.view()


def test_old_baseline_configuration_stays_baseline_without_policy_field() -> None:
    game = new("baseline")
    data = json.loads(dumps_game(game))
    assert "coach_policy" not in data["config"]
    assert game.coach_policy == "baseline"
    teams = default_teams()
    restored = loads_game(
        dumps_game(game), lambda key: teams[0] if key.endswith("alpha-tech") else teams[1]
    )
    assert restored.coach_policy == "baseline"
    assert game.coach_step("home", "1") == restored.coach_step("home", "1")


@pytest.mark.parametrize("policy", ["unknown", "chart", True, None, ["chart-v1"]])
def test_invalid_policies_are_refused(policy: object) -> None:
    with pytest.raises(SaveFormatError):
        new(policy)


@pytest.mark.parametrize("human,calls", [("home", ("1", "9")), ("away", ("A", "F"))])
def test_chart_computer_call_cannot_depend_on_hidden_human_call(
    human: str, calls: tuple[str, str]
) -> None:
    first, second = new(), new()
    assert first.coach_step(human, calls[0])[3] == second.coach_step(human, calls[1])[3]


def test_chart_previews_and_invalid_requests_preserve_gameplay_save_facts() -> None:
    game = new()
    before = json.loads(dumps_game(game))
    for _ in range(4):
        _, turn = game.coach_view("home")
        assert not hasattr(turn, "computer_choice")
    from bowl_bound.session import InvalidDecisionError

    with pytest.raises(InvalidDecisionError):
        game.coach_step("home", "F")
    after = json.loads(dumps_game(game))
    for key in ("commands", "rolls", "random_state", "state_digest", "config"):
        assert before[key] == after[key]


def test_analysis_failure_is_audited_in_committed_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    from bowl_bound.coaching_evaluation import ActionEstimate

    monkeypatch.setattr(
        "bowl_bound.chart_coaching.evaluate_action",
        lambda home, away, observation, key, **kwargs: ActionEstimate(key, 32, 1, None, None, None),
    )
    game = new()
    # The human calls a legal defense; chart analysis fails before commit, and
    # the returned diagnostic still records the policy fallback.
    _, _, _, choice = game.coach_step("away", "A")
    assert choice is not None and choice.fallback


def test_cli_hard_flag_and_legacy_chart_resume_preserve_distinct_policies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    teams = tuple(replace(chart, season=2007) for chart in default_teams())
    for chart in teams:
        write_team(tmp_path, chart)
    policies = []

    def run(self: TerminalGame) -> int:
        policies.append(self.game.coach_policy)
        return 0

    monkeypatch.setattr(TerminalGame, "run", run)
    assert (
        main(
            [
                "--seasons",
                str(tmp_path),
                "--home",
                "2007/alpha-tech",
                "--away",
                "2007/beta-state",
                "-d",
                "hard",
            ]
        )
        == 0
    )
    assert policies == ["hard-v1"]
    path = tmp_path / "private-test.json"
    game = SavedGame.new(
        *teams,
        home_id="2007/alpha-tech",
        away_id="2007/beta-state",
        seed=7,
        coach_seed=31,
        coach_policy="chart-v1",
    )
    path.write_text(dumps_game(game))
    assert main(["--seasons", str(tmp_path), "--load", str(path), "--compact"]) == 0
    assert policies == ["hard-v1", "chart-v1"]


def test_api_can_opt_in_without_exposing_policy_plan(tmp_path: Path) -> None:
    ids = [write_team(tmp_path, chart) for chart in default_teams()]
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/api/games?human_side=home",
        json={"home": ids[0], "away": ids[1], "seed": 7, "coach_policy": "chart-v1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "computer_choice" not in body["turn"] and "estimates" not in body
    saved = client.get(f"/api/games/{body['game_id']}/save").json()
    assert saved["config"]["coach_policy"] == "chart-v1"
    assert (
        client.post(
            "/api/games", json={"home": ids[0], "away": ids[1], "coach_policy": "unknown"}
        ).status_code
        == 422
    )
