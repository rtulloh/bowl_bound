"""Core API examples are fictional and exercise explicit source unknowns."""

from pathlib import Path

import pytest

from tools.chartgen.espn_core import normalize_game


@pytest.mark.parametrize("kind", ["Rush", "Pass Completion", "Sack"])
def test_cross_drive_primary_fumble_keeps_primary_gain_and_source_facts(kind: str) -> None:
    from tests.test_audit_espn_fumbles import pair
    from tools.chartgen.generate import _primary_fumble

    first, second = pair(kind)
    first.update(
        drive={"$ref": "https://example.test/games/1/drives/1001"},
        statYardage=-3,
        end={
            "team": {"$ref": "https://example.test/teams/1"},
            "yardLine": 33,
            "down": 2,
            "distance": 13,
        },
    )
    second.update(
        drive={"$ref": "https://example.test/games/1/drives/1002"},
        sequenceNumber="1",
        statYardage=59,
        team={"$ref": "https://example.test/teams/2"},
    )
    second["start"].update(yardLine=33, down=2, distance=13)
    events, report = normalize_game(
        [first, second],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    action, recovery = events
    assert action.fumble is True
    assert action.yards == -3
    assert action.fumble_team == "1"
    assert action.recovery_team == "2"
    assert action.fumble_lost is True
    assert action.optional_flag_observations[0].value is None
    assert _primary_fumble(action)
    assert recovery.no_play is True
    assert recovery.source_text == second["text"]
    assert report["primary_fumbles"]["links"] == [{"primary": "p1", "recovery": "p2", "kind": kind}]
    from tools.chartgen.espn_core import enrich_primary_fumbles

    assert enrich_primary_fumbles(events, [first, second]) == (events, report["primary_fumbles"])


@pytest.mark.parametrize("adapter_version", [1, 2, 3])
def test_previous_core_receipts_remain_readable(tmp_path: Path, adapter_version: int) -> None:
    from tools.chartgen.espn_core import source_receipt
    from tools.chartgen.source import read_normalized, write_normalized

    events, _ = normalize_game(
        [play("Rush")],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    receipt = source_receipt(events, {"g1": "a" * 64})
    receipt["adapter"] = f"espn-core-v2-conservative-v{adapter_version}"
    receipt.pop("primary_fumble_policy")
    if adapter_version == 1:
        receipt.pop("return_fumble_policy")
    elif adapter_version == 2:
        receipt["return_fumble_policy"] = "espn-cross-drive-return-fumble-v1"
    path = tmp_path / "old-source.json"
    write_normalized(path, events, receipt)
    assert read_normalized(path) == (events, receipt)


def test_interception_return_fumble_preserves_interception_and_owner(tmp_path: Path) -> None:
    from tests.test_audit_espn_fumbles import return_pair
    from tools.chartgen.espn_core import enrich_return_fumbles, source_receipt
    from tools.chartgen.evidence import summarize_events
    from tools.chartgen.generate import _primary_fumble
    from tools.chartgen.source import read_normalized, write_normalized

    action, recovery = return_pair()
    action.update(
        type={"text": "Pass Interception"},
        text="Casey Sample (HT) pass intercepted by Alex Example (CV). Returned for 15 yards.",
        statYardage=0,
    )
    action["start"]["team"]["$ref"] = "https://example.test/teams/2"
    recovery["team"] = {"$ref": "https://example.test/teams/2"}
    recovery["clock"] = dict(action["clock"])
    events, report = normalize_game(
        [action, recovery],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    interception, duplicate = events
    assert interception.kind == "interception"
    assert interception.return_yards == 15
    assert interception.team == "2"
    assert interception.fumble_team == "1"
    assert interception.fumble is True
    assert interception.fumble_lost is True
    assert interception.optional_flag_observations[0].value is None
    assert not _primary_fumble(interception)
    assert duplicate.no_play is True
    assert duplicate.event_phase == "scrimmage"
    assert summarize_events(events, "1")["fumbles_lost"] == 1
    assert summarize_events(events, "2")["fumbles"] == 0
    assert summarize_events(events, "2")["interceptions"] == 1
    assert enrich_return_fumbles(events, [action, recovery]) == (events, report["return_fumbles"])
    path = tmp_path / "source.json"
    receipt = source_receipt(events, {"g1": "a" * 64})
    write_normalized(path, events, receipt)
    assert read_normalized(path) == (events, receipt)


@pytest.mark.parametrize("family", ["kickoff", "punt", "punt_muff"])
def test_cross_drive_return_fumble_reaches_generator_once_with_source_lineage(
    tmp_path: Path, family: str
) -> None:
    from tests.test_audit_espn_fumbles import return_pair
    from tools.chartgen.espn_core import enrich_return_fumbles, source_receipt
    from tools.chartgen.generate import EvidenceModel, _primary_fumble
    from tools.chartgen.source import read_normalized, write_normalized

    rows = return_pair("punt" if family == "punt_muff" else family)
    rows[0]["start"]["team"]["$ref"] = "https://example.test/teams/2"
    rows[0]["statYardage"] = 25
    rows[1]["team"] = {"$ref": "https://example.test/teams/2"}
    if family == "punt_muff":
        rows[0]["text"] = "Punt by Taylor Sample (HT) no return by Owls."
        rows[1]["clock"] = dict(rows[0]["clock"])
    events, report = normalize_game(
        rows,
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    action, recovery = events
    assert action.kind == ("kickoff" if family == "kickoff" else "punt")
    assert action.fumble is True
    assert action.fumble_team == "1" == action.opponent
    assert action.recovery_team == "2"
    assert action.return_yards == (None if family == "punt_muff" else 25)
    assert action.yards is None
    assert not _primary_fumble(action)
    assert action.optional_flag_observations[0].value is None
    assert "linked-recovery:p2" in action.recovery_evidence
    assert recovery.no_play is True
    assert recovery.fumble is True  # Retained evidence, omitted duplicate fitting record.
    model = EvidenceModel.from_events(events)
    assert sum(e.fumble is True for e in model.live) == 1
    from tools.chartgen.evidence import summarize_events

    receiving = summarize_events(events, "1")
    kicking = summarize_events(events, "2")
    assert (receiving["fumbles"], receiving["fumbles_lost"]) == (1, 1)
    assert (kicking["fumbles"], kicking["fumbles_lost"]) == (0, 0)
    assert receiving["scrimmage_fumbles"] == kicking["scrimmage_fumbles"] == 0
    assert report["return_fumbles"]["links"][0]["family"] == action.kind + "_return"
    repeated, repeated_report = enrich_return_fumbles(events, rows)
    assert repeated == events
    assert repeated_report == report["return_fumbles"]
    path = tmp_path / "normalized.json"
    source = source_receipt(events, {"g1": "a" * 64})
    write_normalized(path, events, source)
    assert read_normalized(path) == (events, source)


def test_linked_return_positive_cannot_make_unknown_returns_a_100_percent_fumble_rate() -> None:
    from dataclasses import replace

    import pytest

    from tools.chartgen.evidence import Event
    from tools.chartgen.generate import _return_fumble_probability

    positive = Event(
        2002,
        "g1",
        "p1",
        "2",
        "1",
        "Harbor Tech",
        "Cedar Valley",
        "kickoff",
        None,
        fumble=True,
        fumble_team="1",
        return_yards=25,
    )
    unknown = replace(positive, event_id="p2", fumble=None, fumble_team=None)
    with pytest.raises(ValueError, match="positive-only return fumble"):
        _return_fumble_probability([positive, unknown], 1.0)
    negative = replace(unknown, fumble=False)
    assert _return_fumble_probability([positive, negative], 1.0) == 0.5
    assert _return_fumble_probability([positive], 1.0) == 1.0


def test_core_snapshot_roundtrip_binds_each_games_raw_bytes(tmp_path) -> None:
    import hashlib
    import json

    import pytest

    from tools.chartgen.espn_core import source_receipt
    from tools.chartgen.source import read_normalized, write_normalized

    events, _ = normalize_game(
        [play("Rush")],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    source = source_receipt(events, {"g1": "a" * 64})
    path = tmp_path / "normalized.json"
    write_normalized(path, events, source)
    assert read_normalized(path) == (events, source)
    document = json.loads(path.read_text())
    document["source"]["game_source_sha256"]["g1"] = "b" * 64
    # Even a repinned source inventory cannot substitute evidence for the events.
    document["source"]["raw_sha256"] = hashlib.sha256(
        json.dumps(
            document["source"]["game_source_sha256"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="core source"):
        read_normalized(path)


def play(label: str, yards: int | None = 9) -> dict:
    return {
        "id": "g1p1",
        "sequenceNumber": "3",
        "type": {"id": "5", "text": label},
        "text": "Fictional play",
        "statYardage": yards,
        "start": {
            "team": {"$ref": "https://example.test/teams/1"},
            "down": 2,
            "distance": 4,
            "yardsToEndzone": 0,
        },
        "end": {"team": {"$ref": "https://example.test/teams/1"}},
        "period": {"number": 1},
        "clock": {"displayValue": "10:00"},
    }


def test_core_rush_preserves_yards_and_missing_optional_flags() -> None:
    events, receipt = normalize_game(
        [play("Rush")],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert len(events) == 1
    assert (events[0].team, events[0].opponent, events[0].yards) == ("1", "2", 9)
    assert events[0].fumble is None
    assert events[0].yards_to_goal is None  # Old feed's constant zero is not field position.
    assert events[0].optional_flag_source_sha256 == "a" * 64
    assert receipt["source_rows"] == 1


def test_core_return_yardage_is_never_gross_kick_yardage() -> None:
    row = play("Punt Return", 12)
    row["team"] = {"$ref": "https://example.test/teams/2"}
    events, _ = normalize_game(
        [row],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert events[0].kind == "punt"
    assert events[0].team == "1"
    assert events[0].yards is None
    assert events[0].return_yards == 12


def test_core_unknown_possession_is_counted_and_not_guessed() -> None:
    row = play("Rush")
    row["start"] = {}
    events, receipt = normalize_game(
        [row],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert not events
    assert receipt["excluded_unknown_possession"] == 1


def test_core_missing_rush_yards_remain_unknown() -> None:
    events, _ = normalize_game(
        [play("Rush", None)],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert events[0].yards is None


def test_core_rush_scoring_flag_marks_touchdown() -> None:
    row = play("Rush", 9)
    row.update(scoringPlay=True, scoreValue=6)
    events, _ = normalize_game(
        [row],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert events[0].touchdown is True


def test_core_missing_type_keeps_explicit_field_goal_evidence() -> None:
    row = play("", 39)
    row["type"] = {}
    row["text"] = "39 yard field goal by Fictional Kicker is good."
    events, _ = normalize_game(
        [row],
        season=2002,
        game_id="g1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert (events[0].kind, events[0].yards, events[0].kick_good) == ("field_goal", 39, True)


def test_core_interception_spot_requires_corroborating_next_snap() -> None:
    first = play("Pass Interception", 0)
    first["text"] = "Fictional pass intercepted. Returned for no gain."
    first["start"]["yardLine"] = 30
    first["end"] = {
        "team": {"$ref": "https://example.test/teams/2"},
        "yardLine": 70,
        "yardsToEndzone": 70,
    }
    following = play("Rush", 4)
    following["id"] = "g1p2"
    following["start"].update(team={"$ref": "https://example.test/teams/2"}, yardLine=70)
    following["end"] = {
        "team": {"$ref": "https://example.test/teams/2"},
        "yardLine": 66,
        "yardsToEndzone": 66,
    }
    events, _ = normalize_game(
        [first, following],
        season=2002,
        game_id="g1",
        home_team="1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert events[0].interception_yards == 40
    assert "next-event:g1p2" in events[0].location_evidence
    following["start"]["yardLine"] = 69
    disputed, _ = normalize_game(
        [first, following],
        season=2002,
        game_id="g1",
        home_team="1",
        teams={"1": "Cedar Valley", "2": "Harbor Tech"},
        source_sha256="a" * 64,
    )
    assert disputed[0].interception_yards is None
