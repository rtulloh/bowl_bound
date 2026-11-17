"""Independent synthetic totals distinguish source consistency from certification."""

from typing import Any

import pytest

from tools.chartgen.evidence import Event, classify_espn, summarize_events
from tools.chartgen.refine import source_targets
from tools.chartgen.source import coverage_report


def _row(event_id: str, label: str, **facts: Any) -> dict[str, Any]:
    return {
        "season": 2007,
        "game_id": "synthetic-game",
        "id": event_id,
        "pos_team_id": "a",
        "def_pos_team_id": "b",
        "type.text": label,
        "text": "",
        **facts,
    }


@pytest.mark.parametrize("void_flag", ["penalty_no_play", "penalty_negated_play", "penalty_offset"])
def test_source_int_sack_fga_totals_use_live_primary_events_and_college_denominators(
    void_flag: str,
) -> None:
    rows = [
        _row("rush", "Rush", rush=True, yds_rushed=5),
        _row("complete", "Pass Completion", pass_attempt=True, completion=True, yds_receiving=8),
        _row("incomplete", "Pass Incompletion", pass_attempt=True),
        _row("int", "Interception", pass_attempt=True, int=True),
        # Providers can mark sacks as pass attempts and rushes simultaneously.
        _row("sack1", "Sack", pass_attempt=True, rush=True, sack=True, yds_sacked=5),
        _row("sack2", "Sack", pass_attempt=True, sack=True, yds_sacked=3),
        _row("fg1", "Field Goal Good", fg_attempt=True, yds_fg=30, fg_made=True),
        _row("fg2", "Field Goal Missed", fg_attempt=True, yds_fg=40, fg_made=False),
        _row("fg3", "Blocked Field Goal", fg_attempt=True, yds_fg=45, fg_made=False),
        _row("void-int", "Interception", int=True, **{void_flag: True}),
        _row("void-sack", "Sack", sack=True, yds_sacked=9, **{void_flag: True}),
        _row("void-fg", "Field Goal Good", fg_attempt=True, yds_fg=20, **{void_flag: True}),
        _row("try-int", "Two-Point Pass Interception", int=True, pass_attempt=True),
    ]
    events = [classify_espn(row) for row in rows]
    assert all(isinstance(event, Event) for event in events)
    summary = summarize_events(events, "a")
    assert summary["interceptions"] == 1
    assert summary["sacks"] == 2
    assert summary["event_counts"]["field_goal"] == 3
    assert summary["pass_attempts"] == 3
    assert summary["rush_attempts"] == 3
    assert summary["rush_yards"] == -3
    targets = source_targets(events, ["a"])
    assert targets["completion"] == pytest.approx(1 / 3)
    assert targets["interception"] == pytest.approx(1 / 3)
    assert targets["sack"] == pytest.approx(2 / 5)
    assert targets["pure_rush_yards_per_attempt"] == 5
    assert targets["pass_yards_per_attempt"] == pytest.approx(8 / 3)
    # Even correct source-derived counters do not supply independent totals.
    report = coverage_report(events, "a", expected_games=["synthetic-game"])
    assert not report["official_totals_supplied"]
    assert not report["historical_reconciliation_passed"]


def test_unlocated_conflicting_fg_row_does_not_create_a_pass_or_invent_distance() -> None:
    row = _row(
        "conflict",
        "Pass Incompletion",
        pass_attempt=True,
        fg_attempt=True,
        fg_made=False,
    )
    event = classify_espn(row)
    assert event is not None and event.kind == "field_goal" and event.yards is None
    assert event.kick_good is False
    summary = summarize_events([event], "a")
    assert summary["event_counts"]["field_goal"] == 1
    assert summary["pass_attempts"] == 0
    assert summary["unknown_yardage"] == 1
