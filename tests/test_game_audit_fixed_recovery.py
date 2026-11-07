"""Fixed in-field recovery subjects and independently stated BB expectations."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import OffensiveRoll
from bowl_bound.models import ResultKind
from tests import test_game_audit_kickoff as kickoff
from tests.test_game_audit_ordinary_commitment import change_report, log_digest
from tests.test_game_audit_recovery_inventory import bind_synthetic_inputs
from tests.test_game_audit_supplemental import subject_receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


def kick_recovery(monkeypatch, *, side="home", retained=False, advance=False):
    original = kickoff.subject_teams

    def fumble_teams():
        return tuple(
            replace(
                team,
                special_teams=tuple(
                    replace(record, cell=replace(record.cell, kind=ResultKind.FUMBLE, yards=0))
                    if record.column.value == "kickoff_return"
                    else record
                    for record in team.special_teams
                ),
            )
            for team in original()
        )

    monkeypatch.setattr(kickoff, "subject_teams", fumble_teams)
    row, inventory, teams = kickoff.kickoff_subject(
        chooser=side,
        return_yards=0,
        return_teams=True,
        recovery_roll=(OffensiveRoll(1, 3, 4) if retained else OffensiveRoll(3, 3, 4))
        if advance
        else OffensiveRoll(2, 0, 0)
        if retained
        else OffensiveRoll(2, 4, 4),
        recovery_return_roll=OffensiveRoll(2, 0, 0) if advance else None,
    )
    for record in inventory["cells"]:
        if (
            record["address"]["table"] == "special_teams"
            and record["address"]["column"] == "kickoff_return"
        ):
            record["facts"].update(kind="fumble", yards=0)
    return row, bind_synthetic_inputs(inventory, teams)


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize("retained", [False, True])
def test_fixed_kick_recovery_owner_is_checked_from_external_interval(monkeypatch, side, retained):
    row, inventory = kick_recovery(monkeypatch, side=side, retained=retained)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["ordinary_kickoff_commitment"] == "GO"
    assert result["kickoff_counts"]["recoveries"] == 1
    assert result["kickoff_counts"]["checked"] == 1
    assert result["components"]["standard_clock"] == "GO"
    assert result["standard_clock_counts"]["deferred"] == int(not retained)
    assert result["full_play_by_play_qualification"] is False


@pytest.mark.parametrize("fault", ["timing", "field", "clock", "phase", "box"])
def test_fixed_kick_recovery_cannot_skip_owner_field_clock_or_box_checks(monkeypatch, fault):
    row, inventory = kick_recovery(monkeypatch, retained=False)
    command = row["audit_capture"]["typed_capture"]["commands"][-1]
    if fault == "timing":
        report = command["report_changes"][0]["after"]
        report["timing"]["change_of_possession"] = True
        command["returned_report"] = deepcopy(report)
        command["report_revisions"] = [deepcopy(report)]
        command["after"]["log_sha256"] = log_digest([report])
    elif fault == "field":
        command["after"]["view"]["state"]["possession"] = "home"
    elif fault == "clock":
        command["after"]["view"]["clock"]["remaining"] -= 10
    elif fault == "phase":
        command["after"]["view"].update(phase="scrimmage", pending=None, clock_optional=False)
    else:
        command["after"]["view"]["statistics"]["home"]["rushing_attempts"] = 1
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)


@pytest.mark.parametrize(
    "chain,location,category",
    [
        (("QT",), -3, "sack"),
        (("QT",), 0, "rush"),
        (("QT",), 3, "rush"),
        (("QR",), -3, "rush"),
        (("B",), 3, "completion"),
    ],
)
@pytest.mark.parametrize("retained", [False, True])
@pytest.mark.parametrize("side", ["home", "away"])
def test_fixed_scrimmage_recovery_has_original_owner_and_terminal_category(
    chain, location, category, retained, side
):
    row, inventory, teams = subject_receipt(
        chain=chain,
        terminal=("fumble", location),
        side=side,
        defense=0,
        recovery_roll=OffensiveRoll(2, 0, 0) if retained else OffensiveRoll(2, 4, 4),
        return_teams=True,
    )
    result = audit_receipt(row, lookup_inventory=bind_synthetic_inputs(inventory, teams))
    counts = result["supplemental_commitment_counts"]
    assert result["components"]["supplemental_commitment"] == "GO"
    assert counts["recoveries"] == 1
    assert counts["dispositions"][0]["derived_category"] == category
    assert counts["dispositions"][0]["derived_yards"] == location
    credit = row["engine_log"][-1]["statistics"]
    assert credit == dict(kind=category, team=side, yards=location, touchdown=False)


@pytest.mark.parametrize("fault", ["owner", "yards", "category", "called", "resolved", "outcome"])
def test_fixed_qt_fumble_corruptions_cannot_hide_behind_complex_terminal(fault):
    row, inventory, teams = subject_receipt(
        chain=("QT",),
        terminal=("fumble", -3),
        defense=0,
        recovery_roll=OffensiveRoll(2, 4, 4),
        return_teams=True,
    )

    def mutate(report, command):
        if fault == "owner":
            report["statistics"]["team"] = "away"
        elif fault == "yards":
            report["statistics"]["yards"] = 0
        elif fault == "category":
            report["statistics"]["kind"] = "completion"
        elif fault in {"called", "resolved"}:
            report[fault + "_play"] = "Option"
        else:
            report["outcome"] = "offensive_recovery"

    change_report(row, mutate)
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=bind_synthetic_inputs(inventory, teams))


def test_version_one_keeps_fixed_fumble_recovery_unknown():
    row, inventory = subject_receipt(
        chain=("QT",),
        terminal=("fumble", -3),
        defense=0,
        recovery_roll=OffensiveRoll(2, 4, 4),
    )
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["supplemental_commitment"] == "UNVERIFIED"


@pytest.mark.parametrize("retained", [False, True])
def test_permitted_recovery_advance_stays_unknown_instead_of_false_refusal(retained):
    row, inventory, teams = subject_receipt(
        chain=("QT",),
        terminal=("fumble", -3),
        defense=0,
        recovery_roll=OffensiveRoll(1, 3, 4) if retained else OffensiveRoll(3, 3, 4),
        recovery_return_roll=OffensiveRoll(2, 0, 0),
        return_teams=True,
    )
    result = audit_receipt(row, lookup_inventory=bind_synthetic_inputs(inventory, teams))
    assert result["components"]["captured_row_linkage"] == "GO"
    counts = result["supplemental_commitment_counts"]
    assert counts["checked"] == 0
    assert counts["dispositions"][0]["reason"] == "recovery_advance_authority"


@pytest.mark.parametrize("retained", [False, True])
def test_permitted_kick_recovery_advance_stays_unknown(monkeypatch, retained):
    row, inventory = kick_recovery(monkeypatch, retained=retained, advance=True)
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["captured_row_linkage"] == "GO"
    counts = result["kickoff_counts"]
    assert counts["checked"] == 0
    assert counts["dispositions"][1]["reason"] == "recovery_advance_authority"


def test_known_interval_with_wrong_chart_identity_refuses():
    row, inventory, teams = subject_receipt(
        chain=("QT",),
        terminal=("fumble", -3),
        defense=0,
        recovery_roll=OffensiveRoll(2, 4, 4),
        return_teams=True,
    )
    inventory = bind_synthetic_inputs(inventory, teams)
    inventory["teams"][0]["fingerprint"] = "0" * 64
    with pytest.raises(ReceiptAuditError, match="fingerprint"):
        audit_receipt(row, lookup_inventory=inventory)
