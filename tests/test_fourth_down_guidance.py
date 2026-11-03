"""UI-041: public, pure player guidance shared with normal CPU policy."""

import io
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame
from bowl_bound.coaching import public_fourth_down_call
from bowl_bound.coaching_session import observe_game
from bowl_bound.models import TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PendingDecisionView
from tests.synthetic_teams import team_chart, write_team


def fourth_down(tier: str = "medium", side: str = "home", spot: int = 31) -> SavedGame:
    home = team_chart("Home", offense=0, defense=0)
    away = team_chart("Away", offense=0, defense=0)
    game = SavedGame.new(
        home,
        away,
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        coach_seed=31,
        difficulty=tier,
        start_yards_to_goal=spot if side == "home" else 100 - spot,
    )
    for _ in range(3 if side == "home" else 7):
        game.snap("1", "A")
    assert game.view().state.possession == side
    assert game.view().state.down == 4
    return game


def saved_facts(game: SavedGame) -> dict[str, object]:
    data = json.loads(dumps_game(game))
    return {k: v for k, v in data.items() if k not in {"saved_at", "integrity"}}


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("spot", [31, 38, 65])
def test_player_guidance_matches_shared_policy_without_mutation(
    tier: str,
    side: str,
    spot: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = fourth_down(tier, side, spot)
    view = game.view()
    before = saved_facts(game)
    history = game._coach.call_history()
    original = TeamChart.__getattribute__

    def reject_chart(chart: TeamChart, name: str) -> object:
        if name in {"special_teams", "offense", "defense", "pat_outcomes"}:
            raise AssertionError("public guidance must not inspect charts")
        return original(chart, name)

    with monkeypatch.context() as guarded:
        guarded.setattr(TeamChart, "__getattribute__", reject_chart)
        advice = game.fourth_down_guidance(side, view=view)
        assert advice == game.fourth_down_guidance(side, view=view)
    assert advice.action == public_fourth_down_call(
        observe_game(view, side),
        aggression=game._coach.aggression,
        chase_seconds=game._coach.behavior.chase_seconds,
    )
    assert advice.attempt_distance == spot + 17
    assert advice.difficulty == tier
    assert advice.aggression == game._coach.aggression
    assert advice.label and advice.summary
    assert game.fourth_down_guidance("away" if side == "home" else "home") is None
    assert game.fourth_down_guidance(None) == advice
    assert game._coach.call_history() == history
    assert saved_facts(game) == before
    restored = loads_game(
        dumps_game(game), lambda key: game._charts["home" if key.endswith("home") else "away"]
    )
    assert restored.fourth_down_guidance(side) == advice


def test_guidance_uses_the_supplied_atomic_response_view() -> None:
    game = fourth_down()
    captured = game.view()
    game.snap("1", "A")
    assert game.fourth_down_guidance("home") is None
    assert game.fourth_down_guidance("home", view=captured).action == "field_goal"


def test_guidance_is_unavailable_outside_an_enabled_fourth_down() -> None:
    game = fourth_down()
    view = game.view()
    for unavailable in (
        replace(view, finished=True),
        replace(view, state=None),
        replace(view, phase="two_point_try"),
        replace(view, pending=PendingDecisionView("Home", (), "home")),
        replace(view, state=replace(view.state, down=3)),
        replace(view, actions=replace(view.actions, special=())),
    ):
        assert game.fourth_down_guidance("home", view=unavailable) is None
    with pytest.raises(ValueError, match="human side"):
        game.fourth_down_guidance("spectator")


def test_development_and_legacy_policies_do_not_claim_shared_guidance() -> None:
    game = SavedGame.new(
        team_chart("Home"), team_chart("Away"), home_id="2026/home", away_id="2026/away", seed=7
    )
    assert game.difficulty is None
    assert game.fourth_down_guidance(None) is None


def test_cli_displays_engine_guidance_verbatim() -> None:
    game = fourth_down("hard")
    output = io.StringIO()
    cli = TerminalGame(
        game,
        lambda key: game._charts["home" if key.endswith("home") else "away"],
        human_side="home",
        output=output,
    )
    advice = game.fourth_down_guidance("home")
    cli.display()
    assert advice.label in output.getvalue()
    assert advice.summary in output.getvalue()


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_api_guidance_matches_engine_and_clears_after_kick(tmp_path: Path, tier: str) -> None:
    game = fourth_down(tier)
    root = tmp_path / "seasons"
    for chart in game._charts.values():
        write_team(root, chart)
    client = TestClient(create_app(root))
    response = client.post(
        "/api/games/load?human_side=home",
        content=dumps_game(game),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    expected = asdict(game.fourth_down_guidance("home"))
    assert data["view"]["fourth_down_guidance"] == expected
    key = data["game_id"]
    assert (
        client.get(f"/api/games/{key}?human_side=home").json()["view"]["fourth_down_guidance"]
        == expected
    )
    kicked = client.post(f"/api/games/{key}/kick?human_side=home", json={"action": "field_goal"})
    assert kicked.status_code == 200, kicked.text
    assert kicked.json()["view"]["fourth_down_guidance"] is None


def test_short_fourth_down_shows_go_guidance_using_public_facts() -> None:
    game = fourth_down(spot=30)
    view = game.view()
    short = replace(view, state=replace(view.state, yards_to_go=1))
    assert game.fourth_down_guidance("home", view=short).action == "go"


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_coached_response_attaches_guidance_only_for_the_offense(tmp_path: Path, tier: str) -> None:
    game = fourth_down(tier)
    root = tmp_path / "seasons"
    for chart in game._charts.values():
        write_team(root, chart)
    client = TestClient(create_app(root))
    defender = client.post(
        "/api/games/load?human_side=away",
        content=dumps_game(game),
        headers={"content-type": "application/json"},
    ).json()
    assert defender["view"]["fourth_down_guidance"] is None
    # Replay two snaps so the actual coached API command creates fourth down.
    fresh = SavedGame.new(
        *game._charts.values(),
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        coach_seed=31,
        difficulty=tier,
        start_yards_to_goal=31,
    )
    for _ in range(2):
        fresh.snap("1", "A")
    loaded = client.post(
        "/api/games/load?human_side=home",
        content=dumps_game(fresh),
        headers={"content-type": "application/json"},
    ).json()
    assert loaded["view"]["fourth_down_guidance"] is None
    response = client.post(
        f"/api/games/{loaded['game_id']}/coach",
        json={
            "human_side": "home",
            "human_call": "1",
            "expected_revision": 2,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["view"]["fourth_down_guidance"] == asdict(
        game.fourth_down_guidance("home")
    )
