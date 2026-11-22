"""Select one disjoint CI shard while keeping tests with shared state together."""

import hashlib
import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Select the same shard independently on each xdist worker."""
    index = int(os.environ["BB_TEST_SHARD"])
    count = int(os.environ["BB_TEST_SHARDS"])
    if not 0 <= index < count:
        raise pytest.UsageError("BB_TEST_SHARD must be between zero and BB_TEST_SHARDS minus one")

    selected = []
    deselected = []
    for item in items:
        groups = sorted(marker.args[0] for marker in item.iter_markers("xdist_group"))
        key = "|".join(groups) if groups else item.nodeid
        digest = hashlib.sha256(key.encode()).digest()
        bucket = int.from_bytes(digest[:8], "big") % count
        (selected if bucket == index else deselected).append(item)
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected
