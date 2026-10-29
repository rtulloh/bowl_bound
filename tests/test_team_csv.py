# ruff: noqa: E501, E701, E702, I001
from __future__ import annotations

from pathlib import Path

import pytest

from bowl_bound.models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    NormalizedCell,
    OffensiveCell,
    PatOutcome,
    Play,
    Provenance,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.team_csv import (
    PROVENANCE_DIR,
    TEAM_FILES,
    TeamFileMetadata,
    TeamFormatError,
    load_team,
    provenance_to_csv,
    team_from_files,
    team_to_files,
    team_folder_name,
    validate_team_name,
)

SHA = "a" * 64


def evidence(text: str = "source") -> Provenance:
    return Provenance(SHA, "synthetic.pdf", 1, BoundingBox(-0.0, 0.0, 1.0, 1.0), text, (1, 2, 3))


def chart(name: str = "Ohio State") -> TeamChart:
    cell = NormalizedCell(ResultKind.YARDS, evidence(), yards=1)
    return TeamChart(
        1,
        name,
        2026,
        tuple(OffensiveCell(p, r, cell) for p in Play for r in range(10, 40)),
        tuple(
            SupplementalCell(c, r, NormalizedCell(ResultKind.BREAKAWAY, evidence()))
            for c in SupplementalColumn
            for r in range(10, 40)
        ),
        tuple(DefensiveCell(d, p, r, cell) for d in Defense for p in Play for r in range(1, 6)),
        tuple(SpecialTeamsCell(c, r, cell) for c in SpecialTeamsColumn for r in range(10, 40)),
        tuple(PatOutcome(r, r % 2 == 0, evidence()) for r in range(10, 40)),
        range(10, 27),
    )


def metadata() -> TeamFileMetadata:
    return TeamFileMetadata(5.5, ("W",), "Buckeyes", SHA, (("rating", evidence("note")),))


def test_paydirt_layout_round_trip_and_positions() -> None:
    files = team_to_files(chart(), metadata())
    assert tuple(files) == TEAM_FILES
    assert files["offense.csv"].splitlines()[0] == (
        "#,Line Plunge,Counter,End Reverse,Draw,Option,Screen,Sprint Out,Boot-leg,Drop Back,B,QT,Fumble,QR"
    )
    assert len(files["offense.csv"].splitlines()) == 31
    row = files["offense.csv"].splitlines()[1].split(",")
    assert row[1:10] == ["1"] * 9 and row[10:13] == ["B", "B", "R"]
    assert team_from_files(files, provenance_to_csv(chart(), metadata())) == (chart(), metadata())


@pytest.mark.parametrize(
    "name", ["Ohio State", "Miami (Florida)", "Texas A&M", "St. John's", "Hawai'i", "49ers"]
)
def test_valid_team_names(name: str) -> None:
    assert validate_team_name(name) == name


@pytest.mark.parametrize(
    "name", ["", "..", "../x", "a/b", "a\\b", " x", "x.", "PROVENANCE", "a\x00b", "x" * 101]
)
def test_invalid_team_names(name: str) -> None:
    with pytest.raises(TeamFormatError):
        validate_team_name(name)


def test_yaml_is_strict_and_preserves_string_like_values() -> None:
    files = team_to_files(chart("2002"), metadata())
    assert "team_name: '2002'" in files["team.yaml"]
    bad = files["team.yaml"].replace("team_name:", "team_name: &x", 1)
    with pytest.raises(TeamFormatError):
        team_from_files({**files, "team.yaml": bad}, provenance_to_csv(chart("2002"), metadata()))


def _with_yaml(text_edit: object) -> dict[str, str]:
    files = team_to_files(chart(), metadata())
    return {**files, "team.yaml": text_edit(files["team.yaml"])}  # type: ignore[operator]


@pytest.mark.parametrize(
    "edit",
    [
        lambda y: y + "status: validated\n",  # duplicate key, last value must not win
        lambda y: y.replace("season: 2026", "season: 2026\nseason: 2003"),
        lambda y: y.replace("team_name: Ohio State", "<<: {team_name: Foo}\nteam_name: Ohio State"),
        lambda y: y.replace("team_file_version: 1", "team_file_version: true"),
        lambda y: y.replace("team_file_version: 1", "team_file_version: 1.0"),
    ],
)
def test_yaml_rejects_duplicate_keys_merge_keys_and_non_integer_versions(edit: object) -> None:
    files = _with_yaml(edit)
    with pytest.raises(TeamFormatError):
        team_from_files(files, provenance_to_csv(chart(), metadata()))


def test_all_fumbles_lost_is_a_format_error_not_a_bare_value_error() -> None:
    files = team_to_files(chart(), metadata())
    lines = files["offense.csv"].splitlines()
    header = lines[0].split(",")
    fumble = header.index("Fumble")
    edited = [lines[0]]
    for line in lines[1:]:
        cells = line.split(",")
        if cells[0].isdigit():
            cells[fumble] = "L"
        edited.append(",".join(cells))
    with pytest.raises(TeamFormatError):
        team_from_files(
            {**files, "offense.csv": "\n".join(edited) + "\n"},
            provenance_to_csv(chart(), metadata()),
        )


def test_huge_power_rating_is_a_format_error() -> None:
    files = _with_yaml(lambda y: y.replace("power_rating: 5.5", "power_rating: " + "1" + "0" * 400))
    with pytest.raises(TeamFormatError):
        team_from_files(files, provenance_to_csv(chart(), metadata()))


@pytest.mark.parametrize("season_name", ["+2002", "02002", " 2002", "٢٠٠٢", "2_002"])
def test_load_team_rejects_non_canonical_season_directory_names(
    tmp_path: Path, season_name: str
) -> None:
    season = tmp_path / season_name
    _write_team(season, "ohio-state")
    with pytest.raises(TeamFormatError):
        load_team(season, "ohio-state")


def test_load_team_refuses_a_symlinked_season_directory(tmp_path: Path) -> None:
    real = tmp_path / "real"
    _write_team(real / "2026", "ohio-state")
    link = tmp_path / "2026"
    link.symlink_to(real / "2026", target_is_directory=True)
    with pytest.raises(TeamFormatError):
        load_team(link, "ohio-state")


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Ohio State", "ohio-state"),
        ("Miami (Florida)", "miami-florida"),
        ("Texas A&M", "texas-a-m"),
        ("St. John's", "st-john-s"),
        ("Hawai'i", "hawai-i"),
        ("San José State", "san-jose-state"),
        ("49ers", "49ers"),
    ],
)
def test_team_folder_name_is_a_lowercase_hyphenated_slug(name: str, slug: str) -> None:
    assert team_folder_name(name) == slug


@pytest.mark.parametrize("name", ["", "..", "///", "---", "provenance", "PROVENANCE", "日本"])
def test_team_folder_name_rejects_unsafe_or_empty_names(name: str) -> None:
    with pytest.raises(TeamFormatError):
        team_folder_name(name)


@pytest.mark.parametrize("name", ["../../evil", "a/b", "a\\b", "/etc/passwd"])
def test_team_folder_name_never_contains_a_path_separator_or_dots(name: str) -> None:
    slug = team_folder_name(name)
    assert not set(slug) & set("/\\.") and slug == slug.strip("-")


@pytest.mark.parametrize("name", ["../../evil", "a/b", "a\\b", "/etc/passwd"])
def test_names_with_separators_are_still_refused_before_any_slug_is_used(name: str) -> None:
    with pytest.raises(TeamFormatError):
        validate_team_name(name)


def _write_team(season: Path, slug: str) -> None:
    folder = season / slug
    folder.mkdir(parents=True)
    for name, text in team_to_files(chart(), metadata()).items():
        (folder / name).write_text(text, encoding="utf-8", newline="")
    (season / PROVENANCE_DIR).mkdir(exist_ok=True)
    (season / PROVENANCE_DIR / f"{slug}.csv").write_text(
        provenance_to_csv(chart(), metadata()), encoding="utf-8", newline=""
    )


def test_load_team_uses_slug_folder_and_season_provenance_directory(tmp_path: Path) -> None:
    season = tmp_path / "2026"
    _write_team(season, "ohio-state")
    assert load_team(season, "ohio-state") == (chart(), metadata())
    with pytest.raises(TeamFormatError):
        load_team(season, "Ohio State")


def test_load_team_refuses_a_folder_that_belongs_to_another_team(tmp_path: Path) -> None:
    season = tmp_path / "2026"
    _write_team(season, "miami-florida")
    with pytest.raises(TeamFormatError):
        load_team(season, "miami-florida")
