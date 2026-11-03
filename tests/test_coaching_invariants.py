"""AI-010: exact, synthetic coaching contracts independent of football randomness."""

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import replace
from math import exp
from pathlib import Path
from typing import Any

import pytest

from bowl_bound.cli import TerminalGame, main
from bowl_bound.coaching_evaluation import ActionEstimate
from bowl_bound.coaching_session import plan_turn
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    TeamChart,
)
from bowl_bound.save_game import GameRevisionConflict, SavedGame, dumps_game, loads_game
from bowl_bound.session import InvalidDecisionError
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, write_team, yards
from tests.test_cli import saved_facts
from tests.test_coaching import observation
from tests.test_models import provenance
from tests.test_save_game import charts, opening


class RecordedRandom:
    """Capture exact categorical probabilities instead of sampling frequencies."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], tuple[float, ...]]] = []

    def choices(self, population: Sequence[str], weights: Sequence[float], *, k: int) -> list[str]:
        assert k == 1
        self.calls.append((tuple(population), tuple(weights)))
        return [population[0]]


def coach(mode: str = "hard", **kwargs: Any) -> DifficultyCoach:
    return DifficultyCoach(31, team_chart("Home"), team_chart("Away"), mode, **kwargs)


def game(
    *, tier: str = "hard", teams: tuple[TeamChart, TeamChart] | None = None, **kwargs: Any
) -> SavedGame:
    return SavedGame.new(
        *(teams or charts()),
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        difficulty=tier,
        **kwargs,
    )


def history(computer: DifficultyCoach) -> object:
    return deepcopy((computer._counts, computer._recent, computer._situational_recent))


@pytest.fixture
def fast_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use complete equal synthetic estimates; test engine sampling separately."""
    monkeypatch.setattr(
        DifficultyCoach,
        "_evaluate",
        lambda self, obs, key, role, weights: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )


def test_hard_previews_and_rejected_steps_preserve_all_history(fast_analysis: None) -> None:
    saved = game()
    saved.snap("1", "A")
    before = saved_facts(saved), history(saved._coach), deepcopy(saved._charts)
    for _ in range(12):
        saved.coach_view("home")
        saved.coach_view("away")
    with pytest.raises(InvalidDecisionError):
        saved.coach_step("home", "F")
    with pytest.raises(GameRevisionConflict):
        saved.coach_step("home", "1", expected_revision=-1)
    assert (saved_facts(saved), history(saved._coach), saved._charts) == before


@pytest.mark.parametrize("human", ["home", "away"])
def test_real_hard_engine_analysis_preserves_live_game_sources(human: str) -> None:
    saved = game()
    before = saved_facts(saved), history(saved._coach), deepcopy(saved._charts)
    planned = plan_turn(saved.view(), human, saved._coach)
    assert planned.computer_choice is not None
    assert not planned.computer_choice.fallback
    assert (saved_facts(saved), history(saved._coach), saved._charts) == before


def test_hard_history_replays_over_one_hundred_real_snaps_and_possessions(
    fast_analysis: None,
) -> None:
    incomplete = NormalizedCell(ResultKind.INCOMPLETE, provenance())
    teams = tuple(
        replace(t, offense=team_chart(t.name, plays={Play.SIX: incomplete}).offense)
        for t in charts()
    )
    saved = game(teams=teams, mode="regulation")
    opening(saved)
    possessions = set()
    for _ in range(220):
        view = saved.view()
        while view.pending or not view.actions.offense:
            if view.pending:
                choices = [c.id for c in view.pending.choices if c.enabled]
                selected = next(
                    (
                        c
                        for c in ("clock:standard", "clock:runoff", "kick:touchback")
                        if c in choices
                    ),
                    choices[0],
                )
                saved.decide(selected)
            else:
                saved.kick("kickoff")
            view = saved.view()
        possessions.add(view.state.possession)
        saved.snap("6", "A")
    assert len(possessions) == 2
    assert (
        sum(
            sum(c.values()) for (side, role), c in saved._coach._counts.items() if role == "offense"
        )
        == 220
    )
    for key, counts in saved._coach._counts.items():
        assert len(saved._coach._recent[key]) == min(96, sum(counts.values()))
        assert len(saved._coach._situational_recent[key]) == min(96, sum(counts.values()))
    restored = loads_game(
        dumps_game(saved), lambda key: teams[0] if key.endswith("home") else teams[1]
    )
    assert history(restored._coach) == history(saved._coach)
    assert saved_facts(restored) == saved_facts(saved)
    assert restored.coach_view("home") == saved.coach_view("home")
    assert restored.coach_view("away") == saved.coach_view("away")


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
@pytest.mark.parametrize("human,calls", [("home", ("1", "9")), ("away", ("A", "F"))])
def test_all_tiers_choose_before_the_hidden_human_input(
    tier: str, human: str, calls: tuple[str, str], fast_analysis: None
) -> None:
    results = [game(tier=tier)._coach_step_with_choice(human, call) for call in calls]
    assert results[0][3] == results[1][3]
    assert all(result[0].supported for result in results)


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
@pytest.mark.parametrize("pending", ["penalty", "conversion", "overtime"])
def test_each_tier_resumes_pending_engine_procedures(
    tier: str, pending: str, fast_analysis: None
) -> None:
    teams = charts(gain=100 if pending == "conversion" else 0)
    options = {}
    if pending == "penalty":
        penalty = NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
        )
        teams = tuple(
            replace(
                t,
                offense=tuple(
                    replace(r, cell=penalty if r.roll == 10 else yards(8)) for r in t.offense
                ),
            )
            for t in teams
        )
        options["dice"] = ScriptedDice(
            [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]
        )
    elif pending == "overtime":
        options.update(mode="regulation", clock=Clock(4, 1))
    saved = game(tier=tier, teams=teams, **options)
    if pending == "overtime":
        opening(saved)
    saved.snap("1", "A")
    if pending == "overtime":
        saved.decide("clock:runoff")
    assert saved.view().pending is not None
    expected = {"penalty": "decline", "conversion": "conversion:two", "overtime": "ot:offense"}[
        pending
    ]
    assert expected in [c.id for c in saved.view().pending.choices if c.enabled]
    restored = loads_game(
        dumps_game(saved), lambda key: teams[0] if key.endswith("home") else teams[1]
    )
    assert history(restored._coach) == history(saved._coach)
    for human in ("home", "away"):
        assert restored.coach_view(human) == saved.coach_view(human)
    assert restored.decide(expected) == saved.decide(expected)
    assert restored.view() == saved.view()
    assert saved_facts(restored) == saved_facts(saved)


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
@pytest.mark.parametrize(
    "method,changes",
    [
        ("offense", {}),
        ("offense", {"offense": (), "special": ("kickoff",)}),
        ("offense", {"down": 4, "yards_to_goal": 10}),
        ("offense", {"down": 4, "yards_to_goal": 70}),
        (
            "offense",
            {
                "game_actions": ("kneel",),
                "can_kneel_out_game": True,
                "quarter": 4,
                "remaining": 10,
                "score_difference": 7,
            },
        ),
        (
            "offense",
            {"quarter": 4, "remaining": 10, "score_difference": -7, "game_actions": ("hail_mary",)},
        ),
        ("offense", {"quarter": 4, "remaining": 10, "score_difference": -2, "yards_to_goal": 20}),
        ("offense", {"phase": "two_point_try", "yards_to_goal": 2, "distance": 2}),
        ("defense", {"possession": "away"}),
        ("decision", {"choices": ("conversion:kick", "conversion:two")}),
        ("decision", {"choices": ("clock:standard", "clock:runoff", "clock:timeout:home")}),
        ("decision", {"choices": ("kick:touchback", "kick:return")}),
        ("decision", {"choices": ("interception:return", "interception:decline")}),
        ("decision", {"choices": ("decline", "accept:0:previous")}),
        ("decision", {"choices": ("ot:offense", "ot:defense")}),
    ],
)
def test_every_coaching_branch_preserves_game_dice_tape_charts_and_history(
    tier: str, method: str, changes: dict[str, Any], fast_analysis: None
) -> None:
    saved = game(tier=tier)
    before = saved_facts(saved), deepcopy(saved._charts), history(saved._coach)
    obs = observation(**changes)
    result = getattr(saved._coach, method)(obs)
    legal = (
        obs.choices
        if method == "decision"
        else obs.defense
        if method == "defense"
        else obs.offense + obs.special + obs.game_actions
    )
    assert result in legal
    assert (saved_facts(saved), saved._charts, history(saved._coach)) == before


def test_estimate_cache_is_lru_and_retains_hit_identity(fast_analysis: None) -> None:
    computer = coach()
    computer.behavior = replace(computer.behavior, cache_entries=2)
    first, second, third = (observation(distance=i, special=()) for i in (7, 8, 9))
    first_values = computer.estimates(first, "offense")
    second_values = computer.estimates(second, "offense")
    assert computer.estimates(replace(first, play_number=500), "offense") is first_values
    computer.estimates(third, "offense")
    assert computer.estimates(first, "offense") is first_values
    assert computer.estimates(second, "offense") is not second_values
    assert len(computer._cache) == 2


@pytest.mark.parametrize(
    "role,side,play,defense", [("offense", "home", "1", "F"), ("defense", "away", "9", "A")]
)
def test_opponent_counts_are_part_of_cache_identity(
    role: str, side: str, play: str, defense: str, fast_analysis: None
) -> None:
    computer = coach()
    obs = observation(special=())
    first = computer.estimates(obs, role)
    computer.commit_call(side, play, defense, observation=obs)
    second = computer.estimates(obs, role)
    assert second is not first
    assert computer.estimates(obs, role) is second


@pytest.mark.parametrize("human", ["home", "away"])
def test_hard_analysis_fallback_reaches_private_plan_and_resets(
    human: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = game()
    monkeypatch.setattr(
        DifficultyCoach,
        "_evaluate",
        lambda self, obs, key, role, weights: ActionEstimate(key, 32, 1, None, None, None),
    )
    failed = plan_turn(saved.view(), human, saved._coach)
    assert failed.computer_choice is not None and failed.computer_choice.fallback
    saved._coach._cache.clear()
    monkeypatch.setattr(
        DifficultyCoach,
        "_evaluate",
        lambda self, obs, key, role, weights: ActionEstimate(key, 32, 0, 0.0, 0.0, 0.0),
    )
    recovered = plan_turn(saved.view(), human, saved._coach)
    assert recovered.computer_choice is not None and not recovered.computer_choice.fallback


@pytest.mark.parametrize("role", ["offense", "defense"])
def test_exact_exploration_exploitation_mixture(role: str, monkeypatch: pytest.MonkeyPatch) -> None:
    computer = coach()
    rng = RecordedRandom()
    monkeypatch.setattr(computer, "_random", lambda obs, role: rng)
    monkeypatch.setattr(computer, "_preference_weight", lambda obs, role, key, weight: weight)
    values = tuple(
        ActionEstimate(key, 32, 0, value, 0.0, 0.0)
        for key, value in [("1", 0.0), ("2", 0.6), ("3", 1.2)]
    )
    monkeypatch.setattr(computer, "estimates", lambda obs, role: values)
    computer._select(observation(), role, "1")
    keys, weights = rng.calls[-1]
    exploitation = [exp(-2), exp(-1), 1]
    expected = [0.15 / 3 + 0.85 * weight / sum(exploitation) for weight in exploitation]
    assert keys == ("1", "2", "3")
    assert weights == pytest.approx(expected)
    assert sum(weights) == pytest.approx(1)


@pytest.mark.parametrize("symbolic", [False, True])
def test_medium_exact_group_tilt_and_symbolic_fallback(
    symbolic: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_cell = NormalizedCell(ResultKind.BREAKAWAY, provenance()) if symbolic else yards(5)
    passing_cell = NormalizedCell(ResultKind.BREAKAWAY, provenance()) if symbolic else yards(1)
    home = team_chart(
        "Home",
        plays={
            p: run_cell if int(p.value) <= 5 else passing_cell for p in Play if 1 <= p.value <= 9
        },
    )
    computer = DifficultyCoach(31, home, team_chart("Away"), "medium")
    rng = RecordedRandom()
    monkeypatch.setattr(computer, "_random", lambda obs, role: rng)
    computer.offense(observation(special=()))
    keys, weights = rng.calls[-1]
    run_probability = 0.55 if symbolic else 0.75
    assert computer._strength["home"] == pytest.approx(0 if symbolic else 0.2)
    assert keys == tuple("123456789")
    assert weights == pytest.approx([run_probability / 5] * 5 + [(1 - run_probability) / 4] * 4)


@pytest.mark.parametrize("resumed", [False, True])
def test_cli_keeps_one_coach_for_all_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resumed: bool
) -> None:
    teams = charts()
    for chart in teams:
        write_team(tmp_path, chart)
    saved_path = tmp_path / "synthetic-save.json"
    saved_path.write_text(dumps_game(game(teams=teams, tier="medium")))
    created = []
    original = DifficultyCoach.__init__

    def record(self, *args: Any, **kwargs: Any) -> None:
        original(self, *args, **kwargs)
        created.append(self)

    monkeypatch.setattr(DifficultyCoach, "__init__", record)

    def run(terminal: TerminalGame) -> int:
        identity = terminal.game._coach
        for _ in range(8):
            terminal.public_view()
            terminal.command("status")
            terminal.command("help")
            assert terminal.game._coach is identity
        return 0

    monkeypatch.setattr(TerminalGame, "run", run)
    args = ["--seasons", str(tmp_path)]
    args += (
        ["--load", str(saved_path)] if resumed else ["--home", "2002/home", "--away", "2002/away"]
    )
    assert main(args) == 0
    assert len(created) == 1
