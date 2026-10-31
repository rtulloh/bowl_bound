"""Baseline coaching preferences, never football rules or chart interpretation.

Situational mixtures adapted from Paydirt ComputerAI (MIT, rtulloh), commit
bfaf8410cb586149f06f98bf98ecca572cae360d. See docs/ATTRIBUTION.md.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from json import dumps
from random import Random

from .coaching_profiles import BASELINE_V1


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


@dataclass(frozen=True)
class CoachChoice:
    key: str
    fallback: bool = False


def safe_choice(candidate: str, legal: tuple[str, ...]) -> CoachChoice:
    """Constrain a policy suggestion to the supplied enabled engine options."""
    if not legal:
        raise NoLegalAction("No enabled engine action is available.")
    return CoachChoice(candidate) if candidate in legal else CoachChoice(legal[0], True)


class BaselineCoach:
    """Reproducible, varied calls with private randomness separate from game dice.

    The seed belongs to coaching only; never pass the gameplay seed or dice state.
    Deriving a local stream per public observation makes previews pure and retries
    stable without consuming future calls or recording an uncommitted selection.
    """

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self.behavior = BASELINE_V1
        self.analysis_fallback = False

    def commit_call(self, offense_side: str, play: str, defense: str) -> None:
        """Observe a committed pair; baseline/legacy policies intentionally learn nothing."""

    def _random(self, observation: CoachObservation, role: str) -> Random:
        facts = asdict(observation)
        # Freeze the baseline-v1 input contract so old saves retain future calls.
        facts.pop("hurried")
        facts.pop("phase")
        public = dumps(facts, sort_keys=True, separators=(",", ":"))
        digest = sha256(f"baseline-v1:{self._seed}:{role}:{public}".encode()).digest()
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
        if protecting and "kneel" in observation.game_actions and observation.down < 4:
            return "kneel"
        chasing = (
            not observation.overtime
            and observation.quarter == 4
            and observation.remaining <= self.behavior.chase_seconds
            and observation.score_difference < 0
        )
        if observation.down == 4 and not chasing:
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

    def decision(self, observation: CoachObservation) -> str:
        """Conservative baseline preferences with engine-constrained fallback."""
        choices = observation.choices
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
