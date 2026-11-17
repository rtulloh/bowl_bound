"""Synthetic late caller edits must not change an already-pinned research batch."""

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import FrameType
from typing import Any

import pytest

from tests.synthetic_teams import team_chart
from tools.chartgen import cohort_simulation
from tools.chartgen.cohort_simulation import run_historical_batch

from .test_cohort_simulation import prepared


@pytest.mark.parametrize("change", ("team_chart", "manifest", "targets", "catalog"))
def test_progress_caller_cannot_change_frozen_batch_inputs(tmp_path: Path, change: str) -> None:
    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "late-input"
    changed = []

    def progress(completed: int, total: int, status: str) -> None:
        if completed != 1:
            return
        if change == "team_chart":
            identity = catalog["a"]
            chart, metadata = teams[identity]
            teams[identity] = (
                team_chart(chart.name, season=chart.season, offense=17, defense=0),
                metadata,
            )
        elif change == "manifest":
            report["teams"]["a"]["conference"] = "synthetic-late-change"
        elif change == "catalog":
            catalog["a"] = catalog["b"]
        else:
            targets["a"]["offense"]["completion"] = 0.999
        changed.append(change)

    with pytest.raises(ValueError, match="frozen simulation inputs"):
        run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            output,
            repetitions=1,
            master_seed=481,
            domain="training",
            progress=progress,
        )
    assert changed == [change]
    assert not (output / "summary.json").exists()

    rejection = json.loads(next(output.glob("rejected-inputs-*.json")).read_text())
    assert rejection["changed_components"] == [{"team_chart": "teams"}.get(change, change)]
    assert (output / "game-000001.json").exists()


@pytest.mark.parametrize("boundary", ("summary", "resume", "publication"))
def test_late_summary_and_resume_only_refuse_changed_original_preserving_evidence(
    tmp_path: Path, boundary: str
) -> None:
    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / boundary
    options = {"repetitions": 1, "master_seed": 481, "domain": "training"}
    prior = None
    if boundary == "resume":
        run_historical_batch(report, teams, catalog, targets, output, **options)
        prior = (output / "summary.json").read_bytes()
    changed = []
    target_code = (
        cohort_simulation.summarize_cohort.__code__
        if boundary == "summary"
        else cohort_simulation._run_frozen_batch.__code__
    )

    def observe(frame: FrameType, event: str, argument: Any) -> None:
        expected_event = "return" if boundary == "publication" else "call"
        if not changed and event == expected_event and frame.f_code is target_code:
            report["teams"]["a"]["conference"] = "late original edit"
            changed.append(boundary)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        with pytest.raises(ValueError, match="frozen simulation inputs"):
            run_historical_batch(
                report, teams, catalog, targets, output, resume=boundary == "resume", **options
            )
    finally:
        sys.setprofile(previous)
    assert changed == [boundary]
    assert list(output.glob("rejected-inputs-*.json"))
    if prior is None:
        assert not (output / "summary.json").exists()
        if boundary == "publication":
            rejected = json.loads(next(output.glob("rejected-summary-*.json")).read_text())
            assert rejected["failed_games"] == 0
            assert "late original edit" not in rejected["conferences"]
    else:
        assert (output / "summary.json").read_bytes() == prior


def test_transient_caller_edit_during_actual_game_does_not_change_frozen_computation(
    tmp_path: Path,
) -> None:
    report, targets, catalog, teams = prepared(tmp_path)
    options = {"repetitions": 1, "master_seed": 481, "domain": "training"}
    baseline = tmp_path / "private-data" / "baseline"
    run_historical_batch(report, teams, catalog, targets, baseline, **options)
    output = tmp_path / "private-data" / "transient"
    identity = catalog["a"]
    original = teams[identity]
    changed = []

    def observe(frame: FrameType, event: str, argument: Any) -> None:
        if frame.f_code is not cohort_simulation._execute_run.__code__:
            return
        if event == "call":
            chart, meta = original
            teams[identity] = (team_chart(chart.name, season=chart.season, offense=17), meta)
            changed.append("call")
        elif event == "return":
            teams[identity] = original
            changed.append("return")

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        result = run_historical_batch(report, teams, catalog, targets, output, **options)
    finally:
        sys.setprofile(previous)
        teams[identity] = original
    assert changed == ["call", "return", "call", "return"]
    assert result["failed_games"] == 0
    for number in (1, 2):
        filename = f"game-{number:06d}.json"
        expected = json.loads((baseline / filename).read_text())
        actual = json.loads((output / filename).read_text())
        assert actual == expected
        assert actual["result"]["research_inputs_sha256"] == result["research_inputs_sha256"]
        assert set(actual["result"]["consumed_chart_sha256"]) == set(
            actual["result"]["teams"].values()
        )


@pytest.mark.parametrize("field", ("research_inputs_sha256", "consumed_chart_sha256"))
def test_retained_game_cannot_omit_or_repin_complete_input_binding(
    tmp_path: Path, field: str
) -> None:
    from tools.chartgen.cohort_report import canonical_hash

    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "tampered-receipt"
    options = {"repetitions": 1, "master_seed": 481, "domain": "training"}
    run_historical_batch(report, teams, catalog, targets, output, **options)
    prior = (output / "summary.json").read_bytes()
    artifact = output / "game-000001.json"
    value = json.loads(artifact.read_text())
    value["result"].pop(field)
    value["result_sha256"] = canonical_hash(value["result"])
    artifact.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="frozen simulation inputs.*game receipt"):
        run_historical_batch(report, teams, catalog, targets, output, resume=True, **options)
    assert (output / "summary.json").read_bytes() == prior
    assert json.loads(artifact.read_text()) == value
    rejection = json.loads(next(output.glob("rejected-inputs-*.json")).read_text())
    assert rejection["stage"] == "game receipt"
    assert rejection["side"] == "worker"


@pytest.mark.parametrize("change", ("cycle", "nonfinite", "unsupported"))
def test_invalid_worker_catalog_retains_structured_hash_only_refusal(
    change: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.chartgen.cohort_simulation import FixtureRun, _execute_run
    from tools.chartgen.research_inputs import FrozenResearchInputs, InputConsistencyError
    from tools.chartgen.scope import HistoricalGame

    catalog = {"a": "2026/a", "b": "2026/b"}
    frozen = FrozenResearchInputs.capture(teams={}, manifest={}, catalog=catalog, targets={})
    monkeypatch.setattr(
        cohort_simulation,
        "_WORKER_RESEARCH_INPUTS",
        json.dumps({"identity": frozen.identity, "complete": True}).encode(),
    )
    run = FixtureRun(1, HistoricalGame("g", 2026, "a", "b"), 0, "training", 1)
    if change == "cycle":
        catalog["bad"] = catalog
    elif change == "nonfinite":
        catalog["bad"] = float("nan")
    else:
        catalog["bad"] = object()
    with pytest.raises(
        InputConsistencyError, match="frozen simulation inputs.*worker catalog"
    ) as e:
        _execute_run((run, catalog, False))
    assert e.value.evidence["changed_components"] == ["catalog"]
    assert e.value.evidence["observed"]["components"]["catalog"].startswith("invalid:")


@pytest.mark.parametrize("resume", (False, True))
def test_duplicate_chart_name_admission_precedes_game_and_resume_consumption(
    tmp_path: Path,
    resume: bool,
) -> None:
    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "duplicate-admission"
    options = {"repetitions": 1, "master_seed": 481, "domain": "training"}
    prior = None
    if resume:
        run_historical_batch(report, teams, catalog, targets, output, **options)
        prior = (output / "summary.json").read_bytes()
    chart, meta = teams[catalog["b"]]
    teams[catalog["b"]] = (replace(chart, name=teams[catalog["a"]][0].name), meta)
    calls = []

    def observe(frame: FrameType, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code is cohort_simulation._execute_run.__code__:
            calls.append(True)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        with pytest.raises(ValueError, match="duplicate chart names"):
            run_historical_batch(report, teams, catalog, targets, output, resume=resume, **options)
    finally:
        sys.setprofile(previous)
    assert calls == []
    if prior is None:
        assert not output.exists()
    else:
        assert (output / "summary.json").read_bytes() == prior


def test_changed_unused_worker_chart_refused_before_engine_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.synthetic_teams import metadata
    from tools.chartgen.cohort_simulation import FixtureRun, _execute_run
    from tools.chartgen.research_inputs import FrozenResearchInputs, InputConsistencyError
    from tools.chartgen.scope import HistoricalGame

    teams = {f"2026/{key}": (team_chart(key.upper()), metadata()) for key in ("a", "b", "c")}
    catalog = {key: f"2026/{key}" for key in ("a", "b", "c")}
    frozen = FrozenResearchInputs.capture(teams=teams, manifest={}, catalog=catalog, targets={})
    worker_teams = frozen.values["teams"]
    chart, meta = worker_teams["2026/c"]
    worker_teams["2026/c"] = (replace(chart, name="A"), meta)
    monkeypatch.setattr(cohort_simulation, "_WORKER_TEAMS", worker_teams)
    monkeypatch.setattr(
        cohort_simulation,
        "_WORKER_RESEARCH_INPUTS",
        json.dumps({"identity": frozen.identity, "complete": True}).encode(),
    )
    run = FixtureRun(1, HistoricalGame("g", 2026, "a", "b"), 0, "training", 1)

    def refuse_unchecked_engine_entry(frame: FrameType, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code is cohort_simulation._play_one.__code__:
            raise AssertionError("changed observer-only chart reached engine entry")

    previous = sys.getprofile()
    sys.setprofile(refuse_unchecked_engine_entry)
    try:
        with pytest.raises(InputConsistencyError, match="frozen simulation inputs.*worker charts"):
            _execute_run((run, frozen.values["catalog"], False))
    finally:
        sys.setprofile(previous)


@pytest.mark.parametrize("changed", (False, True))
def test_engine_failure_retains_changed_worker_input_refusal_without_inventing_it(
    monkeypatch: pytest.MonkeyPatch,
    changed: bool,
) -> None:
    from tests.synthetic_teams import metadata
    from tools.chartgen.cohort_simulation import FixtureRun, _execute_run
    from tools.chartgen.research_inputs import FrozenResearchInputs, InputConsistencyError
    from tools.chartgen.scope import HistoricalGame

    teams = {f"2026/{key}": (team_chart(key.upper()), metadata()) for key in ("a", "b", "c")}
    catalog = {key: f"2026/{key}" for key in ("a", "b", "c")}
    frozen = FrozenResearchInputs.capture(teams=teams, manifest={}, catalog=catalog, targets={})
    monkeypatch.setattr(cohort_simulation, "_WORKER_TEAMS", frozen.values["teams"])
    monkeypatch.setattr(
        cohort_simulation,
        "_WORKER_RESEARCH_INPUTS",
        json.dumps({"identity": frozen.identity, "complete": True}).encode(),
    )
    run = FixtureRun(1, HistoricalGame("g", 2026, "a", "b"), 0, "training", 1)

    class StoppedBeforeGame(RuntimeError):
        pass

    def stop_at_engine_entry(frame: FrameType, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code is cohort_simulation._play_one.__code__:
            if changed:
                chart, meta = cohort_simulation._WORKER_TEAMS["2026/c"]
                cohort_simulation._WORKER_TEAMS["2026/c"] = (replace(chart, name="A"), meta)
            raise StoppedBeforeGame("test boundary; engine body did not execute")

    previous = sys.getprofile()
    sys.setprofile(stop_at_engine_entry)
    try:
        expected = InputConsistencyError if changed else StoppedBeforeGame
        with pytest.raises(expected):
            _execute_run((run, frozen.values["catalog"], False))
    finally:
        sys.setprofile(previous)


@pytest.mark.parametrize("changed", (False, True))
def test_engine_failure_retains_changed_catalog_refusal_without_inventing_it(
    monkeypatch: pytest.MonkeyPatch,
    changed: bool,
) -> None:
    from tests.synthetic_teams import metadata
    from tools.chartgen.cohort_simulation import FixtureRun, _execute_run
    from tools.chartgen.research_inputs import FrozenResearchInputs, InputConsistencyError
    from tools.chartgen.scope import HistoricalGame

    teams = {f"2026/{key}": (team_chart(key.upper()), metadata()) for key in ("a", "b", "c")}
    catalog = {key: f"2026/{key}" for key in ("a", "b", "c")}
    frozen = FrozenResearchInputs.capture(teams=teams, manifest={}, catalog=catalog, targets={})
    monkeypatch.setattr(cohort_simulation, "_WORKER_TEAMS", frozen.values["teams"])
    monkeypatch.setattr(
        cohort_simulation,
        "_WORKER_RESEARCH_INPUTS",
        json.dumps({"identity": frozen.identity, "complete": True}).encode(),
    )
    run = FixtureRun(1, HistoricalGame("g", 2026, "a", "b"), 0, "training", 1)

    class StoppedBeforeGame(RuntimeError):
        pass

    def stop_at_engine_entry(frame: FrameType, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code is cohort_simulation._play_one.__code__:
            if changed:
                frozen.values["catalog"]["c"] = "2026/a"
            raise StoppedBeforeGame("test boundary; engine body did not execute")

    previous = sys.getprofile()
    sys.setprofile(stop_at_engine_entry)
    try:
        expected = InputConsistencyError if changed else StoppedBeforeGame
        with pytest.raises(expected):
            _execute_run((run, frozen.values["catalog"], False))
    finally:
        sys.setprofile(previous)


@pytest.mark.parametrize("boundary", ("engine", "observer"))
def test_changed_observer_only_chart_rejected_before_successful_batch_retention(
    tmp_path: Path,
    boundary: str,
) -> None:
    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "worker-observer-footprint"
    original_name = teams[catalog["c"]][0].name
    changed = []
    observed = []
    target_code = (
        cohort_simulation._play_one.__code__
        if boundary == "engine"
        else cohort_simulation.observe_chart_draws.__code__
    )

    def observe(frame: FrameType, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code is cohort_simulation.observe_chart_draws.__code__:
            observed.append("draw")
        if event == "call" and frame.f_code is cohort_simulation.observe_primary_results.__code__:
            observed.append("primary")
        if not changed and event == "return" and frame.f_code is target_code:
            chart, meta = cohort_simulation._WORKER_TEAMS[catalog["c"]]
            name = cohort_simulation._WORKER_TEAMS[catalog["a"]][0].name
            cohort_simulation._WORKER_TEAMS[catalog["c"]] = (replace(chart, name=name), meta)
            changed.append(boundary)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        with pytest.raises(ValueError, match="frozen simulation inputs.*worker charts"):
            run_historical_batch(
                report,
                teams,
                catalog,
                targets,
                output,
                repetitions=1,
                master_seed=481,
                domain="training",
            )
    finally:
        sys.setprofile(previous)
    assert changed == [boundary]
    assert teams[catalog["c"]][0].name == original_name
    assert observed == ([] if boundary == "engine" else ["draw", "primary"])
    assert not (output / "summary.json").exists()
    assert not (output / "game-000001.json").exists()
    evidence = json.loads(next(output.glob("rejected-inputs-*.json")).read_text())
    assert evidence["stage"] == "worker charts"
    assert evidence["changed_components"] == ["teams"]
