"""Synthetic conditional-evidence and finite physical-mass contracts."""

from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product

import pytest

from bowl_bound.models import Play, ResultKind
from bowl_bound.team_csv import parse_cell
from tests.synthetic_teams import team_chart
from tests.test_models import provenance
from tools.chart_depth_policy import apply_depth_policy, encode_depths, location_distribution


@dataclass(frozen=True)
class Observation:
    kind: str = "interception"
    called_family: int | None = None
    family_confidence: str = "unknown"
    interception_yards: int | None = 44
    air_yards: int | None = None
    no_play: bool = False
    family_evidence: tuple[str, ...] = ()


def test_unidentified_and_generic_deep_pass_do_not_establish_designed_call() -> None:
    source = [
        Observation(),
        Observation(
            called_family=9, family_confidence="narrative", family_evidence=("text:long-pass",)
        ),
    ]
    for play in range(6, 10):
        distribution = location_distribution(source, play)
        assert distribution.evidence["observed_conditional_samples"] == 0
        assert 44 not in dict(distribution.support)
        assert distribution.evidence["known_unmatched_call_samples"] == 2


@pytest.mark.parametrize("play,marker,depth", [(6, "screen", -8), (9, "drop-back", 61)])
def test_known_designed_call_retains_real_support_without_universal_cap(
    play: int,
    marker: str,
    depth: int,
) -> None:
    observation = Observation(
        called_family=play,
        family_confidence="narrative",
        interception_yards=depth,
        family_evidence=("text:" + marker,),
    )
    result = location_distribution([observation], play)
    assert dict(result.support)[depth] == Fraction(1, 5)
    assert result.evidence["observed_conditional_samples"] == 1
    other = location_distribution([observation], 7)
    assert other.evidence["observed_conditional_samples"] == 0


def test_missing_voided_and_inferred_are_not_observed_zero() -> None:
    observations = [
        Observation(interception_yards=None),
        Observation(no_play=True),
        Observation(called_family=6, family_confidence="inferred-depth"),
    ]
    result = location_distribution(observations, 6)
    assert result.evidence["unknown_location_samples"] == 1
    assert result.evidence["observed_conditional_samples"] == 0
    assert result.evidence["known_unmatched_call_samples"] == 1
    assert result.evidence["method"] == "authored-prior"


@pytest.mark.parametrize("weights", [(1,), (1, 2), (2, 3, 1), (12, 11, 9, 3, 1)])
def test_finite_encoder_matches_independent_exhaustive_oracle(weights: tuple[int, ...]) -> None:
    support = ((-3, Fraction(1, 4)), (0, Fraction(1, 2)), (3, Fraction(1, 4)))
    values, report = encode_depths(weights, support)

    def cost(candidate: tuple[int, ...]) -> tuple[Fraction, Fraction]:
        errors = [
            abs(
                Fraction(
                    sum(w for x, w in zip(candidate, weights, strict=True) if x <= point),
                    sum(weights),
                )
                - sum(p for x, p in support if x <= point)
            )
            for point, _ in support
        ]
        return (
            sum(error * (support[i + 1][0] - support[i][0]) for i, error in enumerate(errors[:-1])),
            max(errors),
        )

    optimum = min(cost(candidate) for candidate in product((-3, 0, 3), repeat=len(weights)))
    assert cost(values) == optimum
    assert (Fraction(report["wasserstein"]), Fraction(report["cdf_error"])) == optimum


def test_zero_budget_is_dormant_not_imputed() -> None:
    values, report = encode_depths((), location_distribution([], 6).support)
    assert values == ()
    assert report["status"] == "dormant"
    assert report["wasserstein"] is None


def test_both_sides_preserve_every_nondepth_fact_and_source_inputs() -> None:
    original = team_chart("Synthetic")
    original = replace(
        original,
        offense=tuple(
            replace(row, cell=parse_cell("INT 44", provenance()))
            if row.play is Play.SIX and row.roll in {10, 18, 39}
            else row
            for row in original.offense
        ),
        defense=tuple(
            replace(row, cell=parse_cell("INT 44", provenance()))
            if row.play is Play.SIX and row.roll == 5
            else row
            for row in original.defense
        ),
    )
    candidate, report = apply_depth_policy(original, [Observation()], [])
    for side in ("offense", "defense"):
        for before, after in zip(getattr(original, side), getattr(candidate, side), strict=True):
            if before.cell.kind is ResultKind.INTERCEPTION:
                assert after.cell.yards in {-3, 0, 3}
                assert (
                    replace(after.cell, yards=before.cell.yards, provenance=before.cell.provenance)
                    == before.cell
                )
            else:
                assert after == before
    assert report["columns"]["offense"]["6"]["evidence"]["observed_conditional_samples"] == 0
    assert {
        row.cell.yards for row in original.offense if row.cell.kind is ResultKind.INTERCEPTION
    } == {44}


def test_independent_gate_refuses_pooled_screen_and_changed_event_mass() -> None:
    from tools.chart_depth_audit import DepthAuditError, audit_depth_change
    from tools.chart_depth_policy import CONTRACT

    baseline = team_chart("Synthetic")
    baseline = replace(
        baseline,
        offense=tuple(
            replace(row, cell=parse_cell("INT 44", provenance()))
            if row.play is Play.SIX and row.roll == 18
            else row
            for row in baseline.offense
        ),
    )
    with pytest.raises(DepthAuditError, match="unsupported conditional depth"):
        audit_depth_change(baseline, baseline, [Observation()], [], CONTRACT)
    candidate, _ = apply_depth_policy(baseline, [Observation()], [])
    audit = audit_depth_change(baseline, candidate, [Observation()], [], CONTRACT)
    assert audit["physical_offense"] == 216
    assert audit["physical_defense"] == 36
    assert len(audit["pairs"]) == 24
    assert all(pair["physical_pairs"] == 7776 for pair in audit["pairs"].values())
    mutated = replace(
        candidate,
        offense=tuple(
            replace(row, cell=parse_cell("BLACK", provenance()))
            if row.play is Play.SIX and row.roll == 18
            else row
            for row in candidate.offense
        ),
    )
    with pytest.raises(DepthAuditError):
        audit_depth_change(baseline, mutated, [Observation()], [], CONTRACT)


def test_standard_export_rebases_logical_evidence_and_roundtrips_all_facts() -> None:
    from bowl_bound.team_csv import provenance_to_csv, team_from_files, team_to_files
    from tests.synthetic_teams import metadata
    from tools.chart_depth_export import chart_facts, encode_depth_candidate

    unnormalized = team_chart("Synthetic")
    with pytest.raises(ValueError, match="football facts"):
        encode_depth_candidate(
            unnormalized, metadata(), source_sha256="b" * 64, baseline_sha256="c" * 64
        )
    chart, meta = team_from_files(
        team_to_files(unnormalized, metadata()), provenance_to_csv(unnormalized, metadata())
    )
    files, report = encode_depth_candidate(
        chart, meta, source_sha256="b" * 64, baseline_sha256="c" * 64
    )
    loaded, loaded_meta = team_from_files(
        {name: text for name, text in files.items() if name != "provenance.csv"},
        files["provenance.csv"],
    )
    assert chart_facts(loaded) == chart_facts(chart)
    assert loaded_meta.source_sha256 == report["virtual_source_sha256"]
    assert all(
        row.cell.provenance.filename == "generated-bb-call-depth-v1.json" for row in loaded.offense
    )
    assert all(row.cell.provenance.original_text != "INT 44" for row in loaded.offense)
