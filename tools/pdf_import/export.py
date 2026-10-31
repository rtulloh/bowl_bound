"""Validated team assembly and versioned document export, without gameplay rules."""

import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from bowl_bound.models import (
    Defense,
    DefensiveCell,
    OffensiveCell,
    PatOutcome,
    Play,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.normalization import (
    CELL_LEGEND,
    CONVERTED_CMYK_PALETTE,
    ChartColor,
    NormalizationError,
    normalize_cell,
)
from bowl_bound.team_csv import TeamFileMetadata

from .cells import ExtractedCell, extract_cells
from .errors import ImportValidationError
from .inspection import inspect_document
from .layout import CellPosition, locate_cells
from .metadata import TeamMetadata, extract_metadata
from .page_view import rotate_portrait_page


@dataclass(frozen=True)
class ExportedTeam:
    """A validated chart with the metadata that is written beside it."""

    chart: TeamChart
    metadata: TeamFileMetadata


_COLORS = {
    legend.rgb_color: color for color, legend in CELL_LEGEND.items()
} | CONVERTED_CMYK_PALETTE


def build_team(
    name: str,
    season: int,
    records: list[tuple[CellPosition, ExtractedCell]],
    metadata: TeamMetadata,
) -> TeamChart:
    """Normalize and validate every address; PAT uses its own dice-column background.

    Only document problems become ``ImportValidationError``. A malformed ``CellPosition``
    is a programming error and propagates unchanged.
    """
    offense, supplemental, defense, special, pats = [], [], [], [], []
    for position, raw in records:
        if raw.rotation != 0:
            raise ImportValidationError("Chart cells must contain upright text")
        if position.section == "pat":
            if raw.text.strip() != str(position.roll):
                raise ImportValidationError("PAT source text must match the printed roll")
            pat_color = _COLORS.get(raw.rgb_color)
            if pat_color not in {ChartColor.RED, ChartColor.WHITE}:
                raise ImportValidationError("PAT background must be red or white")
            pats.append(
                PatOutcome(
                    position.roll,
                    pat_color is ChartColor.WHITE,
                    raw.provenance,
                )
            )
            continue
        color = _COLORS.get(raw.rgb_color)
        if color is None:
            raise ImportValidationError("Unknown chart background; no color guessing allowed")
        try:
            cell = normalize_cell(raw.provenance, color)
        except NormalizationError as error:
            raise ImportValidationError("chart cell data is invalid") from error
        if position.section == "offense":
            offense.append(OffensiveCell(Play(int(position.column)), position.roll, cell))
        elif position.section == "supplemental":
            supplemental.append(
                SupplementalCell(SupplementalColumn(position.column), position.roll, cell)
            )
        elif position.section == "defense":
            defense.append(
                DefensiveCell(
                    Defense(position.defense), Play(int(position.column)), position.roll, cell
                )
            )
        elif position.section == "special_teams":
            special.append(
                SpecialTeamsCell(SpecialTeamsColumn(position.column), position.roll, cell)
            )
        else:
            raise ImportValidationError("Unknown chart section")
    try:
        return TeamChart(
            1,
            name,
            season,
            # Canonical order, identical to the CSV reader, so equal charts compare equal.
            tuple(sorted(offense, key=lambda x: (x.play.value, x.roll))),
            tuple(sorted(supplemental, key=lambda x: (x.column.value, x.roll))),
            tuple(sorted(defense, key=lambda x: (x.defense.value, x.play.value, x.roll))),
            tuple(
                sorted(special, key=lambda x: (list(SpecialTeamsColumn).index(x.column), x.roll))
            ),
            tuple(sorted(pats, key=lambda x: x.roll)),
            metadata.recovery_range,
        )
    except (ValueError, TypeError) as error:
        raise ImportValidationError("chart is incomplete or inconsistent") from error


def export_document(
    source: Path, *, use_local_rating_placeholder: bool = False
) -> list[ExportedTeam]:
    """Return validated teams in document order; the caller controls writing or dry-run."""
    inspection = inspect_document(source)
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != inspection.source_sha256:
        raise ImportValidationError("Source PDF changed after inspection")
    import pdfplumber

    teams: list[ExportedTeam] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for offense_info, defense_info in zip(
            inspection.pages[::2], inspection.pages[1::2], strict=True
        ):
            offense_page = pdf.pages[offense_info.page - 1]
            defense_page = pdf.pages[defense_info.page - 1]
            if offense_info.rotation == 90:
                offense_page = rotate_portrait_page(offense_page)
            if defense_info.rotation == 90:
                defense_page = rotate_portrait_page(defense_page)
            metadata = extract_metadata(
                offense_page,
                defense_page,
                inspection.source_sha256,
                source.name,
                offense_info.page,
                use_local_rating_placeholder=use_local_rating_placeholder,
            )
            records = []
            for info in (offense_info, defense_info):
                page = pdf.pages[info.page - 1]
                if info.rotation == 90:
                    page = rotate_portrait_page(page)
                positions = locate_cells(page, info.role)
                cells = extract_cells(
                    page,
                    tuple(pos.bounds for pos in positions),
                    source_sha256=inspection.source_sha256,
                    filename=source.name,
                    page_number=info.page,
                )
                records.extend(zip(positions, cells, strict=True))
            chart = build_team(offense_info.team_name, offense_info.season, records, metadata)
            teams.append(
                ExportedTeam(
                    chart,
                    TeamFileMetadata(
                        metadata.power_rating,
                        metadata.privileges,
                        defense_info.team_name,
                        inspection.source_sha256,
                        tuple((fact.label, fact.provenance) for fact in metadata.evidence),
                        metadata.power_rating_is_placeholder,
                    ),
                )
            )
    return teams
