"""Authored tactical policy, synthetic effects and isolated reference diagnostics.

Production generation accepts neutral, authored or synthetic profiles. Reference-derived
profiles are rejected by the generator; studying them cannot supply baseline or
refinement strengths, bounds, placement targets, or selection criteria.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from statistics import mean
from typing import Any

from bowl_bound.models import Defense, Play, Priority, ResultKind, TeamChart

from .generate import defensive_weights

APPROVED_YARDAGE_POLICY_SHA256 = "bbb35953b3812769bde39d5c567fc21dece00b0899cb037feaad0db7aa88280c"


@dataclass(frozen=True)
class TacticDelta:
    formation: Defense
    play: Play
    yard_offset: float = 0.0
    incomplete_delta: float = 0.0
    interception_delta: float = 0.0
    sack_delta: float = 0.0
    scramble_delta: float = 0.0
    breakaway_delta: float = 0.0
    override_delta: float = 0.0

    def __post_init__(self) -> None:
        if type(self.formation) is not Defense or type(self.play) is not Play:
            raise ValueError("tactic address needs a Bowl Bound formation and play")
        for field in fields(self)[2:]:
            value = getattr(self, field.name)
            bound = 4 if field.name == "yard_offset" else 0.12
            if not math.isfinite(value) or abs(value) > bound + 1e-9:
                raise ValueError("tactical effects exceed finite predeclared bounds")


@dataclass(frozen=True)
class TacticalProfile:
    effects: tuple[TacticDelta, ...]
    origin: str
    source_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        addresses = {(effect.formation, effect.play) for effect in self.effects}
        if len(self.effects) != 54 or len(addresses) != 54:
            raise ValueError("tactical profile needs exactly 54 unique addresses")
        if self.origin not in {
            "neutral",
            "authored-bb-v1",
            "authored-bb-yardage-v1",
            "synthetic",
            "reference-derived",
        }:
            raise ValueError("unknown tactical prior origin")
        for play in Play:
            observations = [effect for effect in self.effects if effect.play is play]
            for field in fields(TacticDelta)[2:]:
                if abs(sum(getattr(effect, field.name) for effect in observations)) > 1e-7:
                    raise ValueError(
                        "tactical priors must be centered per play, independent of team strength"
                    )

    @classmethod
    def neutral(cls) -> TacticalProfile:
        return cls(
            tuple(TacticDelta(formation, play) for formation in Defense for play in Play),
            "neutral",
            (),
        )

    @classmethod
    def bowl_bound_yardage_v1(cls) -> TacticalProfile:
        """Return the selected original experimental numeric-only tactical policy.

        These are authored counterplay coefficients, not observed formation
        effects. Response-rate deltas remain zero; source allocation is unchanged.
        The rejected probability-changing proposal is not a construction input.
        """
        yardage = (
            (0, -2, 0, 1, 2, -1),
            (0, -2, -1, 1, 2, 0),
            (0, 2, -3, 0, 1, 0),
            (0, -2, -1, 0, 1, 2),
            (0, -1, -2, 1, 2, 0),
            (0, 0, 0, -3, 1, 2),
            (0, 1, -1, -2, 3, -1),
            (0, 1, 1, -1, -2, 1),
            (0, 2, 2, 0, -3, -1),
        )
        effects = tuple(
            TacticDelta(formation, play, yard_offset=yardage[play.value - 1][index])
            for play in Play
            for index, formation in enumerate(Defense)
        )
        return cls(effects, "authored-bb-yardage-v1", ())

    @classmethod
    def for_corrected_release(cls, expected_sha256: str) -> TacticalProfile:
        """Require the explicitly selected reviewed policy and immutable hash."""
        profile = cls.bowl_bound_yardage_v1()
        if expected_sha256 != APPROVED_YARDAGE_POLICY_SHA256 or profile.sha256 != expected_sha256:
            raise ValueError("corrected release requires the approved tactical policy hash")
        return profile

    def lookup(self, formation: Defense, play: Play) -> TacticDelta:
        return next(
            effect
            for effect in self.effects
            if effect.formation is formation and effect.play is play
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "origin": self.origin,
            "source_hashes": list(self.source_hashes),
            "effects": [asdict(effect) for effect in self.effects],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TacticalProfile:
        if (
            set(value) != {"schema_version", "origin", "source_hashes", "effects"}
            or value["schema_version"] != 1
        ):
            raise ValueError("unsupported tactical profile schema")
        effects = tuple(
            TacticDelta(
                **(
                    record
                    | {"formation": Defense(record["formation"]), "play": Play(record["play"])}
                )
            )
            for record in value["effects"]
        )
        return cls(effects, value["origin"], tuple(value["source_hashes"]))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


def learn_tactics(charts: Sequence[TeamChart]) -> TacticalProfile:
    """Retain a legacy descriptive audit; its result is forbidden as generation input.

    Pool within-team centered formation effects, with a fixed 50% shrinkage.

    Chart response frequencies are structural priors, not observed formations in
    PBP. Negative rate deltas identify relative opportunities; generation uses
    only feasible positive responses, and reports the resulting quantization.
    """
    if not charts:
        raise ValueError("tactical estimation requires authorized reference charts")
    metrics = [field.name for field in fields(TacticDelta)[2:]]
    samples: dict[tuple[Defense, Play], dict[str, list[float]]] = {
        (formation, play): {metric: [] for metric in metrics}
        for formation in Defense
        for play in Play
    }
    weights = defensive_weights()
    for chart in charts:
        raw = {}
        for formation in Defense:
            for play in Play:
                records = [
                    record
                    for record in chart.defense
                    if record.defense is formation and record.play is play
                ]
                totals = dict.fromkeys(metrics, 0.0)
                for record in records:
                    cell, mass = record.cell, weights[record.roll] / 36
                    if cell.kind is ResultKind.YARDS:
                        totals["yard_offset"] += cell.yards * mass
                    mapping = {
                        ResultKind.INCOMPLETE: "incomplete_delta",
                        ResultKind.INTERCEPTION: "interception_delta",
                        ResultKind.QUARTERBACK_TRAPPED: "sack_delta",
                        ResultKind.QUARTERBACK_RUN: "scramble_delta",
                        ResultKind.BREAKAWAY: "breakaway_delta",
                    }
                    if cell.kind in mapping:
                        totals[mapping[cell.kind]] += mass
                    if cell.priority is not Priority.NORMAL and cell.kind is ResultKind.YARDS:
                        totals["override_delta"] += mass
                raw[formation, play] = totals
        for play in Play:
            for metric in metrics:
                center = mean(raw[formation, play][metric] for formation in Defense)
                for formation in Defense:
                    samples[formation, play][metric].append(raw[formation, play][metric] - center)
    pooled = {
        address: {metric: 0.5 * mean(values) for metric, values in observations.items()}
        for address, observations in samples.items()
    }
    for play in Play:
        for metric in metrics:
            bound = 4 if metric == "yard_offset" else 0.12
            largest = max(abs(pooled[formation, play][metric]) for formation in Defense)
            scale = min(1, bound / largest) if largest else 1
            for formation in Defense:
                pooled[formation, play][metric] *= scale
    effects = tuple(
        TacticDelta(formation, play, **pooled[formation, play])
        for formation in Defense
        for play in Play
    )
    hashes = tuple(
        sorted(
            {record.cell.provenance.source_sha256 for chart in charts for record in chart.defense}
        )
    )
    return TacticalProfile(effects, "reference-derived", hashes)
