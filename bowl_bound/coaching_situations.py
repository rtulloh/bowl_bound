"""Shared public-situation bucketing for coaching and its audits."""

from dataclasses import replace

from .coaching import CoachObservation

SituationBucket = tuple[CoachObservation, str]


def situation_bucket(observation: CoachObservation, role: str) -> SituationBucket:
    """Return the audit's comparable public situation for one decision role.

    Keep side, role, down, quarter, overtime, hurry, phase, and legal menus exact.
    Pool distance at <=3/<=6/<=10/long; field at <=20/<=50/<=80/deep; time at
    <=60/<=120/<=180/ordinary; score at tied/one-score/multiple, preserving
    lead versus deficit. Play number is excluded.
    """
    if role not in {"offense", "defense", "decision"}:
        raise ValueError("coaching role must be offense, defense or decision")

    def band(value: int, bounds: tuple[int, ...]) -> int:
        return sum(value > bound for bound in bounds)

    score = observation.score_difference
    pooled = replace(
        observation,
        play_number=0,
        distance=band(observation.distance, (3, 6, 10)),
        yards_to_goal=band(observation.yards_to_goal, (20, 50, 80)),
        remaining=band(observation.remaining, (60, 120, 180)),
        score_difference=(1 if score > 0 else -1) * (1 if abs(score) <= 8 else 2) if score else 0,
    )
    return pooled, role
