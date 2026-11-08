"""Synthetic final-stage tests use the ordinary loader's actual exported data."""

from dataclasses import replace
from fractions import Fraction

import pytest

from bowl_bound.models import Play, ResultKind
from bowl_bound.team_csv import parse_cell, provenance_to_csv, team_from_files, team_to_files
from tests.synthetic_teams import _with_legend_color, metadata, team_chart
from tests.test_chart_depth_policy import Observation
from tests.test_models import provenance
from tools.chart_depth_audit import DepthAuditError
from tools.chart_depth_pipeline import finalize_depth_files


def calibrated_files() -> dict[str, str]:
    chart = team_chart("Synthetic")
    chart = replace(
        chart,
        offense=tuple(
            replace(row, cell=_with_legend_color(parse_cell("INT 44", provenance())))
            if row.play is Play.SIX and row.roll in {10, 18, 39}
            else row
            for row in chart.offense
        ),
        defense=tuple(
            replace(row, cell=_with_legend_color(parse_cell("INT 44", provenance())))
            if row.play is Play.SIX and row.roll == 5
            else row
            for row in chart.defense
        ),
    )
    meta = metadata()
    files = team_to_files(chart, meta)
    files["provenance.csv"] = provenance_to_csv(chart, meta)
    return files


def finalize(files=None, **kwargs):
    return finalize_depth_files(
        calibrated_files() if files is None else files,
        [Observation()],
        [],
        source_sha256="a" * 64,
        parent_model_sha256="b" * 64,
        **kwargs,
    )


def test_final_ordinary_files_fix_both_sides_after_calibration() -> None:
    baseline = calibrated_files()
    files, receipt = finalize(baseline)
    loaded, _ = team_from_files(
        {k: v for k, v in files.items() if k != "provenance.csv"}, files["provenance.csv"]
    )
    assert baseline == calibrated_files()
    for side in ("offense", "defense"):
        depths = [
            r.cell.yards
            for r in getattr(loaded, side)
            if r.play is Play.SIX and r.cell.kind is ResultKind.INTERCEPTION
        ]
        assert depths and set(depths) <= {-3, 0, 3}
    assert receipt["stage_order"][0] == "completed-parent-calibration"
    assert receipt["parent_model_sha256"] == "b" * 64
    assert len(receipt["baseline_file_sha256"]) == 5
    assert receipt["independent_encoding"]["status"] == "PASS-exhaustive"
    assert len(receipt["independent_encoding"]["columns"]) == 28
    assert (
        receipt["independent_policy"]["columns"]["offense/6"]["observed_conditional_samples"] == 0
    )
    assert receipt["historical_fit"] == "UNVERIFIED"
    assert files == finalize()[0]


def test_final_stage_uses_independently_qualified_target_weights() -> None:
    event = Observation(
        called_family=6,
        family_confidence="narrative",
        family_evidence=("text:screen",),
        interception_yards=-8,
    )
    _, receipt = finalize_depth_files(
        calibrated_files(), [event], [], source_sha256="a" * 64, parent_model_sha256="b" * 64
    )
    support = dict(receipt["independent_policy"]["columns"]["offense/6"]["modeled_target"])
    assert {x: Fraction(p) for x, p in support.items()} == {
        -8: Fraction(1, 5),
        -3: Fraction(1, 5),
        0: Fraction(2, 5),
        3: Fraction(1, 5),
    }
    assert (
        receipt["independent_policy"]["columns"]["defense/6"]["observed_conditional_samples"] == 0
    )


def test_unqualified_finite_encoding_cannot_export() -> None:
    with pytest.raises(DepthAuditError, match="unqualified"):
        finalize(enumeration_budget=1)


def test_completed_parent_inventory_and_identity_are_required() -> None:
    files = calibrated_files()
    files.pop("special.csv")
    with pytest.raises(ValueError, match="five"):
        finalize(files)
    with pytest.raises(ValueError, match="SHA256"):
        finalize_depth_files(
            calibrated_files(), [], [], source_sha256="", parent_model_sha256="b" * 64
        )
