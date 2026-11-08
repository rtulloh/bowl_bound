"""Broad passing-cell controls use only synthetic complete charts."""

import pytest

from bowl_bound.models import Defense, Play
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chart_depth_audit import DepthAuditError, audit_depth_change
from tools.chart_depth_policy import CONTRACT
from tools.chart_passing_audit import (
    GainEnvelope,
    PassingAuditError,
    audit_passing_chart,
    passing_primary_panel,
)


def supports():
    return {
        **{f"offense/{p}": tuple(x for x, _ in CONTRACT["priors"][p]) for p in range(6, 10)},
        **{
            f"defense/{p}/{d.value}": tuple(x for x, _ in CONTRACT["priors"][p])
            for p in range(6, 10)
            for d in Defense
        },
    }


def envelopes():
    evidence = GainEnvelope(-20, 100, 20, 2, "synthetic unidentified complete-play observations")
    return {
        **{f"offense/{p}": evidence for p in range(5, 10)},
        **{f"defense/{p}/{d.value}": evidence for p in range(5, 10) for d in Defense},
        **{f"supplemental/{s}": evidence for s in ("B", "QR")},
        "supplemental/QT/negative": evidence,
        "supplemental/QT/nonnegative": evidence,
    }


def audit(chart):
    return audit_passing_chart(chart, supports(), envelopes())


def test_extreme_pass_gain_cannot_inherit_depth_only_pass() -> None:
    chart = team_chart("Synthetic", plays={Play.SIX: parse_cell("999", provenance())})
    result = audit(chart)
    assert result["status"] == "REVIEW-required"
    assert len([f for f in result["findings"] if f["status"].startswith("REVIEW")]) == 30


def test_long_screen_completion_is_not_an_interception_depth_cap() -> None:
    chart = team_chart("Synthetic", plays={Play.SIX: parse_cell("80", provenance())})
    assert audit_depth_change(chart, chart, [], [], CONTRACT)["status"].startswith("PASS")
    result = audit(chart)
    cell = next(c for c in result["cells"] if c["address"] == "offense/6/10")
    assert cell["status"] == "UNVERIFIED-within-unidentified-source-envelope"
    assert not result["status"].startswith("PASS")


def test_actual_screen_int44_still_fails_the_conditional_support_gate() -> None:
    chart = team_chart("Synthetic", plays={Play.SIX: parse_cell("INT 44", provenance())})
    with pytest.raises(DepthAuditError, match="unsupported conditional depth"):
        audit_depth_change(chart, chart, [], [], CONTRACT)
    with pytest.raises(PassingAuditError, match="unsupported conditional INT depth"):
        audit(chart)


def test_complete_coverage_exact_weights_flags_and_all_family_clusters() -> None:
    result = audit(team_chart("Synthetic", plays={Play.SIX: parse_cell("[5]*", provenance())}))
    assert result["coverage"] == {
        "direct_pass_cells": 240,
        "option_cells": 60,
        "supplemental_cells": 90,
        "scoped_cells": 390,
        "all_family_cluster_cells": 630,
        "columns": 66,
    }
    column = result["columns"]["offense/6"]
    assert column["physical_mass"] == 216
    assert column["numeric_histogram"] == {5: 216}
    assert any("bracketed/OOB=True" in k for k in column["flag_union_mass"])
    assert result["clusters"]["identical_columns"]
    assert result["columns"]["offense/6"]["runs"][0]["start"] == 10
    assert result["columns"]["offense/6"]["runs"][0]["end"] == 39


@pytest.mark.parametrize("value,meaning", [(-3, "sack"), (0, "rush"), (3, "rush")])
def test_qt_signed_terminal_classification_stays_distinct(value, meaning) -> None:
    chart = team_chart("Synthetic", offense=value)
    result = audit(chart)
    cell = next(c for c in result["cells"] if c["address"] == "supplemental/QT/10")
    assert cell["detail"]["meaning"] == meaning
    assert cell["status"].startswith("UNVERIFIED")


@pytest.mark.parametrize("token,target", [("SOP", 7), ("BLP", 8)])
def test_option_continuation_retains_called_and_resolved_play(token, target) -> None:
    result = audit(team_chart("Synthetic", plays={Play.FIVE: parse_cell(token, provenance())}))
    continuations = result["option_continuations"]
    assert len(continuations) == 30
    assert sum(c["offensive_trigger_mass"] for c in continuations) == 216
    assert all(c["called_play"] == 5 and c["resolved_play"] == target for c in continuations)
    assert all(c["continuation_denominator"] == 216 for c in continuations)


def test_missing_evidence_and_unmapped_support_do_not_become_passes() -> None:
    result = audit_passing_chart(team_chart("Synthetic"), supports(), {})
    assert any(f["status"] == "UNVERIFIED-missing-numeric-evidence" for f in result["findings"])
    with pytest.raises(PassingAuditError, match="support inventory"):
        audit_passing_chart(team_chart("Synthetic"), {}, {})


def test_invalid_future_semantic_kind_cannot_silently_enter_census() -> None:
    chart = team_chart("Synthetic")
    # Emulate an unvalidated future deserializer, without extending valid model grammar.
    object.__setattr__(chart.offense[0].cell, "kind", "unmapped")
    with pytest.raises(PassingAuditError, match="unmapped scrimmage token"):
        audit(chart)


def test_primary_panel_uses_all_physical_mass_and_refuses_bad_oracle() -> None:
    chart = team_chart("Synthetic")
    # All subjects are synthetic normal numeric4 + numeric3. This literal
    # independent expectation keeps the public fixture self-contained.
    expected = {
        "operation": "ADD",
        "source": "both",
        "kind": "yards",
        "yards": 7,
        "pending": False,
        "out_of_bounds": False,
        "penalty": None,
        "defensive_end_zone_depth": None,
    }
    result = passing_primary_panel(chart, chart, expected_priority=lambda a, b: expected)
    assert result["contexts"] == 30
    assert result["address_pairs"] == 4500
    assert all(r["physical_mass"] == 7776 for r in result["results"].values())
    with pytest.raises(ValueError, match="independent priority mismatch"):
        passing_primary_panel(chart, chart, expected_priority=lambda a, b: {})


@pytest.mark.parametrize("args", [(0, 1, 0, 0, "none"), (3, 1, 1, 0, "reversed")])
def test_empty_or_reversed_source_envelopes_are_not_zero_evidence(args) -> None:
    with pytest.raises(PassingAuditError):
        GainEnvelope(*args)
