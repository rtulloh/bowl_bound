"""Independent finite-encoding qualification uses synthetic charts only."""

from dataclasses import replace
from fractions import Fraction

import pytest

from bowl_bound.models import Play
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chart_depth_audit import DepthAuditError, audit_depth_change
from tools.chart_depth_encoding_audit import audit_chart_encoding, audit_slot_encoding
from tools.chart_depth_policy import CONTRACT, apply_depth_policy


def targets():
    distributions = {
        play: tuple((x, Fraction(w)) for x, w in support)
        for play, support in CONTRACT["priors"].items()
    }
    return {
        **{f"offense/{play}": support for play, support in distributions.items()},
        **{
            f"defense/{play}/{formation}": support
            for play, support in distributions.items()
            for formation in "ABCDEF"
        },
    }


def test_supported_but_collapsed_distribution_is_refused() -> None:
    chart = team_chart("Synthetic")
    chart = replace(
        chart,
        offense=tuple(
            replace(row, cell=parse_cell("INT 0", provenance()))
            if row.play is Play.SIX and row.roll in {10, 18, 39}
            else row
            for row in chart.offense
        ),
    )
    # The older support/incidence gate accepts this mutation; the new gate
    # independently refuses its distribution, without weakening that earlier gate.
    audit_depth_change(chart, chart, [], [], CONTRACT)
    with pytest.raises(DepthAuditError, match="finite encoding"):
        audit_chart_encoding(chart, targets())
    corrected, _ = apply_depth_policy(chart, [], [])
    assert audit_chart_encoding(corrected, targets())["status"] == "PASS-exhaustive"


def test_exhaustive_tails_dormancy_and_budget_remain_explicit() -> None:
    support = ((-3, Fraction(1, 4)), (0, Fraction(1, 2)), (3, Fraction(1, 4)))
    result = audit_slot_encoding((1, 2, 1), (-3, 0, 3), support)
    assert result["wasserstein"] == result["cdf_error"] == "0"
    assert result["assignments"] == 27
    single = audit_slot_encoding((1,), (0,), support)
    assert single["omitted_support"] == (-3, 3)
    assert single["wasserstein"] == "3/2"
    assert audit_slot_encoding((), (), support)["status"] == "dormant"
    limited = audit_slot_encoding((1, 2, 1), (-3, 0, 3), support, enumeration_budget=26)
    assert limited["status"] == "UNVERIFIED-enumeration-budget"
    with pytest.raises(DepthAuditError, match="target inventory"):
        audit_chart_encoding(team_chart("Synthetic"), {})
