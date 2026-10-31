"""Synthetic Milestone 9b roster tests. Names are invented; no historical rosters."""

import json
import os
from pathlib import Path
from random import Random

import pytest

from bowl_bound.dice import RandomDice
from bowl_bound.roster import (
    POSITIONS,
    Roster,
    RosterFormatError,
    load_roster,
    parse_roster,
    player_name,
    roster_to_json,
)

SAMPLE = {
    "qb": ["Alex Quill", "Sam Rook"],
    "rb": ["Ray Bolt"],
    "wr": ["Wes Reed", "Walt Finch"],
    "te": ["Tom Edge"],
    "ol": ["Olin Post", "Otto Wall", "Owen Gate", "Ollie Rock", "Orrin Slab"],
    "dl": ["Dean Lock"],
    "lb": ["Lee Brandt"],
    "db": ["Dale Cover", "Dax Hawk"],
    "k": ["Kip Boot"],
    "p": ["Pat Punt"],
    "kr": ["Rex Return"],
}


def text(data: object) -> str:
    return json.dumps(data)


def test_positions_match_the_paydirt_format() -> None:
    assert POSITIONS == ("qb", "rb", "wr", "te", "ol", "dl", "lb", "db", "k", "p", "kr")


def test_sample_roster_loads_and_round_trips() -> None:
    roster = parse_roster(text(SAMPLE))
    assert isinstance(roster, Roster)
    assert roster.players["qb"] == ("Alex Quill", "Sam Rook")
    assert json.loads(roster_to_json(roster)) == SAMPLE
    assert parse_roster(roster_to_json(roster)) == roster


def test_verified_starter_lists_drive_commentary_name_rotation() -> None:
    data = {
        **SAMPLE,
        "qb": ["Alex Quill", "Sam Rook", "Pat Reserve"],
        "rb": ["Ray Bolt", "Rex Backup"],
        "starters": {"qb": ["Sam Rook", "Alex Quill"]},
    }
    roster = parse_roster(text(data))

    assert player_name(roster, "qb", 0) == "Sam Rook"
    assert player_name(roster, "qb", 1) == "Alex Quill"
    assert player_name(roster, "qb", 2) == "Sam Rook"
    assert player_name(roster, "rb", 0) == "Ray Bolt"
    assert player_name(roster, "rb", 1) == "Rex Backup"
    assert parse_roster(roster_to_json(roster)) == roster


@pytest.mark.parametrize(
    "starters",
    [
        None,
        [],
        {"coach": ["ZZ-Secret-Player"]},
        {"quarterback": ["ZZ-Secret-Player"]},
        {"qb": "ZZ-Secret-Player"},
        {"qb": ["ZZ-Secret-Player"]},
        {"qb": ["Alex Quill", "Alex Quill"]},
    ],
)
def test_invalid_starter_metadata_is_rejected_without_echoing_names(starters: object) -> None:
    secret = "ZZ-Secret-Player"
    with pytest.raises(RosterFormatError) as info:
        parse_roster(text({**SAMPLE, "starters": starters}))
    assert secret not in str(info.value)


def test_missing_positions_are_empty_not_errors() -> None:
    roster = parse_roster(text({"qb": ["Alex Quill"]}))
    assert roster.players["rb"] == ()
    assert json.loads(roster_to_json(roster)) == {"qb": ["Alex Quill"]}


def test_empty_object_is_a_valid_empty_roster() -> None:
    assert all(not names for names in parse_roster("{}").players.values())


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "[]",
        '"qb"',
        "null",
        "{",
        '{"qb": "Alex Quill"}',
        '{"qb": [1]}',
        '{"qb": [null]}',
        '{"qb": [""]}',
        '{"qb": ["   "]}',
        '{"qb": [" Alex Quill"]}',
        '{"qb": ["Alex\\nQuill"]}',
        '{"qb": ["Alex\\u0000Quill"]}',
        '{"qb": ["Alex Quill", "Alex Quill"]}',
        '{"qb": ["' + "x" * 101 + '"]}',
        '{"qb": ["Alex Quill"], "coach": ["Pat Lead"]}',
        '{"QB": ["Alex Quill"]}',
        '{"qb": ["Alex Quill"], "qb": ["Sam Rook"]}',
        '{"qb": ["Alex Quill"], "rb": NaN}',
        '{"qb": ["a"], "rb": ' + text([f"n{i}" for i in range(61)]) + "}",
    ],
)
def test_malformed_rosters_are_rejected(bad: str) -> None:
    with pytest.raises(RosterFormatError):
        parse_roster(bad)


def test_non_string_input_is_rejected() -> None:
    with pytest.raises(RosterFormatError):
        parse_roster(None)  # type: ignore[arg-type]
    with pytest.raises(RosterFormatError):
        parse_roster(b"{}")  # type: ignore[arg-type]


def test_errors_never_echo_values() -> None:
    secret = "ZZ-Secret-Player"
    for bad in (
        text({"qb": [secret, secret]}),
        text({"qb": [secret], secret: ["x"]}),
        text({"qb": [secret + "\n"]}),
    ):
        with pytest.raises(RosterFormatError) as info:
            parse_roster(bad)
        assert secret not in str(info.value)


def test_missing_roster_falls_back_to_generic_wording() -> None:
    assert player_name(None, "qb") == "the quarterback"
    assert player_name(None, "ol") == "the offensive lineman"
    assert player_name(parse_roster("{}"), "kr") == "the kick returner"
    for position in POSITIONS:
        assert player_name(None, position).startswith("the ")


def test_player_name_is_deterministic_and_wraps_without_randomness() -> None:
    roster = parse_roster(text(SAMPLE))
    assert player_name(roster, "qb", 0) == "Alex Quill"
    assert player_name(roster, "qb", 1) == "Sam Rook"
    assert player_name(roster, "qb", 2) == "Alex Quill"
    assert player_name(roster, "qb", 0) == player_name(roster, "qb", 0)


@pytest.mark.parametrize("bad", ["quarterback", "", None, 3])
def test_unknown_position_is_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        player_name(None, bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-1, True, "0", 1.5])
def test_invalid_index_is_rejected(bad: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        player_name(None, "qb", bad)  # type: ignore[arg-type]


def test_naming_never_consumes_or_perturbs_the_gameplay_random_stream() -> None:
    roster = parse_roster(text(SAMPLE))
    with_names = RandomDice(Random(2002))
    without_names = RandomDice(Random(2002))
    first = [with_names.offensive(), with_names.defensive()]
    for position in POSITIONS:
        player_name(roster, position, 3)
        player_name(None, position, 3)
    first += [with_names.offensive(), with_names.defensive()]
    second = [
        without_names.offensive(),
        without_names.defensive(),
        without_names.offensive(),
        without_names.defensive(),
    ]
    assert first == second


def make_team_folder(root: Path, season: str = "2002", slug: str = "ohio-state") -> Path:
    folder = root / season / slug
    folder.mkdir(parents=True)
    return folder


def test_load_roster_reads_the_file_beside_the_team(tmp_path: Path) -> None:
    folder = make_team_folder(tmp_path)
    (folder / "roster.json").write_text(text(SAMPLE), encoding="utf-8")
    roster = load_roster(tmp_path / "2002", "ohio-state")
    assert roster is not None and roster.players["qb"][0] == "Alex Quill"


def test_load_roster_returns_none_when_no_file_exists(tmp_path: Path) -> None:
    make_team_folder(tmp_path)
    assert load_roster(tmp_path / "2002", "ohio-state") is None


def test_load_roster_rejects_a_malformed_file_instead_of_ignoring_it(tmp_path: Path) -> None:
    folder = make_team_folder(tmp_path)
    (folder / "roster.json").write_text('{"coach": []}', encoding="utf-8")
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / "2002", "ohio-state")


def test_load_roster_rejects_non_utf8_and_bom(tmp_path: Path) -> None:
    folder = make_team_folder(tmp_path)
    (folder / "roster.json").write_bytes(b"\xff\xfe{}")
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / "2002", "ohio-state")
    (folder / "roster.json").write_bytes(b"\xef\xbb\xbf{}")
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / "2002", "ohio-state")


def test_load_roster_refuses_symlinks(tmp_path: Path) -> None:
    folder = make_team_folder(tmp_path)
    target = tmp_path / "elsewhere.json"
    target.write_text(text(SAMPLE), encoding="utf-8")
    os.symlink(target, folder / "roster.json")
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / "2002", "ohio-state")


def test_load_roster_refuses_oversized_files(tmp_path: Path) -> None:
    folder = make_team_folder(tmp_path)
    (folder / "roster.json").write_text(" " * 200_000 + "{}", encoding="utf-8")
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / "2002", "ohio-state")


@pytest.mark.parametrize("slug", ["Ohio State", "../x", "ohio/state", "", "provenance"])
def test_load_roster_requires_a_canonical_folder_name(tmp_path: Path, slug: str) -> None:
    make_team_folder(tmp_path)
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / "2002", slug)


@pytest.mark.parametrize("season", ["02002", "abc", "0", "-1"])
def test_load_roster_requires_a_canonical_season_folder(tmp_path: Path, season: str) -> None:
    make_team_folder(tmp_path, season=season)
    with pytest.raises(RosterFormatError):
        load_roster(tmp_path / season, "ohio-state")


def test_same_seed_gives_identical_play_and_state_with_and_without_a_roster() -> None:
    from dataclasses import replace

    from bowl_bound.game_state import Possession, apply_result, start_drive
    from bowl_bound.models import Defense, NormalizedCell, Play, ResultKind
    from bowl_bound.resolution import resolve_play
    from tests.test_models import complete_chart, provenance

    chart = complete_chart()
    gain = NormalizedCell(ResultKind.YARDS, provenance(), yards=6)
    chart = replace(
        chart,
        offense=tuple(replace(r, cell=gain) for r in chart.offense),
        defense=tuple(replace(r, cell=gain) for r in chart.defense),
    )
    roster = parse_roster(text(SAMPLE))

    def run(use_roster: bool) -> tuple[object, object, str]:
        dice = RandomDice(Random(1983))
        state = start_drive(Possession.HOME, 60)
        wording = []
        outcomes = []
        for _ in range(3):
            play = resolve_play(chart, chart, Play.ONE, Defense.A, dice)
            transition = apply_result(state, play.result)
            outcomes.append((play.result.yards, play.trace[0].roll, play.trace[1].roll))
            wording.append(player_name(roster if use_roster else None, "rb", len(outcomes)))
            state = transition.state or state
        return outcomes, state, " ".join(wording)

    with_roster = run(True)
    without_roster = run(False)
    assert with_roster[0] == without_roster[0]
    assert with_roster[1] == without_roster[1]
    assert with_roster[2] != without_roster[2]
