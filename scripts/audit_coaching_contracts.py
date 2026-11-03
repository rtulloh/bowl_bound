"""Prove AI-010 regressions detect deliberate faults in isolated source copies.

Run with the project's supported Python interpreter. The live checkout is never
modified. A passing audit requires each mutant to fail an actual assertion in its
designated regression, rather than fail collection or crash the test process.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass(frozen=True)
class Mutation:
    """A single reversible fault and the contract that must detect it."""

    name: str
    module: str
    before: str
    after: str
    test: str


MUTATIONS = (
    Mutation(
        "rejected human call learns history",
        "save_game",
        "if human_call not in plan.human_legal:\n",
        "if human_call not in plan.human_legal:\n"
        '                    self._coach.commit_call("home", "1", "A")\n',
        "hard_previews_and_rejected_steps",
    ),
    Mutation(
        "pending save replay omits learned calls",
        "save_game",
        'if operation == "snap" and result is not None and result.supported:',
        'if operation == "snap" and result is not None and result.supported '
        "and not self._tape.replaying:",
        "each_tier_resumes_pending_engine_procedures",
    ),
    Mutation(
        "decision preview mutates history",
        "coaching",
        "choices = observation.choices",
        'self.commit_call("home", "1", "A")\n        choices = observation.choices',
        "every_coaching_branch",
    ),
    Mutation(
        "offense selection mutates a team chart",
        "difficulty",
        "observation = self._situational_offense(observation)",
        'object.__setattr__(self._home, "name", "mutated")\n'
        "        observation = self._situational_offense(observation)",
        "every_coaching_branch",
    ),
    Mutation(
        "preview learns uncommitted calls",
        "save_game",
        "return view, plan_turn(view, human_side, self._coach).turn",
        'self._coach.commit_call("home", "1", "A")\n'
        "            return view, plan_turn(view, human_side, self._coach).turn",
        "hard_previews_and_rejected_steps",
    ),
    Mutation(
        "replay loses recent history",
        "save_game",
        "return result\n\n    def snap",
        'self._coach._recent[("home", "offense")].clear()\n        return result\n\n    def snap',
        "hard_history_replays_over_one_hundred",
    ),
    Mutation(
        "hidden human call changes coach seed",
        "save_game",
        "plan = plan_turn(view, human_side, self._coach)",
        'self._coach._seed = sum(map(ord, human_call or ""))\n'
        "            plan = plan_turn(view, human_side, self._coach)",
        "all_tiers_choose_before_the_hidden",
    ),
    Mutation(
        "preview consumes gameplay dice",
        "save_game",
        "return view, plan_turn(view, human_side, self._coach).turn",
        "self._tape.offensive()\n"
        "            return view, plan_turn(view, human_side, self._coach).turn",
        "hard_previews_and_rejected_steps",
    ),
    Mutation(
        "offense selection mutates history",
        "difficulty",
        "observation = self._situational_offense(observation)",
        'self.commit_call("home", "1", "A")\n'
        "        observation = self._situational_offense(observation)",
        "every_coaching_branch",
    ),
    Mutation(
        "defense selection mutates history",
        "difficulty",
        'safe_choice("", observation.defense)',
        'self.commit_call("home", "1", "A")\n        safe_choice("", observation.defense)',
        "every_coaching_branch",
    ),
    Mutation(
        "cache hit fails to refresh LRU",
        "chart_coaching",
        "self._cache.move_to_end(key)",
        "pass",
        "estimate_cache_is_lru",
    ),
    Mutation(
        "cache ignores opponent counts",
        "chart_coaching",
        "key = (model, role, weights)",
        "key = (model, role, None)",
        "opponent_counts_are_part_of_cache_identity",
    ),
    Mutation(
        "failed analysis hides fallback",
        "chart_coaching",
        "self.analysis_fallback = True",
        "self.analysis_fallback = False",
        "hard_analysis_fallback_reaches_private_plan",
    ),
    Mutation(
        "exploration term omitted",
        "chart_coaching",
        "self.behavior.exploration / len(weights)",
        "0.0",
        "exact_exploration_exploitation_mixture",
    ),
    Mutation(
        "Medium tilt omitted",
        "difficulty",
        "run_probability += self._strength[obs.side]",
        "run_probability += 0.0",
        "medium_exact_group_tilt_and_symbolic_fallback",
    ),
    Mutation(
        "symbolic charts acquire numeric bias",
        "difficulty",
        "if not all(groups):\n            return 0.0",
        "if not all(groups):\n            return 0.1",
        "medium_exact_group_tilt_and_symbolic_fallback",
    ),
    Mutation(
        "CLI replaces coach during previews",
        "cli",
        "return self.game.coach_view(self.human_side)",
        "from .difficulty import DifficultyCoach\n"
        "        self.game._coach = DifficultyCoach(31, *self.game._charts.values(), 'medium')\n"
        "        return self.game.coach_view(self.human_side)",
        "cli_keeps_one_coach_for_all_commands",
    ),
)


def run_regressions(target: Path, selected: str = "") -> subprocess.CompletedProcess[str]:
    """Run real assertions with a bounded duration and captured diagnostics."""
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "tests/test_coaching_invariants.py",
            "-q",
            "-k",
            selected,
            "--tb=short",
            "--assert=plain",
        ],
        cwd=target,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def main() -> int:
    """Run assertion-based mutation checks against a disposable synthetic checkout."""
    root = Path(__file__).resolve().parents[1]
    failed = []
    with TemporaryDirectory(prefix="bowl-bound-coaching-mutations-") as temporary:
        target = Path(temporary)
        for folder in ("bowl_bound", "tests"):
            shutil.copytree(
                root / folder, target / folder, ignore=shutil.ignore_patterns("__pycache__")
            )
        baseline = run_regressions(target)
        if baseline.returncode != 0:
            print(baseline.stdout + baseline.stderr)
            return 1
        print("Clean contract baseline passed.", flush=True)
        for mutation in MUTATIONS:
            path = target / "bowl_bound" / (mutation.module + ".py")
            original = path.read_text()
            if original.count(mutation.before) != 1:
                raise ValueError(f"Mutation target must occur once: {mutation.name}")
            path.write_text(original.replace(mutation.before, mutation.after))
            try:
                result = run_regressions(target, mutation.test)
            finally:
                path.write_text(original)
                shutil.rmtree(path.parent / "__pycache__", ignore_errors=True)
            caught = result.returncode == 1 and "AssertionError" in result.stdout
            print(f"{'DETECTED' if caught else 'FAILED'}: {mutation.name}", flush=True)
            if not caught:
                failed.append(mutation.name)
                print(result.stdout + result.stderr, flush=True)
    print(f"{len(MUTATIONS) - len(failed)}/{len(MUTATIONS)} faults detected by assertions.")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
