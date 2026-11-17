"""Individual-PBP outcome vectors before Bowl Bound encoding or calibration.

Adapted in architecture from Paydirt's EmpiricalChartData boundary, with original
Bowl Bound data types. No NFL mappings, aggregate synthesis or reference inputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from bowl_bound.models import Play

from .evidence import Event

_PASS_KINDS = {"complete", "incomplete", "interception", "sack"}


@dataclass(frozen=True)
class FamilyVector:
    """Whole source outcomes, retaining uncertainty and conditional branches."""

    play: Play
    events: tuple[Event, ...]

    @property
    def numeric_yards(self) -> tuple[int, ...]:
        """Known primary gains only; missing, sack and incomplete are distinct."""
        return tuple(
            event.yards
            for event in self.events
            if event.kind in {"rush", "complete"} and event.yards is not None
        )


@dataclass(frozen=True)
class EmpiricalData:
    families: tuple[FamilyVector, ...]
    unknown_runs: tuple[Event, ...]
    unknown_passes: tuple[Event, ...]
    penalties: tuple[Event, ...]
    special_teams: tuple[Event, ...]

    def family(self, play: Play) -> FamilyVector:
        if type(play) is not Play:
            raise ValueError("empirical family must be a Bowl Bound Play")
        return self.families[play.value - 1]


@dataclass(frozen=True)
class WeightedObservation:
    event: Event
    weight: float


@dataclass(frozen=True)
class EmpiricalPool:
    """Source observations and explicit sparse-pool weights, never synthetic plays."""

    observations: tuple[WeightedObservation, ...]
    method: str
    own_family_samples: int
    league_samples: int

    @property
    def effective_weight(self) -> float:
        return sum(record.weight for record in self.observations)

    @property
    def effective_sample_size(self) -> float:
        squared = sum(record.weight**2 for record in self.observations)
        return self.effective_weight**2 / squared if squared else 0.0


def family_pool(
    vectors: EmpiricalData,
    play: Play,
    league: Sequence[Event],
    *,
    team: str,
    minimum: int = 30,
) -> EmpiricalPool:
    """Pool unidentified same-unit PBP, without stealing other known calls.

    Option terminal observations can inform their resolved pass family. Sparse
    families retain their own outcomes and unknown-call evidence. Other teams'
    unknown-call evidence receives only the remaining minimum-sample weight;
    every original observation is retained and the weight is not a new sample.
    """
    if minimum <= 0:
        raise ValueError("minimum family samples must be positive")
    known = vectors.family(play).events
    if play in {Play.SEVEN, Play.EIGHT}:
        known += tuple(
            event
            for event in vectors.family(Play.FIVE).events
            if event.resolved_family == play.value and event.kind in _PASS_KINDS
        )
    numeric_kind = "rush" if play.value <= 5 else "complete"
    numeric_count = sum(event.kind == numeric_kind and event.yards is not None for event in known)
    if numeric_count >= minimum:
        return EmpiricalPool(
            tuple(WeightedObservation(e, 1.0) for e in known), "family-PBP", len(known), 0
        )
    unit = "run" if play.value <= 5 else "pass"
    unknown = (
        tuple(event for event in vectors.unknown_runs if not event.quarterback_scramble)
        if unit == "run"
        else vectors.unknown_passes
        + tuple(event for event in vectors.unknown_runs if event.quarterback_scramble is True)
    )
    own = known + unknown
    observations = [WeightedObservation(event, 1.0) for event in own]
    own_numeric = sum(event.kind == numeric_kind and event.yards is not None for event in own)
    others = (
        sorted(
            (
                event
                for event in league
                if event.team != team
                and not event.no_play
                and event.event_phase != "try"
                and event.called_family is None
                and (
                    (event.kind == "rush" and not event.quarterback_scramble)
                    if unit == "run"
                    else event.kind in _PASS_KINDS
                    or (event.kind == "rush" and event.quarterback_scramble is True)
                )
            ),
            key=lambda event: (event.game_id, event.event_id, event.team),
        )
        if own_numeric < minimum
        else []
    )
    other_numeric = sum(event.kind == numeric_kind and event.yards is not None for event in others)
    if other_numeric:
        weight = min(1.0, (minimum - own_numeric) / other_numeric)
        observations.extend(WeightedObservation(event, weight) for event in others)
    return EmpiricalPool(
        tuple(observations),
        f"pooled-unidentified-{unit}",
        len(known),
        len(others) if other_numeric else 0,
    )


def empirical_vectors(events: Sequence[Event], team: str) -> EmpiricalData:
    """Partition a team's individual observations, without filling unknown calls.

    No-play events cannot become primary gains. Accepted penalties retain their
    separate evidence even when a live play also occurred. Per-event IDs, return
    ownership, source labels, known zeroes and missing values remain intact.
    """
    own = tuple(
        sorted(
            (event for event in events if event.team == team),
            key=lambda event: (event.game_id, event.event_id),
        )
    )
    live = tuple(event for event in own if not event.no_play)
    primary = tuple(
        event
        for event in live
        if event.event_phase != "try" and (event.kind == "rush" or event.kind in _PASS_KINDS)
    )
    return EmpiricalData(
        tuple(
            FamilyVector(
                play, tuple(event for event in primary if event.called_family == play.value)
            )
            for play in Play
        ),
        tuple(event for event in primary if event.called_family is None and event.kind == "rush"),
        tuple(
            event for event in primary if event.called_family is None and event.kind in _PASS_KINDS
        ),
        tuple(event for event in own if event.penalty and not event.penalty_declined),
        tuple(event for event in live if event.kind in {"punt", "kickoff", "field_goal", "pat"}),
    )
