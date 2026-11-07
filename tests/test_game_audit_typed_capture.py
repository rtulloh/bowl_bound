"""Noninterfering isolated command/draw/raw-priority evidence on synthetic games."""

from dataclasses import replace
from datetime import datetime

import pytest

from bowl_bound.dice import DefensiveRoll, DiceSequenceError, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from tests.synthetic_teams import yards
from tests.test_models import provenance
from tests.test_save_game import charts
from tools.game_audit_capture import capture_receipts
from tools.game_audit_envelope import audit_capture_links
from tools.game_audit_priority import audit_priority


def game(teams=None, rolls=None):
    home, away = teams or charts()
    return SavedGame.new(
        home,
        away,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive",
        advanced_ii=False,
        dice=ScriptedDice(rolls) if rolls is not None else None,
    )


@pytest.fixture
def fixed_save_clock(monkeypatch):
    import bowl_bound.save_game as codec

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 6, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(codec, "datetime", FixedDateTime)


def test_typed_capture_retains_actual_command_draw_and_raw_priority():
    subject = game(rolls=[OffensiveRoll(2, 0, 1), DefensiveRoll(2, 1)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "F")
    payload = capture.payload()
    assert audit_priority(payload["priority"]) == 1
    assert audit_capture_links(payload)["commands_checked"] == 1
    envelope = payload["typed_capture"]
    assert envelope["version"] == "2"
    assert envelope["errors"] == []
    command = envelope["commands"][0]
    assert command["operation"] == "snap"
    assert command["arguments"] == ["1", "F"]
    assert command["exception_type"] is None
    assert command["draw_range"] == [0, 2]
    assert command["priority_range"] == [0, 1]
    assert command["report_range"] == [0, 1]
    assert command["journal_range"] == [0, 1]
    assert envelope["draws"][0]["faces"] == dict(black=2, white_one=0, white_two=1)
    assert envelope["draws"][1]["faces"] == dict(red=2, green=1)
    assert command["before"]["view"]["state"] != command["after"]["view"]["state"]


@pytest.mark.parametrize("branch", ["B", "QT", "SOP", "penalty"])
def test_nested_priority_calls_and_imported_penalty_alias_are_captured(branch):
    if branch == "penalty":
        cell = NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
        )
    else:
        cell = NormalizedCell(ResultKind(branch), provenance())
    teams = charts(cell=None if branch == "SOP" else cell)
    teams = tuple(
        replace(
            team,
            offense=tuple(
                replace(row, cell=yards(8))
                if row.play in {Play.SEVEN, Play.NINE} and row.roll != 10
                else row
                for row in team.offense
            ),
            supplemental=tuple(
                replace(row, cell=yards(-4 if row.column.value == "QT" else 12))
                for row in team.supplemental
            ),
        )
        for team in teams
    )
    # SOP is callable as Play5, rather than a direct pass placement.
    if branch == "SOP":
        teams = tuple(
            replace(
                team,
                offense=tuple(
                    replace(row, cell=cell)
                    if row.play is Play.FIVE
                    else replace(row, cell=yards(8))
                    if row.play is Play.NINE
                    else row
                    for row in team.offense
                ),
            )
            for team in teams
        )
    subject = game(teams, [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("5" if branch == "SOP" else "9", "A")
    payload = capture.payload()
    assert audit_priority(payload["priority"]) == 2
    assert audit_capture_links(payload)["priority_events_checked"] == 2
    assert len(payload["typed_capture"]["draws"]) == 3
    assert payload["typed_capture"]["commands"][0]["priority_range"] == [0, 2]
    if branch == "penalty":
        assert payload["priority"]["events"][1]["caller"]["module"] == "bowl_bound.penalties"


def test_failed_noop_command_and_failed_partial_draw_attempt_are_both_retained():
    subject = game(rolls=[OffensiveRoll(1, 0, 0)])
    with capture_receipts(typed=True) as capture:
        with pytest.raises(ValueError, match="play must be"):
            subject.snap("unknown", "A")
        with pytest.raises(DiceSequenceError):
            subject.snap("1", "A")
    envelope = capture.payload()["typed_capture"]
    assert len(envelope["commands"]) == 2
    first, second = envelope["commands"]
    assert first["exception_type"] == "ValueError"
    assert first["draw_range"] == [0, 0]
    assert first["journal_range"] == [0, 0]
    assert second["exception_type"] == "DiceSequenceError"
    assert second["draw_range"] == [0, 1]
    assert second["draw_request_range"] == [0, 2]
    assert second["journal_range"] == [0, 1]
    assert envelope["draw_requests"][1]["completed"] is False
    links = audit_capture_links(capture.payload())
    assert links["failed_commands_observed"] == 2
    assert links["incomplete_draw_requests"] == 1


def test_capture_preserves_full_save_bytes_rng_journal_and_continuation(fixed_save_clock):
    ordinary = game()
    ordinary.snap("1", "A")
    before, state, journal = dumps_game(ordinary), ordinary.view(), list(ordinary._commands)
    ordinary.snap("2", "F")
    continuation = dumps_game(ordinary)
    subject = game()
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
        assert subject.view() == state
        assert subject._commands == journal
        assert dumps_game(subject) == before
        subject.snap("2", "F")
        assert dumps_game(subject) == continuation
    assert capture.payload()["typed_capture"]["errors"] == []


def test_tape_code_replacement_cannot_evade_frozen_target_identity(monkeypatch):
    from bowl_bound.save_game import _Tape

    def replacement(self, expected):
        return None

    with capture_receipts(typed=True) as capture:
        monkeypatch.setattr(_Tape._next, "__code__", replacement.__code__)
    assert capture.payload()["typed_capture"]["usable"] is False
    assert any(
        row["stage"] == "target_identity" for row in capture.payload()["typed_capture"]["errors"]
    )


def test_existing_profiler_is_rejected_and_preserved():
    import sys

    def foreign(frame, event, argument):
        return None

    previous = sys.getprofile()
    sys.setprofile(foreign)
    try:
        with pytest.raises(RuntimeError, match="without a profiler"):
            with capture_receipts(typed=True):
                pytest.fail("body must not execute")
        assert sys.getprofile() is foreign
    finally:
        sys.setprofile(previous)


def test_cleanup_restores_original_execute_and_profile_after_body_error():
    import sys

    original = SavedGame._execute
    with pytest.raises(RuntimeError, match="synthetic body error"):
        with capture_receipts(typed=True):
            raise RuntimeError("synthetic body error")
    assert SavedGame._execute is original
    assert sys.getprofile() is None


def test_collector_failure_is_visible_without_changing_delegate_result(
    monkeypatch, fixed_save_clock
):
    from tools import game_audit_typed_capture

    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    ordinary = game(rolls=rolls)
    expected = ordinary.snap("1", "A")

    def broken(cell):
        raise ValueError("synthetic collector failure")

    monkeypatch.setattr(game_audit_typed_capture, "_cell_facts", broken)
    subject = game(rolls=rolls)
    with capture_receipts(typed=True) as capture:
        assert subject.snap("1", "A") == expected
    assert subject.view() == ordinary.view()
    assert subject._commands == ordinary._commands
    assert subject._tape.rolls == ordinary._tape.rolls
    assert dumps_game(subject) == dumps_game(ordinary)
    assert capture.payload()["typed_capture"]["usable"] is False
    assert capture.payload()["typed_capture"]["errors"]


def test_foreign_target_module_origin_is_rejected_before_body(monkeypatch):
    from importlib.machinery import ModuleSpec

    import bowl_bound.resolution as resolution

    monkeypatch.setattr(
        resolution, "__spec__", ModuleSpec(resolution.__name__, None, origin="foreign.py")
    )
    with pytest.raises(ValueError, match="origin"):
        with capture_receipts(typed=True):
            pytest.fail("body must not execute")


def test_transient_alias_replacement_is_retained_even_when_restored(monkeypatch):
    import bowl_bound.penalties as penalties

    original_execute, original_resolve = SavedGame._execute, penalties.resolve_cells

    def replacement(*args):
        return original_resolve(*args)

    def transient(game, operation, arguments):
        with monkeypatch.context() as transient_patch:
            transient_patch.setattr(penalties, "resolve_cells", replacement)
            return original_execute(game, operation, arguments)

    monkeypatch.setattr(SavedGame, "_execute", transient)
    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
    assert penalties.resolve_cells is original_resolve
    assert capture.payload()["typed_capture"]["usable"] is False


@pytest.mark.parametrize("failure", ["errors", "unusable", "version", "boolean_errors"])
def test_receipt_cannot_reuse_partial_priority_when_collector_failed(failure):
    from tests.test_game_receipt_audit import receipt
    from tools.game_audit import ReceiptAuditError, audit_receipt

    row = receipt()
    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
    evidence = capture.payload()["typed_capture"]
    if failure == "errors":
        evidence["errors"] = [dict(stage="profile_return", exception_type="ValueError")]
    elif failure == "unusable":
        evidence["usable"] = False
    elif failure == "version":
        evidence["version"] = "999"
    else:
        evidence["errors"] = False
    row["audit_capture"] = dict(typed_capture=evidence)
    with pytest.raises(ReceiptAuditError, match="typed capture"):
        audit_receipt(row)


@pytest.mark.parametrize(
    "procedure,choice",
    [
        ("interception", "interception:return"),
        ("interception", "interception:decline"),
        ("penalty", "accept:0:previous"),
        ("penalty", "accept:0:end"),
        ("penalty", "decline"),
        ("punt", "kick:return"),
        ("punt", "kick:fair_catch"),
    ],
)
@pytest.mark.parametrize("lookup_rows", [False, True])
def test_pending_save_replay_and_continuation_are_byte_identical(
    procedure, choice, fixed_save_clock, lookup_rows
):
    if procedure == "interception":
        teams = charts(cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=15))
    elif procedure == "penalty":
        teams = charts(
            cell=NormalizedCell(
                ResultKind.PENALTY,
                provenance(),
                penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIVE_YARDS),
            )
        )
        teams = tuple(
            replace(
                team,
                offense=tuple(
                    replace(row, cell=yards(8)) if row.play is Play.NINE and row.roll != 10 else row
                    for row in team.offense
                ),
            )
            for team in teams
        )
    else:
        teams = charts()
    rolls = (
        [OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)]
        if procedure == "punt"
        else [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(2, 0, 0)]
    )

    def run():
        subject = game(teams, rolls)
        if procedure == "punt":
            subject.kick("punt")
        else:
            subject.snap("9", "A")
        pending = dumps_game(subject)
        restored = loads_game(
            pending, lambda key: dict(zip(("2002/home", "2002/away"), teams, strict=True))[key]
        )
        assert dumps_game(restored) == pending
        result = restored.decide(choice)
        return pending, result, restored.view(), dumps_game(restored)

    ordinary = run()
    with capture_receipts(typed=True, lookup_rows=lookup_rows) as capture:
        assert run() == ordinary
    envelope = capture.payload()["typed_capture"]
    assert envelope["errors"] == []
    assert len(envelope["commands"]) == 2
    assert envelope["replay_commands_skipped"] == 1
    assert envelope["commands"][1]["operation"] == "decide"
    links = audit_capture_links(capture.payload())
    assert links["commands_checked"] == links["game_objects_observed"] == 2
    # Pending results are not appended to the committed report log yet.
    assert links["initial_reports_not_observed"] == 0
    assert links["initial_journal_entries_not_observed"] == 1
    assert links["report_revision_address_linkage"] == "GO"


def test_original_command_delegate_is_called_exactly_once(monkeypatch):
    original = SavedGame._execute
    calls = []

    def counted(subject, operation, arguments):
        calls.append((operation, list(arguments)))
        return original(subject, operation, arguments)

    monkeypatch.setattr(SavedGame, "_execute", counted)
    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True):
        subject.snap("1", "A")
    assert calls == [("snap", ["1", "A"])]


def test_profile_loss_is_explicit_and_cleanup_restores_unprofiled_process(monkeypatch):
    import sys

    original = SavedGame._execute

    def loses_profile(subject, operation, arguments):
        sys.setprofile(None)
        return original(subject, operation, arguments)

    monkeypatch.setattr(SavedGame, "_execute", loses_profile)
    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
    assert capture.payload()["typed_capture"]["usable"] is False
    assert any(
        row["stage"] == "profile_ownership" for row in capture.payload()["typed_capture"]["errors"]
    )
    assert sys.getprofile() is None


def test_identity_collector_failure_does_not_replace_original_game_result(monkeypatch):
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    expected_subject = game(rolls=rolls)
    expected = expected_subject.snap("1", "A")
    subject = game(rolls=rolls)

    def broken():
        raise RuntimeError("synthetic identity collector failure")

    with capture_receipts(typed=True) as capture:
        monkeypatch.setattr(capture, "_check_bindings", broken)
        assert subject.snap("1", "A") == expected
    assert subject.view() == expected_subject.view()
    assert subject._commands == expected_subject._commands
    assert capture.payload()["typed_capture"]["usable"] is False


def test_foreign_tape_with_equal_faces_cannot_be_silently_ignored(monkeypatch):
    original = SavedGame._execute
    foreign = game(rolls=[OffensiveRoll(1, 0, 0)])

    def wrong_source(subject, operation, arguments):
        foreign._tape.offensive()
        return original(subject, operation, arguments)

    monkeypatch.setattr(SavedGame, "_execute", wrong_source)
    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
    assert capture.payload()["typed_capture"]["usable"] is False
    assert any(
        row["stage"] == "foreign_tape_request"
        for row in capture.payload()["typed_capture"]["errors"]
    )


def test_equal_game_states_retain_distinct_actual_game_and_team_identities():
    first = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    second = SavedGame.new(
        *charts(),
        home_id="2002/other",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive",
        advanced_ii=False,
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]),
    )
    assert first.view() == second.view()
    with capture_receipts(typed=True) as capture:
        first.snap("1", "A")
        second.snap("1", "A")
    commands = capture.payload()["typed_capture"]["commands"]
    assert [row["game_number"] for row in commands] == [1, 2]
    assert commands[0]["before"]["teams"]["home"]["id"] == "2002/home"
    assert commands[1]["before"]["teams"]["home"]["id"] == "2002/other"


def test_exhausted_script_keeps_identical_save_refusal_state_and_journal():
    from bowl_bound.save_game import SaveFormatError

    ordinary = game(rolls=[OffensiveRoll(1, 0, 0)])
    with pytest.raises(DiceSequenceError):
        ordinary.snap("1", "A")
    with pytest.raises(SaveFormatError) as ordinary_refusal:
        dumps_game(ordinary)
    subject = game(rolls=[OffensiveRoll(1, 0, 0)])
    with capture_receipts(typed=True) as capture:
        with pytest.raises(DiceSequenceError):
            subject.snap("1", "A")
        with pytest.raises(SaveFormatError) as observed_refusal:
            dumps_game(subject)
    assert str(observed_refusal.value) == str(ordinary_refusal.value)
    assert subject.view() == ordinary.view()
    assert subject._commands == ordinary._commands
    assert subject._tape.rolls == ordinary._tape.rolls
    assert subject._tape.future._position == ordinary._tape.future._position
    assert capture.payload()["typed_capture"]["draw_requests"][-1]["completed"] is False


def test_unwinding_raw_priority_call_never_becomes_a_successful_zero_result(monkeypatch):
    import bowl_bound.resolution as resolution

    invalid = NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=10)

    def unresolved(game, operation, arguments):
        return resolution.resolve_cells(invalid, yards(0))

    monkeypatch.setattr(SavedGame, "_execute", unresolved)
    subject = game()
    with capture_receipts(typed=True) as capture:
        with pytest.raises(resolution.ChartResolutionError):
            subject.snap("1", "A")
    payload = capture.payload()
    assert "priority" not in payload
    attempt = payload["typed_capture"]["priority_attempts"][0]
    assert attempt["completed"] is False
    assert "exception_type" not in attempt
    assert payload["typed_capture"]["commands"][0]["exception_type"] == "ChartResolutionError"


def test_python310_caller_code_without_co_qualname_is_supported():
    from types import SimpleNamespace

    import bowl_bound.resolution as resolution
    from bowl_bound.save_game import _Tape
    from tools.game_audit_typed_capture import TypedReceiptCapture

    capture = TypedReceiptCapture(resolution.resolve_cells, _Tape._next)
    capture._active = game(), dict(number=1)
    frame = SimpleNamespace(
        f_code=resolution.resolve_cells.__code__,
        f_locals=dict(offense=yards(1), defense=yards(0)),
        f_back=SimpleNamespace(
            f_globals=dict(__name__="synthetic"), f_code=SimpleNamespace(co_name="py310_caller")
        ),
    )
    capture.profile(frame, "call", None)
    assert capture.errors == []
    assert capture.priority_attempts[0]["caller"]["function"] == "py310_caller"


def test_foreign_thread_delegates_once_but_is_not_claimed_as_profiled():
    from concurrent.futures import ThreadPoolExecutor

    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    ordinary, subject = game(rolls=rolls), game(rolls=rolls)
    expected = ordinary.snap("1", "A")
    with capture_receipts(typed=True) as capture:
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(subject.snap, "1", "A").result() == expected
    assert subject.view() == ordinary.view()
    assert subject._commands == ordinary._commands
    envelope = capture.payload()["typed_capture"]
    assert envelope["usable"] is False
    assert envelope["commands"] == []
    assert envelope["unprofiled_commands"][0]["reason"] == "foreign_thread"


def test_nested_command_delegates_once_without_replacing_game_result(monkeypatch):
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    expected_subject, subject, nested = game(rolls=rolls), game(rolls=rolls), game(rolls=rolls)
    expected = expected_subject.snap("1", "A")
    original = SavedGame._execute

    def enters_nested(candidate, operation, arguments):
        if candidate is subject:
            nested.snap("1", "A")
        return original(candidate, operation, arguments)

    monkeypatch.setattr(SavedGame, "_execute", enters_nested)
    with capture_receipts(typed=True) as capture:
        assert subject.snap("1", "A") == expected
    assert subject.view() == nested.view() == expected_subject.view()
    assert subject._commands == nested._commands == expected_subject._commands
    envelope = capture.payload()["typed_capture"]
    assert envelope["usable"] is False
    assert envelope["unprofiled_commands"][0]["reason"] == "nested_command"


def test_self_green_envelope_without_core_evidence_is_rejected():
    from tests.test_game_receipt_audit import receipt
    from tools.game_audit import ReceiptAuditError, audit_receipt

    row = receipt()
    row["audit_capture"] = dict(typed_capture=dict(version="1", usable=True, errors=[]))
    with pytest.raises(ReceiptAuditError, match="typed capture"):
        audit_receipt(row)


@pytest.mark.parametrize(
    "field",
    [
        "commands",
        "draws",
        "draw_requests",
        "foreign_tape_requests",
        "unprofiled_commands",
        "priority_attempts",
        "replay_commands_skipped",
        "targets",
        "aliases",
        "scope",
    ],
)
def test_each_missing_core_field_is_rejected_individually(field):
    from tests.test_game_receipt_audit import receipt
    from tools.game_audit import ReceiptAuditError, audit_receipt

    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    del row["audit_capture"]["typed_capture"][field]
    with pytest.raises(ReceiptAuditError, match="typed capture"):
        audit_receipt(row)


@pytest.mark.parametrize("lookup_rows", [False, True])
def test_complete_synthetic_game_preserves_receipt_and_accepts_bounded_observations(lookup_rows):
    from scripts.run_local_season import GameSpec, _play_one
    from tests.season_audit.test_engine_runner import bundles
    from tools.game_audit import audit_receipt

    spec = GameSpec(1, 2007, "2007/synthetic-away", "2007/synthetic-home", 31)
    with capture_receipts(typed=True, lookup_rows=lookup_rows) as capture:
        row = _play_one(spec, bundles(), both_sides_policy="hard", verify_replay=True)
    assert row["status"] == "passed", row.get("error_detail")
    assert row == _play_one(spec, bundles(), both_sides_policy="hard", verify_replay=True)
    row["audit_capture"] = capture.payload()
    result = audit_receipt(row)
    assert result["components"]["symbolic_priority"] == "GO"
    assert result["components"]["capture_internal_linkage"] == "GO"
    assert result["components"]["chart_priority_and_cells"] == "UNVERIFIED"
    assert result["components"]["typed_lookup_agreement"] == "UNVERIFIED"
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False
    assert row["audit_capture"]["typed_capture"]["replay_commands_skipped"] > 0
    if lookup_rows:
        observed = row["audit_capture"]["lookup_rows"]
        assert observed["errors"] == [] and observed["usable"] is True
        assert observed["events"]
        assert observed["qualification"] == "UNVERIFIED"


def test_profiler_is_active_only_during_delegated_commands(monkeypatch):
    import sys

    original = SavedGame._execute
    profiled = []

    def observed(subject, operation, arguments):
        profiled.append(sys.getprofile() is not None)
        return original(subject, operation, arguments)

    monkeypatch.setattr(SavedGame, "_execute", observed)
    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        assert sys.getprofile() is None
        subject.snap("1", "A")
        assert sys.getprofile() is None
    assert profiled == [True]
    assert audit_priority(capture.payload()["priority"]) == 1


@pytest.mark.parametrize(
    "mutation", ["missing_target_hash", "boolean_target", "boolean_view", "missing_revisions"]
)
def test_core_observation_metadata_cannot_be_malformed_and_self_green(mutation):
    from tests.test_game_receipt_audit import receipt
    from tools.game_audit import ReceiptAuditError, audit_receipt

    subject = game(rolls=[OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    with capture_receipts(typed=True) as capture:
        subject.snap("1", "A")
    row = receipt()
    row["audit_capture"] = capture.payload()
    envelope = row["audit_capture"]["typed_capture"]
    if mutation == "missing_target_hash":
        del envelope["targets"][0]["source_sha256"]
    elif mutation == "boolean_target":
        envelope["targets"][0] = True
    elif mutation == "boolean_view":
        envelope["commands"][0]["before"]["view"] = True
    else:
        envelope["commands"][0]["report_revisions"] = None
    with pytest.raises(ReceiptAuditError, match="typed capture"):
        audit_receipt(row)


def test_unprofiled_serialization_failure_still_delegates_foreign_command_once(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from tools import game_audit_typed_capture

    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]
    ordinary, subject = game(rolls=rolls), game(rolls=rolls)
    expected = ordinary.snap("1", "A")

    def broken(value):
        raise ValueError("synthetic unprofiled metadata failure")

    with capture_receipts(typed=True) as capture:
        monkeypatch.setattr(game_audit_typed_capture, "_json_value", broken)
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(subject.snap, "1", "A").result() == expected
    assert subject.view() == ordinary.view()
    assert subject._commands == ordinary._commands
    assert capture.payload()["typed_capture"]["usable"] is False
    assert capture.payload()["typed_capture"]["errors"]
