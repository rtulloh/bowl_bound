"""Comparable-call audit buckets are explicit, reproducible public situations."""

from dataclasses import replace

import pytest

from bowl_bound.coaching_audit import CallAudit
from tests.test_coaching import observation


def test_minor_clock_and_field_changes_remain_comparable() -> None:
    audit = CallAudit()
    first = replace(observation(), yards_to_goal=65, remaining=650, distance=8)
    audit.record(first, "offense", "1", fallback=False)
    audit.record(
        replace(first, yards_to_goal=61, remaining=620, distance=10), "offense", "1", fallback=False
    )
    assert audit.comparable_calls == audit.repeated_calls == 1


@pytest.mark.parametrize(
    "change",
    [
        {"down": 3},
        {"distance": 2},
        {"yards_to_goal": 10},
        {"remaining": 110},
        {"score_difference": -14},
        {"hurried": True},
        {"offense": ("1",)},
        {"side": "away"},
    ],
)
def test_material_situations_and_legal_menus_are_not_pooled(change: dict[str, object]) -> None:
    audit = CallAudit()
    first = replace(observation(), down=1, distance=10, yards_to_goal=65, remaining=650)
    audit.record(first, "offense", "1", fallback=False)
    audit.record(replace(first, **change), "offense", "1", fallback=False)
    assert audit.comparable_calls == audit.repeated_calls == 0
