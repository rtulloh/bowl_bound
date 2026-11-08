"""Synthetic typed lookup/dice evidence; no engine is an expectation oracle."""

from copy import deepcopy
from itertools import product

import pytest

from tests.test_game_receipt_audit import receipt
from tools.game_audit import ReceiptAuditError, audit_receipt


def facts(yards=7):
    return dict(
        kind="yards",
        yards=yards,
        variable=None,
        variable_multiplier=None,
        priority="normal",
        out_of_bounds=False,
        penalty=None,
        chart_color="white",
    )


def address(table="offense", *, roll=10, play=1, column=None, formation=None):
    return dict(
        team_id="synthetic",
        season=2007,
        table=table,
        play=play,
        column=column,
        formation=formation,
        roll=roll,
    )


def inventory():
    cells = []
    for play, roll in product(range(1, 10), range(10, 40)):
        cells.append(dict(address=address(roll=roll, play=play), facts=facts()))
    for column, roll in product(("B", "QR", "QT"), range(10, 40)):
        cells.append(
            dict(
                address=address("supplemental", roll=roll, play=None, column=column), facts=facts()
            )
        )
    for formation, play, roll in product("ABCDEF", range(1, 10), range(1, 6)):
        cells.append(
            dict(
                address=address("defense", roll=roll, play=play, formation=formation),
                facts=facts(-1),
            )
        )
    for column, roll in product(
        ("kickoff", "kickoff_return", "punt", "punt_return", "field_goal", "interception_return"),
        range(10, 40),
    ):
        cells.append(
            dict(
                address=address("special_teams", roll=roll, play=None, column=column), facts=facts()
            )
        )
    for roll in range(10, 40):
        cells.append(dict(address=address("pat", roll=roll, play=None), facts=dict(good=True)))
    return dict(version="1", teams=[dict(team_id="synthetic", season=2007)], cells=cells)


def evidence():
    return dict(
        version="1",
        draws=[
            dict(
                number=1,
                kind="offensive",
                faces=dict(black=1, white_one=0, white_two=0),
                total=10,
                direct_sum=1,
            )
        ],
        events=[dict(number=1, draw_number=1, address=address(), facts=facts())],
    )


def audited(observed, frozen=None):
    row = receipt()
    row["audit_capture"] = dict(lookup=observed)
    return audit_receipt(row, lookup_inventory=inventory() if frozen is None else frozen)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("draw", "number", True),
        ("draw", "number", 2),
        ("draw", "kind", "unknown"),
        ("draw", "total", 11),
        ("draw", "total", True),
        ("draw", "direct_sum", 10),
        ("event", "number", True),
        ("event", "number", 2),
        ("event", "draw_number", 2),
        ("event", "draw_number", True),
        ("address", "team_id", "foreign"),
        ("address", "season", 2008),
        ("address", "play", 2),
        ("address", "play", True),
        ("address", "roll", 11),
        ("address", "formation", "A"),
        ("facts", "yards", 8),
        ("facts", "out_of_bounds", True),
        ("facts", "chart_color", "yellow"),
        ("facts", "yards", True),
        ("faces", "white_one", 5),
        ("faces", "black", True),
    ],
)
def test_corrupt_physical_or_typed_lookup_evidence_is_rejected(target, field, value):
    observed = evidence()
    selected = dict(
        draw=observed["draws"][0],
        event=observed["events"][0],
        address=observed["events"][0]["address"],
        facts=observed["events"][0]["facts"],
        faces=observed["draws"][0]["faces"],
    )[target]
    frozen = inventory()
    if target == "address" and field == "play" and value == 2:
        frozen["cells"][30]["facts"] = facts(8)
    selected[field] = value
    with pytest.raises(ReceiptAuditError, match="lookup"):
        audited(observed, frozen)


def test_supplied_lookup_without_external_inventory_is_not_trusted():
    row = receipt()
    row["audit_capture"] = dict(lookup=evidence())
    with pytest.raises(ReceiptAuditError, match="lookup.*inventory"):
        audit_receipt(row)


def test_lookup_pass_only_covers_supplied_facts_and_leaves_capture_unverified():
    observed, frozen = evidence(), inventory()
    original = deepcopy((observed, frozen))
    result = audited(observed, frozen)
    assert result["components"]["typed_lookup_agreement"] == "GO"
    assert result["components"]["supplied_physical_draws"] == "GO"
    assert result["components"]["chart_priority_and_cells"] == "UNVERIFIED"
    assert result["lookup_counts"] == dict(
        draws_checked=1, lookups_checked=1, draws_without_lookup=0
    )
    assert result["full_play_by_play_qualification"] is False
    assert result["accuracy_qualification"] is False
    assert (observed, frozen) == original


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_unused",
        "duplicate",
        "duplicate_team",
        "unknown_team",
        "empty_teams",
        "empty_cells",
        "version",
        "bool_season",
        "missing_facts",
        "extra_facts",
        "unknown_kind",
        "bool_pat",
    ],
)
def test_incomplete_or_malformed_frozen_inventory_is_rejected(mutation):
    frozen = inventory()
    if mutation == "missing_unused":
        frozen["cells"].pop()
    elif mutation == "duplicate":
        frozen["cells"].append(deepcopy(frozen["cells"][0]))
    elif mutation == "duplicate_team":
        frozen["teams"] *= 2
    elif mutation == "unknown_team":
        frozen["cells"][-1]["address"]["team_id"] = "foreign"
    elif mutation == "empty_teams":
        frozen["teams"] = []
    elif mutation == "empty_cells":
        frozen["cells"] = []
    elif mutation == "version":
        frozen["version"] = "999"
    elif mutation == "bool_season":
        frozen["teams"][0]["season"] = True
    elif mutation == "missing_facts":
        del frozen["cells"][-2]["facts"]["good"]
    elif mutation == "extra_facts":
        frozen["cells"][0]["facts"]["original_text"] = "not an oracle"
    elif mutation == "unknown_kind":
        frozen["cells"][0]["facts"]["kind"] = "unsupported"
    else:
        frozen["cells"][-1]["facts"]["good"] = 1
    with pytest.raises(ReceiptAuditError, match="lookup"):
        audited(evidence(), frozen)


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_draws",
        "empty_events",
        "version",
        "duplicate_draw",
        "duplicate_event",
        "missing_face",
        "extra_face",
        "wrong_kind",
        "missing_fact",
        "bad_penalty_type",
        "bad_variable_type",
    ],
)
def test_lookup_inventory_and_fact_shapes_fail_closed(mutation):
    observed = evidence()
    if mutation == "empty_draws":
        observed["draws"] = []
    elif mutation == "empty_events":
        observed["events"] = []
    elif mutation == "version":
        observed["version"] = "999"
    elif mutation == "duplicate_draw":
        observed["draws"] *= 2
    elif mutation == "duplicate_event":
        observed["events"] *= 2
    elif mutation == "missing_face":
        del observed["draws"][0]["faces"]["white_two"]
    elif mutation == "extra_face":
        observed["draws"][0]["faces"]["blue"] = 1
    elif mutation == "wrong_kind":
        observed["draws"][0] = dict(number=1, kind="defensive", faces=dict(red=1, green=0), total=1)
    elif mutation == "missing_fact":
        del observed["events"][0]["facts"]["priority"]
    elif mutation == "bad_penalty_type":
        observed["events"][0]["facts"]["penalty"] = dict(
            team="offense", code="fixed", yards=True, variable=None, variable_multiplier=None
        )
    else:
        observed["events"][0]["facts"]["variable"] = []
    with pytest.raises(ReceiptAuditError, match="lookup"):
        audited(observed)


def test_all_216_offensive_and_36_defensive_physical_combinations_have_correct_mass():
    from collections import Counter

    observed = dict(version="1", draws=[], events=[])
    offensive_mass, defensive_mass = Counter(), Counter()
    # Literal independent expectations, not production dice constants or roll helpers.
    for black, one, two in product((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5)):
        number = len(observed["draws"]) + 1
        total = 10 * black + one + two
        offensive_mass[total] += 1
        observed["draws"].append(
            dict(
                number=number,
                kind="offensive",
                faces=dict(black=black, white_one=one, white_two=two),
                total=total,
                direct_sum=black + one + two,
            )
        )
        observed["events"].append(
            dict(number=number, draw_number=number, address=address(roll=total), facts=facts())
        )
    for red, green in product((1, 1, 1, 2, 2, 3), (0, 0, 0, 0, 1, 2)):
        number = len(observed["draws"]) + 1
        total = red + green
        defensive_mass[total] += 1
        observed["draws"].append(
            dict(number=number, kind="defensive", faces=dict(red=red, green=green), total=total)
        )
        observed["events"].append(
            dict(
                number=number,
                draw_number=number,
                address=address("defense", roll=total, formation="F"),
                facts=facts(-1),
            )
        )
    assert [offensive_mass[i] for i in range(10, 40)] == [
        2,
        3,
        4,
        5,
        6,
        6,
        4,
        3,
        2,
        1,
        4,
        6,
        8,
        10,
        12,
        12,
        8,
        6,
        4,
        2,
        6,
        9,
        12,
        15,
        18,
        18,
        12,
        9,
        6,
        3,
    ]
    assert defensive_mass == {1: 12, 2: 11, 3: 9, 4: 3, 5: 1}
    assert audited(observed)["lookup_counts"] == dict(
        draws_checked=252, lookups_checked=252, draws_without_lookup=0
    )


def test_one_physical_draw_may_support_multiple_chart_lookups_or_no_chart_lookup():
    observed = evidence()
    observed["events"].append(
        dict(
            number=2,
            draw_number=1,
            address=address("supplemental", play=None, column="B"),
            facts=facts(),
        )
    )
    observed["draws"].append(dict(number=2, kind="defensive", faces=dict(red=3, green=2), total=5))
    assert audited(observed)["lookup_counts"] == dict(
        draws_checked=2, lookups_checked=2, draws_without_lookup=1
    )


@pytest.mark.parametrize(
    "table,column", [("supplemental", "QT"), ("special_teams", "punt"), ("pat", None)]
)
def test_other_table_axes_are_checked_without_deciding_their_gameplay(table, column):
    observed = evidence()
    observed["events"][0]["address"] = address(table, play=None, column=column)
    if table == "pat":
        observed["events"][0]["facts"] = dict(good=True)
    assert audited(observed)["lookup_counts"]["lookups_checked"] == 1


def test_compiled_inventory_is_detached_from_mutable_input():
    from tools.game_audit_lookup import LookupInventory

    frozen = inventory()
    compiled = LookupInventory(frozen)
    frozen["cells"][0]["facts"]["yards"] = 100
    assert audited(evidence(), compiled)["components"]["typed_lookup_agreement"] == "GO"
