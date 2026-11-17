"""Synthetic actual-engine tests for the provisional authored event model."""

from collections import Counter
from dataclasses import replace
from itertools import product

import pytest

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.models import Defense, Play, ResultKind, SupplementalColumn
from bowl_bound.resolution import resolve_play
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chartgen.event_risks import apply_event_model, joint_allocate, model_identity


def flat_defense():
    chart = team_chart("Flat synthetic", defense=0)
    return replace(
        chart,
        defense=tuple(
            replace(r, cell=parse_cell("BLACK", provenance()))
            if r.play.value >= 6 and r.roll == 3
            else r
            for r in chart.defense
        ),
    )


def primary_counts(offense, defense, play, formation):
    counts = Counter()
    for black, w1, w2, red, green in product(
        BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES, RED_FACES, GREEN_FACES
    ):
        dice = ScriptedDice(
            [
                OffensiveRoll(black, w1, w2),
                DefensiveRoll(red, green),
                OffensiveRoll(1, 0, 0),
            ]
        )
        result = resolve_play(offense, defense, play, formation, dice)
        counts[result.result.kind.value] += 1
    assert sum(counts.values()) == 216 * 36
    return counts


def terminal_credit_counts(offense, defense, play, formation):
    from bowl_bound.game_state import Possession
    from bowl_bound.statistics import scrimmage_credit

    counts = Counter()
    total_yards = 0
    for black, w1, w2, red, green in product(
        BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES, RED_FACES, GREEN_FACES
    ):
        result = resolve_play(
            offense,
            defense,
            play,
            formation,
            ScriptedDice(
                [OffensiveRoll(black, w1, w2), DefensiveRoll(red, green), OffensiveRoll(1, 0, 0)]
            ),
        )
        credit = scrimmage_credit(result, Possession.HOME, result.result.yards or 0)
        counts[credit.kind.value] += 1
        total_yards += credit.yards
    assert sum(counts.values()) == 216 * 36
    return counts, total_yards


def test_short_prevent_has_actual_completion_benefit_and_long_counterplay():
    offense = team_chart("Ordinary offense", offense=10)
    baseline = flat_defense()
    candidate, _ = apply_event_model(baseline)
    standard = primary_counts(offense, candidate, Play.SIX, Defense.A)
    short = primary_counts(offense, candidate, Play.SIX, Defense.D)
    long = primary_counts(offense, candidate, Play.NINE, Defense.D)
    assert short[ResultKind.INCOMPLETE.value] > standard[ResultKind.INCOMPLETE.value]
    assert long[ResultKind.INCOMPLETE.value] < standard[ResultKind.INCOMPLETE.value]


def test_old_flat_model_is_a_meaningful_negative_control():
    offense = team_chart("Ordinary offense", offense=10)
    chart = flat_defense()
    assert primary_counts(offense, chart, Play.SIX, Defense.A) == primary_counts(
        offense, chart, Play.SIX, Defense.D
    )


def test_protected_unit_int_means_request_six_represented_nine_not_six():
    allocation = joint_allocate(
        (12, 11, 9, 3), (0, 0, 0, 1), (0, 0, 0, 0), (6, 0), baseline=(3, 0), direction=(1, 0)
    )
    assert allocation.represented == (9, 0)
    assert allocation.mass_error == 3
    assert allocation.mean_error == "0"
    assert (6, 0) not in allocation.attainable


def test_individually_possible_three_one_one_is_jointly_impossible():
    # INT is the protected unit row; INC3 and QT1 cannot share that same unit.
    allocation = joint_allocate((12, 11, 9, 3), (0, 0, 0, 1), (0, 0, 0, 0), (3, 1), baseline=(3, 0))
    assert (3, 1) not in allocation.attainable
    assert allocation.mass_error > 0
    assert allocation.represented != (3, 1)


def test_numeric_support_is_not_replaced_with_a_fabricated_zero_mean():
    result = joint_allocate((12, 11), (1, 2), (0, 0), (12, 11), baseline=(12, 11))
    assert result.status == "undefined-numeric-support"
    assert result.assignments is None and result.mean_error is None


def test_a_b_c_and_all_nondefense_and_protected_int_are_exact():
    chart = flat_defense()
    chart = replace(
        chart,
        defense=tuple(
            replace(r, cell=parse_cell("INT 17", provenance()))
            if r.play.value >= 6 and r.roll == 5
            else r
            for r in chart.defense
        ),
    )
    candidate, receipt = apply_event_model(chart)
    for old, new in zip(chart.defense, candidate.defense, strict=True):
        if old.defense in (Defense.A, Defense.B, Defense.C) or old.play.value < 6 or old.roll == 5:
            assert old == new
    for field in ("offense", "supplemental", "special_teams", "pat_outcomes", "recovery_range"):
        assert getattr(chart, field) == getattr(candidate, field)
    assert receipt["model_identity"]["origin"] != "authored-bb-yardage-v1"
    assert receipt["model_identity"] == model_identity()
    assert apply_event_model(chart) == (candidate, receipt)


def test_zero_inc_baseline_reports_saturated_counterplay_not_a_strict_event_pass():
    _, receipt = apply_event_model(team_chart("Zero INC", defense=0))
    d_long = next(r for r in receipt["allocations"] if r["formation"] == "D" and r["play"] == 9)
    assert d_long["saturated"] == (True, False)
    assert d_long["requested_total"][0] == 0


@pytest.mark.parametrize("play", [Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE])
def test_e_reverses_short_and_long_actual_completion_roles(play):
    offense = team_chart("Ordinary offense", offense=10)
    chart, _ = apply_event_model(flat_defense())
    a = primary_counts(offense, chart, play, Defense.A)
    e = primary_counts(offense, chart, play, Defense.E)
    assert (e["incomplete"] - a["incomplete"]) * (1 if play.value >= 8 else -1) > 0


@pytest.mark.parametrize("qt_yards,expected", [(-6, "sack"), (0, "rush"), (5, "rush")])
def test_actual_qt_terminal_credit_uses_sign_not_printed_qt(qt_yards, expected):
    from bowl_bound.game_state import FieldState, Possession
    from bowl_bound.session import PlaySession
    from bowl_bound.statistics import StatKind

    offense = team_chart("Ordinary offense", offense=10)
    offense = replace(
        offense,
        supplemental=tuple(
            replace(r, cell=parse_cell(str(qt_yards), provenance()))
            if r.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else r
            for r in offense.supplemental
        ),
    )
    chart, _ = apply_event_model(flat_defense())
    row = next(
        r
        for r in chart.defense
        if r.defense is Defense.F
        and r.play is Play.SEVEN
        and r.cell.kind is ResultKind.QUARTERBACK_TRAPPED
    )
    pairs = [(r, g) for r in RED_FACES for g in GREEN_FACES if r + g == row.roll]
    # All 216 supplemental outcomes have identical authored numeric facts.
    for black, w1, w2 in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        session = PlaySession.for_analysis(offense, chart, FieldState(Possession.HOME, 50, 1, 10))
        report = session.snap(
            "7",
            "F",
            dice=ScriptedDice(
                [OffensiveRoll(1, 0, 0), DefensiveRoll(*pairs[0]), OffensiveRoll(black, w1, w2)]
            ),
        )
        assert report.statistics.kind is StatKind(expected)
        assert report.statistics.yards == qt_yards
        assert not report.pending


@pytest.mark.parametrize("value", [4, 10, 18])
def test_preserves_offensive_strength_in_fixed_crossed_context(value):
    offense = team_chart("Crossed offense", offense=value)
    chart, _ = apply_event_model(flat_defense())
    # Select an actual numeric branch, without asserting which physical row is numeric.
    numeric = next(
        r
        for r in chart.defense
        if r.defense is Defense.D
        and r.play is Play.SIX
        and r.cell.kind in (ResultKind.YARDS, ResultKind.NO_CHANGE)
    )
    red, green = next((r, g) for r in RED_FACES for g in GREEN_FACES if r + g == numeric.roll)
    result = resolve_play(
        offense,
        chart,
        Play.SIX,
        Defense.D,
        ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(red, green)]),
    )
    assert result.result.yards == value


@pytest.mark.parametrize("play", [Play.SEVEN, Play.NINE])
def test_f_adds_actual_qt_pressure_opportunity_without_int_bonus(play):
    offense = team_chart("Pressure offense", offense=-6)
    chart, receipt = apply_event_model(flat_defense())
    a = primary_counts(offense, chart, play, Defense.A)
    f = primary_counts(offense, chart, play, Defense.F)

    # QT resolves to yards; the consulted supplemental trace proves its origin.
    def qt_mass(formation):
        return sum(
            w
            for w, row in zip(
                (12, 11, 9, 3, 1),
                sorted(
                    (r for r in chart.defense if r.play is play and r.defense is formation),
                    key=lambda r: r.roll,
                ),
                strict=True,
            )
            if row.cell.kind is ResultKind.QUARTERBACK_TRAPPED
        )

    assert qt_mass(Defense.F) > qt_mass(Defense.A)
    assert a.get("interception", 0) == f.get("interception", 0) == 0
    assert (
        next(
            r for r in receipt["allocations"] if r["formation"] == "F" and r["play"] == play.value
        )["represented_total"][1]
        > 0
    )
    a_credit, _ = terminal_credit_counts(offense, chart, play, Defense.A)
    f_credit, _ = terminal_credit_counts(offense, chart, play, Defense.F)
    assert f_credit["sack"] > a_credit["sack"]


@pytest.mark.parametrize("play", [Play.SIX, Play.EIGHT])
def test_f_has_actual_completion_vulnerability_in_counterplays(play):
    offense = team_chart("Counter offense", offense=10)
    chart, _ = apply_event_model(flat_defense())
    a = primary_counts(offense, chart, play, Defense.A)
    f = primary_counts(offense, chart, play, Defense.F)
    assert f["incomplete"] < a["incomplete"]


def test_protected_offense_can_make_printed_defensive_roles_inert():
    chart, _ = apply_event_model(flat_defense())
    offense = team_chart("Protected offense", plays={Play.SIX: parse_cell("(12)", provenance())})
    assert primary_counts(offense, chart, Play.SIX, Defense.A) == primary_counts(
        offense, chart, Play.SIX, Defense.D
    )


def test_crossed_defense_strength_survives_weighted_terminal_credit():
    offense = team_chart("Fixed offense", offense=10)
    weak = flat_defense()
    strong = replace(
        weak,
        defense=tuple(
            replace(r, cell=parse_cell("-3", provenance()))
            if r.cell.kind is ResultKind.YARDS
            else r
            for r in weak.defense
        ),
    )
    weak, _ = apply_event_model(weak)
    strong, _ = apply_event_model(strong)
    weak_credit, weak_yards = terminal_credit_counts(offense, weak, Play.SIX, Defense.D)
    strong_credit, strong_yards = terminal_credit_counts(offense, strong, Play.SIX, Defense.D)
    assert weak_credit == strong_credit
    assert weak_yards - strong_yards == weak_credit["completion"] * 3
