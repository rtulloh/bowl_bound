"""Synthetic complete-bundle, physical-probability and safety contracts."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from bowl_bound.models import Play, ResultKind, TeamChart
from bowl_bound.team_csv import load_team, provenance_to_csv, team_from_files, team_to_files
from tools.chartgen.evidence import Event
from tools.chartgen.generate import (
    CalibrationProfile,
    defensive_weights,
    generate_team,
    nearest_mass_rows,
    offensive_weights,
    write_bundle,
)


@pytest.fixture
def events() -> list[Event]:
    output = []
    for team, opponent, name in [("1", "2", "Cedar Valley"), ("2", "1", "Harbor Tech")]:
        for i in range(360):
            kind = ["rush", "rush", "complete", "complete", "incomplete", "sack"][i % 6]
            yards = (i % 19) - 3 if kind in {"rush", "complete"} else -6 if kind == "sack" else None
            output.append(
                Event(
                    2007,
                    f"g{i // 90}",
                    f"{team}-{i}",
                    team,
                    opponent,
                    name,
                    "Opponent",
                    kind,
                    yards,
                    fumble=i % 91 == 0,
                    fumble_team=team if i % 91 == 0 else None,
                    fumble_lost=i % 2 == 0 if i % 91 == 0 else None,
                )
            )
        for kind, yards in [
            ("punt", 42),
            ("kickoff", 60),
            ("field_goal", 35),
            ("pat", None),
            ("interception", None),
        ]:
            for i in range(30):
                output.append(
                    Event(
                        2007,
                        f"g{i // 8}",
                        f"{team}-{kind}-{i}",
                        team,
                        opponent,
                        name,
                        "Opponent",
                        kind,
                        yards,
                        return_yards=i % 17,
                        kick_good=i % 7 != 0,
                        fumble=False,
                        interception_yards=12 if kind == "interception" else None,
                    )
                )
    return output


def test_physical_dice_weights_and_rare_rate() -> None:
    assert sum(offensive_weights().values()) == 216
    assert sum(defensive_weights().values()) == 36
    selected = nearest_mass_rows(offensive_weights(), 1 / 216, seed=7)
    assert sum(offensive_weights()[r] for r in selected) == 1
    assert offensive_weights()[10] != offensive_weights()[35]


def test_normalized_cross_drive_fumble_supplies_return_chart_evidence(events: list[Event]) -> None:
    from tests.test_audit_espn_fumbles import return_pair
    from tools.chartgen.espn_core import normalize_game

    rows = return_pair()
    rows[0]["start"]["team"]["$ref"] = "https://example.test/teams/2"
    rows[0]["statYardage"] = 25
    rows[1]["team"] = {"$ref": "https://example.test/teams/2"}
    normalized, _ = normalize_game(
        rows,
        season=2007,
        game_id="linked",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    # Synthetic gross kick evidence allows this test to reach return generation.
    normalized[0] = replace(normalized[0], yards=60)
    _, _, report = generate_team([*events, *normalized], "1", "Cedar Valley", 2007, seed=19)
    evidence = report["special_evidence"]["kickoff_return"]
    assert evidence["fumbles"] == 1
    assert evidence["fumble_probability_unidentified"] is False


def test_positive_only_oob_mentions_use_matching_ordinary_outcomes(events: list[Event]) -> None:
    """Sparse positive evidence cannot become certainty after dropping unknowns."""
    indexes = {"rush": 0, "complete": 0}
    selected = []
    for event in events:
        bounds = None
        if event.team == "1" and event.kind in indexes:
            indexes[event.kind] += 1
            interval = 10 if event.kind == "rush" else 4
            bounds = True if indexes[event.kind] % interval == 0 else None
        # An OOB mention on another outcome cannot inflate ordinary completions.
        if event.team == "1" and event.kind == "incomplete":
            bounds = True
        selected.append(replace(event, out_of_bounds=bounds))
    generated, _, manifest = generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    weights = offensive_weights()
    for play in Play:
        kind = "rush" if play.value <= 5 else "complete"
        source = [
            e
            for e in selected
            if e.team == "1" and e.kind == kind and e.yards is not None and not e.fumble
        ]
        requested = sum(e.out_of_bounds is True for e in source) / len(source)
        numeric = [
            r
            for r in generated.offense
            if r.play is play and r.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}
        ]
        mass = sum(weights[r.roll] for r in numeric)
        marked = sum(weights[r.roll] for r in numeric if r.cell.out_of_bounds)
        attainable = {0}
        for row in numeric:
            attainable |= {value + weights[row.roll] for value in attainable}
        assert abs(marked - requested * mass) == pytest.approx(
            min(abs(value - requested * mass) for value in attainable)
        )
        evidence = manifest["family_evidence"][str(play.value)]["out_of_bounds_evidence"]
        assert evidence["requested_numeric_probability"] == pytest.approx(requested)
        assert evidence["unknown_observations"] > 0
        assert evidence["state"] == "partial-positive-evidence"


def test_supplemental_oob_uses_tail_sack_and_proxy_supports(events: list[Event]) -> None:
    selected = [
        replace(e, out_of_bounds=e.yards >= 12 if e.kind == "rush" else False)
        if e.team == "1" and e.yards is not None
        else e
        for e in events
    ]
    generated, _, manifest = generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    numeric = {
        column: [
            r.cell
            for r in generated.supplemental
            if r.column.value == column and r.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}
        ]
        for column in ("B", "QT", "QR")
    }
    assert numeric["B"] and all(c.out_of_bounds for c in numeric["B"])
    assert numeric["QT"] and not any(c.out_of_bounds for c in numeric["QT"])
    evidence = manifest["supplemental_evidence"]
    assert evidence["B"]["out_of_bounds_evidence"]["requested_numeric_probability"] == 1
    assert evidence["QT"]["out_of_bounds_evidence"]["requested_numeric_probability"] == 0
    assert evidence["QR"]["out_of_bounds_evidence"]["support"] == "dormant-rush-proxy"


def test_qr_oob_does_not_borrow_other_rush_or_pass_outcomes(events: list[Event]) -> None:
    selected = [
        replace(e, quarterback_scramble=e.yards == 4, out_of_bounds=e.yards != 4)
        if e.team == "1" and e.kind == "rush"
        else e
        for e in events
    ]
    generated, _, manifest = generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    numeric = [
        r.cell
        for r in generated.supplemental
        if r.column.value == "QR" and r.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}
    ]
    assert numeric and not any(c.out_of_bounds for c in numeric)
    report = manifest["supplemental_evidence"]["QR"]["out_of_bounds_evidence"]
    assert report["requested_numeric_probability"] == 0
    assert report["support"] == "team-PBP"


def test_missing_qt_support_never_borrows_rush_oob_evidence(
    events: list[Event], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import generate

    selected = [e for e in events if e.kind != "sack"]
    supports = []
    original = generate._out_of_bounds_evidence

    def capture(records: Any) -> Any:
        supports.append(tuple(records))
        return original(records)

    monkeypatch.setattr(generate, "_out_of_bounds_evidence", capture)
    # Existing generation correctly refuses a QT column with no numeric evidence.
    # Its dormant OOB diagnostic must not first inspect an unrelated rush proxy.
    with pytest.raises(ValueError, match="numeric distribution has no known evidence"):
        generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    assert supports[-1] == ()


@pytest.mark.parametrize("rare", [-99, 99])
def test_generation_exposes_rare_tail_before_integration(events: list[Event], rare: int) -> None:
    base = [replace(e, yards=4) if e.kind == "rush" else e for e in events]
    base = [e for e in base if not (e.team == "1" and e.kind == "rush")]
    base.extend(
        Event(
            2007,
            "synthetic",
            f"rare-{i}",
            "1",
            "2",
            "Cedar Valley",
            "Harbor Tech",
            "rush",
            rare if i == 799 else 4,
            fumble=False,
        )
        for i in range(800)
    )
    _, _, manifest = generate_team(base, "1", "Cedar Valley", 2007, seed=19)
    report = manifest["family_evidence"]["1"]["distribution_audit"]
    assert report["source_numeric_masses"] == {"4": 799, str(rare): 1}
    endpoint = "source_min" if rare < 4 else "source_max"
    tail = "missing_lower_tail_mass" if rare < 4 else "missing_upper_tail_mass"
    assert report["distribution"][endpoint] == rare
    assert report["distribution"]["encoded_max"] == 4
    assert report["distribution"][tail] == pytest.approx(1 / 800)
    assert report["scope"].startswith("PBP-only")


def test_generation_audits_source_locations_and_applicable_numeric_columns(
    events: list[Event],
) -> None:
    _, _, manifest = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
    reports = manifest["source_distribution_audits"]
    addresses = {(r["section"], r["column"]) for r in reports}
    assert len(reports) == 18
    assert len([r for r in reports if r["section"] == "offense"]) == 9
    assert len([r for r in reports if r["section"] == "supplemental"]) == 3
    assert len([r for r in reports if r["section"] == "special_teams"]) == 6
    assert ("supplemental", "QT") in addresses
    pass_report = next(r for r in reports if (r["section"], r["column"]) == ("offense", "6"))
    assert pass_report["location_distributions"]["interception"]["source_masses"] == {"12": 30}
    assert pass_report["kind_probabilities"]["interception"]["requested"] > 0
    assert manifest["defensive_distribution_audit"]["state"] == "unidentifiable"
    assert "formation" in manifest["defensive_distribution_audit"]["reason"]


@pytest.mark.parametrize(
    "response,kind,ordinary,extreme", [("QT", "sack", -3, -80), ("QR", "rush", 2, 80)]
)
def test_supplemental_fumble_only_location_cannot_become_ordinary_gain(
    events: list[Event], response: str, kind: str, ordinary: int, extreme: int
) -> None:
    selected = [e for e in events if not (e.team == "1" and e.kind == kind)]
    selected.extend(
        Event(
            2007,
            "synthetic",
            f"conditional-{i}",
            "1",
            "2",
            "Cedar Valley",
            "Harbor Tech",
            kind,
            extreme if i >= 80 else ordinary,
            fumble=i >= 80,
            fumble_team="1" if i >= 80 else None,
            recovery_team="1" if i >= 80 else None,
            quarterback_scramble=True if response == "QR" else None,
        )
        for i in range(100)
    )
    generated, _, manifest = generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    cells = [r.cell for r in generated.supplemental if r.column.value == response]
    assert {c.yards for c in cells if c.kind is ResultKind.YARDS} == {ordinary}
    assert {c.yards for c in cells if c.kind is ResultKind.FUMBLE} == {extreme}
    report = next(
        r
        for r in manifest["source_distribution_audits"]
        if r["section"] == "supplemental" and r["column"] == response
    )
    assert report["source_numeric_masses"] == {str(ordinary): 80}
    assert report["location_distributions"]["fumble"]["source_masses"] == {str(extreme): 20}


def test_return_fumble_only_location_cannot_become_ordinary_return(events: list[Event]) -> None:
    selected = [
        replace(
            e,
            return_yards=99 if i % 5 == 0 else 5,
            fumble=i % 5 == 0,
            fumble_team="1" if i % 5 == 0 else None,
            recovery_team="1" if i % 5 == 0 else None,
        )
        if e.team == "2" and e.kind == "punt"
        else e
        for i, e in enumerate(events)
    ]
    generated, _, _ = generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    cells = [r.cell for r in generated.special_teams if r.column.value == "punt_return"]
    assert {c.yards for c in cells if c.kind is ResultKind.YARDS} == {5}
    assert {c.yards for c in cells if c.kind is ResultKind.FUMBLE} == {99}


def test_all_fumble_column_needs_no_fabricated_ordinary_numeric_sample() -> None:
    from tools.chartgen.generate import _column

    result = _column([], [("F", 1.0)], seed=19, locations={"F": [-6]})
    assert set(result.values()) == {"F - 6"}
    with pytest.raises(ValueError, match="numeric distribution has no known evidence"):
        _column([], [("F", 0.5)], seed=19, locations={"F": [-6]})


def test_all_fumble_family_does_not_claim_ordinary_evidence(events: list[Event]) -> None:
    selected = [
        *events,
        *[
            Event(
                2007,
                "synthetic",
                f"all-F-{i}",
                "1",
                "2",
                "Cedar Valley",
                "Harbor Tech",
                "rush",
                13,
                called_family=1,
                family_confidence="narrative",
                fumble=True,
                fumble_team="1",
                recovery_team="1",
            )
            for i in range(30)
        ],
    ]
    generated, _, manifest = generate_team(selected, "1", "Cedar Valley", 2007, seed=19)
    assert all(r.cell.kind is ResultKind.FUMBLE for r in generated.offense if r.play is Play.ONE)
    report = manifest["family_evidence"]["1"]["distribution_audit"]
    assert report["source_numeric_masses"] == {}
    with pytest.raises(ValueError, match="numeric distribution has no known evidence"):
        generate_team(
            selected,
            "1",
            "Cedar Valley",
            2007,
            seed=19,
            profile=CalibrationProfile(fumble_scale=0.6),
        )


def test_complete_bundle_roundtrip_determinism(events: list[Event]) -> None:
    first = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
    second = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
    assert first == second
    chart, metadata, manifest = first
    restored, _ = team_from_files(
        team_to_files(chart, metadata), provenance_to_csv(chart, metadata)
    )
    assert restored == chart
    assert (
        len(chart.offense) + len(chart.defense) + len(chart.supplemental) + len(chart.special_teams)
        == 810
    )
    assert len(chart.pat_outcomes) == 30
    assert manifest["tactical_evidence"] == "inferred-neutral"
    assert manifest["source_sha256"] == metadata.source_sha256
    assert all(c.cell.kind is not ResultKind.TOUCHDOWN for c in chart.offense)
    # A complete bundle no longer fabricates option branches absent from PBP.
    assert manifest["mechanics"]["option_SOP_BLP"] is False
    assert manifest["modeled_priors"]["option_SOP_probability"] == 0
    assert manifest["modeled_priors"]["option_BLP_probability"] == 0


def test_generation_retains_independent_semantic_audit_and_checksum(
    tmp_path: Path, events: list[Event]
) -> None:
    import hashlib
    import json

    bundle = generate_team(events, "1", "Cedar Valley", 2007)
    root = tmp_path / "private-data" / "audited"
    write_bundle(root, bundle)
    report = json.loads((root / "generation-audits" / "2007-cedar-valley.json").read_text())
    assert report["structural_ready"] and not report["semantic_issues"]
    digest = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert bundle[2]["chart_audit"]["semantic_sha256"] == digest
    assert report["play_formation_pairs"] == 54


def test_generation_rejects_a_serializable_but_misplaced_ordinary_cell(
    events: list[Event], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import generate

    original = generate._cell

    def misplaced(token: str, source_hash: str, filename: str, row: int, column: int) -> Any:
        return original("BK 3" if column == 1 else token, source_hash, filename, row, column)

    monkeypatch.setattr(generate, "_cell", misplaced)
    with pytest.raises(ValueError, match="semantic audit"):
        generate_team(events, "1", "Cedar Valley", 2007)


@pytest.mark.parametrize(
    "directory", ["2007", "2007/provenance", "generation-manifests", "generation-audits"]
)
def test_bundle_preflights_child_directories_before_private_output(
    tmp_path: Path, events: list[Event], directory: str
) -> None:
    root = tmp_path / "private-data" / "candidate"
    linked = root / directory
    linked.parent.mkdir(parents=True)
    external = tmp_path / "outside"
    external.mkdir()
    linked.symlink_to(external, target_is_directory=True)
    bundle = generate_team(events, "1", "Cedar Valley", 2007)
    with pytest.raises(ValueError, match="symlink"):
        write_bundle(root, bundle)
    assert list(external.iterdir()) == []
    assert not (root / "2007" / "cedar-valley").exists()


def test_cached_evidence_model_preserves_outputs_and_fits_once(
    events: list[Event], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import generate

    expected = [
        generate_team(events, team, name, 2007, seed=19)
        for team, name in [("1", "Cedar Valley"), ("2", "Harbor Tech")]
    ]
    original = generate._source
    calls = []

    def source_once(sample: list[Event]) -> tuple[str, str]:
        calls.append(len(sample))
        assert len(calls) == 1, "batch must not repeatedly encode full evidence"
        return original(sample)

    monkeypatch.setattr(generate, "_source", source_once)
    model = generate.EvidenceModel.from_events(events)
    actual = [
        generate_team(model.events, team, name, 2007, seed=19, model=model)
        for team, name in [("1", "Cedar Valley"), ("2", "Harbor Tech")]
    ]
    assert actual == expected and len(calls) == 1
    with pytest.raises(ValueError, match="model.*evidence"):
        generate_team(events[:-1], "1", "Cedar Valley", 2007, model=model)


def test_cached_vectors_preserve_no_play_penalty_evidence(events: list[Event]) -> None:
    from tools.chartgen.generate import EvidenceModel

    foul = replace(
        events[0], event_id="no-play-foul", kind="penalty", yards=None, penalty=True, no_play=True
    )
    model = EvidenceModel.from_events([*events, foul])
    assert foul in model.empirical_by_team["1"].penalties
    assert foul not in model.by_team["1"]


def test_sparse_fallback_covers_full_distribution_independent_of_source_order() -> None:
    from statistics import mean

    from tools.chartgen.generate import _pool

    source = [
        Event(2007, "g", str(i), "x", "y", "X", "Y", "rush", yards)
        for i, yards in enumerate([0] * 30 + [100] * 30)
    ]
    first = _pool([], source, "rush", {})
    second = _pool([], source[::-1], "rush", {})
    assert first == second
    assert min(first) == 0 and max(first) == 100 and mean(first) == 50


def test_batch_preserves_every_requested_team_and_refuses_overwrite(
    tmp_path: Path, events: list[Event]
) -> None:
    from tools.chartgen.batch import generate_cohort

    root = tmp_path / "private-data" / "cohort"
    names = {"1": "Cedar Valley", "2": "Harbor Tech", "missing": "Pine College"}
    result = generate_cohort(events, names, 2007, root, seed=19)
    assert set(result["teams"]) == set(names)
    assert result["teams"]["1"]["state"] == "generated"
    assert result["teams"]["missing"]["state"] == "unidentifiable"
    assert "no source events" in result["teams"]["missing"]["reason"]
    chart, _ = load_team(root / "2007", "cedar-valley")
    assert chart == generate_team(events, "1", "Cedar Valley", 2007, seed=19)[0]
    with pytest.raises(ValueError, match="new"):
        generate_cohort(events, names, 2007, root)


def test_missing_run_evidence_is_not_silently_zero(events: list[Event]) -> None:
    missing = [replace(e, yards=None) if e.kind == "rush" else e for e in events]
    with pytest.raises(ValueError, match="rush yardage"):
        generate_team(missing, "1", "Cedar Valley", 2007)


def test_profile_bounds_are_checked_before_generation() -> None:
    with pytest.raises(ValueError, match="bound"):
        CalibrationProfile(run_yards_scale=12)
    with pytest.raises(ValueError, match="finite"):
        CalibrationProfile(pass_yards_scale=float("nan"))


def test_private_output_no_overwrite_and_loadable(tmp_path: Path, events: list[Event]) -> None:
    bundle = generate_team(events, "1", "Cedar Valley", 2007)
    destination = tmp_path / "private-data" / "candidate"
    write_bundle(destination, bundle)
    chart, _ = load_team(destination / "2007", "cedar-valley")
    assert chart == bundle[0]
    with pytest.raises(FileExistsError):
        write_bundle(destination, bundle)
    with pytest.raises(ValueError, match="private-data"):
        write_bundle(tmp_path / "public", bundle)


def test_symlink_output_rejected(tmp_path: Path, events: list[Event]) -> None:
    private = tmp_path / "private-data"
    private.mkdir()
    (private / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        write_bundle(
            private / "link" / "candidate", generate_team(events, "1", "Cedar Valley", 2007)
        )


def test_generated_charts_complete_real_engine_games(tmp_path: Path, events: list[Event]) -> None:
    from tools.chartgen.refine import run_batch

    teams = {}
    for team, name in [("1", "Cedar Valley"), ("2", "Harbor Tech")]:
        bundle = generate_team(events, team, name, 2007, seed=23)
        teams[f"2007/{name.lower().replace(' ', '-')}"] = bundle[:2]
    report = run_batch(teams, [817, 991], tmp_path / "private-data" / "batch")
    assert report["failed_games"] == 0
    assert report["passed_games"] == 2
    assert report["team_games"] == {"2007/cedar-valley": 2, "2007/harbor-tech": 2}
    assert report["metrics"]["completion"]["n"] > 0
    assert report["call_distribution"]
    assert report["metrics"]["drawn_punt_yards"]["n"] > 0
    assert report["metrics"]["drawn_punt_return_yards"]["n"] > 0


def test_defensive_outcome_strength_is_separate_from_offense(events: list[Event]) -> None:
    strengthened = events + [
        Event(
            2007,
            f"x{i // 90}",
            f"extra-{i}",
            "3",
            "1",
            "Synthetic",
            "Cedar Valley",
            "incomplete",
            None,
        )
        for i in range(600)
    ]
    chart, _, manifest = generate_team(strengthened, "1", "Cedar Valley", 2007)
    assert any(c.cell.kind is ResultKind.INCOMPLETE for c in chart.defense if c.play.value >= 6)
    assert manifest["opponent_model"]["rate_effects"]["completion"] < 0


def test_probability_audit_covers_every_physical_pair(events: list[Event]) -> None:
    from tools.chartgen.audit import audit_chart

    chart, _, _ = generate_team(events, "1", "Cedar Valley", 2007)
    report = audit_chart(chart)
    assert report["physical_offensive_combinations"] == 216
    assert report["physical_defensive_combinations"] == 36
    assert report["play_formation_pairs"] == 54
    assert all(sum(pair["outcome_masses"].values()) == 216 * 36 for pair in report["pairs"])


def test_family_specific_yardage_obeys_recorded_calibration(events: list[Event]) -> None:
    # Keep unidentified runs for the other sparse families instead of silently
    # relabelling a different known call as their evidence.
    explicit = [
        replace(e, called_family=1)
        if e.kind == "rush" and int(e.event_id.split("-")[-1]) < 120
        else e
        for e in events
    ]
    neutral = generate_team(explicit, "1", "Cedar Valley", 2007, seed=71)[0]
    scaled = generate_team(
        explicit,
        "1",
        "Cedar Valley",
        2007,
        seed=71,
        profile=CalibrationProfile(run_yards_scale=1.4),
    )[0]

    def total(chart: TeamChart) -> int:
        return sum(c.cell.yards or 0 for c in chart.offense if c.play is Play.ONE)

    assert total(scaled) > total(neutral)


def test_known_other_call_cannot_fill_an_unidentified_family(events: list[Event]) -> None:
    evidence = [replace(e, called_family=1) if e.kind == "rush" else e for e in events]
    with pytest.raises(ValueError, match="play 2 rush evidence"):
        generate_team(evidence, "1", "Cedar Valley", 2007)


def test_two_phase_refinement_retains_baseline_and_heldout(
    tmp_path: Path, events: list[Event]
) -> None:
    from tools.chartgen.refine import SeedPlan, run_refinement

    output = tmp_path / "private-data" / "refinement"
    plan = SeedPlan(817, 2, 2)
    report = run_refinement(
        events,
        {"1": "Cedar Valley", "2": "Harbor Tech"},
        2007,
        output,
        seed_plan=plan,
        iterations=1,
    )
    assert report["mechanics_ready"]
    assert not report["heldout_assessment"]["passed"]
    assert report["historical_fit_claim"] is False
    assert report["training_history"][0]["summary"]["seeds"] == list(plan.training)
    assert report["heldout"]["seeds"] == list(plan.validation)
    assert (output / "candidate-00" / "2007" / "cedar-valley" / "offense.csv").is_file()
    assert (output / "selected-profile.json").is_file()
    assert all(a["save_continuation_verified"] for a in report["save_replay_audits"])


def test_observed_return_fumbles_are_supported(events: list[Event]) -> None:
    risky = [
        replace(e, fumble=True, fumble_lost=True, fumble_team=e.opponent) if e.kind == "punt" else e
        for e in events
    ]
    chart, _, manifest = generate_team(risky, "1", "Cedar Valley", 2007)
    assert any(
        c.cell.kind is ResultKind.FUMBLE
        for c in chart.special_teams
        if c.column.value == "punt_return"
    )
    assert manifest["special_evidence"]["punt_return"]["fumbles"] > 0


def test_private_output_cannot_escape_with_parent_traversal(
    tmp_path: Path, events: list[Event]
) -> None:
    with pytest.raises(ValueError, match="private-data"):
        write_bundle(
            tmp_path / "private-data" / ".." / "public",
            generate_team(events, "1", "Cedar Valley", 2007),
        )
    assert not (tmp_path / "public").exists()


def test_compatible_pass_tails_preserve_full_completion_distribution(events: list[Event]) -> None:
    from collections import Counter

    from bowl_bound.models import SupplementalColumn

    chart, _, manifest = generate_team(events, "1", "Cedar Valley", 2007)
    weights = offensive_weights()
    source = [e.yards for e in events if e.team == "1" and e.kind == "complete"]
    for play in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
        gains: Counter[int] = Counter()
        for record in chart.offense:
            if record.play is not play:
                continue
            if record.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}:
                gains[record.cell.yards or 0] += weights[record.roll]
            elif record.cell.kind is ResultKind.BREAKAWAY:
                for extra in chart.supplemental:
                    if extra.column is SupplementalColumn.BREAKAWAY:
                        gains[extra.cell.yards or 0] += (
                            weights[record.roll] * weights[extra.roll] / 216
                        )
        assert min(gains) >= min(source) and max(gains) <= max(source)
        total = sum(gains.values())
        error = max(
            abs(
                sum(m for y, m in gains.items() if y <= point) / total
                - sum(y <= point for y in source) / len(source)
            )
            for point in set(source) | gains.keys()
        )
        # Quantizing two conditional columns may move at most two physical rows.
        assert error <= 2 * max(weights.values()) / total
    assert "compatible" in manifest["modeled_priors"]["breakaway_tail_method"]


def test_observed_zero_run_is_white_no_change_for_qb_sneak(events: list[Event]) -> None:
    from itertools import product

    from bowl_bound.dice import (
        BLACK_FACES,
        WHITE_ONE_FACES,
        WHITE_TWO_FACES,
        OffensiveRoll,
        ScriptedDice,
    )
    from bowl_bound.resolution import resolve_qb_sneak

    zero_runs = [replace(e, yards=0) if e.kind == "rush" else e for e in events]
    chart, _, _ = generate_team(zero_runs, "1", "Cedar Valley", 2007)
    blank = next(
        (c for c in chart.offense if c.play is Play.ONE and c.cell.kind is ResultKind.NO_CHANGE),
        None,
    )
    assert blank is not None
    faces = next(
        f
        for f in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
        if OffensiveRoll(*f).total == blank.roll
    )
    result = resolve_qb_sneak(
        chart, None, ScriptedDice([OffensiveRoll(*faces)]), free_wildcard=False
    )
    assert result.result.yards == 0


def test_centered_tactics_make_formations_distinct_without_changing_offense(
    events: list[Event],
) -> None:
    from tools.chartgen.tactics import TacticalProfile

    neutral = TacticalProfile.neutral()
    effects = tuple(
        replace(
            effect,
            yard_offset=1
            if effect.formation.value == "A"
            else -1
            if effect.formation.value == "B"
            else 0,
        )
        for effect in neutral.effects
    )
    tactical = TacticalProfile(effects, "synthetic", ())
    first = generate_team(events, "1", "Cedar Valley", 2007)
    second = generate_team(events, "1", "Cedar Valley", 2007, tactics=tactical)
    assert first[0].offense == second[0].offense
    assert first[0].defense != second[0].defense
    assert second[2]["tactical_profile"]["sha256"] == tactical.sha256
    assert sum(effect.yard_offset for effect in tactical.effects) == 0


def test_real_refinement_consumes_complete_phase_readiness(
    tmp_path: Path, events: list[Event]
) -> None:
    import sys

    import tools.chartgen.refine as refine
    from tools.chartgen.readiness import refinement_phase_status

    observed = []

    def observe(frame: Any, event: str, argument: Any) -> None:
        if event == "return" and frame.f_code is refinement_phase_status.__code__:
            observed.append(argument)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        report = refine.run_refinement(
            events,
            {"1": "Cedar Valley", "2": "Harbor Tech"},
            2007,
            tmp_path / "private-data" / "complete-phases",
            seed_plan=refine.SeedPlan(411, 1, 1),
            iterations=1,
        )
    finally:
        sys.setprofile(previous)
    assert observed == [report["qualification"]]
    assert report["mechanics_ready"] == observed[0]["mechanics_ready"]
    assert set(observed[0]["phases"]) == {"training:0", "heldout", "coaching"}
    assert observed[0]["training_inventory"] == {
        "complete": True,
        "attempted_candidates": [0],
        "expected_candidates": [0],
        "observed_candidates": [0],
    }
    assert all(unit["coverage"]["complete"] for unit in observed[0]["phases"].values())
    assert report["qualification"]["state"] == "unverified"


def test_prepare_cohort_generates_charts_and_exact_historical_review_scope(
    tmp_path: Path, events: list[Event]
) -> None:
    from tools.chartgen.cohort_sources import HistoricalContracts
    from tools.chartgen.prepare import prepare_cohort
    from tools.chartgen.scope import HistoricalGame, TeamSeason

    source = [
        replace(e, period=int(e.event_id.split("-")[-1]) % 4 + 1, clock="0:20") for e in events
    ]
    contracts = HistoricalContracts(
        {
            "1": TeamSeason("1", "Cedar Valley", "cfb:sec", "fbs"),
            "2": TeamSeason("2", "Harbor Tech", "cfb:sec", "fbs"),
            "3": TeamSeason("3", "Pine College", "cfb:sec", "fbs"),
        },
        tuple(HistoricalGame(f"g{i}", 2007, "1", "2") for i in range(4))
        + (HistoricalGame("absent", 2007, "1", "3"),),
        {"membership": {"sha256": "synthetic"}},
    )
    source += [
        replace(
            e,
            team="outer-a",
            opponent="outer-b",
            game_id="unjoined-external",
            event_id="outer-" + e.event_id,
        )
        for e in source[:10]
    ]
    root = tmp_path / "private-data" / "prepared"
    result = prepare_cohort(
        source, contracts, 2007, root, source_provenance={"synthetic": True}, minimum_source_games=1
    )
    assert result["generated_teams"] == 2
    assert result["stage"] == "baseline_ready_for_authorized_historical_study"
    assert result["selected_fixtures"] == 4
    assert result["excluded_fixtures"] == 1
    import json

    manifest = json.loads((root / "review" / "manifest.json").read_text())
    targets = json.loads((root / "review" / "targets.json").read_text())
    assert manifest["teams"]["3"]["chart_qualification"]["state"] == "insufficient_evidence"
    assert manifest["source"]["unjoined_source_game_ids"] == ["unjoined-external"]
    assert set(manifest["target_game_ids"]) == {f"g{i}" for i in range(4)}
    assert targets["1"]["game_ids"] == manifest["teams"]["1"]["offensive_game_ids"]
    assert (root / "charts" / "2007" / "cedar-valley" / "offense.csv").is_file()
    with pytest.raises(ValueError, match="new"):
        prepare_cohort(source, contracts, 2007, root, source_provenance={}, minimum_source_games=1)


def test_offensive_refinement_preserves_independently_modeled_defense(events: list[Event]) -> None:
    from tools.chartgen.tactics import TacticalProfile

    neutral = TacticalProfile.neutral()
    effects = tuple(
        replace(
            e,
            override_delta=0.08
            if e.formation.value == "A"
            else -0.08
            if e.formation.value == "B"
            else 0,
        )
        for e in neutral.effects
    )
    tactics = TacticalProfile(effects, "synthetic", ())
    first = generate_team(events, "1", "Cedar Valley", 2007, tactics=tactics)[0]
    second = generate_team(
        events,
        "1",
        "Cedar Valley",
        2007,
        tactics=tactics,
        profile=CalibrationProfile(pass_yards_scale=1.4),
    )[0]
    assert first.offense != second.offense
    assert first.defense == second.defense


def test_defensive_calibration_is_bounded_and_preserves_offense(events: list[Event]) -> None:
    from tools.chartgen.generate import DefensiveProfile

    first = generate_team(events, "1", "Cedar Valley", 2007)[0]
    second = generate_team(
        events,
        "1",
        "Cedar Valley",
        2007,
        defensive_profile=DefensiveProfile(run_yards_offset=1.5, completion_shift=-0.06),
    )[0]
    assert first.offense == second.offense
    assert first.defense != second.defense
    with pytest.raises(ValueError, match="bound"):
        DefensiveProfile(run_yards_offset=3)
    with pytest.raises(ValueError, match="finite"):
        DefensiveProfile(sack_shift=float("nan"))


def _prepare_refinement_example(
    tmp_path: Path, evidence: list[Event]
) -> tuple[list[Event], dict, dict]:
    import json

    from tools.chartgen.cohort_sources import HistoricalContracts
    from tools.chartgen.prepare import prepare_cohort
    from tools.chartgen.scope import HistoricalGame, TeamSeason

    source = [
        replace(e, period=int(e.event_id.split("-")[-1]) % 4 + 1, clock="0:20") for e in evidence
    ]
    contracts = HistoricalContracts(
        {
            "1": TeamSeason("1", "Cedar Valley", "cfb:sec", "fbs"),
            "2": TeamSeason("2", "Harbor Tech", "cfb:sec", "fbs"),
        },
        tuple(HistoricalGame(f"g{i}", 2007, "1", "2") for i in range(4)),
        {},
    )
    prepared = tmp_path / "private-data" / "prepared"
    prepare_cohort(source, contracts, 2007, prepared, source_provenance={}, minimum_source_games=1)
    manifest = json.loads((prepared / "review" / "manifest.json").read_text())
    targets = json.loads((prepared / "review" / "targets.json").read_text())
    return source, manifest, targets


@pytest.mark.parametrize("compression", ["json", "gzip"])
def test_historical_cohort_two_phase_driver_preserves_baseline_and_unused_validation(
    tmp_path: Path, events: list[Event], compression: str
) -> None:
    from tools.chartgen.cohort_refinement import run_cohort_refinement

    source, manifest, targets = _prepare_refinement_example(tmp_path, events)
    output = tmp_path / "private-data" / "refinement"
    report = run_cohort_refinement(
        source,
        manifest,
        targets,
        output,
        reviewed_manifest_sha256=manifest["manifest_sha256"],
        training_repetitions=1,
        validation_repetitions=1,
        coaching_repetitions=1,
        iterations=1,
        master_seed=77,
        compression=compression,
    )
    assert report["config"]["artifact_storage_policy"]["compression"] == compression
    assert report["heldout"]["artifact_storage"]["compression"] == compression
    assert report["mechanics_ready"]
    assert set(report["config"]["profile_bounds"]) == {"offense", "defense"}
    assert report["config"]["profile_bounds"]["defense"]["run_yards_offset"] == [-2.0, 2.0]
    assert not report["all_team_statistical_gates_passed"]
    assert report["historical_full_season_fit_claim"] is False
    assert report["training_history"][0]["summary"]["domain"] == "training"
    assert report["heldout"]["domain"] == "heldout"
    assert report["coaching_assessment"]["completed_runs"] == 4
    assert report["selected_regeneration_identical"]
    import csv

    with (output / "calibration-matchups.csv").open() as stream:
        used = list(csv.DictReader(stream))
    assert {r["game_id"] for r in used} == {f"g{i}" for i in range(4)}
    assert all(r["training_runs"] == "1" and r["heldout_runs"] == "1" for r in used)
    assert all(r["failed_runs"] == "0" for r in used)
    assert (output / "calibration-matchups.md").is_file()
    assert (output / "candidate-00" / "charts" / "2007" / "cedar-valley" / "offense.csv").exists()
    assert (output / "playtest-charts" / "2007" / "cedar-valley" / "offense.csv").exists()
    assert report == run_cohort_refinement(
        source,
        manifest,
        targets,
        output,
        reviewed_manifest_sha256=manifest["manifest_sha256"],
        training_repetitions=1,
        validation_repetitions=1,
        coaching_repetitions=1,
        iterations=1,
        master_seed=77,
        compression=compression,
        resume=True,
    )


def test_refinement_capacity_preflight_precedes_candidate_generation(
    tmp_path: Path, events: list[Event], monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from tools.chartgen import artifacts, cohort_refinement

    source, manifest, targets = _prepare_refinement_example(tmp_path, events)
    monkeypatch.setattr(artifacts.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    output = tmp_path / "private-data" / "insufficient-refinement"
    import cProfile

    with cProfile.Profile() as calls:
        with pytest.raises(artifacts.StorageCapacityError, match="insufficient storage"):
            cohort_refinement.run_cohort_refinement(
                source,
                manifest,
                targets,
                output,
                reviewed_manifest_sha256=manifest["manifest_sha256"],
            )
    assert not any(
        entry.code is cohort_refinement._candidate_charts.__code__ for entry in calls.getstats()
    )
    assert not output.exists()


def test_no_unobserved_option_or_scramble_branches_are_fabricated(events: list[Event]) -> None:
    chart, _, _ = generate_team(events, "1", "Cedar Valley", 2007)
    unsupported = {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS, ResultKind.QUARTERBACK_RUN}
    assert not any(record.cell.kind in unsupported for record in chart.offense)


def test_classified_overlapping_scrambles_supply_pass_qr_support(events: list[Event]) -> None:
    from tools.chartgen.evidence import classify_espn

    scrambles = [
        classify_espn(
            {
                "season": 2007,
                "game_id": "synthetic-scrambles",
                "id": f"scramble-{i}",
                "pos_team_id": 1,
                "def_pos_team_id": 2,
                "type.text": "Rush",
                "rush": True,
                "pass": True,
                "qb_scramble": True,
                "fumble_vec": False,
                "fumble_or_muff": False,
                "yds_rushed": 7,
                "statYardage": 7,
            }
        )
        for i in range(30)
    ]
    assert all(event is not None and event.kind == "rush" for event in scrambles)
    chart, _, report = generate_team(
        [*events, *(event for event in scrambles if event is not None)],
        "1",
        "Cedar Valley",
        2007,
    )
    assert any(
        row.play.value >= 6 and row.cell.kind is ResultKind.QUARTERBACK_RUN
        for row in chart.offense
    )
    assert report["family_evidence"]["6"]["source_QR_probability"] > 0


def test_completion_only_tail_cannot_enter_run_distribution(events: list[Event]) -> None:
    from dataclasses import replace

    from bowl_bound.models import SupplementalColumn

    evidence = [replace(e, yards=90) if e.kind == "complete" else e for e in events]
    chart, _, _ = generate_team(evidence, "1", "Cedar Valley", 2007)
    run_has_breakaway = any(
        r.play is Play.ONE and r.cell.kind is ResultKind.BREAKAWAY for r in chart.offense
    )
    largest_run = max(e.yards for e in evidence if e.kind == "rush")
    unsupported_tail = any(
        r.column is SupplementalColumn.BREAKAWAY
        and r.cell.yards is not None
        and r.cell.yards > largest_run
        for r in chart.supplemental
    )
    assert not (run_has_breakaway and unsupported_tail)


def test_source_penalty_side_and_distance_are_preserved(events: list[Event]) -> None:
    from bowl_bound.models import PenaltyCode, PenaltyTeam

    evidence = events + [
        Event(
            2007,
            "g0",
            f"off-foul-{i}",
            "1",
            "2",
            "Cedar Valley",
            "Harbor Tech",
            "penalty",
            None,
            penalty=True,
            no_play=True,
            penalty_side="offense",
            penalty_yards=15,
        )
        for i in range(30)
    ]
    chart, _, _ = generate_team(evidence, "1", "Cedar Valley", 2007)
    fouls = [r.cell.penalty for r in chart.offense if r.cell.penalty is not None]
    assert fouls
    assert all(
        p.team is PenaltyTeam.OFFENSE and p.code is PenaltyCode.FIXED and p.yards == 15
        for p in fouls
    )


def test_reference_tactical_strength_cannot_enter_pbp_baseline(events: list[Event]) -> None:
    from dataclasses import replace

    from tools.chartgen.tactics import TacticalProfile

    reference = replace(
        TacticalProfile.neutral(), origin="reference-derived", source_hashes=("a" * 64,)
    )
    with pytest.raises(ValueError, match="reference.*independent"):
        generate_team(events, "1", "Cedar Valley", 2007, tactics=reference)


def test_missing_interception_locations_cannot_become_zero_prior(events: list[Event]) -> None:
    from dataclasses import replace

    evidence = [
        replace(e, air_yards=None, interception_yards=None) if e.kind == "interception" else e
        for e in events
    ]
    with pytest.raises(ValueError, match="no known interception location"):
        generate_team(evidence, "1", "Cedar Valley", 2007)


def test_unknown_interception_locations_use_only_known_interception_pool(
    events: list[Event],
) -> None:
    from dataclasses import replace

    evidence = [
        replace(e, interception_yards=17, location_evidence=("synthetic-known-spot",))
        if e.team == "2" and e.kind == "interception"
        else replace(e, interception_yards=None)
        if e.kind == "interception"
        else e
        for e in events
    ]
    chart, _, manifest = generate_team(evidence, "1", "Cedar Valley", 2007)
    locations = [r.cell.yards for r in chart.offense if r.cell.kind is ResultKind.INTERCEPTION]
    assert locations and set(locations) == {17}
    assert manifest["location_evidence"]["interception"]["method"] == "league-PBP"


def test_run_fumbles_keep_locations_and_do_not_become_pass_fumbles(events: list[Event]) -> None:
    from dataclasses import replace

    evidence = [
        replace(
            e,
            fumble=e.kind == "rush" and int(e.event_id.split("-")[-1]) % 12 == 0,
            fumble_team=e.team,
            yards=7 if e.kind == "rush" else e.yards,
        )
        if e.kind in {"rush", "complete", "incomplete", "sack"}
        else e
        for e in events
    ]
    chart, _, _ = generate_team(evidence, "1", "Cedar Valley", 2007)
    run_fumbles = [
        r.cell.yards
        for r in chart.offense
        if r.play.value <= 5 and r.cell.kind is ResultKind.FUMBLE
    ]
    assert run_fumbles and set(run_fumbles) == {7}
    assert not any(r.play.value >= 6 and r.cell.kind is ResultKind.FUMBLE for r in chart.offense)


def test_kicking_team_fumble_is_not_assigned_to_receiving_team_return(events: list[Event]) -> None:
    from dataclasses import replace

    from bowl_bound.models import SpecialTeamsColumn

    evidence = [
        replace(e, fumble=True, fumble_team=e.team) if e.kind == "punt" else e for e in events
    ]
    chart, _, manifest = generate_team(evidence, "1", "Cedar Valley", 2007)
    assert not any(
        r.column is SpecialTeamsColumn.PUNT_RETURN and r.cell.kind is ResultKind.FUMBLE
        for r in chart.special_teams
    )
    assert manifest["special_evidence"]["punt_return"]["fumbles"] == 0


def test_missing_recovery_evidence_cannot_create_half_recovery_prior(events: list[Event]) -> None:
    evidence = [replace(e, fumble_lost=None, recovery_team=None) for e in events]
    with pytest.raises(ValueError, match="no known fumble recovery"):
        generate_team(evidence, "1", "Cedar Valley", 2007)


def test_sack_fumbles_are_on_conditional_trapped_response(events: list[Event]) -> None:
    from bowl_bound.models import SupplementalColumn

    evidence = [
        replace(
            e,
            fumble=e.kind == "sack",
            fumble_team=e.team,
            fumble_lost=False if e.kind == "sack" else None,
        )
        if e.kind in {"rush", "complete", "incomplete", "sack"}
        else e
        for e in events
    ]
    chart, _, _ = generate_team(evidence, "1", "Cedar Valley", 2007)
    assert not any(r.cell.kind is ResultKind.FUMBLE for r in chart.offense)
    trapped = [r for r in chart.supplemental if r.column is SupplementalColumn.QUARTERBACK_TRAPPED]
    assert all(r.cell.kind is ResultKind.FUMBLE and r.cell.yards == -6 for r in trapped)


def test_conditional_interception_location_distribution_keeps_both_observed_tails(
    events: list[Event],
) -> None:
    evidence = [
        replace(e, interception_yards=-8 if int(e.event_id.split("-")[-1]) % 2 else 42)
        if e.kind == "interception"
        else e
        for e in events
    ]
    chart, _, _ = generate_team(evidence, "1", "Cedar Valley", 2007)
    weights = offensive_weights()
    for play in (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE):
        locations = [
            r for r in chart.offense if r.play is play and r.cell.kind is ResultKind.INTERCEPTION
        ]
        assert {r.cell.yards for r in locations} == {-8, 42}
        mass = sum(weights[r.roll] for r in locations)
        assert (
            abs(sum(weights[r.roll] for r in locations if r.cell.yards == -8) / mass - 0.5)
            <= max(weights[r.roll] for r in locations) / mass
        )


def test_defensive_positive_response_cannot_synthesize_mean_as_observed_gain(
    events: list[Event],
) -> None:
    from tools.chartgen.tactics import TacticalProfile

    source = [
        replace(e, yards=0 if int(e.event_id.split("-")[-1]) % 2 else 80)
        if e.kind == "complete"
        else e
        for e in events
    ]
    neutral = TacticalProfile.neutral()
    tactics = replace(
        neutral,
        origin="synthetic",
        effects=tuple(
            replace(
                e,
                override_delta=(
                    0.12 if e.formation.value == "A" else -0.12 if e.formation.value == "B" else 0
                )
                if e.play.value >= 6
                else 0,
            )
            for e in neutral.effects
        ),
    )
    chart, _, _ = generate_team(source, "1", "Cedar Valley", 2007, tactics=tactics)
    responses = [
        r.cell.yards
        for r in chart.defense
        if r.defense.value == "A" and r.play.value >= 6 and r.cell.kind is ResultKind.YARDS
    ]
    assert responses and set(responses) <= {0, 80}
    # A rare defensive response may occupy a single finite-dice row; its
    # conditional support cannot cover both tails, but 40 was never observed.


def test_defensive_interception_uses_intercepting_team_evidence(events: list[Event]) -> None:
    from tools.chartgen.tactics import TacticalProfile

    source = [
        replace(e, interception_yards=-8 if e.team == "1" else 42)
        if e.kind == "interception"
        else e
        for e in events
    ]
    neutral = TacticalProfile.neutral()
    tactics = replace(
        neutral,
        origin="synthetic",
        effects=tuple(
            replace(
                e,
                interception_delta=(
                    0.12 if e.formation.value == "A" else -0.12 if e.formation.value == "B" else 0
                )
                if e.play.value >= 6
                else 0,
            )
            for e in neutral.effects
        ),
    )
    chart, _, _ = generate_team(source, "1", "Cedar Valley", 2007, tactics=tactics)
    locations = [r.cell.yards for r in chart.defense if r.cell.kind is ResultKind.INTERCEPTION]
    assert locations and set(locations) == {42}


def test_blocked_punt_location_is_observed_instead_of_zero(events: list[Event]) -> None:
    from bowl_bound.models import SpecialTeamsColumn

    source = [
        replace(e, blocked=True, yards=0, blocked_kick_yards=-7)
        if e.kind == "punt" and e.team == "1" and int(e.event_id.split("-")[-1]) % 3 == 0
        else e
        for e in events
    ]
    chart, _, _ = generate_team(source, "1", "Cedar Valley", 2007)
    locations = [
        r.cell.yards
        for r in chart.special_teams
        if r.column is SpecialTeamsColumn.PUNT and r.cell.kind is ResultKind.BLOCKED_KICK
    ]
    assert locations and set(locations) == {-7}


def test_field_goal_observations_do_not_gain_unobserved_pseudocount_misses(
    events: list[Event],
) -> None:
    from bowl_bound.models import SpecialTeamsColumn

    source = [replace(e, kick_good=True) if e.kind == "field_goal" else e for e in events]
    chart, _, _ = generate_team(source, "1", "Cedar Valley", 2007)
    ranges = [
        r.cell.yards for r in chart.special_teams if r.column is SpecialTeamsColumn.FIELD_GOAL
    ]
    # Observed kick distance 35 = LOS 18. Finite rows may not add failures here.
    assert all(distance is not None and distance >= 18 for distance in ranges)


def test_missing_field_goal_outcomes_are_not_misses(events: list[Event]) -> None:
    source = [replace(e, kick_good=None) if e.kind == "field_goal" else e for e in events]
    with pytest.raises(ValueError, match="field_goal outcome"):
        generate_team(source, "1", "Cedar Valley", 2007)


def test_recovery_reports_nearest_legal_codec_mass_instead_of_claiming_exact_one(
    events: list[Event],
) -> None:
    source = [
        replace(e, fumble_lost=False, recovery_team=e.fumble_team) if e.fumble else e
        for e in events
    ]
    chart, _, manifest = generate_team(source, "1", "Cedar Valley", 2007)
    weights = offensive_weights()
    achieved = sum(weights[r] for r in chart.recovery_range) / 216
    legal = [sum(w for r, w in weights.items() if r <= end) / 216 for end in range(10, 39)]
    assert achieved == max(legal) < 1
    assert manifest["recovery_evidence"]["requested_probability"] == 1
    assert manifest["recovery_evidence"]["quantization_error"] == achieved - 1
    assert "DATA-023" in manifest["recovery_evidence"]["constraint"]


def test_identified_other_pass_scrambles_cannot_enter_qualified_screen(events: list[Event]) -> None:
    source = [
        replace(e, called_family=6, resolved_family=6)
        if e.team == "1" and e.kind == "complete"
        else e
        for e in events
    ]
    source += [
        replace(
            source[0],
            event_id=f"known-long-scramble-{i}",
            kind="rush",
            yards=8,
            called_family=9,
            resolved_family=9,
            quarterback_scramble=True,
            fumble=False,
            fumble_lost=None,
            fumble_team=None,
        )
        for i in range(30)
    ]
    chart, _, _ = generate_team(source, "1", "Cedar Valley", 2007)
    assert not any(
        r.play is Play.SIX and r.cell.kind is ResultKind.QUARTERBACK_RUN for r in chart.offense
    )


def test_option_fumble_frequency_is_conditioned_on_its_rush_mechanism(events: list[Event]) -> None:
    from tools.chartgen.empirical import WeightedObservation
    from tools.chartgen.generate import _fumble_distribution

    branches = [
        replace(
            events[0],
            event_id=f"option-sop-{i}",
            called_family=5,
            resolved_family=7,
            kind="complete",
            yards=12,
            fumble=None,
            fumble_team=None,
            fumble_lost=None,
        )
        for i in range(60)
    ]
    rush = replace(
        events[0],
        event_id="option-rush-fumble",
        called_family=5,
        resolved_family=5,
        kind="rush",
        yards=7,
        fumble=True,
        fumble_team="1",
        fumble_lost=False,
    )
    probability, locations = _fumble_distribution(
        [WeightedObservation(event, 1.0) for event in [rush, *branches]], 0.0, 1.0, kind="rush"
    )
    assert probability == pytest.approx(1 / 61)
    assert set(locations) == {7}


def test_recovery_team_pool_includes_its_observed_return_fumbles(events: list[Event]) -> None:
    source = [
        replace(e, fumble=False, fumble_team=None, recovery_team=None, fumble_lost=None)
        if e.team == "1"
        else e
        for e in events
    ]
    source = [
        replace(e, fumble=True, fumble_team="1", recovery_team="1", fumble_lost=None)
        if e.team == "2" and e.kind == "punt"
        else e
        for e in source
    ]
    _, _, manifest = generate_team(source, "1", "Cedar Valley", 2007)
    assert manifest["recovery_evidence"]["method"] == "team-PBP"
    assert manifest["recovery_evidence"]["known_team_samples"] == 30
    assert manifest["recovery_evidence"]["requested_probability"] == 1


@pytest.mark.parametrize("effect", [-6.25, -0.51, -0.49, 0.0, 0.49, 0.51, 6.25])
def test_defensive_fractional_effect_uses_nearest_physical_mass(effect: float) -> None:
    from tools.chartgen.generate import quantized_defensive_offsets

    weights = defensive_weights()
    offsets = quantized_defensive_offsets(weights, effect, seed=19)
    import math

    lower = math.floor(effect)
    attainable = {0}
    for weight in weights.values():
        attainable |= {mass + weight for mass in tuple(attainable)}
    achieved = sum(weights[row] * offsets[row] for row in weights) / 36
    expected = min(
        (lower + mass / 36 for mass in attainable),
        key=lambda value: (abs(value - effect), value),
    )
    assert achieved == pytest.approx(expected)
    assert set(offsets.values()) <= {lower, lower + 1}
    assert offsets == quantized_defensive_offsets(
        dict(reversed(list(weights.items()))), effect, seed=19
    )


@pytest.mark.parametrize(
    "weights,effect", [({1: 0}, 0.0), ({1: -1}, 0.0), ({1: 1.5}, 0.0), ({1: 1}, float("nan"))]
)
def test_defensive_quantization_rejects_invalid_weights_or_effect(
    weights: dict, effect: float
) -> None:
    from tools.chartgen.generate import quantized_defensive_offsets

    with pytest.raises(ValueError):
        quantized_defensive_offsets(weights, effect, seed=1)


@pytest.mark.parametrize("effect", [-6.25, -0.51, -0.49, 0.49, 0.51, 6.25])
def test_generated_defense_preserves_fractional_effect_without_reference_clamp(
    events: list[Event], effect: float
) -> None:
    from tools.chartgen.generate import EvidenceModel

    model = replace(EvidenceModel.from_events(events), run_effects={"1": effect, "2": 0.0})
    chart, _, manifest = generate_team(events, "1", "Cedar Valley", 2007, seed=19, model=model)
    cells = [cell for cell in chart.defense if cell.defense.value == "A" and cell.play == Play.ONE]
    weighted = sum(defensive_weights()[cell.roll] * (cell.cell.yards or 0) for cell in cells) / 36
    # Five weighted rows have gaps in attainable means; 1/36 is not a universal bound.
    import math
    from itertools import product

    lower = math.floor(effect)
    attainable = [
        sum(
            defensive_weights()[row] * (lower + upper)
            for row, upper in zip(range(1, 6), choices, strict=True)
        )
        / 36
        for choices in product((0, 1), repeat=5)
    ]
    expected = min(attainable, key=lambda value: (abs(value - effect), value))
    assert weighted == pytest.approx(expected)
    assert abs(weighted - effect) < abs(round(effect) - effect)
    assert manifest["modeled_priors"]["defense_effect_bound_yards"] is None
    audit = manifest["defensive_quantization"]["A/1"]
    assert audit["requested_yardage_effect"] == effect
    assert audit["ordinary_achieved_effect"] == weighted
    assert audit["ordinary_physical_mass"] == 36


def test_defensive_offsets_are_quantized_after_response_allocation(events: list[Event]) -> None:
    from itertools import product
    from math import floor

    from bowl_bound.models import Priority
    from tools.chartgen.generate import EvidenceModel

    source = [replace(event, yards=10) if event.kind == "complete" else event for event in events]
    model = replace(
        EvidenceModel.from_events(source),
        pass_effects={"1": 0.49, "2": 0.0},
        rate_effects={"complete": {"1": 0.12}, "interception": {}, "sack": {}},
    )
    chart, _, manifest = generate_team(source, "1", "Cedar Valley", 2007, seed=19, model=model)
    cells = [cell for cell in chart.defense if cell.defense.value == "A" and cell.play == Play.SIX]
    groups = {
        "ordinary": [cell for cell in cells if cell.cell.priority is Priority.NORMAL],
        "response": [cell for cell in cells if cell.cell.priority is not Priority.NORMAL],
    }
    assert all(groups.values())
    for name, records in groups.items():
        assert all(cell.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE} for cell in records)
        mass = sum(defensive_weights()[cell.roll] for cell in records)
        achieved = (
            sum(
                defensive_weights()[cell.roll]
                * ((cell.cell.yards or 0) - (10 if name == "response" else 0))
                for cell in records
            )
            / mass
        )
        attainable = [
            sum(
                defensive_weights()[cell.roll] * (floor(0.49) + upper)
                for cell, upper in zip(records, choices, strict=True)
            )
            / mass
            for choices in product((0, 1), repeat=len(records))
        ]
        expected = min(attainable, key=lambda value: (abs(value - 0.49), value))
        assert achieved == pytest.approx(expected)
    assert manifest["defensive_quantization"]["A/6"]["ordinary_physical_mass"] < 36


def test_defensive_semantic_mass_audit_exposes_conditional_attainability(
    events: list[Event],
) -> None:
    from itertools import product

    from tools.chartgen.generate import EvidenceModel

    model = replace(
        EvidenceModel.from_events(events),
        rate_effects={"complete": {"1": -0.12}, "interception": {"1": 0.035}, "sack": {"1": 0.04}},
    )
    chart, _, manifest = generate_team(events, "1", "Cedar Valley", 2007, seed=19, model=model)
    allocations = manifest["defensive_quantization"]["A/6"]["semantic_allocations"]
    remaining = defensive_weights()
    expected_kinds = {
        "INT": ResultKind.INTERCEPTION,
        "QT": ResultKind.QUARTERBACK_TRAPPED,
        "BLACK": ResultKind.INCOMPLETE,
    }
    for allocation in allocations:
        weights = list(remaining.values())
        attainable = sorted(
            {
                sum(weight * selected for weight, selected in zip(weights, mask, strict=True))
                for mask in product((0, 1), repeat=len(weights))
            }
        )
        assert allocation["available_physical_mass"] == sum(weights)
        assert allocation["attainable_physical_masses"] == attainable
        expected = min(
            attainable,
            key=lambda mass: (abs(mass - allocation["requested_probability"] * 36), mass),
        )
        assert allocation["selected_physical_mass"] == expected
        rows = allocation["rows"]
        assert sum(remaining[row] for row in rows) == expected
        if allocation["token"] in expected_kinds:
            assert all(
                next(
                    cell.cell.kind
                    for cell in chart.defense
                    if cell.defense.value == "A" and cell.play == Play.SIX and cell.roll == row
                )
                is expected_kinds[allocation["token"]]
                for row in rows
            )
        for row in rows:
            del remaining[row]
    assert manifest["defensive_quantization"]["A/6"]["ordinary_physical_mass"] == sum(
        remaining.values()
    )


def test_training_selection_is_sealed_before_any_heldout_game(
    tmp_path: Path, events: list[Event]
) -> None:
    import json

    from tools.chartgen import cohort_refinement
    from tools.chartgen.cohort_report import canonical_hash

    source, manifest, targets = _prepare_refinement_example(tmp_path, events)
    output = tmp_path / "private-data" / "sealed"
    import sys

    observed_boundaries = []

    def observe_boundary(frame: Any, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code is cohort_refinement.run_historical_batch.__code__:
            domain = frame.f_locals["domain"]
            if domain in {"heldout", "coaching"}:
                receipt = json.loads((output / "training-selection.json").read_text())
                body = {key: value for key, value in receipt.items() if key != "semantic_sha256"}
                assert canonical_hash(body) == receipt["semantic_sha256"]
                assert receipt["selected_candidate"] == 0
                observed_boundaries.append(domain)

    previous = sys.getprofile()
    sys.setprofile(observe_boundary)
    try:
        result = cohort_refinement.run_cohort_refinement(
            source,
            manifest,
            targets,
            output,
            reviewed_manifest_sha256=manifest["manifest_sha256"],
            training_repetitions=1,
            validation_repetitions=1,
            coaching_repetitions=1,
            iterations=1,
            master_seed=91,
        )
    finally:
        sys.setprofile(previous)
    assert observed_boundaries == ["heldout", "coaching"]
    assert (
        result["training_selection"]["semantic_sha256"]
        == json.loads((output / "training-selection.json").read_text())["semantic_sha256"]
    )
    assert result["selected_profiles"] == result["training_selection"]["selected_profiles"]
    # A fresh second run in a different directory repeats complete engine games.
    repeated = cohort_refinement.run_cohort_refinement(
        source,
        manifest,
        targets,
        tmp_path / "private-data" / "sealed-repeat",
        reviewed_manifest_sha256=manifest["manifest_sha256"],
        training_repetitions=1,
        validation_repetitions=1,
        coaching_repetitions=1,
        iterations=1,
        master_seed=91,
    )
    assert repeated == result


def test_pure_candidate_claim_rejects_nonconsecutive_cycle_before_another_batch() -> None:
    from tools.chartgen.training_selection import claim_training_fingerprint

    seen: set[str] = set()
    batches = []
    for fingerprint in ("A", "B", "A"):
        if not claim_training_fingerprint(fingerprint, seen):
            break
        batches.append(fingerprint)
    assert batches == ["A", "B"]
    assert seen == {"A", "B"}


def test_reference_files_and_learner_do_not_influence_initial_generation(
    tmp_path: Path, events: list[Event], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import tactics
    from tools.chartgen.batch import bundle_hash

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        tactics, "learn_tactics", lambda *args: pytest.fail("reference learner consulted")
    )
    first = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
    reference = tmp_path / "seasons" / "2007" / "fictional-developer-reference"
    reference.mkdir(parents=True)
    original_read = Path.read_text

    def forbid_reference_read(path: Path, *args: Any, **kwargs: Any) -> str:
        assert not path.is_relative_to(reference)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", forbid_reference_read)
    for value in (99, -99):
        (reference / "offense.csv").write_text(f"fictional reference perturbation,{value}\n")
        changed = generate_team(events, "1", "Cedar Valley", 2007, seed=19)
        assert bundle_hash(*first[:2]) == bundle_hash(*changed[:2])
        assert first[2] == changed[2]


def test_pure_training_plateau_consumer_uses_the_predeclared_limit() -> None:
    from tools.chartgen.training_selection import SELECTION_POLICY, training_plateau_reached

    limit = SELECTION_POLICY["no_improvement_candidate_limit"]
    assert all(not training_plateau_reached(count) for count in range(limit))
    assert training_plateau_reached(limit)
    assert training_plateau_reached(limit + 1)


def test_real_workflow_claims_before_batching_and_stops_without_qualified_probes(
    tmp_path: Path, events: list[Event]
) -> None:
    import sys

    from tools.chartgen import cohort_refinement
    from tools.chartgen.training_selection import claim_training_fingerprint

    source, manifest, targets = _prepare_refinement_example(tmp_path, events)
    observed = []

    def observe(frame: Any, event: str, argument: Any) -> None:
        if event == "return" and frame.f_code is claim_training_fingerprint.__code__:
            observed.append(("claimed", argument))
        if event == "call" and frame.f_code is cohort_refinement.run_historical_batch.__code__:
            observed.append(("batch", frame.f_locals["domain"]))

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        result = cohort_refinement.run_cohort_refinement(
            source,
            manifest,
            targets,
            tmp_path / "private-data" / "finite-budget",
            reviewed_manifest_sha256=manifest["manifest_sha256"],
            training_repetitions=1,
            validation_repetitions=1,
            coaching_repetitions=1,
            iterations=4,
            master_seed=93,
        )
    finally:
        sys.setprofile(previous)
    assert observed == [
        ("claimed", True),
        ("batch", "training"),
        ("batch", "heldout"),
        ("batch", "coaching"),
    ]
    assert len(result["training_history"]) == 1
    assert not result["training_history"][0]["qualified_objective"]["qualified_units"]
    assert result["stopping_rule"] == "bounded probes yielded no qualified local improvement"
    assert result["total_completed_engine_runs"] == 12
    assert result["qualification"]["state"] == "unverified"
    assert all(
        phase["team_inventory"]["complete"] for phase in result["qualification"]["phases"].values()
    )
    assert all(
        phase["team_inventory"]["expected_count"] == len(manifest["teams"])
        for phase in result["qualification"]["phases"].values()
    )


def _prepare_qualified_refinement_example(
    tmp_path: Path, events: list[Event], *, copies: int = 1
) -> tuple[list[Event], dict, dict]:
    import json

    from tools.chartgen.cohort_sources import HistoricalContracts
    from tools.chartgen.prepare import prepare_cohort
    from tools.chartgen.scope import HistoricalGame, TeamSeason

    source = []
    for event in events:
        index = int(event.event_id.split("-")[-1])
        per_game = 60 if event.event_id.count("-") == 1 else 5
        source.append(
            replace(event, game_id=f"g{index // per_game}", period=index % 4 + 1, clock="0:20")
        )
    source = [
        replace(event, event_id=f"{event.event_id}-replica-{copy}")
        for copy in range(copies)
        for event in source
    ]
    contracts = HistoricalContracts(
        {
            team: TeamSeason(team, name, "cfb:sec", "fbs")
            for team, name in (("1", "Cedar Valley"), ("2", "Harbor Tech"))
        },
        tuple(HistoricalGame(f"g{index}", 2007, "1", "2") for index in range(6)),
        {},
    )
    prepared = tmp_path / "private-data" / "qualified-source"
    prepare_cohort(source, contracts, 2007, prepared, source_provenance={"synthetic": True})
    manifest = json.loads((prepared / "review" / "manifest.json").read_text())
    targets = json.loads((prepared / "review" / "targets.json").read_text())
    assert len(manifest["target_game_ids"]) == 6
    assert all(
        record["historical_exposure"][role]["qualified"]
        for record in targets.values()
        for role in ("offense", "defense")
    )
    return source, manifest, targets


def test_qualified_historical_source_reaches_real_engine_selection(
    tmp_path: Path, events: list[Event]
) -> None:
    from tools.chartgen.cohort_refinement import run_cohort_refinement

    source, manifest, targets = _prepare_qualified_refinement_example(tmp_path, events)
    result = run_cohort_refinement(
        source,
        manifest,
        targets,
        tmp_path / "private-data" / "qualified-study",
        reviewed_manifest_sha256=manifest["manifest_sha256"],
        training_repetitions=1,
        validation_repetitions=1,
        coaching_repetitions=1,
        iterations=1,
        master_seed=94,
    )
    assert result["mechanics_ready"]
    assert result["training_selection"]["qualified_units"] == [
        "1/defense",
        "1/offense",
        "2/defense",
        "2/offense",
    ]
    assert not result["training_selection"]["descriptive_only_units"]
    assert result["total_completed_engine_runs"] == 18


def test_actual_engine_coordinate_probes_freeze_opponents_and_only_combine_local_benefits(
    tmp_path: Path, events: list[Event]
) -> None:
    from tools.chartgen.cohort_refinement import run_cohort_refinement

    source, manifest, targets = _prepare_qualified_refinement_example(tmp_path, events, copies=3)
    result = run_cohort_refinement(
        source,
        manifest,
        targets,
        tmp_path / "private-data" / "isolated-coordinates",
        reviewed_manifest_sha256=manifest["manifest_sha256"],
        training_repetitions=1,
        validation_repetitions=1,
        coaching_repetitions=1,
        iterations=4,
        master_seed=95,
    )
    history = result["training_history"]
    baseline = history[0]["profiles"]
    assert history[0]["candidate_kind"] == "baseline"
    probes = [entry for entry in history if entry["candidate_kind"] == "isolated_coordinate"]
    assert probes
    assert len(probes) <= 2
    for probe in probes:
        changed = [
            (team, role, knob)
            for role, teams in baseline.items()
            for team, values in teams.items()
            for knob, value in values.items()
            if probe["profiles"][role][team][knob] != value
        ]
        coordinate = probe["coordinate_probe"]["coordinate"]
        assert changed == [(coordinate["team"], coordinate["role"], coordinate["knob"])]
        assert coordinate["source_qualified"] is True
        assert probe["coordinate_probe"]["fingerprint"] == probe["chart_fingerprint"]
    beneficial = {
        entry["candidate"]
        for entry in probes
        if entry["coordinate_probe"]["local_probe_loss"]
        < entry["coordinate_probe"]["local_baseline_loss"]
    }
    for joint in [entry for entry in history if entry["candidate_kind"] == "joint_validation"]:
        assert set(joint["composed_probe_candidates"]) <= beneficial
    assert result["mechanics_ready"]
    assert not result["source_holdout_claim"]
    assert result["total_completed_engine_runs"] <= 36
    assert (
        result["training_selection"]["execution_contract"]["coordinate_policy"][
            "opponents_frozen_during_probes"
        ]
        is True
    )
    repeated = run_cohort_refinement(
        source,
        manifest,
        targets,
        tmp_path / "private-data" / "isolated-coordinates-repeat",
        reviewed_manifest_sha256=manifest["manifest_sha256"],
        training_repetitions=1,
        validation_repetitions=1,
        coaching_repetitions=1,
        iterations=4,
        master_seed=95,
    )
    assert repeated == result
