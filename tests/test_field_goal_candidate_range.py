"""AI-038: automatic field-goal candidates respect the shared public range."""

import json
from dataclasses import replace

import pytest

from bowl_bound.chart_coaching import ChartAwareCoach
from bowl_bound.coaching import (
    CoachObservation,
    field_goal_attempt_distance,
    public_fourth_down_call,
)
from bowl_bound.coaching_audit_sampling import capture_preferences
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.coaching_session import observe_game
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_coaching import observation
from tests.test_models import provenance
from tests.test_special_teams import special_chart


@pytest.fixture
def tempting_kick(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    def estimate(
        home: TeamChart, away: TeamChart, obs: CoachObservation, key: str, **kwargs: object
    ) -> ActionEstimate:
        seen.append(key)
        return ActionEstimate(key, 32, 0, 1000.0 if key == "field_goal" else 0.0, 0.0, 0.0)

    monkeypatch.setattr("bowl_bound.difficulty.evaluate_action", estimate)
    monkeypatch.setattr("bowl_bound.chart_coaching.evaluate_action", estimate)
    return seen


def coach(mode: str, *, version: int = CURRENT_DIFFICULTY_VERSION) -> DifficultyCoach:
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, version=version)


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("down", [1, 2, 3])
@pytest.mark.parametrize("quarter", [2, 4])
@pytest.mark.parametrize("yards_to_goal", [39, 76])
def test_late_half_out_of_range_field_goal_never_enters_candidate_or_selection_mixture(
    mode: str, side: str, down: int, quarter: int, yards_to_goal: int, tempting_kick: list[str]
) -> None:
    obs = observation(
        side=side,
        possession=side,
        down=down,
        distance=14,
        yards_to_goal=yards_to_goal,
        quarter=quarter,
        remaining=70,
        score_difference=-3,
    )
    policy = coach(mode)
    assert field_goal_attempt_distance(obs) == yards_to_goal + 17
    with capture_preferences(policy, observation=obs) as draws:
        call = policy.offense(obs)
    assert "field_goal" not in tempting_kick
    assert "field_goal" not in draws[-1]
    assert call != "field_goal"
    assert "field_goal" in obs.special  # The human retains the engine-legal action.


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("down", [1, 2, 3, 4])
@pytest.mark.parametrize("yards_to_goal,eligible", [(38, True), (39, False), (76, False)])
def test_current_chart_candidate_boundary_matches_public_attempt_distance(
    side: str, down: int, yards_to_goal: int, eligible: bool, tempting_kick: list[str]
) -> None:
    policy = ChartAwareCoach(
        31, team_chart("Home"), team_chart("Away"), version=CURRENT_DIFFICULTY_VERSION
    )
    obs = observation(
        side=side,
        possession=side,
        down=down,
        quarter=2,
        remaining=70,
        yards_to_goal=yards_to_goal,
    )
    keys = {estimate.key for estimate in policy.estimates(obs, "offense")}
    assert ("field_goal" in keys) is eligible
    assert ("field_goal" in tempting_kick) is eligible


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
@pytest.mark.parametrize("side", ["home", "away"])
def test_in_range_late_half_field_goal_and_fourth_down_guidance_stay_available(
    mode: str, side: str, tempting_kick: list[str]
) -> None:
    policy = coach(mode)
    obs = observation(
        side=side,
        possession=side,
        quarter=2,
        remaining=70,
        down=3,
        distance=8,
        yards_to_goal=38,
        score_difference=-3,
    )
    with capture_preferences(policy, observation=obs) as draws:
        policy.offense(obs)
    assert draws[-1]["field_goal"] > 0
    assert "field_goal" in tempting_kick
    for distance in (38, 39, 76):
        fourth = replace(obs, down=4, yards_to_goal=distance)
        assert policy.offense(fourth) == public_fourth_down_call(
            fourth, aggression=policy.aggression
        )
    assert policy.offense(replace(obs, remaining=10, yards_to_goal=20, score_difference=-2)) == (
        "field_goal"
    )


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_failed_comparison_falls_back_without_selecting_an_out_of_range_kick(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def failed(
        home: TeamChart, away: TeamChart, obs: CoachObservation, key: str, **kwargs: object
    ) -> ActionEstimate:
        seen.append(key)
        return ActionEstimate(key, 32, 1, None, None, None)

    monkeypatch.setattr("bowl_bound.difficulty.evaluate_action", failed)
    policy = coach(mode)
    call = policy.offense(
        observation(down=3, quarter=2, remaining=70, yards_to_goal=76, score_difference=-3)
    )
    assert "field_goal" not in seen
    assert call in "123456789" and policy.analysis_fallback


def test_frozen_v14_keeps_its_pre_fix_seeded_candidates(tempting_kick: list[str]) -> None:
    obs = observation(
        quarter=2,
        remaining=70,
        down=3,
        distance=14,
        yards_to_goal=76,
        score_difference=-3,
    )
    policy = coach("hard", version=14)
    assert [policy.offense(replace(obs, play_number=i)) for i in range(20)] == [
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "6",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "field_goal",
        "3",
    ]


def test_named_save_upgrades_future_policy_and_preserves_recorded_game() -> None:
    home, away = team_chart("Home"), team_chart("Away")
    original = SavedGame.new(
        home,
        away,
        home_id="2007/home",
        away_id="2007/away",
        seed=7,
        coach_seed=31,
        coach_policy="hard-v14",
    )
    original.snap("1", "A")
    payload = dumps_game(original)
    loader = {"2007/home": home, "2007/away": away}.__getitem__
    current = loads_game(payload, loader)
    frozen = loads_game(payload, loader, preserve_development_policy=True)
    assert current._coach.version == CURRENT_DIFFICULTY_VERSION == 15
    assert frozen._coach.version == 14
    assert current.view() == frozen.view() == original.view()
    before = json.loads(payload)
    after = json.loads(dumps_game(current))
    for key in ("commands", "rolls", "random_state", "state_digest", "teams"):
        assert after[key] == before[key]
    obs = observe_game(current.view(), "home")
    assert "field_goal" not in {
        estimate.key
        for estimate in current._coach.estimates(
            replace(obs, quarter=2, remaining=70, yards_to_goal=76), "offense"
        )
    }


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_replayed_live_own_24_opportunity_asks_for_a_defensive_formation(
    side: str, mode: str
) -> None:
    charts = tuple(
        replace(
            team_chart(
                name,
                season=2002,
                offense=0,
                defense=0,
                plays={
                    Play.ONE: replace(yards(4), out_of_bounds=True),
                    Play.TWO: NormalizedCell(ResultKind.INCOMPLETE, provenance()),
                },
            ),
            special_teams=special_chart(name, kickoff=yards(70)).special_teams,
        )
        for name in ("Home", "Away")
    )
    original = SavedGame.new(
        *charts,
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        coach_policy=f"{mode}-v14",
        mode="regulation",
        clock=Clock(2, 90),
    )
    chooser = original.view().pending.chooser_side
    original.decide("toss:receive" if chooser == side else "toss:kick")
    original.kick("kickoff")
    original.decide("kick:touchback")
    original.snap("1", "A")
    original.snap("2", "A")
    view = original.view()
    assert view.state.possession == side and view.state.yards_to_goal == 76
    assert view.state.down == 3 and view.clock.remaining == 70
    loader = dict(zip(("2002/home", "2002/away"), charts, strict=True)).__getitem__
    current = loads_game(dumps_game(original), loader)
    before = json.loads(dumps_game(current))
    obs = observe_game(current.view(), side)
    assert field_goal_attempt_distance(obs) == 93
    assert "field_goal" not in {
        estimate.key for estimate in current._coach.estimates(obs, "offense")
    }
    human = "away" if side == "home" else "home"
    _, turn = current.coach_view(human)
    assert not turn.automatic and turn.human_role == "defense"
    assert {action.key for action in turn.actions.defense} == set("ABCDEF")
    after = json.loads(dumps_game(current))
    for key in ("commands", "rolls", "random_state", "state_digest"):
        assert after[key] == before[key]
