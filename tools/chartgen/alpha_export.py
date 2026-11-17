"""Standard runtime export with newly authored logical-cell source evidence.

Detailed input ancestry belongs in private producer receipts. This format uses
the existing installed CSV loader; no runtime decoder or rule changes are needed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, replace
from typing import Any

from bowl_bound.models import BoundingBox, Provenance, TeamChart
from bowl_bound.team_csv import (
    TeamFileMetadata,
    format_cell,
    provenance_to_csv,
    team_from_files,
    team_to_files,
)

from .alpha_event_risks import TOOL_VERSION, model_identity
from .research_inputs import semantic_sha256

TABLES = ("offense", "supplemental", "defense", "special_teams", "pat_outcomes")
VIRTUAL_FILENAME = "generated-bb-alpha-authored-v1.json"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _key(table: str, row: Any) -> tuple:
    if table == "offense":
        return row.play.value, row.roll
    if table == "defense":
        return row.defense.value, row.play.value, row.roll
    if table == "pat_outcomes":
        return (row.roll,)
    return row.column.value, row.roll


def football_facts_sha256(chart: TeamChart) -> str:
    """Hash all addressed football facts, independently of record order/evidence."""
    facts: dict[str, object] = {
        "schema_version": chart.schema_version,
        "name": chart.name,
        "season": chart.season,
        "recovery_range": tuple(chart.recovery_range),
    }
    for table in TABLES:
        records = []
        for row in sorted(getattr(chart, table), key=lambda r: _key(table, r)):
            value = asdict(row)
            del (value if table == "pat_outcomes" else value["cell"])["provenance"]
            records.append(value)
        facts[table] = records
    return semantic_sha256(facts)


def gameplay_metadata_sha256(metadata: TeamFileMetadata) -> str:
    """Hash rating/ordered markers/label/placeholder without old source claims."""
    return semantic_sha256(
        {
            "power_rating": float(metadata.power_rating),
            "markers": metadata.defense_chart_markers,
            "label": metadata.defense_label,
            "placeholder": metadata.power_rating_is_placeholder,
        }
    )


def encode_standard_alpha(
    chart: TeamChart,
    metadata: TeamFileMetadata,
    producer_receipt: Mapping[str, object],
    *,
    expected_baseline_sha256: str,
    source_sha256: str,
) -> tuple[dict[str, str], dict[str, object]]:
    """Export the original Alpha 9 model with its immutable identity."""
    return _encode_standard(
        chart,
        metadata,
        producer_receipt,
        expected_baseline_sha256=expected_baseline_sha256,
        source_sha256=source_sha256,
        compiled=model_identity(),
        tool_version=TOOL_VERSION,
    )


def encode_standard_cohort(
    chart: TeamChart,
    metadata: TeamFileMetadata,
    producer_receipt: Mapping[str, object],
    *,
    expected_baseline_sha256: str,
    source_sha256: str,
) -> tuple[dict[str, str], dict[str, object]]:
    """Export the explicitly versioned cohort extension using the ordinary codec."""
    from .cohort_model import TOOL_VERSION as cohort_version
    from .cohort_model import model_identity as cohort_identity

    return _encode_standard(
        chart,
        metadata,
        producer_receipt,
        expected_baseline_sha256=expected_baseline_sha256,
        source_sha256=source_sha256,
        compiled=cohort_identity(),
        tool_version=cohort_version,
    )


def _encode_standard(
    chart: TeamChart,
    metadata: TeamFileMetadata,
    producer_receipt: Mapping[str, object],
    *,
    expected_baseline_sha256: str,
    source_sha256: str,
    compiled: dict[str, object],
    tool_version: str,
) -> tuple[dict[str, str], dict[str, object]]:
    """Emit ordinary files only for an externally bound represented alpha output.

    The virtual source describes derived logical cells. It does not claim that
    their tokens/coordinates were printed in a historical PDF or independently
    observed in PBP. Returned full identities belong to the actual standard load.
    """
    for value in (expected_baseline_sha256, source_sha256):
        if (
            type(value) is not str
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("producer requires exact baseline and source identities")
    try:
        valid = (
            producer_receipt.get("status") == "represented"
            and _canonical(producer_receipt.get("model_identity")) == _canonical(compiled)
            and producer_receipt.get("baseline_sha256") == expected_baseline_sha256
            and producer_receipt.get("source_identity") == source_sha256
            and producer_receipt.get("output_sha256") == semantic_sha256(chart)
        )
    except (TypeError, ValueError) as error:
        raise ValueError("producer identity is not the compiled alpha contract") from error
    if not valid:
        raise ValueError(
            "producer status/model/output/baseline/source does not match frozen inputs"
        )
    original = semantic_sha256((chart, metadata))
    facts_hash, metadata_hash = football_facts_sha256(chart), gameplay_metadata_sha256(metadata)
    descriptor = {
        "schema_version": 1,
        "kind": "authored-logical-chart-cells",
        "model_sha256": compiled["sha256"],
        "source_sha256": source_sha256,
        "football_facts_sha256": facts_hash,
        "gameplay_metadata_sha256": metadata_hash,
        "coordinates": "table-page;addressed-column-and-row;emitted-token-and-RGB",
    }
    virtual_sha = _sha(_canonical(descriptor))

    def evidence(
        page: int, column: int, roll: int, token: str, rgb: tuple[int, int, int] | None
    ) -> Provenance:
        return Provenance(
            virtual_sha,
            VIRTUAL_FILENAME,
            page,
            BoundingBox(column, roll, column + 1, roll + 1),
            token,
            rgb,
        )

    changes = {}
    count = 0
    for page, table in enumerate(TABLES, 1):
        rows = []
        columns = sorted({_key(table, row)[:-1] for row in getattr(chart, table)})
        for row in getattr(chart, table):
            key = _key(table, row)
            prior = row.provenance if table == "pat_outcomes" else row.cell.provenance
            if prior is None:
                raise ValueError("standard alpha requires complete cell evidence")
            token = ("" if row.good else "NG") if table == "pat_outcomes" else format_cell(row.cell)
            source = evidence(page, columns.index(key[:-1]), key[-1], token, prior.rgb_color)
            rows.append(
                replace(row, provenance=source)
                if table == "pat_outcomes"
                else replace(row, cell=replace(row.cell, provenance=source))
            )
            count += 1
        changes[table] = tuple(rows)
    if count != 840:
        raise ValueError("standard alpha requires exactly840 addressed records")
    authored = replace(chart, **changes)
    authored_meta = replace(
        metadata,
        source_sha256=virtual_sha,
        evidence=tuple(
            (name, evidence(6, i, 0, text, None))
            for i, (name, text) in enumerate(
                (
                    ("rating", str(float(metadata.power_rating))),
                    ("markers", ",".join(metadata.defense_chart_markers)),
                    ("label", metadata.defense_label),
                    ("placeholder", str(metadata.power_rating_is_placeholder).lower()),
                )
            )
        ),
    )
    files = team_to_files(authored, authored_meta)
    files["team.yaml"] = (
        "# Experimental generated alpha; authored logical source evidence\n"
        + files["team.yaml"].split("\n", 1)[1]
    )
    provenance = provenance_to_csv(authored, authored_meta)
    loaded, actual_meta = team_from_files(files, provenance)
    if (
        football_facts_sha256(loaded) != facts_hash
        or gameplay_metadata_sha256(actual_meta) != metadata_hash
    ):
        raise ValueError("standard alpha roundtrip changed football facts or gameplay metadata")
    if semantic_sha256((chart, metadata)) != original:
        raise ValueError("standard alpha inputs changed during encoding")
    files["provenance.csv"] = provenance
    return files, {
        "schema_version": 1,
        "model_identity": compiled,
        "tool_version": tool_version,
        "virtual_source_descriptor": descriptor,
        "virtual_source_sha256": virtual_sha,
        "coordinate_count": count,
        "football_facts_sha256": facts_hash,
        "gameplay_metadata_sha256": metadata_hash,
        "loaded_chart_sha256": semantic_sha256(loaded),
        "loaded_metadata_sha256": semantic_sha256(actual_meta),
        "file_sha256": {name: _sha(text) for name, text in files.items()},
    }
