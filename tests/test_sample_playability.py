"""Playable fictional charts are not exhaustive engine stress fixtures."""

from collections import Counter
from itertools import product

import pytest

from bowl_bound.dice import BLACK_FACES, GREEN_FACES, RED_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES
from bowl_bound.models import (
    Defense,
    PenaltyCode,
    Play,
    ResultKind,
    SpecialTeamsColumn,
    SupplementalColumn,
)
from bowl_bound.resolution import resolve_cells
from bowl_bound.sample_teams import SOURCE_HASH, sample_teams


@pytest.mark.parametrize("index", [0, 1])
def test_running_columns_never_contain_pass_only_results(index: int) -> None:
    team = sample_teams()[index]
    pass_only = {
        ResultKind.INCOMPLETE,
        ResultKind.INTERCEPTION,
        ResultKind.QUARTERBACK_RUN,
        ResultKind.QUARTERBACK_TRAPPED,
    }
    for row in (*team.offense, *team.defense):
        if row.play.value <= Play.FIVE.value:
            assert row.cell.kind not in pass_only, (row.play, row.cell)
            assert row.cell.penalty is None or row.cell.penalty.code is not PenaltyCode.PI
            assert (
                row.cell.kind not in {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS}
                or row.play is Play.FIVE
            )


@pytest.mark.parametrize("index", [0, 1])
def test_playable_samples_have_no_total_roll_losses_or_remote_turnover_locations(
    index: int,
) -> None:
    team = sample_teams()[index]
    for row in (*team.offense, *team.defense):
        assert row.cell.variable is None, row.cell
        if row.cell.yards is not None:
            assert row.cell.yards >= -12, row.cell
        if row.cell.kind is ResultKind.INTERCEPTION:
            assert row.play.value >= Play.SIX.value
            assert row.cell.yards is not None and 0 <= row.cell.yards <= 40
    for row in team.supplemental:
        assert row.cell.yards is not None and -12 <= row.cell.yards <= 60


def test_all_numeric_sample_matchups_have_bounded_net_losses() -> None:
    home, away = sample_teams()
    for offense, defense in ((home, away), (away, home)):
        for attack in offense.offense:
            for defend in defense.defense:
                if attack.play is not defend.play:
                    continue
                result = resolve_cells(attack.cell, defend.cell)
                if result.kind is ResultKind.YARDS and not result.pending:
                    assert result.yards is not None and -12 <= result.yards <= 60


def test_samples_retain_actual_football_events_and_option_pass_branches() -> None:
    for team in sample_teams():
        passing = [r.cell for r in team.offense if r.play.value >= Play.SIX.value]
        assert any(c.kind is ResultKind.INTERCEPTION for c in passing)
        assert any(c.kind is ResultKind.INCOMPLETE for c in passing)
        assert any(c.penalty and c.penalty.code is PenaltyCode.PI for c in passing)
        assert any(r.cell.kind is ResultKind.FUMBLE for r in team.offense)
        assert {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS} <= {
            r.cell.kind for r in team.offense if r.play is Play.FIVE
        }


def test_complete_weighted_primary_matchup_audit() -> None:
    """Audit all 839,808 physical primary lookups, aggregating identical totals."""
    offensive_weights = Counter(
        10 * black + first + second
        for black, first, second in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    defensive_weights = Counter(red + green for red, green in product(RED_FACES, GREEN_FACES))
    assert sum(offensive_weights.values()) == 216
    assert sum(defensive_weights.values()) == 36
    supported = {
        ResultKind.YARDS,
        ResultKind.FUMBLE,
        ResultKind.INTERCEPTION,
        ResultKind.INCOMPLETE,
        ResultKind.PENALTY,
        ResultKind.BREAKAWAY,
        ResultKind.QUARTERBACK_RUN,
        ResultKind.QUARTERBACK_TRAPPED,
        ResultKind.SPRINT_OUT_PASS,
        ResultKind.BOOTLEG_PASS,
    }
    home, away = sample_teams()
    total_cases = 0
    for offense, defense in ((home, away), (away, home)):
        families: Counter[ResultKind] = Counter()
        for play, formation in product(Play, Defense):
            attacks = {r.roll: r.cell for r in offense.offense if r.play is play}
            defenses = {
                r.roll: r.cell for r in defense.defense if r.play is play and r.defense is formation
            }
            assert set(attacks) == set(offensive_weights)
            assert set(defenses) == set(defensive_weights)
            cases = 0
            for attack_roll, defense_roll in product(offensive_weights, defensive_weights):
                result = resolve_cells(attacks[attack_roll], defenses[defense_roll])
                context = (offense.name, play, formation, attack_roll, defense_roll)
                assert result.kind in supported, context
                weight = offensive_weights[attack_roll] * defensive_weights[defense_roll]
                cases += weight
                families[result.kind] += weight
                if play.value <= Play.FIVE.value:
                    assert result.kind not in {
                        ResultKind.INCOMPLETE,
                        ResultKind.INTERCEPTION,
                        ResultKind.QUARTERBACK_RUN,
                        ResultKind.QUARTERBACK_TRAPPED,
                    }, context
                    assert result.penalty is None or result.penalty.code is not PenaltyCode.PI, (
                        context
                    )
                if result.kind is ResultKind.YARDS:
                    assert not result.pending and result.yards is not None, context
                    assert -12 <= result.yards <= 60, context
                if result.kind in {ResultKind.INTERCEPTION, ResultKind.FUMBLE}:
                    assert result.yards is not None and -4 <= result.yards <= 40, context
            assert cases == 216 * 36
            total_cases += cases
        # Broad demo-design sanity, not a claim about calibrated real-team odds.
        count = sum(families.values())
        assert count == 419904
        assert 0.70 < families[ResultKind.YARDS] / count < 0.90
        assert 0 < families[ResultKind.PENALTY] / count < 0.10
        assert 0 < families[ResultKind.INTERCEPTION] / count < 0.05
        assert 0 < families[ResultKind.FUMBLE] / count < 0.10
    assert total_cases == 839808


def test_all_supplemental_special_pat_recovery_and_provenance_values() -> None:
    """Audit all 1,680 installed-recipe entries, including non-scrimmage columns."""
    special_limits = {
        SpecialTeamsColumn.KICKOFF: (45, 75),
        SpecialTeamsColumn.KICKOFF_RETURN: (0, 40),
        SpecialTeamsColumn.PUNT: (25, 60),
        SpecialTeamsColumn.PUNT_RETURN: (-5, 30),
        SpecialTeamsColumn.INTERCEPTION_RETURN: (0, 40),
        SpecialTeamsColumn.FIELD_GOAL: (20, 65),
    }
    supplemental_limits = {
        SupplementalColumn.BREAKAWAY: (10, 60),
        SupplementalColumn.QUARTERBACK_TRAPPED: (-12, 0),
        SupplementalColumn.QUARTERBACK_RUN: (-5, 20),
    }
    entries = 0
    for team in sample_teams():
        for rows, limits in (
            (team.special_teams, special_limits),
            (team.supplemental, supplemental_limits),
        ):
            assert {r.column for r in rows} == set(limits)
            for column, (low, high) in limits.items():
                column_rows = [r for r in rows if r.column is column]
                assert len(column_rows) == 30
                assert {r.roll for r in column_rows} == set(range(10, 40))
                for row in column_rows:
                    assert row.cell.kind is ResultKind.YARDS
                    assert row.cell.yards is not None and low <= row.cell.yards <= high
        assert len(team.pat_outcomes) == 30
        assert {r.roll for r in team.pat_outcomes} == set(range(10, 40))
        assert all(type(r.good) is bool for r in team.pat_outcomes)
        assert any(r.good for r in team.pat_outcomes) and any(not r.good for r in team.pat_outcomes)
        assert team.recovery_range.step == 1
        assert set(team.recovery_range) and set(team.recovery_range) < set(range(10, 40))
        cells = [
            r.cell for r in (*team.offense, *team.defense, *team.supplemental, *team.special_teams)
        ]
        evidence = [c.provenance for c in cells] + [r.provenance for r in team.pat_outcomes]
        assert len(evidence) == 840
        assert all(
            p.source_sha256 == SOURCE_HASH and p.filename == "sample-teams-v2" for p in evidence
        )
        entries += len(evidence)
    assert entries == 1680
