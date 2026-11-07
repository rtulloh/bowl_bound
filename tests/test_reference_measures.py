"""Physical benchmark measurement controls use only fictional chart facts."""

from dataclasses import replace

import pytest

from bowl_bound.models import Defense, NormalizedCell, Play, Priority, ResultKind, VariableReference
from tests.test_team_csv import chart, evidence
from tools.reference_measures import primary_measure, table_measures


def cell(kind: ResultKind = ResultKind.YARDS, yards: int | None = 10, **kwargs):
    return NormalizedCell(kind, evidence(), yards=yards, **kwargs)


def teams(offense_cell=None, defense_cell=None):
    home, away = chart("Cedar Valley"), chart("Harbor Tech")
    o = offense_cell or cell()
    d = defense_cell or cell(ResultKind.NO_CHANGE, None)
    return replace(home, offense=tuple(replace(r, cell=o) for r in home.offense)), replace(
        away, defense=tuple(replace(r, cell=d) for r in away.defense)
    )


def test_primary_numeric_law_has_full_physical_denominator_and_signed_adjustment():
    offense, defense = teams(defense_cell=cell(yards=-3))
    result = primary_measure(offense, defense, Play.SIX, Defense.D)
    assert result["physical_mass"] == 7776
    assert result["ordinary_numeric_histogram"] == {7: 7776}
    assert result["ordinary_yardage_contribution"] == "7"
    assert result["pending_mass"] == 0
    assert result["independent_priority_checked"] is False


def test_protected_offense_suppresses_defensive_interception():
    offense, defense = teams(
        cell(priority=Priority.PARENTHESIZED), cell(ResultKind.INTERCEPTION, 5)
    )
    result = primary_measure(offense, defense, Play.SIX, Defense.D)
    assert result["kind_mass"] == {"yards": 7776}
    assert result["ordinary_numeric_histogram"] == {10: 7776}
    assert result["selected_INT_location_histogram"] == {}


def test_int_min_depth_is_selected_location_not_a_committed_turnover():
    offense, defense = teams(cell(ResultKind.INTERCEPTION, 20), cell(ResultKind.INTERCEPTION, 5))
    result = primary_measure(offense, defense, Play.NINE, Defense.A)
    assert result["selected_INT_location_histogram"] == {5: 7776}
    assert result["operation_mass"] == {"INT_MIN": 7776}
    assert result["pending_mass"] == 7776
    assert result["ordinary_yardage_contribution"] == "0"
    assert result["terminal_acceptance"] == "NOTRUN-symbolic-primary-only"


def test_qt_trigger_preserves_pending_mass_and_is_not_completion():
    offense, defense = teams(defense_cell=cell(ResultKind.QUARTERBACK_TRAPPED, None))
    result = primary_measure(offense, defense, Play.NINE, Defense.F)
    assert result["kind_mass"] == {"QT": 7776}
    assert result["pending_mass"] == 7776
    assert result["ordinary_numeric_mass"] == 0


def test_variable_distance_is_not_fabricated_zero_yards():
    offense, defense = teams(
        cell(ResultKind.VARIABLE_X, None, variable=VariableReference.X, variable_multiplier=1)
    )
    result = primary_measure(offense, defense, Play.SIX, Defense.A)
    assert result["kind_mass"] == {"unresolved_variable": 7776}
    assert result["pending_mass"] == 7776
    assert result["ordinary_numeric_histogram"] == {}


def test_physical_offensive_row_mass_is_not_one_thirtieth():
    offense, defense = teams()
    offense = replace(
        offense,
        offense=tuple(
            replace(r, cell=cell(ResultKind.INTERCEPTION, 3)) if r.roll == 10 else r
            for r in offense.offense
        ),
    )
    result = primary_measure(offense, defense, Play.SIX, Defense.A)
    assert result["kind_mass"]["interception"] == 2 * 36
    assert result["kind_mass"]["yards"] == 214 * 36


def test_physical_defensive_row_five_is_one_thirty_sixth():
    offense, defense = teams()
    defense = replace(
        defense,
        defense=tuple(
            replace(r, cell=cell(ResultKind.INTERCEPTION, 3)) if r.roll == 5 else r
            for r in defense.defense
        ),
    )
    result = primary_measure(offense, defense, Play.SIX, Defense.A)
    assert result["kind_mass"]["interception"] == 216


def test_supplied_independent_oracle_mismatch_is_not_silently_ignored():
    offense, defense = teams()
    with pytest.raises(ValueError, match="independent priority mismatch"):
        primary_measure(
            offense, defense, Play.SIX, Defense.A, expected_priority=lambda o, d: {"yards": 999}
        )


def test_literal_independent_numeric_oracle_checks_every_address_pair():
    offense, defense = teams()
    expected = dict(
        operation="ADD",
        source="both",
        kind="yards",
        yards=10,
        pending=False,
        out_of_bounds=False,
        penalty=None,
        defensive_end_zone_depth=None,
    )
    result = primary_measure(
        offense, defense, Play.SIX, Defense.A, expected_priority=lambda o, d: expected
    )
    assert result["independent_priority_checked"] is True
    assert result["independent_priority_address_pairs"] == 150


def test_boolean_is_not_an_integer_expected_distance():
    offense, defense = teams(cell(yards=1))
    expected = dict(
        operation="ADD",
        source="both",
        kind="yards",
        yards=True,
        pending=False,
        out_of_bounds=False,
        penalty=None,
        defensive_end_zone_depth=None,
    )
    with pytest.raises(ValueError, match="independent priority mismatch"):
        primary_measure(
            offense, defense, Play.SIX, Defense.A, expected_priority=lambda o, d: expected
        )


def test_table_measures_cover_all_records_with_correct_procedure_weights():
    result = table_measures(chart("Cedar Valley"))
    assert result["chart_records"] == 840
    assert len(result["columns"]) == 73
    assert result["columns"]["offense/6"]["physical_mass"] == 216
    assert result["columns"]["defense/A/6"]["physical_mass"] == 36
    assert result["columns"]["pat"]["physical_mass"] == 216
    assert result["recovery"]["physical_mass"] == 216
    assert result["columns"]["offense/6"]["numeric_gain_histogram"] == {1: 216}
    assert result["columns"]["supplemental/B"]["kind_mass"] == {"B": 216}
