"""Immutable coaching preferences, never football rules or runtime tuning knobs.

Changing a value requires a new policy version: existing saved policies retain
their selection streams. Names are diagnostic and are not added to RNG inputs.
"""

from dataclasses import dataclass, replace


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
CHART_V2 = replace(CHART_V1, name="chart-v2")
EASY_V2 = replace(EASY_V1, name="easy-v2")
MEDIUM_V2 = replace(MEDIUM_V1, name="medium-v2")
HARD_V2 = replace(HARD_V1, name="hard-v2")
CHART_V3 = replace(CHART_V2, name="chart-v3")
EASY_V3 = replace(EASY_V2, name="easy-v3")
MEDIUM_V3 = replace(MEDIUM_V2, name="medium-v3")
HARD_V3 = replace(HARD_V2, name="hard-v3")


def behavior_for_policy(policy: str) -> CoachBehavior:
    """Return an immutable profile using the persisted save policy identifier."""
    for key, profile in (
        ("baseline", BASELINE_V1),
        ("chart-v1", CHART_V1),
        ("easy-v1", EASY_V1),
        ("medium-v1", MEDIUM_V1),
        ("hard-v1", HARD_V1),
        ("baseline-v2", BASELINE_V2),
        ("chart-v2", CHART_V2),
        ("easy-v2", EASY_V2),
        ("medium-v2", MEDIUM_V2),
        ("hard-v2", HARD_V2),
        ("chart-v3", CHART_V3),
        ("easy-v3", EASY_V3),
        ("medium-v3", MEDIUM_V3),
        ("hard-v3", HARD_V3),
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
