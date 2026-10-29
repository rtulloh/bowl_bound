"""Bowl Bound difficulty preferences inspired by Paydirt, without its NFL rules.

Medium tilts run/pass groups, not individual chart rankings. Hard combines bounded
real-engine evaluation with committed-public opponent frequencies and recent-call
variety. No policy owns or changes gameplay dice.
"""

from collections import Counter, deque
from dataclasses import asdict
from hashlib import sha256
from json import dumps
from random import Random

from .chart_coaching import ChartAwareCoach
from .coaching import BaselineCoach, CoachObservation, safe_choice
from .coaching_evaluation import ActionEstimate, evaluate_action
from .coaching_profiles import behavior_for_policy
from .models import TeamChart
from .player_coaching import estimate_plays

AGGRESSION = {
    mode: behavior_for_policy(f"{mode}-v1").aggression for mode in ("easy", "medium", "hard")
}


class DifficultyCoach(ChartAwareCoach):
    """Versioned preferences over legal controls with replay-reconstructed history.

    Previews never update history. Per-team role histories prevent learning from
    our own offense as though it were the opposing offense.
    """

    def __init__(self, seed: int, home: TeamChart, away: TeamChart, mode: str) -> None:
        if mode not in AGGRESSION:
            raise ValueError("difficulty must be easy, medium or hard")
        super().__init__(seed, home, away)
        self.mode = mode
        self.behavior = behavior_for_policy(f"{mode}-v1")
        self.aggression = self.behavior.aggression
        self.policy = f"{mode}-v1"
        self._counts: dict[tuple[str, str], Counter[str]] = {
            (side, role): Counter() for side in ("home", "away") for role in ("offense", "defense")
        }
        self._recent: dict[tuple[str, str], deque[str]] = {
            key: deque(maxlen=self.behavior.recent_calls) for key in self._counts
        }
        self._strength = {"home": self._run_bias(home), "away": self._run_bias(away)}

    @staticmethod
    def _run_bias(chart: TeamChart) -> float:
        # Paydirt's category-only adjustment idea, using Bowl Bound's own columns
        # and exact physical dice. Unsupported numeric coverage contributes no bias.
        groups: list[list[float]] = [[], []]
        for key in "123456789":
            (estimate,) = estimate_plays(chart.offense, (key,), down=1, distance=10)
            if not estimate.limited and estimate.average_yards is not None:
                groups[int(key) >= 6].append(float(estimate.average_yards))
        if not all(groups):
            return 0.0
        run, passing = (sum(group) / len(group) for group in groups)
        behavior = behavior_for_policy("medium-v1")
        return max(
            -behavior.medium_bias_limit,
            min(behavior.medium_bias_limit, (run - passing) / behavior.medium_bias_divisor),
        )

    def _random(self, observation: CoachObservation, role: str) -> Random:
        public = dumps(asdict(observation), sort_keys=True, separators=(",", ":"))
        digest = sha256(f"{self.policy}:{self._seed}:{role}:{public}".encode()).digest()
        return Random(int.from_bytes(digest, "big"))

    def commit_call(self, offense_side: str, play: str, defense: str) -> None:
        """Learn only an already committed pair, never a preview or attempted call."""
        if (
            offense_side not in {"home", "away"}
            or play not in tuple("123456789")
            or defense not in tuple("ABCDEF")
        ):
            raise ValueError("history requires a public committed offensive/defensive call")
        other = "away" if offense_side == "home" else "home"
        for key, value in (((offense_side, "offense"), play), ((other, "defense"), defense)):
            self._counts[key][value] += 1
            self._recent[key].append(value)

    def _basic_offense(self, obs: CoachObservation) -> str:
        fallback = BaselineCoach.offense(self, obs)
        if fallback not in obs.offense:
            return fallback
        run_probability = (
            self.behavior.run_probability_base - self.aggression / self.behavior.aggression_divisor
        )
        if obs.down >= 3 and obs.distance > self.behavior.passing_distance:
            run_probability = self.behavior.passing_down_run_probability
        elif self.mode == "medium" and obs.down <= 2:
            run_probability += self._strength[obs.side]
        run_probability = max(
            self.behavior.min_run_probability,
            min(self.behavior.max_run_probability, run_probability),
        )
        runs = sum(key in "12345" for key in obs.offense)
        passes = len(obs.offense) - runs
        weights = [
            run_probability / runs if key in "12345" else (1 - run_probability) / passes
            for key in obs.offense
        ]
        return self._random(obs, "offense").choices(obs.offense, weights=weights, k=1)[0]

    def offense(self, observation: CoachObservation) -> str:
        self.analysis_fallback = False
        fallback = self._basic_offense(observation)
        if self.mode != "hard" or not observation.offense or fallback == "kneel":
            return fallback
        return self._select(observation, "offense", fallback)

    def defense(self, observation: CoachObservation) -> str:
        self.analysis_fallback = False
        safe_choice("", observation.defense)
        weights = [1 + self.aggression if key == "F" else 1 for key in observation.defense]
        fallback = self._random(observation, "defense").choices(
            observation.defense, weights=weights, k=1
        )[0]
        return self._select(observation, "defense", fallback) if self.mode == "hard" else fallback

    def _opponent_weights(
        self, observation: CoachObservation, role: str
    ) -> tuple[float, ...] | None:
        other = "away" if observation.side == "home" else "home"
        opponent_role = "offense" if role == "defense" else "defense"
        opposing = observation.offense if role == "defense" else observation.defense
        return tuple(1.0 + self._counts[(other, opponent_role)][key] for key in opposing) or None

    def _evaluate(
        self,
        observation: CoachObservation,
        key: str,
        role: str,
        opponent_weights: tuple[float, ...] | None,
    ) -> ActionEstimate:
        return evaluate_action(
            self._home,
            self._away,
            observation,
            key,
            role=role,
            opponent_weights=opponent_weights,
            utility_policy="hard-v1",
        )

    def _preference_weight(
        self, observation: CoachObservation, role: str, key: str, weight: float
    ) -> float:
        recent = Counter(self._recent[(observation.side, role)])
        aggressive = key in {"7", "8", "9"} if role == "offense" else key == "F"
        preference = 1 + self.aggression if aggressive else 1
        return weight * preference / (1 + recent[key])

    def _selection_role(self, role: str) -> str:
        return role
