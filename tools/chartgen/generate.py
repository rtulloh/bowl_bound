"""Deterministic empirical quantization into the production Bowl Bound format.

No historical chart values are embedded here. Unobserved tactics use an explicit
neutral estimator. Physical row masses come exclusively from engine dice faces.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
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

from .evidence import Event, summarize_events
from .private_io import private_destination

if TYPE_CHECKING:
    from .tactics import TacticalProfile

TOOL_VERSION = "college-chartgen-v1"
MINIMUM_FAMILY_SAMPLES = 30


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


def _column(
    values: Sequence[int],
    specials: Sequence[tuple[str, float]],
    *,
    seed: int,
    out_of_bounds: float = 0.0,
) -> dict[int, str]:
    if not values:
        raise ValueError("numeric distribution has no known evidence")
    weights = offensive_weights()
    result: dict[int, str] = {}
    original_mass = sum(weights.values())
    for index, (token, probability) in enumerate(sorted(specials, key=lambda item: item[1])):
        if not weights:
            raise ValueError("special probabilities consume every numeric cell")
        remaining_probability = min(1.0, probability * original_mass / sum(weights.values()))
        selected = nearest_mass_rows(weights, remaining_probability, seed=_seed(seed, str(index)))
        for row in selected:
            result[row] = token
            del weights[row]
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


def _source(events: Sequence[Event]) -> tuple[str, str]:
    encoded = json.dumps([e.to_dict() for e in events], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest(), "generated-model-v1.json"


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


def _pool(
    own: Sequence[Event],
    league: Sequence[Event],
    kind: str,
    diagnostics: dict[str, Any],
) -> list[int]:
    values = _known(own, kind)
    if len(values) < MINIMUM_FAMILY_SAMPLES:
        fallback = _known(league, kind)
        diagnostics[kind] = {
            "samples": len(values),
            "fallback": "league-empirical",
            "fallback_samples": len(fallback),
        }
        # Partial pooling gives the observed team increasing influence. No values
        # are invented if the entire supplied source lacks this category.
        # Cover the whole empirical distribution rather than early source rows.
        # These are pooled observations, not additional independent samples.
        ordered = sorted(fallback)
        needed = min(len(ordered), max(0, MINIMUM_FAMILY_SAMPLES - len(values)))
        values += [ordered[int((index + 0.5) * len(ordered) / needed)] for index in range(needed)]
    else:
        diagnostics[kind] = {"samples": len(values), "fallback": None}
    if not values:
        raise ValueError(f"no known {kind} yardage evidence; supply source/aggregate evidence")
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
    seasons: frozenset[int]
    source_hash: str
    source_filename: str
    run_effects: Mapping[str, float]
    pass_effects: Mapping[str, float]
    rate_effects: Mapping[str, Mapping[str, float]]

    @classmethod
    def from_events(cls, events: Sequence[Event]) -> EvidenceModel:
        snapshot = tuple(events)
        live = tuple(e for e in snapshot if not e.no_play)
        grouped: dict[str, list[Event]] = defaultdict(list)
        for event in live:
            grouped[event.team].append(event)
        source_hash, filename = _source(snapshot)
        return cls(
            snapshot,
            live,
            {t: tuple(rows) for t, rows in grouped.items()},
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
    tactics: TacticalProfile | None = None,
    model: EvidenceModel | None = None,
) -> tuple[TeamChart, TeamFileMetadata, dict[str, Any]]:
    """Build a complete local-only bundle from normalized evidence, without I/O."""
    profile = profile or CalibrationProfile()
    from .tactics import TacticalProfile

    tactics = tactics or TacticalProfile.neutral()
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
    rush = _pool(own, live, "rush", diagnostics)
    complete = _pool(own, live, "complete", diagnostics)
    sacks = _pool(own, live, "sack", diagnostics)
    run_effects = model.run_effects
    pass_effects = model.pass_effects
    run_correction = mean(run_effects.get(e.opponent, 0.0) for e in own)
    pass_correction = mean(pass_effects.get(e.opponent, 0.0) for e in own)
    rush = [round((yards - run_correction) * profile.run_yards_scale) for yards in rush]
    complete = [round((yards - pass_correction) * profile.pass_yards_scale) for yards in complete]
    dropbacks = [e for e in own if e.kind in {"complete", "incomplete", "interception", "sack"}]
    if not dropbacks:
        raise ValueError("no pass outcome evidence")
    count = len(dropbacks)
    rate_effects = model.rate_effects
    int_correction = mean(rate_effects["interception"].get(e.opponent, 0) for e in dropbacks)
    sack_correction = mean(rate_effects["sack"].get(e.opponent, 0) for e in dropbacks)
    completion_correction = mean(rate_effects["complete"].get(e.opponent, 0) for e in dropbacks)
    int_rate = (
        max(0, sum(e.kind == "interception" for e in dropbacks) / count - int_correction)
        * profile.interception_scale
    )
    sack_rate = (
        max(0, sum(e.kind == "sack" for e in dropbacks) / count - sack_correction)
        * profile.sack_scale
    )
    complete_rate = max(
        0.05,
        min(
            0.9,
            sum(e.kind == "complete" for e in dropbacks) / count
            - completion_correction
            + profile.completion_shift,
        ),
    )
    snaps = [e for e in own if e.kind in {"rush", "complete", "incomplete", "interception", "sack"}]
    known_fumbles = [e for e in snaps if e.fumble is not None]
    fumble_rate = (
        (sum(e.fumble is True for e in known_fumbles) / len(known_fumbles))
        if known_fumbles
        else 2 / 216
    ) * profile.fumble_scale
    penalties = [e for e in events if e.team == team and e.penalty and not e.penalty_declined]
    penalty_rate = min(0.08, len(penalties) / max(1, len(snaps)))
    # Explicit sparse mechanics priors: two physical outcomes each, independent of
    # historical matrices. These describe modeled behavior, not observed calls.
    rare = 2 / 216
    oob = sum(e.out_of_bounds is True for e in own) / max(1, sum(e.yards is not None for e in own))
    offense = []
    family_diagnostics = {}
    tail = (
        sorted(rush)[max(0, int(len(rush) * 0.9)) :]
        + sorted(complete)[max(0, int(len(complete) * 0.9)) :]
    )
    for play in Play:
        specific = [e.yards for e in own if e.called_family == play.value and e.yards is not None]
        if len(specific) >= MINIMUM_FAMILY_SAMPLES:
            correction = run_correction if play.value <= 5 else pass_correction
            scale = profile.run_yards_scale if play.value <= 5 else profile.pass_yards_scale
            values = [round((yards - correction) * scale) for yards in specific]
        else:
            values = rush if play.value <= 5 else complete
        family_diagnostics[str(play.value)] = {
            "observed": len(specific),
            "method": "family-empirical"
            if len(specific) >= MINIMUM_FAMILY_SAMPLES
            else "pooled-run"
            if play.value <= 5
            else "pooled-pass",
        }
        specials = [("F", fumble_rate), ("OFF 5", penalty_rate / 2), ("DEF 5Y", penalty_rate / 2)]
        body = sorted(values)[: max(1, int(len(values) * 0.9))]
        difference = mean(tail) - mean(body)
        break_probability = (mean(values) - mean(body)) / difference if difference > 0 else rare
        break_probability = min(0.3, max(0, break_probability)) if mean(tail) > 0 else 0
        values = body
        if play.value <= 5:
            specials += [("B", break_probability)]
            if play is Play.FIVE:
                specials += [("SOP", rare), ("BLP", rare)]
        else:
            specials += [
                ("B", complete_rate * break_probability),
                ("INT 0", int_rate),
                ("QT", sack_rate),
                ("QR", rare),
                (
                    "BLACK",
                    max(
                        0.0,
                        1
                        - complete_rate
                        - int_rate
                        - sack_rate
                        - rare
                        - fumble_rate
                        - penalty_rate,
                    ),
                ),
            ]
        column = _column(values, specials, seed=_seed(seed, f"offense/{play}"), out_of_bounds=oob)
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
    for index, column in enumerate(SupplementalColumn):
        values = (
            tail
            if column is SupplementalColumn.BREAKAWAY
            else sacks
            if column is SupplementalColumn.QUARTERBACK_TRAPPED
            else rush
        )
        tokens = _column(values, [], seed=_seed(seed, column.value), out_of_bounds=oob)
        supplemental.extend(
            SupplementalCell(column, row, _cell(token, source_hash, filename, row, 10 + index))
            for row, token in tokens.items()
        )
    defense = []
    league_dropbacks = [
        e for e in live if e.kind in {"complete", "incomplete", "interception", "sack"}
    ]
    league_completion = sum(e.kind == "complete" for e in league_dropbacks) / len(league_dropbacks)
    for formation in Defense:
        for play in Play:
            effect = (run_effects if play.value <= 5 else pass_effects).get(team, 0.0)
            tactical = tactics.lookup(formation, play)
            value = round(max(-4, min(4, effect)) + tactical.yard_offset)
            tokens = dict.fromkeys(range(1, 6), str(value) if value else "")
            if play.value >= 6 or tactics.origin != "neutral":
                remaining = defensive_weights()
                completion_effect = rate_effects["complete"].get(team, 0) if play.value >= 6 else 0
                interception_effect = (
                    rate_effects["interception"].get(team, 0) if play.value >= 6 else 0
                )
                sack_effect = rate_effects["sack"].get(team, 0) if play.value >= 6 else 0
                response_mean = mean(complete if play.value >= 6 else rush) + value
                desired = [
                    ("INT 0", max(0, interception_effect + tactical.interception_delta)),
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
                        f"({round(response_mean)})",
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
                    for row in rows:
                        tokens[row] = token
                        del remaining[row]
            for row, token in tokens.items():
                defense.append(
                    DefensiveCell(
                        formation, play, row, _cell(token, source_hash, filename, row, play.value)
                    )
                )
    specials = []
    special_evidence: dict[str, Any] = {}
    for index, column in enumerate(SpecialTeamsColumn):
        if column in {SpecialTeamsColumn.PUNT, SpecialTeamsColumn.KICKOFF}:
            kind = "punt" if column is SpecialTeamsColumn.PUNT else "kickoff"
            values = _pool(own, live, kind, diagnostics)
            sample = [e for e in own if e.kind == kind]
            blocked_rate = sum(e.blocked for e in sample) / max(1, len(sample))
            tokens = _column(
                values,
                [("BK 0", blocked_rate)] if kind == "punt" else [],
                seed=_seed(seed, column.value),
            )
        elif column is SpecialTeamsColumn.FIELD_GOAL:
            sample = [e for e in own if e.kind == "field_goal" and e.yards is not None]
            if not sample:
                raise ValueError("no field_goal yardage evidence")
            # A per-row maximum LOS distance. Empirical success curve is constrained
            # monotone; kick distance includes 7-yard hold + 10-yard end zone.
            limits = []
            for i in range(216):
                q = (i + 0.5) / 216
                limit = 0
                for distance in range(17, 71):
                    neighborhood = [e for e in sample if abs(e.yards - distance) <= 10]
                    if not neighborhood:
                        continue
                    rate = (sum(e.kick_good is True for e in neighborhood) + 1) / (
                        len(neighborhood) + 2
                    )
                    if q <= min(1, max(0, rate + profile.field_goal_shift)):
                        limit = max(limit, distance - 17)
                limits.append(limit)
            tokens = _column(limits, [], seed=_seed(seed, column.value))
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
                raise ValueError(f"no {column.value} evidence; supply source/aggregate evidence")
            fumbles = [e for e in empirical_sample if e.fumble]
            known_fumble_sample = [e for e in empirical_sample if e.fumble is not None]
            fumble_probability = (
                len(fumbles) / len(known_fumble_sample) if known_fumble_sample else 2 / 216
            ) * profile.fumble_scale
            location = round(mean(e.return_yards for e in fumbles)) if fumbles else 0
            token = "F" if not location else f"F {'-' if location < 0 else '+'} {abs(location)}"
            tokens = _column(values, [(token, fumble_probability)], seed=_seed(seed, column.value))
            special_evidence[column.value] = {
                "known_return_samples": len(sample),
                "modeled_samples": len(empirical_sample),
                "fumbles": len(fumbles),
                "fumble_probability_fallback": not known_fumble_sample,
                "return_ownership": "opponent of original kicking/passing team",
            }
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
    fumbles = [e for e in live if e.fumble and e.fumble_lost is not None and e.team == team]
    recovery = sum(e.fumble_lost is False for e in fumbles) / len(fumbles) if fumbles else 0.5
    weights = offensive_weights()
    end = min(
        range(10, 39),
        key=lambda r: abs(sum(w for x, w in weights.items() if x <= r) / 216 - recovery),
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
    manifest = {
        "schema_version": 1,
        "tool_version": TOOL_VERSION,
        "team": team,
        "name": name,
        "season": season,
        "seed": seed,
        "source_sha256": source_hash,
        "profile": asdict(profile),
        "source_summary": summarize_events(events, team),
        "source_scope": "all supplied live events, including postseason and overtime",
        "tactical_evidence": "inferred-neutral"
        if tactics.origin == "neutral"
        else "inferred-private-prior",
        "tactical_profile": {
            "origin": tactics.origin,
            "sha256": tactics.sha256,
            "source_hashes": list(tactics.source_hashes),
        },
        "family_evidence": family_diagnostics,
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
        "modeled_priors": {
            "option_SOP_probability": rare,
            "option_BLP_probability": rare,
            "pass_QR_probability": rare,
            "breakaway_tail_fraction": 0.1,
            "breakaway_tail_method": "joint empirical run/completion upper tails",
            "recovery_probability": recovery,
            "recovery_fallback": not fumbles,
            "fumble_probability_fallback": not known_fumbles,
            "defense_effect_bound_yards": 4,
            "opponent_ridge_play_count": 100,
        },
        "mechanics": {
            "guaranteed_TD_cells": False,
            "B_QR_QT": True,
            "option_SOP_BLP": True,
            "fumbles_recovery": True,
            "penalties": True,
            "OOB": "positive narrative evidence only",
            "special_teams": True,
            "defensive_formations": "neutral inferred",
            "variable_responses": "not identifiable; fixed empirical results used",
            "advanced_II": False,
            "QB_Sneak_RZDZ": "engine-owned legal actions",
        },
        "provenance_coordinates": "generated virtual evidence table; not PDF geometry",
        "limitations": [
            "Designed calls and formations mostly unobserved",
            "No measured air yards; interception location uses explicit modeled +0 prior",
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
    season = root / str(chart.season)
    folder = season / slug
    if folder.exists():
        raise FileExistsError("candidate already exists; select a new immutable output root")
    folder.mkdir(parents=True, mode=0o700)
    provenance = season / "provenance"
    provenance.mkdir(exist_ok=True, mode=0o700)
    outputs = {folder / name: content for name, content in team_to_files(chart, metadata).items()}
    outputs[provenance / f"{slug}.csv"] = provenance_to_csv(chart, metadata)
    reports = root / "generation-manifests"
    reports.mkdir(exist_ok=True, mode=0o700)
    outputs[reports / f"{chart.season}-{slug}.json"] = json.dumps(manifest, indent=2) + "\n"
    for path, content in outputs.items():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
