"""Deterministic empirical quantization into the production Bowl Bound format.

No historical chart values are embedded here. Unobserved tactics use the explicit
neutral baseline or a separately selected authored experimental policy. Physical
row masses come exclusively from engine dice faces.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import product
from pathlib import Path
from random import Random
from statistics import mean
from typing import TYPE_CHECKING, Any

from bowl_bound.dice import BLACK_FACES, GREEN_FACES, RED_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES
from bowl_bound.models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    OffensiveCell,
    PatOutcome,
    Play,
    Provenance,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import (
    LOCAL_PLACEHOLDER_POWER_RATING,
    TeamFileMetadata,
    parse_cell,
    provenance_to_csv,
    team_folder_name,
    team_from_files,
    team_to_files,
)

from .audit import ColumnEvidence, compare_column_distributions
from .empirical import EmpiricalData, WeightedObservation, empirical_vectors, family_pool
from .evidence import Event, summarize_events
from .private_io import private_destination

if TYPE_CHECKING:
    from .tactics import TacticalProfile

TOOL_VERSION = "college-chartgen-v9"
MINIMUM_FAMILY_SAMPLES = 30
MINIMUM_RECOVERY_SAMPLES = 30


@dataclass(frozen=True)
class CalibrationProfile:
    """Bounded response knobs; neutral values define the immutable source baseline."""

    run_yards_scale: float = 1.0
    pass_yards_scale: float = 1.0
    completion_shift: float = 0.0
    interception_scale: float = 1.0
    sack_scale: float = 1.0
    fumble_scale: float = 1.0
    return_yards_scale: float = 1.0
    field_goal_shift: float = 0.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"profile {name} must be finite")
            lower, upper = (-0.15, 0.15) if name.endswith("shift") else (0.6, 1.4)
            if not lower <= value <= upper:
                raise ValueError(f"profile {name} outside bounds [{lower}, {upper}]")


@dataclass(frozen=True)
class DefensiveProfile:
    """Independent bounded residuals; zero preserves the source-fitted defense."""

    run_yards_offset: float = 0.0
    pass_yards_offset: float = 0.0
    completion_shift: float = 0.0
    interception_shift: float = 0.0
    sack_shift: float = 0.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"defensive profile {name} must be finite")
            bound = 2.0 if name.endswith("offset") else 0.08 if name == "completion_shift" else 0.03
            if abs(value) > bound:
                raise ValueError(f"defensive profile {name} outside bounds [-{bound}, {bound}]")


def offensive_weights() -> dict[int, int]:
    return dict(
        sorted(
            Counter(
                10 * b + w + x for b, w, x in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
            ).items()
        )
    )


def defensive_weights() -> dict[int, int]:
    return dict(sorted(Counter(r + g for r, g in product(RED_FACES, GREEN_FACES)).items()))


def _seed(seed: int, label: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{seed}:{label}".encode()).digest()[:8], "big")


def nearest_mass_rows(weights: Mapping[int, int], probability: float, *, seed: int) -> set[int]:
    """Choose an exact subset nearest the requested mass, including rare 1/216 cells."""
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("probability must be finite within [0, 1]")
    rows = list(weights)
    Random(seed).shuffle(rows)
    attainable: dict[int, tuple[int, ...]] = {0: ()}
    for row in rows:
        for mass, chosen in list(attainable.items()):
            attainable.setdefault(mass + weights[row], chosen + (row,))
    target = probability * sum(weights.values())
    best = min(attainable, key=lambda mass: (abs(mass - target), mass))
    return set(attainable[best])


def quantized_defensive_offsets(
    weights: Mapping[int, int], effect: float, *, seed: int
) -> dict[int, int]:
    """Encode a fractional effect using nearest attainable physical dice mass.

    Each row receives one of the adjacent integers. Canonical row ordering and
    seeded equal-mass placement are independent of input mapping insertion order.
    No reference-derived or unexplained absolute yardage clamp is applied.
    """
    if not math.isfinite(effect):
        raise ValueError("defensive effect must be finite")
    if any(type(weight) is not int or weight <= 0 for weight in weights.values()):
        raise ValueError("defensive physical weights must be positive integers")
    ordered = dict(sorted(weights.items()))
    if not ordered:
        return {}
    lower = math.floor(effect)
    upper_rows = nearest_mass_rows(ordered, effect - lower, seed=seed)
    return {row: lower + (row in upper_rows) for row in ordered}


def _column(
    values: Sequence[int],
    specials: Sequence[tuple[str, float]],
    *,
    seed: int,
    out_of_bounds: float = 0.0,
    locations: Mapping[str, Sequence[int]] | None = None,
) -> dict[int, str]:
    weights = offensive_weights()
    result: dict[int, str] = {}
    original_mass = sum(weights.values())
    for index, (token, probability) in enumerate(sorted(specials, key=lambda item: item[1])):
        if probability <= 0:
            continue
        if not weights:
            raise ValueError("special probabilities consume every numeric cell")
        remaining_probability = min(1.0, probability * original_mass / sum(weights.values()))
        selected = nearest_mass_rows(weights, remaining_probability, seed=_seed(seed, str(index)))
        conditional = sorted((locations or {}).get(token, ()))
        if locations is not None and token in locations and not conditional:
            raise ValueError(f"no known {token} location evidence")
        position, mass = 0, sum(weights[row] for row in selected)
        for row in sorted(selected):
            value = (
                conditional[
                    min(
                        len(conditional) - 1,
                        int((position + weights[row] / 2) / mass * len(conditional)),
                    )
                ]
                if conditional
                else None
            )
            result[row] = _location_token(token, value) if value is not None else token
            position += weights[row]
            del weights[row]
    if weights and not values:
        raise ValueError("numeric distribution has no known evidence")
    ordered = list(weights)
    Random(seed).shuffle(ordered)
    numbers = sorted(values)
    position, total = 0, sum(weights.values())
    numeric: dict[int, str] = {}
    for row in ordered:
        q = (position + weights[row] / 2) / total
        value = numbers[min(len(numbers) - 1, int(q * len(numbers)))]
        numeric[row] = str(value)
        position += weights[row]
    bounds = nearest_mass_rows(weights, min(1.0, out_of_bounds), seed=_seed(seed, "bounds"))
    result.update({row: token + ("*" if row in bounds else "") for row, token in numeric.items()})
    return result


def _out_of_bounds_evidence(
    records: Sequence[WeightedObservation],
) -> tuple[float, dict[str, Any]]:
    """Model positive OOB incidence within the supplied ordinary numeric support.

    Unknown source facts remain unknown. They contribute exposure to this explicit
    lower-bound model, rather than disappearing from the denominator and turning
    sparse positive mentions into certainty.
    """
    weights = {
        "positive": math.fsum(r.weight for r in records if r.event.out_of_bounds is True),
        "explicit_false": math.fsum(r.weight for r in records if r.event.out_of_bounds is False),
        "unknown": math.fsum(r.weight for r in records if r.event.out_of_bounds is None),
    }
    total = sum(weights.values())
    known = weights["positive"] + weights["explicit_false"]
    requested = weights["positive"] / total if total else 0.0
    return requested, {
        "policy": "positive-only narrative incidence / all matching ordinary numeric weight; "
        "lower-bound model, unknown is not observed in bounds",
        "state": "dormant"
        if not total
        else "unidentified"
        if not known
        else "partial-positive-evidence"
        if weights["unknown"]
        else "complete-explicit-evidence",
        "ordinary_numeric_observations": len(records),
        "ordinary_numeric_weight": total,
        "positive_observations": sum(r.event.out_of_bounds is True for r in records),
        "explicit_false_observations": sum(r.event.out_of_bounds is False for r in records),
        "unknown_observations": sum(r.event.out_of_bounds is None for r in records),
        **{name + "_weight": weight for name, weight in weights.items()},
        "explicit_evidence_coverage": known / total if total else None,
        "requested_numeric_probability": requested,
    }


def _out_of_bounds_encoding(tokens: Mapping[int, str], evidence: dict[str, Any]) -> None:
    """Add exact physical-dice achievement without changing encoded outcomes."""
    weights = offensive_weights()
    numeric = {row: token for row, token in tokens.items() if re.fullmatch(r"[+-]?\d+\*?", token)}
    mass = sum(weights[row] for row in numeric)
    marked = sum(weights[row] for row, token in numeric.items() if token.endswith("*"))
    achieved = marked / mass if mass else None
    evidence.update(
        {
            "physical_combinations": 216,
            "encoded_numeric_mass": mass,
            "encoded_oob_mass": marked,
            "achieved_numeric_probability": achieved,
            "achieved_unconditional_probability": marked / 216,
            "numeric_quantization_error": achieved - evidence["requested_numeric_probability"]
            if achieved is not None
            else None,
        }
    )
    if mass and not evidence["ordinary_numeric_weight"]:
        evidence["state"] = "unsupported-numeric-proxy"


def _location_token(kind: str, yards: int) -> str:
    if kind in {"INT", "BK"}:
        return f"{kind} {yards}"
    return kind if yards == 0 else f"{kind} {'-' if yards < 0 else '+'} {abs(yards)}"


def _quantiles(values: Sequence[tuple[int, float]]) -> list[int]:
    """216 deterministic integration points, not additional independent samples."""
    if not values:
        raise ValueError("numeric distribution has no known evidence")
    counts: Counter[int] = Counter()
    for value, weight in values:
        counts[value] += weight
    ordered = sorted(counts)
    total = sum(counts.values())
    result, index, cumulative = [], 0, counts[ordered[0]]
    for point in range(216):
        target = (point + 0.5) * total / 216
        while cumulative < target and index < len(ordered) - 1:
            index += 1
            cumulative += counts[ordered[index]]
        result.append(ordered[index])
    return result


def _histogram(values: Sequence[tuple[int, float]]) -> dict[int, float]:
    masses: Counter[int] = Counter()
    for yards, weight in values:
        masses[yards] += weight
    return dict(masses)


def _column_evidence(
    section: str,
    column: str,
    values: Sequence[tuple[int, float]],
    specials: Sequence[tuple[str, float]],
    *,
    scope: str,
    locations: Mapping[str, Sequence[tuple[int, float]]] | None = None,
) -> ColumnEvidence:
    kinds = {
        "F": ResultKind.FUMBLE,
        "INT": ResultKind.INTERCEPTION,
        "BK": ResultKind.BLOCKED_KICK,
        "B": ResultKind.BREAKAWAY,
        "QT": ResultKind.QUARTERBACK_TRAPPED,
        "QR": ResultKind.QUARTERBACK_RUN,
        "SOP": ResultKind.SPRINT_OUT_PASS,
        "BLP": ResultKind.BOOTLEG_PASS,
        "BLACK": ResultKind.INCOMPLETE,
        "OFF": ResultKind.PENALTY,
        "DEF": ResultKind.PENALTY,
    }
    rates: Counter[str] = Counter()
    for token, probability in specials:
        rates[kinds[token.split()[0]].value] += probability
    return ColumnEvidence(
        section,
        column,
        None,
        _histogram(values),
        scope,
        locations={kind: _histogram(records) for kind, records in (locations or {}).items()},
        kind_probabilities=dict(rates),
    )


def _fumble_locations(
    records: Sequence[WeightedObservation], correction: float, scale: float, *, kind: str
) -> list[tuple[int, float]]:
    return [
        (round((r.event.yards - correction) * scale), r.weight)
        for r in records
        if r.event.kind == kind and _primary_fumble(r.event) and r.event.yards is not None
    ]


def _int_locations(own: Sequence[Event], live: Sequence[Event]) -> tuple[list[int], dict[str, Any]]:
    def known(sample: Sequence[Event]) -> list[int]:
        return [
            e.interception_yards if e.interception_yards is not None else e.air_yards
            for e in sample
            if e.kind == "interception"
            and (e.interception_yards is not None or e.air_yards is not None)
        ]

    local = known(own)
    values = local or known(live)
    if not values and any(e.kind == "interception" for e in live):
        raise ValueError("no known interception location evidence; preserve unknown source spots")
    return values, {
        "method": "team-PBP" if local else "league-PBP" if values else "unobserved",
        "known_team_samples": len(local),
        "modeled_samples": len(values),
        "unknown_team_samples": sum(e.kind == "interception" for e in own) - len(local),
        "policy": "observed or corroborated INT spots only; no completion/zero proxy",
    }


def _blocked_locations(
    own: Sequence[Event], live: Sequence[Event]
) -> tuple[list[int], dict[str, Any]]:
    """Pool only known initial blocked-punt movement, independently of block rate."""
    blocks = [e for e in own if e.kind == "punt" and e.blocked]
    local = [e.blocked_kick_yards for e in blocks if e.blocked_kick_yards is not None]
    values = local or (
        [
            e.blocked_kick_yards
            for e in live
            if e.kind == "punt" and e.blocked and e.blocked_kick_yards is not None
        ]
        if blocks
        else []
    )
    return values, {
        "known_blocked_locations": len(local),
        "unknown_blocked_locations": len(blocks) - len(local),
        "blocked_location_method": "team-PBP"
        if local
        else "league-PBP"
        if values
        else "unobserved",
        "modeled_blocked_location_samples": len(values),
        "blocked_location_policy": "explicit physical initial movement only; "
        "no statistical-credit or return-advance proxy",
    }


def _return_fumble_probability(sample: Sequence[Event], scale: float) -> float:
    """Refuse positive-only annotations when other return observations are unknown."""
    known = [event for event in sample if event.fumble is not None]
    fumbles = [event for event in known if event.fumble and event.fumble_team == event.opponent]
    if fumbles and len(known) < len(sample) and all(event.fumble is True for event in known):
        raise ValueError("positive-only return fumble support; supply a qualified denominator")
    return min(1.0, (len(fumbles) / len(known) if known else 0) * scale)


def _primary_fumble(event: Event) -> bool:
    # A missing fumbler on a primary rush/completion can be inferred from that
    # primary event. Return events require an explicit independent owner.
    return (
        event.fumble is True
        and event.kind in {"rush", "complete", "sack"}
        and event.fumble_team in {None, event.team}
    )


def _positive_fumble_records(
    records: Sequence[WeightedObservation],
) -> list[WeightedObservation]:
    """Zero-weight facts are not observations; invalid probability weights reject."""
    for record in records:
        if (
            type(record.weight) not in {int, float}
            or not math.isfinite(record.weight)
            or record.weight < 0
        ):
            raise ValueError("fumble support weight must be finite nonnegative numeric evidence")
    return [record for record in records if record.weight > 0]


def _fumble_support(
    records: Sequence[WeightedObservation], *, kind: str, team: str
) -> dict[str, Any]:
    """Describe annotation support before pooling can obscure a team's unknowns.

    Effective weights are model support, never independent source samples.
    Completeness of provider annotations is a separate source qualification.
    """
    from .primary_fumbles import primary_source_fumble

    mechanism = [r for r in _positive_fumble_records(records) if r.event.kind == kind]
    own = [r for r in mechanism if r.event.team == team]

    def state(rows: Sequence[WeightedObservation]) -> str:
        if not rows:
            return "dormant_empty"
        known = [r for r in rows if primary_source_fumble(r.event) is not None]
        if not known:
            return "unsupported_all_unknown"
        if len(known) != len(rows):
            return "partial_known"
        return (
            "observed_positive" if any(_primary_fumble(r.event) for r in known) else "observed_zero"
        )

    known = [r for r in mechanism if primary_source_fumble(r.event) is not None]
    unknown = [r for r in mechanism if primary_source_fumble(r.event) is None]
    fumbles = [r for r in known if primary_source_fumble(r.event) is True]
    return {
        "kind": kind,
        "state": state(mechanism),
        "own_state": state(own),
        "raw_eligible_records": sum(r.event.kind == kind for r in records),
        "positive_weight_records": len(mechanism),
        "zero_weight_records": sum(r.event.kind == kind and r.weight == 0 for r in records),
        "known_primary_presence": len(known),
        "unknown_primary_presence": len(unknown),
        "own_unknown_primary_presence": sum(r.event.team == team for r in unknown),
        "pooled_known_primary_presence": sum(r.event.team != team for r in known),
        "known_primary_fumbles": len(fumbles),
        "known_location_records": sum(r.event.yards is not None for r in fumbles),
        "unknown_location_records": sum(r.event.yards is None for r in fumbles),
        "mechanism_weight_exact": str(sum((Fraction(r.weight) for r in mechanism), Fraction())),
        "known_weight_exact": str(sum((Fraction(r.weight) for r in known), Fraction())),
        "unknown_weight_exact": str(sum((Fraction(r.weight) for r in unknown), Fraction())),
        "method": "pooled-known-annotation-conditional"
        if any(r.event.team != team for r in known)
        else "own-known-annotation-conditional",
        "source_accuracy_qualified": False,
        "limits": "annotation support is not provider completeness or independent sample exposure",
    }


def _fumble_distribution(
    records: Sequence[WeightedObservation],
    correction: float,
    scale: float,
    *,
    kind: str,
) -> tuple[float, list[int]]:
    from .primary_fumbles import primary_source_fumble

    positive = _positive_fumble_records(records)
    mechanism = [record for record in positive if record.event.kind == kind]
    if not mechanism:
        return 0.0, []  # Explicitly dormant, not an observed no-fumble rate.
    known = [record for record in mechanism if primary_source_fumble(record.event) is not None]
    if not known:
        raise ValueError(f"all positive {kind} primary fumble support is unknown")
    fumbles = [record for record in known if primary_source_fumble(record.event) is True]

    def weight(rows: Sequence[WeightedObservation]) -> Fraction:
        return sum((Fraction(r.weight) for r in rows), Fraction())

    probability = float(weight(fumbles) / weight(known) * weight(mechanism) / weight(positive))
    located = _fumble_locations(positive, correction, scale, kind=kind)
    if fumbles and not located:
        raise ValueError("no known primary fumble location evidence")
    return probability, _quantiles(located) if located else []


def _recovery_probability(
    own: Sequence[Event], live: Sequence[Event], *, team: str | None = None
) -> tuple[float, dict[str, Any]]:
    def known(
        sample: Sequence[Event],
        holder_filter: str | None = None,
        excluded_holder: str | None = None,
    ) -> tuple[list[bool], int]:
        outcomes = []
        unknown = 0
        for event in sample:
            if not event.fumble or event.no_play or event.event_phase == "try":
                continue
            owner = event.fumble_team
            if owner is None and event.kind in {"rush", "complete", "sack"}:
                owner = event.team
            if owner is None:
                unknown += event.fumble_count or 1
                continue
            if event.recovery_policy != "legacy":
                # Net possession (including a following try/free kick) is not
                # evidence of a physical recovery. Walk only known holders.
                recoverers = [event.recovery_team, event.recovery_team_2]
                for index in range(event.fumble_count or 1):
                    recoverer = recoverers[index] if index < len(recoverers) else None
                    if (
                        holder_filter is None or owner == holder_filter
                    ) and owner != excluded_holder:
                        if owner is None or recoverer is None:
                            unknown += 1
                        else:
                            outcomes.append(recoverer == owner)
                    owner = recoverer
                continue
            if (holder_filter is not None and owner != holder_filter) or owner == excluded_holder:
                continue
            if event.recovery_team is not None:
                recovered = event.recovery_team == owner
                if (
                    owner == event.team
                    and event.fumble_lost is not None
                    and recovered == event.fumble_lost
                ):
                    raise ValueError("fumble recovery identity conflicts with known loss flag")
                outcomes.append(recovered)
            elif owner == event.team and event.fumble_lost is not None:
                outcomes.append(not event.fumble_lost)
        return outcomes, unknown

    local, unknown = known(own, team)
    league, league_unknown = known(live)
    weighted = [(value, 1.0) for value in local]
    other_samples, other_weight = 0, 0.0
    if team is not None and len(local) < MINIMUM_RECOVERY_SAMPLES:
        others, _ = known(live, excluded_holder=team)
        if others:
            other_weight = min(1.0, (MINIMUM_RECOVERY_SAMPLES - len(local)) / len(others))
            weighted.extend((value, other_weight) for value in others)
            other_samples = len(others)
    elif not local:
        weighted = [(value, 1.0) for value in league]
        other_samples, other_weight = len(league), 1.0
    if not weighted:
        raise ValueError("no known fumble recovery evidence; no neutral recovery prior is supplied")
    total_weight = sum(weight for _, weight in weighted)
    return sum(value * weight for value, weight in weighted) / total_weight, {
        "method": "sparse-team-plus-league-PBP"
        if local and other_samples
        else "team-PBP"
        if local
        else "league-PBP",
        "known_team_samples": len(local),
        "modeled_samples": len(weighted),
        "other_team_samples": other_samples,
        "other_observation_weight": other_weight,
        "effective_sample_size": total_weight**2 / sum(weight**2 for _, weight in weighted),
        "minimum_team_samples": MINIMUM_RECOVERY_SAMPLES,
        "unknown_recovery_steps": unknown,
        "unknown_league_recovery_steps": league_unknown,
        "policy": (
            "physical recovery chain; try rows excluded; "
            "inferred aliases/net possession are not observations"
        ),
    }


def _pass_rate(
    records: Sequence[WeightedObservation],
    kind: str,
    rate_effects: Mapping[str, Mapping[str, float]],
    profile: CalibrationProfile,
) -> float:
    total = sum(r.weight for r in records)
    observed = sum(r.weight for r in records if r.event.kind == kind) / max(1e-12, total)
    residual = sum(r.weight * rate_effects[kind].get(r.event.opponent, 0) for r in records) / max(
        1e-12, total
    )
    value = observed - residual
    if kind == "complete":
        return min(1, max(0, value + profile.completion_shift))
    scale = profile.interception_scale if kind == "interception" else profile.sack_scale
    return min(1, max(0, value) * scale)


def _source(events: Sequence[Event]) -> tuple[str, str]:
    encoded = json.dumps([e.to_dict() for e in events], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest(), "generated-model-v3.json"


def _checked_audit(chart: TeamChart) -> tuple[dict[str, Any], dict[str, Any]]:
    from .audit import audit_chart

    report = audit_chart(chart)
    if not report["structural_ready"]:
        raise ValueError(
            "generated chart failed independent semantic audit; inspect source mechanisms"
        )
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    return report, {
        "schema_version": report["schema_version"],
        "semantic_sha256": hashlib.sha256(encoded).hexdigest(),
        "structural_ready": True,
        "scope": report["scope"],
    }


def _cell(token: str, source_hash: str, filename: str, row: int, column: int) -> Any:
    color = chart_color_for_csv_token(token)
    # These are GENERATED coordinates in a virtual evidence table, never claimed
    # PDF observations. The sidecar manifest documents the model and source hashes.
    provenance = Provenance(
        source_hash,
        filename,
        1,
        BoundingBox(column, row, column + 1, row + 1),
        token,
        CELL_LEGEND[color].rgb_color,
    )
    return parse_cell(token, provenance)


def _known(events: Sequence[Event], kind: str) -> list[int]:
    return [
        event.yards
        for event in events
        if event.kind == kind and event.yards is not None and not (kind == "punt" and event.blocked)
    ]


def _penalty_token(event: Event) -> str | None:
    """Encode supported observed side/distance without substituting a foul side.

    Narrative foul names remain in source evidence. A fixed nominal enforcement
    does not claim an unidentified PI location or automatic-first-down response.
    """
    side = (event.penalty_side or "").strip().casefold()
    team = {"offense": "OFF", "off": "OFF", "pos": "OFF", "defense": "DEF", "def": "DEF"}.get(side)
    if team is None or event.penalty_yards is None or event.penalty_yards == 0:
        return None
    return f"{team} {abs(event.penalty_yards)}"


def _same_distribution(first: Sequence[int], second: Sequence[int]) -> bool:
    """Require identical empirical conditional tails before sharing a B column."""
    left, right = Counter(first), Counter(second)
    return all(
        left[value] * len(second) == right[value] * len(first)
        for value in left.keys() | right.keys()
    )


def _selected_numeric_support(
    records: Sequence[WeightedObservation],
    selected_values: Sequence[int],
    *,
    value: Callable[[Event], int],
) -> list[WeightedObservation]:
    """Retain whole tied observations proportionally to selected numeric mass.

    The caller's unchanged numeric selection defines the mass, never the number
    of returned objects. Fractional support is not new independent evidence.
    Source/family/proxy eligibility must already be established by the caller.
    """
    grouped: dict[int, list[float]] = defaultdict(list)
    for record in records:
        if not math.isfinite(record.weight) or record.weight <= 0:
            raise ValueError("numeric support requires positive finite source weights")
        grouped[value(record.event)].append(record.weight)
    counts = Counter(selected_values)
    totals = {gain: math.fsum(weights) for gain, weights in grouped.items()}
    if any(gain not in totals for gain in counts):
        raise ValueError("selected numeric value has no source support")
    return [
        WeightedObservation(record.event, record.weight * counts[gain] / totals[gain])
        for record in records
        if (gain := value(record.event)) in counts
    ]


def _pool(
    own: Sequence[Event],
    league: Sequence[Event],
    kind: str,
    diagnostics: dict[str, Any],
    *,
    observations: list[WeightedObservation] | None = None,
) -> list[int]:
    values = _known(own, kind)
    if observations is not None:
        observations.extend(
            WeightedObservation(event, 1.0)
            for event in own
            if event.kind == kind and event.yards is not None
        )
    if len(values) < MINIMUM_FAMILY_SAMPLES:
        fallback = _known(league, kind)
        diagnostics[kind] = {
            "samples": len(values),
            "fallback": "league-empirical",
            "fallback_samples": len(fallback),
            "attached_evidence_selection": "proportional within numeric-value ties; "
            "fractional weight is not an independent observation",
        }
        # Partial pooling gives the observed team increasing influence. No values
        # are invented if the entire supplied source lacks this category.
        # Cover the whole empirical distribution rather than early source rows.
        # These are pooled observations, not additional independent samples.
        ordered = sorted(fallback)
        needed = min(len(ordered), max(0, MINIMUM_FAMILY_SAMPLES - len(values)))
        selected = [ordered[int((index + 0.5) * len(ordered) / needed)] for index in range(needed)]
        values += selected
        if observations is not None:
            observations.extend(
                _selected_numeric_support(
                    [
                        WeightedObservation(event, 1.0)
                        for event in league
                        if event.kind == kind and event.yards is not None
                    ],
                    selected,
                    value=lambda event: event.yards,
                )
            )
    else:
        diagnostics[kind] = {"samples": len(values), "fallback": None}
    if not values:
        raise ValueError(
            f"no known {kind} yardage evidence; supply individual-play source evidence"
        )
    return values


@lru_cache(maxsize=4)
def _opponent_effects(events: tuple[Event, ...], kind: str) -> dict[str, float]:
    """Regularized additive team/opponent model, retaining FCS opponents by identity.

    Equal event likelihood and a 100-play zero-centered ridge prior prevent tiny
    opponent samples from dominating. No conference/ranking data is fabricated.
    """
    usable = [e for e in events if e.kind == kind and e.yards is not None and not e.no_play]
    if not usable:
        return {}
    center = mean(e.yards for e in usable)
    offense = dict.fromkeys({e.team for e in usable}, 0.0)
    defense = dict.fromkeys({e.opponent for e in usable}, 0.0)
    by_offense: dict[str, list[Event]] = defaultdict(list)
    by_defense: dict[str, list[Event]] = defaultdict(list)
    for event in usable:
        by_offense[event.team].append(event)
        by_defense[event.opponent].append(event)
    for _ in range(12):
        for team, sample in by_offense.items():
            offense[team] = sum(e.yards - center - defense[e.opponent] for e in sample) / (
                len(sample) + 100
            )
        for team, sample in by_defense.items():
            defense[team] = sum(e.yards - center - offense[e.team] for e in sample) / (
                len(sample) + 100
            )
    return defense


@lru_cache(maxsize=4)
def _rate_effects(events: tuple[Event, ...], kind: str) -> dict[str, float]:
    """Regularized opponent residuals for dropback outcomes, separate from yards."""
    sample = [
        e
        for e in events
        if not e.no_play and e.kind in {"complete", "incomplete", "interception", "sack"}
    ]
    if not sample:
        return {}
    center = mean(e.kind == kind for e in sample)
    offense: dict[str, float] = dict.fromkeys({e.team for e in sample}, 0.0)
    defense: dict[str, float] = dict.fromkeys({e.opponent for e in sample}, 0.0)
    by_offense: dict[str, list[Event]] = defaultdict(list)
    by_defense: dict[str, list[Event]] = defaultdict(list)
    for event in sample:
        by_offense[event.team].append(event)
        by_defense[event.opponent].append(event)
    for _ in range(12):
        for team, observations in by_offense.items():
            offense[team] = sum(
                (e.kind == kind) - center - defense[e.opponent] for e in observations
            ) / (len(observations) + 100)
        for team, observations in by_defense.items():
            defense[team] = sum(
                (e.kind == kind) - center - offense[e.team] for e in observations
            ) / (len(observations) + 100)
    return defense


@dataclass(frozen=True)
class EvidenceModel:
    """One immutable source snapshot with reusable provenance and opponent fits."""

    events: tuple[Event, ...]
    live: tuple[Event, ...]
    by_team: Mapping[str, tuple[Event, ...]]
    empirical_by_team: Mapping[str, EmpiricalData]
    unidentified: tuple[Event, ...]
    seasons: frozenset[int]
    source_hash: str
    source_filename: str
    run_effects: Mapping[str, float]
    pass_effects: Mapping[str, float]
    rate_effects: Mapping[str, Mapping[str, float]]

    @classmethod
    def from_events(cls, events: Sequence[Event]) -> EvidenceModel:
        snapshot = tuple(events)
        live = tuple(
            e for e in snapshot if not e.no_play and (e.event_phase != "try" or e.kind == "pat")
        )
        grouped: dict[str, list[Event]] = defaultdict(list)
        all_grouped: dict[str, list[Event]] = defaultdict(list)
        for event in snapshot:
            all_grouped[event.team].append(event)
            if not event.no_play and (event.event_phase != "try" or event.kind == "pat"):
                grouped[event.team].append(event)
        source_hash, filename = _source(snapshot)
        return cls(
            snapshot,
            live,
            {t: tuple(rows) for t, rows in grouped.items()},
            {t: empirical_vectors(rows, t) for t, rows in all_grouped.items()},
            tuple(e for e in live if e.called_family is None),
            frozenset(e.season for e in snapshot),
            source_hash,
            filename,
            _opponent_effects(live, "rush"),
            _opponent_effects(live, "complete"),
            {kind: _rate_effects(live, kind) for kind in ("complete", "interception", "sack")},
        )


def generate_team(
    events: Sequence[Event],
    team: str,
    name: str,
    season: int,
    *,
    seed: int = 1,
    profile: CalibrationProfile | None = None,
    defensive_profile: DefensiveProfile | None = None,
    tactics: TacticalProfile | None = None,
    model: EvidenceModel | None = None,
) -> tuple[TeamChart, TeamFileMetadata, dict[str, Any]]:
    """Build a complete local-only bundle from normalized evidence, without I/O."""
    profile = profile or CalibrationProfile()
    defensive_profile = defensive_profile or DefensiveProfile()
    from .tactics import APPROVED_YARDAGE_POLICY_SHA256, TacticalProfile

    tactics = tactics or TacticalProfile.neutral()
    if tactics.origin == "reference-derived":
        raise ValueError("reference charts are independent validation inputs, not baseline tactics")
    if tactics.origin == "authored-bb-v1":
        raise ValueError("rejected probability-changing tactical proposal cannot enter generation")
    if (
        tactics.origin == "authored-bb-yardage-v1"
        and tactics.sha256 != APPROVED_YARDAGE_POLICY_SHA256
    ):
        raise ValueError("generation requires the approved tactical policy hash")
    if model is not None and model.events is not events and model.events != tuple(events):
        raise ValueError("cached model differs from supplied evidence")
    model = model or EvidenceModel.from_events(events)
    if model.seasons != {season}:
        raise ValueError("source season differs from requested chart season")
    live = model.live
    own = model.by_team.get(team, ())
    if not own:
        raise ValueError("requested team has no source events")
    source_hash, filename = model.source_hash, model.source_filename
    diagnostics: dict[str, Any] = {}
    rush_pool_records: list[WeightedObservation] = []
    rush = _pool(own, live, "rush", diagnostics, observations=rush_pool_records)
    run_effects = model.run_effects
    pass_effects = model.pass_effects
    run_correction = mean(run_effects.get(e.opponent, 0.0) for e in own)
    pass_correction = mean(pass_effects.get(e.opponent, 0.0) for e in own)
    rush = [round((yards - run_correction) * profile.run_yards_scale) for yards in rush]
    dropbacks = [e for e in own if e.kind in {"complete", "incomplete", "interception", "sack"}]
    if not dropbacks:
        raise ValueError("no pass outcome evidence")
    rate_effects = model.rate_effects
    interception_locations, interception_evidence = _int_locations(own, live)
    defensive_interception_locations, defensive_interception_evidence = _int_locations(
        tuple(e for e in live if e.opponent == team), live
    )
    snaps = [e for e in own if e.kind in {"rush", "complete", "incomplete", "interception", "sack"}]
    known_fumbles = [e for e in snaps if e.fumble is not None]
    penalties = [e for e in events if e.team == team and e.penalty and not e.penalty_declined]
    penalty_counts = Counter(token for event in penalties if (token := _penalty_token(event)))
    penalty_denominator = len(snaps) + sum(event.no_play for event in penalties)
    penalty_rates = [
        (token, count / max(1, penalty_denominator))
        for token, count in sorted(penalty_counts.items())
    ]
    penalty_rate = sum(probability for _, probability in penalty_rates)
    option_calls = [e for e in own if e.called_family == 5]
    option_rates = {
        branch: sum(e.resolved_family == resolved for e in option_calls) / max(1, len(option_calls))
        for branch, resolved in (("SOP", 7), ("BLP", 8))
    }
    scrambles = [e for e in own if e.kind == "rush" and e.quarterback_scramble is True]
    scramble_rate = len(scrambles) / max(1, len(dropbacks) + len(scrambles))
    offense = []
    family_diagnostics = {}
    source_columns = []
    # Only distribution-compatible empirical tails may share the B response.
    # Fumbles are kept on their originating family, outside this shared pool.
    ordinary_run = [
        round((e.yards - run_correction) * profile.run_yards_scale)
        for e in own
        if e.kind == "rush" and e.yards is not None and not _primary_fumble(e)
    ] or rush
    tail = sorted(ordinary_run)[max(0, int(len(ordinary_run) * 0.9)) :]
    ordinary_run_records = [
        WeightedObservation(e, 1.0)
        for e in own
        if e.kind == "rush" and e.yards is not None and not _primary_fumble(e)
    ]
    # The existing numeric tail determines mass. Do not use the expanded number
    # of fractional fallback observations as a new numeric rank/sample count.
    tail_records = _selected_numeric_support(
        ordinary_run_records or rush_pool_records,
        tail,
        value=lambda event: round((event.yards - run_correction) * profile.run_yards_scale),
    )
    for play in Play:
        pool = family_pool(model.empirical_by_team[team], play, model.unidentified, team=team)
        records = pool.observations
        is_run = play.value <= 5
        correction = run_correction if is_run else pass_correction
        scale = profile.run_yards_scale if is_run else profile.pass_yards_scale
        numeric_records = [
            r
            for r in records
            if r.event.kind == ("rush" if is_run else "complete")
            and r.event.yards is not None
            and not _primary_fumble(r.event)
        ]
        numeric = [(round((r.event.yards - correction) * scale), r.weight) for r in numeric_records]
        # An all-fumble conditional outcome is legal without ordinary evidence.
        # A profile that then needs an ordinary cell must fail, not relabel F.
        if not numeric and not _fumble_locations(
            records, correction, scale, kind="rush" if is_run else "complete"
        ):
            raise ValueError(
                f"no known play {play.value} {('rush' if is_run else 'completion')} evidence"
            )
        values = _quantiles(numeric) if numeric else []
        total_weight = pool.effective_weight
        fumble_rate, fumble_locations = _fumble_distribution(
            records, correction, scale, kind="rush" if is_run else "complete"
        )
        fumble_rate = min(1, fumble_rate * profile.fumble_scale)
        family_diagnostics[str(play.value)] = {
            "observed": pool.own_family_samples,
            "classification_counts": dict(Counter(r.event.family_confidence for r in records)),
            "method": pool.method,
            "raw_observations": len(records),
            "league_samples": pool.league_samples,
            "effective_weight": total_weight,
            "effective_sample_size": pool.effective_sample_size,
            "unknown_fumble_observations": sum(r.event.fumble is None for r in records),
            "fumble_support": _fumble_support(
                records, kind="rush" if is_run else "complete", team=team
            ),
            "inferred_primary_fumbler_observations": sum(
                _primary_fumble(r.event) and r.event.fumble_team is None for r in records
            ),
            "gain_policy": (
                "weighted individual PBP quantiles; 216 integration points are not samples"
            ),
        }
        specials = [("F", fumble_rate * (1 - penalty_rate)), *penalty_rates]
        split = max(1, int(len(values) * 0.9))
        family_tail = sorted(values)[split:]
        compatible = bool(family_tail) and _same_distribution(family_tail, tail)
        break_probability = len(family_tail) / len(values) if compatible else 0
        if compatible:
            values = sorted(values)[:split]
        if is_run:
            branch_rates = {}
            if play is Play.FIVE:
                branch_rates = {
                    branch: sum(r.weight for r in records if r.event.resolved_family == resolved)
                    / max(1e-12, total_weight)
                    for branch, resolved in (("SOP", 7), ("BLP", 8))
                }
            fumble_rate = min(fumble_rate, max(0, 1 - sum(branch_rates.values())))
            specials[0] = ("F", fumble_rate * (1 - penalty_rate))
            numeric_rate = max(0, 1 - fumble_rate - sum(branch_rates.values()))
            specials += [("B", (1 - penalty_rate) * numeric_rate * break_probability)]
            specials += [
                (branch, (1 - penalty_rate) * rate) for branch, rate in branch_rates.items()
            ]
        else:
            int_rate = _pass_rate(records, "interception", rate_effects, profile)
            sack_rate = _pass_rate(records, "sack", rate_effects, profile)
            complete_rate = max(
                0, _pass_rate(records, "complete", rate_effects, profile) - fumble_rate
            )
            # Bounded phase-two shifts cannot create total categorical mass > 1.
            family_scramble_rate = sum(
                r.weight
                for r in records
                if r.event.kind == "rush" and r.event.quarterback_scramble is True
            ) / max(1e-12, total_weight)
            family_diagnostics[str(play.value)]["source_QR_probability"] = family_scramble_rate
            categorical = int_rate + sack_rate + family_scramble_rate + fumble_rate
            factor = min(1.0, 1 / categorical) if categorical else 1.0
            family_diagnostics[str(play.value)]["bounded_category_scale"] = factor
            int_rate, sack_rate, qr_rate = (
                int_rate * factor,
                sack_rate * factor,
                family_scramble_rate * factor,
            )
            specials[0] = ("F", fumble_rate * factor * (1 - penalty_rate))
            complete_rate = min(complete_rate, max(0, 1 - categorical * factor))
            specials += [
                ("B", (1 - penalty_rate) * complete_rate * break_probability),
                ("INT", (1 - penalty_rate) * int_rate),
                ("QT", (1 - penalty_rate) * sack_rate),
                ("QR", (1 - penalty_rate) * qr_rate),
                ("BLACK", (1 - penalty_rate) * max(0, 1 - complete_rate - categorical * factor)),
            ]
        family_oob, bounds_evidence = _out_of_bounds_evidence(numeric_records)
        bounds_evidence["support"] = "rush" if is_run else "complete"
        source_columns.append(
            _column_evidence(
                "offense",
                str(play.value),
                numeric,
                specials,
                scope="PBP-only weighted conditional gains before integration; "
                "modeled opponent/profile adjustment; pooled family status recorded separately",
                locations={
                    "fumble": _fumble_locations(
                        records, correction, scale, kind="rush" if is_run else "complete"
                    ),
                    "interception": [(yards, 1.0) for yards in interception_locations]
                    if not is_run
                    else [],
                },
            )
        )
        column = _column(
            values,
            specials,
            seed=_seed(seed, f"offense/{play}"),
            out_of_bounds=family_oob,
            locations={"F": fumble_locations, "INT": interception_locations},
        )
        _out_of_bounds_encoding(column, bounds_evidence)
        family_diagnostics[str(play.value)]["out_of_bounds_evidence"] = bounds_evidence
        offense.extend(
            OffensiveCell(
                play,
                row,
                _cell(
                    "" if token == "0" else "*" if token == "0*" else token,
                    source_hash,
                    filename,
                    row,
                    play.value,
                ),
            )
            for row, token in column.items()
        )
    supplemental = []
    supplemental_evidence = {}
    for index, column in enumerate(SupplementalColumn):
        values = (
            tail
            if column is SupplementalColumn.BREAKAWAY
            else []
            if column is SupplementalColumn.QUARTERBACK_TRAPPED
            else rush
        )
        conditional_records = []
        source_values = [(yards, 1.0) for yards in values]
        if column is SupplementalColumn.QUARTERBACK_TRAPPED:
            conditional_records = [WeightedObservation(e, 1.0) for e in own if e.kind == "sack"]
            if not any(e.event.yards is not None for e in conditional_records):
                conditional_records = [
                    WeightedObservation(e, 1.0) for e in live if e.kind == "sack"
                ]
        elif column is SupplementalColumn.QUARTERBACK_RUN:
            conditional_records = [
                WeightedObservation(e, 1.0)
                for e in own
                if e.kind == "rush" and e.quarterback_scramble is True
            ]
            if not conditional_records:
                conditional_records = [
                    WeightedObservation(e, 1.0)
                    for e in live
                    if e.kind == "rush" and e.quarterback_scramble is True
                ]
            if conditional_records:
                located = [
                    (e.event.yards, e.weight)
                    for e in conditional_records
                    if e.event.yards is not None
                ]
                if not located:
                    raise ValueError("no known quarterback scramble yardage evidence")
        if conditional_records:
            # Keep the same whole observations as the F probability/location
            # model; a fumble gain is not an ordinary conditional observation.
            source_values = [
                (record.event.yards, record.weight)
                for record in conditional_records
                if record.event.yards is not None and not _primary_fumble(record.event)
            ]
            values = _quantiles(source_values) if source_values else []
        fumble_rate, locations = _fumble_distribution(
            conditional_records,
            0.0,
            1.0,
            kind="sack" if column is SupplementalColumn.QUARTERBACK_TRAPPED else "rush",
        )
        if conditional_records:
            conditional_method = (
                "team-PBP"
                if all(r.event.team == team for r in conditional_records)
                else "league-PBP"
            )
        else:
            conditional_method = (
                "compatible-run-tail"
                if column is SupplementalColumn.BREAKAWAY
                else "dormant-rush-proxy"
            )
        supplemental_evidence[column.value] = {
            "method": conditional_method,
            "conditional_observations": len(conditional_records),
            "ordinary_numeric_evidence_weight": sum(weight for _, weight in source_values),
            "unknown_conditional_yards": sum(r.event.yards is None for r in conditional_records),
            "fumble_support": _fumble_support(
                conditional_records,
                kind="sack" if column is SupplementalColumn.QUARTERBACK_TRAPPED else "rush",
                team=team,
            ),
            "policy": (
                "ordinary and F locations use the same whole source records; "
                "known F gains are excluded from ordinary conditional gains"
            ),
        }
        bounds_records = (
            conditional_records
            if conditional_records
            else tail_records
            if column is SupplementalColumn.BREAKAWAY
            else rush_pool_records
            if column is SupplementalColumn.QUARTERBACK_RUN
            else []
        )
        bounds_records = [
            r for r in bounds_records if r.event.yards is not None and not _primary_fumble(r.event)
        ]
        conditional_oob, bounds_evidence = _out_of_bounds_evidence(bounds_records)
        bounds_evidence["support"] = conditional_method
        if column is SupplementalColumn.BREAKAWAY:
            bounds_evidence["support_membership_policy"] = (
                "tie-proportional support of unchanged selected numeric tail; "
                "not observed tail membership or independent samples"
            )
        source_columns.append(
            _column_evidence(
                "supplemental",
                column.value,
                source_values,
                [("F", min(1, fumble_rate * profile.fumble_scale))],
                scope="PBP-only supplemental encoder inputs; B is a compatible tail; "
                "QT uses sack evidence; dormant QR may use the documented rush proxy",
                locations={
                    "fumble": _fumble_locations(
                        conditional_records,
                        0.0,
                        1.0,
                        kind="sack" if column is SupplementalColumn.QUARTERBACK_TRAPPED else "rush",
                    )
                },
            )
        )
        tokens = _column(
            values,
            [("F", min(1, fumble_rate * profile.fumble_scale))],
            seed=_seed(seed, column.value),
            out_of_bounds=conditional_oob,
            locations={"F": locations},
        )
        _out_of_bounds_encoding(tokens, bounds_evidence)
        supplemental_evidence[column.value]["out_of_bounds_evidence"] = bounds_evidence
        supplemental.extend(
            SupplementalCell(column, row, _cell(token, source_hash, filename, row, 10 + index))
            for row, token in tokens.items()
        )
    defense = []
    defensive_quantization: dict[str, Any] = {}
    neutral_response_values = {
        kind: sorted(
            e.yards
            for e in live
            if e.kind == kind and e.yards is not None and not _primary_fumble(e)
        )
        for kind in ("rush", "complete")
    }
    league_dropbacks = [
        e for e in live if e.kind in {"complete", "incomplete", "interception", "sack"}
    ]
    league_completion = sum(e.kind == "complete" for e in league_dropbacks) / len(league_dropbacks)
    for formation in Defense:
        for play in Play:
            effect = (run_effects if play.value <= 5 else pass_effects).get(team, 0.0)
            effect += (
                defensive_profile.run_yards_offset
                if play.value <= 5
                else defensive_profile.pass_yards_offset
            )
            tactical = tactics.lookup(formation, play)
            effect += tactical.yard_offset
            tokens = dict.fromkeys(range(1, 6), "")
            ordinary_weights = defensive_weights()
            response_offsets: dict[int, int] = {}
            semantic_allocations: list[dict[str, Any]] = []
            if play.value >= 6 or tactics.origin != "neutral":
                remaining = defensive_weights()
                completion_effect = rate_effects["complete"].get(team, 0) if play.value >= 6 else 0
                interception_effect = (
                    rate_effects["interception"].get(team, 0) if play.value >= 6 else 0
                )
                sack_effect = rate_effects["sack"].get(team, 0) if play.value >= 6 else 0
                if play.value >= 6:
                    completion_effect += defensive_profile.completion_shift
                    interception_effect += defensive_profile.interception_shift
                    sack_effect += defensive_profile.sack_shift
                response_values = neutral_response_values["complete" if play.value >= 6 else "rush"]
                desired = [
                    ("INT", max(0, interception_effect + tactical.interception_delta)),
                    ("QT", max(0, sack_effect + tactical.sack_delta)),
                    ("QR", max(0, tactical.scramble_delta)),
                    ("(B)", max(0, tactical.breakaway_delta)),
                    (
                        "BLACK",
                        max(
                            0,
                            -completion_effect / max(0.1, league_completion)
                            + tactical.incomplete_delta,
                        ),
                    ),
                    (
                        "RESPONSE",
                        max(
                            0,
                            completion_effect / max(0.1, 1 - league_completion)
                            + tactical.override_delta,
                        ),
                    ),
                ]
                for index, (token, probability) in enumerate(
                    sorted(desired, key=lambda item: item[1])
                ):
                    if not remaining:
                        break
                    rows = nearest_mass_rows(
                        remaining,
                        min(1, probability * 36 / sum(remaining.values())),
                        seed=_seed(seed, f"defense/{formation}/{play}/{index}"),
                    )
                    mass = sum(remaining[row] for row in rows)
                    attainable = {0}
                    for weight in remaining.values():
                        attainable |= {value + weight for value in tuple(attainable)}
                    semantic_allocations.append(
                        {
                            "token": token,
                            "requested_probability": probability,
                            "available_physical_mass": sum(remaining.values()),
                            "attainable_physical_masses": sorted(attainable),
                            "selected_physical_mass": mass,
                            "rows": sorted(rows),
                            "encoded_probability": mass / 36,
                            "probability_error": mass / 36 - probability,
                            "scope": (
                                "printed defensive-cell mass before offense priority "
                                "and supplemental resolution"
                            ),
                        }
                    )
                    if token == "RESPONSE":
                        response_offsets = quantized_defensive_offsets(
                            {row: remaining[row] for row in rows},
                            effect,
                            seed=_seed(seed, f"defense-response/{formation}/{play}"),
                        )
                    position = 0
                    for row in sorted(rows):
                        if token == "INT":
                            if not defensive_interception_locations:
                                raise ValueError(
                                    "no known interception location evidence for defense"
                                )
                            ordered_locations = sorted(defensive_interception_locations)
                            point = int(
                                (position + remaining[row] / 2) / mass * len(ordered_locations)
                            )
                            tokens[row] = _location_token(
                                "INT", ordered_locations[min(len(ordered_locations) - 1, point)]
                            )
                        elif token == "RESPONSE":
                            point = int(
                                (position + remaining[row] / 2) / mass * len(response_values)
                            )
                            response_yards = response_values[min(len(response_values) - 1, point)]
                            tokens[row] = f"({response_yards + response_offsets[row]})"
                        else:
                            tokens[row] = token
                        position += remaining[row]
                        del remaining[row]
                ordinary_weights = remaining
            offsets = quantized_defensive_offsets(
                ordinary_weights, effect, seed=_seed(seed, f"defense-offset/{formation}/{play}")
            )
            for row, value in offsets.items():
                tokens[row] = str(value) if value else ""
            ordinary_mass = sum(ordinary_weights.values())
            achieved = (
                sum(ordinary_weights[row] * value for row, value in offsets.items()) / ordinary_mass
                if ordinary_mass
                else None
            )
            defensive_quantization[f"{formation.value}/{play.value}"] = {
                "requested_yardage_effect": effect,
                "semantic_allocations": semantic_allocations,
                "ordinary_physical_mass": ordinary_mass,
                "ordinary_achieved_effect": achieved,
                "ordinary_quantization_error": achieved - effect if achieved is not None else None,
                "response_offset_physical_mass": sum(
                    defensive_weights()[row] for row in response_offsets
                ),
                "method": (
                    "nearest attainable adjacent-integer mean, independently within "
                    "ordinary and numeric response rows"
                ),
            }
            for row, token in tokens.items():
                defense.append(
                    DefensiveCell(
                        formation, play, row, _cell(token, source_hash, filename, row, play.value)
                    )
                )
    specials = []
    special_evidence: dict[str, Any] = {}
    for index, column in enumerate(SpecialTeamsColumn):
        requested_specials: list[tuple[str, float]] = []
        source_locations: dict[str, list[tuple[int, float]]] = {}
        distribution_scope = (
            "PBP-only ordinary return gains; F locations and rates are separate; "
            "explicit supplied-league pooling when own returns are absent"
        )
        if column in {SpecialTeamsColumn.PUNT, SpecialTeamsColumn.KICKOFF}:
            distribution_scope = (
                "PBP-only ordinary kick distances; small-sample pool policy is recorded separately"
            )
            kind = "punt" if column is SpecialTeamsColumn.PUNT else "kickoff"
            values = _pool(own, live, kind, diagnostics)
            sample = [e for e in own if e.kind == kind]
            blocked_rate = sum(e.blocked for e in sample) / max(1, len(sample))
            requested_specials = [("BK", blocked_rate)] if kind == "punt" else []
            blocked_locations, blocked_evidence = _blocked_locations(sample, live)
            source_locations = {"blocked_kick": [(value, 1.0) for value in blocked_locations]}
            tokens = _column(
                values,
                requested_specials,
                seed=_seed(seed, column.value),
                locations={"BK": blocked_locations},
            )
            special_evidence[column.value] = blocked_evidence
        elif column is SpecialTeamsColumn.FIELD_GOAL:
            distribution_scope = (
                "PBP-only modeled maximum-LOS thresholds from observed attempts; "
                "not a raw kick-distance histogram"
            )
            located_attempts = [e for e in own if e.kind == "field_goal" and e.yards is not None]
            sample = [e for e in located_attempts if e.kick_good is not None]
            if not sample:
                raise ValueError("no known field_goal outcome/yardage evidence")
            special_evidence[column.value] = {
                "known_outcomes": len(sample),
                "unknown_outcomes": len(located_attempts) - len(sample),
                "policy": (
                    "PBP local-distance empirical curve; "
                    "no pseudocounts or long-range extrapolation"
                ),
                "maximum_observed_kick_distance": max(e.yards for e in sample),
            }
            # A per-row maximum LOS distance. Empirical success curve is constrained
            # monotone; kick distance includes 7-yard hold + 10-yard end zone.
            limits = []
            for i in range(216):
                q = (i + 0.5) / 216
                limit = 0
                for distance in range(17, min(70, max(e.yards for e in sample)) + 1):
                    neighborhood = [e for e in sample if abs(e.yards - distance) <= 10]
                    if not neighborhood:
                        continue
                    rate = sum(e.kick_good is True for e in neighborhood) / len(neighborhood)
                    if q <= min(1, max(0, rate + profile.field_goal_shift)):
                        limit = max(limit, distance - 17)
                limits.append(limit)
            tokens = _column(limits, [], seed=_seed(seed, column.value))
            values = limits
        else:
            kind = {
                SpecialTeamsColumn.KICKOFF_RETURN: "kickoff",
                SpecialTeamsColumn.PUNT_RETURN: "punt",
                SpecialTeamsColumn.INTERCEPTION_RETURN: "interception",
            }[column]
            sample = [
                e
                for e in live
                if e.opponent == team and e.kind == kind and e.return_yards is not None
            ]
            values = [round(e.return_yards * profile.return_yards_scale) for e in sample]
            empirical_sample = sample
            if not values:
                empirical_sample = [
                    e for e in live if e.kind == kind and e.return_yards is not None
                ]
                values = [
                    round(e.return_yards * profile.return_yards_scale)
                    for e in live
                    if e.kind == kind and e.return_yards is not None
                ]
                diagnostics[column.value] = {"samples": 0, "fallback": "league-empirical"}
            if not values:
                raise ValueError(
                    f"no {column.value} evidence; supply individual-play source evidence"
                )
            fumbles = [e for e in empirical_sample if e.fumble and e.fumble_team == e.opponent]
            ordinary_returns = [
                e for e in empirical_sample if not (e.fumble and e.fumble_team == e.opponent)
            ]
            values = [round(e.return_yards * profile.return_yards_scale) for e in ordinary_returns]
            known_fumble_sample = [e for e in empirical_sample if e.fumble is not None]
            fumble_probability = _return_fumble_probability(empirical_sample, profile.fumble_scale)
            requested_specials = [("F", fumble_probability)]
            source_locations = {
                "fumble": [
                    (round(e.return_yards * profile.return_yards_scale), 1.0) for e in fumbles
                ]
            }
            tokens = _column(
                values,
                requested_specials,
                seed=_seed(seed, column.value),
                locations={
                    "F": [round(e.return_yards * profile.return_yards_scale) for e in fumbles]
                },
            )
            special_evidence[column.value] = {
                "known_return_samples": len(sample),
                "ordinary_return_samples": len(ordinary_returns),
                "modeled_samples": len(empirical_sample),
                "fumbles": len(fumbles),
                "fumble_probability_fallback": False,
                "fumble_probability_unidentified": not known_fumble_sample,
                "unidentified_fumble_owner": sum(
                    e.fumble is True and e.fumble_team is None for e in empirical_sample
                ),
                "other_team_fumbles": sum(
                    e.fumble is True and e.fumble_team == e.team for e in empirical_sample
                ),
                "return_ownership": (
                    "explicit fumbling team equals original receiving/intercepting team"
                ),
            }
        source_columns.append(
            _column_evidence(
                "special_teams",
                column.value,
                [(yards, 1.0) for yards in values],
                requested_specials,
                locations=source_locations,
                scope=distribution_scope,
            )
        )
        specials.extend(
            SpecialTeamsCell(column, row, _cell(token, source_hash, filename, row, 20 + index))
            for row, token in tokens.items()
        )
    pat_sample = [e for e in own if e.kind == "pat" and e.kick_good is not None]
    if not pat_sample:
        raise ValueError("no PAT attempt evidence")
    misses = nearest_mass_rows(
        offensive_weights(),
        sum(not e.kick_good for e in pat_sample) / len(pat_sample),
        seed=_seed(seed, "PAT"),
    )
    pat = tuple(
        PatOutcome(
            row,
            row not in misses,
            _cell("NG" if row in misses else "", source_hash, filename, row, 30).provenance,
        )
        for row in range(10, 40)
    )
    own_fumble_evidence = tuple(
        event
        for event in live
        if event.fumble_team == team
        or (event.team == team and event.fumble_team is None and _primary_fumble(event))
        or (event.recovery_team == team and (event.fumble_count or 0) > 1)
    )
    recovery, recovery_evidence = _recovery_probability(own_fumble_evidence, live, team=team)
    weights = offensive_weights()
    end = min(
        range(10, 39),
        key=lambda r: abs(sum(w for x, w in weights.items() if x <= r) / 216 - recovery),
    )
    achieved_recovery = sum(w for row, w in weights.items() if row <= end) / 216
    recovery_evidence.update(
        {
            "requested_probability": recovery,
            "achieved_probability": achieved_recovery,
            "quantization_error": achieved_recovery - recovery,
            "constraint": (
                "current CSV requires nonempty prefix ending before 39; "
                "zero and one are not exactly representable; DATA-023"
            ),
        }
    )
    chart = TeamChart(
        1,
        name,
        season,
        tuple(sorted(offense, key=lambda c: (c.play, c.roll))),
        tuple(sorted(supplemental, key=lambda c: (c.column.value, c.roll))),
        tuple(defense),
        tuple(sorted(specials, key=lambda c: (c.column.value, c.roll))),
        pat,
        range(10, end + 1),
    )
    metadata = TeamFileMetadata(
        LOCAL_PLACEHOLDER_POWER_RATING, (), "Generated local prototype", source_hash, (), True
    )
    # Round-trip validation is part of generation, before any output exists.
    chart, metadata = team_from_files(
        team_to_files(chart, metadata), provenance_to_csv(chart, metadata)
    )
    audit_report, chart_audit = _checked_audit(chart)
    distribution_audits = compare_column_distributions(audit_report, source_columns)
    for report in distribution_audits:
        if report["section"] == "offense":
            family_diagnostics[report["column"]]["distribution_audit"] = report
    manifest = {
        "schema_version": 1,
        "tool_version": TOOL_VERSION,
        "chart_audit": chart_audit,
        "team": team,
        "name": name,
        "season": season,
        "seed": seed,
        "source_sha256": source_hash,
        "profile": asdict(profile),
        "defensive_profile": asdict(defensive_profile),
        "source_summary": summarize_events(events, team),
        "source_scope": "all supplied live events, including postseason and overtime",
        "tactical_evidence": (
            "inferred-neutral"
            if tactics.origin == "neutral"
            else "authored-model-policy"
            if tactics.origin == "authored-bb-yardage-v1"
            else "synthetic-test-effects"
        ),
        "tactical_profile": {
            "origin": tactics.origin,
            "sha256": tactics.sha256,
            "source_hashes": list(tactics.source_hashes),
            "authored_experimental": tactics.origin == "authored-bb-yardage-v1",
        },
        "family_evidence": family_diagnostics,
        "source_distribution_audits": distribution_audits,
        "defensive_quantization": defensive_quantization,
        "defensive_distribution_audit": {
            "state": "unidentifiable",
            "reason": "formation-specific historical distributions are not observed; "
            "defensive cells are inferred modifiers/responses, not direct offensive gain samples",
            "validation": "real-engine selected-actual-matchup defensive targets; "
            "independent private reference semantics remain diagnostic only",
        },
        "opponent_model": {
            "yardage_effects": {
                "rush": run_effects.get(team, 0),
                "complete": pass_effects.get(team, 0),
            },
            "rate_effects": {
                "completion" if key == "complete" else key: effect.get(team, 0)
                for key, effect in rate_effects.items()
            },
        },
        "sparse_categories": diagnostics,
        "special_evidence": special_evidence,
        "supplemental_evidence": supplemental_evidence,
        "location_evidence": {
            "interception": interception_evidence,
            "defensive_interception": defensive_interception_evidence,
        },
        "recovery_evidence": recovery_evidence,
        "modeled_priors": {
            "option_SOP_probability": option_rates["SOP"],
            "option_BLP_probability": option_rates["BLP"],
            "pass_QR_probability": scramble_rate,
            "breakaway_tail_fraction": 0.1,
            "breakaway_tail_method": (
                "compatible empirical conditional tails; otherwise direct gains"
            ),
            "recovery_probability": recovery,
            "recovery_fallback": recovery_evidence["method"] == "league-PBP",
            "fumble_probability_fallback": False,
            "fumble_probability_unidentified": not known_fumbles,
            "defense_effect_bound_yards": None,
            "opponent_ridge_play_count": 100,
            "defensive_completion_yards": (
                "source league empirical conditional gains plus defensive effect; "
                "independent of own offense"
            ),
        },
        "mechanics": {
            "guaranteed_TD_cells": False,
            "B_QR_QT": True,
            "option_SOP_BLP": any(option_rates.values()),
            "fumbles_recovery": True,
            "penalties": True,
            "OOB": "positive-only narrative incidence within matching ordinary numeric support; "
            "unknown counts and exact dice achievement reported",
            "special_teams": True,
            "defensive_formations": (
                "not directly observed; modeled prior recorded in tactical_profile"
            ),
            "variable_responses": "not identifiable; fixed empirical results used",
            "advanced_II": False,
            "QB_Sneak_RZDZ": "engine-owned legal actions",
        },
        "penalty_evidence": {
            "accepted": len(penalties),
            "encoded_side_distance": sum(penalty_counts.values()),
            "unidentified_side_distance": len(penalties) - sum(penalty_counts.values()),
            "source_types": dict(Counter(e.penalty_type or "unknown" for e in penalties)),
            "policy": (
                "observed nominal fixed enforcement; no inferred PI spot/automatic first down"
            ),
        },
        "provenance_coordinates": "generated virtual evidence table; not PDF geometry",
        "limitations": [
            "OOB is a positive-evidence lower-bound model; unknown is not observed in bounds",
            "Designed calls and formations mostly unobserved",
            "Unknown interception locations remain unknown; known INT-only pooling is explicit",
            "Aggregate reconciliation must be reviewed separately",
            "Neutral/small-cohort simulations are not a historical-schedule fit",
        ],
    }
    return chart, metadata, manifest


def write_bundle(
    root: Path,
    bundle: tuple[TeamChart, TeamFileMetadata, dict[str, Any]],
) -> None:
    """Write a new immutable private candidate; refuse overwrite and symlink paths."""
    root = private_destination(root)
    chart, metadata, manifest = bundle
    slug = team_folder_name(chart.name)
    season = private_destination(root / str(chart.season))
    folder = private_destination(season / slug)
    if folder.exists():
        raise FileExistsError("candidate already exists; select a new immutable output root")
    audit_report, audit_summary = _checked_audit(chart)
    if manifest.get("chart_audit") != audit_summary:
        raise ValueError("bundle semantic audit differs from its generation manifest")
    # Validate every existing child path before creating any candidate output.
    provenance = private_destination(season / "provenance")
    reports = private_destination(root / "generation-manifests")
    audits = private_destination(root / "generation-audits")
    folder.mkdir(parents=True, mode=0o700)
    provenance.mkdir(exist_ok=True, mode=0o700)
    outputs = {folder / name: content for name, content in team_to_files(chart, metadata).items()}
    outputs[provenance / f"{slug}.csv"] = provenance_to_csv(chart, metadata)
    reports.mkdir(exist_ok=True, mode=0o700)
    audits.mkdir(exist_ok=True, mode=0o700)
    outputs[reports / f"{chart.season}-{slug}.json"] = json.dumps(manifest, indent=2) + "\n"
    outputs[audits / f"{chart.season}-{slug}.json"] = json.dumps(audit_report, indent=2) + "\n"
    for path, content in outputs.items():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
