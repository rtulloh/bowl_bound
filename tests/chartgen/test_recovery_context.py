"""Fictional college recovery/try cases; no historical input or network."""

import pytest

from tools.chartgen.evidence import Event, classify_espn, summarize_events
from tools.chartgen.generate import _recovery_probability


def provider_row(**changes: object) -> dict[str, object]:
    return {
        "season": 2007,
        "game_id": "fictional-recovery",
        "id": "p1",
        "pos_team_id": 1,
        "def_pos_team_id": 2,
        "pos_team": "Cedar Valley",
        "def_pos_team": "Harbor Tech",
        "type.text": "Rush",
        "rush": True,
        "statYardage": -4,
        "yds_rushed": -4,
        "text": "Runner rush for a loss of 4 yards, fumbled, recovered by Cedar Valley Runner.",
        "fumble_vec": True,
        "fumbling_team": 1,
        "fumble_lost": True,
        "change_of_pos_team": True,
        "pos_fumble_lost": False,
        "def_fumble_lost": False,
        "recovery_team": 1,
        "fumble_recovery_team": 1,
        **changes,
    }


def event(**changes: object) -> Event:
    result = classify_espn(provider_row(**changes))
    assert result is not None
    return result


@pytest.mark.parametrize("label", ["Rush", "Safety", "Fumble Recovery (Own) Touchdown"])
def test_next_possession_flag_does_not_overrule_own_first_recovery(label: str) -> None:
    result = event(**{"type.text": label})
    assert result.fumble_lost is False
    assert result.net_possession_fumble_lost is True
    assert result.recovery_confidence == "provider-parsed"
    probability, diagnostics = _recovery_probability([result], [result])
    assert probability == 1
    assert diagnostics["known_team_samples"] == 1


def test_inferred_provider_recovery_is_not_labeled_directly_observed() -> None:
    result = event(recovery_team=None)
    assert result.recovery_team is None
    assert result.provider_recovery_team == "1"
    assert result.recovery_confidence == "provider-inferred"
    assert result.net_possession_fumble_lost is True
    assert "provider-inferred:fumble_recovery_team" in result.recovery_evidence


def test_two_losses_are_not_reduced_to_final_possession() -> None:
    result = event(
        text=(
            "Runner fumbled, recovered by Harbor Tech Returner, "
            "fumbled, recovered by Cedar Valley Runner."
        ),
        recovery_team=2,
        fumble_recovery_team=2,
        recovery_team_2=1,
        fumble_lost=False,
        change_of_pos_team=False,
        pos_fumble_lost=True,
        def_fumble_lost=True,
    )
    assert result.fumble_count == 2
    assert result.recovery_team == "2" and result.recovery_team_2 == "1"
    assert result.fumble_lost is True
    assert result.net_possession_fumble_lost is False
    probability, diagnostics = _recovery_probability([result], [result])
    assert probability == 0
    assert diagnostics["known_team_samples"] == 2


def test_missing_second_recovery_stays_unknown_even_when_end_team_is_known() -> None:
    result = event(
        text="Runner fumbled, recovered by Returner, fumbled, recovered by Runner.",
        recovery_team=2,
        fumble_recovery_team=2,
        recovery_team_2=None,
        **{"end.pos_team.id": 1},
    )
    assert result.fumble_count == 2
    assert result.recovery_team_2 is None
    _, diagnostics = _recovery_probability([result], [result])
    assert diagnostics["unknown_recovery_steps"] == 1


def test_ball_out_of_endzone_does_not_invent_a_physical_recoverer() -> None:
    result = event(
        **{
            "type.text": "Safety",
            "text": "Team fumbled in the endzone, ball out-of-bounds for a SAFETY.",
            "recovery_team": None,
        }
    )
    assert result.fumble is True
    assert result.recovery_team is None
    assert result.recovery_confidence == "unknown"
    assert result.net_possession_fumble_lost is True


def test_defensive_try_return_retains_two_points_and_stays_out_of_scrimmage() -> None:
    result = event(
        **{
            "type.text": "Defensive 2pt Conversion",
            "text": (
                "Two-point conversion attempt, Runner fumble recovered by Returner "
                "and returned for a defensive two-point conversion."
            ),
            "rush": True,
            "recovery_team": 2,
            "fumble_recovery_team": 2,
        }
    )
    assert result.event_phase == "try" and result.kind == "other"
    assert result.try_points == 2 and result.try_scoring_team == "2"
    assert result.fumble is True
    summary = summarize_events([result], "1")
    assert summary["rush_attempts"] == 0 and summary["scrimmage_fumbles"] == 0
    own = event()
    probability, diagnostics = _recovery_probability([own, result], [own, result])
    assert probability == 1 and diagnostics["known_team_samples"] == 1


def test_repeated_touchdown_text_in_pat_does_not_create_another_ordinary_fumble() -> None:
    result = event(
        **{
            "type.text": "Extra Point Good",
            "text": "Returner returned fumble for a TOUCHDOWN. Kicker extra point GOOD.",
            "rush": False,
            "xp_attempt": True,
        }
    )
    assert result.event_phase == "try" and result.kind == "pat"
    assert result.try_points == 1 and result.try_scoring_team == "1"
    assert result.prior_touchdown_mention is True
    own = event()
    _, diagnostics = _recovery_probability([own, result], [own, result])
    assert diagnostics["known_team_samples"] == 1
    assert result.source_text.endswith("extra point GOOD.")


def test_explicit_identity_conflict_still_requires_reconciliation() -> None:
    with pytest.raises(ValueError, match="conflicting recovery"):
        event(recovery_team=1, fumble_recovery_team=2)


def test_new_context_roundtrip_preserves_raw_net_flag_and_unknown_chain() -> None:
    result = event(
        text="Runner fumbled, recovered by Returner, fumbled, recovered by Runner.",
        recovery_team_2=None,
    )
    loaded = Event.from_dict(result.to_dict())
    assert loaded == result
    assert loaded.net_possession_fumble_lost is True
    assert loaded.fumble_count == 2 and loaded.recovery_team_2 is None


def test_defensive_recovery_return_does_not_replace_originating_gain_or_force_td() -> None:
    result = event(
        **{
            "type.text": "Fumble Recovery (Opponent) Touchdown",
            "type.id": "5",
            "text": (
                "Runner rush for 3 yards, fumbled, recovered by Harbor Tech Returner "
                "for 70 yards for a TOUCHDOWN."
            ),
            "statYardage": 3,
            "yds_rushed": 3,
            "yds_fumble_return": 70,
            "recovery_team": 2,
            "fumble_recovery_team": 2,
            "fumble_lost": False,
            "change_of_pos_team": False,
            "pos_fumble_lost": True,
            "touchdown": True,
        }
    )
    assert result.kind == "rush" and result.yards == 3
    assert result.return_yards == 70
    assert result.fumble_lost is True
    assert result.event_phase == "scrimmage"


def test_original_pat_identity_survives_a_provider_recovery_td_relabel() -> None:
    result = event(
        **{
            "type.text": "Fumble Recovery (Opponent) Touchdown",
            "type.id": "61",
            "text": "Returner fumble return for a TOUCHDOWN. Kicker extra point GOOD.",
            "rush": False,
            "xp_attempt": True,
            "xp_made": True,
            "kicking_team": 2,
        }
    )
    assert result.event_phase == "try" and result.kind == "pat"
    assert result.team == "2" and result.try_scoring_team == "2"
    assert result.prior_touchdown_mention is True
    own = event()
    _, diagnostics = _recovery_probability([own, result], [own, result])
    assert diagnostics["known_team_samples"] == 1


def test_unknown_try_owner_is_retained_without_fabricated_pat_team() -> None:
    result = event(
        **{
            "type.text": "Fumble Recovery (Opponent) Touchdown",
            "type.id": "61",
            "text": "Returner fumble return for a TOUCHDOWN. Kicker extra point GOOD.",
            "rush": False,
            "xp_attempt": True,
            "xp_made": True,
            "kicking_team": None,
            "end.pos_team.id": 2,
        }
    )
    assert result.event_phase == "try" and result.kind == "other"
    assert result.try_points == 1 and result.try_scoring_team is None
    assert result.prior_touchdown_mention is True


def test_unidentified_provider_recovery_is_not_used_as_observed_estimator_sample() -> None:
    inferred = event(recovery_team=None, fumble_recovery_team=2)
    observed = event()
    probability, diagnostics = _recovery_probability([observed, inferred], [observed, inferred])
    assert probability == 1
    assert diagnostics["known_team_samples"] == 1
    assert diagnostics["unknown_recovery_steps"] == 1


def test_team_placeholder_does_not_establish_physical_recovery() -> None:
    result = event(text="Runner sacked, fumbled, recovered by Team for a SAFETY.")
    assert result.recovery_team is None
    assert result.provider_recovery_team == "1"
    assert result.recovery_confidence == "unknown"
    assert result.fumble_lost is None


def test_non_try_recovery_td_keeps_normal_engine_endpoint_semantics() -> None:
    result = event(**{"type.text": "Fumble Recovery (Own) Touchdown", "touchdown": True})
    assert result.touchdown is True
    assert result.kind == "rush" and result.yards == -4
    assert result.recovery_team == "1" and result.fumble_lost is False


def test_team_recovery_estimate_separates_own_and_opponent_chain_steps() -> None:
    result = event(
        text="Runner fumbled, recovered by Returner, fumbled, recovered by Returner.",
        recovery_team=2,
        fumble_recovery_team=2,
        recovery_team_2=2,
    )
    probability, diagnostics = _recovery_probability([result], [result], team="1")
    assert probability == 0.5  # One lost local fumble plus one retained other-team fumble.
    assert diagnostics["known_team_samples"] == 1
    assert diagnostics["other_team_samples"] == 1


@pytest.mark.parametrize("conversion_kind", ["rush", "complete"])
def test_try_phase_is_not_reintroduced_by_a_source_neutral_kind(conversion_kind: str) -> None:
    from dataclasses import replace

    from bowl_bound.models import Play
    from tools.chartgen.empirical import empirical_vectors, family_pool
    from tools.chartgen.generate import EvidenceModel
    from tools.chartgen.refine import source_targets

    ordinary = event(id="ordinary")
    conversion = replace(event(id="conversion"), event_phase="try", kind=conversion_kind, yards=90)
    assert summarize_events([ordinary, conversion], "1")["rush_attempts"] == 1
    vectors = empirical_vectors([ordinary, conversion], "1")
    assert vectors.unknown_runs == (ordinary,)
    pool = family_pool(vectors, Play.ONE, [conversion], team="1")
    assert all(record.event != conversion for record in pool.observations)
    passing = event(
        id="pass",
        rush=False,
        **{"type.text": "Pass Completion", "pass": True, "completion": True, "yds_receiving": 8},
    )
    targets = source_targets([ordinary, conversion, passing], ["1"])
    assert targets["pure_rush_yards_per_attempt"] == -4
    assert targets["pass_yards_per_attempt"] == 8
    model = EvidenceModel.from_events([ordinary, conversion, passing])
    assert conversion not in model.live
    assert conversion not in model.by_team["1"]


@pytest.mark.parametrize(
    "changes",
    [
        {"fumble_count": -1},
        {"fumble_count": True},
        {"recovery_team_2": "3"},
        {"provider_recovery_team": "3"},
        {"net_possession_fumble_lost": "true"},
        {"try_points": 6},
        {"try_points": True},
        {"try_scoring_team": "3"},
        {"event_phase": "invented"},
        {"recovery_confidence": "certain"},
    ],
)
def test_normalized_context_rejects_malformed_facts(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Event.from_dict(event().to_dict() | changes)


def test_sparse_team_recovery_uses_real_other_pbp_without_fabricated_prior() -> None:
    from dataclasses import replace

    local = event(id="local")
    others = [
        replace(
            event(id=f"other-{i}", recovery_team=2, fumble_recovery_team=2),
            team="2",
            opponent="1",
            fumble_team="2",
            recovery_team="1",
            provider_recovery_team="1",
            fumble_lost=True,
        )
        for i in range(9)
    ]
    probability, diagnostics = _recovery_probability([local], [local, *others], team="1")
    assert probability == pytest.approx(0.1)
    assert diagnostics["known_team_samples"] == 1
    assert diagnostics["modeled_samples"] == 10
    assert diagnostics["other_team_samples"] == 9
    assert diagnostics["effective_sample_size"] == 10
    assert diagnostics["method"] == "sparse-team-plus-league-PBP"
