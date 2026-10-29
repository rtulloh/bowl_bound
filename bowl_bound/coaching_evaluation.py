"""Bounded one-action Monte Carlo estimates using isolated real-engine sessions.

Unlike exact chart distributions, these estimates settle penalty/return/recovery
procedures. They are sampled coaching utilities, not exact win probabilities.
No live engine, gameplay seed, hidden call or dice source is accepted.
"""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from json import dumps
from math import isfinite
from random import Random
from typing import Literal

from .coaching import BaselineCoach, CoachObservation
from .coaching_profiles import CHART_V1, HARD_V1
from .coaching_session import observe_game
from .dice import RandomDice
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


def _settle(session: PlaySession, report: PlayReport, dice: RandomDice) -> SessionView:
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
        choice = BaselineCoach(0).decision(observe_game(view, side))
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
        session = PlaySession.for_analysis(
            home, away, field, overtime=observation.overtime, phase=phase
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
