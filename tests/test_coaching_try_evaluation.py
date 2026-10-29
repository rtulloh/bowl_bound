"""AI-004: hypothetical tries use real try scoring and termination."""

from dataclasses import replace

import pytest

from bowl_bound.coaching_session import _observation
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.session import PlaySession, SessionPhase
from tests.synthetic_teams import team_chart
from tests.test_overtime import miss_series, overtime_game, start_overtime
from tests.test_regulation import snap


@pytest.mark.parametrize("possession", ["home", "away"])
@pytest.mark.parametrize("paired", [False, True])
def test_real_overtime_try_estimates_score_two_and_failed_try_has_no_possession(
    possession: str,
    paired: bool,
) -> None:
    game = overtime_game(2021)
    start_overtime(game, first=possession)
    if paired:
        for _ in range(4):
            miss_series(game)
    else:
        snap(game)
        game.decide("conversion:two")
    before = game.view()
    assert before.phase == SessionPhase.TWO_POINT_TRY.value
    obs = _observation(before, possession)
    charts = game._session._charts
    coach = DifficultyCoach(31, charts[Possession.HOME], charts[Possession.AWAY], "hard")
    values = {entry.key: entry for entry in coach.estimates(obs, "offense")}
    assert values["1"].complete and values["3"].complete
    assert values["1"].mean_points == 2
    assert values["1"].mean_utility == 2
    assert values["3"].mean_points == 0
    assert values["3"].mean_utility == 0
    assert game.view() == before

    other = "away" if possession == "home" else "home"
    defending = replace(_observation(before, other), offense=("1",))
    defense_values = coach.estimates(defending, "defense")
    assert all(entry.complete and entry.mean_points == -2 for entry in defense_values)
    assert all(entry.mean_utility == -2 for entry in defense_values)


def test_try_and_scrimmage_at_identical_spot_have_distinct_model_cache_entries() -> None:
    game = overtime_game(2021)
    start_overtime(game)
    snap(game)
    game.decide("conversion:two")
    obs = _observation(game.view(), "home")
    charts = game._session._charts
    coach = DifficultyCoach(31, charts[Possession.HOME], charts[Possession.AWAY], "hard")
    tried = coach.estimates(obs, "offense")
    scrimmage = coach.estimates(replace(obs, phase="scrimmage"), "offense")
    assert tried is not scrimmage
    assert coach.cached_situations == 2
    assert tried[0].mean_points == 2 and scrimmage[0].mean_points == 6


@pytest.mark.parametrize("phase", ["two_point_try", "scrimmage", None, True])
def test_analysis_factory_requires_typed_phase(phase: object) -> None:
    with pytest.raises(TypeError, match="phase"):
        PlaySession.for_analysis(
            team_chart("Home"),
            team_chart("Away"),
            FieldState(Possession.HOME, 2, 1, 2),
            phase=phase,
        )


@pytest.mark.parametrize(
    "field", [FieldState(Possession.HOME, 3, 1, 3), FieldState(Possession.AWAY, 2, 2, 2)]
)
def test_analysis_factory_refuses_noncanonical_try_start(field: FieldState) -> None:
    with pytest.raises(ValueError, match="first-and-goal"):
        PlaySession.for_analysis(
            team_chart("Home"), team_chart("Away"), field, phase=SessionPhase.TWO_POINT_TRY
        )


def test_ordinary_overtime_analysis_does_not_schedule_a_kickoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = overtime_game(2021)
    start_overtime(game)
    before = game.view()
    obs = _observation(before, "home")
    charts = game._session._charts

    def no_kick(*args: object, **kwargs: object) -> None:
        pytest.fail("ordinary overtime rollout attempted a kickoff")

    monkeypatch.setattr(PlaySession, "kick", no_kick)
    coach = DifficultyCoach(31, charts[Possession.HOME], charts[Possession.AWAY], "hard")
    estimate = coach.estimates(replace(obs, offense=("1",), special=()), "offense")[0]
    assert estimate.complete and estimate.mean_points == 6
    assert game.view() == before
