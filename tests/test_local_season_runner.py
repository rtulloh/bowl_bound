"""Synthetic coverage for the local-only historical-season audit tooling."""

from collections import Counter
from dataclasses import replace
from types import SimpleNamespace

import pytest

from bowl_bound.cli import TeamEntry
from bowl_bound.coaching import BaselineCoach, CoachObservation
from bowl_bound.session import ScoreView
from bowl_bound.statistics import PlayStatistics, summarize
from scripts.run_local_season import (
    GameSpec,
    _new_audit_game,
    _offense_choice,
    _period_for_score,
    _play_one,
    _private_run_dir,
    _submit_offense_choice,
    _summary,
    build_schedule,
    run_games,
    run_local_season,
    validate_game,
)
from tests.synthetic_teams import metadata, team_chart, write_team


def teams(count: int, season: int = 2007) -> tuple[TeamEntry, ...]:
    return tuple(
        TeamEntry(f"{season}/synthetic-{number}", f"Synthetic {number}", season)
        for number in range(count)
    )


@pytest.mark.parametrize("count", [2, 3, 4, 6, 7])
def test_schedule_gives_each_team_twelve_games_and_balances_home_field(count: int) -> None:
    entries = teams(count)

    schedule = build_schedule(entries, games_per_team=12, master_seed=31415)

    assert len(schedule) == count * 12 // 2
    home = Counter(game.home_id for game in schedule)
    away = Counter(game.away_id for game in schedule)
    for entry in entries:
        assert home[entry.key] == 6
        assert away[entry.key] == 6
        assert home[entry.key] + away[entry.key] == 12
    assert len({game.seed for game in schedule}) == len(schedule)


def test_schedule_is_deterministic_and_independent_of_input_order() -> None:
    entries = teams(4)

    first = build_schedule(entries, games_per_team=12, master_seed=99)
    second = build_schedule(tuple(reversed(entries)), games_per_team=12, master_seed=99)

    assert first == second
    assert first != build_schedule(entries, games_per_team=12, master_seed=100)


@pytest.mark.parametrize(
    "entries, games_per_team",
    [
        ((), 12),
        (teams(1), 12),
        ((teams(2)[0], teams(2)[0]), 12),
        ((teams(2)[0], TeamEntry("2008/other", "Other", 2008)), 12),
        (teams(3), 1),
    ],
)
def test_schedule_rejects_invalid_team_groups(entries, games_per_team: int) -> None:
    with pytest.raises(ValueError):
        build_schedule(entries, games_per_team=games_per_team, master_seed=1)


def finished_view() -> SimpleNamespace:
    state = SimpleNamespace(
        possession="home",
        possession_name="Home",
        down=1,
        yards_to_go=10,
        yards_to_goal=65,
        spot="own 35",
        situation="1st and 10",
        attacking="right",
        ball_from_left=35,
        first_down_from_left=45,
    )
    report = SimpleNamespace(
        number=1,
        supported=True,
        pending=False,
        trace=(),
        statistics=PlayStatistics(),
        state_before=state,
        state_after=state,
    )
    event = SimpleNamespace(team="Home", points=3)
    return SimpleNamespace(
        home="Home",
        away="Away",
        finished=True,
        phase="final",
        pending=None,
        untimed_down=False,
        log=(report,),
        score=ScoreView(home=3, away=0),
        scoring=(event,),
        statistics=summarize((PlayStatistics(),)),
        timing_log=tuple(
            SimpleNamespace(play_number=1, quarter=quarter, before=900, seconds=900, after=0)
            for quarter in range(1, 5)
        ),
    )


def test_game_audit_accepts_complete_engine_log_with_reconciled_score() -> None:
    validate_game(finished_view(), ((3, 0), (0, 0), (0, 0), (0, 0)))


def test_game_audit_accepts_the_engine_halftime_kickoff_reset() -> None:
    view = finished_view()
    halftime_state = SimpleNamespace(
        **(
            vars(view.log[0].state_before)
            | {
                "possession": "away",
                "possession_name": "Away",
                "yards_to_goal": 70,
                "spot": "own 30",
                "ball_from_left": 30,
                "first_down_from_left": 40,
            }
        )
    )
    view.log = (
        view.log[0],
        SimpleNamespace(
            number=2,
            supported=True,
            pending=False,
            trace=(),
            statistics=PlayStatistics(),
            state_before=halftime_state,
            state_after=halftime_state,
            called_play="Kickoff",
        ),
    )
    view.statistics = summarize((PlayStatistics(), PlayStatistics()))

    validate_game(view, ((3, 0), (0, 0), (0, 0), (0, 0)))


def test_scoring_after_a_quarter_boundary_is_credited_to_the_new_quarter() -> None:
    before = SimpleNamespace(clock=SimpleNamespace(quarter=1), overtime=None)
    after = SimpleNamespace(clock=SimpleNamespace(quarter=2), overtime=None)

    assert _period_for_score(before, after) == 2


@pytest.mark.parametrize(
    "failure",
    [
        "unfinished",
        "pending",
        "unsupported",
        "score",
        "statistics",
        "timing",
        "rewind",
        "state",
        "period",
    ],
)
def test_game_audit_rejects_incomplete_or_inconsistent_game(failure: str) -> None:
    view = finished_view()
    if failure == "unfinished":
        view.finished = False
    elif failure == "pending":
        view.pending = SimpleNamespace(chooser="Home")
    elif failure == "unsupported":
        view.log = (SimpleNamespace(number=1, supported=False, pending=False, trace=()),)
    elif failure == "score":
        view.score = ScoreView(home=7, away=0)
    elif failure == "statistics":
        view.statistics = SimpleNamespace(home="mismatch")
    elif failure == "timing":
        view.timing_log = (SimpleNamespace(quarter=1, before=900, seconds=899, after=0),)
    elif failure == "rewind":
        view.timing_log = tuple(
            charge
            for quarter in range(1, 5)
            for charge in (
                SimpleNamespace(play_number=1, quarter=quarter, before=900, seconds=450, after=450),
                SimpleNamespace(play_number=1, quarter=quarter, before=900, seconds=450, after=450),
            )
        )
    elif failure == "state":
        disconnected = SimpleNamespace(
            possession="away",
            possession_name="Away",
            down=1,
            yards_to_go=10,
            yards_to_goal=65,
            spot="own 35",
            situation="1st and 10",
            attacking="right",
            ball_from_left=35,
            first_down_from_left=45,
        )
        view.log = (
            view.log[0],
            SimpleNamespace(
                number=2,
                supported=True,
                pending=False,
                trace=(),
                statistics=PlayStatistics(),
                state_before=disconnected,
                state_after=disconnected,
            ),
        )
        view.statistics = summarize(report.statistics for report in view.log)

    with pytest.raises(ValueError):
        periods = ((3, 0), (0, 0), (0, 0), (0, 0))
        if failure == "period":
            periods = ((2, 0), (0, 0), (0, 0), (0, 0))
        validate_game(view, periods)


def test_game_audit_rejects_trace_roll_that_does_not_match_its_faces() -> None:
    view = finished_view()
    report = SimpleNamespace(
        number=1,
        supported=True,
        pending=False,
        state_before=view.log[0].state_before,
        state_after=view.log[0].state_after,
        trace=(
            SimpleNamespace(
                team="Home",
                section="offense",
                roll={"faces": [1, 2, 3], "total": 7},
                cell="4",
            ),
        ),
    )
    view.log = (report,)

    with pytest.raises(ValueError, match="trace"):
        validate_game(view, ((3, 0), (0, 0), (0, 0), (0, 0)))


def test_batch_runner_keeps_later_games_after_one_failure() -> None:
    entries = teams(2)
    schedule = build_schedule(entries, games_per_team=2, master_seed=10)
    attempted = []

    def play(spec):
        attempted.append(spec.seed)
        if len(attempted) == 1:
            raise RuntimeError("synthetic failure")
        return {"status": "passed", "seed": spec.seed}

    results = run_games(schedule, play)

    assert attempted == [spec.seed for spec in schedule]
    assert [result["status"] for result in results] == ["failed", "passed"]
    assert results[0]["error"] == "RuntimeError"


def test_simulator_uses_engine_and_records_calls_and_full_trace() -> None:
    away_id, home_id = "2007/synthetic-away", "2007/synthetic-home"
    spec = GameSpec(1, 2007, away_id, home_id, 31415)
    charts = {
        away_id: (team_chart("Synthetic Away", season=2007), metadata()),
        home_id: (team_chart("Synthetic Home", season=2007), metadata()),
    }

    result = _play_one(spec, charts)

    assert result["status"] == "passed"
    assert result["final"]["finished"] is True
    assert result["final"]["report_count"] == len(result["engine_log"])
    assert any(report["trace"] for report in result["engine_log"])
    assert result["coaching_calls"]
    assert sum(row["home"] for row in result["period_scores"]) == result["final"]["home_score"]
    assert sum(row["away"] for row in result["period_scores"]) == result["final"]["away_score"]
    assert len(result["final"]["timing_log"]) > 0
    assert result["final"]["statistics"]
    assert not any(call["fallback"] for call in result["coaching_calls"])
    assert {call["team_id"] for call in result["coaching_calls"]} == {away_id, home_id}
    assert result["configuration"] == {
        "engine_coach_policy": "baseline",
        "simulation_coach_policy": "baseline",
        "advanced_ii": False,
        "defense_chart_markers": {"home": [], "away": []},
    }


def test_audit_game_preserves_w_marker_without_enabling_wild_card() -> None:
    away_id, home_id = "2007/synthetic-away", "2007/synthetic-home"
    spec = GameSpec(1, 2007, away_id, home_id, 31415)
    teams = {
        away_id: (
            team_chart("Synthetic Away", season=2007),
            replace(metadata(), defense_chart_markers=("W",)),
        ),
        home_id: (team_chart("Synthetic Home", season=2007), metadata()),
    }

    game = _new_audit_game(spec, teams)
    session = game._engine._session

    assert not any(action.key.startswith("WC") for action in session.view().actions.defense)


def fourth_down_observation() -> CoachObservation:
    return CoachObservation(
        side="home",
        possession="home",
        down=4,
        distance=6,
        yards_to_goal=54,
        quarter=1,
        remaining=500,
        score_difference=0,
        play_number=20,
        offense=tuple(str(number) for number in range(1, 10)),
        defense=(),
        special=("punt", "field_goal"),
        game_actions=(),
        choices=(),
    )


def test_fourth_down_policy_kick_is_preserved_as_a_legal_special_call() -> None:
    observation = fourth_down_observation()

    choice = _offense_choice(observation, BaselineCoach(101))

    assert choice.key == "punt"
    assert choice.fallback is False


def test_offense_dispatch_uses_the_engine_kick_path_for_a_punt() -> None:
    class FakeGame:
        def __init__(self) -> None:
            self.executed = None

        def coach_execute(self, side, operation, key):
            self.executed = (side, operation, key)
            return "report", "view", "turn"

        def coach_step(self, side, key):
            raise AssertionError("a special teams call must not be submitted as a snap")

    game = FakeGame()
    observation = fourth_down_observation()
    choice = _offense_choice(observation, BaselineCoach(101))

    _submit_offense_choice(game, "home", observation, choice)

    assert game.executed == ("home", "kick", "punt")


def test_summary_groups_coaching_calls_and_standings_by_team_id() -> None:
    result = {
        "status": "passed",
        "teams": {"home": "2007/home", "away": "2007/away"},
        "final": {"home_score": 7, "away_score": 3},
        "coaching_calls": [
            {
                "team_id": "2007/home",
                "role": "offense",
                "choice": "1",
                "fallback": True,
                "observation": {"down": 1, "distance": 10},
            },
            {
                "team_id": "2007/away",
                "role": "defense",
                "choice": "A",
                "fallback": False,
                "observation": {"down": 1, "distance": 10},
            },
        ],
    }

    summary = _summary([result])

    assert summary["standings"]["2007/home"]["wins"] == 1
    assert summary["standings"]["2007/away"]["losses"] == 1
    assert summary["fallbacks"] == 1
    assert (
        next(row for row in summary["coaching_calls"] if row["team_id"] == "2007/home")["fallbacks"]
        == 1
    )
    assert {row["team_id"] for row in summary["coaching_calls"]} == {
        "2007/home",
        "2007/away",
    }


def test_local_runner_writes_seeded_synthetic_games_under_private_data(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seasons = tmp_path / "seasons"
    write_team(seasons, team_chart("Synthetic Home", season=2007))
    write_team(seasons, team_chart("Synthetic Away", season=2007))
    monkeypatch.chdir(tmp_path)

    def simulated(spec, _charts):
        return {
            "status": "passed",
            "spec": {
                "season": spec.season,
                "number": spec.number,
                "away_id": spec.away_id,
                "home_id": spec.home_id,
                "seed": spec.seed,
            },
            "teams": {"home": spec.home_id, "away": spec.away_id},
            "final": {"home_score": 7, "away_score": 3},
            "coaching_calls": [],
            "engine_log": [],
        }

    monkeypatch.setattr("scripts.run_local_season._play_one", simulated)

    run_dir, summary = run_local_season(
        seasons,
        games_per_team=2,
        master_seed=42,
        output_root=tmp_path / "private-data" / "audits",
    )

    assert run_dir.is_relative_to(tmp_path / "private-data")
    assert summary["games"] == summary["passed"] == 2
    assert len(list(run_dir.glob("game-*.json"))) == 2
    assert (run_dir / "summary.json").is_file()


def test_output_path_outside_private_data_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="private-data"):
        _private_run_dir(tmp_path / "reports", master_seed=1)


def test_overtime_reset_requires_matching_observed_series_evidence() -> None:
    from scripts.run_local_season import OvertimeSeriesStart, _state_facts

    view = finished_view()
    original = view.log[0]
    state = SimpleNamespace(
        **(
            vars(original.state_before)
            | {
                "possession": "away",
                "possession_name": "Away",
                "yards_to_goal": 25,
                "spot": "opp 25",
                "ball_from_left": 75,
                "first_down_from_left": 85,
            }
        )
    )
    view.log += (
        SimpleNamespace(
            **(
                vars(original)
                | {
                    "number": 2,
                    "state_before": state,
                    "state_after": state,
                    "called_play": "Counter",
                }
            )
        ),
    )
    start = OvertimeSeriesStart(2, 1, 1, "away", "away", False, _state_facts(state))
    periods = ((0, 0), (0, 0), (0, 0), (0, 0), (3, 0))
    with pytest.raises(ValueError, match="disconnected"):
        validate_game(view, periods)
    validate_game(view, periods, overtime_starts=(start,))
    with pytest.raises(ValueError, match="overtime"):
        validate_game(
            view,
            periods,
            overtime_starts=(replace(start, state=_state_facts(original.state_before)),),
        )
    with pytest.raises(ValueError, match="overtime"):
        validate_game(view, periods, overtime_starts=(replace(start, report_number=1),))


def test_overtime_series_evidence_requires_engine_order() -> None:
    from scripts.run_local_season import OvertimeSeriesStart, _state_facts

    view = finished_view()
    state = view.log[0].state_before
    start = OvertimeSeriesStart(2, 2, 1, "home", "home", False, _state_facts(state))
    with pytest.raises(ValueError, match="overtime"):
        validate_game(view, ((3, 0), (0, 0), (0, 0), (0, 0), (0, 0)), overtime_starts=(start,))


def test_simulator_reconciles_a_real_engine_overtime_reset() -> None:
    from tests.test_special_teams import special_chart, yards

    teams = {
        f"2007/synthetic-{side}": (
            replace(
                team_chart("Synthetic " + side.title(), season=2007, offense=0, defense=0),
                special_teams=special_chart(
                    side,
                    kickoff=yards(40),
                    kickoff_return=yards(10),
                    punt=yards(40),
                    punt_return=yards(0),
                    field_goal=yards(40 if side == "home" else 0),
                ).special_teams,
            ),
            metadata(),
        )
        for side in ("home", "away")
    }

    result = _play_one(GameSpec(1, 2007, "2007/synthetic-away", "2007/synthetic-home", 7), teams)

    assert result["status"] == "passed", result["error"]
    assert result["final"]["finished"]
    assert (result["final"]["home_score"], result["final"]["away_score"]) == (3, 0)
    starts = result["overtime_series_starts"]
    assert [(start["round_number"], start["series_number"]) for start in starts] == [(1, 1), (1, 2)]
    assert {start["possession"] for start in starts} == {"home", "away"}
    assert all(start["state"][4] == 25 for start in starts)
    assert len(result["period_scores"]) == 5


@pytest.mark.parametrize(
    "problem", ["reverse_reports", "duplicate", "untied_regulation", "no_regulation_end"]
)
def test_overtime_boundary_evidence_cannot_hide_a_disconnected_report(problem: str) -> None:
    from scripts.run_local_season import OvertimeSeriesStart, _state_facts

    view = finished_view()
    original = view.log[0]
    states = [
        SimpleNamespace(
            **(
                vars(original.state_before)
                | {
                    "possession": side,
                    "possession_name": side.title(),
                    "yards_to_goal": 25,
                    "spot": "opp 25",
                    "ball_from_left": 75,
                    "first_down_from_left": 85,
                }
            )
        )
        for side in ("home", "away")
    ]
    view.log += tuple(
        SimpleNamespace(
            **(
                vars(original)
                | {
                    "number": number,
                    "state_before": state,
                    "state_after": state,
                }
            )
        )
        for number, state in enumerate(states, 2)
    )
    starts = (
        OvertimeSeriesStart(2, 1, 1, "home", "home", False, _state_facts(states[0])),
        OvertimeSeriesStart(3, 1, 2, "home", "away", False, _state_facts(states[1])),
    )
    periods = ((0, 0), (0, 0), (0, 0), (0, 0), (3, 0))
    if problem == "reverse_reports":
        starts = (
            replace(starts[0], report_number=3),
            replace(starts[1], report_number=2),
        )
        # Keep each forged report's possession matching its claimed boundary.
        view.log = (
            original,
            replace_namespace(view.log[1], state_before=states[1], state_after=states[1]),
            replace_namespace(view.log[2], state_before=states[0], state_after=states[0]),
        )
    elif problem == "duplicate":
        starts = (starts[0], starts[0])
    elif problem == "untied_regulation":
        periods = ((3, 0), (0, 0), (0, 0), (0, 0), (0, 0))
    else:
        view.timing_log = tuple(charge for charge in view.timing_log if charge.quarter != 4)

    with pytest.raises(ValueError, match="overtime"):
        validate_game(view, periods, overtime_starts=starts)


def replace_namespace(value: SimpleNamespace, **changes: object) -> SimpleNamespace:
    return SimpleNamespace(**(vars(value) | changes))
