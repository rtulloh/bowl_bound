"""Development-only observation of policy draws without changing their RNG stream."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from random import Random
from unittest.mock import patch

from .coaching import BaselineCoach, CoachObservation


class _ObservedRandom(Random):
    def __init__(self, source: Random, draws: list[dict[str, float]]) -> None:
        self._source = source
        self._draws = draws

    def choice(self, population: Sequence[str]) -> str:
        selected = self._source.choice(population)
        self._draws.append({key: 1 / len(population) for key in population})
        return selected

    def choices(
        self,
        population: Sequence[str],
        weights: Sequence[float] | None = None,
        *,
        cum_weights: Sequence[float] | None = None,
        k: int = 1,
    ) -> list[str]:
        selected = self._source.choices(population, weights, cum_weights=cum_weights, k=k)
        if cum_weights is not None:
            weights = [
                cum_weights[0],
                *(b - a for a, b in zip(cum_weights, cum_weights[1:], strict=False)),
            ]
        values = tuple(weights) if weights is not None else (1.0,) * len(population)
        total = sum(values)
        self._draws.append(
            {key: value / total for key, value in zip(population, values, strict=True)}
        )
        return selected


@contextmanager
def capture_preferences(
    coach: BaselineCoach,
    *,
    observation: CoachObservation | None = None,
) -> Iterator[list[dict[str, float]]]:
    """Observe this coach only; no global RNG patch, extra draw or live dice access.

    The final draw is the selected policy mixture; earlier discarded fallback
    draws are not reported. A deterministic decision has no draws.
    """
    draws: list[dict[str, float]] = []
    original = coach._random

    def observed(context: CoachObservation, role: str) -> Random:
        # coach_step also prepares the next concealed turn; never export its
        # preview mixture as evidence for the call that just committed.
        selected_draws = draws if observation is None or observation == context else []
        return _ObservedRandom(original(context, role), selected_draws)

    with patch.object(coach, "_random", observed):
        yield draws
