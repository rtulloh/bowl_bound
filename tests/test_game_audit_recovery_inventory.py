"""Explicit source-pinned recovery metadata is distinct from missing evidence."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict

import pytest

from tests.test_game_audit_row_links import frozen_inventory
from tools.game_audit_lookup import LookupEvidenceError, LookupInventory


def bind_synthetic_inputs(value: dict, teams: tuple) -> dict:
    """Pin literal fixture inputs, never report/credit-derived outcome facts."""
    value = deepcopy(value)
    value["version"] = "2"
    for metadata, chart in zip(value["teams"], teams, strict=True):
        raw = asdict(chart)
        raw["recovery_range"] = list(chart.recovery_range)

        def digest(data: dict) -> str:
            return hashlib.sha256(
                json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest()

        object_sha = digest(raw)
        for table in ("offense", "defense", "supplemental", "special_teams"):
            for record in raw[table]:
                record["cell"].pop("chart_color", None)
        metadata.update(
            fingerprint=digest(raw),
            object_sha256=object_sha,
            metadata_sha256=digest({"season": chart.season, "range": raw["recovery_range"]}),
            recovery_range=[chart.recovery_range.start, chart.recovery_range.stop - 1],
        )
    return value


def recovery_inventory() -> dict:
    value = frozen_inventory()
    value["version"] = "2"
    for team in value["teams"]:
        team.update(
            fingerprint="a" * 64,
            object_sha256="b" * 64,
            metadata_sha256="c" * 64,
            recovery_range=[10, 19],
        )
    return value


def test_version_one_does_not_invent_a_recovery_interval() -> None:
    inventory = LookupInventory(frozen_inventory())
    assert inventory.recovery_interval("2002/home", "a" * 64) is None


def test_version_two_binds_the_inclusive_range_to_team_and_fingerprint() -> None:
    inventory = LookupInventory(recovery_inventory())
    assert inventory.recovery_interval("2002/home", "a" * 64) == (10, 19)
    assert inventory.recovery_interval("2002/absent", "a" * 64) is None
    with pytest.raises(LookupEvidenceError, match="fingerprint"):
        inventory.recovery_interval("2002/home", "d" * 64)


@pytest.mark.parametrize(
    "interval", [[True, 19], [10, False], [9, 19], [10, 40], [20, 10], [10], [], None, "10..19"]
)
def test_invalid_recovery_ranges_refuse(interval) -> None:
    value = recovery_inventory()
    value["teams"][0]["recovery_range"] = interval
    with pytest.raises(LookupEvidenceError, match="recovery interval"):
        LookupInventory(value)


@pytest.mark.parametrize("key", ["fingerprint", "object_sha256", "metadata_sha256"])
@pytest.mark.parametrize("invalid", [None, True, "x" * 64, "a" * 63])
def test_recovery_metadata_requires_explicit_sha256_bindings(key, invalid) -> None:
    value = deepcopy(recovery_inventory())
    value["teams"][0][key] = invalid
    with pytest.raises(LookupEvidenceError, match="metadata SHA"):
        LookupInventory(value)


def test_detached_inventory_retains_reviewed_range_after_caller_mutation() -> None:
    value = recovery_inventory()
    inventory = LookupInventory(value)
    value["teams"][0]["recovery_range"][:] = [20, 39]
    assert inventory.recovery_interval("2002/home", "a" * 64) == (10, 19)
