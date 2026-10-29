"""Chart-aware choices are legal, chart-sensitive, reproducible and concealed."""

from dataclasses import replace

import pytest

from bowl_bound.coaching import BaselineCoach
from bowl_bound.models import Play
from tests.synthetic_teams import team_chart, yards
from tests.test_coaching import observation


def test_chart_quality_changes_call_mix_without_banning_other_legal_calls() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach

    home = team_chart("Home", offense=-5, plays={Play.NINE: yards(20)})
    coach = ChartAwareCoach(31, home, team_chart("Away", defense=0))
    obs = observation(special=())
    calls = [coach.offense(replace(obs, play_number=i)) for i in range(1000)]
    assert calls.count("9") > 350
    assert set(calls) == set(obs.offense)
    assert calls == [coach.offense(replace(obs, play_number=i)) for i in range(1000)]
    assert not coach.analysis_fallback


def test_defensive_chart_is_consulted_not_the_hidden_offensive_call() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach

    away = team_chart("Away", defense=10)
    away = replace(
        away,
        defense=tuple(
            replace(r, cell=yards(-8)) if r.defense.value == "F" else r for r in away.defense
        ),
    )
    coach = ChartAwareCoach(31, team_chart("Home", offense=0), away)
    obs = observation(side="away", special=())
    calls = [coach.defense(replace(obs, play_number=i)) for i in range(600)]
    assert calls.count("F") > 300
    assert set(calls) == set(obs.defense)


def test_exact_baseline_decisions_and_late_kneel_remain_legal() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach

    coach = ChartAwareCoach(31, team_chart("Home"), team_chart("Away"))
    obs = observation(quarter=4, remaining=40, score_difference=7, game_actions=("kneel",))
    assert coach.offense(obs) == "kneel"
    for choices in [
        ("conversion:kick", "conversion:two"),
        ("clock:hurry", "clock:runoff"),
        ("ot:offense",),
    ]:
        current = replace(obs, choices=choices)
        assert coach.decision(current) == BaselineCoach(31).decision(current)


def test_failed_estimates_have_explicit_legal_baseline_fallback() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach
    from bowl_bound.models import Priority

    bad = replace(yards(4), priority=Priority.BRACKETED)
    home = team_chart("Home", plays={play: bad for play in Play})
    coach = ChartAwareCoach(31, home, team_chart("Away"))
    obs = observation(special=())
    assert coach.offense(obs) == BaselineCoach(31).offense(obs)
    assert coach.analysis_fallback
    assert all(not estimate.complete for estimate in coach.estimates(obs, "offense"))


def test_estimate_cache_is_bounded_and_play_number_does_not_change_model_values() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach

    coach = ChartAwareCoach(31, team_chart("Home"), team_chart("Away"))
    obs = observation(offense=("1",), defense=("A",), special=())
    first = coach.estimates(obs, "offense")
    assert coach.estimates(replace(obs, play_number=17), "offense") is first
    for index in range(140):
        coach.estimates(replace(obs, remaining=index), "offense")
    assert coach.cached_situations <= 128


def test_public_hurry_context_is_propagated_without_gameplay_seed() -> None:
    from bowl_bound.coaching_session import _observation
    from bowl_bound.regulation import RegulationView
    from bowl_bound.session import PlaySession

    home, away = team_chart("Home"), team_chart("Away")
    base = PlaySession.new(home, away, seed=123).view()
    view = RegulationView(**base.__dict__, hurried=True)
    assert _observation(view, "home").hurried
    assert not _observation(base, "home").hurried


def test_analysis_role_is_validated() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach

    coach = ChartAwareCoach(31, team_chart("Home"), team_chart("Away"))
    with pytest.raises(ValueError, match="role"):
        coach.estimates(observation(), "unknown")


def test_new_public_context_does_not_change_baseline_v1_selection_stream() -> None:
    from dataclasses import asdict
    from hashlib import sha256
    from json import dumps
    from random import Random

    for index in range(50):
        obs = observation(play_number=index)
        public = asdict(obs)
        public.pop("hurried", None)
        public.pop("phase", None)  # Added public context is not part of baseline-v1.
        assert set(public) == {
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
        }
        encoded = dumps(public, sort_keys=True, separators=(",", ":"))
        digest = sha256(f"baseline-v1:31:defense:{encoded}".encode()).digest()
        expected = Random(int.from_bytes(digest, "big")).choice(obs.defense)
        assert BaselineCoach(31).defense(obs) == expected
        assert BaselineCoach(31).defense(replace(obs, phase="two_point_try")) == expected


def test_chart_defender_uses_its_own_offered_late_timeout_not_offensive_hurry() -> None:
    from bowl_bound.chart_coaching import ChartAwareCoach

    coach = ChartAwareCoach(31, team_chart("Home"), team_chart("Away"))
    obs = observation(
        side="away",
        quarter=4,
        remaining=90,
        score_difference=-3,
        choices=("clock:runoff", "clock:timeout:away", "clock:hurry"),
    )
    assert coach.decision(obs) == "clock:timeout:away"
    assert coach.decision(replace(obs, choices=("clock:runoff", "clock:hurry"))) == "clock:runoff"
    assert coach.decision(replace(obs, overtime=True)) == "clock:runoff"
