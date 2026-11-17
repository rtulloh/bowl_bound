"""PBP-only location reconstruction uses original fictional source sequences."""

from dataclasses import replace

import pytest

from tools.chartgen.evidence import Event, classify_espn


def sequence() -> list[Event]:
    rows = [
        {
            "id": "int",
            "game_play_number": 10,
            "type.text": "Pass Interception",
            "pass": True,
            "int": True,
            "yds_int_return": 10,
            "start.yardsToEndzone": 70,
            "end.team.id": 2,
            "end.yardsToEndzone": 55,
        },
        {"id": "admin", "game_play_number": None, "type.text": "Timeout"},
        {
            "id": "next",
            "game_play_number": 11,
            "type.text": "Rush",
            "rush": True,
            "pos_team_id": 2,
            "def_pos_team_id": 1,
            "start.yardsToEndzone": 55,
            "yds_rushed": 3,
        },
    ]
    events = []
    for row in rows:
        event = classify_espn(
            {
                "season": 2007,
                "game_id": "fictional-game",
                "pos_team_id": 1,
                "def_pos_team_id": 2,
                "text": "Fictional source evidence.",
                **row,
            }
        )
        assert event is not None
        events.append(event)
    return events


def test_verified_end_return_and_next_snap_reconstruct_interception_location() -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    enriched, diagnostics = enrich_interception_locations(rows)
    event = enriched[0]
    assert event.interception_yards == 35  # start x30, return ends x55, catch x65
    assert "next-event:next" in event.location_evidence
    assert "end-return-next-snap" in event.location_evidence
    assert diagnostics["reconstructed"] == 1
    assert Event.from_dict(event.to_dict()) == event
    reversed_events, _ = enrich_interception_locations(list(reversed(rows)))
    assert {e.event_id: e for e in reversed_events} == {e.event_id: e for e in enriched}


@pytest.mark.parametrize(
    "interception,next_play",
    [
        ({"end_yards_to_goal": 45}, {}),  # mirrored rather than next-snap matched
        ({"end_team": "1"}, {}),
        ({"end_yards_to_goal": -1}, {}),
        ({"return_yards": None}, {}),
        ({"penalty": True}, {}),
        ({"fumble": True}, {}),
        ({"touchdown": True}, {}),
        ({"source_text": "Interception, touchback."}, {}),
        ({}, {"team": "1", "opponent": "2"}),
        ({}, {"game_id": "different-actual-game"}),
        ({}, {"season": 2008}),
        ({}, {"source_sequence": 12}),
        ({}, {"source_sequence": 10}),
        ({}, {"source_sequence": None}),
        ({}, {"no_play": True, "penalty": True}),
    ],
)
def test_unverified_sequence_is_unknown_without_zero_substitution(
    interception: dict[str, object], next_play: dict[str, object]
) -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    rows[0] = replace(rows[0], **interception)
    rows[2] = replace(rows[2], **next_play)
    enriched, diagnostics = enrich_interception_locations(rows)
    assert enriched[0].interception_yards is None
    assert diagnostics["unidentified"] == 1


def test_declined_penalty_does_not_invalidate_live_location_evidence() -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    rows[0] = replace(rows[0], penalty=True, penalty_declined=True)
    enriched, _ = enrich_interception_locations(rows)
    assert enriched[0].interception_yards == 35


def test_explicit_air_yards_conflict_requires_source_reconciliation() -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    rows[0] = replace(
        rows[0], air_yards=12, interception_yards=12, location_evidence=("air_yards",)
    )
    with pytest.raises(ValueError, match="interception location.*conflict"):
        enrich_interception_locations(rows)


def test_valid_zero_location_is_distinct_from_an_unidentified_location() -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    rows[0] = replace(rows[0], yards_to_goal=35)  # catch x65 is exactly the LOS
    enriched, _ = enrich_interception_locations(rows)
    assert enriched[0].interception_yards == 0


def test_conflicting_explicit_spot_fields_are_rejected_without_a_successor() -> None:
    from tools.chartgen.locations import enrich_interception_locations

    event = replace(sequence()[0], air_yards=12, interception_yards=35)
    with pytest.raises(ValueError, match="interception location.*conflict"):
        enrich_interception_locations([event])


def test_fumble_owner_identity_is_not_assigned_from_original_possession() -> None:
    event = classify_espn(
        {
            "season": 2007,
            "game_id": "g",
            "id": "e",
            "pos_team_id": 1,
            "def_pos_team_id": 2,
            "type.text": "Punt",
            "punt": True,
            "text": "Fictional punt return fumble.",
            "fumble_vec": True,
            "fumbling_team": 2,
            "fumble_recovery_team": 1,
        }
    )
    assert event is not None and event.fumble_team == "2"
    assert event.recovery_team is None and event.provider_recovery_team == "1"
    assert event.recovery_confidence == "provider-inferred"


@pytest.mark.parametrize(
    "changes",
    [
        {"penalty": True},
        {"no_play": True},
        {"source_type": "End Spot Correction"},
    ],
)
def test_field_changing_admin_rows_are_not_skipped(changes: dict[str, object]) -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    rows[1] = replace(rows[1], **changes)
    enriched, _ = enrich_interception_locations(rows)
    assert enriched[0].interception_yards is None


def test_repeated_source_identity_requires_reconciliation() -> None:
    from tools.chartgen.locations import enrich_interception_locations

    rows = sequence()
    rows[2] = replace(rows[2], event_id=rows[0].event_id)
    with pytest.raises(ValueError, match="duplicate.*identity"):
        enrich_interception_locations(rows)
