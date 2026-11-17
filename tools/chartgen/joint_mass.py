"""Exact finite whole-row mass planning, separate from chart encoding/authority.

This pure API optimizes mass stages only. Legal chart placement and source or
role targets must be supplied by independently reviewed consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from bowl_bound.models import ResultKind

ORDINARY = "ordinary"
KNOWN_FAMILIES = frozenset(
    {
        ORDINARY,
        *(
            kind.value
            for kind in ResultKind
            if kind not in {ResultKind.YARDS, ResultKind.NO_CHANGE}
        ),
    }
)


@dataclass(frozen=True)
class MassRow:
    """One indivisible physical row and its declared family domain."""

    row_id: int
    weight: int
    original: str
    allowed: tuple[str, ...]
    protected: bool = False


@dataclass(frozen=True)
class FamilyTarget:
    """An exact physical numerator, or an explicitly unknown target."""

    family: str
    mass: int | Fraction | None


@dataclass(frozen=True)
class JointMassRequest:
    rows: tuple[MassRow, ...]
    targets: tuple[FamilyTarget, ...]
    require_ordinary: bool = True
    exact_only: bool = False


@dataclass(frozen=True)
class JointMassResult:
    """Observable finite evidence; nearest is not an acceptance decision."""

    status: str
    families: tuple[str, ...]
    requested: tuple[Fraction | None, ...]
    represented: tuple[int, ...] | None = None
    assignment: tuple[str, ...] | None = None
    attainable: tuple[tuple[int, ...], ...] = ()
    requested_family_minima: tuple[tuple[int, ...], ...] = ()
    partition_frontier: tuple[tuple[int, ...], ...] = ()
    requested_family_error: Fraction | None = None
    partition_error: Fraction | None = None
    unknown_families: tuple[str, ...] = ()


def _validated(
    request: JointMassRequest,
) -> tuple[tuple[MassRow, ...], tuple[str, ...], tuple[Fraction | None, ...]]:
    if type(request) is not JointMassRequest or type(request.rows) is not tuple or not request.rows:
        raise ValueError("mass request requires a nonempty immutable row inventory")
    if (
        type(request.targets) is not tuple
        or type(request.require_ordinary) is not bool
        or type(request.exact_only) is not bool
    ):
        raise ValueError("mass request requires immutable targets and boolean dispositions")
    if any(
        type(row) is not MassRow or type(row.row_id) is not int or row.row_id <= 0
        for row in request.rows
    ):
        raise ValueError("mass rows require positive integer row identities")
    if len({row.row_id for row in request.rows}) != len(request.rows):
        raise ValueError("mass row identities must be unique")
    if (
        any(type(row.weight) is not int or row.weight <= 0 for row in request.rows)
        or sum(row.weight for row in request.rows) != 36
    ):
        raise ValueError("physical row weights must be positive integers with total 36")
    targets: dict[str, Fraction | None] = {}
    for target in request.targets:
        if (
            type(target) is not FamilyTarget
            or type(target.family) is not str
            or target.family not in KNOWN_FAMILIES
            or target.family == ORDINARY
            or target.family in targets
        ):
            raise ValueError(
                "target family inventory must be unique canonical nonordinary families"
            )
        if target.mass is not None and (
            type(target.mass) not in {int, Fraction} or target.mass < 0
        ):
            raise ValueError("target mass must be an exact nonnegative integer/Fraction or unknown")
        targets[target.family] = None if target.mass is None else Fraction(target.mass)
    if sum(value for value in targets.values() if value is not None) > 36:
        raise ValueError("nonordinary requested mass total cannot exceed 36")
    for row in request.rows:
        if (
            type(row.allowed) is not tuple
            or not row.allowed
            or any(type(family) is not str for family in row.allowed)
            or len(set(row.allowed)) != len(row.allowed)
        ):
            raise ValueError("row domain must be a nonempty unique immutable family inventory")
        if type(row.original) is not str or row.original not in row.allowed:
            raise ValueError("row original family must belong to its domain")
        if any(
            type(family) is not str
            or family not in KNOWN_FAMILIES
            or (family != ORDINARY and family not in targets)
            for family in row.allowed
        ):
            raise ValueError("row domain contains an undeclared or noncanonical family")
        if type(row.protected) is not bool or (row.protected and row.allowed != (row.original,)):
            raise ValueError("protected row must retain its singleton original domain")
    families = (ORDINARY, *sorted(targets))
    ordinary = (
        None if any(value is None for value in targets.values()) else 36 - sum(targets.values())
    )
    return (
        tuple(sorted(request.rows, key=lambda row: row.row_id)),
        families,
        (ordinary, *(targets[name] for name in families[1:])),
    )


def allocate_joint(request: JointMassRequest) -> JointMassResult:
    """Enumerate mass-optimal disjoint rows without encoding chart tokens.

    Requested-family L1 is primary; complete-partition L1 is secondary. All
    tied mass vectors are retained. The canonical witness is not asserted to
    optimize later numeric-mean or edit-cost stages.
    """
    rows, families, wanted = _validated(request)
    unknown = tuple(
        name for name, value in zip(families[1:], wanted[1:], strict=True) if value is None
    )
    if unknown:
        return JointMassResult("unknown-target", families, wanted, unknown_families=unknown)
    if request.require_ordinary and not any(row.original == ORDINARY for row in rows):
        return JointMassResult("undefined-numeric-support", families, wanted)
    family_index = {name: index for index, name in enumerate(families)}
    vectors: dict[tuple[int, ...], tuple[int, ...]] = {}
    domains = tuple(tuple(sorted(family_index[name] for name in row.allowed)) for row in rows)
    for assignment in product(*domains):
        if request.require_ordinary and 0 not in assignment:
            continue
        mass = tuple(
            sum(row.weight for row, kind in zip(rows, assignment, strict=True) if kind == index)
            for index in range(len(families))
        )
        if mass not in vectors or assignment < vectors[mass]:
            vectors[mass] = assignment
    if not vectors:
        return JointMassResult("infeasible", families, wanted)
    scores = {
        mass: (
            sum(
                (abs(value - target) for value, target in zip(mass[1:], wanted[1:], strict=True)),
                Fraction(),
            ),
            sum(
                (abs(value - target) for value, target in zip(mass, wanted, strict=True)),
                Fraction(),
            ),
        )
        for mass in vectors
    }
    first = min(score[0] for score in scores.values())
    first_vectors = tuple(sorted(mass for mass, score in scores.items() if score[0] == first))
    second = min(scores[mass][1] for mass in first_vectors)
    frontier = tuple(mass for mass in first_vectors if scores[mass][1] == second)
    selected = min(frontier, key=lambda mass: vectors[mass])
    exact = first == 0
    withheld = request.exact_only and not exact
    return JointMassResult(
        "infeasible" if withheld else "exact" if exact else "nearest",
        families,
        wanted,
        None if withheld else selected,
        None if withheld else tuple(families[index] for index in vectors[selected]),
        tuple(sorted(vectors)),
        first_vectors,
        frontier,
        first,
        second,
    )
