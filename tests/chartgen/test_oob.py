"""Synthetic OOB evidence denominators; no historical source inputs."""

from dataclasses import replace

import pytest

from tools.chartgen.empirical import WeightedObservation
from tools.chartgen.evidence import Event, classify_espn
from tools.chartgen.generate import _out_of_bounds_evidence


def observation(bounds: bool | None, weight: float) -> WeightedObservation:
    return WeightedObservation(
        Event(2007, "g", str(weight), "1", "2", "Cedar", "Harbor", "rush", 4, out_of_bounds=bounds),
        weight,
    )


@pytest.mark.parametrize(
    "records,requested,state",
    [
        ([observation(True, 1), observation(None, 99)], 0.01, "partial-positive-evidence"),
        ([observation(True, 1), observation(False, 3)], 0.25, "complete-explicit-evidence"),
        (
            [observation(True, 1), observation(False, 3), observation(None, 6)],
            0.1,
            "partial-positive-evidence",
        ),
        ([observation(None, 8)], 0.0, "unidentified"),
        ([], 0.0, "dormant"),
    ],
)
def test_oob_evidence_preserves_unknowns_and_weights(
    records: list[WeightedObservation], requested: float, state: str
) -> None:
    before = [record.event.to_dict() for record in records]
    rate, report = _out_of_bounds_evidence(records)
    assert rate == pytest.approx(requested)
    assert report["state"] == state
    assert report["ordinary_numeric_weight"] == sum(record.weight for record in records)
    assert report["positive_weight"] == sum(
        r.weight for r in records if r.event.out_of_bounds is True
    )
    assert report["explicit_false_weight"] == sum(
        r.weight for r in records if r.event.out_of_bounds is False
    )
    assert report["unknown_weight"] == sum(
        r.weight for r in records if r.event.out_of_bounds is None
    )
    assert report["unknown_observations"] == sum(r.event.out_of_bounds is None for r in records)
    assert [record.event.to_dict() for record in records] == before
    assert "positive-only narrative incidence" in report["policy"]


def test_adapter_oob_absence_remains_unknown_and_explicit_false_roundtrips() -> None:
    row = {
        "season": 2007,
        "game_id": "g",
        "id": "r",
        "pos_team_id": 1,
        "def_pos_team_id": 2,
        "type.text": "Rush",
        "rush": True,
        "yds_rushed": 4,
        "text": "Runner rush for 4 yards.",
    }
    ordinary = classify_espn(row)
    positive = classify_espn({**row, "text": "Runner rush for 4 yards, out of bounds."})
    assert ordinary is not None and ordinary.out_of_bounds is None
    assert positive is not None and positive.out_of_bounds is True
    explicit = replace(ordinary, out_of_bounds=False)
    assert Event.from_dict(explicit.to_dict()).out_of_bounds is False
