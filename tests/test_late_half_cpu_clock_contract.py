"""AI-035 boundary, version, migration and real-API controls; fictional charts only."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.coaching_session import plan_turn
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import Play, TeamChart
from bowl_bound.save_game import SavedGame, _semantic_view_digest, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_coaching import observation
from tests.test_regulation import kickoff, new_game, snap
from tests.test_special_teams import special_chart


def saved_scoring_opportunity(side: str, mode: str) -> SavedGame:
    """Reach the entire Q2 state by journaled commands, suitable for strict replay."""
    charts = []
    for name in ("Home", "Away"):
        ordinary = team_chart(
            name,
            season=2002,
            offense=0,
            defense=0,
            plays={Play.ONE: yards(1), Play.TWO: yards(60)},
        )
        special = special_chart(
            name,
            kickoff=yards(70),
            kickoff_return=yards(10),
            punt=yards(40),
            field_goal=yards(40),
        )
        charts.append(replace(ordinary, special_teams=special.special_teams))
    game = SavedGame.new(
        *charts,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        mode="regulation",
        clock=Clock(2, 110),
        coach_policy=f"{mode}-v11",
    )
    chooser = game.view().pending.chooser_side
    game.decide("toss:receive" if chooser == side else "toss:kick")
    game.kick("kickoff")
    game.decide("kick:touchback")
    for play in ("2", "1", "1", "1"):
        game.snap(play, "A")
    view = game.view()
    assert view.clock.quarter == 2 and view.clock.remaining == 30
    assert view.state.possession == side and view.state.down == 4
    assert view.state.yards_to_goal == 17 and view.state.yards_to_go == 7
    return game


def chart_loader(game: SavedGame) -> Callable[[str], TeamChart]:
    return {"2002/home": game._charts["home"], "2002/away": game._charts["away"]}.__getitem__


def legacy_seed_digest() -> str:
    rows = []
    home, away = team_chart("Home"), team_chart("Away")
    obs = observation(quarter=2, remaining=30, down=4, distance=7, yards_to_goal=17)
    for version in range(1, 12):
        coaches = [
            BaselineCoach(31, version=version),
            ChartAwareCoach(31, home, away, version=version),
        ]
        coaches += [
            DifficultyCoach(31, home, away, tier, version=version)
            for tier in ("easy", "medium", "hard")
        ]
        for coach in coaches:
            for role in ("offense", "defense"):
                stream = coach._random(obs, role)
                rows.append(
                    (
                        coach.policy if hasattr(coach, "policy") else f"baseline-v{version}",
                        role,
                        [stream.getrandbits(32) for _ in range(3)],
                    )
                )
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def test_frozen_v1_through_v11_seed_contract() -> None:
    assert (
        legacy_seed_digest() == "cdceea6ec51de66e151fdcdd53a24028984ee9531b2eb5f59ed1c461fd0cb02a"
    )


@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("remaining", [20, 30, 31])
@pytest.mark.parametrize("gain,normal_seconds", [(3, 30), (10, 20)])
def test_engine_owns_the_pending_normal_timing_fact(
    quarter: int, remaining: int, gain: int, normal_seconds: int
) -> None:
    game = new_game(clock=Clock(quarter, remaining), gain=gain)
    kickoff(game)
    assert game.view().normal_timing_ends_period is False
    snap(game)
    before = game.view()
    assert before.normal_timing_ends_period is (remaining <= normal_seconds)
    assert game.view() == before
    game.decide("clock:timeout:home")
    assert game.view().normal_timing_ends_period is False
    assert game.view().clock.remaining == remaining - 10


@pytest.mark.parametrize("version", range(1, 12))
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_frozen_clock_methods_delegate_without_new_preferences(version: int, mode: str) -> None:
    coach = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=version)
    obs = observation(
        quarter=2,
        remaining=30,
        down=4,
        distance=7,
        yards_to_goal=17,
        phase="clock_choice",
        choices=("clock:timeout:home", "clock:hurry", "clock:standard"),
    )
    assert coach.clock_decision(obs, normal_timing_ends_period=True) == coach.decision(obs)


@pytest.mark.parametrize(
    "changes,ends",
    [
        ({}, False),
        ({"remaining": 10}, True),
        ({"remaining": 5}, True),
        ({"remaining": 0}, True),
        ({"quarter": 1}, True),
        ({"quarter": 3}, True),
        ({"score_difference": 1}, True),
        ({"overtime": True}, True),
        ({"phase": "scrimmage"}, True),
        ({"side": "away"}, True),
        ({"down": 3}, True),
        ({"yards_to_goal": 70, "distance": 8}, True),
        ({"special": ("punt",)}, True),
        ({"choices": ("clock:timeout:away", "clock:standard")}, True),
        ({"choices": ("clock:standard",)}, True),
        ({"quarter": 4, "score_difference": -7}, True),
    ],
)
def test_new_clock_policy_is_limited_to_the_reviewed_scoring_boundary(
    changes: dict, ends: bool
) -> None:
    coach = DifficultyCoach(
        31, team_chart("Home"), team_chart("Away"), "medium", version=CURRENT_DIFFICULTY_VERSION
    )
    obs = observation(
        quarter=2,
        remaining=30,
        down=4,
        distance=7,
        yards_to_goal=17,
        phase="clock_choice",
        choices=("clock:timeout:home", "clock:standard"),
    )
    obs = replace(obs, **changes)
    assert coach.clock_decision(obs, normal_timing_ends_period=ends) == coach.decision(obs)


@pytest.mark.parametrize("quarter", [2, 4])
@pytest.mark.parametrize("margin", [0, -1, -3])
def test_current_clock_method_uses_only_own_offered_timeout(quarter: int, margin: int) -> None:
    coach = DifficultyCoach(
        31, team_chart("Home"), team_chart("Away"), "medium", version=CURRENT_DIFFICULTY_VERSION
    )
    obs = observation(
        quarter=quarter,
        remaining=20,
        down=4,
        distance=7,
        yards_to_goal=17,
        score_difference=margin,
        phase="clock_choice",
        choices=("clock:timeout:home", "clock:timeout:away", "clock:standard"),
    )
    assert coach.clock_decision(obs, normal_timing_ends_period=True) == "clock:timeout:home"


def test_only_derived_view_fact_is_excluded_from_semantic_digest() -> None:
    game = new_game(clock=Clock(2, 30))
    kickoff(game)
    snap(game)
    original = asdict(game.view())
    changed = {**original, "normal_timing_ends_period": False}
    legacy = {key: value for key, value in original.items() if key != "normal_timing_ends_period"}
    assert (
        _semantic_view_digest(original)
        == _semantic_view_digest(changed)
        == _semantic_view_digest(legacy)
    )
    changed["clock"] = {**changed["clock"], "remaining": 29}
    assert _semantic_view_digest(changed) != _semantic_view_digest(original)


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("side", ["home", "away"])
def test_ordinary_load_upgrades_but_explicit_audit_load_keeps_v11(mode: str, side: str) -> None:
    original = saved_scoring_opportunity(side, mode)
    text = dumps_game(original)
    frozen = loads_game(text, chart_loader(original), preserve_development_policy=True)
    current = loads_game(text, chart_loader(original))
    assert frozen._coach.version == 11
    assert current._coach.version == CURRENT_DIFFICULTY_VERSION == 13
    assert current.view() == frozen.view()
    assert json.loads(dumps_game(current))["config"]["difficulty"] == mode
    assert "coach_policy" not in json.loads(dumps_game(current))["config"]
    human = "away" if side == "home" else "home"
    assert plan_turn(frozen.view(), human, frozen._coach).operation == "kick"
    assert plan_turn(current.view(), human, current._coach).arguments == (f"clock:timeout:{side}",)
    rolls = json.loads(dumps_game(current))["rolls"]
    current.coach_step(human)
    assert json.loads(dumps_game(current))["rolls"] == rolls
    assert current.view().clock.remaining == 20
    assert current.view().clock.timeouts == ((2, 3) if side == "home" else (3, 2))
    resumed = loads_game(dumps_game(current), chart_loader(original))
    assert resumed.view() == current.view()
    resumed.coach_step(human)
    current.coach_step(human)
    assert resumed.view() == current.view()
    assert current.view().score.home + current.view().score.away == 3
    assert len(json.loads(dumps_game(current))["rolls"]) == len(rolls) + 1


@pytest.mark.parametrize("side", ["home", "away"])
def test_real_api_load_and_automatic_steps_preserve_the_scoring_attempt(
    tmp_path: Path, side: str
) -> None:
    original = saved_scoring_opportunity(side, "medium")
    root = tmp_path / "seasons"
    for chart in original._charts.values():
        write_team(root, chart)
    client = TestClient(create_app(root))
    human = "away" if side == "home" else "home"
    loaded = client.post(
        f"/api/games/load?human_side={human}",
        content=dumps_game(original),
        headers={"content-type": "application/json"},
    )
    assert loaded.status_code == 200, loaded.text
    data = loaded.json()
    assert data["view"]["normal_timing_ends_period"] is True
    assert data["turn"]["automatic"] is True
    path = f"/api/games/{data['game_id']}/coach"
    for expected_remaining in (20, 10):
        response = client.post(
            path, json={"human_side": human, "expected_revision": data["revision"]}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["view"]["clock"]["remaining"] == expected_remaining
        assert data["view"]["normal_timing_ends_period"] is False
        assert data["view"]["clock"]["timeouts"] == ([2, 3] if side == "home" else [3, 2])
    assert data["view"]["score"][side] == 3
    assert data["view"]["log"][-1]["called_play"] == "Field goal attempt"
