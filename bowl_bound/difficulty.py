"""Bowl Bound difficulty preferences inspired by Paydirt, without its NFL rules.

Medium tilts run/pass groups, not individual chart rankings. Hard combines bounded
real-engine evaluation with committed-public opponent frequencies and recent-call
variety. No policy owns or changes gameplay dice.
"""

from collections import Counter, deque
from dataclasses import asdict, replace
from hashlib import sha256
from json import dumps
from math import exp
from random import Random

from .chart_coaching import ChartAwareCoach
from .coaching import BaselineCoach, CoachObservation, safe_choice
from .coaching_evaluation import ActionEstimate, evaluate_action
from .coaching_profiles import behavior_for_policy
from .coaching_situations import SituationBucket, situation_bucket
from .models import TeamChart
from .player_coaching import estimate_plays
from .session import SessionPhase

AGGRESSION = {
    mode: behavior_for_policy(f"{mode}-v1").aggression for mode in ("easy", "medium", "hard")
}
_ADVANCED_DEFENSE_CALLS = frozenset(
    {
        "RUN",
        "PASS",
        "NICKEL",
        "REDZONE",
        *(f"WC{number}" for number in (1, 2, 3, 4, 6, 7, 8, 9)),
        "WC5",
        "WC5SOP",
        "WC5BLP",
        "WCSNEAK",
        "WCRZDZ",
    }
)


class DifficultyCoach(ChartAwareCoach):
    """Versioned preferences over legal controls with replay-reconstructed history.

    Previews never update history. Per-team role histories prevent learning from
    our own offense as though it were the opposing offense.
    """

    def __init__(
        self, seed: int, home: TeamChart, away: TeamChart, mode: str, *, version: int = 1
    ) -> None:
        if mode not in AGGRESSION:
            raise ValueError("difficulty must be easy, medium or hard")
        if type(version) is not int or version not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
            raise ValueError("difficulty policy version must be 1 through 10")
        super().__init__(seed, home, away, version=version)
        self.mode = mode
        self.behavior = behavior_for_policy(f"{mode}-v{version}")
        self.aggression = self.behavior.aggression
        self.policy = f"{mode}-v{version}"
        self._counts: dict[tuple[str, str], Counter[str]] = {
            (side, role): Counter() for side in ("home", "away") for role in ("offense", "defense")
        }
        self._recent: dict[tuple[str, str], deque[str]] = {
            key: deque(maxlen=self.behavior.recent_calls) for key in self._counts
        }
        self._situational_recent: dict[tuple[str, str], deque[tuple[SituationBucket, str]]] = {
            key: deque(maxlen=self.behavior.recent_calls) for key in self._counts
        }
        self._strength = {"home": self._run_bias(home), "away": self._run_bias(away)}

    def call_history(self) -> tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...]:
        """Return stable committed call counts by side and role for final summaries."""
        return tuple(
            (side, role, tuple(sorted(counts.items())))
            for (side, role), counts in sorted(self._counts.items())
            if counts
        )

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
        facts = asdict(observation)
        if self.version < 8:
            facts.pop("decision_outcomes")
        if self.version < 9:
            facts.pop("advanced_ii")
            facts.pop("free_advanced_defense")
        if self.version == 1:
            facts.pop("can_kneel_out_game")
        public = dumps(facts, sort_keys=True, separators=(",", ":"))
        digest = sha256(f"{self.policy}:{self._seed}:{role}:{public}".encode()).digest()
        return Random(int.from_bytes(digest, "big"))

    def commit_call(
        self,
        offense_side: str,
        play: str,
        defense: str,
        *,
        observation: CoachObservation | None = None,
    ) -> None:
        """Learn only an already committed pair, never a preview or attempted call."""
        if (
            offense_side not in {"home", "away"}
            or (play not in "123456789Q" and play != "RZDZ")
            or type(defense) is not str
        ):
            raise ValueError("history requires a public committed offensive/defensive call")
        other = "away" if offense_side == "home" else "home"
        offense_observation = observation
        defense_observation = (
            replace(observation, side=other, score_difference=-observation.score_difference)
            if observation is not None
            else None
        )
        role_calls = [((offense_side, "offense"), play, offense_observation)]
        if defense in tuple("ABCDEF"):
            role_calls.append(((other, "defense"), defense, defense_observation))
        elif defense in _ADVANCED_DEFENSE_CALLS:
            role_calls.append(((other, "defense"), defense, defense_observation))
        else:
            raise ValueError("history requires a public committed offensive/defensive call")
        for key, value, role_observation in role_calls:
            self._counts[key][value] += 1
            self._recent[key].append(value)
            if self.mode == "hard" and self.version >= 5 and role_observation is not None:
                self._situational_recent[key].append(
                    (situation_bucket(role_observation, key[1]), value)
                )

    def _repetition_discount(self, observation: CoachObservation, role: str, key: str) -> float:
        """Discount matching Hard calls by bucket and intervening own calls."""
        bucket = situation_bucket(observation, role)
        repeats = sum(
            self.behavior.repetition_decay**age
            for age, (past_bucket, past_key) in enumerate(
                reversed(self._situational_recent[(observation.side, role)])
            )
            if past_bucket == bucket and past_key == key
        )
        return max(
            self.behavior.repetition_floor,
            1 / (1 + self.behavior.repetition_multiplier * repeats),
        )

    def _basic_offense(self, obs: CoachObservation) -> str:
        fallback = BaselineCoach.offense(self, obs)
        if fallback not in obs.offense:
            return fallback
        run_probability = (
            self.behavior.run_probability_base - self.aggression / self.behavior.aggression_divisor
        )
        if obs.down >= 3 and obs.distance > self.behavior.passing_distance:
            run_probability = self.behavior.passing_down_run_probability
            if self.version >= 4:
                run_probability += (
                    0.5 - self.aggression
                ) * self.behavior.passing_down_aggression_scale
        elif self.mode == "medium" and obs.down <= 2:
            run_probability += self._strength[obs.side]
        run_probability += self._situational_pressure(obs) * self.behavior.pressure_run_shift
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

    @staticmethod
    def _situational_offense(observation: CoachObservation) -> CoachObservation:
        """Remove short-yardage-only calls before a coaching tier evaluates them."""
        if "Q" not in observation.offense or observation.distance <= 2:
            return observation
        return replace(observation, offense=tuple(key for key in observation.offense if key != "Q"))

    def _situational_pressure(self, observation: CoachObservation) -> float:
        """Return signed, bounded score pressure; positive protects a lead."""
        if (
            self.version < 4
            or observation.overtime
            or observation.quarter not in {2, 4}
            or observation.remaining <= 0
            or observation.score_difference == 0
        ):
            return 0.0
        minutes_left = max(observation.remaining / 60, 1.0)
        scores_needed = abs(observation.score_difference) / self.behavior.pressure_points_per_score
        pressure = 1 - exp(-scores_needed / minutes_left)
        return pressure if observation.score_difference > 0 else -pressure

    @staticmethod
    def _public_field_goal_distance(observation: CoachObservation) -> int:
        """Return the conventional attempt distance visible from the line of scrimmage."""
        return observation.yards_to_goal + 17

    def _public_fourth_down_call(self, observation: CoachObservation) -> str | None:
        """Choose a kick, punt, or go decision without inspecting team chart data.

        Version 10's fourth-down policy is deliberately shared with a human
        player: line of scrimmage, yards to gain, clock, score, and difficulty
        aggression are its only inputs. The engine still resolves any selected
        kick from its chart.
        """
        if (
            self.version < 10
            or observation.overtime
            or observation.phase == SessionPhase.TWO_POINT_TRY.value
            or observation.down != 4
        ):
            return None

        field_goal_available = "field_goal" in observation.special
        punt_available = "punt" in observation.special
        field_goal_distance = self._public_field_goal_distance(observation)
        late_trailing = (
            observation.quarter == 4
            and observation.remaining <= self.behavior.chase_seconds
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
            if observation.distance == 1 and self.aggression >= 0.5:
                return "go"
            return "field_goal"
        if field_goal_available and field_goal_distance <= 50:
            return "field_goal"
        if field_goal_available and field_goal_distance <= 55:
            if self.aggression >= 0.5:
                return "field_goal"
            return "punt" if punt_available else "go"
        if observation.distance == 1 and self.aggression >= 0.5:
            return "go"
        return "punt" if punt_available else "go"

    def offense(self, observation: CoachObservation) -> str:
        self.analysis_fallback = False
        observation = self._situational_offense(observation)
        last_snap = (
            self.version >= 3
            and not observation.overtime
            and observation.quarter in {2, 4}
            and 0 < observation.remaining <= 20
            and observation.score_difference in {-2, -1}
        )
        if last_snap and self.version < 10 and "field_goal" in observation.special:
            field_goal = next(
                (
                    estimate
                    for estimate in self.estimates(observation, "offense")
                    if estimate.key == "field_goal"
                ),
                None,
            )
            if field_goal is not None and field_goal.complete and field_goal.mean_points == 3:
                return "field_goal"
        if (
            last_snap
            and self.version >= 10
            and "field_goal" in observation.special
            and self._public_field_goal_distance(observation) <= 55
        ):
            return "field_goal"
        if (
            self.version >= 3
            and not observation.overtime
            and observation.quarter in {2, 4}
            and 0 < observation.remaining <= 20
            and observation.score_difference < 0
            and "hail_mary" in observation.game_actions
        ):
            return "hail_mary"
        public_fourth_down_call = self._public_fourth_down_call(observation)
        if public_fourth_down_call in {"field_goal", "punt"}:
            return public_fourth_down_call
        if public_fourth_down_call == "go":
            return self._basic_offense(observation)
        fallback = self._basic_offense(observation)
        if observation.phase == SessionPhase.TWO_POINT_TRY.value and (
            observation.down != 1 or observation.yards_to_goal != 2 or observation.distance != 2
        ):
            # The evaluator models canonical tries from the two. Keep an
            # engine-adjusted attempt playable without inventing a rollout.
            return fallback
        if not observation.offense or fallback == "kneel":
            return fallback
        if self.version < 3:
            return (
                self._select(observation, "offense", fallback) if self.mode == "hard" else fallback
            )

        late_half = (
            not observation.overtime
            and observation.quarter in {2, 4}
            and observation.remaining <= self.behavior.late_seconds
        )
        fourth_down = observation.down == 4
        if self.mode != "hard" and not fourth_down and not late_half:
            return fallback
        selection = observation
        needs_touchdown = (
            not observation.overtime
            and observation.quarter == 4
            and observation.remaining <= self.behavior.chase_seconds
            and observation.score_difference <= -4
        )
        protects_multi_score_lead = (
            not observation.overtime
            and observation.quarter == 4
            and observation.remaining <= self.behavior.protect_seconds
            and observation.score_difference >= self.behavior.large_lead_points
            and fourth_down
        )
        if needs_touchdown:
            selection = replace(
                observation,
                special=(),
                game_actions=tuple(key for key in observation.game_actions if key == "hail_mary"),
            )
        elif protects_multi_score_lead:
            selection = replace(
                observation,
                offense=(),
                special=tuple(key for key in observation.special if key in {"punt", "field_goal"}),
                game_actions=(),
            )
        legal = selection.offense + selection.special + selection.game_actions
        if not legal:
            return fallback
        selection_fallback = fallback if fallback in legal else safe_choice("", legal).key
        return self._select(selection, "offense", selection_fallback)

    def decision(self, observation: CoachObservation) -> str:
        """Apply versioned margin-aware try choices before the baseline fallback."""
        if self.version >= 7:
            self.analysis_fallback = False
        choices = observation.choices
        if (
            self.version >= 3
            and not observation.overtime
            and observation.quarter == 4
            and "conversion:kick" in choices
            and "conversion:two" in choices
        ):
            if observation.score_difference <= self.behavior.two_point_tie_margin:
                return "conversion:two"
            if (
                observation.score_difference == self.behavior.two_point_lead_margin
                and observation.remaining <= self.behavior.two_point_lead_seconds
                and self.aggression >= self.behavior.two_point_aggression_threshold
            ):
                return "conversion:two"
            if (
                observation.score_difference >= self.behavior.large_lead_points
                and observation.remaining <= self.behavior.protect_seconds
            ):
                return "conversion:kick"
        return super().decision(observation)

    def defense(self, observation: CoachObservation) -> str:
        self.analysis_fallback = False
        safe_choice("", observation.defense)
        weights = [
            (1 + self.aggression if key == "F" else 1)
            * self._defense_situation_weight(observation, key)
            for key in observation.defense
        ]
        fallback = self._random(observation, "defense").choices(
            observation.defense, weights=weights, k=1
        )[0]
        return self._select(observation, "defense", fallback) if self.mode == "hard" else fallback

    def _defense_situation_weight(self, observation: CoachObservation, key: str) -> float:
        """Adjust formation preferences without removing legal defensive calls."""
        if self.version < 6:
            return 1.0
        multiplier = self.behavior.defense_situation_multiplier
        weight = 1.0
        if observation.yards_to_goal <= self.behavior.defense_goal_line_yards and key in {"B", "C"}:
            weight *= multiplier
        likely_fourth_down_kick = observation.down == 4 and (
            "field_goal" in observation.special
            or (
                "punt" in observation.special
                and observation.distance > self.behavior.passing_distance
            )
        )
        if likely_fourth_down_kick:
            if key == "A":
                weight *= multiplier
            elif key == "F":
                weight /= multiplier
        protecting_lead = (
            not observation.overtime
            and observation.quarter in {2, 4}
            and observation.remaining <= self.behavior.protect_seconds
            and observation.score_difference >= self.behavior.large_lead_points
        )
        if protecting_lead:
            if key in {"D", "E"}:
                weight *= multiplier
            elif key == "F":
                weight /= multiplier
        return weight

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
        if role == "offense" and self.version >= 4:
            if key in "12345":
                preference = 1.0
            elif key in "6789":
                preference = 1 + self.aggression
            elif key in {"punt", "field_goal"}:
                preference = 2 - self.aggression
            else:
                preference = 1.0
            if key in "6789":
                preference *= exp(
                    -self._situational_pressure(observation) * self.behavior.pressure_run_shift
                )
        elif role == "offense" and self.version >= 3:
            if observation.down == 4 and key in tuple("123456789"):
                preference = 1 + self.aggression
            elif key in {"punt", "field_goal"}:
                preference = 2 - self.aggression
            else:
                preference = 1 + self.aggression if key in {"7", "8", "9"} else 1
        else:
            aggressive = key in {"7", "8", "9"} if role == "offense" else key == "F"
            preference = 1 + self.aggression if aggressive else 1
        if role == "defense" and self.version >= 6:
            preference *= self._defense_situation_weight(observation, key)
        if self.mode == "hard" and self.version >= 5:
            return weight * preference * self._repetition_discount(observation, role, key)
        return weight * preference / (1 + recent[key])

    def _selection_role(self, role: str) -> str:
        return role
