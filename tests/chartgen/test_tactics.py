"""Public tactical priors are synthetic; historical parameters stay private."""

from dataclasses import replace

import pytest

from bowl_bound.models import Defense, Play
from tests.synthetic_teams import team_chart
from tools.chartgen.tactics import TacticalProfile, TacticDelta, learn_tactics


def test_neutral_profile_has_no_tactical_effects() -> None:
    profile = TacticalProfile.neutral()
    assert len(profile.effects) == 54
    assert all(effect.yard_offset == 0 for effect in profile.effects)
    assert TacticalProfile.from_dict(profile.to_dict()) == profile


def test_profile_rejects_team_strength_drift_and_unbounded_values() -> None:
    neutral = TacticalProfile.neutral()
    changed = tuple(
        replace(effect, yard_offset=1) if effect.formation is Defense.B else effect
        for effect in neutral.effects
    )
    with pytest.raises(ValueError, match="centered"):
        TacticalProfile(changed, "synthetic", ())
    with pytest.raises(ValueError, match="bound"):
        TacticDelta(Defense.A, Play.ONE, yard_offset=99)


def test_reference_estimator_retains_roles_but_removes_overall_team_strength() -> None:
    chart = team_chart("Original Fictional")
    changed = replace(
        chart,
        defense=tuple(
            replace(record, cell=replace(record.cell, yards=-3))
            if record.defense is Defense.B
            else record
            for record in chart.defense
        ),
    )
    first = learn_tactics([changed])
    shifted = replace(
        changed,
        defense=tuple(
            replace(record, cell=replace(record.cell, yards=record.cell.yards + 2))
            for record in changed.defense
        ),
    )
    second = learn_tactics([shifted])
    assert first.effects == second.effects
    assert (
        first.lookup(Defense.B, Play.ONE).yard_offset
        < first.lookup(Defense.A, Play.ONE).yard_offset
    )
