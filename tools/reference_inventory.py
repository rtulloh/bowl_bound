"""Freeze explicit local reference inputs without making reference cells targets.

This development-only helper normalizes captured bytes through the standard CSV
codec. It verifies source-PDF identity, not a fresh PDF text/geometry import.
Detailed return values belong in ignored local evidence, never release data.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
)
from bowl_bound.team_csv import TEAM_FILES, team_folder_name, team_from_files


@dataclass(frozen=True)
class ReferenceInput:
    """An explicitly selected source; callers must supply all six frozen hashes."""

    season_dir: Path
    slug: str
    source_pdf: Path
    expected_sha256: tuple[tuple[str, str], ...]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value: Any, *, provenance: bool = True) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _json(asdict(value), provenance=provenance)
    if isinstance(value, dict):
        return {
            key: _json(item, provenance=provenance)
            for key, item in value.items()
            if provenance or key != "provenance"
        }
    if isinstance(value, (list, tuple, range)):
        return [_json(item, provenance=provenance) for item in value]
    return value


def _fingerprint(value: Any, *, provenance: bool = True) -> str:
    return _sha(
        json.dumps(
            _json(value, provenance=provenance),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    )


def physical_weights() -> tuple[dict[int, int], dict[int, int]]:
    """Count physical face combinations; these are not uniform chart addresses.

    A resolver benchmark must additionally retain individual faces for DS and
    shared-roll dependencies. These totals suffice for single-column inventories.
    """
    offense = Counter(
        10 * black + one + two
        for black, one, two in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    defense = Counter(red + green for red, green in product(RED_FACES, GREEN_FACES))
    return dict(sorted(offense.items())), dict(sorted(defense.items()))


def inventory_reference(source: ReferenceInput) -> dict[str, Any]:
    """Verify one immutable six-file reference and return its local inventory.

    Raises:
        ValueError: Inputs are incomplete, stale, symlinked, mismatched, or change
            while the captured chart bytes are being normalized.
    """
    names = (*TEAM_FILES, "provenance.csv", "source.pdf")
    if (
        type(source.expected_sha256) is not tuple
        or len(source.expected_sha256) != len(names)
        or {key for key, _ in source.expected_sha256} != set(names)
    ):
        raise ValueError("reference inventory requires exact six frozen input hashes")
    expected = dict(source.expected_sha256)
    if any(
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in expected.values()
    ):
        raise ValueError("frozen input hash must be lowercase SHA256")
    if team_folder_name(source.slug) != source.slug:
        raise ValueError("reference folder must be a canonical slug")
    paths = {name: source.season_dir / source.slug / name for name in TEAM_FILES}
    paths["provenance.csv"] = source.season_dir / "provenance" / f"{source.slug}.csv"
    paths["source.pdf"] = source.source_pdf
    if source.season_dir.is_symlink() or any(
        path.is_symlink() or path.parent.is_symlink() or not path.is_file()
        for path in paths.values()
    ):
        raise ValueError("reference input missing or symlinked")
    captured = {name: path.read_bytes() for name, path in paths.items()}
    actual = {name: _sha(data) for name, data in captured.items()}
    if actual != expected:
        raise ValueError("frozen input hash mismatch")
    chart, metadata = team_from_files(
        {name: captured[name].decode("utf-8") for name in TEAM_FILES},
        captured["provenance.csv"].decode("utf-8"),
    )
    if str(chart.season) != source.season_dir.name or team_folder_name(chart.name) != source.slug:
        raise ValueError("reference season or folder mismatch")
    rows = [
        row.cell.provenance
        for section in (chart.offense, chart.supplemental, chart.defense, chart.special_teams)
        for row in section
    ]
    rows.extend(row.provenance for row in chart.pat_outcomes)
    rows.extend(value for _, value in metadata.evidence)
    if metadata.source_sha256 != actual["source.pdf"] or any(
        value is None or value.source_sha256 != actual["source.pdf"] for value in rows
    ):
        raise ValueError("PDF provenance hash mismatch")
    filenames = {value.filename for value in rows if value is not None}
    if len(filenames) != 1:
        raise ValueError("PDF provenance filename mismatch")
    if any(_sha(path.read_bytes()) != actual[name] for name, path in paths.items()):
        raise ValueError("reference input changed during inventory")
    return {
        "schema_version": 1,
        "name": chart.name,
        "season": chart.season,
        "slug": source.slug,
        "input_sha256": actual,
        "input_paths": {name: str(path) for name, path in paths.items()},
        "counts": {
            name: len(getattr(chart, name))
            for name in ("offense", "supplemental", "defense", "special_teams", "pat_outcomes")
        },
        "provenance_records": len(rows),
        "source_filename": next(iter(filenames)),
        "pdf_binding_verified": True,
        "pdf_text_geometry_reimported": False,
        "full_chart_sha256": _fingerprint(chart),
        "semantic_chart_sha256": _fingerprint(chart, provenance=False),
        "metadata_sha256": _fingerprint(metadata),
        "power_rating_is_placeholder": metadata.power_rating_is_placeholder,
        "power_rating": metadata.power_rating,
        "defense_chart_markers": metadata.defense_chart_markers,
        "recovery_range": list(chart.recovery_range),
        "source_pages": sorted({value.page for value in rows if value is not None}),
    }
