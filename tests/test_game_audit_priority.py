"""Pure JSON symbolic-priority corruption controls, independent of engine code."""

from copy import deepcopy

import pytest

from tests.test_game_receipt_audit import receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


def fact(kind: str = "yards", yards: int | None = 7, **changes: object) -> dict:
    result = dict(
        kind=kind,
        yards=yards,
        variable=None,
        variable_multiplier=None,
        priority="normal",
        out_of_bounds=False,
        penalty=None,
    )
    result.update(changes)
    return result


def priority_receipt() -> dict:
    row = receipt()
    row["audit_capture"] = dict(
        priority=dict(
            version="1",
            events=[
                dict(
                    number=1,
                    offense=fact(),
                    defense=fact(yards=-2),
                    result=dict(
                        operation="ADD",
                        source="both",
                        kind="yards",
                        yards=5,
                        pending=False,
                        offense_category="positive",
                        defense_category="negative",
                        out_of_bounds=False,
                        penalty=None,
                        defensive_end_zone_depth=None,
                    ),
                )
            ],
        )
    )
    event = row["audit_capture"]["priority"]["events"][0]
    event["result"].update(offense=deepcopy(event["offense"]), defense=deepcopy(event["defense"]))
    return row


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation", "O"),
        ("source", "offense"),
        ("kind", "incomplete"),
        ("yards", 7),
        ("pending", True),
        ("out_of_bounds", True),
        ("offense_category", "blank"),
        ("defense_category", "positive"),
        ("defensive_end_zone_depth", 1),
        ("penalty", {"team": "offense"}),
    ],
)
def test_priority_corruption_is_not_hidden_by_correct_final_accounting(
    field: str,
    value: object,
) -> None:
    row = priority_receipt()
    row["audit_capture"]["priority"]["events"][0]["result"][field] = value
    with pytest.raises(ReceiptAuditError, match=f"priority event 1.*{field}"):
        audit_receipt(row)


@pytest.mark.parametrize(
    "change",
    [
        dict(kind="mystery"),
        dict(yards=True),
        dict(priority="unknown"),
        dict(out_of_bounds=1),
        dict(kind="no_change", yards=7),
    ],
)
def test_invalid_typed_priority_operands_fail_closed(change: dict) -> None:
    row = priority_receipt()
    row["audit_capture"]["priority"]["events"][0]["offense"].update(change)
    with pytest.raises(ReceiptAuditError, match="priority event 1.*offense"):
        audit_receipt(row)


def test_symbolic_check_does_not_claim_lookup_or_full_game_resolution() -> None:
    row = priority_receipt()
    original = deepcopy(row)
    result = audit_receipt(row)
    assert result["components"]["symbolic_priority"] == "GO"
    assert result["coverage"]["symbolic_priority"] == dict(checked=1, excluded=0, unknown=0)
    assert result["components"]["chart_priority_and_cells"] == "UNVERIFIED"
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False
    assert row == original


@pytest.mark.parametrize("version,events", [("future", [{}]), ("1", []), ("1", None)])
def test_priority_contract_version_and_nonempty_inventory_are_required(
    version: str,
    events: object,
) -> None:
    row = priority_receipt()
    row["audit_capture"]["priority"].update(version=version, events=events)
    with pytest.raises(ReceiptAuditError, match="priority evidence"):
        audit_receipt(row)


@pytest.mark.parametrize("numbers", [[True], [0], [2], [1, 1], [1, 3]])
def test_priority_event_identity_must_be_contiguous_integer(numbers: list) -> None:
    row = priority_receipt()
    event = row["audit_capture"]["priority"]["events"][0]
    row["audit_capture"]["priority"]["events"] = [
        dict(deepcopy(event), number=number) for number in numbers
    ]
    with pytest.raises(ReceiptAuditError, match="priority event.*identity"):
        audit_receipt(row)


def test_missing_priority_result_field_is_not_a_default() -> None:
    row = priority_receipt()
    del row["audit_capture"]["priority"]["events"][0]["result"]["pending"]
    with pytest.raises(ReceiptAuditError, match="priority event 1.*pending"):
        audit_receipt(row)


def coordinate_facts(label: str, variant: str = "") -> dict:
    """Synthetic JSON representatives; no engine constructor or classifier."""
    values = {
        "positive_yards_or_breakaway": fact(),
        "positive_yards": fact(yards=4),
        "negative_yards": fact(yards=-3),
        "blank": fact("no_change", None),
        "parenthesized_positive": fact(yards=6, priority="parenthesized"),
        "parenthesized_negative": fact(yards=-2, priority="parenthesized"),
        "bracketed_positive": fact(yards=8, priority="bracketed"),
        "bracketed_negative": fact(yards=-5, priority="bracketed"),
        "touchdown": fact("touchdown", None),
        "quarterback_run": fact("QR", None),
        "quarterback_trapped": fact("QT", None),
        "interception": fact("interception", 12),
        "fumble": fact("fumble", 9),
        "incomplete": fact("incomplete", None),
        "sprint_out_or_bootleg_pass": fact("SOP", None),
        "penalty": fact(
            "penalty",
            None,
            penalty=dict(
                team="offense",
                code="S",
                yards=None,
                variable=None,
                variable_multiplier=None,
            ),
        ),
    }
    value = values[label]
    if variant in {"B", "BLP"}:
        value.update(kind=variant, yards=None)
    elif variant:
        value["priority"] = variant
    return value


def coordinates() -> list:
    from tests.priority_matrix import COLUMNS, PRIORITY_MATRIX, ROWS

    cases = []
    for row, label in enumerate(ROWS):
        variants = ("", "B") if row == 0 else (("", "BLP") if row == 10 else ("",))
        for column, defensive in enumerate(COLUMNS):
            decorations = ("parenthesized", "bracketed") if column == 7 else ("",)
            for variant in variants:
                for decoration in decorations:
                    cases.append(
                        (
                            coordinate_facts(label, variant),
                            coordinate_facts(defensive, decoration),
                            PRIORITY_MATRIX[row][column],
                        )
                    )
    return cases


@pytest.mark.parametrize("offense,defense,operation", coordinates())
def test_every_independently_transcribed_coordinate(
    offense: dict,
    defense: dict,
    operation: str,
) -> None:
    from tools.game_audit_priority import expected_priority

    assert expected_priority(offense, defense)["operation"] == operation


@pytest.mark.parametrize(
    "offense,defense,expected",
    [
        (
            fact(yards=7, priority="parenthesized"),
            fact(yards=-2, priority="parenthesized"),
            dict(operation="O", yards=7, out_of_bounds=False),
        ),
        (
            fact(yards=7, priority="parenthesized", out_of_bounds=True),
            fact(yards=-2, priority="bracketed"),
            dict(operation="D", yards=-2, out_of_bounds=False),
        ),
        (
            fact(),
            fact(yards=-2, out_of_bounds=True),
            dict(operation="ADD", yards=5, out_of_bounds=True),
        ),
        (fact("interception", 12), fact("QR", None), dict(operation="QT", kind="QT", pending=True)),
        (
            fact("interception", 12),
            fact(yards=-2, priority="bracketed"),
            dict(operation="INT_MIN", yards=-2, pending=True),
        ),
        (fact("fumble", -5), fact("fumble", -3), dict(operation="F_MIN", yards=-5)),
        (
            fact("fumble", 9),
            fact("touchdown", None),
            dict(operation="F_ENDZONE", yards=None, defensive_end_zone_depth=1),
        ),
        (fact("B", None), fact("incomplete", None), dict(operation="INC", pending=False)),
        (
            fact("variable_ds", None, variable="DS", variable_multiplier=1),
            fact(yards=-2),
            dict(operation="ADD", kind=None, yards=None, pending=True),
        ),
        (fact("SOP", None), fact("B", None, priority="parenthesized"), dict(operation="OPTION")),
        (
            fact(yards=0, priority="parenthesized"),
            fact("B", None, priority="parenthesized"),
            dict(operation="O", yards=0),
        ),
    ],
)
def test_literal_signed_location_bounds_and_branch_rules(
    offense: dict,
    defense: dict,
    expected: dict,
) -> None:
    from tools.game_audit_priority import expected_priority

    result = expected_priority(offense, defense)
    assert {key: result[key] for key in expected} == expected


def test_nested_penalty_boolean_does_not_equal_integer_distance() -> None:
    row = priority_receipt()
    event = row["audit_capture"]["priority"]["events"][0]
    penalty = dict(team="offense", code="fixed", yards=1, variable=None, variable_multiplier=None)
    event["offense"] = fact("penalty", None, penalty=penalty)
    event["result"].update(
        operation="PENALTY",
        source="offense",
        kind="penalty",
        yards=None,
        pending=True,
        offense_category="PENALTY",
        penalty=dict(penalty, yards=True),
        offense=deepcopy(event["offense"]),
    )
    with pytest.raises(ReceiptAuditError, match="priority event 1.*penalty"):
        audit_receipt(row)


@pytest.mark.parametrize("change", [dict(priority=[]), dict(variable=[], variable_multiplier=1)])
def test_unhashable_typed_fact_is_a_concrete_event_failure(change: dict) -> None:
    row = priority_receipt()
    row["audit_capture"]["priority"]["events"][0]["offense"].update(change)
    with pytest.raises(ReceiptAuditError, match="priority event 1.*offense"):
        audit_receipt(row)


@pytest.mark.parametrize("side", ["offense", "defense"])
def test_result_cannot_substitute_its_retained_original_operand(side: str) -> None:
    row = priority_receipt()
    row["audit_capture"]["priority"]["events"][0]["result"][side]["yards"] = 99
    with pytest.raises(ReceiptAuditError, match=f"priority event 1.*{side}"):
        audit_receipt(row)
