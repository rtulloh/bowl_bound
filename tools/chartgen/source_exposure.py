"""Historical source exposure, independently of simulation repetitions.

The six-game floor mirrors the existing baseline source-game minimum. It is an
engineering qualification floor, not a proof of representative historical fit.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence, Set
from typing import Any, Literal

from .evidence import Event
from .optional_flags import optional_measurement_missing_evidence
from .primary_fumbles import primary_source_fumble

MINIMUM_SOURCE_GAMES = 6


def historical_exposure(
    events: Sequence[Event],
    team: str,
    game_ids: Set[str],
    *,
    role: Literal["offense", "defense"],
) -> dict[str, Any]:
    """Count known individual-play evidence only within exact selected fixtures.

    Pure-rush efficiency excludes sacks, matching the Phase1 run pool. NCAA
    rushing totals remain separate diagnostics. A known zero rate has
    exposure; unknown ownership does not become a known no-fumble observation.
    """
    if role not in {"offense", "defense"}:
        raise ValueError("historical exposure role must be offense or defense")
    names = (
        "completion",
        "interception",
        "sack",
        "pure_rush_yards_per_attempt",
        "pass_yards_per_attempt",
        "fumble",
    )
    counts: dict[str, Counter[str]] = {name: Counter() for name in names}
    numerators: dict[str, Counter[str]] = {name: Counter() for name in names}
    unknown: Counter[str] = Counter()
    missing: dict[str, set[str]] = {}
    for event in events:
        if (
            event.game_id not in game_ids
            or (event.team if role == "offense" else event.opponent) != team
            or event.no_play
            or event.event_phase == "try"
        ):
            continue
        pass_attempt = event.kind in {"complete", "incomplete", "interception"}
        eligible = {
            "completion": pass_attempt,
            "interception": pass_attempt,
            "sack": pass_attempt or event.kind == "sack",
            "pure_rush_yards_per_attempt": event.kind == "rush",
            "pass_yards_per_attempt": pass_attempt,
            "fumble": event.kind in {"rush", "sack", "complete", "incomplete", "interception"},
        }
        for name, included in eligible.items():
            if not included:
                continue
            if name == "fumble":
                missing.setdefault(name, set()).update(
                    optional_measurement_missing_evidence(
                        event.optional_flag_policy,
                        event.optional_flag_observations,
                        event.optional_flag_source_sha256,
                    )
                )
            identified = not (
                name == "fumble"
                and primary_source_fumble(event) is None
                or name in {"pure_rush_yards_per_attempt", "pass_yards_per_attempt"}
                and event.kind in {"rush", "sack", "complete"}
                and event.yards is None
            )
            if identified:
                counts[name][event.game_id] += 1
                if name == "completion":
                    value = int(event.kind == "complete")
                elif name == "interception":
                    value = int(event.kind == "interception")
                elif name == "sack":
                    value = int(event.kind == "sack")
                elif name == "fumble":
                    value = int(primary_source_fumble(event) is True)
                else:
                    value = event.yards if event.kind in {"rush", "sack", "complete"} else 0
                assert value is not None
                numerators[name][event.game_id] += value
            else:
                unknown[name] += 1
                if name == "fumble":
                    missing.setdefault(name, set()).add("unknown_primary_fumble_presence")
    for event in events:
        if event.game_id not in game_ids or event.no_play or role != "offense":
            continue
        if event.event_phase == "try" and event.kind != "pat":
            continue
        metric = None
        if event.team == team and event.kind in {"punt", "kickoff"}:
            metric = f"drawn_{event.kind}_yards"
            value = event.yards
            identified = value is not None
        elif event.opponent == team and event.kind in {"punt", "kickoff", "interception"}:
            metric = f"drawn_{event.kind}_return_yards"
            value = event.return_yards
            identified = value is not None
        elif event.team == team and event.kind == "pat":
            metric = "pat"
            value = int(event.kick_good) if event.kick_good is not None else None
            identified = value is not None
            missing.setdefault(metric, set()).update(
                optional_measurement_missing_evidence(
                    event.optional_flag_policy,
                    event.optional_flag_observations,
                    event.optional_flag_source_sha256,
                )
            )
        if metric is not None:
            counts.setdefault(metric, Counter())
            numerators.setdefault(metric, Counter())
            if identified:
                counts.setdefault(metric, Counter())[event.game_id] += 1
                assert value is not None
                numerators.setdefault(metric, Counter())[event.game_id] += value
            else:
                unknown[metric] += 1
    metrics = {}
    for name in sorted(counts):
        games = counts[name]
        total = sum(games.values())
        estimate = sum(numerators[name].values()) / total if total else None
        variance = (
            len(games)
            / (len(games) - 1)
            * sum((numerators[name][game] - estimate * count) ** 2 for game, count in games.items())
            / total**2
            if len(games) > 1 and estimate is not None
            else None
        )
        metrics[name] = {
            "source_mean": estimate,
            "source_ratio_variance": variance,
            "source_standard_error": math.sqrt(variance) if variance is not None else None,
            "source_sampling_method": (
                "observed-game cluster-robust ratio; finite-cluster correction"
            ),
            "uncertainty_state": (
                "insufficient_source_clusters"
                if variance is None
                else "zero_between_game_variation_not_proof_of_no_risk"
                if variance == 0
                else "estimated_from_observed_game_clusters"
            ),
            "uncertainty_limits": (
                "assumes independent observed game clusters; "
                "not a population-confidence guarantee; "
                "zero observed variation does not establish absence of unseen rare risk; "
                "excludes opponent-model, classification and systematic missingness uncertainty"
            ),
            "source_events": total,
            "unknown_source_events": unknown[name],
            "source_game_ids": sorted(games),
            "source_games": len(games),
            "events_per_game": dict(sorted(games.items())),
            "effective_game_count": total**2 / sum(value**2 for value in games.values())
            if total
            else 0.0,
            "missing_evidence": sorted(missing.get(name, ())),
            "qualified": len(games) >= MINIMUM_SOURCE_GAMES and not missing.get(name),
        }
    qualified = bool(game_ids) and all(metrics[name]["qualified"] for name in names)
    return {
        "schema_version": 4,
        "team_id": team,
        "role": role,
        "selected_game_ids": sorted(game_ids),
        "minimum_source_games": MINIMUM_SOURCE_GAMES,
        "metrics": metrics,
        "qualified": qualified,
        "state": "qualified_historical_exposure"
        if qualified
        else "unverified_source_mechanism"
        if any(missing.values())
        else "sparse_historical_exposure",
        "limits": (
            "six selected source games is a necessary engineering floor, not an accuracy "
            "or representativeness proof; repeated simulations add no historical evidence"
        ),
    }
