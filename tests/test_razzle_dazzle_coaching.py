"""AI-033: choose RZDZ outcomes, not the first legal chart-cell identifier."""

from dataclasses import replace
from itertools import product
from pathlib import Path

import pytest

from bowl_bound.coaching import CoachObservation
from bowl_bound.coaching_evaluation import (
    RazzleChoiceEstimate,
    _hard_potential,
    evaluate_razzle_decisions,
    sample_razzle_decisions,
)
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.coaching_session import observe_game, observe_policy
from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.difficulty import DifficultyCoach
from bowl_bound.game_state import FieldState, Possession, apply_gain
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    Priority,
    ResultKind,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PlaySession, SessionPhase
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_defensive_razzle_prefers_a_known_loss_to_a_positive_breakaway(mode: str) -> None:
    home = team_chart(
        "Cedar Test",
        offense=8,
        plays={
            Play.ONE: NormalizedCell(ResultKind.BREAKAWAY, provenance()),
            Play.TWO: yards(-4),
        },
    )
    away = team_chart("Harbor Test", defense=0)
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=NormalizedCell(ResultKind.NO_CHANGE, provenance()))
            for row in away.defense
        ),
    )
    # Only the two observed comparison rolls exist. An evaluator that consumes
    # the live future stream will exhaust this source rather than invent dice.
    source = ScriptedDice([OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5)])
    session = PlaySession.new(home, away, seed=1)
    session.snap("RZDZ", "A", dice=source)
    before = session.view()
    assert before.pending.chooser_side == "away"
    coach = DifficultyCoach(11, home, away, mode, version=CURRENT_DIFFICULTY_VERSION)

    choice = coach.decision(observe_game(before, "away"))

    assert choice in {"razzle:2:15", "razzle:2:18"}
    assert session.view() == before
    assert source._position == 2


def test_pending_razzle_exposes_only_its_observed_rolls_and_declared_formation() -> None:
    home, away = team_chart("Cedar Test"), team_chart("Harbor Test")
    source = ScriptedDice([OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5)])
    session = PlaySession.new(home, away, seed=1)
    session.snap("RZDZ", "C", dice=source)
    context = session.view().pending.razzle_context
    assert context.defense == "C"
    assert context.rolls == (OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5))
    assert not context.free_wildcard
    assert observe_game(session.view(), "away").razzle_context == context
    assert source._position == 2


def charts(
    *,
    candidate: NormalizedCell | None = None,
    supplement: int = 8,
    recovery: range = range(10, 27),
) -> tuple[TeamChart, TeamChart]:
    home = team_chart(
        "Cedar Test",
        offense=8,
        plays={
            Play.ONE: NormalizedCell(ResultKind.BREAKAWAY, provenance()),
            **({Play.TWO: candidate} if candidate is not None else {}),
        },
    )
    home = replace(
        home,
        recovery_range=recovery,
        supplemental=tuple(replace(row, cell=yards(supplement)) for row in home.supplemental),
    )
    away = team_chart("Harbor Test", defense=0)
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=NormalizedCell(ResultKind.NO_CHANGE, provenance()))
            for row in away.defense
        ),
        special_teams=tuple(replace(row, cell=yards(0)) for row in away.special_teams),
    )
    return home, away


def observation(
    home: TeamChart,
    away: TeamChart,
    side: str = "away",
    field: FieldState | None = None,
) -> CoachObservation:
    field = field or FieldState(Possession.HOME, 65, 1, 10)
    session = PlaySession.for_analysis(home, away, field)
    rolls = [OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5)]
    if side == field.possession.value:
        rolls[1] = rolls[0]  # offense owns ties, one legal total
    session.snap("RZDZ", "A", dice=ScriptedDice(rolls))
    view = session.view()
    assert view.pending.chooser_side == side
    return observe_game(view, side)


@pytest.mark.parametrize(
    "kind,supplement",
    [
        (ResultKind.INCOMPLETE, 8),
        (ResultKind.QUARTERBACK_TRAPPED, -8),
        (ResultKind.QUARTERBACK_RUN, -5),
        (ResultKind.INTERCEPTION, 8),
    ],
)
@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_defense_uses_engine_black_qt_qr_and_turnover_outcomes(
    kind: ResultKind, supplement: int, mode: str
) -> None:
    candidate = NormalizedCell(
        kind, provenance(), yards=0 if kind is ResultKind.INTERCEPTION else None
    )
    home, away = charts(candidate=candidate)
    if kind in {ResultKind.QUARTERBACK_TRAPPED, ResultKind.QUARTERBACK_RUN}:
        column = SupplementalColumn(kind.value)
        home = replace(
            home,
            supplemental=tuple(
                replace(row, cell=yards(supplement)) if row.column is column else row
                for row in home.supplemental
            ),
        )
    obs = observation(home, away)
    coach = DifficultyCoach(1, home, away, mode, version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs) in {"razzle:2:15", "razzle:2:18"}
    assert not coach.analysis_fallback


@pytest.mark.parametrize("side", ["home", "away"])
def test_offense_and_defense_have_opposite_objectives_and_ties_belong_to_offense(side: str) -> None:
    home, away = charts(candidate=yards(-4))
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=yards(18)) if row.play is Play.THREE else row for row in home.offense
        ),
    )
    obs = observation(home, away, side)
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    chosen = coach.decision(obs)
    assert chosen.startswith("razzle:3:" if side == "home" else "razzle:2:")
    if side == "home":
        assert {key.rsplit(":", 1)[1] for key in obs.choices} == {"15"}


@pytest.mark.parametrize(
    "recovery,expected", [(range(10, 40), "razzle:1:"), (range(10, 11), "razzle:2:")]
)
def test_fumble_is_evaluated_by_recovery_distribution_not_assumed_lost(
    recovery: range, expected: str
) -> None:
    home, away = charts(
        candidate=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=10),
        supplement=4,
        recovery=recovery,
    )
    obs = observation(home, away, field=FieldState(Possession.HOME, 80, 1, 10))
    coach = DifficultyCoach(1, home, away, "hard", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs).startswith(expected)
    assert not coach.analysis_fallback


@pytest.mark.parametrize(
    "kind,target", [(ResultKind.SPRINT_OUT_PASS, Play.SEVEN), (ResultKind.BOOTLEG_PASS, Play.EIGHT)]
)
def test_options_use_their_actual_followup_and_ordinary_defense_priority(
    kind: ResultKind, target: Play
) -> None:
    home, away = charts()
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=NormalizedCell(kind, provenance()))
            if row.play is Play.FIVE
            else replace(row, cell=yards(-6))
            if row.play is target
            else row
            for row in home.offense
        ),
    )
    away = replace(away, defense=tuple(replace(row, cell=yards(10)) for row in away.defense))
    obs = observation(home, away)
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs).startswith("razzle:5:")
    assert not coach.analysis_fallback


def test_priority_can_make_breakaway_the_correct_defensive_choice_without_a_supplemental_roll() -> (
    None
):
    home, away = charts(supplement=30)
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=replace(yards(-6), priority=Priority.PARENTHESIZED))
            if row.play is Play.ONE
            else row
            for row in away.defense
        ),
    )
    obs = observation(home, away)
    estimates = evaluate_razzle_decisions(home, away, obs)
    assert all(e.complete for e in estimates)
    assert next(e for e in estimates if e.key == "razzle:1:15").evaluations == 6
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs).startswith("razzle:1:")


def test_qt_is_not_automatically_better_for_defense_than_breakaway() -> None:
    home, away = charts(candidate=NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
    home = replace(
        home,
        supplemental=tuple(
            replace(row, cell=yards(20))
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in home.supplemental
        ),
    )
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert not coach.decision(observation(home, away)).startswith("razzle:2:")
    assert not coach.analysis_fallback


def test_exact_breakaway_and_defensive_weights_match_all_216_by_36_physical_faces() -> None:
    home, away = charts()
    home = replace(
        home, supplemental=tuple(replace(row, cell=yards(row.roll)) for row in home.supplemental)
    )
    away = replace(away, defense=tuple(replace(row, cell=yards(-row.roll)) for row in away.defense))
    obs = replace(observation(home, away), choices=("razzle:1:15",))
    (estimate,) = evaluate_razzle_decisions(home, away, obs)
    field = FieldState(Possession.HOME, 65, 1, 10)
    values = []
    for black, first, second in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        for red, green in product(RED_FACES, GREEN_FACES):
            gain = OffensiveRoll(black, first, second).total - DefensiveRoll(red, green).total
            after = apply_gain(field, gain).state
            values.append(_hard_potential(after, "home") - _hard_potential(field, "home"))
    assert len(values) == 216 * 36
    assert estimate.complete
    assert estimate.mean_utility == pytest.approx(sum(values) / len(values), abs=1e-12)


def test_supplemental_penalty_uses_its_actual_enforcement_not_zero_yards() -> None:
    home, away = charts()
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 15),
    )
    home = replace(
        home,
        supplemental=tuple(
            replace(row, cell=penalty) if row.column is SupplementalColumn.BREAKAWAY else row
            for row in home.supplemental
        ),
    )
    obs = observation(home, away)
    estimates = evaluate_razzle_decisions(home, away, obs)
    assert all(e.complete for e in estimates)
    b = next(e.mean_utility for e in estimates if e.key == "razzle:1:15")
    ordinary = next(e.mean_utility for e in estimates if e.key == "razzle:2:15")
    assert b > ordinary
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert not coach.decision(obs).startswith("razzle:1:")


def test_fourth_down_loss_can_beat_an_interception_at_a_better_offensive_spot() -> None:
    home, away = charts(candidate=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20))
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=yards(-5)) if row.play is Play.THREE else row for row in home.offense
        ),
    )
    obs = observation(home, away, field=FieldState(Possession.HOME, 65, 4, 10))
    coach = DifficultyCoach(1, home, away, "hard", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs).startswith("razzle:3:")


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_frozen_v10_keeps_first_choice_and_normal_save_load_upgrades_to_current(mode: str) -> None:
    home, away = charts(candidate=yards(-4))
    source = ScriptedDice(
        [
            OffensiveRoll(1, 2, 3),
            OffensiveRoll(1, 3, 5),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
        ]
    )
    game = SavedGame.new(
        home,
        away,
        home_id="2026/cedar-test",
        away_id="2026/harbor-test",
        seed=1,
        coach_seed=2,
        coach_policy=f"{mode}-v10",
        dice=source,
    )
    game.snap("RZDZ", "A")
    text = dumps_game(game)
    teams = {"2026/cedar-test": home, "2026/harbor-test": away}
    frozen = loads_game(text, teams.__getitem__, preserve_development_policy=True)
    upgraded = loads_game(text, teams.__getitem__)
    assert frozen._coach.version == 10
    assert frozen._coach.decision(observe_policy(frozen.view(), "away", 10)) == "razzle:1:15"
    assert observe_policy(frozen.view(), "away", 10).razzle_context is None
    assert upgraded._coach.version == CURRENT_DIFFICULTY_VERSION
    assert upgraded._coach.decision(observe_game(upgraded.view(), "away")).startswith("razzle:2:")
    assert upgraded.view() == frozen.view()
    assert frozen.coach_step("home")[0].yards == 8
    assert upgraded.coach_step("home")[0].yards == -4


def test_exact_oracle_budget_and_failed_sample_fallback_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home, away = charts(candidate=yards(-4))
    obs = observation(home, away)
    estimates = evaluate_razzle_decisions(home, away, obs, max_evaluations=1)
    assert all(
        e.mean_utility is None and e.unexplored_probability == 1 and e.failed_probability == 0
        for e in estimates
    )
    sampled = tuple(RazzleChoiceEstimate(key, 16, 1, None, None) for key in obs.choices)
    monkeypatch.setattr("bowl_bound.chart_coaching.sample_razzle_decisions", lambda *_: sampled)
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs) in obs.choices
    assert coach.analysis_fallback


def test_equal_engine_outcomes_preserve_legal_order_independent_of_extra_rolls() -> None:
    home, away = charts()
    obs = observation(home, away)
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs) == obs.choices[0]


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_same_revealed_pending_choice_ignores_future_stream_and_remains_a_gamble(mode: str) -> None:
    from dataclasses import asdict
    from json import dumps

    from bowl_bound.coaching_session import plan_turn
    from tests.test_cli import saved_facts

    home, away = charts(candidate=NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
    home = replace(
        home,
        supplemental=tuple(
            replace(row, cell=yards(-10 if row.roll == 10 else -2))
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in home.supplemental
        ),
    )
    decisions, reports = [], []
    for future in (OffensiveRoll(1, 0, 0), OffensiveRoll(3, 4, 5)):
        source = ScriptedDice(
            [OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5), DefensiveRoll(1, 0), future]
        )
        game = SavedGame.new(
            home,
            away,
            home_id="2026/cedar-test",
            away_id="2026/harbor-test",
            seed=1,
            coach_seed=2,
            difficulty=mode,
            dice=source,
        )
        game.snap("RZDZ", "A")
        before = saved_facts(game)
        before_view = game.view()
        history = game._coach.call_history()
        context = observe_game(before_view, "away")
        assert before_view.pending.decision_outcomes == ()
        assert (
            next(c for c in before_view.pending.choices if c.id == "razzle:2:15").presentation_value
            == "QT"
        )
        selected = [game._coach.decision(context) for _ in range(3)]
        plans = [plan_turn(game.view(), "home", game._coach) for _ in range(3)]
        assert all(key == selected[0] for key in selected)
        assert all(plan.arguments == (selected[0],) for plan in plans)
        assert saved_facts(game) == before
        assert game.view() == before_view
        assert game._coach.call_history() == history
        assert source._position == 2
        assert "mean_utility" not in dumps(asdict(before_view))
        decisions.append(selected[0])
        reports.append(game.coach_step("home")[0])
        assert source._position == 4  # actual future draw only after commitment
        teams = {"2026/cedar-test": home, "2026/harbor-test": away}
        replayed = loads_game(dumps_game(game), teams.__getitem__)
        assert replayed.view() == game.view()
    assert decisions[0] == decisions[1]
    assert decisions[0].startswith("razzle:2:")
    assert [report.yards for report in reports] == [-10, -2]


def test_recursive_supplemental_branches_retain_failed_and_unexplored_mass() -> None:
    home, away = charts()
    home = replace(
        home,
        supplemental=tuple(
            replace(row, cell=NormalizedCell(ResultKind.BREAKAWAY, provenance()))
            if row.column is SupplementalColumn.BREAKAWAY
            else row
            for row in home.supplemental
        ),
    )
    obs = replace(observation(home, away), choices=("razzle:1:15",))
    (estimate,) = evaluate_razzle_decisions(home, away, obs, max_evaluations=50)
    assert estimate.failed_probability > 0
    assert estimate.unexplored_probability > 0
    assert estimate.failed_probability + estimate.unexplored_probability == 1
    assert estimate.mean_utility is None
    assert not estimate.complete


def test_unexpected_razzle_analysis_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_utility(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected programming error")

    home, away = charts(candidate=yards(-4))
    monkeypatch.setattr("bowl_bound.coaching_evaluation._utility", broken_utility)
    with pytest.raises(RuntimeError, match="injected programming error"):
        evaluate_razzle_decisions(home, away, observation(home, away))
    with pytest.raises(RuntimeError, match="injected programming error"):
        sample_razzle_decisions(home, away, observation(home, away))


def test_pending_comparison_cache_reuses_only_equivalent_observations_and_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home, away = charts(candidate=yards(-4))
    obs = observation(home, away)
    original = sample_razzle_decisions
    calls: list[CoachObservation] = []

    def counted(
        offense: TeamChart, defense: TeamChart, model: CoachObservation
    ) -> tuple[RazzleChoiceEstimate, ...]:
        calls.append(model)
        return original(offense, defense, model)

    monkeypatch.setattr("bowl_bound.chart_coaching.sample_razzle_decisions", counted)
    coach = DifficultyCoach(1, home, away, "easy", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs).startswith("razzle:2:")
    assert coach.decision(replace(obs, play_number=99)).startswith("razzle:2:")
    assert len(calls) == 1
    # A revealed formation can change normal priority and must not share a value.
    changed = replace(obs, razzle_context=replace(obs.razzle_context, defense="B"))
    assert coach.decision(changed).startswith("razzle:2:")
    assert len(calls) == 2
    for seconds in range(1, 129):
        coach.decision(replace(obs, remaining=seconds))
    assert len(coach._decision_cache) == 128
    count = len(calls)
    coach.decision(obs)  # evicted original must be evaluated again
    assert len(calls) == count + 1


@pytest.mark.parametrize("prefix", ["baseline", "chart", "easy", "medium", "hard"])
def test_current_revision_is_accepted_by_development_api_policy_contract(prefix: str) -> None:
    from backend.app import NewGame

    policy = f"{prefix}-v{CURRENT_DIFFICULTY_VERSION}"
    request = NewGame(home="2026/cedar-test", away="2026/harbor-test", coach_policy=policy)
    assert request.coach_policy == policy


@pytest.mark.parametrize("prefix", ["baseline", "chart", "easy", "medium", "hard"])
def test_current_revision_is_accepted_by_audit_cli(
    prefix: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from bowl_bound.coaching_audit import main

    monkeypatch.setattr("bowl_bound.coaching_audit.compare_policies", lambda *a, **k: ())
    assert main(["--policies", f"{prefix}-v{CURRENT_DIFFICULTY_VERSION}"]) == 0
    assert '"games": []' in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["easy", "medium", "hard"])
def test_loaded_web_game_automatically_commits_the_defensive_choice_once(
    tmp_path: Path, mode: str
) -> None:
    from json import loads

    from fastapi.testclient import TestClient

    from backend.app import create_app
    from tests.synthetic_teams import _with_legend_color, write_team

    home, away = charts(candidate=yards(-4))
    away = replace(
        away,
        defense=tuple(replace(row, cell=_with_legend_color(row.cell)) for row in away.defense),
    )
    home_id, away_id = write_team(tmp_path, home), write_team(tmp_path, away)
    game = SavedGame.new(
        home,
        away,
        home_id=home_id,
        away_id=away_id,
        seed=1,
        coach_seed=2,
        difficulty=mode,
        dice=ScriptedDice([OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5), DefensiveRoll(1, 0)]),
    )
    game.snap("RZDZ", "A")
    client = TestClient(create_app(tmp_path))
    loaded = client.post("/api/games/load?human_side=home", content=dumps_game(game))
    assert loaded.status_code == 200, loaded.text
    data = loaded.json()
    path = f"/api/games/{data['game_id']}"
    assert data["turn"]["automatic"]
    assert data["view"]["pending"]["chooser_side"] == "away"

    def save_facts() -> dict[str, object]:
        # Export time and its checksum change on every save, independently of play.
        document = loads(client.get(path + "/save").content)
        return {
            key: value for key, value in document.items() if key not in {"saved_at", "integrity"}
        }

    before = save_facts()
    for _ in range(3):
        assert client.get(path + "?human_side=home").json() == data
        assert save_facts() == before
    response = client.post(
        path + "/coach", json={"human_side": "home", "expected_revision": data["revision"]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["report"]["yards"] == -4
    saved = loads(client.get(path + "/save").content)
    assert len(saved["commands"]) == 2
    assert len(saved["rolls"]) == 3
    teams = {home_id: home, away_id: away}
    replayed = loads_game(client.get(path + "/save").text, teams.__getitem__)
    assert replayed.view().log[-1].yards == -4


def test_audit_cli_defaults_to_current_normal_tiers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from bowl_bound.coaching_audit import main

    seen: list[tuple[str, ...]] = []

    def compare(seeds: tuple[int, ...], *, policies: tuple[str, ...]) -> tuple[()]:
        assert seeds == (101, 307)
        seen.append(policies)
        return ()

    monkeypatch.setattr("bowl_bound.coaching_audit.compare_policies", compare)
    assert main([]) == 0
    assert seen == [
        (
            "baseline-v2",
            *(f"{mode}-v{CURRENT_DIFFICULTY_VERSION}" for mode in ("easy", "medium", "hard")),
        )
    ]
    assert '"games": []' in capsys.readouterr().out


@pytest.mark.parametrize("side", ["home", "away"])
def test_razzle_try_choices_use_two_point_outcomes_without_scrimmage_potential(side: str) -> None:
    home, away = charts(candidate=yards(-4))
    session = PlaySession.for_analysis(
        home,
        away,
        FieldState(Possession.HOME, 2, 1, 2),
        phase=SessionPhase.TWO_POINT_TRY,
        overtime=True,
    )
    rolls = [OffensiveRoll(1, 2, 3), OffensiveRoll(1, 3, 5)]
    if side == "home":
        rolls[1] = rolls[0]
    source = ScriptedDice(rolls)
    session.snap("RZDZ", "A", dice=source)
    obs = observe_game(session.view(), side)
    estimates = evaluate_razzle_decisions(home, away, obs)
    assert all(estimate.complete for estimate in estimates)
    assert {estimate.mean_utility for estimate in estimates} == {0, 2}
    coach = DifficultyCoach(1, home, away, "hard", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs).startswith("razzle:1:" if side == "home" else "razzle:2:")
    assert not coach.analysis_fallback
    assert source._position == 2


def test_production_branching_comparison_has_shared_engine_budget_and_no_first_choice_collapse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home, away = charts(candidate=yards(-4))
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 15),
    )
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=0))
            if row.play is Play.FOUR
            else replace(row, cell=NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
            if row.play is Play.THREE
            else row
            for row in home.offense
        ),
        supplemental=tuple(
            replace(row, cell=yards(-8))
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else replace(row, cell=penalty)
            if row.column is SupplementalColumn.BREAKAWAY and row.roll < 25
            else row
            for row in home.supplemental
        ),
    )
    obs = observation(home, away)
    original = PlaySession.for_analysis
    evaluations = 0

    def bounded(*args: object, **kwargs: object) -> PlaySession:
        nonlocal evaluations
        evaluations += 1
        assert evaluations <= 288, "production comparison exceeded shared rollout budget"
        return original(*args, **kwargs)

    monkeypatch.setattr(PlaySession, "for_analysis", bounded)
    coach = DifficultyCoach(1, home, away, "medium", version=CURRENT_DIFFICULTY_VERSION)
    chosen = coach.decision(obs)
    assert not chosen.startswith("razzle:1:")
    assert not coach.analysis_fallback
    assert 1 <= evaluations <= 288


def test_sampled_choices_share_streams_and_report_sampling_uncertainty() -> None:
    home, away = charts(candidate=NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance()))
    home = replace(
        home,
        supplemental=tuple(replace(row, cell=yards(row.roll - 24)) for row in home.supplemental),
    )
    obs = replace(observation(home, away), choices=("razzle:1:15", "razzle:2:15"))
    first, second = sample_razzle_decisions(home, away, obs)
    assert first.samples == second.samples == 32
    assert first.failed_samples == second.failed_samples == 0
    assert first.mean_utility == second.mean_utility
    assert first.standard_error == second.standard_error
    assert first.standard_error > 0
    for seed in (1, 987654):
        coach = DifficultyCoach(seed, home, away, "medium", version=CURRENT_DIFFICULTY_VERSION)
        assert coach.decision(obs) == obs.choices[0]
        assert not coach.analysis_fallback


def test_failed_rollouts_are_counted_without_success_renormalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bowl_bound.coaching_evaluation import EvaluationError

    home, away = charts(candidate=yards(-4))
    obs = observation(home, away)
    calls = 0

    def partly_failed(*args: object, **kwargs: object) -> tuple[float, float, bool]:
        nonlocal calls
        calls += 1
        if calls % 2:
            raise EvaluationError("synthetic unsupported rollout")
        return 100.0, 0.0, False

    monkeypatch.setattr("bowl_bound.coaching_evaluation._utility", partly_failed)
    estimates = sample_razzle_decisions(home, away, obs)
    assert sum(item.samples for item in estimates) == 288
    assert all(item.failed_samples == 8 and item.samples == 16 for item in estimates)
    assert all(item.mean_utility is None and item.standard_error is None for item in estimates)
    coach = DifficultyCoach(1, home, away, "medium", version=CURRENT_DIFFICULTY_VERSION)
    assert coach.decision(obs) in obs.choices
    assert coach.analysis_fallback


@pytest.mark.parametrize("budget", [True, 0, 17, 289])
def test_shared_sample_budget_rejects_invalid_or_incomplete_candidate_coverage(budget: int) -> None:
    home, away = charts()
    with pytest.raises(ValueError, match="budget"):
        sample_razzle_decisions(home, away, observation(home, away), total_samples=budget)


def test_single_sample_reports_unknown_sampling_error_instead_of_false_zero() -> None:
    home, away = charts()
    estimates = sample_razzle_decisions(home, away, observation(home, away), total_samples=18)
    assert all(item.samples == 1 and item.complete for item in estimates)
    assert all(item.standard_error is None for item in estimates)
