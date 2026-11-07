"""Ordinary CSV export of authored call-depth candidates and logical provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from enum import Enum
from typing import Any

from bowl_bound.models import BoundingBox, Provenance, TeamChart
from bowl_bound.team_csv import (
    TeamFileMetadata,
    format_cell,
    provenance_to_csv,
    team_from_files,
    team_to_files,
)

from .chart_depth_policy import execution_identity

TABLES = ("offense", "supplemental", "defense", "special_teams", "pat_outcomes")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=lambda item: item.value if isinstance(item, Enum) else str(item),
        ).encode()
    ).hexdigest()


def chart_facts(chart: TeamChart) -> dict[str, Any]:
    """Return every football fact with provenance removed."""
    facts = asdict(chart)
    for table in TABLES:
        for row in facts[table]:
            (row if table == "pat_outcomes" else row["cell"]).pop("provenance")
    return facts


def encode_depth_candidate(
    chart: TeamChart,
    metadata: TeamFileMetadata,
    *,
    source_sha256: str,
    baseline_sha256: str,
    model_identity: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Rebase all 840 cells to a new synthetic source container and reload them."""
    try:
        expected_identity = execution_identity(
            model_identity["contract"]["prior_equivalent_observations"]
        )
        valid_identity = (
            model_identity["sha256"] == expected_identity["sha256"]
            and model_identity["origin"] == expected_identity["origin"]
            and model_identity["authored_experimental"] is True
            and _digest(model_identity["contract"]) == expected_identity["sha256"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("export requires a valid effective model identity") from error
    if not valid_identity:
        raise ValueError("export requires a valid effective model identity")
    for value in (source_sha256, baseline_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("export requires frozen source and baseline SHA256 identities")
    meta_facts = {
        "power_rating": metadata.power_rating,
        "markers": metadata.defense_chart_markers,
        "label": metadata.defense_label,
        "placeholder": metadata.power_rating_is_placeholder,
    }
    descriptor = {
        "schema_version": 1,
        "kind": "authored-logical-chart-cells",
        "model_sha256": expected_identity["sha256"],
        "source_sha256": source_sha256,
        "baseline_sha256": baseline_sha256,
        "football_facts_sha256": _digest(chart_facts(chart)),
        "gameplay_metadata_sha256": _digest(meta_facts),
        "coordinates": "table-page;addressed-column-and-row;emitted-token-and-RGB",
    }
    virtual_sha = _digest(descriptor)
    filename = "generated-bb-call-depth-v1.json"

    def key(table: str, row: Any) -> tuple:
        if table == "offense":
            return row.play.value, row.roll
        if table == "defense":
            return row.defense.value, row.play.value, row.roll
        if table == "pat_outcomes":
            return (row.roll,)
        return row.column.value, row.roll

    def evidence(page: int, column: int, roll: int, token: str, rgb: Any) -> Provenance:
        return Provenance(
            virtual_sha, filename, page, BoundingBox(column, roll, column + 1, roll + 1), token, rgb
        )

    changes = {}
    for page, table in enumerate(TABLES, 1):
        columns = sorted({key(table, row)[:-1] for row in getattr(chart, table)})
        rows = []
        for row in getattr(chart, table):
            prior = row.provenance if table == "pat_outcomes" else row.cell.provenance
            if prior is None:
                raise ValueError("export requires complete input provenance")
            address = key(table, row)
            token = ("" if row.good else "NG") if table == "pat_outcomes" else format_cell(row.cell)
            source = evidence(
                page, columns.index(address[:-1]), address[-1], token, prior.rgb_color
            )
            rows.append(
                replace(row, provenance=source)
                if table == "pat_outcomes"
                else replace(row, cell=replace(row.cell, provenance=source))
            )
        changes[table] = tuple(rows)
    authored = replace(chart, **changes)
    logical_meta = tuple(
        (name, text)
        for name, text in (
            ("rating", str(float(metadata.power_rating))),
            ("markers", ",".join(metadata.defense_chart_markers)),
            ("label", metadata.defense_label),
            ("placeholder", str(metadata.power_rating_is_placeholder).lower()),
        )
    )
    authored_meta = replace(
        metadata,
        source_sha256=virtual_sha,
        evidence=tuple(
            (name, evidence(6, index, 0, text, None))
            for index, (name, text) in enumerate(logical_meta)
        ),
    )
    files = team_to_files(authored, authored_meta)
    provenance_csv = provenance_to_csv(authored, authored_meta)
    loaded, actual_meta = team_from_files(files, provenance_csv)
    if chart_facts(loaded) != chart_facts(chart):
        raise ValueError("ordinary CSV roundtrip changed football facts")
    if (
        actual_meta.power_rating,
        actual_meta.defense_chart_markers,
        actual_meta.defense_label,
        actual_meta.power_rating_is_placeholder,
    ) != (
        metadata.power_rating,
        metadata.defense_chart_markers,
        metadata.defense_label,
        metadata.power_rating_is_placeholder,
    ):
        raise ValueError("ordinary CSV roundtrip changed gameplay metadata")
    files["provenance.csv"] = provenance_csv
    return files, {
        "model_identity": expected_identity,
        "virtual_source_descriptor": descriptor,
        "virtual_source_sha256": virtual_sha,
        "football_facts_sha256": _digest(chart_facts(loaded)),
        "file_sha256": {
            name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()
        },
    }
