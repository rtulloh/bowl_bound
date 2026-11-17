"""Research attestations describe the code actually imported, never another tree."""

import shutil
import subprocess
import sys
from collections.abc import Callable
from contextlib import contextmanager
from functools import lru_cache, wraps
from pathlib import Path
from reprlib import recursive_repr
from types import FunctionType, ModuleType

import pytest

import bowl_bound.dice
import bowl_bound.models
import tools.chartgen.research_runner
from tools.chartgen import cohort_simulation, refine
from tools.chartgen.runtime_identity import require_runtime_identity


def test_identity_attests_matching_runtime_origins_and_components() -> None:
    identity = refine.engine_identity()
    assert identity["runtime_identity_version"] == 2
    assert identity["runtime_origins_verified"] is True
    assert identity["runtime_modules"]["bowl_bound.models"]["path"] == "bowl_bound/models.py"
    assert identity["runtime_modules"]["tools.chartgen.research_runner"]["path"] == (
        "tools/chartgen/research_runner.py"
    )
    assert len(identity["runtime_code_sha256"]) == 64


@pytest.mark.parametrize("module", (bowl_bound.models, tools.chartgen.research_runner, refine))
def test_identity_rejects_foreign_import_origin_even_for_identical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: ModuleType
) -> None:
    original = Path(module.__file__)
    foreign = tmp_path / original.name
    foreign.write_bytes(original.read_bytes())
    monkeypatch.setattr(module, "__file__", str(foreign))
    with pytest.raises(ValueError, match="runtime.*origin"):
        refine.engine_identity()


def test_identity_rejects_foreign_bound_harness_callable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace: dict[str, object] = {}
    exec(
        compile("def _play_one(*args, **kwargs): return {}", str(tmp_path / "foreign.py"), "exec"),
        namespace,
    )
    monkeypatch.setattr(refine, "_play_one", namespace["_play_one"])
    with pytest.raises(ValueError, match="runtime.*callable"):
        refine.engine_identity()


def test_identity_rejects_altered_loaded_code_with_unchanged_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tools.chartgen.research_runner.stable_seed
    namespace: dict[str, object] = {}
    exec(
        compile(
            "def stable_seed(master, identity): return 17", target.__code__.co_filename, "exec"
        ),
        namespace,
    )
    monkeypatch.setattr(target, "__code__", namespace["stable_seed"].__code__)
    with pytest.raises(ValueError, match="runtime.*code"):
        refine.engine_identity()


def test_source_function_cannot_hide_changed_code_with_generated_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace: dict[str, object] = {}
    exec(
        compile("def stable_seed(master, identity): return 17", "<review-probe>", "exec"), namespace
    )
    monkeypatch.setattr(
        tools.chartgen.research_runner.stable_seed, "__code__", namespace["stable_seed"].__code__
    )
    with pytest.raises(ValueError, match="runtime.*(code|callable)"):
        refine.engine_identity()


def test_dataclass_handwritten_method_cannot_claim_generated_exemption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace: dict[str, object] = {}
    exec(compile("def __post_init__(self): return None", "<string>", "exec"), namespace)
    monkeypatch.setattr(
        bowl_bound.models.TeamChart.__post_init__, "__code__", namespace["__post_init__"].__code__
    )
    with pytest.raises(ValueError, match="runtime.*(code|callable)"):
        refine.engine_identity()


def test_wrapper_cannot_hide_the_code_that_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    original = bowl_bound.dice.RandomDice.offensive

    @wraps(original)
    def changed(self: object) -> None:
        return None

    monkeypatch.setattr(bowl_bound.dice.RandomDice, "offensive", changed)
    with pytest.raises(ValueError, match="runtime.*(code|callable)"):
        refine.engine_identity()


def test_source_function_cannot_borrow_sibling_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tools.chartgen.research_runner.stable_seed,
        "__code__",
        tools.chartgen.research_runner._period_for_score.__code__,
    )
    with pytest.raises(ValueError, match="runtime.*code"):
        refine.engine_identity()


def test_handwritten_body_requires_its_actual_module_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = bowl_bound.dice.RandomDice.offensive
    context = {**original.__globals__, "BLACK_FACES": (3,) * 6}
    replacement = FunctionType(
        original.__code__, context, original.__name__, original.__defaults__, original.__closure__
    )
    monkeypatch.setattr(bowl_bound.dice.RandomDice, "offensive", replacement)
    with pytest.raises(ValueError, match="runtime.*globals"):
        refine.engine_identity()


def test_generated_repr_can_use_source_attested_reprlib_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tools.chartgen.research_runner.GameSpec.__repr__.__wrapped__
    replacement = recursive_repr()(original)
    replacement.__wrapped__ = original  # Python 3.13's dataclass repr contract.
    monkeypatch.setattr(tools.chartgen.research_runner.GameSpec, "__repr__", replacement)
    identity = refine.engine_identity()
    assert "reprlib" in identity["standard_wrapper_sources"]


@pytest.mark.parametrize("decorate", (contextmanager, lru_cache(maxsize=4)))
def test_known_wrapper_requires_authority_in_source_declaration(
    monkeypatch: pytest.MonkeyPatch,
    decorate: Callable[[Callable[..., object]], Callable[..., object]],
) -> None:
    original = bowl_bound.dice.RandomDice.offensive
    monkeypatch.setattr(bowl_bound.dice.RandomDice, "offensive", decorate(original))
    with pytest.raises(ValueError, match="runtime.*(wrapper|cache)"):
        refine.engine_identity()


def test_real_mixed_checkout_import_cannot_attest_local_engine(tmp_path: Path) -> None:
    root = Path(refine.__file__).resolve().parents[2]
    foreign = tmp_path / "other-checkout"
    shutil.copytree(
        root / "bowl_bound", foreign / "bowl_bound", ignore=shutil.ignore_patterns("__pycache__")
    )
    program = (
        "import sys; "
        f"sys.path[:0] = [{str(foreign)!r}, {str(root)!r}]; "
        "from tools.chartgen.refine import engine_identity; engine_identity()"
    )
    result = subprocess.run(
        [sys.executable, "-c", program], cwd=tmp_path, text=True, capture_output=True
    )
    assert result.returncode != 0, "foreign engine was silently attested as the local checkout"
    assert "runtime" in result.stderr and "origin" in result.stderr


def test_identity_rejects_foreign_worker_harness_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace: dict[str, object] = {}
    exec(
        compile("def _play_one(*args, **kwargs): return {}", str(tmp_path / "foreign.py"), "exec"),
        namespace,
    )
    monkeypatch.setattr(cohort_simulation, "_play_one", namespace["_play_one"])
    with pytest.raises(ValueError, match="runtime.*callable"):
        refine.engine_identity()


def test_worker_initialization_checks_its_own_loaded_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bowl_bound.models, "__file__", str(tmp_path / "models.py"))
    with pytest.raises(ValueError, match="runtime.*origin"):
        cohort_simulation._initialize_worker({})


def test_identity_rejects_changed_harness_policy_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools.chartgen.research_runner, "MAX_GAME_ACTIONS", 3)
    with pytest.raises(ValueError, match="runtime.*constant"):
        refine.engine_identity()


def test_identity_rejects_changed_bound_function_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools.chartgen.research_runner._play_one, "__kwdefaults__", {})
    with pytest.raises(ValueError, match="runtime.*defaults"):
        refine.engine_identity()


def test_contextmanager_wrapper_closure_must_execute_its_declared_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.coaching_audit_sampling import capture_preferences

    target = capture_preferences.__closure__[0]
    monkeypatch.setattr(target, "cell_contents", lambda: None)
    with pytest.raises(ValueError, match="runtime.*closure"):
        refine.engine_identity()


@pytest.mark.parametrize("change", ("code", "defaults"))
def test_generated_body_observation_cannot_reuse_reviewed_runtime(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    recorded = refine.engine_identity()
    if change == "code":
        namespace: dict[str, object] = {}
        exec(compile("def __eq__(self, other): return True", "<string>", "exec"), namespace)
        monkeypatch.setattr(
            tools.chartgen.research_runner.GameSpec.__eq__, "__code__", namespace["__eq__"].__code__
        )
    else:
        monkeypatch.setattr(
            tools.chartgen.research_runner.GameSpec.__init__, "__defaults__", ("changed",)
        )
    current = refine.engine_identity()
    assert (
        current["runtime_modules"]["tools.chartgen.research_runner"]["observed_generated_methods"]
        > 0
    )
    assert current["runtime_code_sha256"] != recorded["runtime_code_sha256"]
    with pytest.raises(ValueError, match="runtime identity"):
        require_runtime_identity(recorded, current)


@pytest.mark.parametrize("mutation", ("missing", "extra", "optimize", "code"))
def test_reviewed_identity_requires_exact_runtime_inventory(mutation: str) -> None:
    from copy import deepcopy

    current = refine.engine_identity()
    recorded = deepcopy(current)
    require_runtime_identity(recorded, current)
    if mutation == "missing":
        recorded["runtime_modules"].pop("bowl_bound.models")
    elif mutation == "extra":
        recorded["required_runtime_modules"].append("bowl_bound.synthetic_extra")
    elif mutation == "optimize":
        recorded["python_optimize"] += 1
    else:
        recorded["runtime_code_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="runtime identity"):
        require_runtime_identity(recorded, current)


def test_batch_refuses_runtime_change_after_last_game(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from .test_cohort_simulation import prepared

    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "late-runtime-change"

    def late_change(done: int, total: int, status: str) -> None:
        if done == total:
            monkeypatch.setattr(tools.chartgen.research_runner, "MAX_GAME_ACTIONS", 3)

    with pytest.raises(ValueError, match="runtime.*constant"):
        cohort_simulation.run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            output,
            repetitions=1,
            master_seed=77,
            domain="training",
            progress=late_change,
        )
    assert not (output / "summary.json").exists()


def test_worker_refuses_different_reviewed_runtime() -> None:
    expected = refine.engine_identity()
    expected["runtime_code_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="runtime identity"):
        cohort_simulation._initialize_worker({}, expected)


@pytest.mark.parametrize("mutation", ("legacy", "tool", "policy", "unverified"))
def test_refinement_rejects_stale_runtime_contract_before_source_reuse(
    tmp_path: Path, mutation: str
) -> None:
    from tools.chartgen.cohort_refinement import run_cohort_refinement
    from tools.chartgen.cohort_report import write_matchup_report
    from tools.chartgen.scope import build_slate, qualified_games, slate_targets

    from .test_scope import events, game, members

    schedule = [game("ab", "a", "b")]
    source = events("ab", "a", "b")
    slate = build_slate(
        schedule,
        members(),
        generated_teams={"a", "b"},
        game_evidence=qualified_games(source, schedule),
        season=2007,
        major_conferences={"alpha"},
    )
    targets = slate_targets(source, slate)
    identity = refine.engine_identity()
    if mutation == "legacy":
        identity.pop("runtime_identity_version")
    elif mutation == "tool":
        identity["tool_sha256"] = "0" * 64
    elif mutation == "policy":
        identity["training_policy"] = "different policy"
    else:
        identity["runtime_origins_verified"] = False
    report = write_matchup_report(
        tmp_path / "private-data" / "review",
        slate,
        targets,
        source={},
        engine=identity,
        profiles_sha256="neutral",
        chart_qualifications={},
    )
    with pytest.raises(ValueError, match="runtime identity"):
        run_cohort_refinement(
            source,
            report,
            targets,
            tmp_path / "private-data" / "candidate",
            reviewed_manifest_sha256=report["manifest_sha256"],
        )
