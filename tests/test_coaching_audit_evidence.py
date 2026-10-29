"""AI-009: audit evidence is observed, replay-checked and public-safe."""

import json
from dataclasses import replace
from random import getstate

import pytest

from bowl_bound import coaching_audit as audit
from bowl_bound.coaching import BaselineCoach, CoachObservation
from bowl_bound.sample_teams import sample_teams
from bowl_bound.save_game import SavedGame
from bowl_bound.session import PlayReport
from tests.test_coaching import observation


def test_illegal_selection_is_counted_before_audit_rejects_it() -> None:
    evidence = audit.CallAudit()
    with pytest.raises(ValueError, match="legal"):
        evidence.record(observation(), "offense", "illegal", fallback=False)
    assert evidence.illegal_selections == 1
    assert not evidence.calls["offense"]


def test_concentration_summary_tracks_streaks_distinct_calls_and_small_samples() -> None:
    evidence = audit.CallAudit()
    obs = observation()
    for index in range(32):
        evidence.record(replace(obs, play_number=index), "offense", "1", fallback=False)
    evidence.record(replace(obs, play_number=33), "offense", "2", fallback=False)
    summary = evidence.summaries()[0]
    assert summary.samples == 33 and summary.distinct_calls == 2
    assert summary.largest_share == pytest.approx(32 / 33)
    assert summary.longest_streak == 32 and not summary.small_sample
    assert summary.advisory_warning
    evidence.record(replace(obs, down=3), "offense", "9", fallback=False)
    assert evidence.summaries()[1].small_sample
    assert not evidence.summaries()[1].advisory_warning


def test_preference_capture_preserves_actual_rng_and_records_normalized_weights() -> None:
    coach = BaselineCoach(31)
    obs = observation(down=3, distance=12)
    before = getstate()
    with audit.capture_preferences(coach) as draws:
        call = coach.offense(obs)
    assert call == BaselineCoach(31).offense(obs) and getstate() == before
    assert len(draws) == 1
    assert sum(draws[0].values()) == pytest.approx(1)
    assert draws[0]["1"] / draws[0]["9"] == pytest.approx(0.45)
    assert set(draws[0]) == set(obs.offense)


def test_stand_in_receives_fourth_down_kicks_and_does_not_kick_after_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = []
    original = BaselineCoach.offense
    kick = SavedGame.kick

    def offense(self: BaselineCoach, obs: CoachObservation) -> str:
        if self._seed == 9871 and obs.down == 4:
            seen.append(obs.special)
        return original(self, obs)

    def guarded_kick(self: SavedGame, key: str) -> PlayReport:
        assert not self.view().finished, "kick attempted after game over"
        return kick(self, key)

    monkeypatch.setattr(BaselineCoach, "offense", offense)
    monkeypatch.setattr(SavedGame, "kick", guarded_kick)
    result = audit.audit_game(
        *sample_teams(), seed=101, coach_seed=31, policy="baseline", cpu_side="away"
    )
    assert result.finished and seen
    assert all("punt" in menu or "field_goal" in menu for menu in seen)
    assert result.stand_in_calls["punt"] > 0


@pytest.mark.parametrize("policy", ["baseline", "hard-v1"])
def test_complete_audit_has_actual_preferences_periods_and_replayed_steps(policy: str) -> None:
    result = audit.audit_game(
        *sample_teams(),
        seed=101,
        coach_seed=31,
        policy=policy,
        cpu_side="away",
        replay_checkpoint=2,
    )
    assert result.replayed_steps > 0 and result.save_continuation_verified
    assert result.call_records
    assert len(result.call_records) == sum(sum(c.values()) for c in result.calls.values())
    for record in result.call_records:
        assert sum(record.preferences.values()) == pytest.approx(1)
        assert record.preferences[record.key] > 0
    assert tuple(map(sum, zip(*result.period_scores, strict=True))) == (
        result.home_score,
        result.away_score,
    )


def test_replay_mismatch_is_a_failure_not_a_success_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    original = audit.loads_game

    def corrupt(*args: object, **kwargs: object) -> SavedGame:
        restored = original(*args, **kwargs)
        current = restored.view
        restored.view = lambda: replace(current(), status="synthetic replay divergence")
        return restored

    monkeypatch.setattr(audit, "loads_game", corrupt)
    with pytest.raises(ValueError, match="saved future"):
        audit.audit_game(
            *sample_teams(), seed=101, coach_seed=31, policy="baseline", cpu_side="away"
        )


def test_period_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="period"):
        audit.reconcile_period_scores(((7, 0), (0, 3)), (8, 3))


@pytest.mark.parametrize("checkpoint", [-1, True, 1.5])
def test_bad_replay_checkpoint_is_rejected(checkpoint: object) -> None:
    with pytest.raises(ValueError, match="checkpoint"):
        audit.audit_game(
            *sample_teams(),
            seed=101,
            coach_seed=31,
            policy="baseline",
            cpu_side="away",
            replay_checkpoint=checkpoint,
        )


def test_json_runner_uses_public_sample_matrix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen = []

    def compare(
        seeds: tuple[int, ...], *, policies: tuple[str, ...]
    ) -> tuple[audit.GameAudit, ...]:
        seen.append((seeds, policies))
        return ()

    monkeypatch.setattr(audit, "compare_policies", compare)
    assert audit.main(["--seeds", "101", "307", "--policies", "baseline"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema_version"] == 1 and result["games"] == []
    assert seen == [((101, 307), ("baseline",))]


def test_json_runner_redacts_engine_exception_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic-private-chart-and-path")

    monkeypatch.setattr(audit, "compare_policies", fail)
    assert audit.main(["--seeds", "101", "307"]) == 1
    captured = capsys.readouterr()
    assert "synthetic-private-chart-and-path" not in captured.out + captured.err
    assert json.loads(captured.err)["error"] == "audit failed"


def test_hashed_coaching_seeds_fit_the_existing_save_contract() -> None:
    assert all(0 <= audit.audit_seed(seed, "synthetic-coach") <= 2**63 - 1 for seed in range(32))


def test_preference_capture_excludes_next_turn_previews() -> None:
    coach = BaselineCoach(31)
    current = observation(down=3, distance=12)
    with audit.capture_preferences(coach, observation=current) as draws:
        coach.offense(current)
        coach.defense(replace(current, play_number=1))
    assert len(draws) == 1 and set(draws[0]) == set(current.offense)


def test_json_serialization_preserves_counter_counts_not_counted_pairs() -> None:
    from collections import Counter

    record = audit.CallRecord(observation(), "offense", "1", False, {"1": 1.0})
    output = json.loads(
        json.dumps({"records": (record,), "calls": Counter({"1": 3})}, default=audit._json_default)
    )
    assert output["calls"] == {"1": 3}
    assert output["records"][0]["preferences"] == {"1": 1.0}


@pytest.mark.parametrize(
    "preferences", [{"illegal": 1.0}, {"1": 0.5}, {"1": float("nan")}, {"1": 0.0, "2": 1.0}]
)
def test_invalid_call_preferences_do_not_become_committed_evidence(
    preferences: dict[str, float],
) -> None:
    evidence = audit.CallAudit()
    with pytest.raises(ValueError, match="preference vector"):
        evidence.record(observation(), "offense", "1", fallback=False, preferences=preferences)
    assert not evidence.records and not evidence.calls["offense"]


def test_preference_observation_handles_uniform_and_cumulative_weights() -> None:
    from random import Random

    from bowl_bound.coaching_audit_sampling import _ObservedRandom

    source, reference = Random(17), Random(17)
    draws = []
    sampler = _ObservedRandom(source, draws)
    assert sampler.choices(("A", "F")) == reference.choices(("A", "F"))
    assert draws[-1] == {"A": 0.5, "F": 0.5}
    assert sampler.choices(("A", "F"), cum_weights=(1, 4)) == reference.choices(
        ("A", "F"), cum_weights=(1, 4)
    )
    assert draws[-1] == {"A": 0.25, "F": 0.75}
