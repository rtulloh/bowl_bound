"""The comparison matrix must include the legacy baseline and independent seeds."""

import pytest

from bowl_bound.coaching_audit import compare_policies
from bowl_bound.models import TeamChart


def test_default_comparison_includes_baseline_both_arrangements_and_sides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = []

    def audit(home: TeamChart, away: TeamChart, **kwargs: object) -> None:
        seen.append((home.name, away.name, kwargs))

    monkeypatch.setattr("bowl_bound.coaching_audit.audit_game", audit)
    compare_policies((101, 307))
    assert len(seen) == 32
    assert {entry[2]["policy"] for entry in seen} == {"baseline", "easy-v1", "medium-v1", "hard-v1"}
    assert {entry[2]["cpu_side"] for entry in seen} == {"home", "away"}
    assert len({(home, away) for home, away, _ in seen}) == 2
    assert len({entry[2]["coach_seed"] for entry in seen}) == 32
    assert len({entry[2]["stand_in_seed"] for entry in seen}) == 32
    first = list(seen)
    seen.clear()
    compare_policies((101, 307))
    assert seen == first
    assert all(entry[2]["coach_seed"] != entry[2]["seed"] for entry in seen)
