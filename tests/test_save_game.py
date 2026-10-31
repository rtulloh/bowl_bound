"""Versioned private saves use synthetic teams and resume actual engine procedures."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.save_game import (
    SavedGame,
    SaveFormatError,
    dumps_game,
    loads_game,
)
from bowl_bound.session import PendingDecisionError, SessionFinishedError
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tests.test_special_teams import special_chart


def charts(*, cell: NormalizedCell | None = None, gain: int = 0):
    result = []
    for name in ("Home", "Away"):
        ordinary = team_chart(
            name, season=2002, offense=gain, defense=0, plays={Play.NINE: cell} if cell else None
        )
        kicks = special_chart(
            name,
            kickoff=yards(70),
            punt=yards(40),
            interception_return=yards(20),
            field_goal=yards(40),
        )
        result.append(replace(ordinary, special_teams=kicks.special_teams))
    return tuple(result)


def new(*, teams=None, mode="drive", rolls=None, clock=None, spot=65):
    home, away = teams or charts()
    return SavedGame.new(
        home,
        away,
        home_id="2002/home",
        away_id="2002/away",
        seed=1,
        mode=mode,
        start_yards_to_goal=spot,
        clock=clock,
        dice=ScriptedDice(rolls) if rolls is not None else None,
    )


def clone(game, teams=None):
    home, away = teams or charts()
    restored = loads_game(dumps_game(game), lambda key: {"2002/home": home, "2002/away": away}[key])
    assert restored.view() == game.view()
    return restored


def opening(game):
    game.decide("toss:receive")
    game.kick("kickoff")
    game.decide("kick:touchback")


@pytest.mark.parametrize("choice", ["interception:return", "interception:decline"])
def test_pending_interception_uses_saved_future_source(choice: str) -> None:
    teams = charts(cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15))
    game = new(
        teams=teams, rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)]
    )
    game.snap("9", "A")
    restored = clone(game, teams)
    assert restored.decide(choice) == game.decide(choice)
    assert restored.view() == game.view()


@pytest.mark.parametrize("choice", ["accept:0:previous", "accept:0:end", "decline"])
def test_pending_penalty_restores_resolved_roll_not_another_snap(choice: str) -> None:
    teams = charts(
        cell=NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
        )
    )
    teams = tuple(
        replace(
            t,
            offense=tuple(
                replace(r, cell=yards(8)) if r.play is Play.NINE and r.roll != 10 else r
                for r in t.offense
            ),
        )
        for t in teams
    )
    game = new(
        teams=teams, rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]
    )
    game.snap("9", "A")
    restored = clone(game, teams)
    assert restored.decide(choice) == game.decide(choice)
    assert restored.view() == game.view()


@pytest.mark.parametrize("choice", ["kick:fair_catch", "kick:return"])
def test_pending_punt_callbacks_are_rebuilt_without_serializing_code(choice: str) -> None:
    game = new(rolls=[OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)])
    game.kick("punt")
    restored = clone(game)
    assert restored.decide(choice) == game.decide(choice)
    assert restored.view() == game.view()


@pytest.mark.parametrize("choice", ["conversion:kick", "conversion:two"])
def test_touchdown_and_conversion_resume_with_statistics(choice: str) -> None:
    teams = charts(gain=100)
    game = new(teams=teams)
    game.snap("1", "A")
    restored = clone(game, teams)
    assert restored.decide(choice) == game.decide(choice)
    if choice.endswith("two"):
        restored = clone(restored, teams)
        assert restored.snap("6", "A") == game.snap("6", "A")
    assert restored.view() == game.view()


def test_rng_resume_is_independent_of_view_and_save_requests() -> None:
    game = new(mode="regulation")
    opening(game)
    game.snap("1", "A")
    restored = clone(game)
    for _ in range(25):
        dumps_game(game)
        game.view()
        assert restored.snap("6", "A") == game.snap("6", "A")
        assert restored.view() == game.view()


def test_halftime_and_opening_kicker_resume_without_duplicate_kickoff() -> None:
    game = new(mode="regulation", clock=Clock(2, 1))
    opening(game)
    game.snap("1", "A")
    game.decide("clock:runoff")
    assert game.view().phase == "halftime_choice"
    restored = clone(game)
    assert restored.decide("half:kick") == game.decide("half:kick")
    restored = clone(restored)
    assert restored.kick("kickoff") == game.kick("kickoff")
    if game.view().pending:
        assert restored.decide("kick:touchback") == game.decide("kick:touchback")
    assert restored.view() == game.view()
    assert len(game.view().log) == 3


def test_overtime_toss_series_timeout_and_final_guard_survive_resume() -> None:
    game = new(mode="regulation", clock=Clock(4, 1))
    opening(game)
    game.snap("1", "A")
    game.decide("clock:runoff")
    assert game.view().phase == "overtime_choice"
    restored = clone(game)
    assert restored.decide("ot:offense") == game.decide("ot:offense")
    timeout = game.view().game_actions[0].key
    assert restored.action(timeout) == game.action(timeout)
    restored = clone(restored)
    assert restored.kick("field_goal") == game.kick("field_goal")
    restored = clone(restored)
    assert restored.action("kneel") == game.action("kneel")
    for _ in range(3):
        assert restored.action("kneel") == game.action("kneel")
    assert game.view().finished
    restored = clone(restored)
    for current in (game, restored):
        with pytest.raises(SessionFinishedError):
            current.snap("1", "A")
    assert game.view() == restored.view()


def test_rejected_requests_replay_without_changing_legal_state() -> None:
    game = new()
    with pytest.raises(ValueError, match="play must be"):
        game.snap("bad", "A")
    game.kick("punt")
    with pytest.raises(PendingDecisionError):
        game.snap("1", "A")
    restored = clone(game)
    assert restored.decide("kick:fair_catch") == game.decide("kick:fair_catch")
    assert restored.view() == game.view()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "{",
        "[]",
        "null",
        '{"schema_version":99}',
        '{"schema_version":1,"schema_version":1}',
        '{"x":NaN}',
    ],
)
def test_malformed_and_incompatible_saves_are_safe(text: str) -> None:
    with pytest.raises(SaveFormatError):
        loads_game(text, lambda _: pytest.fail("invalid save must not load teams"))


def test_changed_teams_are_rejected_and_save_omits_charts_and_local_paths() -> None:
    game = new()
    text = dumps_game(game)
    assert "offense" not in text and "provenance" not in text and "/Users/" not in text
    with pytest.raises(SaveFormatError, match="teams"):
        loads_game(text, lambda _: charts(gain=1)[0])
    data = json.loads(text)
    assert data["schema_version"] == 1
    assert data["teams"]["home"]["id"] == "2002/home"
    data["commands"] = [{"operation": "__import__", "arguments": []}]
    with pytest.raises(SaveFormatError):
        loads_game(json.dumps(data), lambda _: charts()[0])


def seal(data: dict) -> str:
    import hashlib

    payload = {key: value for key, value in data.items() if key != "integrity"}
    data["integrity"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return json.dumps(data)


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("engine_profile",), "other"),
        (("python",), [0, 0]),
        (("config", "seed"), True),
        (("config", "mode"), []),
        (("config", "clock", "quarter"), 5),
        (("config", "clock", "timeouts"), [4, 0]),
        (("teams", "home", "id"), "../../private"),
        (("random_state", "state"), [3, [0] * 624, None]),
        (("random_state", "state"), [3, [0] * 624 + [625], None]),
        (("random_state", "state"), [3, [False] * 625, None]),
        (("rolls",), [[9, 9, 9]]),
        (("rolls",), [[True, 0, 0]]),
        (("commands",), [{"operation": "eval", "arguments": [], "error": None}]),
        (("commands",), [{"operation": "snap", "arguments": [1, "A"], "error": None}]),
        (("commands",), [{"operation": "kick", "arguments": ["punt"], "error": []}]),
    ],
)
def test_structural_validation_rejects_resigned_malformed_fields_before_team_lookup(
    path, value
) -> None:
    data = json.loads(dumps_game(new()))
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(SaveFormatError):
        loads_game(seal(data), lambda _: pytest.fail("malformed save must not look up teams"))


@pytest.mark.parametrize(
    "change", ["unused_roll", "missing_roll", "wrong_roll_kind", "state_digest", "error"]
)
def test_replay_rejects_mismatched_evidence_even_with_valid_checksum(change: str) -> None:
    game = new()
    game.snap("1", "A")
    data = json.loads(dumps_game(game))
    if change == "unused_roll":
        data["rolls"].append([1, 0, 0])
    elif change == "missing_roll":
        data["rolls"].pop()
    elif change == "wrong_roll_kind":
        data["rolls"][0] = [1, 0]
    elif change == "state_digest":
        data["state_digest"] = "0" * 64
    else:
        data["commands"][0]["error"] = "ValueError"
    with pytest.raises(SaveFormatError):
        loads_game(seal(data), lambda key: charts()[0 if key.endswith("home") else 1])


def test_save_waits_until_inflight_snap_and_journal_commit_together(monkeypatch) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    game = new()
    entered, release, saved = Event(), Event(), Event()
    original = game._engine.snap

    def paused(*args, **kwargs):
        result = original(*args, **kwargs)
        entered.set()
        assert release.wait(2)
        return result

    def save():
        text = dumps_game(game)
        saved.set()
        return text

    monkeypatch.setattr(game._engine, "snap", paused)
    with ThreadPoolExecutor(2) as pool:
        snap_future = pool.submit(game.snap, "1", "A")
        assert entered.wait(2)
        save_future = pool.submit(save)
        try:
            assert not saved.wait(0.05), "save observed uncommitted snap state"
        finally:
            release.set()
        snap_future.result()
        text = save_future.result()
    restored = loads_game(text, lambda key: charts()[0 if key.endswith("home") else 1])
    assert restored.view() == game.view()


def test_saved_wrapper_preserves_existing_seeded_engine_behavior() -> None:
    from bowl_bound.regulation import RegulationGame
    from bowl_bound.session import PlaySession

    home, away = charts()
    for mode in ("drive", "regulation"):
        saved = new(mode=mode)
        plain = (
            PlaySession.new(home, away, seed=1)
            if mode == "drive"
            else RegulationGame.new(home, away, seed=1)
        )
        if mode == "regulation":
            opening(saved)
            opening(plain)
        for _ in range(3):
            assert saved.snap("1", "A") == plain.snap("1", "A")
        assert saved.view() == plain.view()


def test_loading_replays_only_observed_rolls_without_drawing_new_random_values(monkeypatch) -> None:
    from bowl_bound.dice import RandomDice

    game = new(mode="regulation")
    opening(game)
    game.snap("1", "A")
    text = dumps_game(game)
    with monkeypatch.context() as context:
        context.setattr(
            RandomDice, "offensive", lambda _: pytest.fail("load drew fresh offensive dice")
        )
        context.setattr(
            RandomDice, "defensive", lambda _: pytest.fail("load drew fresh defensive dice")
        )
        restored = loads_game(text, lambda key: charts()[0 if key.endswith("home") else 1])
    assert restored.snap("6", "A") == game.snap("6", "A")


def test_pre_m27_normal_timing_digest_remains_loadable() -> None:
    fixture = Path(__file__).parent / "fixtures" / "legacy_pre_m27_normal.json"
    teams = charts(cell=NormalizedCell(ResultKind.INCOMPLETE, provenance()))
    restored = loads_game(
        fixture.read_text(encoding="utf-8"),
        lambda key: teams[0 if key.endswith("home") else 1],
    )

    expected = new(mode="regulation", clock=Clock(1, 600), teams=teams)
    opening(expected)
    expected.snap("1", "A")
    expected.snap("1", "A")
    expected.snap("9", "A")
    assert restored.view() == expected.view()
    assert restored.snap("6", "A") == expected.snap("6", "A")
    assert restored.view() == expected.view()


def test_pre_m27_clock_choice_save_loads_without_restoring_runoff_action() -> None:
    fixture = Path(__file__).parent / "fixtures" / "legacy_pre_m27_clock.json"
    restored = loads_game(
        fixture.read_text(encoding="utf-8"),
        lambda key: charts()[0 if key.endswith("home") else 1],
    )

    expected = new(mode="regulation", clock=Clock(1, 600))
    opening(expected)
    expected.snap("1", "A")
    assert restored.view() == expected.view()
    assert restored.view().clock_optional
    assert all(
        choice.id != "clock:runoff"
        for choice in restored.view().clock_modifiers + restored.view().pending.choices
    )


def test_hurry_state_and_timeout_counts_survive_resume() -> None:
    game = new(mode="regulation")
    opening(game)
    game.snap("1", "A")
    game.decide("clock:timeout:home")
    game.snap("1", "A")
    game.decide("clock:hurry")
    assert game.view().hurried and game.view().clock.timeouts == (2, 3)
    restored = clone(game)
    assert restored.snap("1", "A") == game.snap("1", "A")
    assert restored.view() == game.view()


def test_repeated_overtime_and_paired_try_resume_do_not_add_offensive_statistics() -> None:
    teams = tuple(
        replace(
            t,
            offense=tuple(
                replace(r, cell=yards(100)) if r.play is Play.ONE else r for r in t.offense
            ),
        )
        for t in charts()
    )
    teams = tuple(replace(t, season=2021) for t in teams)
    game = new(teams=teams, mode="regulation", clock=Clock(4, 1))
    opening(game)
    game.snap("3", "A")
    game.decide("clock:runoff")
    game.decide("ot:offense")
    for _ in range(4):
        game.snap("1", "A")
        game.decide("conversion:two")
        game = clone(game, teams)
        game.snap("1", "A")
    assert game.view().overtime.round_number == 3
    assert game.view().overtime.paired_tries
    before = game.view().statistics
    restored = clone(game, teams)
    assert restored.snap("1", "A") == game.snap("1", "A")
    restored = clone(restored, teams)
    assert restored.snap("3", "A") == game.snap("3", "A")
    assert restored.view() == game.view()
    assert game.view().finished and game.view().statistics == before


def test_return_fumble_penalty_continuation_is_restored_before_next_recovery() -> None:
    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    teams = charts(cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15))
    home, away = teams
    return_chart = special_chart(
        "Away", interception_return=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=4)
    )
    away = replace(
        away,
        special_teams=tuple(
            replace(r, cell=foul) if r.column.value == "interception_return" and r.roll == 10 else r
            for r in return_chart.special_teams
        ),
    )
    teams = (home, away)
    game = new(
        teams=teams,
        rolls=[
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(1, 0, 0),
        ],
    )
    game.snap("9", "A")
    game.decide("interception:return")
    assert any(c.id == "return:decline" for c in game.view().pending.choices)
    restored = clone(game, teams)
    assert restored.decide("return:decline") == game.decide("return:decline")
    assert restored.view() == game.view()


@pytest.mark.parametrize(
    "limit,value", [("MAX_SAVE_BYTES", 1), ("MAX_COMMANDS", 0), ("MAX_ROLLS", 0)]
)
def test_save_limits_fail_without_altering_live_game(monkeypatch, limit: str, value: int) -> None:
    from bowl_bound import save_game

    game = new()
    game.snap("1", "A")
    before = game.view()
    monkeypatch.setattr(save_game, limit, value)
    with pytest.raises(SaveFormatError):
        dumps_game(game)
    assert game.view() == before
    assert game.snap("1", "A").supported


def test_unsupported_dice_source_is_refused_before_play() -> None:
    home, away = charts()
    with pytest.raises(SaveFormatError, match="dice source"):
        SavedGame.new(home, away, home_id="2002/home", away_id="2002/away", seed=1, dice=object())


def test_complete_regulation_resume_matches_score_clock_statistics_and_traces() -> None:
    game = new(mode="regulation")
    opening(game)
    restored = clone(game)
    phases = set()
    checkpoints = set()
    for _ in range(1000):
        view = game.view()
        phases.add(view.phase)
        checkpoint = (
            view.clock.quarter,
            view.phase,
            view.overtime.round_number if view.overtime else 0,
        )
        if checkpoint not in checkpoints:
            checkpoints.add(checkpoint)
            restored = clone(restored)
        assert restored.view() == view
        if view.finished:
            assert {"halftime_choice", "overtime_choice", "final"} <= phases
            for quarter in range(1, 5):
                assert (
                    sum(c.before - c.after for c in view.timing_log if c.quarter == quarter) == 900
                )
            assert view.statistics.home.total_plays + view.statistics.away.total_plays > 100
            return
        if view.pending and not view.clock_optional:
            choices = [c.id for c in view.pending.choices if c.enabled]
            choice = next(
                (
                    c
                    for c in ("clock:runoff", "half:receive", "ot:offense", "kick:touchback")
                    if c in choices
                ),
                choices[0],
            )
            assert restored.decide(choice) == game.decide(choice)
        elif view.phase == "kickoff":
            assert restored.kick("kickoff") == game.kick("kickoff")
        elif view.overtime and view.overtime.series_number == 2:
            assert restored.action("kneel") == game.action("kneel")
        elif view.overtime:
            assert restored.kick("field_goal") == game.kick("field_goal")
        else:
            assert restored.snap("1", "A") == game.snap("1", "A")
    pytest.fail("synthetic saved regulation did not finish")


def test_oversized_remaining_script_cannot_export_an_unloadable_save(monkeypatch) -> None:
    from bowl_bound import save_game

    game = new(rolls=[OffensiveRoll(1, 0, 0)] * 5)
    monkeypatch.setattr(save_game, "MAX_ROLLS", 4)
    with pytest.raises(SaveFormatError):
        dumps_game(game)


def test_failed_scripted_request_is_refused_instead_of_exporting_unreplayable_dice() -> None:
    from bowl_bound.dice import DiceSequenceError

    game = new(rolls=[OffensiveRoll(1, 0, 0)])
    with pytest.raises(DiceSequenceError):
        game.snap("1", "A")
    with pytest.raises(SaveFormatError):
        dumps_game(game)


@pytest.mark.parametrize("profile", ["bowl-bound-m18-v1", "bowl-bound-m18a-v1"])
def test_pre_ui_engine_profile_is_rejected_before_replay(profile: str) -> None:
    game = new()
    data = json.loads(dumps_game(game))
    data["engine_profile"] = profile
    with pytest.raises(SaveFormatError, match="incompatible"):
        loads_game(seal(data), lambda _: pytest.fail("old profile must not look up teams"))


@pytest.mark.parametrize("depth", [0, 5, 9])
def test_save_resumes_end_zone_interception_depth_and_future_return(depth: int) -> None:
    teams = charts(cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=10 + depth))
    game = new(
        teams=teams,
        spot=10,
        rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0)],
    )
    game.snap("9", "A")
    game.decide("interception:return")
    assert game.view().pending is not None
    restored = clone(game, teams)
    assert restored.decide("end_zone:return") == game.decide("end_zone:return")
    assert game.view().state.yards_to_goal == 80 + depth
    assert game.view().statistics.home.interceptions == 1


def test_complete_variable_yardage_game_reconciles_clock_stats_and_save_continuation() -> None:
    from bowl_bound.models import VariableReference

    variable = NormalizedCell(
        ResultKind.VARIABLE_DS, provenance(), variable=VariableReference.DS, variable_multiplier=1
    )
    teams = tuple(
        replace(t, offense=tuple(replace(r, cell=variable) for r in t.offense)) for t in charts()
    )
    game = new(teams=teams, mode="regulation")
    opening(game)
    restored = clone(game, teams)
    for _ in range(1000):
        view = game.view()
        assert restored.view() == view
        if view.finished:
            for quarter in range(1, 5):
                assert (
                    sum(c.before - c.after for c in view.timing_log if c.quarter == quarter) == 900
                )
            reports = [r for r in view.log if r.statistics.kind.value != "excluded"]
            assert reports and all(r.supported for r in view.log)
            assert any(e.section == "variable:offense" for r in reports for e in r.trace)
            for side in ("home", "away"):
                facts = [r.statistics for r in reports if r.statistics.team.value == side]
                stats = getattr(view.statistics, side)
                assert stats.total_plays == len(facts)
                assert stats.total_yards == sum(f.yards for f in facts)
            return
        if view.pending and not view.clock_optional:
            choices = [c.id for c in view.pending.choices if c.enabled]
            choice = next(
                (
                    c
                    for c in ("clock:runoff", "half:receive", "ot:offense", "kick:touchback")
                    if c in choices
                ),
                choices[0],
            )
            assert restored.decide(choice) == game.decide(choice)
        elif view.phase == "kickoff":
            assert restored.kick("kickoff") == game.kick("kickoff")
        elif view.overtime and view.overtime.series_number == 2:
            assert restored.action("kneel") == game.action("kneel")
        elif view.overtime:
            assert restored.kick("field_goal") == game.kick("field_goal")
        else:
            assert restored.snap("1", "A") == game.snap("1", "A")
        if game.view().clock.quarter != view.clock.quarter:
            restored = clone(restored, teams)
    pytest.fail("synthetic variable-yardage regulation did not finish")


def test_pending_own_recovery_foul_replays_original_line_to_gain() -> None:
    from bowl_bound.models import SpecialTeamsColumn
    from tests.test_engine_hardening import return_team

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
    )
    home = return_team("Home", 0)
    home = replace(
        home,
        offense=team_chart(
            "Home",
            offense=1,
            plays={Play.NINE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=9)},
        ).offense,
        special_teams=tuple(
            replace(r, cell=foul)
            if r.column is SpecialTeamsColumn.INTERCEPTION_RETURN and r.roll == 10
            else r
            for r in home.special_teams
        ),
    )
    teams = (home, return_team("Away"))
    game = new(
        teams=teams,
        rolls=[
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 4, 3),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 1),
        ],
    )
    game.snap("1", "A")
    game.snap("1", "A")
    game.snap("9", "A")
    restored = clone(game, teams)
    report = game.decide("return:accept")
    assert restored.decide("return:accept") == report
    assert (report.state_after.down, report.state_after.yards_to_go) == (3, 4)
    assert report.statistics.yards == 9
