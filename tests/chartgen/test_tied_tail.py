"""Tied gains retain all attached true/false/unknown source evidence."""

import hashlib
import json
from collections import Counter
from dataclasses import replace

import pytest

from bowl_bound.models import Play
from bowl_bound.team_csv import team_to_files
from tests.chartgen.test_generation import events as source_events
from tools.chartgen.empirical import WeightedObservation
from tools.chartgen.evidence import Event
from tools.chartgen.generate import generate_team


@pytest.fixture
def events() -> list[Event]:
    """Reuse the maintained complete synthetic bundle source factory."""
    return source_events.__wrapped__()


@pytest.mark.parametrize("sparse", (False, True))
@pytest.mark.parametrize("mixed_gains", (False, True))
def test_equal_gain_boundary_ties_preserve_full_bundle_under_source_permutations(
    events: list[Event], sparse: bool, mixed_gains: bool
) -> None:
    counters = Counter()
    source = []
    for event in events:
        if event.kind == "rush":
            index = counters[event.team]
            counters[event.team] += 1
            low = mixed_gains and index < 48
            flag_index = index // 16 if low else (index - 48) // 24 if mixed_gains else index // 40
            event = replace(
                event,
                yards=4 if low else 20,
                fumble=False,
                out_of_bounds=(True, False, None)[flag_index],
            )
            if sparse and event.team == "1":
                continue
        source.append(event)
    permutations = (source, list(reversed(source)), source[73:] + source[:73])
    bundles = []
    for sequence in permutations:
        chart, metadata, report = generate_team(sequence, "1", "Cedar Valley", 2007, seed=19)
        bounds = report["supplemental_evidence"]["B"]["out_of_bounds_evidence"]
        # All120 tied records:40positive,40false,40unknown. Retained total mass
        # remains12 (own) or3 (sparse30-observation fallback tail).
        assert bounds["requested_numeric_probability"] == pytest.approx(1 / 3)
        assert bounds["ordinary_numeric_weight"] == pytest.approx(3 if sparse else 12)
        assert bounds["ordinary_numeric_observations"] == (72 if mixed_gains else 120)
        per_flag = 24 if mixed_gains else 40
        assert bounds["positive_observations"] == bounds["explicit_false_observations"] == per_flag
        assert bounds["unknown_observations"] == per_flag
        assert bounds["explicit_evidence_coverage"] == pytest.approx(2 / 3)
        assert bounds["state"] == "partial-positive-evidence"
        assert any(row.cell.kind.value == "B" for row in chart.offense if row.play is Play.ONE)
        files = team_to_files(chart, metadata)
        encoded = json.dumps([e.to_dict() for e in sequence], sort_keys=True, separators=(",", ":"))
        assert metadata.source_sha256 == hashlib.sha256(encoded.encode()).hexdigest()
        assert files["team.yaml"].count(metadata.source_sha256) == 1
        # Only the independently checked original sequence hash may differ.
        bundles.append(
            {
                **files,
                "team.yaml": files["team.yaml"].replace(metadata.source_sha256, "0" * 64),
            }
        )
    assert bundles[0] == bundles[1] == bundles[2]


@pytest.mark.parametrize(
    "gains,selected,expected",
    (
        ((1, 2, 3), (2, 3), (0, 1, 1)),
        ((1, 3, 3, 3), (3,), (0, 1 / 3, 1 / 3, 1 / 3)),
        ((1, 3, 3, 4), (3, 4), (0, 0.5, 0.5, 1)),
        ((1, 3, 3, 4), (3, 3, 4), (0, 1, 1, 1)),
    ),
)
def test_selected_numeric_support_preserves_rank_mass_and_whole_attached_facts(
    gains: tuple[int, ...], selected: tuple[int, ...], expected: tuple[float, ...]
) -> None:
    from tools.chartgen.generate import _selected_numeric_support

    records = [
        WeightedObservation(
            Event(
                2007,
                "synthetic",
                str(i),
                "1",
                "2",
                "A",
                "B",
                "rush",
                gain,
                fumble=False,
                out_of_bounds=(True, False, None)[i % 3],
            ),
            1.0,
        )
        for i, gain in enumerate(gains)
    ]
    for sequence in (records, list(reversed(records))):
        support = _selected_numeric_support(sequence, selected, value=lambda e: e.yards)
        assert sum(record.weight for record in support) == pytest.approx(len(selected))
        for index, record in enumerate(records):
            found = [r for r in support if r.event is record.event]
            assert len(found) == (1 if expected[index] else 0)
            if found:
                assert found[0].weight == pytest.approx(expected[index])
        for gain, count in Counter(selected).items():
            assert sum(r.weight for r in support if r.event.yards == gain) == pytest.approx(count)


def test_sparse_pool_ties_preserve_original_mixed_numeric_sample_and_full_support() -> None:
    from tools.chartgen.generate import _pool, _selected_numeric_support

    # Old fallback samples30 numeric ranks from60 observations:24low,6high.
    # The subsequent top10% is3high, regardless expanded support object count.
    league = [
        Event(
            2007,
            "synthetic",
            str(i),
            "2",
            "1",
            "B",
            "A",
            "rush",
            4 if i < 48 else 20,
            fumble=False,
            out_of_bounds=(True, False, None)[i % 3],
        )
        for i in range(60)
    ]
    for sequence in (league, list(reversed(league))):
        records = []
        values = _pool((), sequence, "rush", {}, observations=records)
        assert values == [4] * 24 + [20] * 6
        assert len(records) == 60
        assert sum(r.weight for r in records) == pytest.approx(30)
        tail = _selected_numeric_support(records, values[27:], value=lambda e: e.yards)
        assert len(tail) == 12
        assert all(r.event.yards == 20 for r in tail)
        assert sum(r.weight for r in tail) == pytest.approx(3)
        for flag in (True, False, None):
            assert sum(r.weight for r in tail if r.event.out_of_bounds is flag) == pytest.approx(1)


@pytest.mark.parametrize("all_fumbles", (False, True))
def test_tied_fallback_retains_fumble_fact_without_ordinary_oob_support(all_fumbles: bool) -> None:
    from tools.chartgen.generate import (
        _out_of_bounds_evidence,
        _pool,
        _primary_fumble,
        _selected_numeric_support,
    )

    league = [
        Event(
            2007,
            "synthetic",
            str(i),
            "2",
            "1",
            "B",
            "A",
            "rush",
            20,
            fumble=all_fumbles or i < 30,
            out_of_bounds=True if all_fumbles or i < 30 else None,
        )
        for i in range(60)
    ]
    support = []
    values = _pool((), league, "rush", {}, observations=support)
    assert values == [20] * 30
    tail = _selected_numeric_support(support, values[27:], value=lambda e: e.yards)
    assert len(tail) == 60 and sum(r.weight for r in tail) == pytest.approx(3)
    assert all(r.event is league[i] for i, r in enumerate(tail))
    ordinary = [r for r in tail if not _primary_fumble(r.event)]
    requested, evidence = _out_of_bounds_evidence(ordinary)
    assert requested == 0
    assert evidence["positive_weight"] == evidence["explicit_false_weight"] == 0
    assert evidence["unknown_weight"] == pytest.approx(0 if all_fumbles else 1.5)
    assert evidence["state"] == ("dormant" if all_fumbles else "unidentified")


def test_rounded_numeric_ties_preserve_distinct_raw_gain_and_fractional_support() -> None:
    from tools.chartgen.generate import _selected_numeric_support

    records = [
        WeightedObservation(
            Event(
                2007,
                "synthetic",
                str(i),
                "1",
                "2",
                "A",
                "B",
                "rush",
                gain,
                fumble=False,
                out_of_bounds=flag,
            ),
            weight,
        )
        for i, (gain, flag, weight) in enumerate(((1, True, 0.25), (2, None, 0.75)))
    ]
    support = _selected_numeric_support(records, (0,), value=lambda e: round(e.yards * 0.1))
    assert [r.event for r in support] == [r.event for r in records]
    assert [r.weight for r in support] == [0.25, 0.75]


def test_fractional_mixed_ties_have_exact_order_independent_oob_evidence() -> None:
    from tools.chartgen.generate import _out_of_bounds_evidence, _selected_numeric_support

    records = [
        WeightedObservation(
            Event(
                2007,
                "synthetic",
                str(i),
                "1",
                "2",
                "A",
                "B",
                "rush",
                gain,
                fumble=False,
                out_of_bounds=flag,
            ),
            weight,
        )
        for i, (gain, flag, weight) in enumerate(
            (
                (1, True, 0.1),
                (1, False, 0.7),
                (1, None, 0.3),
                (2, True, 0.2),
                (2, False, 0.6),
                (2, None, 0.9),
            )
        )
    ]
    results = []
    for sequence in (records, list(reversed(records)), records[2:] + records[:2]):
        support = _selected_numeric_support(sequence, (1, 2, 2), value=lambda e: e.yards)
        results.append(_out_of_bounds_evidence(support))
    assert results[0] == results[1] == results[2]
