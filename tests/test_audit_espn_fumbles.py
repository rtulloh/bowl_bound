"""Fictional controls for the separate-row ESPN source investigation."""

from copy import deepcopy

import pytest

from scripts.audit_espn_fumbles import audit_game, audit_snapshot, write_report


def pair(kind: str = "Rush") -> list[dict]:
    text = {
        "Rush": "Alex Example (CV) rushed up the middle for 3 yards.",
        "Sack": "Alex Example (CV) sacked for a loss of 3 yards.",
        "Pass Completion": "Casey Sample (CV) pass complete to Alex Example (CV) for 3 yards.",
    }[kind]
    common = {
        "drive": {"$ref": "https://example.test/drives/drive1"},
        "clock": {"displayValue": "10:00"},
        "period": {"number": 1},
        "start": {"team": {"$ref": "https://example.test/teams/1"}},
    }
    first = dict(deepcopy(common), id="p1", sequenceNumber="1", type={"text": kind}, text=text)
    second = dict(
        deepcopy(common),
        id="p2",
        sequenceNumber="2",
        type={"text": "Fumble Recovery (Own)"},
        text=(
            "Owls fumble by Alex Example (CV), recovered by Alex Example (CV), "
            "advanced for no gain."
        ),
    )
    return [first, second]


@pytest.mark.parametrize("kind", ["Rush", "Pass Completion", "Sack"])
def test_pairs_by_drive_sequence_even_when_response_order_is_reversed(kind: str) -> None:
    first, second = pair(kind)
    report = audit_game([second, first])
    assert report["counts"] == {"fumble_rows": 1, "matched_" + kind: 1}
    assert report["candidate_links"] == [{"primary": "p1", "recovery": "p2", "kind": kind}]
    assert report["negative_observations_established"] is False
    assert report["release_qualified"] is False


@pytest.mark.parametrize("mismatch", ["clock", "period", "team", "carrier", "drive"])
def test_disagreements_remain_unresolved(mismatch: str) -> None:
    first, second = pair()
    if mismatch == "clock":
        second["clock"]["displayValue"] = "9:59"
    elif mismatch == "period":
        second["period"]["number"] = 2
    elif mismatch == "team":
        second["start"]["team"]["$ref"] = "https://example.test/teams/2"
    elif mismatch == "carrier":
        second["text"] = second["text"].replace("Alex Example", "Taylor Sample")
    else:
        second["drive"]["$ref"] = "https://example.test/drives/drive2"
    report = audit_game([first, second])
    assert report["candidate_links"] == []
    assert len(report["unresolved"]) == 1
    assert report["unresolved"][0]["recovery"] == "p2"


def test_duplicate_predecessor_and_missing_clock_never_create_links() -> None:
    first, second = pair()
    duplicate = dict(first, id="duplicate")
    report = audit_game([first, duplicate, second])
    assert report["candidate_links"] == []
    assert report["unresolved"][0]["reason"] == "nonunique_or_missing_predecessor"
    first.pop("clock")
    second.pop("clock")
    assert audit_game([first, second])["candidate_links"] == []


def test_report_binds_source_and_refuses_public_or_existing_output(tmp_path) -> None:
    import hashlib
    import json

    source = tmp_path / "plays"
    source.mkdir()
    rows = pair()
    ordinary = dict(deepcopy(rows[0]), id="p3", sequenceNumber="3")
    path = source / "game1.json"
    raw = json.dumps({"items": [*rows, ordinary]}).encode()
    path.write_bytes(raw)
    report = audit_snapshot(source)
    assert report["sources"] == {"game1.json": hashlib.sha256(raw).hexdigest()}
    assert report["counts"]["matched_Rush"] == 1
    assert report["negative_observations_established"] is False
    assert path.read_bytes() == raw
    with pytest.raises(ValueError, match="private-data"):
        write_report(tmp_path / "public.json", report)
    output = tmp_path / "private-data" / "audit.json"
    write_report(output, report)
    assert json.loads(output.read_text()) == report
    with pytest.raises(FileExistsError):
        write_report(output, report)


def test_malformed_items_and_duplicate_play_ids_fail_instead_of_reporting_success() -> None:
    with pytest.raises(ValueError, match="play records"):
        audit_game([None])
    rows = pair()
    rows[1]["id"] = rows[0]["id"]
    with pytest.raises(ValueError, match="unique"):
        audit_game(rows)


def test_acquisition_raw_directory_selects_only_play_responses(tmp_path) -> None:
    import json

    (tmp_path / "plays-game1.json").write_text(json.dumps({"items": pair()}))
    (tmp_path / "events-2.json").write_text(json.dumps({"items": [{"$ref": "inventory"}]}))
    (tmp_path / "scoreboard-2002.json").write_text(json.dumps({"events": []}))
    report = audit_snapshot(tmp_path)
    assert set(report["sources"]) == {"plays-game1.json"}
    assert report["counts"]["matched_Rush"] == 1


def return_pair(family: str = "kickoff") -> list[dict]:
    """Build a return followed by recovery at the next drive boundary."""
    action, recovery = pair()
    action.update(
        sequenceNumber="7",
        type={"text": "Kickoff Return (Offense)" if family == "kickoff" else "Punt Return"},
        text=(
            "Kickoff returned by Alex Example (CV) for 25 yards."
            if family == "kickoff"
            else "Punt by Taylor Sample (HT), returned by Alex Example (CV) for 5 yards."
        ),
        drive={"$ref": "https://example.test/games/1/drives/1001"},
        end={"team": {"$ref": "https://example.test/teams/1"}, "yardLine": 25},
    )
    recovery.update(
        sequenceNumber="1",
        drive={"$ref": "https://example.test/games/1/drives/1002"},
        clock={"displayValue": "9:47"},
    )
    recovery["start"].update(yardLine=25, down=1)
    return [action, recovery]


@pytest.mark.parametrize("family", ["punt", "kickoff", "punt_muff"])
def test_cross_drive_return_fumbles_are_separate_from_primary_links(family: str) -> None:
    action, recovery = return_pair("punt" if family == "punt_muff" else family)
    if family == "punt_muff":
        action["text"] = "Punt by Taylor Sample (HT) no return by Owls."
        recovery["clock"] = deepcopy(action["clock"])
    before = deepcopy([action, recovery])
    report = audit_game([recovery, action])  # Array order is not chronology.
    assert report["unresolved"] == []
    assert report["candidate_links"] == []
    link = report["return_links"][0]
    assert link["return_play"] == "p1"
    assert link["recovery"] == "p2"
    assert link["family"] == ("punt_return" if family.startswith("punt") else "kickoff_return")
    assert link["muff_or_possessed_fumble"] == "unknown"
    assert link["source_truth_verified"] is False
    assert [action, recovery] == before


@pytest.mark.parametrize(
    "conflict", ["carrier", "owner", "period", "position", "time", "elapsed", "snap", "duplicate"]
)
def test_cross_drive_return_links_refuse_conflicting_or_ambiguous_evidence(conflict: str) -> None:
    action, recovery = return_pair()
    rows = [action, recovery]
    if conflict == "carrier":
        recovery["text"] = recovery["text"].replace("Alex Example", "Casey Sample")
    elif conflict == "owner":
        recovery["start"]["team"]["$ref"] = "https://example.test/teams/2"
    elif conflict == "period":
        recovery["period"]["number"] = 2
    elif conflict == "position":
        recovery["start"]["yardLine"] = 26
    elif conflict == "time":
        recovery["clock"]["displayValue"] = "10:01"
    elif conflict == "elapsed":
        recovery["clock"]["displayValue"] = "9:00"
    elif conflict == "snap":
        rows.append(dict(deepcopy(action), id="p3", sequenceNumber="8", type={"text": "Rush"}))
    else:
        rows.append(dict(deepcopy(action), id="p3"))
    report = audit_game(rows)
    assert report.get("return_links", []) == []
    assert len(report["unresolved"]) == 1


def test_unnamed_punt_requires_same_clock_and_explicit_no_return_text() -> None:
    action, recovery = return_pair("punt")
    action["text"] = "Punt by Taylor Sample (HT) no return by Owls."
    assert audit_game([action, recovery]).get("return_links", []) == []
    recovery["clock"] = deepcopy(action["clock"])
    action["text"] = "Punt by Taylor Sample (HT)."
    assert audit_game([action, recovery]).get("return_links", []) == []


@pytest.mark.parametrize("conflict", [None, "carrier", "owner", "snap", "clock"])
def test_interception_return_fumble_uses_interceptor_and_drive_boundary(
    conflict: str | None,
) -> None:
    action, recovery = return_pair()
    action.update(
        type={"text": "Pass Interception"},
        text="Casey Sample (HT) pass intercepted by Alex Example (CV). Returned for 15 yards.",
    )
    recovery["clock"] = deepcopy(action["clock"])
    rows = [recovery, action]
    if conflict == "carrier":
        recovery["text"] = recovery["text"].replace("Alex Example", "Casey Sample")
    elif conflict == "owner":
        recovery["start"]["team"]["$ref"] = "https://example.test/teams/2"
    elif conflict == "snap":
        rows.append(dict(deepcopy(action), id="p3", sequenceNumber="8", type={"text": "Rush"}))
    elif conflict == "clock":
        recovery["clock"]["displayValue"] = "9:20"
    report = audit_game(rows)
    assert len(report["return_links"]) == (0 if conflict else 1)
    if conflict is None:
        assert report["return_links"][0]["family"] == "interception_return"
        assert report["candidate_links"] == report["unresolved"] == []


@pytest.mark.parametrize("kind", ["Rush", "Pass Completion", "Sack"])
def test_same_clock_primary_fumble_can_cross_a_drive_boundary(kind: str) -> None:
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
    second.update(drive={"$ref": "https://example.test/games/1/drives/1002"}, sequenceNumber="1")
    second["start"].update(yardLine=33, down=2, distance=13)
    report = audit_game([second, first])
    assert report["candidate_links"] == [{"primary": "p1", "recovery": "p2", "kind": kind}]
    assert report["unresolved"] == []


@pytest.mark.parametrize("conflict", ["clock", "down", "distance", "yardLine", "carrier", "gain"])
def test_cross_drive_primary_requires_exact_end_context_and_carrier(conflict: str) -> None:
    first, second = pair("Sack")
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
    second.update(drive={"$ref": "https://example.test/games/1/drives/1002"}, sequenceNumber="1")
    second["start"].update(yardLine=33, down=2, distance=13)
    if conflict in {"down", "distance", "yardLine"}:
        second["start"][conflict] += 1
    elif conflict == "clock":
        second["clock"]["displayValue"] = "9:59"
    elif conflict == "carrier":
        second["text"] = second["text"].replace("Alex Example", "Taylor Sample")
    else:
        first.pop("statYardage")
    assert audit_game([first, second])["candidate_links"] == []
