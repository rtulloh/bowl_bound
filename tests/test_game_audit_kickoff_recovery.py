"""A recovery draw is distinct from the two routine kick/return lookups."""

from copy import deepcopy
from dataclasses import replace

import pytest

from bowl_bound.models import ResultKind
from tests import test_game_audit_kickoff as fixture
from tests.test_game_audit_row_links import frozen_inventory
from tools.game_audit_kickoff import audit_kickoff_commands
from tools.game_audit_lookup import LookupInventory


def inventory(*, fumble: bool = False) -> LookupInventory:
    """Literal synthetic kickoff support; no engine outcome supplies expectations."""
    value = frozen_inventory()
    for team in value["teams"]:
        team.update(team_id="2007/" + team["team_id"].split("/")[-1], season=2007)
    for record in value["cells"]:
        address = record["address"]
        address.update(team_id="2007/" + address["team_id"].split("/")[-1], season=2007)
        if address["table"] == "special_teams":
            if address["column"] == "kickoff":
                record["facts"]["yards"] = 50
            elif address["column"] == "kickoff_return":
                record["facts"].update(
                    kind="fumble" if fumble else "yards", yards=0 if fumble else 12
                )
    return LookupInventory(value)


def test_numeric_kickoff_remains_checked() -> None:
    row, _ = fixture.kickoff_subject()
    result = audit_kickoff_commands(row["audit_capture"], inventory=inventory())
    assert result["checked"] == 1
    assert result["unknown"] == 0


def test_numeric_return_extra_draw_remains_a_refusal() -> None:
    row, _ = fixture.kickoff_subject()
    capture = deepcopy(row["audit_capture"])
    capture["typed_capture"]["commands"][1]["draw_range"][1] += 1
    with pytest.raises(ValueError, match="draw/row exposure"):
        audit_kickoff_commands(capture, inventory=inventory())


def test_actual_fumble_return_recovery_is_unknown_not_routine_draw_failure(monkeypatch) -> None:
    original = fixture.subject_teams

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

    monkeypatch.setattr(fixture, "subject_teams", fumble_teams)
    _, capture = fixture.kickoff_subject(return_yards=0, return_game=True)
    command = capture["typed_capture"]["commands"][1]
    assert command["draw_range"][1] - command["draw_range"][0] == 3
    assert command["returned_report"]["outcome"] == "kick_recovery"
    assert command["returned_report"]["supported"] is True
    result = audit_kickoff_commands(capture, inventory=inventory(fumble=True))
    assert result["checked"] == 0
    assert result["unknown"] == 1
    assert result["dispositions"][1]["reason"] == "return_terminal_authority"
