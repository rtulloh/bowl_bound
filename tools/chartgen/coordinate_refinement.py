"""Bounded independent coordinate probes; no football or reference interpreter."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence, Set
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

from .generate import CalibrationProfile, DefensiveProfile

METRIC_ORDER = (
    "completion",
    "interception",
    "sack",
    "fumble",
    "pure_rush_yards_per_attempt",
    "pass_yards_per_attempt",
    "drawn_punt_return_yards",
    "drawn_kickoff_return_yards",
    "drawn_interception_return_yards",
)
KNOBS = {
    "offense": {
        "completion": "completion_shift",
        "interception": "interception_scale",
        "sack": "sack_scale",
        "fumble": "fumble_scale",
        "pure_rush_yards_per_attempt": "run_yards_scale",
        "pass_yards_per_attempt": "pass_yards_scale",
        **{name: "return_yards_scale" for name in METRIC_ORDER if name.startswith("drawn_")},
    },
    "defense": {
        "completion": "completion_shift",
        "interception": "interception_shift",
        "sack": "sack_shift",
        "pure_rush_yards_per_attempt": "run_yards_offset",
        "pass_yards_per_attempt": "pass_yards_offset",
    },
}


@dataclass(frozen=True)
class Coordinate:
    """One source-qualified measurable residual and its bounded proposal hint."""

    team: str
    role: Literal["offense", "defense"]
    metric: str
    knob: str
    proposed: float
    normalized_error: float
    source_qualified: bool

    def __post_init__(self) -> None:
        if self.role not in KNOBS or KNOBS[self.role].get(self.metric) != self.knob:
            raise ValueError("coordinate needs an identified metric/role/knob association")
        if (
            not self.team
            or not math.isfinite(self.proposed)
            or not math.isfinite(self.normalized_error)
            or self.normalized_error < 0
        ):
            raise ValueError(
                "coordinate needs a valid identity, finite proposal and finite nonnegative error"
            )
        if type(self.source_qualified) is not bool:
            raise ValueError("coordinate source qualification must be explicit")


def plan_coordinate_probe(
    offense: Mapping[str, CalibrationProfile],
    defense: Mapping[str, DefensiveProfile],
    coordinates: Sequence[Coordinate],
    bounds: Mapping[str, Mapping[str, Sequence[float]]],
    seen_fingerprints: Set[str],
    measured_coordinates: Set[tuple[str, str, str]],
    fingerprint: Callable[[str, CalibrationProfile, DefensiveProfile], str],
    *,
    maximum_trials: int = 64,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Find a distinct generated response before allocating a football batch.

    Every probe changes one knob on one team from a frozen baseline. Two signed
    directions and a finite geometric step ladder stay within declared bounds.
    Failed finite trials remain in the ledger; a trial cap is not a global proof.
    """
    if type(maximum_trials) is not int or maximum_trials < 1:
        raise ValueError("coordinate trial limit must be a positive integer")
    eligible = sorted(
        (
            coordinate
            for coordinate in coordinates
            if coordinate.source_qualified
            and coordinate.normalized_error > 1
            and (coordinate.team, coordinate.role, coordinate.knob) not in measured_coordinates
        ),
        key=lambda coordinate: (
            -coordinate.normalized_error,
            METRIC_ORDER.index(coordinate.metric),
            coordinate.team,
            coordinate.role,
            coordinate.knob,
        ),
    )
    ledger: list[dict[str, Any]] = []
    attempted: set[tuple[str, str, str, float]] = set()
    for coordinate in eligible:
        profiles = offense if coordinate.role == "offense" else defense
        previous = getattr(profiles[coordinate.team], coordinate.knob)
        delta = coordinate.proposed - previous
        if not delta:
            continue
        lower, upper = bounds[coordinate.role][coordinate.knob]
        for multiplier in (1, 2, 4, 8, 16, 32, 64, 128):
            for direction in (1, -1):
                value = round(max(lower, min(upper, previous + direction * multiplier * delta)), 12)
                key = (coordinate.team, coordinate.role, coordinate.knob, value)
                if value == previous or key in attempted:
                    continue
                attempted.add(key)
                own, defended = offense[coordinate.team], defense[coordinate.team]
                if coordinate.role == "offense":
                    own = replace(own, **{coordinate.knob: value})
                else:
                    defended = replace(defended, **{coordinate.knob: value})
                response = fingerprint(coordinate.team, own, defended)
                duplicate = response in seen_fingerprints
                ledger.append(
                    {
                        "coordinate": asdict(coordinate),
                        "previous": previous,
                        "value": value,
                        "fingerprint": response,
                        "reason": "seen_chart_fingerprint"
                        if duplicate
                        else "distinct_coordinate_response",
                    }
                )
                if not duplicate:
                    new_offense, new_defense = dict(offense), dict(defense)
                    new_offense[coordinate.team], new_defense[coordinate.team] = own, defended
                    return {"offense": new_offense, "defense": new_defense, **ledger[-1]}, ledger
                if len(ledger) >= maximum_trials:
                    ledger[-1]["search_stopping"] = "predeclared_trial_limit"
                    return None, ledger
    if not ledger:
        ledger.append(
            {
                "reason": "no_bounded_coordinate_movement"
                if eligible
                else "no_qualified_unmeasured_coordinate"
            }
        )
    else:
        ledger[-1]["search_stopping"] = "finite_declared_coordinate_ladder_exhausted"
    return None, ledger


def combine_beneficial_probes(
    offense: Mapping[str, CalibrationProfile],
    defense: Mapping[str, DefensiveProfile],
    probes: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, CalibrationProfile], dict[str, DefensiveProfile], list[int]]:
    """Compose only known locally beneficial training probes, resolving ties early."""
    chosen: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for probe in probes:
        coordinate = probe["coordinate"]
        before, after = probe["local_baseline_loss"], probe["local_probe_loss"]
        if coordinate.get("source_qualified") is not True or before is None or after is None:
            continue
        if not math.isfinite(before) or not math.isfinite(after) or before < 0 or after < 0:
            raise ValueError("joint probe losses must be finite nonnegative or unknown")
        if after >= before:
            continue
        key = coordinate["team"], coordinate["role"], coordinate["knob"]
        previous = chosen.get(key)
        if previous is None or (after, probe["candidate"]) < (
            previous["local_probe_loss"],
            previous["candidate"],
        ):
            chosen[key] = probe
    own, defended = dict(offense), dict(defense)
    for (team, role, knob), probe in sorted(chosen.items()):
        profiles = own if role == "offense" else defended
        profiles[team] = replace(profiles[team], **{knob: probe["value"]})
    return own, defended, sorted(probe["candidate"] for probe in chosen.values())
