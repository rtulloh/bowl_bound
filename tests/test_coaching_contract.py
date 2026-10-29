"""Additive ownership/dice presentation must preserve existing m19 saves."""

import json
from dataclasses import replace
from itertools import product

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
    roll_view,
)
from bowl_bound.sample_teams import sample_teams
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import default_teams


def test_roll_views_preserve_all_physical_faces_and_distinguish_white_dice() -> None:
    count = 0
    for black, one, two in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        roll = OffensiveRoll(black, one, two)
        shown = roll_view(roll)
        assert shown["total"] == roll.total
        assert shown["faces"] == [black, one, two]
        assert [d["role"] for d in shown["dice"]] == ["black", "white_one", "white_two"]
        assert [d["face"] for d in shown["dice"]] == shown["faces"]
        assert [d["color"] for d in shown["dice"]] == ["black", "white", "white"]
        assert [d["label"] for d in shown["dice"]] == ["Black", "White 1", "White 2"]
        count += 1
    assert count == 216
    count = 0
    for red, green in product(RED_FACES, GREEN_FACES):
        shown = roll_view(DefensiveRoll(red, green))
        assert [d["role"] for d in shown["dice"]] == ["red", "green"]
        assert shown["faces"] == [red, green]
        assert shown["total"] == red + green
        count += 1
    assert count == 36


def test_opening_owner_is_explicit_even_with_identical_team_names() -> None:
    home, away = (replace(team, name="Same Name") for team in sample_teams())
    game = SavedGame.new(home, away, home_id="2007/a", away_id="2007/b", seed=39, mode="regulation")
    assert game.view().pending.chooser == "Same Name"
    assert game.view().pending.chooser_side == "home"


def test_presentation_additions_keep_pre_ai_scrimmage_digest_compatible() -> None:
    teams = default_teams()
    game = SavedGame.new(*teams, home_id="2026/alpha-tech", away_id="2026/beta-state", seed=7)
    game.snap("1", "A")
    data = json.loads(dumps_game(game))
    # Recorded from committed m19 (57b4dd6), using only the synthetic default teams.
    assert (
        data["state_digest"] == "1d81213460c860ddbc15267a5817e37d1909a812af6d43cdc36d2649080e149c"
    )
    restored = loads_game(dumps_game(game), lambda key: teams[0] if "alpha" in key else teams[1])
    assert restored.view() == game.view()


def test_presentation_additions_keep_pre_ai_toss_digest_compatible() -> None:
    teams = sample_teams()
    game = SavedGame.new(
        *teams, home_id="2007/cedar-valley", away_id="2007/harbor-tech", seed=39, mode="regulation"
    )
    data = json.loads(dumps_game(game))
    assert (
        data["state_digest"] == "40fc3aa1124dda7b6bc4c09f48fd444b73f0f6d001d46f767442bcd95a62af72"
    )


def test_toss_metadata_describes_only_the_recorded_rolls_without_advancing_dice() -> None:
    game = SavedGame.new(
        *sample_teams(), home_id="2007/a", away_id="2007/b", seed=39, mode="regulation"
    )
    before = json.loads(dumps_game(game))["rolls"]
    view = game.view()
    assert view.toss_dice == tuple(roll_view(roll) for roll in view.toss_rolls)
    assert len(view.toss_dice) == len(before)
    assert view.overtime_toss_dice == ()
    assert json.loads(dumps_game(game))["rolls"] == before


def test_an_actual_m19_config_without_coaching_metadata_loads_and_upgrades_once() -> None:
    from tests.test_save_game import seal

    teams = default_teams()
    game = SavedGame.new(*teams, home_id="2026/alpha-tech", away_id="2026/beta-state", seed=7)
    game.snap("1", "A")
    legacy = json.loads(dumps_game(game))
    del legacy["config"]["coach_seed"]
    legacy["state_digest"] = "1d81213460c860ddbc15267a5817e37d1909a812af6d43cdc36d2649080e149c"

    def loader(key: str):
        return teams[0] if "alpha" in key else teams[1]

    upgraded = loads_game(seal(legacy), loader)
    assert upgraded.view() == game.view()
    restored = loads_game(dumps_game(upgraded), loader)
    assert restored.coach_view("home") == upgraded.coach_view("home")
    assert restored.coach_step("home", "2") == upgraded.coach_step("home", "2")
