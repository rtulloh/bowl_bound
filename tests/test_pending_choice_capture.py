"""Addressed mandatory saves use actual subjects and synthetic charts."""

from datetime import datetime, timezone

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import NormalizedCell, ResultKind
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.test_models import provenance
from tests.test_save_game import charts
from tools.game_audit_capture import capture_receipts
from tools.pending_choice_capture import (
    FIXED_SAVED_AT,
    PendingEvidenceError,
    capture_pending_choices,
    fixed_save,
    verify_pending_choices,
)


def subject(spot=65):
    teams = charts(cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15))
    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=1,
        coach_seed=1,
        start_yards_to_goal=spot,
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]),
    )
    return game, teams


def run(choices=("interception:decline",), spot=65):
    game, teams = subject(spot)
    with capture_receipts(typed=True, lookup_rows=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            game.snap("9", "A")
            for choice in choices:
                game.decide(choice)
    return game, teams, capture.payload(), typed.payload()


def verify(payload, teams, typed=None):
    return verify_pending_choices(
        payload, lambda key: teams[0] if key == "2002/home" else teams[1], typed_payload=typed
    )


def test_each_mandatory_boundary_needs_addressed_save_evidence() -> None:
    game, teams, payload, typed = run()
    boundaries = payload["pending_choice_saves"]["boundaries"]
    assert len(boundaries) == 1
    boundary = boundaries[0]
    assert boundary["creating_command"] == 1 and boundary["attempts"] == [2]
    assert not boundary["before_view"]["log"]
    assert boundary["journal_frontier"] == 1 and boundary["roll_count"] == 2
    assert boundary["team_identities"] and boundary["configuration"]
    assert verify(payload, teams, typed)["status"] == "GO-addressed-replay-only"
    assert len(game.view().log) == 1


def test_engine_pending_save_continuation_control() -> None:
    game, teams = subject()
    game.snap("9", "A")
    assert not game.view().log
    restored = loads_game(
        dumps_game(game), lambda key: teams[0] if key == "2002/home" else teams[1]
    )
    assert game.decide("interception:decline") == restored.decide("interception:decline")
    assert game.view() == restored.view()
    assert len(game.view().log) == 1


def test_original_invalid_choice_exception_survives_capture() -> None:
    from bowl_bound.session import InvalidDecisionError

    game, teams = subject()
    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            game.snap("9", "A")
            with pytest.raises(InvalidDecisionError):
                game.decide("foreign:choice")
    assert not game.view().log
    assert verify(capture.payload(), teams, typed.payload())["status"] == "UNVERIFIED-partial"


def test_collection_on_off_preserves_whole_save_view_report_journal_and_future() -> None:
    expected, teams = subject()
    first = expected.snap("9", "A")
    before = fixed_save(expected)
    final = expected.decide("interception:decline")
    baseline = fixed_save(expected)
    observed, teams, payload, typed = run()
    assert payload["pending_choice_saves"]["boundaries"][0]["save"] == before
    assert observed.view() == expected.view()
    assert observed._commands == expected._commands
    assert fixed_save(observed) == baseline
    assert observed.view().log[-1] == final
    assert first.pending
    verify(payload, teams, typed)
    assert fixed_save(observed) == baseline  # detached replay cannot touch original RNG/journal


def test_nested_end_zone_choice_gets_a_second_actual_boundary() -> None:
    game, teams, payload, typed = run(("interception:return", "end_zone:touchback"), spot=10)
    result = verify(payload, teams, typed)
    assert result["boundaries"] == result["continuations_checked"] == 2
    assert len(game.view().log) == 1
    assert [b["creating_command"] for b in payload["pending_choice_saves"]["boundaries"]] == [1, 2]


@pytest.mark.parametrize("mutation", ["save", "missing-command", "stale-game", "view", "future"])
def test_corrupt_or_missing_addressed_evidence_is_refused(mutation) -> None:
    _, teams, payload, typed = run()
    block = payload["pending_choice_saves"]
    if mutation == "save":
        block["boundaries"][0]["save"] += " "
    elif mutation == "missing-command":
        block["commands"].pop()
    elif mutation == "stale-game":
        block["commands"][1]["typed_game_number"] += 1
    elif mutation == "view":
        block["boundaries"][0]["before_view"]["score"]["home"] = 99
    else:
        block["commands"][1]["after_save"] = block["boundaries"][0]["save"]
    with pytest.raises((PendingEvidenceError, KeyError)):
        verify(payload, teams, typed)


@pytest.mark.parametrize("mutation", ["creating-command", "duplicate-attempt", "enabled-ids"])
def test_complete_boundary_identity_includes_origin_unique_attempts_and_legal_ids(mutation) -> None:
    _, teams, payload, typed = run()
    boundary = payload["pending_choice_saves"]["boundaries"][0]
    if mutation == "creating-command":
        boundary["creating_command"] = 999
    elif mutation == "duplicate-attempt":
        boundary["attempts"].append(2)
    else:
        boundary["enabled_ids"] = []
    with pytest.raises(PendingEvidenceError):
        verify(payload, teams, typed)


def test_equal_looking_games_are_distinct_objects_and_cannot_share_attempts() -> None:
    left, teams = subject()
    right, _ = subject()
    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            left.snap("9", "A")
            right.snap("9", "A")
            left.decide("interception:decline")
            right.decide("interception:decline")
    payload = capture.payload()
    assert len(payload["pending_choice_saves"]["boundaries"]) == 2
    assert verify(payload, teams, typed.payload())["continuations_checked"] == 2
    payload["pending_choice_saves"]["boundaries"][0]["attempts"] = [4]
    with pytest.raises(PendingEvidenceError, match="foreign boundary"):
        verify(payload, teams, typed.payload())


def test_offline_replay_cannot_pollute_active_typed_capture() -> None:
    _, teams, payload, _ = run()
    with capture_receipts(typed=True):
        with pytest.raises(PendingEvidenceError, match="contexts closed"):
            verify(payload, teams)


def test_unselected_boundary_and_missing_typed_linkage_remain_unknown() -> None:
    game, teams = subject()
    with capture_pending_choices() as capture:
        game.snap("9", "A")
    result = verify(capture.payload(), teams)
    assert result["status"] == "UNVERIFIED-partial"
    assert result["boundaries"] == 1 and result["continuations_checked"] == 0


def test_abnormal_capture_exit_cannot_reuse_a_completed_green() -> None:
    game, teams = subject()
    capture = None
    with capture_receipts(typed=True) as typed:
        with pytest.raises(RuntimeError, match="original failure"):
            with capture_pending_choices(typed_capture=typed) as capture:
                game.snap("9", "A")
                game.decide("interception:decline")
                raise RuntimeError("original failure")
    assert capture is not None
    with pytest.raises(PendingEvidenceError, match="failed"):
        verify(capture.payload(), teams, typed.payload())


def test_serialization_clock_is_exactly_the_frozen_engine_save(monkeypatch) -> None:
    import bowl_bound.save_game as codec

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2000, 1, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(codec, "datetime", Frozen)
    game, _ = subject()
    assert fixed_save(game) == dumps_game(game)
    assert FIXED_SAVED_AT == "2000-01-01T00:00:00+00:00"
    with pytest.raises(PendingEvidenceError, match="timezone"):
        fixed_save(game, "2000-01-01T00:00:00")


def test_snapshot_failure_is_recorded_without_replacing_authoritative_result(monkeypatch) -> None:
    import tools.pending_choice_capture as observer

    game, _ = subject()
    game.snap("9", "A")
    expected, _ = subject()
    expected.snap("9", "A")
    report = expected.decide("interception:decline")

    def broken(*args):
        raise ValueError("diagnostic failure")

    monkeypatch.setattr(observer, "fixed_save", broken)
    with capture_pending_choices() as capture:
        assert game.decide("interception:decline") == report
    assert capture.payload()["pending_choice_saves"]["usable"] is False
    assert game.view() == expected.view()


def test_coached_and_atomic_api_paths_capture_the_actual_execute_boundary() -> None:
    for api in ("coached", "atomic"):
        game, teams = subject()
        with capture_receipts(typed=True) as typed:
            with capture_pending_choices(typed_capture=typed) as capture:
                game.snap("9", "A")
                if api == "coached":
                    game.coach_execute("away", "decide", "interception:decline")
                else:
                    game.execute_with_view("decide", ["interception:decline"])
        assert verify(capture.payload(), teams, typed.payload())["continuations_checked"] == 1


def test_complete_synthetic_hard_game_collection_is_noninterfering() -> None:
    from unittest.mock import patch

    from scripts import run_local_season as runner
    from tests.season_audit.test_engine_runner import bundles

    teams = bundles()
    spec = runner.GameSpec(1, 2007, "2007/synthetic-away", "2007/synthetic-home", 31)
    baseline_objects = []
    native_new, native_load = runner._new_audit_game, runner.loads_game

    def remember_new(*args, **kwargs):
        game = native_new(*args, **kwargs)
        baseline_objects.append(game)
        return game

    def remember_load(*args, **kwargs):
        game = native_load(*args, **kwargs)
        baseline_objects.append(game)
        return game

    with (
        patch.object(runner, "_new_audit_game", remember_new),
        patch.object(runner, "loads_game", remember_load),
    ):
        expected = runner._play_one(spec, teams, both_sides_policy="hard", verify_replay=True)
    assert len(baseline_objects) == 3  # Original, midpoint continuation, final strict replay.
    expected_final = baseline_objects[1]
    with capture_receipts(typed=True, lookup_rows=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            observed = runner._play_one(
                spec,
                teams,
                both_sides_policy="hard",
                verify_replay=True,
                resume_checkpoint=capture.resume,
            )
    assert observed == expected and observed["status"] == "passed"
    actual_final = capture.games[-1]
    assert fixed_save(actual_final) == fixed_save(expected_final)
    assert actual_final.view() == expected_final.view()
    assert actual_final._commands == expected_final._commands
    assert actual_final._tape.rolls == expected_final._tape.rolls
    assert actual_final._tape.position == expected_final._tape.position
    result = verify_pending_choices(
        capture.payload(), lambda key: teams[key][0], typed_payload=typed.payload()
    )
    assert result["status"] == "GO-addressed-replay-only", result
    assert result["boundaries"] == result["continuations_checked"] + result["handoffs_checked"] > 0
    assert result["handoffs_checked"] == result["resumes_checked"] == 1


def test_explicit_resume_binds_actual_objects_without_losing_original_boundary() -> None:
    original, teams = subject()

    def loader(key):
        return teams[0] if key == "2002/home" else teams[1]

    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            original.snap("9", "A")
            restored = capture.resume(original, loader)
            assert restored is not original
            restored.decide("interception:decline")
    result = verify(capture.payload(), teams, typed.payload())
    assert result["status"] == "GO-addressed-replay-only"
    assert result["boundaries"] == 2
    assert result["continuations_checked"] == result["handoffs_checked"] == 1


def test_equal_looking_unobserved_object_cannot_supply_resume_origin() -> None:
    observed, teams = subject()
    foreign, _ = subject()
    foreign.snap("9", "A")
    with capture_pending_choices() as capture:
        observed.snap("9", "A")
        assert observed.view() == foreign.view()
        with pytest.raises(PendingEvidenceError, match="observed object"):
            capture.resume(foreign, lambda key: teams[0] if key == "2002/home" else teams[1])
    assert capture.payload()["pending_choice_saves"]["usable"] is False


def test_resume_cannot_hide_a_forked_primary_source_object() -> None:
    original, teams = subject()

    def loader(key):
        return teams[0] if key == "2002/home" else teams[1]

    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            original.snap("9", "A")
            restored = capture.resume(original, loader)
            original.decide("interception:decline")
            restored.decide("interception:decline")
    with pytest.raises(PendingEvidenceError, match="forked source"):
        verify(capture.payload(), teams, typed.payload())


def test_broken_typed_diagnostic_cannot_replace_an_authoritative_command() -> None:
    from types import SimpleNamespace

    game, _ = subject()
    game.snap("9", "A")
    expected, _ = subject()
    expected.snap("9", "A")
    report = expected.decide("interception:decline")
    broken = SimpleNamespace(commands=None)
    with capture_pending_choices(typed_capture=broken) as capture:
        assert game.decide("interception:decline") == report
    assert game.view() == expected.view()
    assert capture.payload()["pending_choice_saves"]["usable"] is False


def test_final_unselected_pending_boundary_cannot_be_omitted() -> None:
    game, teams = subject()
    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            game.snap("9", "A")
    payload = capture.payload()
    payload["pending_choice_saves"]["boundaries"].clear()
    with pytest.raises(PendingEvidenceError, match="boundary"):
        verify(payload, teams, typed.payload())


def test_saved_tape_frontier_cannot_be_fabricated() -> None:
    _, teams, payload, typed = run()
    payload["pending_choice_saves"]["boundaries"][0]["tape_position"] += 1
    with pytest.raises(PendingEvidenceError, match="metadata"):
        verify(payload, teams, typed)


def test_one_typed_command_cannot_qualify_duplicate_observed_attempts() -> None:
    from copy import deepcopy

    _, teams, payload, typed = run()
    block = payload["pending_choice_saves"]
    duplicate = deepcopy(block["commands"][-1])
    duplicate["number"] += 1
    block["commands"].append(duplicate)
    block["boundaries"][0]["attempts"].append(duplicate["number"])
    with pytest.raises(PendingEvidenceError, match="typed command exposure"):
        verify(payload, teams, typed)


def test_optional_normal_clock_continuation_is_replayed_and_counted_separately() -> None:
    from scripts.run_local_season import GameSpec, _new_audit_game
    from tests.season_audit.test_engine_runner import bundles

    teams = bundles()
    game = _new_audit_game(
        GameSpec(1, 2007, "2007/synthetic-away", "2007/synthetic-home", 31),
        teams,
        both_sides_policy="hard",
    )
    game.decide("toss:receive")
    game.kick("kickoff")
    game.snap("3", "C")
    assert game.view().phase == "clock_choice"
    assert getattr(game.view(), "clock_optional", False) is True
    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            game.snap("3", "C")
    result = verify_pending_choices(
        capture.payload(), lambda key: teams[key][0], typed_payload=typed.payload()
    )
    assert result["continuations_checked"] == 1
    assert result["normal_clock_continuations_checked"] == 1
    assert result["mandatory_decisions_checked"] == 0
    assert result["status"] == "UNVERIFIED-partial"  # The next clock menu is unselected.


def test_nonpending_resume_cannot_invent_a_source_object() -> None:
    game, teams = subject()
    with capture_receipts(typed=True) as typed:
        with capture_pending_choices(typed_capture=typed) as capture:
            game.snap("9", "A")
            game.decide("interception:decline")
            assert game.view().pending is None
            capture.resume(game, lambda key: teams[0] if key == "2002/home" else teams[1])
    payload = capture.payload()
    payload["pending_choice_saves"]["resumes"][0]["source_game_number"] = 999
    with pytest.raises(PendingEvidenceError, match="resume source"):
        verify(payload, teams, typed.payload())


@pytest.mark.parametrize("mutation", ["phase", "hidden-creator"])
def test_boundary_metadata_cannot_reclassify_or_hide_a_created_decision(mutation) -> None:
    _, teams, payload, typed = run()
    boundary = payload["pending_choice_saves"]["boundaries"][0]
    if mutation == "phase":
        boundary["phase"] = "clock_choice"
    else:
        boundary["creating_command"] = None
        boundary["initial_anchor"] = True
    with pytest.raises(PendingEvidenceError, match="phase|creating command"):
        verify(payload, teams, typed)


def test_typed_linkage_requires_canonical_json_types() -> None:
    _, teams, payload, typed = run()
    assert type(typed["typed_capture"]["commands"][1]["before"]["view"]["state"]["down"]) is int
    typed["typed_capture"]["commands"][1]["before"]["view"]["state"]["down"] = True
    with pytest.raises(PendingEvidenceError, match="boundary view"):
        verify(payload, teams, typed)
