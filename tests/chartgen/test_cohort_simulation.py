"""Original fictional multi-team historical schedules, engine replay and resume."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.team_csv import load_team
from tools.chartgen.batch import generate_cohort
from tools.chartgen.cohort_report import write_matchup_report
from tools.chartgen.scope import build_slate, qualified_games, slate_targets

from .test_scope import events, game, members


def prepared(tmp_path: Path) -> tuple[dict, dict, dict, dict]:
    schedule = [
        game("ab", "a", "b", date="2007-09-01"),
        game("ac", "a", "c", date="2007-09-08", postseason=True, neutral_site=True),
    ]
    source = events("ab", "a", "b") + events("ac", "a", "c")
    for row in list(source):
        if row.event_id.endswith("-1-0"):
            for kind, yards in [
                ("sack", -6),
                ("punt", 40),
                ("kickoff", 60),
                ("field_goal", 35),
                ("pat", None),
                ("interception", None),
            ]:
                source.append(
                    replace(
                        row,
                        kind=kind,
                        yards=yards,
                        kick_good=True,
                        return_yards=8,
                        event_id=row.event_id + kind,
                    )
                )
    m = {k: v for k, v in members().items() if k != "x"}
    slate = build_slate(
        schedule,
        m,
        generated_teams=set(m),
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha", "beta"},
    )
    targets = slate_targets(source, slate)
    report = write_matchup_report(
        tmp_path / "private-data" / "review",
        slate,
        targets,
        source={},
        engine={},
        profiles_sha256="neutral",
        chart_qualifications={},
    )
    out = tmp_path / "private-data" / "charts"
    generation = generate_cohort(source, {k: v.name for k, v in m.items()}, 2007, out)
    catalog = {k: v["catalog_id"] for k, v in generation["teams"].items()}
    teams = {
        identity: load_team(out / "2007", identity.split("/")[1]) for identity in catalog.values()
    }
    return report, targets, catalog, teams


def test_actual_fixture_seed_domains_are_paired_and_order_independent(tmp_path: Path) -> None:
    from tools.chartgen.cohort_simulation import fixture_runs

    report, _, _, _ = prepared(tmp_path)
    a = fixture_runs(report, repetitions=2, master_seed=77, domain="training")
    b = fixture_runs(report, repetitions=2, master_seed=77, domain="heldout")
    assert len(a) == 4
    assert {r.game.game_id for r in a} == {"ab", "ac"}
    assert a == fixture_runs(report, repetitions=2, master_seed=77, domain="training")
    assert {r.seed for r in a}.isdisjoint(r.seed for r in b)
    assert all(r.game.home == "a" for r in a)
    assert {r.game.neutral_site for r in a} == {True, False}
    with pytest.raises(ValueError, match="domain"):
        fixture_runs(report, repetitions=1, master_seed=77, domain="candidate-profile")


@pytest.mark.parametrize("workers", [1, 2])
def test_real_engine_cohort_resume_is_exact_and_tamper_rejected(
    tmp_path: Path, workers: int
) -> None:
    from tools.chartgen.cohort_simulation import run_historical_batch

    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "simulation"
    result = run_historical_batch(
        report,
        teams,
        catalog,
        targets,
        output,
        repetitions=1,
        master_seed=77,
        domain="training",
        verify_replay=True,
        workers=workers,
    )
    assert result["failed_games"] == 0 and result["passed_games"] == 2
    assert result["team_games"][catalog["a"]] == 2
    assert result["per_source_team"]["a"]["game_ids"] == ["ab", "ac"]
    assert result["per_source_team"]["b"]["game_ids"] == ["ab"]
    assert result["per_source_team"]["a"]["defense"]["metrics"]["completion"]["n"] > 0
    assert not result["per_source_team"]["b"]["offense_assessment"]["passed"]
    assert "alpha" in result["conferences"]
    assert result["source_holdout_claim"] is False
    resumed = run_historical_batch(
        report,
        teams,
        catalog,
        targets,
        output,
        repetitions=1,
        master_seed=77,
        domain="training",
        verify_replay=True,
        resume=True,
    )
    assert resumed == result
    # An interrupted run may have completed its first atomic publication only.
    retained_bytes = (output / "game-000001.json").read_bytes()
    (output / "game-000002.json").unlink()
    recovered = run_historical_batch(
        report,
        teams,
        catalog,
        targets,
        output,
        repetitions=1,
        master_seed=77,
        domain="training",
        verify_replay=True,
        resume=True,
        workers=workers,
    )
    assert recovered == result
    assert (output / "game-000001.json").read_bytes() == retained_bytes
    with pytest.raises(ValueError, match="contract"):
        run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            output,
            repetitions=1,
            master_seed=78,
            domain="training",
            resume=True,
        )
    artifact = output / "game-000001.json"
    value = json.loads(artifact.read_text())
    from tools.chartgen.cohort_simulation import compact_metric_result
    from tools.chartgen.refine import aggregate_games

    compact = compact_metric_result(value["result"])
    assert aggregate_games([compact]) == aggregate_games([value["result"]])
    assert len(json.dumps(compact)) < len(json.dumps(value["result"])) / 2
    from tools.chartgen.cohort_simulation import summarize_cohort
    from tools.chartgen.scope import CORE_METRICS

    strict_targets = {
        t: {
            **record,
            "offense": dict.fromkeys(CORE_METRICS, 0.0),
            "defense": dict.fromkeys(CORE_METRICS, 0.0),
        }
        for t, record in targets.items()
    }
    assessment = summarize_cohort(
        [value["result"]], report, catalog, strict_targets, minimum_samples=1
    )
    assert assessment["per_source_team"]["a"]["state"] == "not_fit"
    for role in ("offense", "defense"):
        strict_targets["a"][role] = {
            k: v["value"]
            for k, v in assessment["per_source_team"]["a"][role]["metrics"].items()
            if k in CORE_METRICS
        }
    assert (
        summarize_cohort([value["result"]], report, catalog, strict_targets, minimum_samples=1)[
            "per_source_team"
        ]["a"]["state"]
        == "fit"
    )

    value["result"]["final"]["home_score"] += 1
    artifact.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="checksum"):
        run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            output,
            repetitions=1,
            master_seed=77,
            domain="training",
            verify_replay=True,
            resume=True,
        )


def test_historical_postseason_configuration_reaches_real_engine(tmp_path: Path) -> None:
    from bowl_bound.save_game import dumps_game
    from scripts.run_local_season import GameSpec, _new_audit_game

    _, _, catalog, teams = prepared(tmp_path)
    spec = GameSpec(1, 2007, catalog["b"], catalog["a"], 7, game_type="postseason")
    engine = _new_audit_game(spec, teams)
    assert json.loads(dumps_game(engine))["config"]["game_type"] == "postseason"


def test_changed_target_values_rejected_before_any_engine_run(tmp_path: Path) -> None:
    from tools.chartgen.cohort_simulation import run_historical_batch

    report, targets, catalog, teams = prepared(tmp_path)
    targets["a"]["offense"]["completion"] = 0.99
    with pytest.raises(ValueError, match="target.*hash"):
        run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            tmp_path / "private-data" / "changed-targets",
            repetitions=1,
            master_seed=77,
            domain="training",
        )
    assert not (tmp_path / "private-data" / "changed-targets").exists()


def test_actual_matchup_usage_rejects_invented_simulation_fixture(tmp_path: Path) -> None:
    from tools.chartgen.cohort_run_report import write_matchup_usage

    manifest, _, _, _ = prepared(tmp_path)
    wrong = {"fixture_exposure": {"invented": {"attempted": 1}}, "failed_fixture_runs": []}
    with pytest.raises(ValueError, match="usage differs"):
        write_matchup_usage(
            tmp_path / "private-data", manifest, [wrong], wrong, wrong, selected_profiles={}
        )


def test_empty_historical_slate_cannot_claim_successful_simulation(tmp_path: Path) -> None:
    from tools.chartgen.cohort_simulation import run_historical_batch

    schedule = [game("ab", "a", "b")]
    source = events("ab", "a", "b")
    slate = build_slate(
        schedule,
        members(),
        generated_teams=set(),
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha", "beta"},
    )
    targets = slate_targets(source, slate)
    report = write_matchup_report(
        tmp_path / "private-data" / "empty-review",
        slate,
        targets,
        source={},
        engine={},
        profiles_sha256="none",
        chart_qualifications={},
    )
    with pytest.raises(ValueError, match="no selected"):
        run_historical_batch(
            report,
            {},
            {},
            targets,
            tmp_path / "private-data" / "empty-simulation",
            repetitions=1,
            master_seed=77,
            domain="training",
        )
    assert not (tmp_path / "private-data" / "empty-simulation").exists()
    from tools.chartgen.cohort_refinement import run_cohort_refinement

    with pytest.raises(ValueError, match="no selected"):
        run_cohort_refinement(
            source,
            report,
            targets,
            tmp_path / "private-data" / "empty-refinement",
            reviewed_manifest_sha256=report["manifest_sha256"],
        )
    assert not (tmp_path / "private-data" / "empty-refinement").exists()


def test_unidentified_core_metric_blocks_full_fit_without_fake_target() -> None:
    from tools.chartgen.cohort_simulation import assess_team_metrics

    targets = {
        "completion": 0.6,
        "interception": 0.03,
        "sack": 0.06,
        "rush_yards_per_attempt": 4.0,
        "pass_yards_per_attempt": 6.0,
    }
    measured = {k: {"n": 2000, "value": v} for k, v in targets.items()}
    assessment = assess_team_metrics(measured, targets, minimum_samples=1000)
    assert all(v["passed"] for v in assessment["metrics"].values())
    assert not assessment["passed"]
    assert assessment["unidentifiable_source_metrics"] == ["fumble"]
    assert "fumble" not in assessment["metrics"]
