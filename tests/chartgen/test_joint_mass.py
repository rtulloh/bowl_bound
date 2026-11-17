"""Synthetic stage-1–3 mass allocation controls; not source-fit judgments."""

from dataclasses import replace
from fractions import Fraction
from itertools import product

import pytest

from bowl_bound.models import ResultKind
from tools.chartgen.joint_mass import FamilyTarget, JointMassRequest, MassRow, allocate_joint

WEIGHTS = (12, 11, 9, 3, 1)
FAMILIES = ("incomplete", "interception", "QT")


def request(masses=(3, 1, 2), *, exact_only=False):
    return JointMassRequest(
        rows=tuple(
            MassRow(i + 1, weight, "ordinary", ("ordinary", *FAMILIES))
            for i, weight in enumerate(WEIGHTS)
        ),
        targets=tuple(
            FamilyTarget(family, mass) for family, mass in zip(FAMILIES, masses, strict=True)
        ),
        exact_only=exact_only,
    )


def oracle(subject):
    families = ("ordinary", *sorted(t.family for t in subject.targets))
    wanted = {t.family: Fraction(t.mass) for t in subject.targets}
    wanted["ordinary"] = 36 - sum(wanted.values())
    vectors = set()
    for assignment in product(*(row.allowed for row in subject.rows)):
        if subject.require_ordinary and "ordinary" not in assignment:
            continue
        vectors.add(
            tuple(
                sum(
                    row.weight
                    for row, family in zip(subject.rows, assignment, strict=True)
                    if family == kind
                )
                for kind in families
            )
        )
    scores = {
        vector: (
            sum(
                abs(vector[i] - wanted[family])
                for i, family in enumerate(families)
                if family != "ordinary"
            ),
            sum(abs(vector[i] - wanted[family]) for i, family in enumerate(families)),
        )
        for vector in vectors
    }
    first = min(value[0] for value in scores.values())
    first_vectors = tuple(sorted(vector for vector, value in scores.items() if value[0] == first))
    second = min(scores[vector][1] for vector in first_vectors)
    frontier = tuple(vector for vector in first_vectors if scores[vector][1] == second)
    return families, tuple(sorted(vectors)), first_vectors, frontier, first, second


def test_joint_requested_and_residual_errors_and_all_tied_minima():
    subject = request()
    result = allocate_joint(subject)
    expected = oracle(subject)
    assert result.families == expected[0]
    assert result.attainable == expected[1]
    assert result.requested_family_minima == expected[2]
    assert result.partition_frontier == expected[3]
    assert result.requested_family_error == expected[4] == 2
    assert result.partition_error == expected[5] == 4
    assert (32, 0, 3, 1) in result.partition_frontier
    assert (32, 1, 3, 0) in result.partition_frontier
    assert result.status == "nearest"
    assert result.assignment is not None


def test_exact_only_retains_evidence_without_selecting_approximation():
    result = allocate_joint(request((3, 1, 1), exact_only=True))
    assert result.status == "infeasible"
    assert result.assignment is None
    assert result.requested_family_error > 0
    assert result.attainable


def test_exact_feasible_has_zero_both_errors():
    result = allocate_joint(request((3, 1, 9)))
    assert result.status == "exact"
    assert result.requested_family_error == result.partition_error == 0
    assert result.represented == result.requested


def test_target_and_domain_order_do_not_change_semantic_result():
    subject = request()
    reversed_subject = replace(
        subject,
        targets=tuple(reversed(subject.targets)),
        rows=tuple(replace(row, allowed=tuple(reversed(row.allowed))) for row in subject.rows),
    )
    assert allocate_joint(subject) == allocate_joint(reversed_subject)


def test_row_sequence_does_not_change_addressed_witness():
    subject = request()
    assert allocate_joint(subject) == allocate_joint(
        replace(subject, rows=tuple(reversed(subject.rows)))
    )


@pytest.mark.parametrize("bad_family", [["incomplete"], True, 1])
def test_invalid_domain_scalar_is_an_actionable_error(bad_family):
    subject = request()
    invalid = replace(
        subject,
        rows=(replace(subject.rows[0], allowed=("ordinary", bad_family)), *subject.rows[1:]),
    )
    with pytest.raises(ValueError, match="domain"):
        allocate_joint(invalid)


def test_protected_rows_cannot_be_given_a_mutable_domain():
    subject = request()
    bad = replace(subject, rows=(replace(subject.rows[0], protected=True), *subject.rows[1:]))
    with pytest.raises(ValueError, match="protected"):
        allocate_joint(bad)


def test_fixed_protected_family_is_counted_in_whole_partition():
    subject = request((3, 1, 9))
    rows = (
        *subject.rows[:4],
        replace(
            subject.rows[4], original="interception", allowed=("interception",), protected=True
        ),
    )
    result = allocate_joint(replace(subject, rows=rows))
    assert result.status == "exact"
    assert result.assignment[-1] == "interception"
    assert all(vector[result.families.index("interception")] >= 1 for vector in result.attainable)


def test_unknown_is_not_zero_or_nearest():
    subject = request()
    result = allocate_joint(
        replace(subject, targets=(replace(subject.targets[0], mass=None), *subject.targets[1:]))
    )
    assert result.status == "unknown-target"
    assert result.assignment is result.requested_family_error is result.partition_error is None
    assert result.unknown_families == ("incomplete",)
    assert not result.attainable


@pytest.mark.parametrize("mass", [True, 1.0, float("nan"), -1, Fraction(-1, 2)])
def test_invalid_mass_has_actionable_error(mass):
    subject = request()
    with pytest.raises(ValueError, match="mass"):
        allocate_joint(
            replace(subject, targets=(replace(subject.targets[0], mass=mass), *subject.targets[1:]))
        )


def test_sum_of_requests_cannot_exceed_total():
    with pytest.raises(ValueError, match="total"):
        allocate_joint(request((20, 20, 1)))


def test_fractional_request_is_not_rounded_before_search():
    subject = request((Fraction(27, 25), 0, 0))
    result = allocate_joint(subject)
    assert result.requested[result.families.index("incomplete")] == Fraction(27, 25)
    assert result.represented[result.families.index("incomplete")] == 1
    assert result.requested_family_error == Fraction(2, 25)


def test_numeric_support_is_admitted_before_attainability():
    result = allocate_joint(request((36, 0, 0)))
    assert all(vector[0] > 0 for vector in result.attainable)
    assert result.status == "nearest"
    assert all(family == "ordinary" for family in allocate_joint(request((0, 0, 0))).assignment)


def test_no_original_numeric_mean_is_explicitly_undefined():
    subject = request()
    subject = replace(
        subject, rows=tuple(replace(row, original="incomplete") for row in subject.rows)
    )
    result = allocate_joint(subject)
    assert result.status == "undefined-numeric-support"
    assert result.assignment is None


def test_all_declared_families_are_jointly_supported_without_claiming_procedure_admission():
    names = tuple(
        sorted(
            kind.value
            for kind in ResultKind
            if kind not in {ResultKind.YARDS, ResultKind.NO_CHANGE}
        )
    )
    subject = JointMassRequest(
        rows=(
            MassRow(1, 12, "ordinary", ("ordinary", *names)),
            *(
                MassRow(i + 2, weight, "ordinary", ("ordinary",))
                for i, weight in enumerate(WEIGHTS[1:])
            ),
        ),
        targets=tuple(FamilyTarget(name, 0) for name in names),
    )
    result = allocate_joint(subject)
    assert result.status == "exact"
    assert len(result.attainable) == len(names) + 1
    assert set(result.families) == {"ordinary", *names}


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("weight", "weight"),
        ("duplicate-row", "row"),
        ("duplicate-target", "family"),
        ("undeclared", "family"),
        ("empty-domain", "domain"),
        ("not-original", "original"),
    ],
)
def test_invalid_row_or_inventory_is_refused(mutation, match):
    subject = request()
    if mutation == "weight":
        subject = replace(subject, rows=(replace(subject.rows[0], weight=13), *subject.rows[1:]))
    elif mutation == "duplicate-row":
        subject = replace(subject, rows=(replace(subject.rows[0], row_id=2), *subject.rows[1:]))
    elif mutation == "duplicate-target":
        subject = replace(subject, targets=(*subject.targets, subject.targets[0]))
    elif mutation == "undeclared":
        subject = replace(subject, targets=subject.targets[1:])
    elif mutation == "empty-domain":
        subject = replace(subject, rows=(replace(subject.rows[0], allowed=()), *subject.rows[1:]))
    else:
        subject = replace(
            subject, rows=(replace(subject.rows[0], original="NG"), *subject.rows[1:])
        )
    with pytest.raises(ValueError, match=match):
        allocate_joint(subject)
