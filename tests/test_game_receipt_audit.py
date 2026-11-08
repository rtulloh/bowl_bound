"""Synthetic mutation controls for the independent retained-event observer."""

from copy import deepcopy

import pytest

from tools.game_audit import ReceiptAuditError, audit_receipt


def empty_totals():
    return dict(
        rushing_attempts=0,
        rushing_yards=0,
        rushing_touchdowns=0,
        passing_attempts=0,
        completions=0,
        passing_yards=0,
        passing_touchdowns=0,
        interceptions=0,
        sacks_taken=0,
        sack_yards_lost=0,
        total_plays=0,
        total_yards=0,
    )


def event(number, kind="rush", team="home", yards=5, outcome="advance"):
    return dict(
        number=number,
        supported=True,
        pending=False,
        outcome=outcome,
        called_play="1",
        resolved_play="1",
        yards=yards,
        state_before=dict(possession="home", possession_name="Synthetic Home", yards_to_goal=65),
        state_after=dict(possession="away", possession_name="Synthetic Away"),
        timing=dict(conversion=False),
        trace=[],
        description="irrelevant prose",
        statistics=dict(kind=kind, team=team, yards=yards, touchdown=False),
    )


def receipt():
    home, away = empty_totals(), empty_totals()
    home.update(rushing_attempts=1, rushing_yards=5, total_plays=1, total_yards=5)
    return dict(
        status="passed",
        engine_log=[event(1)],
        final=dict(
            finished=True,
            statistics=dict(home=home, away=away),
            home_score=0,
            away_score=0,
            scoring=[],
        ),
    )


def box_rows():
    return [
        dict(label=label, home=home, away="0")
        for label, home in (
            ("Rushing attempts", "1"),
            ("Rushing yards", "5"),
            ("Rushing touchdowns", "0"),
            ("Pass attempts", "0"),
            ("Completions", "0"),
            ("Passing yards", "0"),
            ("Passing touchdowns", "0"),
            ("Interceptions thrown", "0"),
            ("Sacks taken", "0"),
            ("Sack yards lost", "0"),
            ("Total offensive plays", "1"),
            ("Total offense yards", "5"),
        )
    ]


def test_ownership_is_checked_before_matching_aggregate_totals():
    row = receipt()
    row["engine_log"][0]["statistics"]["team"] = "away"
    row["final"]["statistics"]["home"], row["final"]["statistics"]["away"] = (
        row["final"]["statistics"]["away"],
        row["final"]["statistics"]["home"],
    )
    with pytest.raises(ReceiptAuditError, match="report 1.*ownership"):
        audit_receipt(row)


@pytest.mark.parametrize("outcome", ["pre_snap", "offsetting"])
def test_voided_play_cannot_receive_credit(outcome):
    row = receipt()
    row["engine_log"][0]["outcome"] = outcome
    with pytest.raises(ReceiptAuditError, match="report 1.*excluded"):
        audit_receipt(row)


def test_conversion_credit_is_rejected():
    row = receipt()
    row["engine_log"][0]["timing"]["conversion"] = True
    with pytest.raises(ReceiptAuditError, match="report 1.*excluded"):
        audit_receipt(row)


@pytest.mark.parametrize("changes", [dict(team="home"), dict(yards=1), dict(touchdown=True)])
def test_excluded_credit_has_no_team_yards_or_touchdown(changes):
    row = receipt()
    row["engine_log"][0]["statistics"] = dict(
        kind="excluded", team=None, yards=0, touchdown=False, **{}
    )
    row["engine_log"][0]["statistics"].update(changes)
    with pytest.raises(ReceiptAuditError, match="report 1.*excluded"):
        audit_receipt(row)


def test_final_totals_are_folded_without_engine_statistics_helpers():
    row = receipt()
    assert audit_receipt(row)["components"]["final_statistics"] == "GO"
    row["final"]["statistics"]["home"]["rushing_yards"] += 1
    with pytest.raises(ReceiptAuditError, match="final.*rushing_yards"):
        audit_receipt(row)


def test_sacks_are_negative_rushing_attempts_and_incomplete_passes_have_no_yards():
    row = receipt()
    report = row["engine_log"][0]
    report["statistics"].update(kind="sack", yards=-3)
    row["final"]["statistics"]["home"].update(
        rushing_yards=-3, sacks_taken=1, sack_yards_lost=3, total_yards=-3
    )
    assert audit_receipt(row)["components"]["final_statistics"] == "GO"
    report["statistics"].update(kind="incomplete", yards=3)
    with pytest.raises(ReceiptAuditError, match="report 1.*incomplete"):
        audit_receipt(row)


def test_accepted_previous_and_end_choices_bind_the_credit_rule():
    row = receipt()
    row["engine_log"][0]["outcome"] = "penalty_accepted"
    row["audit_capture"] = dict(decisions=[dict(report_number=1, choice="accept:0:previous")])
    with pytest.raises(ReceiptAuditError, match="report 1.*previous"):
        audit_receipt(row)
    row["audit_capture"]["decisions"][0]["choice"] = "accept:0:end"
    assert audit_receipt(row)["components"]["accepted_voided_statistics"] == "GO"
    row["engine_log"][0]["statistics"]["yards"] = 15
    with pytest.raises(ReceiptAuditError, match="report 1.*underlying gain"):
        audit_receipt(row)


def test_absent_penalty_choice_and_halftime_are_unverified():
    row = receipt()
    row["engine_log"][0]["outcome"] = "penalty_accepted"
    report = audit_receipt(row)
    assert report["components"]["accepted_voided_statistics"] == "UNVERIFIED"
    assert report["unverified_penalty_reports"] == [1]
    assert report["components"]["halftime"] == "UNVERIFIED"
    assert report["full_play_by_play_qualification"] is False


def test_absent_accepted_penalties_are_not_observed_coverage():
    assert audit_receipt(receipt())["components"]["accepted_voided_statistics"] == "NOTRUN"


def test_halftime_prefix_totals_and_box_rows_are_independent():
    row = receipt()
    row["audit_capture"] = dict(
        halftime=[
            dict(
                report_number=1,
                score=dict(home=0, away=0),
                statistics=deepcopy(row["final"]["statistics"]),
                recap=dict(
                    home=dict(first=0, second=0, total=0),
                    away=dict(first=0, second=0, total=0),
                    statistics=box_rows(),
                ),
            )
        ]
    )
    assert audit_receipt(row)["components"]["halftime"] == "GO"
    row["audit_capture"]["halftime"][0]["recap"]["statistics"][1]["home"] = "6"
    with pytest.raises(ReceiptAuditError, match="halftime.*Rushing yards"):
        audit_receipt(row)


def test_score_points_and_credited_touchdown_ownership_are_checked():
    row = receipt()
    row["final"]["scoring"] = [
        dict(number=1, play_number=1, team="Synthetic Away", kind="touchdown", points=6)
    ]
    row["final"]["away_score"] = 6
    row["engine_log"][0]["statistics"]["touchdown"] = True
    with pytest.raises(ReceiptAuditError, match="report 1.*touchdown"):
        audit_receipt(row)


def test_prose_does_not_control_audit_decisions():
    row = receipt()
    expected = audit_receipt(row)
    row["engine_log"][0]["description"] = "penalty previous spot touchdown fumble accepted"
    assert audit_receipt(row) == expected


def test_incomplete_game_is_not_a_completed_receipt():
    row = receipt()
    row["final"]["finished"] = False
    with pytest.raises(ReceiptAuditError, match="completed"):
        audit_receipt(row)


def test_empty_report_receipt_cannot_pass_accounting():
    row = receipt()
    row["engine_log"] = []
    row["final"]["statistics"] = dict(home=empty_totals(), away=empty_totals())
    with pytest.raises(ReceiptAuditError, match="no retained reports"):
        audit_receipt(row)


@pytest.mark.parametrize("reports", [None, {}, (event(1),)])
def test_report_inventory_must_be_a_list(reports):
    row = receipt()
    row["engine_log"] = reports
    with pytest.raises(ReceiptAuditError, match="retained reports"):
        audit_receipt(row)


@pytest.mark.parametrize("number", [0, 2])
def test_orphan_acceptance_capture_is_rejected(number):
    row = receipt()
    row["audit_capture"] = dict(decisions=[dict(report_number=number, choice="accept:0:previous")])
    with pytest.raises(ReceiptAuditError, match="capture.*report"):
        audit_receipt(row)


def test_acceptance_capture_must_refer_to_a_penalty_acceptance():
    row = receipt()
    row["audit_capture"] = dict(decisions=[dict(report_number=1, choice="accept:0:previous")])
    with pytest.raises(ReceiptAuditError, match="capture.*penalty"):
        audit_receipt(row)


def test_orphan_halftime_capture_is_rejected():
    row = receipt()
    row["audit_capture"] = dict(halftime=[dict(report_number=2)])
    with pytest.raises(ReceiptAuditError, match="halftime.*boundary"):
        audit_receipt(row)
