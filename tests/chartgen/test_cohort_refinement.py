"""Synthetic identifiable/sparse residual updates and globally excluded source games."""

from dataclasses import asdict

from tools.chartgen.generate import CalibrationProfile, DefensiveProfile

from .test_scope import events


def test_regularized_updates_are_bounded_independent_and_sparse_aware() -> None:
    from tools.chartgen.cohort_refinement import propose_team_profiles

    target = {
        "rush_yards_per_attempt": 4.0,
        "pass_yards_per_attempt": 6.0,
        "completion": 0.6,
        "interception": 0.03,
        "sack": 0.06,
        "fumble": 0.02,
    }
    measured = {k: {"value": v, "n": 2000} for k, v in target.items()}
    measured["rush_yards_per_attempt"]["value"] = 6
    own = CalibrationProfile()
    defense = DefensiveProfile()
    next_own, next_defense, diagnostic = propose_team_profiles(
        own, defense, measured, measured, target, target
    )
    assert 0.6 < next_own.run_yards_scale < 1
    assert -2 < next_defense.run_yards_offset < 0
    assert next_own.completion_shift == 0 and next_defense.completion_shift == 0
    assert diagnostic["shrinkage_pseudo_samples"] == 1000
    sparse = {k: {"value": 20.0, "n": 12} for k in target}
    unchanged, unchanged_def, d = propose_team_profiles(
        own, defense, sparse, sparse, target, target
    )
    assert unchanged == own and unchanged_def == defense
    assert d["unidentifiable_or_sparse_metrics"]
    assert asdict(next_own) != asdict(own)


def test_source_holdout_excludes_game_from_both_sides_and_every_fit() -> None:
    from tools.chartgen.cohort_refinement import source_game_partition

    source = events("train", "a", "b") + events("withheld", "a", "c")
    train, heldout = source_game_partition(source, {"withheld"})
    assert {e.game_id for e in train} == {"train"}
    assert {e.game_id for e in heldout} == {"withheld"}
    assert {e.team for e in heldout} == {"a", "c"}
    assert not any(e.opponent == "c" for e in train)


def test_missing_target_has_no_update() -> None:
    from tools.chartgen.cohort_refinement import propose_team_profiles

    own, defense = CalibrationProfile(), DefensiveProfile()
    measured = {"completion": {"n": 2000, "value": 0.7}}
    next_own, next_defense, diagnostic = propose_team_profiles(
        own, defense, measured, measured, {}, {}
    )
    assert next_own == own and next_defense == defense
    assert "offense/source:completion" in diagnostic["unidentifiable_or_sparse_metrics"]


def test_all_profile_bounds_are_recordable() -> None:
    from tools.chartgen.cohort_refinement import profile_bounds

    own, defense = CalibrationProfile(), DefensiveProfile()
    bounds = profile_bounds()
    assert set(bounds["offense"]) == set(asdict(own))
    assert set(bounds["defense"]) == set(asdict(defense))
    assert bounds["offense"]["run_yards_scale"] == [0.6, 1.4]
    assert bounds["defense"]["completion_shift"] == [-0.08, 0.08]
