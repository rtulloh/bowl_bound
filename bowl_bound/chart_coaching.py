"""Opt-in chart-aware-v1 coaching; engine rollouts, not duplicated football rules."""

from collections import OrderedDict
from dataclasses import replace
from math import exp

from .coaching import BaselineCoach, CoachObservation, safe_choice
from .coaching_evaluation import (
    ActionEstimate,
    RazzleChoiceEstimate,
    evaluate_action,
    sample_razzle_decisions,
)
from .coaching_profiles import behavior_for_policy
from .models import TeamChart


class ChartAwareCoach(BaselineCoach):
    """Prefer sampled one-action utility while retaining a varied legal mixture.

    Both immutable board charts are coach-available data. The private selection
    seed is independent of analysis and gameplay. Model values use no human
    selected call, gameplay seed, live session or future dice.
    """

    def __init__(self, seed: int, home: TeamChart, away: TeamChart, *, version: int = 1) -> None:
        super().__init__(seed, version=version)
        self.policy = f"chart-v{version}"
        self.behavior = behavior_for_policy(self.policy)
        self._home, self._away = home, away
        self._cache: OrderedDict[
            tuple[CoachObservation, str, tuple[float, ...] | None], tuple[ActionEstimate, ...]
        ] = OrderedDict()
        self.analysis_fallback = False
        self._decision_cache: OrderedDict[CoachObservation, tuple[RazzleChoiceEstimate, ...]] = (
            OrderedDict()
        )

    @property
    def cached_situations(self) -> int:
        return len(self._cache)

    def estimates(
        self,
        observation: CoachObservation,
        role: str,
        *,
        opponent_weights: tuple[float, ...] | None = None,
    ) -> tuple[ActionEstimate, ...]:
        """Private audit values, never include them in a concealed-call preview."""
        if role not in {"offense", "defense"}:
            raise ValueError("coaching role must be offense or defense")
        model = replace(observation, play_number=0)
        weights = (
            opponent_weights
            if opponent_weights is not None
            else self._opponent_weights(model, role)
        )
        key = (model, role, weights)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        candidates = observation.defense if role == "defense" else observation.offense
        if role == "offense":
            late_quarter = {2, 4} if self.version >= 3 else {4}
            late = (
                not observation.overtime
                and observation.quarter in late_quarter
                and observation.remaining <= self.behavior.late_seconds
            )
            if observation.down == 4 or late:
                candidates += tuple(k for k in observation.special if k in {"punt", "field_goal"})
            candidates += tuple(k for k in observation.game_actions if k == "hail_mary")
        result = tuple(self._evaluate(model, candidate, role, weights) for candidate in candidates)
        self._cache[key] = result
        while len(self._cache) > self.behavior.cache_entries:
            self._cache.popitem(last=False)
        return result

    def _opponent_weights(
        self, observation: CoachObservation, role: str
    ) -> tuple[float, ...] | None:
        return None

    def _evaluate(
        self,
        observation: CoachObservation,
        key: str,
        role: str,
        opponent_weights: tuple[float, ...] | None,
    ) -> ActionEstimate:
        return evaluate_action(
            self._home, self._away, observation, key, role=role, opponent_weights=opponent_weights
        )

    def _preference_weight(
        self, observation: CoachObservation, role: str, key: str, weight: float
    ) -> float:
        return weight

    def _selection_role(self, role: str) -> str:
        return f"{self.policy}-{role}"

    def _select(self, observation: CoachObservation, role: str, fallback: str) -> str:
        self.analysis_fallback = False
        estimates = self.estimates(observation, role)
        # A failed candidate might be better than the successful candidates.
        # Fall back for the whole comparison rather than biasing against it.
        if not estimates or any(not estimate.complete for estimate in estimates):
            self.analysis_fallback = True
            return fallback
        best = max(e.mean_utility for e in estimates if e.mean_utility is not None)
        weights = []
        for estimate in estimates:
            assert estimate.mean_utility is not None
            weight = exp((estimate.mean_utility - best) / self.behavior.temperature)
            weights.append(self._preference_weight(observation, role, estimate.key, weight))
        total = sum(weights)
        mixture = [
            self.behavior.exploration / len(weights) + self.behavior.exploitation * weight / total
            for weight in weights
        ]
        return self._random(observation, self._selection_role(role)).choices(
            [estimate.key for estimate in estimates],
            weights=mixture,
            k=1,
        )[0]

    def offense(self, observation: CoachObservation) -> str:
        self.analysis_fallback = False
        fallback = super().offense(observation)
        if not observation.offense or fallback == "kneel":
            return fallback
        return self._select(observation, "offense", fallback)

    def defense(self, observation: CoachObservation) -> str:
        fallback = super().defense(observation)
        safe_choice(fallback, observation.defense)
        return self._select(observation, "defense", fallback)

    def decision(self, observation: CoachObservation) -> str:
        self.analysis_fallback = False
        if self.version >= 11 and observation.razzle_context is not None:
            model = replace(observation, play_number=0)
            if model not in self._decision_cache:
                self._decision_cache[model] = sample_razzle_decisions(self._home, self._away, model)
                while len(self._decision_cache) > self.behavior.cache_entries:
                    self._decision_cache.popitem(last=False)
            self._decision_cache.move_to_end(model)
            estimates = self._decision_cache[model]
            if estimates and all(
                estimate.complete and estimate.mean_utility is not None for estimate in estimates
            ):
                choose = max if observation.side == observation.possession else min
                return choose(estimates, key=lambda item: item.mean_utility).key
            self.analysis_fallback = True
            choice = super().decision(observation)
            self.analysis_fallback = True
            return choice
        if observation.side != observation.possession and "clock:standard" in observation.choices:
            timeout = f"clock:timeout:{observation.side}"
            if (
                not observation.overtime
                and observation.quarter == 4
                and observation.remaining <= self.behavior.late_seconds
                and observation.score_difference < 0
                and timeout in observation.choices
            ):
                return timeout
            observation = replace(
                observation,
                choices=tuple(
                    key for key in observation.choices if key in {"clock:standard", timeout}
                ),
            )
        return super().decision(observation)
