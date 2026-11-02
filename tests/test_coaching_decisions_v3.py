"""AI-012: score-aware fourth-down and conversion choices use engine facts."""

from dataclasses import replace

import pytest

from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_audit import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import NormalizedCell, ResultKind
from tests.synthetic_teams import team_chart, yards
from tests.test_coaching import observation
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def difficulty_coach(mode: str, *, version: int = 3) -> DifficultyCoach:
    """Create a policy with synthetic charts only."""
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=version)


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v3_conversion_uses_two_points_to_tie_late(side: str, mode: str) -> None:
    coach = difficulty_coach(mode)
    obs = observation(
        side=side,
        possession=side,
        quarter=4,
        remaining=30,
        score_difference=-2,
        choices=("conversion:kick", "conversion:two"),
        phase="conversion_choice",
    )

    assert coach.decision(obs) == "conversion:two"


@pytest.mark.parametrize(
    "mode,expected",
    [("easy", "conversion:kick"), ("medium", "conversion:two"), ("hard", "conversion:two")],
)
def test_v3_aggression_controls_try_for_lead_when_one_point_ties(mode: str, expected: str) -> None:
    coach = difficulty_coach(mode)
    obs = observation(
        quarter=4,
        remaining=30,
        score_difference=-1,
        choices=("conversion:kick", "conversion:two"),
        phase="conversion_choice",
    )

    assert coach.decision(obs) == expected


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v3_large_late_lead_takes_the_safe_point(mode: str) -> None:
    coach = difficulty_coach(mode)
    obs = observation(
        quarter=4,
        remaining=30,
        score_difference=10,
        choices=("conversion:kick", "conversion:two"),
        phase="conversion_choice",
    )

    assert coach.decision(obs) == "conversion:kick"


def test_v3_margin_strategy_does_not_change_third_quarter_try() -> None:
    coach = difficulty_coach("hard")
    obs = observation(
        quarter=3,
        remaining=30,
        score_difference=-2,
        choices=("conversion:kick", "conversion:two"),
        phase="conversion_choice",
    )

    assert coach.decision(obs) == "conversion:kick"


def test_v10_early_long_fourth_down_uses_the_team_field_goal_chart() -> None:
    strong = replace(
        team_chart("Strong", offense=0),
        special_teams=special_chart("Strong", field_goal=yards(100)).special_teams,
    )
    weak = replace(
        team_chart("Weak", offense=0),
        special_teams=special_chart(
            "Weak", field_goal=NormalizedCell(ResultKind.NO_GOOD_FIELD_GOAL, provenance())
        ).special_teams,
    )
    opponent = team_chart("Opponent", defense=0)
    obs = observation(
        quarter=1,
        remaining=600,
        score_difference=0,
        down=4,
        distance=8,
        yards_to_goal=31,
        offense=("1",),
        special=("punt", "field_goal"),
    )

    assert DifficultyCoach(31, strong, opponent, "medium", version=10).offense(obs) == "field_goal"
    assert DifficultyCoach(31, weak, opponent, "medium", version=10).offense(obs) == "punt"


def test_v10_early_long_fourth_down_excludes_razzle_dazzle_from_kick_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coach = difficulty_coach("medium", version=10)
    obs = observation(
        quarter=1,
        remaining=600,
        score_difference=0,
        down=4,
        distance=16,
        yards_to_goal=36,
        offense=("RZDZ", "1"),
        special=("punt", "field_goal"),
    )

    def estimates(observed: CoachObservation, _: str) -> tuple[ActionEstimate, ...]:
        assert observed.offense == ()
        return (
            ActionEstimate("1", 1, 0, -2.0, 1.0, 0.0),
            ActionEstimate("punt", 1, 0, 1.0, 1.0, 0.0),
            ActionEstimate("field_goal", 1, 0, 0.0, 1.0, 0.0),
        )

    monkeypatch.setattr(coach, "estimates", estimates)

    assert coach.offense(obs) == "punt"


def test_v10_late_touchdown_need_keeps_razzle_dazzle_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coach = difficulty_coach("medium", version=10)
    obs = observation(
        quarter=4,
        remaining=60,
        score_difference=-7,
        down=4,
        distance=16,
        yards_to_goal=36,
        offense=("RZDZ", "1"),
        special=("punt", "field_goal"),
    )

    def select(observed: CoachObservation, _: str, __: str) -> str:
        assert "RZDZ" in observed.offense
        return "RZDZ"

    monkeypatch.setattr(coach, "_select", select)

    assert coach.offense(obs) == "RZDZ"


def test_v10_early_long_fourth_down_without_a_kick_keeps_razzle_dazzle() -> None:
    coach = difficulty_coach("medium", version=10)
    obs = observation(
        quarter=1,
        remaining=600,
        score_difference=0,
        down=4,
        distance=16,
        yards_to_goal=36,
        offense=("RZDZ",),
        special=(),
    )

    assert coach.offense(obs) == "RZDZ"


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v3_late_touchdown_need_does_not_punt_or_kick(
    monkeypatch: pytest.MonkeyPatch, mode: str, side: str
) -> None:
    coach = difficulty_coach(mode)
    obs = observation(
        side=side,
        possession=side,
        quarter=4,
        remaining=30,
        score_difference=-4,
        down=4,
        offense=tuple("123456789"),
        special=("punt", "field_goal"),
    )
    selected: list[tuple[CoachObservation, str, str]] = []

    def select(selected_observation: CoachObservation, role: str, fallback: str) -> str:
        selected.append((selected_observation, role, fallback))
        return fallback

    monkeypatch.setattr(coach, "_select", select)

    coach.offense(obs)

    assert selected
    filtered, role, fallback = selected[0]
    assert role == "offense"
    assert not {"punt", "field_goal"} & set(filtered.special)
    assert fallback in filtered.offense


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_v3_large_lead_late_restricts_fourth_down_to_charted_kicks(
    monkeypatch: pytest.MonkeyPatch, mode: str, side: str
) -> None:
    coach = difficulty_coach(mode)
    obs = observation(
        side=side,
        possession=side,
        quarter=4,
        remaining=30,
        score_difference=10,
        down=4,
        offense=tuple("123456789"),
        special=("punt", "field_goal"),
    )
    selected: list[CoachObservation] = []

    def select(selected_observation: CoachObservation, role: str, fallback: str) -> str:
        selected.append(selected_observation)
        return fallback

    monkeypatch.setattr(coach, "_select", select)

    coach.offense(obs)

    assert selected
    assert selected[0].offense == ()
    assert set(selected[0].special) == {"punt", "field_goal"}


def test_v3_aggression_increases_fourth_down_go_preference() -> None:
    obs = observation(down=4, special=("punt", "field_goal"))
    ratios = []
    for mode in ("easy", "medium", "hard"):
        coach = difficulty_coach(mode)
        go_weight = coach._preference_weight(obs, "offense", "1", 1.0)
        kick_weight = coach._preference_weight(obs, "offense", "punt", 1.0)
        ratios.append(go_weight / kick_weight)

    assert ratios[0] < ratios[1] < ratios[2]


def test_v3_q2_field_goal_option_comes_from_an_offered_charted_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chart = team_chart("Home")
    coach = ChartAwareCoach(31, chart, team_chart("Away"), version=3)
    obs = observation(
        quarter=2,
        remaining=10,
        down=1,
        yards_to_goal=60,
        offense=tuple("123456789"),
        special=("punt", "field_goal"),
    )
    evaluated: list[str] = []

    def evaluate(
        _: CoachObservation,
        key: str,
        __: str,
        ___: tuple[float, ...] | None,
    ) -> ActionEstimate:
        evaluated.append(key)
        return ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(coach, "_evaluate", evaluate)

    estimates = coach.estimates(obs, "offense")

    assert "field_goal" in evaluated
    assert {item.key for item in estimates} == set(evaluated)


def test_v2_conversion_strategy_remains_unchanged() -> None:
    coach = difficulty_coach("hard", version=2)
    obs = observation(
        quarter=4,
        remaining=30,
        score_difference=-2,
        choices=("conversion:kick", "conversion:two"),
        phase="conversion_choice",
    )

    assert coach.decision(obs) == "conversion:kick"


@pytest.mark.parametrize("version", [1, 2, 3])
def test_hard_try_policy_falls_back_on_an_engine_adjusted_try_spot(version: int) -> None:
    coach = difficulty_coach("hard", version=version)
    obs = observation(
        down=1,
        distance=1,
        yards_to_goal=1,
        offense=tuple("123456789"),
        special=(),
        phase="two_point_try",
    )

    assert coach.offense(obs) in obs.offense


def test_late_field_goal_uses_simulated_chart_utility_not_a_fixed_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coach = difficulty_coach("medium")
    obs = observation(
        quarter=4,
        remaining=10,
        score_difference=-3,
        down=4,
        yards_to_goal=60,
        offense=tuple("123456789"),
        special=("punt", "field_goal"),
    )
    evaluated: list[str] = []

    def evaluate(
        _: CoachObservation,
        key: str,
        __: str,
        ___: tuple[float, ...] | None,
    ) -> ActionEstimate:
        evaluated.append(key)
        utility = 1000.0 if key == "field_goal" else 0.0
        return ActionEstimate(key, 32, 0, utility, 0.0, 0.0)

    monkeypatch.setattr(coach, "_evaluate", evaluate)

    coach.offense(obs)

    assert "field_goal" in evaluated


def test_field_goal_estimate_uses_bowl_bound_chart_range_at_longer_distance() -> None:
    home = replace(
        team_chart("Home"),
        special_teams=special_chart("Home", field_goal=yards(70)).special_teams,
    )
    coach = DifficultyCoach(31, home, team_chart("Away"), "medium", version=3)
    obs = observation(
        quarter=4,
        remaining=10,
        score_difference=-3,
        down=4,
        yards_to_goal=60,
        offense=tuple("123456789"),
        special=("punt", "field_goal"),
    )

    estimate = next(item for item in coach.estimates(obs, "offense") if item.key == "field_goal")

    assert estimate.complete
    assert estimate.mean_points == 3.0


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("side", ["home", "away"])
def test_last_snap_takes_a_guaranteed_winning_field_goal_before_hail_mary(
    mode: str, side: str
) -> None:
    reliable = replace(
        team_chart("Reliable"),
        special_teams=special_chart("Reliable", field_goal=yards(70)).special_teams,
    )
    other = team_chart("Other")
    home, away = (reliable, other) if side == "home" else (other, reliable)
    coach = DifficultyCoach(31, home, away, mode, version=9)
    obs = observation(
        side=side,
        possession=side,
        quarter=4,
        remaining=10,
        score_difference=-1,
        down=2,
        distance=5,
        yards_to_goal=5,
        offense=tuple("123456789"),
        special=("punt", "field_goal"),
        game_actions=("hail_mary",),
    )

    with capture_preferences(coach, observation=obs) as draws:
        assert coach.offense(obs) == "field_goal"

    assert draws == []
