"""Synthetic source contracts; no historical files or network access."""

import pytest

from tools.chartgen.evidence import Event, classify_espn, summarize_events


def row(**changes: object) -> dict[str, object]:
    return {
        "season": 2007,
        "game_id": "synthetic-1",
        "id": "p1",
        "pos_team_id": 1,
        "def_pos_team_id": 2,
        "pos_team": "Cedar Valley",
        "def_pos_team": "Harbor Tech",
        "type.text": "Rush",
        "rush": True,
        "statYardage": 7,
        "yds_rushed": 7,
        "text": "Runner rush for 7 yards.",
        **changes,
    }


def test_generic_run_does_not_invent_designed_call() -> None:
    event = classify_espn(row())
    assert event is not None and event.kind == "rush" and event.yards == 7
    assert event.called_family is None and event.family_confidence == "unknown"


def test_scoring_yardage_and_explicit_screen_are_preserved() -> None:
    event = classify_espn(
        row(
            **{
                "type.text": "Passing Touchdown",
                "rush": False,
                "pass": True,
                "completion": True,
                "pass_attempt": True,
                "yds_receiving": 42,
                "statYardage": 42,
                "text": "Screen pass complete for 42 yards, touchdown.",
                "touchdown": True,
            }
        )
    )
    assert event is not None and event.yards == 42 and event.touchdown
    assert event.called_family == 6 and event.family_confidence == "narrative"


def test_missing_yards_stay_unknown_and_are_diagnostic() -> None:
    event = classify_espn(row(yds_rushed=None, statYardage=None))
    assert event is not None and event.yards is None
    summary = summarize_events([event], "1")
    assert summary["unknown_yardage"] == 1
    assert summary["rush_yards"] == 0 and summary["rush_yardage_samples"] == 0


def test_no_play_and_declined_penalties_remain_distinct() -> None:
    no_play = classify_espn(row(penalty_no_play=True, penalty_flag=True))
    declined = classify_espn(row(penalty_declined=True, penalty_flag=True))
    assert no_play is not None and no_play.no_play
    assert declined is not None and declined.penalty_declined and not declined.no_play
    summary = summarize_events([no_play, declined], "1")
    assert summary["rush_attempts"] == 1


def test_sacks_use_college_rush_credit_without_double_counting() -> None:
    sack = classify_espn(
        row(
            **{
                "type.text": "Sack",
                "rush": False,
                "pass": True,
                "pass_attempt": False,
                "sack": True,
                "yds_sacked": -8,
                "statYardage": -8,
            }
        )
    )
    assert sack is not None and sack.kind == "sack" and sack.yards == -8
    summary = summarize_events([sack], "1")
    assert summary["rush_attempts"] == 1 and summary["rush_yards"] == -8
    assert summary["pass_attempts"] == 0 and summary["sacks"] == 1


def test_infinite_or_fractional_yardage_rejected() -> None:
    with pytest.raises(ValueError, match="integer"):
        classify_espn(row(yds_rushed=2.5))


def test_event_round_trip_preserves_turnover_and_clock_facts() -> None:
    event = classify_espn(
        row(fumble_vec=True, fumble_lost=True, recovery_team="2", **{"clock.displayValue": "12:21"})
    )
    assert event is not None and Event.from_dict(event.to_dict()) == event
    assert event.fumble and event.fumble_lost and event.recovery_team == "2"


def test_explicit_original_pat_result_beats_unpopulated_derived_flags() -> None:
    good = classify_espn(
        row(
            **{
                "type.text": "Extra Point Good",
                "xp_attempt": False,
                "xp_made": False,
                "rush": False,
            }
        )
    )
    missed = classify_espn(
        row(**{"type.text": "Extra Point Missed", "xp_made": None, "rush": False})
    )
    assert good is not None and good.kind == "pat" and good.kick_good is True
    assert missed is not None and missed.kick_good is False


def test_accepted_no_play_penalty_counted_without_offensive_credit() -> None:
    event = classify_espn(row(penalty_no_play=True, penalty_flag=True))
    assert event is not None
    summary = summarize_events([event], "1")
    assert summary["rush_attempts"] == 0
    assert summary["penalties"] == 1


def test_scrimmage_and_special_fumbles_have_separate_denominators() -> None:
    rush = classify_espn(row(fumble_vec=True))
    punt = classify_espn(
        row(
            **{
                "id": "p2",
                "type.text": "Punt",
                "punt_play": True,
                "rush": False,
                "yds_punted": 40,
                "fumble_vec": True,
            }
        )
    )
    assert rush is not None and punt is not None
    totals = summarize_events([rush, punt], "1")
    assert totals["fumbles"] == 2 and totals["scrimmage_fumbles"] == 1


@pytest.mark.parametrize(
    "text,flags",
    [
        ("Punt for 40 yards, touchback.", {"punt_tb": True}),
        ("Punt for 40 yards, fair catch.", {"punt_fair_catch": True}),
        ("Punt for 40 yards, downed.", {"punt_downed": True}),
    ],
)
def test_non_returns_do_not_become_zero_yard_return_observations(text: str, flags: dict) -> None:
    event = classify_espn(
        row(
            **{
                "type.text": "Punt",
                "punt_play": True,
                "rush": False,
                "yds_punted": 40,
                "yds_punt_return": 0,
                "text": text,
                **flags,
            }
        )
    )
    assert event is not None and event.return_yards is None


def test_explicit_zero_yard_return_is_retained() -> None:
    event = classify_espn(
        row(
            **{
                "type.text": "Punt",
                "punt_play": True,
                "rush": False,
                "yds_punted": 40,
                "yds_punt_return": 0,
                "text": "Punt for 40 yards, Player returns for no gain.",
            }
        )
    )
    assert event is not None and event.return_yards == 0


def test_missing_fumble_flags_stay_unknown() -> None:
    event = classify_espn(row())
    assert event is not None and event.fumble is None
    totals = summarize_events([event], "1")
    assert totals["fumble_unknown_samples"] == 1


def test_normalized_boolean_strings_rejected() -> None:
    event = classify_espn(row())
    assert event is not None
    value = event.to_dict() | {"no_play": "false"}
    with pytest.raises(ValueError, match="boolean"):
        Event.from_dict(value)


def test_kick_ownership_swap_preserves_matching_display_names() -> None:
    event = classify_espn(
        row(
            **{
                "type.text": "Kickoff",
                "kickoff_play": True,
                "kicking_team": "2",
                "def_pos_team": "Harbor Tech",
                "yds_kickoff": 60,
                "rush": False,
            }
        )
    )
    assert event is not None and event.team == "2" and event.opponent == "1"
    assert event.team_name == "Harbor Tech" and event.opponent_name == "Cedar Valley"
