"""Executable private-model admission; not historical source qualification."""

from dataclasses import replace
from fractions import Fraction

import pytest

from bowl_bound.models import Defense, Play
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chartgen.research_inputs import semantic_sha256
from tools.chartgen.typed_event_risks import (
    IntRequestEvidence,
    IntSupportState,
    classify_int_support,
    describe_int_support,
)


@pytest.mark.parametrize(
    "represented,unrounded,state",
    [
        (1, None, IntSupportState.POSITIVE_BASELINE),
        (0, Fraction(1, 2), IntSupportState.POSITIVE_UNROUNDED),
        (0, Fraction(0), IntSupportState.MODELED_ZERO),
        (0, None, IntSupportState.UNKNOWN),
    ],
)
def test_four_states_do_not_infer_source_zero_from_a_printed_zero(represented, unrounded, state):
    assert classify_int_support(represented, unrounded) is state


@pytest.mark.parametrize(
    "represented,unrounded",
    [(True, None), (-1, None), (37, None), (0, 0.5), (0, Fraction(-1)), (1, Fraction(0))],
)
def test_invalid_or_contradictory_support_is_not_opportunistically_selected(represented, unrounded):
    with pytest.raises(ValueError):
        classify_int_support(represented, unrounded)


def evidence(chart, locations=()):
    return IntRequestEvidence(
        baseline_sha256=semantic_sha256(chart),
        play=Play.SIX,
        requested_mass=Fraction(1, 2),
        locations=locations,
        source_identity="a" * 64,
    )


def test_positive_unrounded_zero_representation_does_not_invent_a_depth():
    chart = team_chart("Fictional zero represented")
    record = evidence(chart)
    result = describe_int_support(
        chart, Play.SIX, evidence=record, approved_receipt_sha256=record.receipt_sha256
    )
    assert result.state is IntSupportState.POSITIVE_UNROUNDED
    assert not result.allows_new_int
    assert result.location_support == ()
    assert result.historical_source_status == "UNVERIFIED"


def test_supplied_request_requires_independent_expected_receipt_and_actual_baseline():
    chart = team_chart("Fictional bound request")
    record = evidence(chart, ((17, 1),))
    with pytest.raises(ValueError, match="receipt"):
        describe_int_support(chart, Play.SIX, evidence=record)
    with pytest.raises(ValueError, match="receipt"):
        describe_int_support(
            chart,
            Play.SIX,
            evidence=replace(record, requested_mass=Fraction(1)),
            approved_receipt_sha256=record.receipt_sha256,
        )
    with pytest.raises(ValueError, match="baseline"):
        changed = team_chart("Fictional different baseline")
        describe_int_support(
            changed, Play.SIX, evidence=record, approved_receipt_sha256=record.receipt_sha256
        )
    result = describe_int_support(
        chart, Play.SIX, evidence=record, approved_receipt_sha256=record.receipt_sha256
    )
    assert result.allows_new_int
    assert result.location_support == ((17, 1),)
    assert result.historical_source_status == "UNVERIFIED"


def test_variable_interception_location_is_not_a_new_fixed_payload_authority():
    chart = team_chart("Fictional variable location")
    chart = replace(
        chart,
        defense=tuple(
            replace(row, cell=parse_cell("INT X", provenance()))
            if row.defense is Defense.A and row.play is Play.SIX and row.roll == 5
            else row
            for row in chart.defense
        ),
    )
    support = describe_int_support(chart, Play.SIX)
    assert support.state is IntSupportState.POSITIVE_BASELINE
    assert support.location_support == ()
    assert not support.allows_new_int
    assert support.unlocated_represented_mass == 1
