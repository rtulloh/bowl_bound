"""Independent structural verification for locally exported team folders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bowl_bound.team_csv import TeamFormatError, load_team


class VerificationError(ValueError):
    """A private exported team does not match its expected verification record."""


@dataclass(frozen=True)
class TeamVerification:
    """Counts and metadata verified from one exported team folder."""

    team_name: str
    season: int
    chart_cells: int
    pat_outcomes: int
    recovery_range: range
    pat_failures: tuple[int, ...]
    power_rating: float
    privileges: tuple[str, ...]
    provenance_rows: int


def verify_team_export(
    season_dir: Path, slug: str, expected: Mapping[str, object] | None = None
) -> TeamVerification:
    """Load and verify the complete 810-cell/30-PAT export for one team.

    ``expected`` is intentionally explicit and source-specific. It is used by the local
    Milestone 6 workflow to compare independently recorded values, not to derive expectations
    from the exporter.
    """
    try:
        chart, metadata = load_team(season_dir, slug)
        chart_cells = (
            len(chart.offense)
            + len(chart.supplemental)
            + len(chart.defense)
            + len(chart.special_teams)
        )
        pat_failures = tuple(outcome.roll for outcome in chart.pat_outcomes if not outcome.good)
        provenance = season_dir / "provenance" / f"{slug}.csv"
        provenance_rows = sum(1 for _ in provenance.open(encoding="utf-8", newline="")) - 1
    except (OSError, TeamFormatError, ValueError) as error:
        raise VerificationError("team export is missing, corrupt, or unreadable") from error
    report = TeamVerification(
        chart.name,
        chart.season,
        chart_cells,
        len(chart.pat_outcomes),
        chart.recovery_range,
        pat_failures,
        metadata.power_rating,
        metadata.privileges,
        provenance_rows,
    )
    if report.chart_cells != 810 or report.pat_outcomes != 30 or report.provenance_rows < 840:
        raise VerificationError("team export has incorrect cell, PAT, or provenance counts")
    for key, actual in (expected or {}).items():
        if not hasattr(report, key) or getattr(report, key) != actual:
            label = key.replace("_", " ")
            raise VerificationError(f"team export does not match expected {label}")
    return report
