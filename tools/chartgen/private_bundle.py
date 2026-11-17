"""Opt-in mixed-ancestry transport for reviewed private charts, never a release format.

Canonical CSV remains authoritative for normalized football facts. The separate
ledger restores only provenance/order and must reproduce an externally pinned
complete TeamChart and gameplay-metadata identity. Hashes attest supplied bytes,
not source truth, historical accuracy or approval to publish.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any, cast

from bowl_bound.models import BoundingBox, Provenance, TeamChart
from bowl_bound.team_csv import (
    TEAM_FILES,
    TeamFileMetadata,
    format_cell,
    provenance_to_csv,
    team_from_files,
    team_to_files,
)

from .balanced_event_risks import model_identity as balanced_model_identity
from .coupled_event_risks import model_identity as coupled_model_identity
from .research_inputs import semantic_sha256
from .typed_event_risks import model_identity

TABLES = ("offense", "supplemental", "defense", "special_teams", "pat_outcomes")
FILES = frozenset((*TEAM_FILES, "provenance.csv", "ancestry.json"))
_PROVENANCE_FIELDS = frozenset(Provenance.__dataclass_fields__)
_META_FIELDS = frozenset(TeamFileMetadata.__dataclass_fields__)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gameplay_metadata_sha256(meta: TeamFileMetadata) -> str:
    """Bind every gameplay metadata fact while source/container evidence differs."""
    if type(meta) is not TeamFileMetadata:
        raise ValueError("private bundle requires complete typed gameplay metadata")
    return semantic_sha256(
        {
            "power_rating": meta.power_rating,
            "defense_chart_markers": meta.defense_chart_markers,
            "defense_label": meta.defense_label,
            "power_rating_is_placeholder": meta.power_rating_is_placeholder,
        }
    )


def _key(table: str, row: Any) -> tuple:
    if table == "offense":
        return (row.play.value, row.roll)
    if table == "defense":
        return (row.defense.value, row.play.value, row.roll)
    if table == "pat_outcomes":
        return (row.roll,)
    return (row.column.value, row.roll)


def _provenance(value: object) -> Provenance:
    if type(value) is not dict or set(value) != _PROVENANCE_FIELDS:
        raise ValueError("private ancestry has invalid provenance fields")
    box = value["bounding_box"]
    if type(box) is not dict or set(box) != set(BoundingBox.__dataclass_fields__):
        raise ValueError("private ancestry has invalid logical/source coordinates")
    rgb = value["rgb_color"]
    if rgb is not None and type(rgb) is not list:
        raise ValueError("private ancestry has invalid RGB evidence")
    try:
        return Provenance(
            **(
                value
                | {
                    "bounding_box": BoundingBox(**box),
                    "rgb_color": tuple(rgb) if rgb is not None else None,
                }
            )
        )
    except (TypeError, ValueError) as error:
        raise ValueError("private ancestry has invalid typed finite provenance") from error


def _metadata(value: object) -> TeamFileMetadata:
    if type(value) is not dict or set(value) != _META_FIELDS:
        raise ValueError("private ancestry has invalid metadata fields")
    if type(value["defense_chart_markers"]) is not list or type(value["evidence"]) is not list:
        raise ValueError("private ancestry has invalid metadata collections")
    evidence = []
    for item in value["evidence"]:
        if type(item) is not list or len(item) != 2 or type(item[0]) is not str:
            raise ValueError("private ancestry has invalid metadata evidence")
        evidence.append((item[0], _provenance(item[1])))
    try:
        data = cast(dict[str, Any], value)
        return TeamFileMetadata(
            power_rating=data["power_rating"],
            defense_chart_markers=tuple(data["defense_chart_markers"]),
            defense_label=data["defense_label"],
            source_sha256=data["source_sha256"],
            evidence=tuple(evidence),
            power_rating_is_placeholder=data["power_rating_is_placeholder"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("private ancestry has invalid gameplay metadata") from error


def _model(value: object, expected: str) -> dict[str, Any]:
    admitted = (model_identity(), coupled_model_identity(), balanced_model_identity())
    if type(value) is not dict:
        raise ValueError("private bundle model must be a complete compiled identity")
    try:
        matched = any(_canonical(value) == _canonical(known) for known in admitted)
    except (TypeError, ValueError) as error:
        raise ValueError("private bundle model has invalid typed contract facts") from error
    if not matched or value.get("sha256") != expected:
        raise ValueError("private bundle model differs from the frozen authored model")
    return value


def _ledger(chart: TeamChart) -> list[dict[str, Any]]:
    return [
        {
            "table": table,
            "coordinate": _key(table, row),
            "provenance": asdict(
                row.provenance if table == "pat_outcomes" else row.cell.provenance
            ),
        }
        for table in TABLES
        for row in getattr(chart, table)
    ]


def _restore(chart: TeamChart, records: object) -> TeamChart:
    """Restore ancestry/order only; never replace normalized football facts."""
    if type(records) is not list or len(records) != 840:
        raise ValueError("private ancestry requires the exact840 coordinate inventory")
    inventory = {
        semantic_sha256((table, _key(table, row))): (table, row)
        for table in TABLES
        for row in getattr(chart, table)
    }
    seen = set()
    restored: dict[str, list[Any]] = {table: [] for table in TABLES}
    for record in records:
        if type(record) is not dict or set(record) != {"table", "coordinate", "provenance"}:
            raise ValueError("private ancestry requires exact record fields")
        key = record["coordinate"]
        if type(key) is not list or any(type(part) not in {str, int} for part in key):
            raise ValueError("private ancestry has an invalid coordinate")
        identity = semantic_sha256((record["table"], tuple(key)))
        if identity in seen or identity not in inventory:
            raise ValueError("private ancestry coordinate inventory is not a bijection")
        seen.add(identity)
        table, row = inventory[identity]
        provenance = _provenance(record["provenance"])
        restored[table].append(
            replace(row, provenance=provenance)
            if table == "pat_outcomes"
            else replace(row, cell=replace(row.cell, provenance=provenance))
        )
    if seen != set(inventory):
        raise ValueError("private ancestry coordinate inventory is incomplete")
    return replace(chart, **{table: tuple(rows) for table, rows in restored.items()})


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("private ancestry contains duplicate JSON keys")
        result[key] = value
    return result


def decode_private_bundle(
    files: dict[str, str],
    *,
    expected_file_hashes: dict[str, str],
    expected_output_sha256: str,
    expected_model_sha256: str,
    expected_gameplay_metadata_sha256: str,
) -> tuple[TeamChart, TeamFileMetadata]:
    """Load exact reviewed bytes; the expected identities are external authority.

    The private launcher must freeze them separately from this container. This
    function proves consistency, never that caller-supplied expectations deserve
    historical/source qualification. No model is regenerated during loading.
    """
    if (
        type(files) is not dict
        or set(files) != FILES
        or type(expected_file_hashes) is not dict
        or set(expected_file_hashes) != FILES
    ):
        raise ValueError("private bundle requires exact six-file inventory")
    if any(type(value) is not str for value in files.values()):
        raise ValueError("private bundle requires canonical text snapshots")
    before = semantic_sha256((files, expected_file_hashes))
    snapshot, hashes = dict(files), dict(expected_file_hashes)
    if any(_hash(text) != hashes[name] for name, text in snapshot.items()):
        raise ValueError("private bundle input hash differs from frozen launch inputs")
    try:
        ledger = json.loads(snapshot["ancestry.json"], object_pairs_hook=_no_duplicates)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("private ancestry is not valid canonical JSON") from error
    if (
        type(ledger) is not dict
        or set(ledger)
        != {
            "schema_version",
            "scope",
            "model_identity",
            "producer_receipt",
            "output_sha256",
            "gameplay_metadata_sha256",
            "original_metadata",
            "records",
        }
        or type(ledger["schema_version"]) is not int
        or ledger["schema_version"] != 1
        or ledger["scope"] != "PRIVATE_EXPERIMENT_NOT_RELEASE_OR_SOURCE_QUALIFICATION"
    ):
        raise ValueError("private ancestry schema or scope is unsupported")
    if _canonical(ledger) != snapshot["ancestry.json"]:
        raise ValueError("private ancestry snapshot bytes are not canonical")
    _model(ledger["model_identity"], expected_model_sha256)
    producer = ledger["producer_receipt"]
    if type(producer) is not dict or producer.get("output_sha256") != ledger["output_sha256"]:
        raise ValueError("private producer receipt output disagrees with the ancestry header")
    if producer.get("model_identity") != ledger["model_identity"]:
        raise ValueError("private producer receipt model disagrees with the ancestry header")
    if ledger["output_sha256"] != expected_output_sha256:
        raise ValueError("private bundle output differs from frozen reviewed object")
    original_metadata = _metadata(ledger["original_metadata"])
    if (
        gameplay_metadata_sha256(original_metadata) != expected_gameplay_metadata_sha256
        or ledger["gameplay_metadata_sha256"] != expected_gameplay_metadata_sha256
    ):
        raise ValueError("private bundle gameplay metadata differs from frozen input")
    chart, meta = team_from_files(
        {name: snapshot[name] for name in TEAM_FILES}, snapshot["provenance.csv"]
    )
    if meta.source_sha256 != _hash(snapshot["ancestry.json"]):
        raise ValueError("private container source hash does not identify the ancestry snapshot")
    if gameplay_metadata_sha256(meta) != expected_gameplay_metadata_sha256:
        raise ValueError("private CSV gameplay metadata differs from frozen input")
    restored = _restore(chart, ledger["records"])
    if semantic_sha256(restored) != expected_output_sha256:
        raise ValueError("private bundle output semantic roundtrip differs from frozen object")
    if before != semantic_sha256((files, expected_file_hashes)):
        raise ValueError("private bundle original inputs changed during decoding")
    return restored, meta


def encode_private_bundle(
    chart: TeamChart, metadata: TeamFileMetadata, producer_receipt: dict[str, Any]
) -> dict[str, str]:
    """Encode a reviewed typed result without relabeling derived cells as raw.

    CSV uses a separately authored immutable container source. The sidecar carries
    the exact original/derived ancestry. A failed complete roundtrip refuses the
    supplied chart; it is never normalized opportunistically into different facts.
    """
    original_inputs = (chart, metadata, producer_receipt)
    before = semantic_sha256(original_inputs)
    chart, metadata, receipt = deepcopy((chart, metadata, producer_receipt))
    if receipt.get("output_sha256") != semantic_sha256(chart):
        raise ValueError("private producer receipt output differs from supplied chart")
    supplied_identity = receipt.get("model_identity")
    selected = supplied_identity.get("sha256") if type(supplied_identity) is dict else None
    if type(selected) is not str:
        raise ValueError("private model identity requires an exact hash")
    identity = _model(receipt.get("model_identity"), selected)
    ledger = {
        "schema_version": 1,
        "scope": "PRIVATE_EXPERIMENT_NOT_RELEASE_OR_SOURCE_QUALIFICATION",
        "model_identity": identity,
        "producer_receipt": receipt,
        "output_sha256": semantic_sha256(chart),
        "gameplay_metadata_sha256": gameplay_metadata_sha256(metadata),
        "original_metadata": asdict(metadata),
        "records": _ledger(chart),
    }
    text = _canonical(ledger)
    container = _hash(text)

    def transport_provenance(p: Provenance, page: int, index: int, token: str) -> Provenance:
        return replace(
            p,
            source_sha256=container,
            filename="ancestry.json",
            page=page,
            bounding_box=BoundingBox(0, index, 1, index + 1),
            original_text=token,
        )

    uniform = {}
    for page, table in enumerate(TABLES, 1):
        uniform[table] = tuple(
            replace(
                row,
                provenance=transport_provenance(
                    row.provenance, page, index, "" if row.good else "NG"
                ),
            )
            if table == "pat_outcomes"
            else replace(
                row,
                cell=replace(
                    row.cell,
                    provenance=transport_provenance(
                        row.cell.provenance, page, index, format_cell(row.cell)
                    ),
                ),
            )
            for index, row in enumerate(getattr(chart, table))
        )
    transport_chart = replace(chart, **uniform)
    transport_meta = replace(
        metadata,
        source_sha256=container,
        evidence=tuple(
            (label, transport_provenance(p, 6, index, p.original_text))
            for index, (label, p) in enumerate(metadata.evidence)
        ),
    )
    files = team_to_files(transport_chart, transport_meta)
    files["provenance.csv"] = provenance_to_csv(transport_chart, transport_meta)
    files["ancestry.json"] = text
    decode_private_bundle(
        files,
        expected_file_hashes={name: _hash(value) for name, value in files.items()},
        expected_output_sha256=ledger["output_sha256"],
        expected_model_sha256=identity["sha256"],
        expected_gameplay_metadata_sha256=ledger["gameplay_metadata_sha256"],
    )
    # Verify caller facts as well as the detached values. No callbacks receive the snapshot.
    if before != semantic_sha256(original_inputs) or before != semantic_sha256(
        (chart, metadata, receipt)
    ):
        raise ValueError("private bundle inputs changed during encoding")
    return files
