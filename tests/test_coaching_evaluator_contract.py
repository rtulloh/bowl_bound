"""AI-006: evaluator dispatch and errors match engine contracts."""

from dataclasses import replace
from random import Random

import pytest

from bowl_bound import coaching_evaluation as evaluation
from bowl_bound.coaching_evaluation import EvaluationError, evaluate_action
from bowl_bound.session import InvalidDecisionError, PlayReport, PlaySession
from tests.synthetic_teams import team_chart
from tests.test_coaching import observation


@pytest.mark.parametrize("weighted", [False, True])
def test_hail_mary_uses_regulation_call_and_hurry_without_opponent_sampling(
    monkeypatch: pytest.MonkeyPatch,
    weighted: bool,
) -> None:
    seen = []
    original = PlaySession.snap

    def snap(self: PlaySession, play: str, formation: str, **kwargs: object) -> PlayReport:
        seen.append((play, formation, kwargs.get("hurried"), kwargs.get("hail_mary")))
        return original(self, play, formation, **kwargs)

    original_choice, original_choices = Random.choice, Random.choices

    def choice(self: Random, population: tuple[object, ...]) -> object:
        if tuple(population) == tuple("ABCDEF"):
            pytest.fail("fixed engine action sampled a discarded opponent call")
        return original_choice(self, population)

    def choices(self: Random, population: tuple[object, ...], **kwargs: object) -> list[object]:
        if tuple(population) == tuple("ABCDEF"):
            pytest.fail("fixed engine action sampled a discarded weighted opponent call")
        return original_choices(self, population, **kwargs)

    monkeypatch.setattr(PlaySession, "snap", snap)
    monkeypatch.setattr(Random, "choice", choice)
    monkeypatch.setattr(Random, "choices", choices)
    result = evaluate_action(
        team_chart("Home"),
        team_chart("Away"),
        observation(game_actions=("hail_mary",), hurried=True),
        "hail_mary",
        role="offense",
        samples=3,
        opponent_weights=(1.0,) * 6 if weighted else None,
    )
    assert result.complete
    assert seen == [("8", "A", True, True)] * 3


@pytest.mark.parametrize("stage", ["snap", "settle", "utility"])
def test_unexpected_value_errors_are_not_disguised_as_analysis_fallback(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    def broken(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic programming error")

    if stage == "snap":
        monkeypatch.setattr(PlaySession, "snap", broken)
    else:
        monkeypatch.setattr(evaluation, "_" + stage, broken)
    with pytest.raises(ValueError, match="synthetic programming error"):
        evaluate_action(
            team_chart("Home"), team_chart("Away"), observation(), "1", role="offense", samples=3
        )


@pytest.mark.parametrize("error", [EvaluationError, InvalidDecisionError])
def test_declared_engine_analysis_failures_invalidate_all_samples(
    monkeypatch: pytest.MonkeyPatch,
    error: type[ValueError],
) -> None:
    def refused(*args: object, **kwargs: object) -> None:
        raise error("synthetic declared failure")

    monkeypatch.setattr(PlaySession, "snap", refused)
    result = evaluate_action(
        team_chart("Home"), team_chart("Away"), observation(), "1", role="offense", samples=3
    )
    assert result.failed_samples == 3 and not result.complete
    assert result.mean_utility is result.mean_points is result.turnover_rate is None


def test_turnover_rate_is_documented_as_possession_loss_not_football_turnovers() -> None:
    result = evaluate_action(
        team_chart("Home"),
        team_chart("Away", defense=0),
        observation(down=4, distance=10, yards_to_goal=80),
        "punt",
        role="offense",
        samples=4,
    )
    assert result.complete and result.turnover_rate == 1


@pytest.mark.parametrize("role", ["offense", "defense"])
def test_declared_hurry_field_reaches_both_scrimmage_roles(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    seen = []
    original = PlaySession.snap

    def snap(self: PlaySession, play: str, formation: str, **kwargs: object) -> PlayReport:
        seen.append(kwargs["hurried"])
        return original(self, play, formation, **kwargs)

    monkeypatch.setattr(PlaySession, "snap", snap)
    obs = replace(observation(hurried=True), side="home" if role == "offense" else "away")
    result = evaluate_action(
        team_chart("Home"),
        team_chart("Away", defense=0),
        obs,
        "1" if role == "offense" else "A",
        role=role,
        samples=3,
    )
    assert result.complete and seen == [True] * 3
