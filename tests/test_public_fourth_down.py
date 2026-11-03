"""AI-027: one public fourth-down policy, independent of kick charts and dice."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import CoachObservation, public_fourth_down_call
from bowl_bound.coaching_session import plan_turn
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import NormalizedCell, ResultKind, TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import team_chart, yards
from tests.test_coaching import observation
from tests.test_models import provenance
from tests.test_special_teams import special_chart


@pytest.mark.parametrize("tier,aggression", [("easy", 0.3), ("medium", 0.5), ("hard", 0.7)])
@pytest.mark.parametrize(
    "attempt,distance,conservative,aggressive",
    [
        (34, 1, "field_goal", "field_goal"),
        (35, 1, "field_goal", "field_goal"),
        (36, 1, "field_goal", "go"),
        (47, 1, "field_goal", "go"),
        (48, 1, "field_goal", "field_goal"),
        (50, 1, "field_goal", "field_goal"),
        (51, 1, "punt", "field_goal"),
        (55, 1, "punt", "field_goal"),
        (56, 1, "punt", "go"),
        (35, 8, "field_goal", "field_goal"),
        (36, 8, "field_goal", "field_goal"),
        (47, 8, "field_goal", "field_goal"),
        (48, 8, "field_goal", "field_goal"),
        (50, 8, "field_goal", "field_goal"),
        (51, 8, "punt", "field_goal"),
        (55, 8, "punt", "field_goal"),
        (56, 8, "punt", "punt"),
    ],
)
def test_shared_policy_and_cpu_match_every_approved_band(
    tier: str,
    aggression: float,
    attempt: int,
    distance: int,
    conservative: str,
    aggressive: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    obs = observation(down=4, yards_to_goal=attempt - 17, distance=distance, offense=("1",))
    expected = conservative if tier == "easy" else aggressive
    computer = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), tier, version=10)

    def reject_analysis(*args: object, **kwargs: object) -> None:
        raise AssertionError("fourth-down kick/go policy must not evaluate charts")

    monkeypatch.setattr(computer, "estimates", reject_analysis)
    read_chart = TeamChart.__getattribute__

    def reject_kick_chart(chart: TeamChart, name: str) -> object:
        if name in {"special_teams", "pat_outcomes"}:
            raise AssertionError("fourth-down kick/go policy must not inspect kick charts")
        return read_chart(chart, name)

    monkeypatch.setattr(TeamChart, "__getattribute__", reject_kick_chart)
    assert public_fourth_down_call(obs, aggression=aggression) == expected
    assert computer.offense(obs) == ("1" if expected == "go" else expected)


@pytest.mark.parametrize(
    "deficit,attempt,remaining,expected",
    [
        (1, 55, 180, "field_goal"),
        (3, 55, 180, "field_goal"),
        (4, 35, 180, "go"),
        (1, 56, 180, "go"),
        (4, 35, 181, "field_goal"),
    ],
)
def test_shared_late_trailing_boundary(
    deficit: int, attempt: int, remaining: int, expected: str
) -> None:
    obs = observation(
        down=4,
        yards_to_goal=attempt - 17,
        quarter=4,
        remaining=remaining,
        score_difference=-deficit,
    )
    assert public_fourth_down_call(obs, aggression=0.5) == expected


@pytest.mark.parametrize("changes", [{"down": 3}, {"overtime": True}, {"phase": "two_point_try"}])
def test_shared_policy_excludes_other_phases(changes: dict[str, object]) -> None:
    assert public_fourth_down_call(replace(observation(down=4), **changes), aggression=0.5) is None


@pytest.mark.parametrize(
    "special,spot,expected",
    [
        ((), 10, "go"),
        (("field_goal",), 65, "go"),
        (("punt",), 10, "punt"),
        (("field_goal",), 10, "field_goal"),
    ],
)
def test_shared_policy_respects_offered_kicks(
    special: tuple[str, ...], spot: int, expected: str
) -> None:
    assert (
        public_fourth_down_call(
            observation(down=4, special=special, yards_to_goal=spot), aggression=0.5
        )
        == expected
    )


def test_current_cpu_delegates_to_shared_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    computer = DifficultyCoach(31, team_chart("Home"), team_chart("Away"), "medium", version=10)
    obs = observation(down=4, yards_to_goal=10)
    seen = []

    def shared(public: CoachObservation, *, aggression: float, chase_seconds: int) -> str:
        seen.append((public, aggression, chase_seconds))
        return "punt"

    monkeypatch.setattr("bowl_bound.difficulty.public_fourth_down_call", shared)
    assert computer.offense(obs) == "punt"
    assert seen == [(obs, 0.5, 180)]


@pytest.mark.parametrize("strong", [True, False])
@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_saved_public_choice_is_stable_while_actual_kick_uses_its_chart(
    strong: bool, tier: str
) -> None:
    cell = yards(100) if strong else NormalizedCell(ResultKind.NO_GOOD_FIELD_GOAL, provenance())
    home = replace(
        team_chart("Home", offense=0),
        special_teams=special_chart("Home", field_goal=cell).special_teams,
    )
    away = team_chart("Away", defense=0)
    saved = SavedGame.new(
        home,
        away,
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        coach_seed=31,
        difficulty=tier,
        start_yards_to_goal=31,
    )
    for _ in range(3):
        saved.snap("1", "A")
    restored = loads_game(dumps_game(saved), lambda key: home if key.endswith("home") else away)
    assert plan_turn(saved.view(), "away", saved._coach).computer_choice.key == "field_goal"
    assert restored.coach_view("away") == saved.coach_view("away")
    report, _, _, selected = saved._coach_step_with_choice("away")
    assert selected.key == "field_goal"
    assert restored._coach_step_with_choice("away")[0] == report
    assert report.outcome == ("field_goal_good" if strong else "field_goal_missed")
