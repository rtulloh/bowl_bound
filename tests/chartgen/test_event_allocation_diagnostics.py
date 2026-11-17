"""Admissible support diagnostics must obey the allocator's numeric constraint."""

from collections import Counter
from dataclasses import replace

import pytest

from bowl_bound.dice import GREEN_FACES, RED_FACES
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chartgen.event_risks import WEIGHTS, apply_event_model, joint_allocate


def test_admitted_mass_table_excludes_assignments_without_required_numeric_support():
    allocation = joint_allocate(
        (12, 11, 9, 3, 1),
        (0, 0, 0, 1, 2),
        (0, 0, 0, 0, 0),
        (3, 1),
        baseline=(3, 1),
    )
    assert all(inc + qt < 36 for inc, qt in allocation.attainable)


def test_strict_event_direction_can_be_infeasible_without_erasing_numeric_support():
    allocation = joint_allocate((1,), (0,), (4,), (1, 0), baseline=(0, 0), direction=(1, 0))
    assert allocation.status == "infeasible-direction"
    assert allocation.assignments is None
    assert allocation.represented is None


def test_allocator_weights_are_the_exact_physical_defensive_law():
    observed = Counter(red + green for red in RED_FACES for green in GREEN_FACES)
    assert tuple(observed[i] for i in range(1, 6)) == WEIGHTS
    assert sum(WEIGHTS) == 36


@pytest.mark.parametrize("token", ["(2)", "[2]", "2*", "F + 2", "INT 17", "QR"])
def test_protected_response_facts_are_not_used_as_allocator_slots(token):
    chart = team_chart("Protected synthetic", defense=0)
    chart = replace(
        chart,
        defense=tuple(
            replace(row, cell=parse_cell(token, provenance()))
            if row.play.value >= 6 and row.roll == 5
            else row
            for row in chart.defense
        ),
    )
    candidate, _ = apply_event_model(chart)
    assert tuple(row for row in chart.defense if row.play.value >= 6 and row.roll == 5) == tuple(
        row for row in candidate.defense if row.play.value >= 6 and row.roll == 5
    )
