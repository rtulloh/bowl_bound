"""The baseline sees public situations and legal IDs, never hidden calls or dice."""

from dataclasses import asdict, replace
from random import Random

import pytest

from bowl_bound.coaching import BaselineCoach, CoachObservation, NoLegalAction, safe_choice


def observation(**changes) -> CoachObservation:
    return replace(
        CoachObservation(
            side="home",
            possession="home",
            down=1,
            distance=10,
            yards_to_goal=65,
            quarter=1,
            remaining=900,
            score_difference=0,
            play_number=0,
            offense=tuple(str(i) for i in range(1, 10)),
            defense=tuple("ABCDEF"),
            special=("punt", "field_goal"),
            game_actions=(),
            choices=(),
        ),
        **changes,
    )


def test_baseline_is_reproducible_without_touching_gameplay_randomness() -> None:
    dice = Random(7)
    before = dice.getstate()
    coach = BaselineCoach(31)
    calls = [coach.offense(observation(play_number=i)) for i in range(500)]
    assert calls == [BaselineCoach(31).offense(observation(play_number=i)) for i in range(500)]
    assert dice.getstate() == before
    assert set(calls) == set("123456789")
    assert max(calls.count(play) for play in set(calls)) < 100
    assert set(coach.defense(observation(play_number=i)) for i in range(200)) == set("ABCDEF")


def test_late_long_down_mixture_favors_passing_without_banning_runs() -> None:
    coach = BaselineCoach(31)
    early = [coach.offense(observation(play_number=i)) for i in range(2000)]
    late = [coach.offense(observation(down=3, distance=12, play_number=i)) for i in range(2000)]
    passes = set("6789")
    assert sum(p in passes for p in late) > sum(p in passes for p in early) + 200
    assert set(late) == set("123456789")


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"down": 4, "distance": 10, "yards_to_goal": 70}, "punt"),
        ({"down": 4, "distance": 10, "yards_to_goal": 25}, "field_goal"),
        ({"offense": (), "defense": (), "special": ("kickoff",)}, "kickoff"),
    ],
)
def test_special_team_preferences_are_selected_only_when_offered(changes, expected) -> None:
    coach = BaselineCoach(31)
    assert coach.offense(observation(**changes)) == expected
    if expected != "kickoff":
        assert coach.offense(observation(**(changes | {"special": ()}))) in "123456789"


@pytest.mark.parametrize(
    "choices,expected",
    [
        (("toss:kick", "toss:receive"), "toss:receive"),
        (("half:kick", "half:receive"), "half:receive"),
        (("ot:defense", "ot:offense"), "ot:offense"),
        (("conversion:two", "conversion:kick"), "conversion:kick"),
        (("conversion:two",), "conversion:two"),
        (("kick:return", "kick:touchback"), "kick:touchback"),
        (("kick:return", "kick:fair_catch"), "kick:fair_catch"),
        (("interception:decline", "interception:return"), "interception:return"),
        (("accept:0:previous", "decline"), "accept:0:previous"),
        (("clock:runoff", "clock:hurry"), "clock:runoff"),
    ],
)
def test_required_decisions_use_enabled_engine_ids_with_safe_fallback(choices, expected) -> None:
    assert BaselineCoach(31).decision(observation(choices=choices)) == expected


def test_invalid_policy_suggestion_falls_back_only_to_a_legal_option() -> None:
    assert safe_choice("not-legal", ("2", "4")).key == "2"
    assert safe_choice("not-legal", ("2", "4")).fallback
    assert not safe_choice("4", ("2", "4")).fallback
    with pytest.raises(NoLegalAction):
        safe_choice("not-legal", ())


def test_observation_contract_has_no_opponent_selection_charts_or_future_rolls() -> None:
    assert set(asdict(observation())) == {
        "side",
        "possession",
        "down",
        "distance",
        "yards_to_goal",
        "quarter",
        "remaining",
        "score_difference",
        "play_number",
        "offense",
        "defense",
        "special",
        "game_actions",
        "choices",
        "overtime",
        "hurried",
        "phase",
    }
    with pytest.raises(TypeError):
        CoachObservation(**(asdict(observation()) | {"human_call": "9"}))
