"""Private complete-report storage with deterministic compression and capacity checks."""

from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import tempfile
import zlib
from enum import Enum
from pathlib import Path
from typing import Any


class ArtifactCompression(str, Enum):
    JSON = "json"
    GZIP = "gzip"


class StorageCapacityError(ValueError):
    """The declared retained-artifact budget would consume reserved disk space."""


def storage_policy(compression: ArtifactCompression) -> dict[str, Any]:
    """Conservative engineering estimates, renewed against measured pilot outputs."""
    compression = ArtifactCompression(compression)
    return {
        "compression": compression.value,
        "gzip_level": 6 if compression == ArtifactCompression.GZIP else None,
        "gzip_mtime": 0 if compression == ArtifactCompression.GZIP else None,
        "estimated_bytes_per_game": 256 * 1024
        if compression == ArtifactCompression.GZIP
        else 4 * 1024**2,
        "metadata_allowance_bytes": 64 * 1024**2,
        "reserve_bytes": 3 * 1024**3,
        "estimate_limit": (
            "pre-run estimate, not a report truncation limit; measure actual pilot bytes"
        ),
    }


def check_capacity(
    destination: Path,
    game_reports: int,
    *,
    compression: ArtifactCompression = ArtifactCompression.JSON,
) -> dict[str, Any]:
    """Reject a missing-report budget before engine work or destination creation.

    A fully retained resume may still be read and checked with zero missing
    reports. Changing free space is evidence, never part of deterministic seeds
    or the immutable source/profile contract.
    """
    if type(game_reports) is not int or game_reports < 0:
        raise ValueError("storage game-report count must be a nonnegative integer")
    policy = storage_policy(compression)
    existing = destination
    while not existing.exists():
        existing = existing.parent
    available = shutil.disk_usage(existing).free
    estimated = (
        game_reports * policy["estimated_bytes_per_game"] + policy["metadata_allowance_bytes"]
        if game_reports
        else 0
    )
    required = estimated + policy["reserve_bytes"] if game_reports else 0
    if available < required:
        raise StorageCapacityError(
            f"insufficient storage: {game_reports} complete {policy['compression']} reports "
            f"need an estimated {estimated} bytes plus {policy['reserve_bytes']} reserved bytes; "
            f"{available} bytes available. "
            "Use a smaller declared run or another private destination."
        )
    return {
        **policy,
        "requested_game_reports": game_reports,
        "estimated_artifact_bytes": estimated,
        "available_bytes": available,
        "required_bytes_including_reserve": required,
    }


def game_artifact_path(output: Path, number: int, compression: ArtifactCompression) -> Path:
    suffix = ".json.gz" if ArtifactCompression(compression) == ArtifactCompression.GZIP else ".json"
    return output / f"game-{number:06d}{suffix}"


def write_artifact(
    path: Path,
    payload: Any,
    *,
    compression: ArtifactCompression = ArtifactCompression.JSON,
) -> None:
    """Stream all JSON facts, then atomically publish without overwriting evidence."""
    compression = ArtifactCompression(compression)
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    pending = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            encoded = (
                gzip.GzipFile(filename="", mode="wb", compresslevel=6, fileobj=raw, mtime=0)
                if compression == ArtifactCompression.GZIP
                else raw
            )
            stream = io.TextIOWrapper(encoded, encoding="utf-8", newline="\n")
            try:
                json.dump(payload, stream, sort_keys=True, allow_nan=False)
                stream.write("\n")
                stream.flush()
            finally:
                stream.detach()
                if encoded is not raw:
                    encoded.close()
            raw.flush()
            os.fsync(raw.fileno())
        os.link(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def read_artifact(path: Path) -> Any:
    """Read legacy JSON or complete gzip JSON; retain corrupt inputs for diagnosis."""
    try:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    except (json.JSONDecodeError, UnicodeError, EOFError, gzip.BadGzipFile, zlib.error) as error:
        raise ValueError(f"corrupt or incomplete retained artifact: {path.name}") from error
