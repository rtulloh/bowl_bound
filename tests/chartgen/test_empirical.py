"""Source-neutral empirical vectors use only original fictional individual plays."""

from dataclasses import replace

from bowl_bound.models import Play
from tools.chartgen.evidence import Event


def test_family_vectors_preserve_whole_outcomes_unknowns_and_source_identity() -> None:
    from tools.chartgen.empirical import empirical_vectors

    base = Event(2007, "fictional-game", "e1", "1", "2", "Cedar Valley", "Harbor Tech", "rush", 7)
    explicit = replace(
        base,
        called_family=4,
        resolved_family=4,
        family_confidence="narrative",
        family_evidence=("text:draw",),
        fumble=True,
        fumble_lost=True,
        recovery_team="2",
        out_of_bounds=True,
    )
    unknown = replace(base, event_id="e2", yards=None)
    incomplete = replace(base, event_id="e3", kind="incomplete", yards=None)
    inferred = replace(
        base,
        event_id="e4",
        kind="complete",
        called_family=9,
        resolved_family=9,
        family_confidence="inferred-depth",
        pass_depth="deep",
    )
    penalty = replace(
        base, event_id="e5", penalty=True, no_play=True, penalty_side="offense", penalty_yards=15
    )
    other_team = replace(base, event_id="e6", team="2", opponent="1")
    evidence = [inferred, penalty, unknown, other_team, explicit, incomplete]
    vectors = empirical_vectors(evidence, "1")
    assert vectors == empirical_vectors(list(reversed(evidence)), "1")
    assert tuple(vector.play for vector in vectors.families) == tuple(Play)
    assert vectors.family(Play.FOUR).events == (explicit,)
    assert vectors.family(Play.NINE).events == (inferred,)
    assert vectors.family(Play.FOUR).numeric_yards == (7,)
    assert vectors.unknown_runs == (unknown,) and vectors.unknown_passes == (incomplete,)
    assert vectors.penalties == (penalty,)
    assert not vectors.family(Play.ONE).events
    assert vectors.family(Play.FOUR).events[0].recovery_team == "2"


def test_empirical_numeric_vectors_do_not_turn_incomplete_or_unknown_into_zero() -> None:
    from tools.chartgen.empirical import empirical_vectors

    rows = [
        Event(
            2007, "g", str(i), "1", "2", "Cedar Valley", "Harbor Tech", kind, gain, called_family=6
        )
        for i, (kind, gain) in enumerate(
            [("complete", 0), ("complete", None), ("incomplete", None), ("sack", -7)]
        )
    ]
    vector = empirical_vectors(rows, "1").family(Play.SIX)
    assert vector.events == tuple(rows)
    assert vector.numeric_yards == (0,)


def test_sparse_pool_uses_unidentified_same_unit_without_stealing_known_family_fumbles() -> None:
    from tools.chartgen.empirical import empirical_vectors, family_pool

    base = Event(2007, "g", "e", "1", "2", "Cedar Valley", "Harbor Tech", "rush", 7)
    draw = replace(base, event_id="draw", called_family=4, resolved_family=4, fumble=True)
    other_known = replace(
        base, event_id="counter", called_family=2, resolved_family=2, yards=90, fumble=True
    )
    generic = replace(base, event_id="unknown", fumble=False)
    opponent = [
        replace(base, event_id=f"other-{i}", team="2", opponent="1", yards=i, fumble=False)
        for i in range(40)
    ]
    source = [draw, other_known, generic, *opponent]
    vectors = empirical_vectors(source, "1")
    pool = family_pool(vectors, Play.FOUR, source, team="1")
    assert draw in [record.event for record in pool.observations]
    assert other_known not in [record.event for record in pool.observations]
    assert all(record.weight > 0 for record in pool.observations)
    assert pool.method == "pooled-unidentified-run"
    assert pool.own_family_samples == 1 and pool.league_samples == 40
    assert pool.effective_weight < len(pool.observations)
    plunge = family_pool(vectors, Play.ONE, source, team="1")
    assert not any(record.event.fumble for record in plunge.observations)


def test_option_terminal_outcomes_are_available_under_the_resolved_pass_family() -> None:
    from tools.chartgen.empirical import empirical_vectors, family_pool

    branch = Event(
        2007,
        "g",
        "sop",
        "1",
        "2",
        "Cedar Valley",
        "Harbor Tech",
        "complete",
        17,
        called_family=5,
        resolved_family=7,
    )
    evidence = [replace(branch, event_id=str(i)) for i in range(30)]
    pool = family_pool(empirical_vectors(evidence, "1"), Play.SEVEN, evidence, team="1")
    assert pool.method == "family-PBP"
    assert len(pool.observations) == 30
    assert all(
        record.event.called_family == 5 and record.event.resolved_family == 7
        for record in pool.observations
    )
