"""Synthetic tests for version-1 normalized chart models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from bowl_bound.models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    NormalizedCell,
    OffensiveCell,
    PatOutcome,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    Priority,
    Provenance,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
    VariableReference,
)


def provenance() -> Provenance:
    return Provenance(
        source_sha256="a" * 64,
        filename="synthetic.pdf",
        page=1,
        bounding_box=BoundingBox(0.0, 0.0, 1.0, 1.0),
        original_text="synthetic",
        rgb_color=(0, 255, 0),
    )


def ordinary_cell() -> NormalizedCell:
    return NormalizedCell(ResultKind.YARDS, provenance(), yards=1)


def complete_chart() -> TeamChart:
    cell = ordinary_cell()
    return TeamChart(
        schema_version=1,
        name="Synthetic State",
        season=2007,
        offense=tuple(OffensiveCell(play, roll, cell) for play in Play for roll in range(10, 40)),
        supplemental=tuple(
            SupplementalCell(column, roll, cell)
            for column in SupplementalColumn
            for roll in range(10, 40)
        ),
        defense=tuple(
            DefensiveCell(defense, play, roll, cell)
            for defense in Defense
            for play in Play
            for roll in range(1, 6)
        ),
        special_teams=tuple(
            SpecialTeamsCell(column, roll, cell)
            for column in SpecialTeamsColumn
            for roll in range(10, 40)
        ),
        pat_outcomes=tuple(
            PatOutcome(
                roll,
                good=roll != 16,
                provenance=replace(
                    provenance(), rgb_color=(255, 255, 255) if roll != 16 else (255, 0, 0)
                ),
            )
            for roll in range(10, 40)
        ),
        recovery_range=range(10, 27),
    )


def test_complete_chart_has_independent_810_cells_and_30_pat_outcomes() -> None:
    chart = complete_chart()

    assert len(chart.offense) == 270
    assert len(chart.supplemental) == 90
    assert len(chart.defense) == 270
    assert len(chart.special_teams) == 180
    chart_cells = (chart.offense, chart.supplemental, chart.defense, chart.special_teams)
    assert sum(map(len, chart_cells)) == 810
    assert len(chart.pat_outcomes) == 30
    with pytest.raises(FrozenInstanceError):
        chart.name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("field", ["offense", "supplemental", "special_teams", "pat_outcomes"])
def test_ten_through_thirty_nine_records_reject_missing_and_duplicate_keys(field: str) -> None:
    chart = complete_chart()
    records = getattr(chart, field)

    with pytest.raises(ValueError):
        replace(chart, **{field: records[:-1]})
    with pytest.raises(ValueError):
        replace(chart, **{field: records[:-1] + (records[0],)})


def test_defense_rolls_remain_one_through_five() -> None:
    chart = complete_chart()
    assert chart.defense[0].roll == 1
    with pytest.raises(ValueError):
        DefensiveCell(Defense.A, Play.ONE, 10, ordinary_cell())


@pytest.mark.parametrize(
    "cell",
    [
        NormalizedCell(ResultKind.YARDS, provenance(), yards=-3, out_of_bounds=True),
        NormalizedCell(
            ResultKind.VARIABLE_DS,
            provenance(),
            variable=VariableReference.DS,
            variable_multiplier=-2,
            out_of_bounds=True,
        ),
        NormalizedCell(ResultKind.FUMBLE, provenance(), yards=-4),
        NormalizedCell(
            ResultKind.INTERCEPTION,
            provenance(),
            variable=VariableReference.X,
            variable_multiplier=1,
        ),
        NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, yards=12),
        ),
        NormalizedCell(ResultKind.NO_GOOD_FIELD_GOAL, provenance()),
    ],
)
def test_valid_semantic_combinations(cell: NormalizedCell) -> None:
    assert cell.provenance.filename == "synthetic.pdf"


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": ResultKind.FUMBLE, "yards": 1, "out_of_bounds": True},
        {"kind": ResultKind.INTERCEPTION},
        {"kind": ResultKind.VARIABLE_DS, "variable": VariableReference.DS},
        {"kind": ResultKind.PENALTY},
        {"kind": ResultKind.PENALTY, "penalty": "S"},
        {"kind": ResultKind.YARDS, "yards": True},
    ],
)
def test_invalid_semantic_combinations_are_rejected(changes: dict[str, object]) -> None:
    defaults: dict[str, object] = {"provenance": provenance()}
    defaults.update(changes)
    with pytest.raises((TypeError, ValueError)):
        NormalizedCell(**defaults)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Provenance("+" + "a" * 63, "x", 1, BoundingBox(0, 0, 1, 1), "x", (0, 0, 0)),
        lambda: Provenance(" " + "a" * 63, "x", 1, BoundingBox(0, 0, 1, 1), "x", (0, 0, 0)),
        lambda: OffensiveCell(1, 10, ordinary_cell()),
        lambda: PatOutcome(10, good=1, provenance=provenance()),
        lambda: PatOutcome(9, good=True, provenance=provenance()),
    ],
)
def test_invalid_runtime_types_and_pat_outcomes_are_rejected(factory: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()  # type: ignore[operator]


def test_pat_outcome_preserves_its_own_provenance() -> None:
    outcome = PatOutcome(10, good=True, provenance=provenance())
    assert outcome.good is True
    assert outcome.provenance.rgb_color == (0, 255, 0)


def test_team_identity_and_recovery_range_are_validated() -> None:
    chart = complete_chart()
    with pytest.raises(ValueError):
        replace(chart, name="")
    with pytest.raises((TypeError, ValueError)):
        replace(chart, season=True)
    with pytest.raises(ValueError):
        replace(chart, recovery_range=range(9, 27))
    with pytest.raises(ValueError):
        replace(chart, recovery_range=range(10, 41))


def test_penalty_data_preserves_fixed_yards_and_pi_locations() -> None:
    fixed = PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, yards=15)
    pi = PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, yards=12)
    variable_pi = PenaltyData(
        PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=VariableReference.X, variable_multiplier=1
    )
    assert fixed.yards == 15
    assert pi.yards == 12
    assert variable_pi.variable is VariableReference.X


def test_penalty_data_rejects_missing_and_conflicting_distances() -> None:
    with pytest.raises(ValueError):
        PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED)
    with pytest.raises(ValueError):
        PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI)
    with pytest.raises(ValueError):
        PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.PI, yards=10)
    with pytest.raises(ValueError):
        PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.S, yards=5)


def test_turnover_location_cannot_be_fixed_and_variable() -> None:
    with pytest.raises(ValueError):
        NormalizedCell(
            ResultKind.FUMBLE,
            provenance(),
            yards=5,
            variable=VariableReference.T1,
            variable_multiplier=1,
        )


def test_blank_out_of_bounds_cell_is_a_valid_fact() -> None:
    assert NormalizedCell(ResultKind.NO_CHANGE, provenance(), out_of_bounds=True).out_of_bounds


@pytest.mark.parametrize(
    "field", ["offense", "supplemental", "defense", "special_teams", "pat_outcomes"]
)
def test_all_record_groups_reject_lists_and_missing_positions(field: str) -> None:
    chart = complete_chart()
    records = getattr(chart, field)
    with pytest.raises(TypeError):
        replace(chart, **{field: list(records)})
    with pytest.raises(ValueError):
        replace(chart, **{field: records[:-1]})


def test_schema_version_rejects_unknown_versions_and_bools() -> None:
    chart = complete_chart()
    for version in (True, 2, "1"):
        with pytest.raises(ValueError):
            replace(chart, schema_version=version)


# --- Review corrections: signed penalty locations, kick redirects, placement, coverage ---


def test_penalty_variable_location_is_signed_and_requires_multiplier() -> None:
    negative = PenaltyData(
        PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=VariableReference.X, variable_multiplier=-1
    )
    assert negative.variable_multiplier == -1
    with pytest.raises((TypeError, ValueError)):
        PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=VariableReference.X)
    with pytest.raises(ValueError):
        PenaltyData(
            PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=VariableReference.X, variable_multiplier=0
        )
    with pytest.raises((TypeError, ValueError)):
        PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, yards=5, variable_multiplier=1)
    with pytest.raises((TypeError, ValueError)):
        PenaltyData(
            PenaltyTeam.DEFENSE,
            PenaltyCode.PI,
            variable=VariableReference.X,
            variable_multiplier=True,
        )


@pytest.mark.parametrize("kind", [ResultKind.FIELD_GOAL_REFERENCE, ResultKind.KICKOFF_REFERENCE])
def test_punt_column_redirects_may_carry_out_of_bounds_marker(kind: ResultKind) -> None:
    # Legend: FG* / KO* appear in the punt column and still mean "no return".
    assert NormalizedCell(kind, provenance(), out_of_bounds=True).out_of_bounds


def test_source_hash_must_be_lowercase_hexadecimal() -> None:
    with pytest.raises(ValueError):
        Provenance("A" * 64, "x", 1, BoundingBox(0, 0, 1, 1), "x", (0, 0, 0))


def _special(column: SpecialTeamsColumn, kind: ResultKind) -> SpecialTeamsCell:
    return SpecialTeamsCell(column, 10, NormalizedCell(kind, provenance()))


def test_kind_placement_is_enforced_for_special_team_only_results() -> None:
    ng = NormalizedCell(ResultKind.NO_GOOD_FIELD_GOAL, provenance())
    _special(SpecialTeamsColumn.FIELD_GOAL, ResultKind.NO_GOOD_FIELD_GOAL)
    for column in SpecialTeamsColumn:
        if column is not SpecialTeamsColumn.FIELD_GOAL:
            with pytest.raises(ValueError):
                _special(column, ResultKind.NO_GOOD_FIELD_GOAL)
    with pytest.raises(ValueError):
        OffensiveCell(Play.ONE, 10, ng)
    with pytest.raises(ValueError):
        DefensiveCell(Defense.A, Play.ONE, 1, ng)
    with pytest.raises(ValueError):
        SupplementalCell(SupplementalColumn.BREAKAWAY, 10, ng)


@pytest.mark.parametrize("kind", [ResultKind.FIELD_GOAL_REFERENCE, ResultKind.KICKOFF_REFERENCE])
def test_punt_redirects_only_belong_in_the_punt_column(kind: ResultKind) -> None:
    _special(SpecialTeamsColumn.PUNT, kind)
    for column in SpecialTeamsColumn:
        if column is not SpecialTeamsColumn.PUNT:
            with pytest.raises(ValueError):
                _special(column, kind)
    with pytest.raises(ValueError):
        OffensiveCell(Play.ONE, 10, NormalizedCell(kind, provenance()))


@pytest.mark.parametrize("kind", [ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS])
def test_option_results_only_belong_to_offensive_play_five(kind: ResultKind) -> None:
    option = NormalizedCell(kind, provenance())
    assert OffensiveCell(Play.FIVE, 10, option).cell.kind is kind
    with pytest.raises(ValueError):
        OffensiveCell(Play.FOUR, 10, option)
    with pytest.raises(ValueError):
        DefensiveCell(Defense.A, Play.FIVE, 1, option)
    with pytest.raises(ValueError):
        SupplementalCell(SupplementalColumn.QUARTERBACK_RUN, 10, option)
    with pytest.raises(ValueError):
        _special(SpecialTeamsColumn.PUNT, kind)


def test_parenthesized_breakaway_is_supported_only_on_defensive_charts() -> None:
    result = NormalizedCell(ResultKind.BREAKAWAY, provenance(), priority=Priority.PARENTHESIZED)

    assert DefensiveCell(Defense.A, Play.ONE, 1, result).cell is result
    with pytest.raises(ValueError, match="defensive charts"):
        OffensiveCell(Play.ONE, 10, result)
    with pytest.raises(ValueError, match="defensive charts"):
        SupplementalCell(SupplementalColumn.BREAKAWAY, 10, result)


LEGEND_FACTS = [
    # (legend token, expected normalized fields)
    ("-5", dict(kind=ResultKind.YARDS, yards=-5)),
    (
        "(4)*",
        dict(kind=ResultKind.YARDS, yards=4, priority=Priority.PARENTHESIZED, out_of_bounds=True),
    ),
    ("[-3]", dict(kind=ResultKind.YARDS, yards=-3, priority=Priority.BRACKETED)),
    (
        "T0 alias of X",
        dict(kind=ResultKind.VARIABLE_X, variable=VariableReference.X, variable_multiplier=1),
    ),
    (
        "-DS",
        dict(kind=ResultKind.VARIABLE_DS, variable=VariableReference.DS, variable_multiplier=-1),
    ),
    ("F +T1", dict(kind=ResultKind.FUMBLE, variable=VariableReference.T1, variable_multiplier=1)),
    ("F -DS", dict(kind=ResultKind.FUMBLE, variable=VariableReference.DS, variable_multiplier=-1)),
    ("INT -5", dict(kind=ResultKind.INTERCEPTION, yards=-5)),
    ("BK -7", dict(kind=ResultKind.BLOCKED_KICK, yards=-7)),
    ("INC", dict(kind=ResultKind.INCOMPLETE)),
    ("SOP", dict(kind=ResultKind.SPRINT_OUT_PASS)),
    ("BLP", dict(kind=ResultKind.BOOTLEG_PASS)),
    ("*", dict(kind=ResultKind.NO_CHANGE, out_of_bounds=True)),
]


@pytest.mark.parametrize(("token", "fields"), LEGEND_FACTS, ids=[t for t, _ in LEGEND_FACTS])
def test_every_legend_form_is_representable_with_exact_stored_fields(
    token: str, fields: dict[str, object]
) -> None:
    cell = NormalizedCell(provenance=provenance(), **fields)
    for name, expected in fields.items():
        assert getattr(cell, name) == expected, token
    assert cell.penalty is None


@pytest.mark.parametrize(
    ("team", "code", "extra"),
    [
        (PenaltyTeam.OFFENSE, PenaltyCode.FIXED, dict(yards=10)),
        (PenaltyTeam.DEFENSE, PenaltyCode.FIXED, dict(yards=15)),
        (PenaltyTeam.OFFENSE, PenaltyCode.S, {}),
        (PenaltyTeam.DEFENSE, PenaltyCode.R, {}),
        (PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS, {}),
        (PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS_X, {}),
        (PenaltyTeam.DEFENSE, PenaltyCode.PI, dict(yards=12)),
    ],
)
def test_legend_penalty_forms_are_representable_and_preserved(
    team: PenaltyTeam, code: PenaltyCode, extra: dict[str, object]
) -> None:
    penalty = PenaltyData(team, code, **extra)
    cell = NormalizedCell(ResultKind.PENALTY, provenance(), penalty=penalty)
    assert cell.penalty == penalty
    assert (cell.penalty.team, cell.penalty.code) == (team, code)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "kind": ResultKind.YARDS,
            "yards": 1,
            "variable": VariableReference.X,
            "variable_multiplier": 1,
        },
        {"kind": ResultKind.VARIABLE_DS, "variable": VariableReference.X, "variable_multiplier": 1},
        {"kind": ResultKind.VARIABLE_DS, "variable": VariableReference.DS},
        {
            "kind": ResultKind.VARIABLE_DS,
            "variable": VariableReference.DS,
            "variable_multiplier": 0,
        },
        {
            "kind": ResultKind.VARIABLE_DS,
            "variable": VariableReference.DS,
            "variable_multiplier": True,
        },
        {
            "kind": ResultKind.VARIABLE_DS,
            "variable": VariableReference.DS,
            "variable_multiplier": 1,
            "yards": 3,
        },
        {
            "kind": ResultKind.PENALTY,
            "penalty": PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S),
            "yards": 5,
        },
        {"kind": ResultKind.NO_CHANGE, "penalty": PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.S)},
        {"kind": ResultKind.INCOMPLETE, "out_of_bounds": True},
        {"kind": ResultKind.TOUCHDOWN, "out_of_bounds": True},
        {"kind": ResultKind.INTERCEPTION, "yards": 1, "out_of_bounds": True},
        {"kind": ResultKind.NO_CHANGE, "priority": "normal"},
        {"kind": "yards", "yards": 1},
    ],
)
def test_more_invalid_normalized_cell_combinations(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        NormalizedCell(provenance=provenance(), **changes)


@pytest.mark.parametrize(
    "box",
    [
        (1, 0, 0, 1),
        (0, 1, 1, 0),
        (0, 0, 0, 1),
        (0, 0, float("inf"), 1),
        (0, 0, float("nan"), 1),
        (True, 0, 1, 1),
    ],
)
def test_bounding_box_rejects_bad_geometry(box: tuple[object, ...]) -> None:
    with pytest.raises((TypeError, ValueError)):
        BoundingBox(*box)


@pytest.mark.parametrize(
    "changes",
    [
        {"filename": ""},
        {"page": 0},
        {"page": True},
        {"rgb_color": [1, 2, 3]},
        {"rgb_color": (1, 2)},
        {"rgb_color": (1, 2, -1)},
        {"rgb_color": (1, 2, True)},
        {"bounding_box": (0, 0, 1, 1)},
        {"original_text": None},
    ],
)
def test_provenance_rejects_more_invalid_evidence(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(provenance(), **changes)


def test_normalized_chart_cell_requires_measured_rgb_provenance() -> None:
    evidence = replace(provenance(), rgb_color=None)
    with pytest.raises(ValueError, match="require measured RGB provenance"):
        NormalizedCell(ResultKind.YARDS, evidence, yards=1)
    with pytest.raises(ValueError, match="PAT outcomes require measured RGB provenance"):
        PatOutcome(10, True, evidence)


@pytest.mark.parametrize("roll", [0, 9, 40, True, 10.0])
def test_offense_supplemental_special_and_pat_reject_out_of_range_rolls(roll: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        OffensiveCell(Play.ONE, roll, ordinary_cell())
    with pytest.raises((TypeError, ValueError)):
        SupplementalCell(SupplementalColumn.BREAKAWAY, roll, ordinary_cell())
    with pytest.raises((TypeError, ValueError)):
        SpecialTeamsCell(SpecialTeamsColumn.KICKOFF, roll, ordinary_cell())
    with pytest.raises((TypeError, ValueError)):
        PatOutcome(roll, good=True, provenance=provenance())


@pytest.mark.parametrize("roll", [0, 6, 10, True])
def test_defense_rejects_out_of_range_rolls(roll: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        DefensiveCell(Defense.A, Play.ONE, roll, ordinary_cell())


def test_chart_rejects_duplicate_defense_and_wrong_record_types() -> None:
    chart = complete_chart()
    with pytest.raises(ValueError):
        replace(chart, defense=chart.defense[:-1] + (chart.defense[0],))
    with pytest.raises(TypeError):
        replace(chart, offense=chart.offense[:-1] + (chart.pat_outcomes[0],))
    with pytest.raises(TypeError):
        replace(chart, pat_outcomes=chart.pat_outcomes[:-1] + (chart.special_teams[0],))


@pytest.mark.parametrize("recovery", [range(10, 30, 2), range(10, 10), range(26, 10, -1), [10, 26]])
def test_chart_rejects_bad_recovery_ranges(recovery: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(complete_chart(), recovery_range=recovery)


@pytest.mark.parametrize(
    "changes", [{"name": "   "}, {"name": 5}, {"season": 0}, {"season": "2007"}]
)
def test_chart_rejects_bad_identity(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(complete_chart(), **changes)
