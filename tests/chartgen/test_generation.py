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
                    )
                )
    return output


def test_physical_dice_weights_and_rare_rate() -> None:
    assert sum(offensive_weights().values()) == 216
    assert sum(defensive_weights().values()) == 36
    selected = nearest_mass_rows(offensive_weights(), 1 / 216, seed=7)
    assert sum(offensive_weights()[r] for r in selected) == 1
    assert offensive_weights()[10] != offensive_weights()[35]


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
    assert any(
        c.cell.kind is ResultKind.SPRINT_OUT_PASS for c in chart.offense if c.play is Play.FIVE
    )
    assert any(c.cell.kind is ResultKind.BOOTLEG_PASS for c in chart.offense if c.play is Play.FIVE)


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
    explicit = [replace(e, called_family=1) if e.kind == "rush" else e for e in events]
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
    risky = [replace(e, fumble=True, fumble_lost=True) if e.kind == "punt" else e for e in events]
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


def test_pass_breakaways_use_observed_completion_tails(events: list[Event]) -> None:
    chart, _, manifest = generate_team(events, "1", "Cedar Valley", 2007)
    assert all(
        any(c.cell.kind is ResultKind.BREAKAWAY for c in chart.offense if c.play is play)
        for play in [Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE]
    )
    assert (
        manifest["modeled_priors"]["breakaway_tail_method"]
        == "joint empirical run/completion upper tails"
    )


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


def test_training_reconciliation_failure_blocks_readiness_even_if_heldout_passes(
    tmp_path: Path,
    events: list[Event],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tools.chartgen.refine as refine

    original = refine.run_batch

    def declared_failure(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original(*args, **kwargs)
        if args[2].name == "training":
            result["failed_games"] = 1
        return result

    monkeypatch.setattr(refine, "run_batch", declared_failure)
    report = refine.run_refinement(
        events,
        {"1": "Cedar Valley", "2": "Harbor Tech"},
        2007,
        tmp_path / "private-data" / "failed-training",
        seed_plan=refine.SeedPlan(411, 1, 1),
        iterations=1,
    )
    assert not report["mechanics_ready"]


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
    root = tmp_path / "private-data" / "prepared"
    result = prepare_cohort(
        source, contracts, 2007, root, source_provenance={"synthetic": True}, minimum_source_games=1
    )
    assert result["generated_teams"] == 2
    assert result["selected_fixtures"] == 4
    assert result["excluded_fixtures"] == 1
    import json

    manifest = json.loads((root / "review" / "manifest.json").read_text())
    targets = json.loads((root / "review" / "targets.json").read_text())
    assert manifest["teams"]["3"]["chart_qualification"]["state"] == "insufficient_evidence"
    assert set(manifest["target_game_ids"]) == {f"g{i}" for i in range(4)}
    assert targets["1"]["game_ids"] == manifest["teams"]["1"]["offensive_game_ids"]
    assert (root / "charts" / "2007" / "cedar-valley" / "offense.csv").is_file()
    with pytest.raises(ValueError, match="new"):
        prepare_cohort(source, contracts, 2007, root, source_provenance={}, minimum_source_games=1)
