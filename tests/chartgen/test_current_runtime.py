"""Current research execution must use the independently reviewed release context."""

from pathlib import Path
from types import FrameType

import pytest

from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.difficulty import DifficultyCoach
from tests.synthetic_teams import team_chart
from tools.chartgen.cohort_simulation import _execute_run, _initialize_worker, fixture_runs

from .test_cohort_simulation import prepared


def test_reviewed_current_engine_tier_is_fifteen() -> None:
    assert CURRENT_DIFFICULTY_VERSION == 15


def test_reviewed_contract_binds_optional_source_authorities() -> None:
    import hashlib

    from tools.chartgen import current_runtime

    root = Path(current_runtime.__file__).resolve().parents[2]
    contract = current_runtime.read_contract(
        Path(current_runtime.__file__).with_name("research-runtime-contract.json"),
        expected_sha256=current_runtime.REVIEWED_CONTRACT_SHA256,
    )
    required = {
        "tools/chartgen/optional_flags.py",
        "tools/chartgen/evidence.py",
        "tools/chartgen/source.py",
        "tools/chartgen/source_exposure.py",
        "tools/chartgen/readiness.py",
    }
    assert required <= set(contract["runtime_files"])
    for name in required:
        assert (
            contract["runtime_files"][name]
            == hashlib.sha256((root / name).read_bytes()).hexdigest()
        )


def test_reviewed_contract_binds_actual_field_goal_diagnostic() -> None:
    import hashlib

    from tools.chartgen import current_runtime

    root = Path(current_runtime.__file__).resolve().parents[2]
    contract = current_runtime.read_contract(
        Path(current_runtime.__file__).with_name("research-runtime-contract.json"),
        expected_sha256=current_runtime.REVIEWED_CONTRACT_SHA256,
    )
    name = "tools/chartgen/field_goals.py"
    assert name in contract["runtime_files"]
    assert contract["runtime_files"][name] == hashlib.sha256((root / name).read_bytes()).hexdigest()


def test_reviewed_contract_binds_numeric_source_selection() -> None:
    import hashlib

    from tools.chartgen import current_runtime

    root = Path(current_runtime.__file__).resolve().parents[2]
    contract = current_runtime.read_contract(
        Path(current_runtime.__file__).with_name("research-runtime-contract.json"),
        expected_sha256=current_runtime.REVIEWED_CONTRACT_SHA256,
    )
    name = "tools/chartgen/generate.py"
    assert name in contract["runtime_files"]
    assert contract["runtime_files"][name] == hashlib.sha256((root / name).read_bytes()).hexdigest()


def test_reviewed_current_hard_constructor_is_supported() -> None:
    coach = DifficultyCoach(481, team_chart("Home"), team_chart("Away"), "hard", version=15)
    assert coach.version == 15 and coach.mode == "hard"


@pytest.mark.parametrize("domain", ("training", "heldout", "coaching"))
def test_real_research_worker_uses_current_reference_policy_in_every_domain(
    tmp_path: Path, domain: str
) -> None:
    report, _, catalog, teams = prepared(tmp_path)
    run = fixture_runs(report, repetitions=1, master_seed=481, domain=domain)[0]
    _initialize_worker(teams)
    result = _execute_run((run, catalog, False))
    assert result["status"] == "passed", result["error"]
    configuration = result["configuration"]
    assert configuration["engine_coach_policy"] == "hard-v15"
    assert configuration["simulation_coach_policy"] == "baseline-v15"
    assert "decision_coach_policy" not in configuration  # Engine owns current decisions.


@pytest.mark.parametrize("change", ("changed", "missing", "extra", "nested_extra"))
def test_reviewed_package_inventory_rejects_changed_missing_and_recursive_extra_source(
    tmp_path: Path, change: str
) -> None:
    import hashlib

    from tools.chartgen.current_runtime import verify_source_inventory

    package = tmp_path / "bowl_bound"
    package.mkdir()
    source = package / "core.py"
    source.write_text("VALUE = 1\n")
    expected = {"bowl_bound/core.py": hashlib.sha256(source.read_bytes()).hexdigest()}
    assert verify_source_inventory(tmp_path, expected, package="bowl_bound") == expected
    if change == "changed":
        source.write_text("VALUE = 2\n")
    elif change == "missing":
        source.unlink()
    else:
        extra = package / ("nested/extra.py" if change == "nested_extra" else "extra.py")
        extra.parent.mkdir(exist_ok=True)
        extra.write_text("VALUE = 3\n")
    with pytest.raises(ValueError, match="reviewed.*source"):
        verify_source_inventory(tmp_path, expected, package="bowl_bound")


def test_source_anchor_must_match_bytes_used_by_loaded_runtime_attestation() -> None:
    from tools.chartgen.current_runtime import verify_attested_sources

    reviewed = {"bowl_bound/core.py": "a" * 64}
    attestation = {
        "runtime_modules": {
            "bowl_bound.core": {
                "path": "bowl_bound/core.py",
                "source_sha256": "a" * 64,
            }
        }
    }
    verify_attested_sources(attestation, reviewed)
    # Files could be restored by the later path check: the consulted bytes matter.
    attestation["runtime_modules"]["bowl_bound.core"]["source_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="reviewed.*attested"):
        verify_attested_sources(attestation, reviewed)


@pytest.mark.parametrize("change", ("engine", "runner", "observer", "reference_policy"))
def test_contract_cannot_be_replaced_by_a_candidate_selected_pin(
    tmp_path: Path, change: str
) -> None:
    import hashlib
    import json

    from tools.chartgen.current_runtime import read_contract

    body = {
        "engine": "approved",
        "runner": "approved",
        "observer": "approved",
        "reference_policy": {"away": "hard-v15", "home": "baseline-v15"},
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    approved = hashlib.sha256(encoded).hexdigest()
    path = tmp_path / "contract.json"
    path.write_bytes(encoded)
    assert read_contract(path, expected_sha256=approved) == body
    body[change] = "candidate selected substitute"
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="reviewed.*contract"):
        read_contract(path, expected_sha256=approved)


def test_recorded_current_engine_verification_requires_boolean_true() -> None:
    from tools.chartgen.refine import engine_identity
    from tools.chartgen.runtime_identity import require_runtime_identity

    current = engine_identity()
    require_runtime_identity(current, current)
    recorded = {**current, "reviewed_engine_verified": 1}
    with pytest.raises(ValueError, match="runtime identity differs"):
        require_runtime_identity(recorded, current)


def test_current_reference_metadata_names_ordinary_and_pending_roles_explicitly() -> None:
    from tools.chartgen.refine import engine_identity

    reference = engine_identity()["reference_configuration"]
    assert reference["ordinary_home"] == "baseline-v15"
    assert reference["ordinary_away"] == "hard-v15"
    assert reference["pending_and_clock"] == "hard-v15"
    assert "home" not in reference and "away" not in reference


@pytest.mark.parametrize("change", ("v10", "vague", "missing_pending"))
def test_old_or_vague_reference_roles_cannot_reuse_current_evidence(change: str) -> None:
    from tools.chartgen.refine import engine_identity
    from tools.chartgen.runtime_identity import require_runtime_identity

    current = engine_identity()
    reference = dict(current["reference_configuration"])
    if change == "v10":
        reference["pending_and_clock"] = "baseline-v10"
    elif change == "vague":
        reference["home"] = reference.pop("ordinary_home")
        reference["away"] = reference.pop("ordinary_away")
    else:
        reference.pop("pending_and_clock")
    with pytest.raises(ValueError, match="runtime identity differs"):
        require_runtime_identity({**current, "reference_configuration": reference}, current)


def test_real_runner_consumes_role_specific_current_policies_and_replays(tmp_path: Path) -> None:
    import sys

    from bowl_bound.coaching import BaselineCoach
    from bowl_bound.save_game import SavedGame
    from tools.chartgen.current_runtime import reference_options
    from tools.chartgen.research_runner import GameSpec, _offense_choice, _play_one

    report, _, catalog, teams = prepared(tmp_path)
    run = fixture_runs(report, repetitions=1, master_seed=481, domain="training")[0]
    spec = GameSpec(run.number, 2007, catalog[run.game.away], catalog[run.game.home], run.seed)
    committed = []
    ordinary_human = []
    assessed_clock = []

    def observe(frame: FrameType, event: str, argument: object) -> None:
        if event == "return" and frame.f_code is SavedGame._coach_step_with_choice.__code__:
            local = frame.f_locals
            plan, view, game = local["plan"], local["view"], local["self"]
            if plan.computer_choice is None:
                return
            phase = (
                "clock"
                if view.phase == "clock_choice" and plan.operation == "decide"
                else "pending"
                if view.pending is not None and plan.operation == "decide"
                else "ordinary"
            )
            side = "away" if local["human_side"] == "home" else "home"
            committed.append(
                (phase, side, type(game._coach), game._coach.version, game._coach.mode)
            )
        elif event == "call" and frame.f_code is DifficultyCoach.clock_decision.__code__:
            from bowl_bound.coaching_session import plan_turn

            if frame.f_back.f_code is plan_turn.__code__:
                coach, observation = frame.f_locals["self"], frame.f_locals["observation"]
                assessed_clock.append((observation.side, type(coach), coach.version, coach.mode))
        elif event == "call" and frame.f_code in (
            BaselineCoach.offense.__code__,
            BaselineCoach.defense.__code__,
        ):
            if frame.f_back.f_code not in (_offense_choice.__code__, _play_one.__code__):
                return  # Exclude predictive analysis and inherited internal calls.
            coach, observation = frame.f_locals["self"], frame.f_locals["observation"]
            ordinary_human.append((observation.side, type(coach), coach.version))

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        result = _play_one(spec, teams, verify_replay=True, **reference_options())
    finally:
        sys.setprofile(previous)
    assert result["status"] == "passed", result.get("error")
    assert ordinary_human and set(ordinary_human) == {("home", BaselineCoach, 15)}
    assert {row[:2] for row in committed} == {
        ("ordinary", "away"),
        ("pending", "home"),
        ("pending", "away"),
    }, committed
    assert {row[2:] for row in committed} == {(DifficultyCoach, 15, "hard")}
    assert set(assessed_clock) == {(side, DifficultyCoach, 15, "hard") for side in ("home", "away")}
    assert result["save_replay"]["checkpoint_verified"]
    assert result["save_replay"]["final_replay_verified"]


@pytest.mark.parametrize("side", ("home", "away"))
def test_current_engine_commits_pending_clock_choice_for_either_side(side: str) -> None:
    from bowl_bound.save_game import dumps_game, loads_game
    from tests.test_late_half_cpu_clock_contract import chart_loader, saved_scoring_opportunity
    from tools.chartgen.current_runtime import REFERENCE_COACH_POLICY

    old = saved_scoring_opportunity(side, "hard")
    current = loads_game(dumps_game(old), chart_loader(old))
    assert current._coach.policy == REFERENCE_COACH_POLICY
    before = current.view()
    assert before.phase == "clock_choice" and before.normal_timing_ends_period
    human_side = "away" if side == "home" else "home"
    assert current.coach_view(human_side)[1].automatic
    current.coach_step(human_side)
    after = current.view()
    assert after.clock.remaining == before.clock.remaining - 10
    assert after.clock.timeouts == ((2, 3) if side == "home" else (3, 2))
    assert after.state == before.state and after.log == before.log
    restored = loads_game(dumps_game(current), chart_loader(old), preserve_development_policy=True)
    assert restored.view() == after and restored._coach.policy == REFERENCE_COACH_POLICY


def test_current_identity_binds_all_source_files_and_loaded_module_subset() -> None:
    import json

    from tools.chartgen.current_runtime import SOURCE_ONLY_ENGINE_PATHS
    from tools.chartgen.refine import engine_identity

    identity = engine_identity()
    contract = json.loads(Path("tools/chartgen/research-runtime-contract.json").read_text())
    package = contract["engine_files"]
    assert len(package) == 40
    assert "bowl_bound/rules_summary.py" in package
    assert SOURCE_ONLY_ENGINE_PATHS == ("bowl_bound/__main__.py",)
    loaded = {
        entry["path"]
        for name, entry in identity["runtime_modules"].items()
        if name == "bowl_bound" or name.startswith("bowl_bound.")
    }
    assert loaded == set(package) - set(SOURCE_ONLY_ENGINE_PATHS)
    assert len(loaded) == 39
