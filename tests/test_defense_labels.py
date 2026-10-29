"""Verified Mays/Bowl Bound formation names; synthetic engine and API evidence only."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.save_game import SavedGame, _view_digest, dumps_game, loads_game
from bowl_bound.session import PlaySession
from tests.synthetic_teams import default_teams, write_team

LABELS = [
    ("A", "Standard"),
    ("B", "Short yardage (gaps)"),
    ("C", "Short yardage (wide)"),
    ("D", "Pass prevent (short)"),
    ("E", "Pass prevent (long)"),
    ("F", "Blitz"),
]


def test_engine_and_private_defense_controls_supply_verified_formation_names() -> None:
    game = SavedGame.new(
        *default_teams(), home_id="2026/alpha-tech", away_id="2026/beta-state", seed=7
    )
    assert [(a.key, a.label) for a in game.view().actions.defense] == LABELS
    assert [(a.key, a.label) for a in game.coach_view("away")[1].actions.defense] == LABELS


def test_api_transports_all_six_engine_labels_without_a_client_mapping(tmp_path: Path) -> None:
    for team in default_teams():
        write_team(tmp_path, team)
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/api/games",
        json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7},
    )
    assert response.status_code == 200
    actions = response.json()["view"]["actions"]["defense"]
    assert [(a["key"], a["label"]) for a in actions] == LABELS


def test_selector_names_do_not_change_legacy_save_digests_or_continuation() -> None:
    teams = default_teams()
    game = SavedGame.new(*teams, home_id="2026/alpha-tech", away_id="2026/beta-state", seed=7)
    game.snap("1", "A")
    current = game.view()
    legacy = replace(
        current,
        actions=replace(
            current.actions,
            defense=tuple(replace(a, label=f"Formation {a.key}") for a in current.actions.defense),
        ),
    )
    assert _view_digest(current) == _view_digest(legacy)
    changed_key = replace(
        current,
        actions=replace(current.actions, defense=(replace(current.actions.defense[0], key="F"),)),
    )
    assert _view_digest(changed_key) != _view_digest(current)
    restored = loads_game(dumps_game(game), lambda key: teams[0] if "alpha" in key else teams[1])
    assert restored.snap("2", "F") == game.snap("2", "F")


@pytest.mark.parametrize("key,label", LABELS)
def test_play_log_uses_friendly_defense_names_but_preserves_chart_trace(
    key: str, label: str
) -> None:
    session = PlaySession.new(*default_teams(), seed=7)
    report = session.snap("1", key)
    friendly = f"{key} {label}"
    assert report.defense == friendly
    assert f"Line Plunge vs {friendly} -" in report.description
    assert "Formation" not in report.description
    assert session.view().log[-1] == report
    assert report.trace[1].formation == f"Formation {key}"


@pytest.mark.parametrize("key,label", LABELS)
def test_friendly_log_names_keep_legacy_save_digests_without_hiding_defense_changes(
    key: str, label: str
) -> None:
    session = PlaySession.new(*default_teams(), seed=7)
    report = session.snap("1", key)
    friendly = f"{key} {label}"
    assert report.defense == friendly
    current = session.view()
    legacy_report = replace(
        report,
        defense=f"Formation {key}",
        description=report.description.replace(f"vs {friendly}", f"vs Formation {key}"),
    )
    assert _view_digest(current) == _view_digest(replace(current, log=(legacy_report,)))
    other_key, other_label = LABELS[(ord(key) - ord("A") + 1) % len(LABELS)]
    changed = replace(report, defense=f"{other_key} {other_label}")
    assert _view_digest(current) != _view_digest(replace(current, log=(changed,)))
