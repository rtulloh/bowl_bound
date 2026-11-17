"""Synthetic season and position controls for historical roster acquisition."""

from pathlib import Path

import pytest

from scripts.acquire_rosters import parse_roster_page


def page(title: str = "2002 Football Roster", position: str = "QB") -> str:
    return (
        f"<title>{title}</title><table><tr><th>Name</th><th>Pos.</th></tr>"
        f"<tr><td><a>Alex Example</a></td><td>{position}</td></tr>"
        "<tr><td>Casey Sample</td><td>RB/KR</td></tr></table>"
    )


def test_parser_uses_explicit_positions_and_keeps_return_roles() -> None:
    roster, report = parse_roster_page(page(), 2002)
    assert roster == {"qb": ["Alex Example"], "rb": ["Casey Sample"], "kr": ["Casey Sample"]}
    assert report["unmapped_positions"] == {}


@pytest.mark.parametrize("title", ["2026 Football Roster", "2002 Swimming Roster", "Football"])
def test_url_year_cannot_substitute_for_correct_page_season(title: str) -> None:
    with pytest.raises(ValueError, match="season-specific football roster"):
        parse_roster_page(page(title), 2002)


def test_unknown_position_is_reported_without_inventing_a_role() -> None:
    roster, report = parse_roster_page(page(position="ATH"), 2002)
    assert "Alex Example" not in [name for names in roster.values() for name in names]
    assert report["unmapped_positions"] == {"ATH": 1}


def test_current_navigation_table_cannot_be_mistaken_for_roster() -> None:
    with pytest.raises(ValueError, match="no named positional roster"):
        parse_roster_page(
            "<title>2002 Football Roster</title><table><tr><td>News</td></tr></table>", 2002
        )


def test_explicit_season_heading_is_supported_when_title_omits_roster() -> None:
    html = page("Football 2002 - Fictional University")
    html += "<h1>Football 2002 Roster</h1>"
    assert parse_roster_page(html, 2002)[0]["qb"] == ["Alex Example"]


@pytest.mark.parametrize(
    ("position", "role"),
    [
        ("I Back", "rb"),
        ("Wingback", "rb"),
        ("WB", "rb"),
        ("Left Cornerback", "db"),
        ("Right Cornerback", "db"),
        ("WILL Linebacker", "lb"),
        ("MIKE Linebacker", "lb"),
        ("Strong Side Linebacker", "lb"),
        ("Buck Linebacker", "lb"),
        ("Left Rush End", "dl"),
        ("Right Rush End", "dl"),
        ("Rush End", "dl"),
        ("Nose Guard", "dl"),
        ("Offensive Tackle", "ol"),
        ("Offensive Guard", "ol"),
        ("Left Guard", "ol"),
        ("Defensive Lineman", "dl"),
        ("Offensive Lineman", "ol"),
    ],
)
def test_explicit_historical_position_names(position: str, role: str) -> None:
    roster, report = parse_roster_page(page(position=position), 2002)
    assert "Alex Example" in roster[role]
    assert report["unmapped_positions"] == {}


@pytest.mark.parametrize("position", ["LS", "DS", "Rover", "OS", "Pitcher", "JR"])
def test_specialist_or_ambiguous_labels_stay_unmapped(position: str) -> None:
    roster, report = parse_roster_page(page(position=position), 2002)
    assert all("Alex Example" not in names for names in roster.values())
    assert report["unmapped_positions"] == {position: 1}


def test_names_drop_footnote_stars_and_preserve_suffixes() -> None:
    html = page().replace("Alex Example", "Example, Alex Jr.***")
    assert parse_roster_page(html, 2002)[0]["qb"] == ["Alex Example Jr."]


def test_cached_response_can_be_reparsed_without_refetching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import json

    from scripts.acquire_rosters import main

    cache = tmp_path / "cache"
    cache.mkdir()
    html = "<title>2002 Football Roster</title><table><tr><th>Name</th><th>Pos</th></tr>"
    html += "".join(f"<tr><td>Example {i}</td><td>RB</td></tr>" for i in range(20))
    payload = (html + "</table>").encode()
    (cache / "1.html").write_bytes(payload)
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "season": 2002,
                "teams": {"1": {"name": "Cedar Valley", "url": "https://example.test/2002"}},
            }
        )
    )
    output = tmp_path / "private-data" / "acquired"
    monkeypatch.setattr(
        "sys.argv",
        [
            "acquire_rosters",
            "--sources",
            str(plan),
            "--output",
            str(output),
            "--cache-dir",
            str(cache),
        ],
    )

    def refuse_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("cached response must not be fetched again")

    monkeypatch.setattr("scripts.acquire_rosters.urlopen", refuse_network)
    assert main() == 0
    report = json.loads((output / "acquisition.json").read_text())["teams"]["1"]
    assert report["source_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["players"] == 20
    assert (output / "raw" / "1.html").read_bytes() == payload
