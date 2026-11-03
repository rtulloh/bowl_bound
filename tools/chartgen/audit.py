"""Exhaustive physical probability audit through the engine priority resolver."""

from __future__ import annotations

from collections import Counter
from typing import Any

from bowl_bound.models import Defense, Play, TeamChart
from bowl_bound.resolution import resolve_cells

from .generate import defensive_weights, offensive_weights


def audit_chart(chart: TeamChart) -> dict[str, Any]:
    """Audit every play/formation and weighted physical pair without reroll guesses.

    Pending B/QR/QT/Option/penalty/recovery are reported as pending mechanisms.
    Complete-game batches validate their eventual engine-owned resolution.
    """
    offense = {(record.play, record.roll): record.cell for record in chart.offense}
    defense = {(record.defense, record.play, record.roll): record.cell for record in chart.defense}
    pairs = []
    for play in Play:
        for formation in Defense:
            masses: Counter[str] = Counter()
            for off_roll, off_mass in offensive_weights().items():
                for def_roll, def_mass in defensive_weights().items():
                    result = resolve_cells(
                        offense[play, off_roll], defense[formation, play, def_roll]
                    )
                    label = result.kind.value if result.kind is not None else result.operation.value
                    masses[("pending:" if result.pending else "final:") + label] += (
                        off_mass * def_mass
                    )
            pairs.append(
                {"play": play.value, "formation": formation.value, "outcome_masses": dict(masses)}
            )
    return {
        "physical_offensive_combinations": sum(offensive_weights().values()),
        "physical_defensive_combinations": sum(defensive_weights().values()),
        "play_formation_pairs": len(pairs),
        "pairs": pairs,
        "scope": "engine priority outcomes; pending branches are not terminal probability claims",
    }
