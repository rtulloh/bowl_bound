"""Audits reconcile real complete games and measure repeated comparable calls."""

import pytest

from bowl_bound.sample_teams import sample_teams


@pytest.mark.parametrize("policy", ["baseline", "chart-v1", "easy-v1", "medium-v1", "hard-v1"])
def test_complete_game_audit_reconciles_state_clock_stats_and_saved_future(policy: str) -> None:
    from bowl_bound.coaching_audit import audit_game

    result = audit_game(*sample_teams(), seed=101, coach_seed=31, policy=policy, cpu_side="away")
    assert result.policy == policy and result.finished and result.save_continuation_verified
    assert result.home == sample_teams()[0].name and result.away == sample_teams()[1].name
    assert result.home_score >= 0 and result.away_score >= 0
    assert result.quarter_seconds == (900, 900, 900, 900)
    assert result.illegal_selections == 0
    assert result.plays > 50 and result.trace_rolls > result.plays
    assert result.calls["offense"] and result.calls["defense"]
    assert 0 <= result.repeated_calls <= result.comparable_calls
    assert result.fallbacks == 0


def test_repetition_is_measured_within_comparable_situations() -> None:
    from dataclasses import replace

    from bowl_bound.coaching_audit import CallAudit
    from tests.test_coaching import observation

    audit = CallAudit()
    first = observation()
    audit.record(first, "offense", "1", fallback=False)
    audit.record(replace(first, play_number=1), "offense", "1", fallback=True)
    audit.record(replace(first, down=3, distance=12), "offense", "9", fallback=False)
    audit.record(replace(first, play_number=3), "offense", "2", fallback=False)
    assert audit.comparable_calls == 2 and audit.repeated_calls == 1
    assert audit.fallbacks == 1 and audit.calls["offense"] == {"1": 2, "9": 1, "2": 1}
    with pytest.raises(ValueError, match="legal"):
        audit.record(first, "offense", "illegal", fallback=False)


def test_comparison_seed_validation_does_not_accept_empty_or_training_like_duplicates() -> None:
    from bowl_bound.coaching_audit import compare_policies

    with pytest.raises(ValueError, match="seeds"):
        compare_policies(())
    with pytest.raises(ValueError, match="seeds"):
        compare_policies((7, 7))
