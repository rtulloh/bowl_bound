"""Immutable coaching preferences, never football rules or runtime tuning knobs.

Changing a value requires a new policy version: existing saved policies retain
their selection streams. Names are diagnostic and are not added to RNG inputs.
"""

from dataclasses import dataclass, replace

CURRENT_DIFFICULTY_VERSION = 12


@dataclass(frozen=True)
class CoachBehavior:
    """Versioned choice/analysis bounds; seconds and heuristic utility units.

    Potential coefficients are preferences, not calibrated expected points.
    Run categories are Bowl Bound calls 1–5 versus 6–9, not NFL chart columns.
    """

    name: str
    aggression: float = 0.5
    temperature: float = 0.6
    exploration: float = 0.15
    exploitation: float = 0.85
    cache_entries: int = 128
    recent_calls: int = 6
    analysis_samples: int = 32
    max_analysis_samples: int = 256
    settle_decisions: int = 16
    late_seconds: int = 120
    chase_seconds: int = 180
    protect_seconds: int = 60
    field_goal_yards: int = 30
    punt_distance: int = 2
    passing_distance: int = 3
    baseline_run_weight: float = 0.45
    run_probability_base: float = 0.8
    aggression_divisor: int = 2
    passing_down_run_probability: float = 0.25
    min_run_probability: float = 0.1
    max_run_probability: float = 0.9
    medium_bias_limit: float = 0.2
    medium_bias_divisor: int = 20
    potential_base: int = 2
    potential_progress: int = 4
    potential_exponent: int = 1
    potential_down_discount: float = 0.2
    potential_distance_discount: float = 0.03
    late_lead_bonus: int = 4
    late_tie_bonus: int = 1
    large_lead_points: int = 9
    two_point_tie_margin: int = -2
    two_point_lead_margin: int = -1
    two_point_lead_seconds: int = 60
    two_point_aggression_threshold: float = 0.5
    pressure_points_per_score: int = 7
    pressure_run_shift: float = 0.25
    passing_down_aggression_scale: float = 0.3
    repetition_decay: float = 0.94
    repetition_multiplier: float = 0.9
    repetition_floor: float = 0.30
    defense_goal_line_yards: int = 5
    defense_situation_multiplier: float = 1.5


BASELINE_V1 = CoachBehavior("baseline-v1")
CHART_V1 = replace(BASELINE_V1, name="chart-v1")
EASY_V1 = replace(BASELINE_V1, name="easy-v1", aggression=0.3)
MEDIUM_V1 = replace(BASELINE_V1, name="medium-v1", aggression=0.5)
HARD_V1 = replace(
    BASELINE_V1,
    name="hard-v1",
    aggression=0.7,
    potential_base=-1,
    potential_progress=5,
    potential_exponent=2,
)
BASELINE_V2 = replace(BASELINE_V1, name="baseline-v2")
BASELINE_V8 = replace(BASELINE_V2, name="baseline-v8")
BASELINE_V9 = replace(BASELINE_V8, name="baseline-v9")
BASELINE_V10 = replace(BASELINE_V9, name="baseline-v10")
BASELINE_V11 = replace(BASELINE_V10, name="baseline-v11")
BASELINE_V12 = replace(BASELINE_V11, name="baseline-v12")
CHART_V2 = replace(CHART_V1, name="chart-v2")
EASY_V2 = replace(EASY_V1, name="easy-v2")
MEDIUM_V2 = replace(MEDIUM_V1, name="medium-v2")
HARD_V2 = replace(HARD_V1, name="hard-v2")
CHART_V3 = replace(CHART_V2, name="chart-v3")
EASY_V3 = replace(EASY_V2, name="easy-v3")
MEDIUM_V3 = replace(MEDIUM_V2, name="medium-v3")
HARD_V3 = replace(HARD_V2, name="hard-v3")
CHART_V4 = replace(CHART_V3, name="chart-v4")
EASY_V4 = replace(EASY_V3, name="easy-v4")
MEDIUM_V4 = replace(MEDIUM_V3, name="medium-v4")
HARD_V4 = replace(HARD_V3, name="hard-v4")
CHART_V5 = replace(CHART_V4, name="chart-v5")
EASY_V5 = replace(EASY_V4, name="easy-v5")
MEDIUM_V5 = replace(MEDIUM_V4, name="medium-v5")
HARD_V5 = replace(HARD_V4, name="hard-v5", recent_calls=96)
CHART_V6 = replace(CHART_V5, name="chart-v6")
EASY_V6 = replace(EASY_V5, name="easy-v6")
MEDIUM_V6 = replace(MEDIUM_V5, name="medium-v6")
HARD_V6 = replace(HARD_V5, name="hard-v6")
CHART_V7 = replace(CHART_V6, name="chart-v7")
EASY_V7 = replace(EASY_V6, name="easy-v7")
MEDIUM_V7 = replace(MEDIUM_V6, name="medium-v7")
HARD_V7 = replace(HARD_V6, name="hard-v7")
CHART_V8 = replace(CHART_V7, name="chart-v8")
EASY_V8 = replace(EASY_V7, name="easy-v8")
MEDIUM_V8 = replace(MEDIUM_V7, name="medium-v8")
HARD_V8 = replace(HARD_V7, name="hard-v8")
CHART_V9 = replace(CHART_V8, name="chart-v9")
EASY_V9 = replace(EASY_V8, name="easy-v9")
MEDIUM_V9 = replace(MEDIUM_V8, name="medium-v9")
HARD_V9 = replace(HARD_V8, name="hard-v9")
CHART_V10 = replace(CHART_V9, name="chart-v10")
CHART_V11 = replace(CHART_V10, name="chart-v11")
CHART_V12 = replace(CHART_V11, name="chart-v12")
EASY_V10 = replace(EASY_V9, name="easy-v10")
EASY_V11 = replace(EASY_V10, name="easy-v11")
EASY_V12 = replace(EASY_V11, name="easy-v12")
MEDIUM_V10 = replace(MEDIUM_V9, name="medium-v10")
MEDIUM_V11 = replace(MEDIUM_V10, name="medium-v11")
MEDIUM_V12 = replace(MEDIUM_V11, name="medium-v12")
HARD_V10 = replace(HARD_V9, name="hard-v10")
HARD_V11 = replace(HARD_V10, name="hard-v11")
HARD_V12 = replace(HARD_V11, name="hard-v12")


def behavior_for_policy(policy: str) -> CoachBehavior:
    """Return an immutable profile using the persisted save policy identifier."""
    for key, profile in (
        ("baseline", BASELINE_V1),
        ("chart-v1", CHART_V1),
        ("easy-v1", EASY_V1),
        ("medium-v1", MEDIUM_V1),
        ("hard-v1", HARD_V1),
        ("baseline-v2", BASELINE_V2),
        ("baseline-v8", BASELINE_V8),
        ("baseline-v9", BASELINE_V9),
        ("baseline-v10", BASELINE_V10),
        ("baseline-v11", BASELINE_V11),
        ("baseline-v12", BASELINE_V12),
        ("chart-v2", CHART_V2),
        ("easy-v2", EASY_V2),
        ("medium-v2", MEDIUM_V2),
        ("hard-v2", HARD_V2),
        ("chart-v3", CHART_V3),
        ("easy-v3", EASY_V3),
        ("medium-v3", MEDIUM_V3),
        ("hard-v3", HARD_V3),
        ("chart-v4", CHART_V4),
        ("easy-v4", EASY_V4),
        ("medium-v4", MEDIUM_V4),
        ("hard-v4", HARD_V4),
        ("chart-v5", CHART_V5),
        ("easy-v5", EASY_V5),
        ("medium-v5", MEDIUM_V5),
        ("hard-v5", HARD_V5),
        ("chart-v6", CHART_V6),
        ("easy-v6", EASY_V6),
        ("medium-v6", MEDIUM_V6),
        ("hard-v6", HARD_V6),
        ("chart-v7", CHART_V7),
        ("easy-v7", EASY_V7),
        ("medium-v7", MEDIUM_V7),
        ("hard-v7", HARD_V7),
        ("chart-v8", CHART_V8),
        ("easy-v8", EASY_V8),
        ("medium-v8", MEDIUM_V8),
        ("hard-v8", HARD_V8),
        ("chart-v9", CHART_V9),
        ("easy-v9", EASY_V9),
        ("medium-v9", MEDIUM_V9),
        ("hard-v9", HARD_V9),
        ("chart-v10", CHART_V10),
        ("chart-v11", CHART_V11),
        ("chart-v12", CHART_V12),
        ("easy-v10", EASY_V10),
        ("easy-v11", EASY_V11),
        ("easy-v12", EASY_V12),
        ("medium-v10", MEDIUM_V10),
        ("medium-v11", MEDIUM_V11),
        ("medium-v12", MEDIUM_V12),
        ("hard-v10", HARD_V10),
        ("hard-v11", HARD_V11),
        ("hard-v12", HARD_V12),
    ):
        if policy == key:
            return profile
    raise ValueError("unknown coaching policy")


@dataclass(frozen=True)
class AuditBehavior:
    """Development evidence thresholds; advisory only, never usage constraints."""

    name: str = "coaching-audit-v1"
    replay_checkpoint: int = 40
    min_concentration_samples: int = 30
    concentration_share: float = 0.5


AUDIT_V1 = AuditBehavior()
