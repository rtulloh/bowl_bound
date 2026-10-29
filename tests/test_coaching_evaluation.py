"""One-action estimates resolve football procedures only through isolated engines."""

from dataclasses import replace
from random import getstate

import pytest

from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, Play, ResultKind, SpecialTeamsColumn
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, team_chart, yards
from tests.test_coaching import observation
from tests.test_models import provenance


def test_isolated_analysis_factory_preserves_explicit_field_without_touching_original() -> None:
    home, away = default_teams()
    original = PlaySession.new(home, away, seed=7)
    before = original.view()
    field = FieldState(Possession.AWAY, 23, 4, 2)
    analysis = PlaySession.for_analysis(home, away, field, overtime=True)
    view = analysis.view()
    assert (
        view.state.possession,
        view.state.yards_to_goal,
        view.state.down,
        view.state.yards_to_go,
    ) == ("away", 23, 4, 2)
    assert not view.log and not view.pending and view.score.home == view.score.away == 0
    assert original.view() == before


def test_constant_play_estimate_matches_real_engine_and_is_repeatable() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    home, away = team_chart("Home", offense=5), team_chart("Away", defense=0)
    obs = observation(offense=("1",), defense=("A",), special=())
    state = getstate()
    result = evaluate_action(home, away, obs, "1", role="offense", samples=8)
    assert result.complete and result.samples == 8 and result.failed_samples == 0
    assert result.mean_utility is not None and result.mean_utility > 0
    assert result.turnover_rate == 0 and result.mean_points == 0
    assert result == evaluate_action(home, away, obs, "1", role="offense", samples=8)
    assert getstate() == state


def test_lost_ball_and_offensive_recovery_are_distinguished_by_engine() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2)
    home = replace(team_chart("Home", plays={Play.ONE: fumble}), recovery_range=range(10, 40))
    away = team_chart("Away", defense=0)
    obs = observation(offense=("1",), defense=("A",), special=())
    recovered = evaluate_action(home, away, obs, "1", role="offense", samples=8)
    assert recovered.complete and recovered.turnover_rate == 0
    home = team_chart(
        "Home", plays={Play.ONE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=10)}
    )
    away = replace(
        away,
        special_teams=tuple(
            replace(r, cell=yards(0)) if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN else r
            for r in away.special_teams
        ),
    )
    intercepted = evaluate_action(home, away, obs, "1", role="offense", samples=8)
    assert intercepted.complete and intercepted.turnover_rate == 1
    assert intercepted.mean_utility < recovered.mean_utility


def test_penalty_decisions_are_settled_instead_of_zero_yard_guesses() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    home, away = default_teams()
    obs = observation(offense=("8",), defense=("A",), special=(), down=3, distance=8)
    result = evaluate_action(home, away, obs, "8", role="offense", samples=8)
    assert result.complete and result.turnover_rate == 0
    assert result.mean_utility is not None and result.mean_utility > 0


def test_field_goal_uses_engine_probability_and_score() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    home, away = team_chart("Home"), team_chart("Away")
    home = replace(
        home,
        special_teams=tuple(
            replace(r, cell=yards(100)) if r.column is SpecialTeamsColumn.FIELD_GOAL else r
            for r in home.special_teams
        ),
    )
    obs = observation(
        offense=("1",),
        defense=("A",),
        special=("field_goal",),
        yards_to_goal=20,
        down=4,
        distance=5,
    )
    made = evaluate_action(home, away, obs, "field_goal", role="offense", samples=8)
    assert made.complete and made.mean_points == 3
    home = replace(
        home,
        special_teams=tuple(
            replace(r, cell=yards(0)) if r.column is SpecialTeamsColumn.FIELD_GOAL else r
            for r in home.special_teams
        ),
    )
    missed = evaluate_action(home, away, obs, "field_goal", role="offense", samples=8)
    assert missed.complete and missed.mean_points == 0
    assert made.mean_utility > missed.mean_utility


def test_defensive_evaluation_is_from_defensive_side_not_possession() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    home, away = team_chart("Home", offense=15), team_chart("Away", defense=0)
    obs = observation(side="away", offense=("1",), defense=("A",), special=())
    result = evaluate_action(home, away, obs, "A", role="defense", samples=8)
    assert result.complete and result.mean_utility < 0


def test_rejected_engine_branches_are_not_silently_renormalized() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action
    from bowl_bound.models import Priority

    home = team_chart("Home", plays={Play.ONE: replace(yards(4), priority=Priority.BRACKETED)})
    result = evaluate_action(
        home,
        team_chart("Away"),
        observation(offense=("1",), defense=("A",)),
        "1",
        role="offense",
        samples=4,
    )
    assert not result.complete and result.failed_samples == 4
    assert (
        result.mean_utility is None and result.turnover_rate is None and result.mean_points is None
    )


@pytest.mark.parametrize("samples", [0, -1, True, 1.5, 257])
def test_invalid_sample_budget_is_refused(samples: object) -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    with pytest.raises(ValueError, match="samples"):
        evaluate_action(*default_teams(), observation(), "1", role="offense", samples=samples)


def test_unoffered_actions_and_invalid_roles_are_rejected() -> None:
    from bowl_bound.coaching_evaluation import evaluate_action

    with pytest.raises(ValueError, match="offered"):
        evaluate_action(*default_teams(), observation(), "not-legal", role="offense")
    with pytest.raises(ValueError, match="role"):
        evaluate_action(*default_teams(), observation(), "1", role="unknown")


@pytest.mark.parametrize(
    "weights", [(1.0,), (0.0,) * 6, (-1.0,) * 6, (float("nan"),) * 6, (float("inf"),) * 6]
)
def test_invalid_opponent_mixtures_are_rejected(weights: tuple[float, ...]) -> None:
    from bowl_bound.coaching_evaluation import evaluate_action
    from tests.synthetic_teams import team_chart
    from tests.test_coaching import observation

    with pytest.raises(ValueError, match="opponent weights"):
        evaluate_action(
            team_chart("Home"),
            team_chart("Away"),
            observation(),
            "1",
            role="offense",
            opponent_weights=weights,
        )


def test_weighted_hypothetical_opponent_never_changes_live_or_global_randomness() -> None:
    from random import getstate

    from bowl_bound.coaching_evaluation import evaluate_action
    from tests.synthetic_teams import team_chart
    from tests.test_coaching import observation

    before = getstate()
    first = evaluate_action(
        team_chart("Home"),
        team_chart("Away"),
        observation(),
        "1",
        role="offense",
        opponent_weights=(1, 1, 1, 1, 1, 5),
    )
    assert first.complete and getstate() == before
    assert first == evaluate_action(
        team_chart("Home"),
        team_chart("Away"),
        observation(),
        "1",
        role="offense",
        opponent_weights=(1, 1, 1, 1, 1, 5),
    )


def test_hypothetical_opposing_calls_follow_weights_not_the_live_hidden_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    from bowl_bound.coaching_evaluation import evaluate_action
    from bowl_bound.session import PlaySession
    from tests.synthetic_teams import team_chart
    from tests.test_coaching import observation

    seen = []
    original = PlaySession.snap

    def snap(self, play, formation, **kwargs):
        seen.append(formation)
        return original(self, play, formation, **kwargs)

    monkeypatch.setattr(PlaySession, "snap", snap)
    estimate = evaluate_action(
        team_chart("Home"),
        team_chart("Away"),
        replace(observation(), defense=("A", "F")),
        "1",
        role="offense",
        opponent_weights=(1, 1000),
    )
    assert estimate.complete and len(seen) == 32 and seen.count("F") >= 30
