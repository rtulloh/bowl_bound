"""Simultaneous calls are concealed by the server, not merely hidden with CSS."""

import json
from dataclasses import asdict

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.coaching_session import plan_turn
from bowl_bound.save_game import SavedGame
from tests.synthetic_teams import default_teams


def game() -> SavedGame:
    return SavedGame.new(*default_teams(), home_id="2026/a", away_id="2026/b", seed=7)


@pytest.mark.parametrize("human,role", [("home", "offense"), ("away", "defense")])
def test_preview_exposes_only_human_controls_and_no_computer_selection(
    human: str, role: str
) -> None:
    before = game().view()
    plan = plan_turn(before, human, BaselineCoach(31))
    shown = asdict(plan.turn)
    assert shown["human_role"] == role
    assert not shown["automatic"]
    assert set(shown) == {
        "human_side",
        "human_role",
        "automatic",
        "status",
        "actions",
        "game_actions",
        "pending",
    }
    assert bool(plan.turn.actions.offense) == (role == "offense")
    assert bool(plan.turn.actions.defense) == (role == "defense")
    assert not any(key in json.dumps(shown) for key in ("computer_call", "computer_choice", "seed"))
    assert plan.operation == "snap"
    assert plan.computer_choice.key not in (None, "")


def test_selector_never_receives_the_opponent_selected_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = []
    original = BaselineCoach.defense

    def spy(self, observation):
        seen.append(asdict(observation))
        return original(self, observation)

    monkeypatch.setattr(BaselineCoach, "defense", spy)
    view = game().view()
    first = plan_turn(view, "home", BaselineCoach(31))
    second = plan_turn(view, "home", BaselineCoach(31))
    assert first.computer_choice == second.computer_choice
    assert seen[0] == seen[1]
    assert (
        not {"human_call", "selected_offense", "selected_defense", "trace", "log", "seed"}
        & seen[0].keys()
    )


def test_bad_policy_suggestion_uses_a_legal_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BaselineCoach, "defense", lambda *_: "Z")
    plan = plan_turn(game().view(), "home", BaselineCoach(31))
    assert plan.computer_choice.key == "A" and plan.computer_choice.fallback


def test_invalid_human_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="home or away"):
        plan_turn(game().view(), "third", BaselineCoach(31))
