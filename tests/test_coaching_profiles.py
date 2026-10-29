"""AI-007: profile extraction preserves seeded calls and exposes immutable diagnostics."""

import json
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest

from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import BaselineCoach
from bowl_bound.difficulty import DifficultyCoach
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation


def test_profile_extraction_preserves_pre_refactor_seeded_calls() -> None:
    home, away = team_chart("Home"), team_chart("Away", offense=6, defense=0)
    coaches = [
        BaselineCoach(31),
        ChartAwareCoach(31, home, away),
        *(DifficultyCoach(31, home, away, mode) for mode in ("easy", "medium", "hard")),
    ]
    results = []
    for coach in coaches:
        calls = []
        for n in range(8):
            obs = observation(
                play_number=n,
                down=1 + n % 4,
                distance=3 + n,
                yards_to_goal=20 + n * 8,
                quarter=4,
                remaining=30 + n * 25,
                score_difference=-7 if n % 2 else 3,
            )
            calls.append(
                (
                    coach.offense(obs),
                    coach.defense(replace(obs, side="away")),
                    coach.decision(replace(obs, choices=("clock:runoff", "clock:hurry"))),
                )
            )
        results.append(calls)
    # Captured on 42e43be before any profile extraction, not updated to fit refactors.
    assert sha256(json.dumps(results).encode()).hexdigest() == (
        "f51c29acb717f2c7ec86f3c0f6d4f176f596e5af22488b00e85c9cff7a638021"
    )


def test_profiles_are_named_frozen_and_separate_from_persisted_policy_streams() -> None:
    from bowl_bound.coaching_profiles import behavior_for_policy

    for policy in ("baseline", "chart-v1", "easy-v1", "medium-v1", "hard-v1"):
        profile = behavior_for_policy(policy)
        assert profile.name == ("baseline-v1" if policy == "baseline" else policy)
        assert profile.analysis_samples == 32 and profile.cache_entries == 128
        with pytest.raises(FrozenInstanceError):
            profile.temperature = 9
    assert [behavior_for_policy(f"{m}-v1").aggression for m in ("easy", "medium", "hard")] == [
        0.3,
        0.5,
        0.7,
    ]
    with pytest.raises(ValueError, match="policy"):
        behavior_for_policy("unknown")
