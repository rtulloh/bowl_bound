"""API-003: bind control ownership and reject stale coached requests."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.save_game import MAX_SAVE_BYTES
from tests.synthetic_teams import default_teams, write_team


def _client(seasons: Path) -> TestClient:
    for chart in default_teams():
        write_team(seasons, chart)
    return TestClient(create_app(seasons))


def _create(client: TestClient, human_side: str | None = None) -> tuple[str, dict]:
    suffix = f"?human_side={human_side}" if human_side else ""
    response = client.post(
        "/api/games" + suffix,
        json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return f"/api/games/{data['game_id']}", data


def test_control_side_is_fixed_for_game_lifetime(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, created = _create(client, "home")

    assert "revision" in created and created["revision"] == 0
    assert client.post(path + "/snap", json={"play": "1", "defense": "A"}).status_code == 409
    assert client.get(path).status_code == 409
    assert (
        client.post(
            path + "/coach", json={"human_side": "away", "expected_revision": 0, "human_call": "A"}
        ).status_code
        == 409
    )
    assert (
        client.post(path + "/coach", json={"expected_revision": 0, "human_call": "1"}).status_code
        == 422
    )
    assert client.post(path + "/decision", json={"choice": "conversion:kick"}).status_code == 409
    assert client.get(path + "?human_side=away").status_code == 409


def test_expected_revision_rejects_repeated_coach_posts(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, _ = _create(client, "home")
    body = {"human_side": "home", "expected_revision": 0, "human_call": "1"}

    first = client.post(path + "/coach", json=body)
    duplicate = client.post(path + "/coach", json=body)

    assert first.status_code == 200 and first.json()["revision"] == 1
    assert duplicate.status_code == 409
    assert len(client.get(path + "?human_side=home").json()["view"]["log"]) == 1
    assert (
        client.post(path + "/coach", json={"human_side": "home", "human_call": "1"}).status_code
        == 422
    )


@pytest.mark.parametrize(
    ("human_side", "human_call"),
    [("home", "RZDZ"), ("away", "WCRZDZ")],
)
def test_coached_endpoint_accepts_each_offered_razzle_dazzle_call(
    tmp_path: Path, human_side: str, human_call: str
) -> None:
    client = _client(tmp_path)
    path, created = _create(client, human_side)
    actions = created["view"]["actions"]
    role = "offense" if human_side == "home" else "defense"

    response = client.post(
        path + "/coach",
        json={
            "human_side": human_side,
            "human_call": human_call,
            "expected_revision": created["revision"],
        },
    )

    assert human_call in {action["key"] for action in actions[role]}
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == 1


def test_concurrent_duplicate_coach_posts_resolve_once(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, _ = _create(client, "home")
    body = {"human_side": "home", "expected_revision": 0, "human_call": "1"}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _: client.post(path + "/coach", json=body), range(2)))

    assert sorted(response.status_code for response in results) == [200, 409]
    view = client.get(path + "?human_side=home").json()["view"]
    assert len(view["log"]) == 1


def test_coach_and_decision_bodies_keep_the_16_kib_limit(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, _ = _create(client, "home")
    exact_limit = b" " * (16 * 1024)
    oversized = exact_limit + b" "

    assert client.post(path + "/coach", content=exact_limit).status_code == 422
    assert client.post(path + "/decision", content=exact_limit).status_code == 422
    assert client.post(path + "/coach", content=oversized).status_code == 413
    assert client.post(path + "/decision", content=oversized).status_code == 413


def test_loaded_game_is_bound_to_the_selected_control_side(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, _ = _create(client)
    save = client.get(path + "/save").content

    loaded = client.post("/api/games/load?human_side=away", content=save)
    loaded_path = f"/api/games/{loaded.json()['game_id']}"

    assert loaded.status_code == 200
    assert client.get(loaded_path + "?human_side=away").status_code == 200
    assert client.get(loaded_path + "?human_side=home").status_code == 409


def test_load_accepts_exact_limit_and_rejects_one_byte_more(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, _ = _create(client)
    save = client.get(path + "/save").content
    assert len(save) < MAX_SAVE_BYTES
    exact = save + b" " * (MAX_SAVE_BYTES - len(save))

    accepted = client.post("/api/games/load", content=exact)
    rejected = client.post("/api/games/load", content=exact + b" ")

    assert accepted.status_code == 200
    assert rejected.status_code == 413


def test_load_rejects_changed_team_fingerprint_through_api(tmp_path: Path) -> None:
    client = _client(tmp_path)
    path, _ = _create(client)
    save = client.get(path + "/save").content
    original = default_teams()[0]
    first_cell = original.offense[0].cell
    changed_cell = replace(first_cell, yards=first_cell.yards + 1)
    changed = replace(
        original,
        offense=(replace(original.offense[0], cell=changed_cell), *original.offense[1:]),
    )
    write_team(tmp_path, changed)

    response = client.post("/api/games/load", content=save)

    assert response.status_code == 422
    assert "fingerprint" not in response.text.lower()
