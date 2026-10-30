"""Synthetic two-team seasons for session, API, and browser tests (no historical data)."""

from dataclasses import replace
from pathlib import Path

from bowl_bound.models import (
    DefensiveCell,
    NormalizedCell,
    OffensiveCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    SupplementalCell,
    TeamChart,
)
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import (
    TeamFileMetadata,
    format_cell,
    provenance_to_csv,
    team_folder_name,
    team_to_files,
)
from tests.test_models import complete_chart, provenance

SHA = "a" * 64


def _with_legend_color(cell: NormalizedCell) -> NormalizedCell:
    color = chart_color_for_csv_token(format_cell(cell))
    evidence = replace(cell.provenance, rgb_color=CELL_LEGEND[color].rgb_color)
    return replace(cell, provenance=evidence)


def yards(value: int) -> NormalizedCell:
    return NormalizedCell(ResultKind.YARDS, provenance(), yards=value)


def team_chart(
    name: str,
    *,
    season: int = 2026,
    offense: int = 4,
    defense: int = 3,
    plays: dict[Play, NormalizedCell] | None = None,
) -> TeamChart:
    """A complete chart where every offense cell gains 'offense' and every defense 'defense'.

    'plays' replaces a whole offensive play column with one cell, so a test can force a
    specific outcome (for example an interception on play nine).
    """
    chart = complete_chart()
    plays = plays or {}
    return replace(
        chart,
        name=name,
        season=season,
        offense=tuple(
            OffensiveCell(
                r.play,
                r.roll,
                _with_legend_color(plays.get(r.play, yards(offense))),
            )
            for r in chart.offense
        ),
        supplemental=tuple(
            SupplementalCell(r.column, r.roll, yards(offense)) for r in chart.supplemental
        ),
        defense=tuple(
            DefensiveCell(r.defense, r.play, r.roll, yards(defense)) for r in chart.defense
        ),
    )


def metadata() -> TeamFileMetadata:
    return TeamFileMetadata(5.5, (), "Synthetic", SHA, (("rating", provenance()),))


def write_team(seasons_root: Path, chart: TeamChart) -> str:
    """Write one team in the on-disk layout and return its season/slug id."""
    slug = team_folder_name(chart.name)
    season_dir = seasons_root / str(chart.season)
    folder = season_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    (season_dir / "provenance").mkdir(parents=True, exist_ok=True)
    meta = metadata()
    for file_name, text in team_to_files(chart, meta).items():
        (folder / file_name).write_text(text, encoding="utf-8", newline="")
    (season_dir / "provenance" / (slug + ".csv")).write_text(
        provenance_to_csv(chart, meta), encoding="utf-8", newline=""
    )
    return str(chart.season) + "/" + slug


def default_teams() -> tuple[TeamChart, TeamChart]:
    """Home gains 4 on offense and 3 on defense; play nine is a forced interception."""
    interception = NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)
    return (
        team_chart(
            "Alpha Tech",
            offense=4,
            defense=3,
            plays={
                Play.NINE: interception,
                Play.EIGHT: NormalizedCell(
                    ResultKind.PENALTY,
                    provenance(),
                    penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8),
                ),
            },
        ),
        team_chart("Beta State", offense=5, defense=2),
    )
