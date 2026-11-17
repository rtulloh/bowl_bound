"""Independent distribution/semantic diagnostics use original fictional charts."""

from dataclasses import replace
from itertools import product

import pytest

from bowl_bound.dice import BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES, OffensiveRoll
from bowl_bound.models import ChartColor, Play, ResultKind, SpecialTeamsColumn
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import parse_cell
from tests.test_team_csv import chart


@pytest.mark.parametrize("token", ["SOP", "BLP"])
@pytest.mark.parametrize("play", [play for play in Play if play is not Play.FIVE])
def test_option_branch_requires_called_option_column(token: str, play: Play) -> None:
    from tools.chartgen.audit import _placement_issue

    provenance = chart("Cedar Valley").offense[0].cell.provenance
    color = chart_color_for_csv_token(token)
    cell = parse_cell(
        token,
        replace(provenance, original_text=token, rgb_color=CELL_LEGEND[color].rgb_color),
    )
    assert _placement_issue("offense", str(play.value), cell) is not None
    assert _placement_issue("offense", "5", cell) is None


def test_identical_means_cannot_hide_lost_numeric_ranges_and_tails() -> None:
    from tools.chartgen.audit import compare_distributions

    report = compare_distributions({0: 1, 80: 1}, {40: 216})
    assert report["source_mean"] == report["encoded_mean"] == 40
    assert report["max_cdf_error"] == 0.5
    assert report["wasserstein_yards"] == 40
    assert report["missing_support"] == [0, 80]
    assert report["introduced_support"] == [40]
    assert report["missing_lower_tail_mass"] == report["missing_upper_tail_mass"] == 0.5


def test_small_unrepresented_tail_is_reported_without_inventing_an_observation() -> None:
    from tools.chartgen.audit import compare_distributions

    report = compare_distributions({0: 999, 99: 1}, {0: 216})
    assert report["max_cdf_error"] == pytest.approx(0.001)
    assert report["missing_upper_tail_mass"] == pytest.approx(0.001)
    assert report["source_max"] == 99 and report["encoded_max"] == 0
    assert report["missing_support"] == [99]


def test_empty_distribution_is_unidentifiable_not_an_observed_zero() -> None:
    from tools.chartgen.audit import compare_distributions

    report = compare_distributions({}, {0: 216})
    assert report["state"] == "unidentifiable"
    assert report["max_cdf_error"] is None
    assert report["source_mean"] is None


def test_column_comparison_preserves_exact_source_tail_and_pending_scope() -> None:
    from tools.chartgen.audit import ColumnEvidence, compare_column_distributions

    report = {
        "columns": [
            {
                "section": "offense",
                "column": "1",
                "formation": None,
                "numeric_gains": {"4": 200},
                "physical_mass": 216,
            }
        ]
    }
    evidence = ColumnEvidence("offense", "1", None, {4: 799, 99: 1}, "whole numeric PBP")
    result = compare_column_distributions(report, [evidence])[0]
    assert result["source_numeric_masses"] == {"4": 799, "99": 1}
    assert result["distribution"]["missing_upper_tail_mass"] == pytest.approx(1 / 800)
    assert result["distribution"]["source_max"] == 99
    assert result["distribution"]["encoded_max"] == 4
    assert result["encoded_non_numeric_mass"] == 16
    assert result["scope"] == "whole numeric PBP"
    assert "terminal" in result["limitation"]


def test_column_comparison_rejects_missing_or_duplicate_addresses() -> None:
    from tools.chartgen.audit import ColumnEvidence, compare_column_distributions

    evidence = ColumnEvidence("offense", "1", None, {0: 1}, "synthetic")
    with pytest.raises(ValueError, match="missing"):
        compare_column_distributions({"columns": []}, [evidence])
    report = {
        "columns": [
            {
                "section": "offense",
                "column": "1",
                "formation": None,
                "numeric_gains": {"0": 216},
                "physical_mass": 216,
            }
        ]
    }
    with pytest.raises(ValueError, match="duplicate"):
        compare_column_distributions(report, [evidence, evidence])


def test_conditional_location_and_event_rate_loss_remain_separate() -> None:
    from tools.chartgen.audit import ColumnEvidence, compare_column_distributions

    source = ColumnEvidence(
        "offense",
        "1",
        None,
        {4: 100},
        "synthetic",
        locations={"fumble": {-2: 799, 99: 1}},
        kind_probabilities={"fumble": 0.002},
    )
    encoded = {
        "columns": [
            {
                "section": "offense",
                "column": "1",
                "formation": None,
                "numeric_gains": {"4": 215},
                "physical_mass": 216,
                "kinds": {"yards": 215, "fumble": 1},
                "locations": {"fumble": {"-2": 1}},
            }
        ]
    }
    report = compare_column_distributions(encoded, [source])[0]
    location = report["location_distributions"]["fumble"]
    assert location["source_masses"] == {"-2": 799, "99": 1}
    assert location["comparison"]["missing_upper_tail_mass"] == pytest.approx(1 / 800)
    rate = report["kind_probabilities"]["fumble"]
    assert rate["requested"] == 0.002
    assert rate["encoded"] == pytest.approx(1 / 216)
    assert rate["error"] == pytest.approx(1 / 216 - 0.002)


@pytest.mark.parametrize(
    "bad", [{1: -1}, {1: float("nan")}, {True: 1}, {1.5: 1}, {0: 1e308, 1: 1e308}]
)
def test_distribution_comparison_rejects_invalid_mass_or_yardage(bad: dict) -> None:
    from tools.chartgen.audit import compare_distributions

    with pytest.raises(ValueError, match="distribution"):
        compare_distributions(bad, {0: 216})


def test_inventory_uses_engine_physical_rolls_and_retains_priority_color_and_locations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.chartgen import audit

    original = chart("Cedar Valley")
    record = next(r for r in original.offense if r.play is Play.ONE and r.roll == 10)
    altered = replace(
        original,
        offense=tuple(
            replace(r, cell=replace(r.cell, yards=99)) if r is record else r
            for r in original.offense
        ),
    )
    # The audit must not borrow the generator's probability helper.
    monkeypatch.setattr(audit, "offensive_weights", lambda: {10: 216}, raising=False)
    report = audit.audit_chart(altered)
    column = next(c for c in report["columns"] if c["section"] == "offense" and c["column"] == "1")
    expected = sum(
        OffensiveRoll(*faces).total == 10
        for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    assert column["numeric_gains"]["99"] == expected < 216
    assert column["physical_mass"] == sum(column["kinds"].values()) == 216
    assert column["priorities"] and column["colors"]
    assert (
        sum(c["physical_mass"] for c in report["columns"] if c["section"] == "defense") == 54 * 36
    )


def test_semantic_audit_flags_blocked_kick_misplaced_on_a_return_chart() -> None:
    from tools.chartgen.audit import audit_chart

    original = chart("Cedar Valley")
    record = next(r for r in original.special_teams if r.column is SpecialTeamsColumn.PUNT_RETURN)
    altered = replace(
        original,
        special_teams=tuple(
            replace(r, cell=replace(r.cell, kind=ResultKind.BLOCKED_KICK)) if r is record else r
            for r in original.special_teams
        ),
    )
    report = audit_chart(altered)
    assert report["structural_ready"] is False
    assert any(
        issue["section"] == "special_teams"
        and issue["column"] == "punt_return"
        and issue["kind"] == "blocked_kick"
        for issue in report["semantic_issues"]
    )


def test_matching_but_semantically_wrong_color_requires_authoritative_codec_check() -> None:
    from tools.chartgen.audit import audit_chart

    original = chart("Cedar Valley")
    record = original.offense[0]
    wrong = replace(
        record.cell,
        chart_color=ChartColor.YELLOW,
        provenance=replace(record.cell.provenance, rgb_color=(255, 255, 0)),
    )
    altered = replace(original, offense=(replace(record, cell=wrong), *original.offense[1:]))
    report = audit_chart(altered)
    assert not report["structural_ready"]
    assert any(issue["section"] == "bundle" for issue in report["semantic_issues"])
