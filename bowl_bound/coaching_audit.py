"""Public-safe complete-game coaching audits using the authoritative engine."""

import sys
from argparse import ArgumentParser
from collections import Counter
from dataclasses import dataclass, field, fields, is_dataclass, replace
from hashlib import sha256
from json import dumps
from math import isclose, isfinite

from .coaching import BaselineCoach, CoachObservation
from .coaching_audit_sampling import capture_preferences
from .coaching_profiles import AUDIT_V1, behavior_for_policy
from .coaching_session import observe_game
from .models import TeamChart
from .sample_teams import sample_teams
from .save_game import SavedGame, dumps_game, loads_game
from .statistics import summarize

DEFAULT_REPLAY_CHECKPOINT = AUDIT_V1.replay_checkpoint
MIN_CONCENTRATION_SAMPLES = AUDIT_V1.min_concentration_samples
CONCENTRATION_ADVISORY_SHARE = AUDIT_V1.concentration_share


@dataclass(frozen=True)
class CallRecord:
    """Committed public selection and the actual normalized policy mixture."""

    observation: CoachObservation
    role: str
    key: str
    fallback: bool
    preferences: dict[str, float]


@dataclass(frozen=True)
class SituationSummary:
    """Concentration evidence, never a universal play-usage quota."""

    observation: CoachObservation
    role: str
    samples: int
    distinct_calls: int
    largest_share: float
    longest_streak: int
    small_sample: bool
    advisory_warning: bool


@dataclass
class CallAudit:
    """Count committed calls within documented coarse public-situation buckets.

    Keep side, role, down, quarter, overtime, hurry and legal menus exact.
    Pool distance at <=3/<=6/<=10/long; field at <=20/<=50/<=80/deep;
    time at <=60/<=120/<=180/ordinary; score at tied/one-score/multiple,
    preserving lead versus deficit. Compare to the last call in that bucket.
    """

    calls: dict[str, Counter[str]] = field(
        default_factory=lambda: {"offense": Counter(), "defense": Counter(), "decision": Counter()}
    )
    comparable_calls: int = 0
    repeated_calls: int = 0
    fallbacks: int = 0
    illegal_selections: int = 0
    records: list[CallRecord] = field(default_factory=list)
    _previous: dict[tuple[CoachObservation, str], str] = field(default_factory=dict, repr=False)
    _counts: dict[tuple[CoachObservation, str], Counter[str]] = field(
        default_factory=dict, repr=False
    )
    _streak: Counter = field(default_factory=Counter, repr=False)
    _longest: Counter = field(default_factory=Counter, repr=False)

    def record(
        self,
        observation: CoachObservation,
        role: str,
        key: str,
        *,
        fallback: bool,
        preferences: dict[str, float] | None = None,
    ) -> None:
        legal = {
            "offense": observation.offense + observation.special + observation.game_actions,
            "defense": observation.defense,
            "decision": observation.choices,
        }
        if role not in legal or key not in legal[role]:
            self.illegal_selections += 1
            raise ValueError("audit selection must be legal for its role")
        preferences = dict(preferences) if preferences is not None else {key: 1.0}
        _require(
            set(preferences) <= set(legal[role])
            and all(isfinite(p) and p >= 0 for p in preferences.values())
            and isclose(sum(preferences.values()), 1.0, abs_tol=1e-12)
            and preferences.get(key, 0) > 0,
            "invalid selected-call preference vector",
        )

        def bucket(value: int, bounds: tuple[int, ...]) -> int:
            return sum(value > bound for bound in bounds)

        score = observation.score_difference
        model = replace(
            observation,
            play_number=0,
            distance=bucket(observation.distance, (3, 6, 10)),
            yards_to_goal=bucket(observation.yards_to_goal, (20, 50, 80)),
            remaining=bucket(observation.remaining, (60, 120, 180)),
            score_difference=(1 if score > 0 else -1) * (1 if abs(score) <= 8 else 2)
            if score
            else 0,
        )
        situation = (model, role)
        if situation in self._previous:
            self.comparable_calls += 1
            self.repeated_calls += self._previous[situation] == key
        same = self._previous.get(situation) == key
        self._streak[situation] = self._streak[situation] + 1 if same else 1
        self._longest[situation] = max(self._longest[situation], self._streak[situation])
        self._counts.setdefault(situation, Counter())[key] += 1
        self.records.append(CallRecord(observation, role, key, fallback, preferences))
        self._previous[situation] = key
        self.calls[role][key] += 1
        self.fallbacks += fallback

    def summaries(self) -> tuple[SituationSummary, ...]:
        """Summarize committed calls in the same documented situation buckets."""
        result = []
        for (observation, role), counts in self._counts.items():
            samples = sum(counts.values())
            largest = max(counts.values()) / samples
            small = samples < MIN_CONCENTRATION_SAMPLES
            result.append(
                SituationSummary(
                    observation,
                    role,
                    samples,
                    len(counts),
                    largest,
                    self._longest[(observation, role)],
                    small,
                    not small
                    and role in {"offense", "defense"}
                    and observation.phase == "scrimmage"
                    and observation.down in {1, 2, 3}
                    and len(
                        observation.offense
                        if role == "offense"
                        else observation.defense
                        if role == "defense"
                        else observation.choices
                    )
                    > 1
                    and largest >= CONCENTRATION_ADVISORY_SHARE,
                )
            )
        return tuple(result)


@dataclass(frozen=True)
class GameAudit:
    """Reconciled game evidence; estimates are not claims of win probability."""

    policy: str
    cpu_side: str
    seed: int
    home: str
    away: str
    home_score: int
    away_score: int
    finished: bool
    save_continuation_verified: bool
    quarter_seconds: tuple[int, ...]
    plays: int
    trace_rolls: int
    calls: dict[str, Counter[str]]
    comparable_calls: int
    repeated_calls: int
    fallbacks: int
    illegal_selections: int
    replayed_steps: int
    period_scores: tuple[tuple[int, int], ...]
    stand_in_calls: Counter[str]
    call_records: tuple[CallRecord, ...]
    situations: tuple[SituationSummary, ...]
    coach_seed: int
    stand_in_seed: int
    behavior_profile: str
    audit_profile: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"coaching audit: {message}")


def audit_game(
    home: TeamChart,
    away: TeamChart,
    *,
    seed: int,
    coach_seed: int,
    policy: str,
    cpu_side: str,
    step_limit: int = 1600,
    replay_checkpoint: int = DEFAULT_REPLAY_CHECKPOINT,
    stand_in_seed: int = 9871,
) -> GameAudit:
    """Play solitaire with a baseline stand-in; compare replay after the checkpoint.

    The stand-in receives only public observations. Score, clock and committed
    statistics are reconciled independently of successful game completion.
    """
    if cpu_side not in {"home", "away"}:
        raise ValueError("cpu_side must be home or away")
    if type(replay_checkpoint) is not int or not 0 <= replay_checkpoint < step_limit:
        raise ValueError("replay checkpoint must be an integer within the step limit")
    human = "away" if cpu_side == "home" else "home"
    game = SavedGame.new(
        home,
        away,
        seed=seed,
        coach_seed=coach_seed,
        coach_policy=policy,
        mode="regulation",
        home_id="2007/home",
        away_id="2007/away",
    )
    stand_in = BaselineCoach(stand_in_seed)
    calls = CallAudit()
    restored = None
    replayed_steps = 0
    stand_in_calls: Counter[str] = Counter()
    periods: dict[int, list[int]] = {q: [0, 0] for q in range(1, 5)}
    for step in range(step_limit):
        view = game.view()
        if restored is not None:
            _require(restored.view() == view, "saved future state diverged")
        if view.finished:
            break
        _, turn = game.coach_view(human)
        observation = observe_game(view, human)
        if turn.automatic:
            operation, argument = "coach", None
        elif turn.pending and not getattr(view, "clock_optional", False):
            operation = "decide"
            allowed = tuple(c.id for c in turn.pending.choices if c.enabled)
            argument = stand_in.decision(replace(observation, choices=allowed))
        elif turn.actions.offense or turn.actions.defense:
            operation = "coach"
            argument = (
                stand_in.offense(observation)
                if turn.actions.offense
                else stand_in.defense(observation)
            )
            if argument in {action.key for action in turn.actions.special}:
                operation = "kick"
            elif argument in {action.key for action in turn.game_actions}:
                operation = "action"
        elif turn.actions.special:
            operation, argument = "kick", turn.actions.special[0].key
        else:
            raise ValueError("coaching audit: no legal progress action")
        if not turn.automatic and argument is not None:
            stand_in_calls[argument] += 1

        def advance(
            target: SavedGame, operation: str = operation, argument: str | None = argument
        ) -> object:
            if operation == "coach":
                return target.coach_step(human, argument)
            if operation == "decide":
                return target.decide(argument)
            if operation == "action":
                return target.action(argument)
            return target.kick(argument)

        _require(not view.finished, "action attempted after game over")
        with capture_preferences(game._coach, observation=observe_game(view, cpu_side)) as draws:
            result = advance(game)
        after = game.view()
        period = 4 + view.overtime.round_number if view.overtime else view.clock.quarter
        delta = (after.score.home - view.score.home, after.score.away - view.score.away)
        _require(all(points >= 0 for points in delta), "score decreased during a period")
        total = periods.setdefault(period, [0, 0])
        total[0] += delta[0]
        total[1] += delta[1]
        if restored is not None:
            _require(advance(restored) == result, "saved future calls or outcomes diverged")
            _require(restored.view() == after, "saved future state diverged")
            replayed_steps += 1
        if operation == "coach" and result[3] is not None:
            choice = result[3]
            cpu_observation = observe_game(view, cpu_side)
            role = (
                "decision"
                if view.pending and choice.key in cpu_observation.choices
                else ("defense" if view.state and view.state.possession == human else "offense")
            )
            calls.record(
                cpu_observation,
                role,
                choice.key,
                fallback=choice.fallback,
                preferences=draws[-1] if draws else None,
            )
        if step == replay_checkpoint:
            restored = loads_game(
                dumps_game(game), lambda key: home if key.endswith("home") else away
            )
    view = game.view()
    _require(view.finished, "step limit reached before completion")
    verified = restored is not None and replayed_steps > 0 and restored.view() == view
    _require(verified, "missing saved future verification")
    period_scores = tuple(tuple(periods[q]) for q in sorted(periods))
    reconcile_period_scores(period_scores, (view.score.home, view.score.away))
    _require(
        view.statistics == summarize(r.statistics for r in view.log), "statistics do not reconcile"
    )
    _require(
        view.score.home == sum(e.points for e in view.scoring if e.team == view.home),
        "home scoring ledger differs",
    )
    _require(
        view.score.away == sum(e.points for e in view.scoring if e.team == view.away),
        "away scoring ledger differs",
    )
    _require(
        all(
            c.before - c.after == min(c.before, c.seconds) and c.after >= 0 for c in view.timing_log
        ),
        "invalid clock transition",
    )
    quarters = tuple(
        sum(c.before - c.after for c in view.timing_log if c.quarter == q) for q in range(1, 5)
    )
    _require(quarters == (900,) * 4, "regulation clock does not reconcile")
    _require(
        all(r.supported and not r.pending for r in view.log),
        "unresolved or unsupported final report",
    )
    _require(
        all(t.roll and t.cell for r in view.log for t in r.trace),
        "incomplete structured chart trace",
    )
    return GameAudit(
        policy,
        cpu_side,
        seed,
        view.home,
        view.away,
        view.score.home,
        view.score.away,
        view.finished,
        verified,
        quarters,
        len(view.log),
        sum(len(r.trace) for r in view.log),
        calls.calls,
        calls.comparable_calls,
        calls.repeated_calls,
        calls.fallbacks,
        calls.illegal_selections,
        replayed_steps,
        period_scores,
        stand_in_calls,
        tuple(calls.records),
        calls.summaries(),
        coach_seed,
        stand_in_seed,
        behavior_for_policy(policy).name,
        AUDIT_V1.name,
    )


def compare_policies(
    seeds: tuple[int, ...],
    *,
    policies: tuple[str, ...] = ("baseline", "easy-v1", "medium-v1", "hard-v1"),
) -> tuple[GameAudit, ...]:
    """Compare independent dice seeds across both sample arrangements and CPU sides."""
    if (
        len(seeds) < 2
        or any(type(seed) is not int for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise ValueError("seeds must contain at least two distinct integer seeds")
    teams = sample_teams()
    return tuple(
        audit_game(
            *(teams[::-1] if reverse else teams),
            seed=seed,
            coach_seed=audit_seed(seed, f"coach:{reverse}:{side}:{policy}"),
            stand_in_seed=audit_seed(seed, f"stand-in:{reverse}:{side}:{policy}"),
            policy=policy,
            cpu_side=side,
        )
        for seed in seeds
        for reverse in (False, True)
        for side in ("home", "away")
        for policy in policies
    )


def audit_seed(seed: int, identity: str) -> int:
    """Derive stable independent audit streams without Python hash randomization."""
    return int.from_bytes(
        sha256(f"bowl-bound-audit-v1:{seed}:{identity}".encode()).digest()[:8], "big"
    ) & (2**63 - 1)  # Match the existing private-save seed range.


def reconcile_period_scores(
    periods: tuple[tuple[int, int], ...],
    final: tuple[int, int],
) -> None:
    """Check observed period deltas against engine totals, not inferred scoring rules."""
    _require(
        bool(periods)
        and all(type(p) is int and p >= 0 for period in periods for p in period)
        and (sum(p[0] for p in periods), sum(p[1] for p in periods)) == final,
        "period scores differ from final totals",
    )


def _json_default(value: object) -> dict[str, object]:
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError("unsupported audit evidence type")
    # Keep Counter as a JSON mapping; dataclasses.asdict reconstructs it from
    # (key, value) pairs as counted keys instead of preserving its counts.
    return {item.name: getattr(value, item.name) for item in fields(value)}


def main(argv: list[str] | None = None) -> int:
    """Write JSON evidence for public samples only; redact engine exception text."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[101, 307])
    parser.add_argument(
        "--policies",
        nargs="+",
        choices=("baseline", "chart-v1", "easy-v1", "medium-v1", "hard-v1"),
        default=["baseline", "easy-v1", "medium-v1", "hard-v1"],
    )
    args = parser.parse_args(argv)
    try:
        results = compare_policies(tuple(args.seeds), policies=tuple(args.policies))
        output = dumps(
            {"schema_version": 1, "games": results}, default=_json_default, sort_keys=True
        )
    except Exception as error:
        # CLI boundary only: exception messages can expose private source cells.
        print(dumps({"error": "audit failed", "error_type": type(error).__name__}), file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
