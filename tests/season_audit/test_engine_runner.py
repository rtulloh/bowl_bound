"""Synthetic complete-game evidence through the actual current engine."""

import pytest

from scripts.run_local_season import GameSpec, _new_audit_game, _play_one
from tests.synthetic_teams import metadata, team_chart


def bundles():
    return {
        "2007/synthetic-home": (team_chart("Synthetic Home", season=2007), metadata()),
        "2007/synthetic-away": (team_chart("Synthetic Away", season=2007), metadata()),
    }


def test_postseason_is_passed_to_actual_engine():
    spec = GameSpec(
        1, 2007, "2007/synthetic-away", "2007/synthetic-home", 31, game_type="postseason"
    )
    game = _new_audit_game(spec, bundles())
    assert game._config["game_type"] == "postseason"


def test_both_sides_use_current_hard_and_replay_exactly():
    spec = GameSpec(1, 2007, "2007/synthetic-away", "2007/synthetic-home", 31)
    row = _play_one(spec, bundles(), both_sides_policy="hard", verify_replay=True)
    assert row["status"] == "passed", row.get("error_detail")
    assert row["configuration"]["both_sides_policy"] == "hard-v15"
    assert row["save_replay"]["checkpoint_verified"] is True
    assert row["save_replay"]["final_replay_verified"] is True
    assert row["coaching_history"]
    assert {call["team_side"] for call in row["coaching_calls"]} == {"home", "away"}
    assert row == _play_one(spec, bundles(), both_sides_policy="hard", verify_replay=True)


@pytest.mark.parametrize("swapped", [False, True])
def test_fixed_baseline_both_sides_complete_and_replay_with_legacy_menu(swapped):
    away, home = "2007/synthetic-away", "2007/synthetic-home"
    if swapped:
        away, home = home, away
    teams = bundles()
    # Identical fixed-gain charts force both teams to score forever in overtime.
    teams["2007/synthetic-away"] = (
        team_chart("Synthetic Away", season=2007, offense=0, defense=0),
        metadata(),
    )
    row = _play_one(
        GameSpec(1, 2007, away, home, 31),
        teams,
        both_sides_policy="baseline",
        verify_replay=True,
    )
    assert row["status"] == "passed", row.get("error_detail")
    assert row["save_replay"]["final_replay_verified"] is True
    assert {call["team_side"] for call in row["coaching_calls"]} == {"home", "away"}
    assert not any(
        call["choice"] in {"Q", "RZDZ", "onside_kickoff"} for call in row["coaching_calls"]
    )
