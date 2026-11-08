"""Actual Option rerolls stay outside the fixed ordinary penalty oracle."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    ChartColor,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    ResultKind,
)
from bowl_bound.save_game import SavedGame
from tests.test_game_audit_row_links import frozen_inventory, subject_teams
from tests.test_game_receipt_audit import receipt
from tests.test_models import provenance
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_capture import capture_receipts
from tools.game_audit_penalty import PenaltyEvidenceError, _origin


def option_penalty_subject(marker, side):
    def cell(roll, play):
        if roll in {10, 30}:
            return NormalizedCell(
                ResultKind.PENALTY,
                provenance(),
                penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, yards=5),
                chart_color=ChartColor.WHITE,
            )
        if roll == 20 and play.value == 5:
            return NormalizedCell(ResultKind(marker), provenance(), chart_color=ChartColor.WHITE)
        return NormalizedCell(ResultKind.INCOMPLETE, provenance(), chart_color=ChartColor.WHITE)

    teams = tuple(
        replace(
            chart,
            offense=tuple(replace(row, cell=cell(row.roll, row.play)) for row in chart.offense),
            defense=tuple(
                replace(row, cell=replace(row.cell, yards=-4, chart_color=ChartColor.WHITE))
                for row in chart.defense
            ),
        )
        for chart in subject_teams()
    )
    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=37,
        coach_seed=41,
        mode="drive",
        advanced_ii=False,
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
                OffensiveRoll(3, 4, 5),
                OffensiveRoll(3, 4, 5),
            ]
        ),
    )
    game._engine._field = FieldState(Possession(side), 65, 1, 10)
    with capture_receipts(typed=True, lookup_rows=True) as capture:
        assert game.snap("5", "F").pending is True
        game.decide("accept:0:previous")
    row = receipt()
    row["audit_capture"] = capture.payload()
    commands = row["audit_capture"]["typed_capture"]["commands"]
    final = commands[-1]["after"]["view"]
    row["engine_log"] = deepcopy(commands[-1]["report_revisions"])
    row["final"].update(
        statistics=deepcopy(final["statistics"]), home_score=0, away_score=0, scoring=[]
    )
    inventory = frozen_inventory()
    for record in inventory["cells"]:
        if record["address"]["table"] == "defense":
            record["facts"].update(yards=-4, chart_color="white")
        elif record["address"]["table"] == "offense":
            total = record["address"]["roll"]
            penalty = total in {10, 30}
            record["facts"].update(
                kind="penalty"
                if penalty
                else marker
                if total == 20 and record["address"]["play"] == 5
                else "incomplete",
                yards=None,
                penalty=dict(
                    team="offense", code="fixed", yards=5, variable=None, variable_multiplier=None
                )
                if penalty
                else None,
                chart_color="white",
            )
    return row, inventory


@pytest.mark.parametrize("marker,resolved", [("SOP", "Sprint Out"), ("BLP", "Boot-leg")])
@pytest.mark.parametrize("side", ["home", "away"])
def test_actual_penalty_option_tail_is_unknown_before_retained_defense_closure(
    marker, resolved, side
):
    row, inventory = option_penalty_subject(marker, side)
    capture = row["audit_capture"]
    events = capture["priority"]["events"]
    assert [event["defense"]["kind"] for event in events] == ["yards", "no_change", "no_change"]
    assert [r["facts"]["kind"] for r in capture["lookup_rows"]["events"]] == [
        "penalty",
        "yards",
        marker,
        "penalty",
        "incomplete",
    ]
    assert row["engine_log"][0]["called_play"] == "Option"
    assert row["engine_log"][0]["resolved_play"] == resolved
    result = audit_receipt(row, lookup_inventory=inventory)
    assert result["components"]["accepted_previous_penalty_commitment"] == "UNVERIFIED"
    assert result["penalty_commitment_counts"]["checked"] == 0
    assert result["penalty_commitment_counts"]["unknown_reasons"]["prepared_option_authority"] == 1


def test_ordinary_penalty_still_refuses_changed_retained_defense():
    from tests.test_game_audit_penalty_commitment import penalty_subject

    row, _ = penalty_subject()
    capture = row["audit_capture"]
    capture["priority"]["events"][-1]["defense"]["yards"] = -4
    with pytest.raises(PenaltyEvidenceError, match="retained defensive operand"):
        _origin(capture["typed_capture"]["commands"][0], capture)


def test_option_tail_does_not_hide_pinned_row_disagreement():
    row, inventory = option_penalty_subject("BLP", "home")
    row["audit_capture"]["lookup_rows"]["events"][2]["facts"]["kind"] = "SOP"
    with pytest.raises(ReceiptAuditError):
        audit_receipt(row, lookup_inventory=inventory)
