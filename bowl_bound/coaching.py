"""Baseline coaching preferences, never football rules or chart interpretation.

Situational mixtures adapted from Paydirt ComputerAI (MIT, rtulloh), commit
bfaf8410cb586149f06f98bf98ecca572cae360d. See docs/ATTRIBUTION.md.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from json import dumps
from random import Random

from .coaching_profiles import behavior_for_policy
from .decision_facts import DecisionOutcome, DecisionOutcomeKind, RazzleDazzleContext


class NoLegalAction(ValueError):
    """No enabled engine option exists for the requested coaching role."""


@dataclass(frozen=True)
class CoachObservation:
    """An explicit allowlist of public facts; no engine, charts, seed or hidden call."""

    side: str
    possession: str
    down: int
    distance: int
    yards_to_goal: int
    quarter: int
    remaining: int
    score_difference: int
    play_number: int
    offense: tuple[str, ...]
    defense: tuple[str, ...]
    special: tuple[str, ...]
    game_actions: tuple[str, ...]
    choices: tuple[str, ...]
    overtime: bool = False
    hurried: bool = False
    phase: str = "scrimmage"
    can_kneel_out_game: bool = False
    decision_outcomes: tuple[DecisionOutcome, ...] = ()
    razzle_context: RazzleDazzleContext | None = None
    advanced_ii: bool = False
    free_advanced_defense: bool = False


@dataclass(frozen=True)
class CoachChoice:
    key: str
    fallback: bool = False


@dataclass(frozen=True)
class FourthDownGuidance:
    """Read-only public recommendation shared with the normal CPU policy."""

    action: str
    label: str
    summary: str
    attempt_distance: int
    difficulty: str
    aggression: float


def safe_choice(candidate: str, legal: tuple[str, ...]) -> CoachChoice:
    """Constrain a policy suggestion to the supplied enabled engine options."""
    if not legal:
        raise NoLegalAction("No enabled engine action is available.")
    return CoachChoice(candidate) if candidate in legal else CoachChoice(legal[0], True)


def field_goal_attempt_distance(observation: CoachObservation) -> int:
    """Return the public conventional distance: line of scrimmage plus 17 yards."""
    return observation.yards_to_goal + 17


def public_fourth_down_call(
    observation: CoachObservation, *, aggression: float, chase_seconds: int = 180
) -> str | None:
    """Choose field_goal, punt, or go using the owner-approved public policy.

    Inputs contain only visible game facts and declared aggression. This function
    neither accepts nor inspects a chart and consumes no randomness. It recommends
    an offered kick or scrimmage; the engine separately resolves the actual play.
    Non-fourth downs, overtime and conversion tries are outside this policy.
    """
    if observation.overtime or observation.phase == "two_point_try" or observation.down != 4:
        return None
    field_goal_available = "field_goal" in observation.special
    punt_available = "punt" in observation.special
    field_goal_distance = field_goal_attempt_distance(observation)
    late_trailing = (
        observation.quarter == 4
        and observation.remaining <= chase_seconds
        and observation.score_difference < 0
    )
    if late_trailing:
        if (
            observation.score_difference >= -3
            and field_goal_available
            and field_goal_distance <= 55
        ):
            return "field_goal"
        return "go"

    if field_goal_available and field_goal_distance <= 35:
        return "field_goal"
    if field_goal_available and field_goal_distance <= 47:
        if observation.distance == 1 and aggression >= 0.5:
            return "go"
        return "field_goal"
    if field_goal_available and field_goal_distance <= 50:
        return "field_goal"
    if field_goal_available and field_goal_distance <= 55:
        if aggression >= 0.5:
            return "field_goal"
        return "punt" if punt_available else "go"
    if observation.distance == 1 and aggression >= 0.5:
        return "go"
    return "punt" if punt_available else "go"


class BaselineCoach:
    """Reproducible, varied calls with private randomness separate from game dice.

    The seed belongs to coaching only; never pass the gameplay seed or dice state.
    Deriving a local stream per public observation makes previews pure and retries
    stable without consuming future calls or recording an uncommitted selection.
    """

    def __init__(self, seed: int, *, version: int = 1) -> None:
        if type(version) is not int or not 1 <= version <= 14:
            raise ValueError("baseline policy version must be 1 through 14")
        self._seed = seed
        self.version = version
        if version == 1:
            policy = "baseline"
        elif version < 8:
            policy = "baseline-v2"
        else:
            policy = f"baseline-v{version}"
        self.behavior = behavior_for_policy(policy)
        self.analysis_fallback = False

    def commit_call(
        self,
        offense_side: str,
        play: str,
        defense: str,
        *,
        observation: CoachObservation | None = None,
    ) -> None:
        """Observe a committed pair; baseline/legacy policies intentionally learn nothing."""

    def _random(self, observation: CoachObservation, role: str) -> Random:
        facts = asdict(observation)
        if self.version < 11:
            facts.pop("razzle_context")
        if self.version < 9:
            facts.pop("advanced_ii")
            facts.pop("free_advanced_defense")
        if self.version < 8:
            facts.pop("decision_outcomes")
        # Freeze the baseline-v1 input contract so old saves retain future calls.
        facts.pop("hurried")
        facts.pop("phase")
        if self.version == 1:
            facts.pop("can_kneel_out_game")
        public = dumps(facts, sort_keys=True, separators=(",", ":"))
        digest = sha256(f"baseline-v{self.version}:{self._seed}:{role}:{public}".encode()).digest()
        return Random(int.from_bytes(digest, "big"))

    def offense(self, observation: CoachObservation) -> str:
        """Choose an offered scrimmage, kick or automatic action, without previewing results."""
        legal = observation.offense + observation.special + observation.game_actions
        if "kickoff" in observation.special and not observation.offense:
            return "kickoff"
        protecting = (
            not observation.overtime
            and observation.quarter == 4
            and observation.remaining <= self.behavior.protect_seconds
            and observation.score_difference > 0
        )
        if "kneel" in observation.game_actions and observation.down < 4:
            if self.version == 1 and protecting:
                return "kneel"
            if self.version >= 2 and observation.can_kneel_out_game:
                return "kneel"
        chasing = (
            not observation.overtime
            and observation.quarter == 4
            and observation.remaining <= self.behavior.chase_seconds
            and observation.score_difference < 0
        )
        if observation.down == 4 and not chasing and self.version < 3:
            if (
                observation.yards_to_goal <= self.behavior.field_goal_yards
                and "field_goal" in observation.special
            ):
                return "field_goal"
            if observation.distance > self.behavior.punt_distance and "punt" in observation.special:
                return "punt"
        if not observation.offense:
            return safe_choice("", legal).key
        # Adapted baseline mixture only: all nine Bowl Bound calls remain possible.
        passing_down = (
            observation.down >= 3 and observation.distance > self.behavior.passing_distance
        )
        weights = [
            self.behavior.baseline_run_weight
            if passing_down and key in {"1", "2", "3", "4", "5"}
            else 1.0
            for key in observation.offense
        ]
        return self._random(observation, "offense").choices(
            observation.offense, weights=weights, k=1
        )[0]

    def defense(self, observation: CoachObservation) -> str:
        """Mix all offered formations without seeing the opponent offensive call."""
        safe_choice("", observation.defense)
        return self._random(observation, "defense").choice(observation.defense)

    def clock_decision(
        self, observation: CoachObservation, *, normal_timing_ends_period: bool = False
    ) -> str:
        """Select an offered clock action; historical policies retain their decisions."""
        return self.decision(observation)

    def decision(self, observation: CoachObservation) -> str:
        """Conservative baseline preferences with engine-constrained fallback."""
        if self.version >= 7:
            self.analysis_fallback = False
        choices = observation.choices
        if self.version >= 8:
            preferred = _penalty_choice(observation)
            if preferred is not None:
                return preferred
        protecting_lead = (
            not observation.overtime
            and observation.quarter == 4
            and observation.remaining <= self.behavior.protect_seconds
            and observation.score_difference >= self.behavior.large_lead_points
        )
        if self.version >= 7:
            if protecting_lead:
                for key in ("kick:fair_catch", "kick:touchback", "end_zone:touchback"):
                    if key in choices:
                        return key
            for key in ("kick:return", "end_zone:return"):
                if key in choices:
                    return key
            if "kick:out_of_bounds:spot" in choices:
                return "kick:out_of_bounds:spot"
        if (
            observation.quarter == 4
            and observation.remaining <= self.behavior.late_seconds
            and observation.score_difference < 0
        ):
            if "clock:hurry" in choices:
                return "clock:hurry"
        preferred = (
            "clock:standard",
            "toss:receive",
            "ot:offense",
            "conversion:kick",
            "kick:touchback",
            "end_zone:touchback",
            "kick:fair_catch",
            "interception:return",
        )
        return next((key for key in preferred if key in choices), safe_choice("", choices).key)


def _penalty_choice(observation: CoachObservation) -> str | None:
    """Choose the unique best prepared penalty result from engine-owned projections."""
    outcomes = tuple(
        outcome
        for outcome in observation.decision_outcomes
        if outcome.choice_id in observation.choices
    )
    if len(outcomes) < 2 or any(
        outcome.kind is DecisionOutcomeKind.UNRESOLVED for outcome in outcomes
    ):
        return None
    scores = tuple(_outcome_value(outcome, observation.possession) for outcome in outcomes)
    best = max(scores) if observation.side == observation.possession else min(scores)
    winners = tuple(
        outcome.choice_id for outcome, score in zip(outcomes, scores, strict=True) if score == best
    )
    return winners[0] if len(winners) == 1 else None


def _outcome_value(outcome: DecisionOutcome, offense_side: str) -> tuple[int, int, int, int]:
    """Order known outcomes by scoring, possession, field position, then down/distance."""
    if outcome.kind is DecisionOutcomeKind.SAFETY:
        return (3 if outcome.scoring_side == offense_side else -3, 0, 0, 0)
    if outcome.kind is DecisionOutcomeKind.TOUCHDOWN:
        return (3 if outcome.scoring_side == offense_side else -3, 0, 0, 0)
    if outcome.possession == offense_side:
        return (
            1,
            100 - (outcome.yards_to_goal or 100),
            5 - (outcome.down or 5),
            -(outcome.yards_to_go or 0),
        )
    return (
        -1,
        outcome.yards_to_goal or 0,
        outcome.down or 0,
        outcome.yards_to_go or 0,
    )
