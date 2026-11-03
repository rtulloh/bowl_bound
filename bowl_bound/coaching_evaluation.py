"""Bounded one-action Monte Carlo estimates using isolated real-engine sessions.

Unlike exact chart distributions, these estimates settle penalty/return/recovery
procedures. They are sampled coaching utilities, not exact win probabilities.
No live engine, gameplay seed, hidden call or dice source is accepted.
"""

from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from hashlib import sha256
from json import dumps
from math import fsum, isfinite, sqrt
from random import Random
from typing import Literal

from .coaching import BaselineCoach, CoachObservation
from .coaching_probabilities import (
    _DEFENSIVE_GROUPS,
    _OFFENSIVE_GROUPS,
    _NeedRoll,
    _PrefixDice,
)
from .coaching_profiles import CHART_V1, HARD_V1
from .coaching_session import observe_game
from .dice import DefensiveRoll, DiceSource, OffensiveRoll, RandomDice
from .game_state import FieldState, Possession
from .models import TeamChart
from .resolution import ChartResolutionError
from .session import (
    InvalidDecisionError,
    PendingDecisionError,
    PlayReport,
    PlaySession,
    SessionFinishedError,
    SessionPhase,
    SessionView,
)


@dataclass(frozen=True)
class ActionEstimate:
    """Sampled action values; any failed sample invalidates the estimate.

    ``turnover_rate`` is a legacy possession-loss proxy, not football turnover
    statistics: punts, kickoffs and turnovers on downs can also count as loss.
    """

    key: str
    samples: int
    failed_samples: int
    mean_utility: float | None
    turnover_rate: float | None
    mean_points: float | None

    @property
    def complete(self) -> bool:
        return self.failed_samples == 0


class EvaluationError(ValueError):
    """The hypothetical action did not settle within supported engine limits."""


def _potential(field: FieldState, side: str) -> float:
    value = (
        CHART_V1.potential_base
        + CHART_V1.potential_progress * (100 - field.yards_to_goal) / 100
        - CHART_V1.potential_down_discount * (field.down - 1)
        - CHART_V1.potential_distance_discount * field.yards_to_go
    )
    return value if field.possession.value == side else -value


def _hard_potential(field: FieldState, side: str) -> float:
    """Field-position preference, not calibrated expected points.

    The quadratic ranges from -1 near our goal to +4 near the opponent goal,
    before down/distance discounts. A possession near either goal is therefore
    not given a fixed positive premium. Scoring six beats retaining the ball
    near the goal; changing possession is valued at the actual receiving spot.
    """
    progress = (100 - field.yards_to_goal) / 100
    value = (
        HARD_V1.potential_base
        + HARD_V1.potential_progress * progress**HARD_V1.potential_exponent
        - HARD_V1.potential_down_discount * (field.down - 1)
        - HARD_V1.potential_distance_discount * field.yards_to_go
    )
    return value if field.possession.value == side else -value


def _utility(
    view: SessionView,
    observation: CoachObservation,
    before: FieldState,
    *,
    utility_policy: Literal["legacy-v1", "hard-v1"] = "legacy-v1",
) -> tuple[float, float, bool]:
    """Documented preference units, not a second rules engine or calibrated EPA."""
    points = view.score.home - view.score.away
    if observation.side == "away":
        points = -points
    if utility_policy == "hard-v1" and observation.phase == SessionPhase.TWO_POINT_TRY.value:
        if view.phase != SessionPhase.COMPLETE.value:
            raise EvaluationError("hypothetical try did not settle")
        return float(points), float(points), points < 0
    potential_function = _hard_potential if utility_policy == "hard-v1" else _potential
    potential = 0.0
    if view.state:
        state = view.state
        potential = potential_function(
            FieldState(
                Possession(state.possession), state.yards_to_goal, state.down, state.yards_to_go
            ),
            observation.side,
        )
    value = points + potential - potential_function(before, observation.side)
    behavior = HARD_V1 if utility_policy == "hard-v1" else CHART_V1
    if (
        not observation.overtime
        and observation.quarter == 4
        and observation.remaining <= behavior.late_seconds
    ):
        # Situational preference only: reward a late lead/tie without deciding
        # a game, advancing time or inventing a clock/timeout rule.
        margin = observation.score_difference
        after = margin + points
        value += behavior.late_lead_bonus * (
            (after > 0) - (margin > 0)
        ) + behavior.late_tie_bonus * ((after == 0) - (margin == 0))
    lost = (view.state is not None and view.state.possession != before.possession.value) or (
        view.score.away > 0 if before.possession is Possession.HOME else view.score.home > 0
    )
    return value, float(points), bool(lost)


def _settle(
    session: PlaySession, report: PlayReport, dice: DiceSource, *, coach_version: int = 1
) -> SessionView:
    for _ in range(CHART_V1.settle_decisions):
        if not report.supported:
            raise EvaluationError("unsupported hypothetical engine result")
        view = session.view()
        # Stop at the action boundary; do not append a touchdown conversion,
        # another snap or kickoff to the value of the original action.
        if view.pending is None or view.phase == SessionPhase.CONVERSION_CHOICE.value:
            return view
        side = view.pending.chooser_side
        if side not in {"home", "away"}:
            raise EvaluationError("hypothetical decision lacks side ownership")
        choice = BaselineCoach(0, version=coach_version).decision(observe_game(view, side))
        report = session.decide(choice, dice=dice)
    raise EvaluationError("hypothetical decision limit reached")


def evaluate_action(
    home: TeamChart,
    away: TeamChart,
    observation: CoachObservation,
    key: str,
    *,
    role: str,
    samples: int = CHART_V1.analysis_samples,
    opponent_weights: tuple[float, ...] | None = None,
    utility_policy: Literal["legacy-v1", "hard-v1"] = "legacy-v1",
) -> ActionEstimate:
    """Estimate an action using uniform or supplied weights for opposing calls.

    Opponent calls are sampled only for scrimmage. Fixed actions (kicks, kneel
    and Hail Mary) use the engine procedure without a discarded call draw.

    The fixed versioned analysis stream uses public situation facts only and is
    distinct from private call-selection randomness. Candidates share analysis
    streams to reduce comparison noise. Each trial uses real physical-face dice
    and a fresh session; pending procedures use baseline legal preferences.
    Samples include failures: never drop failures and renormalize successes.
    """
    if utility_policy not in {"legacy-v1", "hard-v1"}:
        raise ValueError("unknown coaching utility policy")
    if type(samples) is not int or not 1 <= samples <= CHART_V1.max_analysis_samples:
        raise ValueError("samples must be an integer within 1..256")
    if role not in {"offense", "defense"}:
        raise ValueError("evaluation role must be offense or defense")
    legal = (
        observation.defense
        if role == "defense"
        else observation.offense + observation.special + observation.game_actions
    )
    if key not in legal:
        raise ValueError("evaluation requires an offered action")
    if (role == "offense") != (observation.side == observation.possession):
        raise ValueError("evaluation role does not match possession")
    opponents = observation.offense if role == "defense" else observation.defense
    if opponent_weights is not None and (
        not opponents
        or len(opponent_weights) != len(opponents)
        or any(not isfinite(weight) or weight <= 0 for weight in opponent_weights)
        or not isfinite(sum(opponent_weights))
    ):
        raise ValueError("opponent weights must match legal calls and be finite positive values")
    field = FieldState(
        Possession(observation.possession),
        observation.yards_to_goal,
        observation.down,
        observation.distance,
    )
    facts = asdict(replace(observation, play_number=0))
    facts.pop("razzle_context")  # Preserve all historical one-action analysis streams.
    if not observation.advanced_ii:
        facts.pop("advanced_ii")
    if not observation.free_advanced_defense:
        facts.pop("free_advanced_defense")
    if utility_policy == "legacy-v1":
        # Preserve the original chart-v1 analysis stream and sandbox semantics.
        facts.pop("phase")
    public = dumps(facts, sort_keys=True, separators=(",", ":"))
    mixture = f":{opponent_weights}" if opponent_weights is not None else ""
    seed = int.from_bytes(
        sha256(f"chart-evaluation-v1:{role}:{public}{mixture}".encode()).digest(), "big"
    )
    total = points = lost = 0.0
    failed = 0
    for index in range(samples):
        opposing = "A"
        if role == "defense" or key in observation.offense:
            rng = Random(seed + index + 2**128)  # Separate from the dice stream.
            if opponent_weights is not None:
                opposing = rng.choices(opponents, weights=opponent_weights, k=1)[0]
            else:
                opposing = rng.choice(opponents) if opponents else "A"
        dice = RandomDice(Random(seed + index))
        phase = (
            SessionPhase.TWO_POINT_TRY
            if utility_policy == "hard-v1" and observation.phase == SessionPhase.TWO_POINT_TRY.value
            else SessionPhase.SCRIMMAGE
        )
        defender_side = (
            observation.side
            if role == "defense"
            else ("away" if observation.possession == "home" else "home")
        )
        session = PlaySession.for_analysis(
            home,
            away,
            field,
            overtime=observation.overtime,
            phase=phase,
            advanced_ii=observation.advanced_ii,
            home_privileges=("W",)
            if observation.free_advanced_defense and defender_side == "home"
            else (),
            away_privileges=("W",)
            if observation.free_advanced_defense and defender_side == "away"
            else (),
        )
        try:
            if role == "defense":
                report = session.snap(opposing, key, dice=dice, hurried=observation.hurried)
            elif key in observation.offense:
                report = session.snap(key, opposing, dice=dice, hurried=observation.hurried)
            elif key in {"punt", "field_goal", "kickoff"}:
                report = session.kick(key, dice=dice)
            elif key == "hail_mary":
                report = session.snap(
                    "8", "A", dice=dice, hurried=observation.hurried, hail_mary=True
                )
            elif key == "kneel":
                report = session.automatic(key)
            else:
                raise EvaluationError("action is not supported by the one-play evaluator")
            value, scored, turnover = _utility(
                _settle(session, report, dice), observation, field, utility_policy=utility_policy
            )
        except (
            EvaluationError,
            ChartResolutionError,
            InvalidDecisionError,
            PendingDecisionError,
            SessionFinishedError,
        ):
            failed += 1
        else:
            total += value
            points += scored
            lost += turnover
    return ActionEstimate(
        key,
        samples,
        failed,
        None if failed else total / samples,
        None if failed else lost / samples,
        None if failed else points / samples,
    )


@dataclass(frozen=True)
class RazzleDecisionEstimate:
    """Exact weighted engine utility, or explicitly incomplete/failed mass."""

    key: str
    mean_utility: float | None
    unexplored_probability: Fraction
    failed_probability: Fraction
    evaluations: int

    @property
    def complete(self) -> bool:
        return self.unexplored_probability == 0 and self.failed_probability == 0


def evaluate_razzle_decisions(
    home: TeamChart,
    away: TeamChart,
    observation: CoachObservation,
    *,
    max_evaluations: int = 10_000,
) -> tuple[RazzleDecisionEstimate, ...]:
    """Library/test oracle for exact RZDZ branches, not the normal request path.

    Both immutable supplied boards, including possible supplemental rows, are
    coach-available. These means are gamble estimates, never future results.
    Only the two public comparison rolls are fixed. Every future roll branches
    with physical-face multiplicity; no live session, dice, seed or hidden call
    is accepted. Grouping by total/direct sum retains black and white-sum facts
    used by engine continuations, including end-zone depth and variable yardage.
    Branches settle with the frozen v10 legal continuation preferences, and use
    the existing documented Hard field/score utility from the offense's side.
    Conversion/kickoff/another snap is outside this one-action boundary.
    Failed/unexplored mass invalidates a candidate, never silently becomes zero.
    """
    context = observation.razzle_context
    if (
        context is None
        or not observation.choices
        or any(not key.startswith("razzle:") for key in observation.choices)
    ):
        raise ValueError("Razzle-Dazzle analysis requires its revealed legal context")
    if type(max_evaluations) is not int or max_evaluations <= 0:
        raise ValueError("analysis budget must be a positive integer")
    field = FieldState(
        Possession(observation.possession),
        observation.yards_to_goal,
        observation.down,
        observation.distance,
    )
    offense_observation = replace(
        observation,
        side=observation.possession,
        score_difference=observation.score_difference
        if observation.side == observation.possession
        else -observation.score_difference,
    )
    advanced = context.defense not in {"A", "B", "C", "D", "E", "F"}
    defender = field.possession.other.value
    estimates = []
    for key in observation.choices:
        frontier: list[tuple[tuple[OffensiveRoll | DefensiveRoll, ...], Fraction]] = [
            ((), Fraction(1))
        ]
        expected = Fraction()
        failed = Fraction()
        evaluations = 0
        while frontier and evaluations < max_evaluations:
            prefix, probability = frontier.pop()
            evaluations += 1
            source = _PrefixDice((*context.rolls, *prefix))
            session = PlaySession.for_analysis(
                home,
                away,
                field,
                overtime=observation.overtime,
                phase=SessionPhase.TWO_POINT_TRY
                if observation.phase == SessionPhase.TWO_POINT_TRY.value
                else SessionPhase.SCRIMMAGE,
                advanced_ii=advanced,
                home_privileges=("W",) if context.free_wildcard and defender == "home" else (),
                away_privileges=("W",) if context.free_wildcard and defender == "away" else (),
            )
            try:
                session.snap("RZDZ", context.defense, dice=source, hurried=observation.hurried)
                report = session.decide(key)
                view = _settle(session, report, source, coach_version=10)
                value, _, _ = _utility(view, offense_observation, field, utility_policy="hard-v1")
            except _NeedRoll as request:
                groups = _OFFENSIVE_GROUPS if request.offensive else _DEFENSIVE_GROUPS
                frontier.extend(((*prefix, roll), probability * weight) for roll, weight in groups)
            except (
                EvaluationError,
                ChartResolutionError,
                InvalidDecisionError,
                PendingDecisionError,
                SessionFinishedError,
                ValueError,
            ):
                failed += probability
            else:
                expected += probability * Fraction(value)
        unexplored = sum((probability for _, probability in frontier), Fraction())
        estimates.append(
            RazzleDecisionEstimate(
                key,
                None if failed or unexplored else float(expected),
                unexplored,
                failed,
                evaluations,
            )
        )
    return tuple(estimates)


RAZZLE_SAMPLE_BUDGET = 288
RAZZLE_MAX_CANDIDATE_SAMPLES = 32


@dataclass(frozen=True)
class RazzleChoiceEstimate:
    """Sampled utility and sampling uncertainty, never a known future result."""

    key: str
    samples: int
    failed_samples: int
    mean_utility: float | None
    standard_error: float | None

    @property
    def complete(self) -> bool:
        """All requested samples succeeded; this is not exhaustive probability."""
        return self.failed_samples == 0


class _RazzleSampleDice:
    """Replay revealed comparisons, then use an independent hypothetical stream."""

    def __init__(self, rolls: tuple[OffensiveRoll, OffensiveRoll], seed: int) -> None:
        self._rolls = rolls
        self._position = 0
        self._future = RandomDice(Random(seed))

    def offensive(self) -> OffensiveRoll:
        if self._position < len(self._rolls):
            roll = self._rolls[self._position]
            self._position += 1
            return roll
        return self._future.offensive()

    def defensive(self) -> DefensiveRoll:
        return self._future.defensive()


def sample_razzle_decisions(
    home: TeamChart,
    away: TeamChart,
    observation: CoachObservation,
    *,
    total_samples: int = RAZZLE_SAMPLE_BUDGET,
) -> tuple[RazzleChoiceEstimate, ...]:
    """Compare legal RZDZ choices with a small shared, deterministic rollout budget.

    All candidates use the same hypothetical streams, derived only from revealed
    observations. Actual gameplay/coach seeds and future dice are unavailable.
    Equal samples per candidate and explicit failures prevent selective dropping
    or renormalization. Standard error describes sampling variation, not a bound
    on heuristic bias or a guarantee of the selected gamble's future result.
    """
    context = observation.razzle_context
    if (
        context is None
        or not observation.choices
        or any(not key.startswith("razzle:") for key in observation.choices)
    ):
        raise ValueError("Razzle-Dazzle analysis requires its revealed legal context")
    if (
        type(total_samples) is not int
        or not len(observation.choices) <= total_samples <= RAZZLE_SAMPLE_BUDGET
    ):
        raise ValueError(
            f"shared sample budget must cover each candidate and be at most {RAZZLE_SAMPLE_BUDGET}"
        )
    samples = min(RAZZLE_MAX_CANDIDATE_SAMPLES, total_samples // len(observation.choices))
    public = dumps(
        asdict(replace(observation, play_number=0)), sort_keys=True, separators=(",", ":")
    )
    seed = int.from_bytes(sha256(f"razzle-choice-estimate-v11:{public}".encode()).digest(), "big")
    field = FieldState(
        Possession(observation.possession),
        observation.yards_to_goal,
        observation.down,
        observation.distance,
    )
    offense_observation = replace(
        observation,
        side=observation.possession,
        score_difference=observation.score_difference
        if observation.side == observation.possession
        else -observation.score_difference,
    )
    defender = field.possession.other.value
    estimates = []
    for key in observation.choices:
        values = []
        failed = 0
        for index in range(samples):
            dice = _RazzleSampleDice(context.rolls, seed + index)
            session = PlaySession.for_analysis(
                home,
                away,
                field,
                overtime=observation.overtime,
                phase=SessionPhase.TWO_POINT_TRY
                if observation.phase == SessionPhase.TWO_POINT_TRY.value
                else SessionPhase.SCRIMMAGE,
                advanced_ii=context.defense not in {"A", "B", "C", "D", "E", "F"},
                home_privileges=("W",) if context.free_wildcard and defender == "home" else (),
                away_privileges=("W",) if context.free_wildcard and defender == "away" else (),
            )
            try:
                session.snap("RZDZ", context.defense, dice=dice, hurried=observation.hurried)
                report = session.decide(key)
                view = _settle(session, report, dice, coach_version=10)
                value, _, _ = _utility(view, offense_observation, field, utility_policy="hard-v1")
            except (
                EvaluationError,
                ChartResolutionError,
                InvalidDecisionError,
                PendingDecisionError,
                SessionFinishedError,
                ValueError,
            ):
                failed += 1
            else:
                values.append(value)
        mean = None if failed else fsum(values) / samples
        error = (
            sqrt(fsum((value - mean) ** 2 for value in values) / (samples - 1) / samples)
            if mean is not None and samples > 1
            else None
        )
        estimates.append(RazzleChoiceEstimate(key, samples, failed, mean, error))
    return tuple(estimates)
