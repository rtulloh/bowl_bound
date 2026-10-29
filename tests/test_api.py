"""Milestone 10 API adapter: transport only; every label and number comes from the engine."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import MAX_GAMES, create_app
from tests.synthetic_teams import default_teams, team_chart, write_team


@pytest.fixture
def seasons(tmp_path: Path) -> Path:
    root = tmp_path / "seasons"
    for chart in default_teams():
        write_team(root, chart)
    return root


@pytest.fixture
def client(seasons: Path) -> TestClient:
    return TestClient(create_app(seasons))


def start(client: TestClient, **extra: object) -> dict:
    body = {"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 7, **extra}
    response = client.post("/api/games", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "healthy", "service": "bowl-bound"}


def test_teams_are_listed_from_the_season_folders(client: TestClient) -> None:
    data = client.get("/api/teams").json()
    assert data["teams"] == [
        {"id": "2026/alpha-tech", "name": "Alpha Tech", "season": 2026},
        {"id": "2026/beta-state", "name": "Beta State", "season": 2026},
    ]
    assert data["problems"] == []


def test_a_broken_team_is_reported_not_hidden(seasons: Path) -> None:
    write_team(seasons, team_chart("Gamma U"))
    (seasons / "2026" / "gamma-u" / "offense.csv").write_text("not a chart", encoding="utf-8")
    data = TestClient(create_app(seasons)).get("/api/teams").json()
    assert [t["id"] for t in data["teams"]] == ["2026/alpha-tech", "2026/beta-state"]
    assert [p["id"] for p in data["problems"]] == ["2026/gamma-u"]
    assert "not a chart" not in str(data["problems"])


def test_provenance_and_stray_folders_are_not_teams(seasons: Path) -> None:
    (seasons / "2026" / "notes").mkdir()
    (seasons / "readme").mkdir()
    data = TestClient(create_app(seasons)).get("/api/teams").json()
    assert len(data["teams"]) == 2 and data["problems"] == []


def test_a_missing_seasons_folder_gives_an_empty_list(tmp_path: Path) -> None:
    data = TestClient(create_app(tmp_path / "nowhere")).get("/api/teams").json()
    assert data == {"teams": [], "problems": []}


def test_new_game_returns_engine_state_and_labels(client: TestClient) -> None:
    game = start(client)
    assert game["game_id"] and game["seed"] == 7
    view = game["view"]
    assert (view["home"], view["away"], view["finished"]) == ("Alpha Tech", "Beta State", False)
    assert view["state"]["situation"] == "1st and 10" and view["state"]["spot"] == "own 35"
    assert [a["label"] for a in view["actions"]["offense"]][:2] == ["Line Plunge", "Counter"]
    assert [a["key"] for a in view["actions"]["defense"]] == list("ABCDEF")
    assert view["log"] == []


def test_a_seed_is_chosen_and_returned_when_none_is_given(client: TestClient) -> None:
    response = client.post(
        "/api/games", json={"home": "2026/alpha-tech", "away": "2026/beta-state"}
    )
    assert response.status_code == 200 and isinstance(response.json()["seed"], int)


def test_snap_resolves_a_real_play(client: TestClient) -> None:
    game = start(client)
    response = client.post(f"/api/games/{game['game_id']}/snap", json={"play": "1", "defense": "A"})
    assert response.status_code == 200
    report = response.json()["report"]
    assert report["supported"] and report["yards"] == 6
    assert report["state_after"]["situation"] == "2nd and 4"
    assert [t["section"] for t in report["trace"]] == ["offense", "defense"]
    assert response.json()["view"]["state"]["situation"] == "2nd and 4"
    assert len(response.json()["view"]["log"]) == 1


def test_get_game_returns_the_current_view(client: TestClient) -> None:
    game = start(client)
    client.post(f"/api/games/{game['game_id']}/snap", json={"play": "1", "defense": "A"})
    view = client.get(f"/api/games/{game['game_id']}").json()["view"]
    assert view["state"]["situation"] == "2nd and 4" and len(view["log"]) == 1


def test_an_interception_is_returned_as_an_engine_owned_decision(client: TestClient) -> None:
    game = start(client)
    response = client.post(f"/api/games/{game['game_id']}/snap", json={"play": "9", "defense": "A"})
    assert response.status_code == 200
    report = response.json()["report"]
    assert report["supported"] and report["outcome"] == "interception_pending"
    pending = response.json()["view"]["pending"]
    assert [choice["id"] for choice in pending["choices"]] == [
        "interception:return",
        "interception:decline",
    ]
    assert response.json()["view"]["score"] == {"home": 0, "away": 0}


@pytest.mark.parametrize(
    "body",
    [
        {"play": "0", "defense": "A"},
        {"play": "1", "defense": "Z"},
        {"play": 1, "defense": "A"},
        {"play": "1"},
        {},
        {"play": "1", "defense": "A", "extra": 1},
    ],
)
def test_invalid_selections_are_rejected_and_nothing_is_logged(
    client: TestClient, body: dict
) -> None:
    game = start(client)
    assert client.post(f"/api/games/{game['game_id']}/snap", json=body).status_code == 422
    assert client.get(f"/api/games/{game['game_id']}").json()["view"]["log"] == []


def test_a_finished_drive_refuses_more_snaps(client: TestClient) -> None:
    game = start(client, start_yards_to_goal=5)
    first = client.post(f"/api/games/{game['game_id']}/snap", json={"play": "1", "defense": "A"})
    assert first.json()["report"]["outcome"] == "touchdown"
    assert first.json()["view"]["finished"] is False
    assert first.json()["view"]["phase"] == "conversion_choice"
    again = client.post(f"/api/games/{game['game_id']}/snap", json={"play": "1", "defense": "A"})
    assert again.status_code == 409
    converted = client.post(
        f"/api/games/{game['game_id']}/decision", json={"choice": "conversion:kick"}
    )
    assert converted.status_code == 200 and converted.json()["view"]["finished"] is True
    assert (
        client.post(
            f"/api/games/{game['game_id']}/snap", json={"play": "1", "defense": "A"}
        ).status_code
        == 409
    )


def test_unknown_game_and_team_are_404(client: TestClient) -> None:
    assert client.get("/api/games/nope").status_code == 404
    assert (
        client.post("/api/games/nope/snap", json={"play": "1", "defense": "A"}).status_code == 404
    )
    missing = client.post("/api/games", json={"home": "2026/zeta", "away": "2026/beta-state"})
    assert missing.status_code == 404


@pytest.mark.parametrize(
    "bad", ["../x", "2026/../x", "2026/Alpha", "abc/def", "2026", "/etc/passwd", ""]
)
def test_team_ids_cannot_escape_the_seasons_folder(client: TestClient, bad: str) -> None:
    response = client.post("/api/games", json={"home": bad, "away": "2026/beta-state"})
    assert response.status_code == 422


def test_a_broken_team_fails_without_leaking_file_contents(seasons: Path) -> None:
    (seasons / "2026" / "alpha-tech" / "offense.csv").write_text("SECRET,text", encoding="utf-8")
    response = TestClient(create_app(seasons)).post(
        "/api/games", json={"home": "2026/alpha-tech", "away": "2026/beta-state"}
    )
    assert response.status_code == 422 and "SECRET" not in response.text
    assert str(seasons) not in response.text


def test_two_games_are_independent_and_seeds_reproduce(client: TestClient) -> None:
    def play(seed: int) -> list[str]:
        game = start(client, seed=seed)
        return [
            client.post(
                f"/api/games/{game['game_id']}/snap", json={"play": "1", "defense": "A"}
            ).json()["report"]["description"]
            for _ in range(2)
        ]

    assert play(21) == play(21)
    first = start(client, seed=1)
    second = start(client, seed=1)
    client.post(f"/api/games/{first['game_id']}/snap", json={"play": "1", "defense": "A"})
    assert client.get(f"/api/games/{second['game_id']}").json()["view"]["log"] == []


def test_the_oldest_games_are_evicted_past_the_cap(client: TestClient) -> None:
    first = start(client)
    for _ in range(MAX_GAMES):
        start(client)
    assert client.get(f"/api/games/{first['game_id']}").status_code == 404


def test_the_same_team_may_not_play_itself_by_accident(client: TestClient) -> None:
    mirror = client.post("/api/games", json={"home": "2026/alpha-tech", "away": "2026/alpha-tech"})
    assert mirror.status_code == 200  # a mirror match is allowed, as in the engine


def test_decision_endpoint_refuses_a_missing_or_nonpending_game(client: TestClient) -> None:
    assert client.post("/api/games/missing/decision", json={"choice": "decline"}).status_code == 404
    game = start(client)
    response = client.post(f"/api/games/{game['game_id']}/decision", json={"choice": "decline"})
    assert response.status_code == 409


def test_penalty_decision_is_applied_once_through_the_api(seasons: Path) -> None:

    from bowl_bound.models import (
        NormalizedCell,
        PenaltyCode,
        PenaltyData,
        PenaltyTeam,
        Play,
        ResultKind,
    )
    from tests.test_models import provenance

    foul = NormalizedCell(
        ResultKind.PENALTY,
        provenance(),
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, 8),
    )
    home = team_chart("Alpha Tech", plays={Play.ONE: foul})
    write_team(seasons, home)
    client = TestClient(create_app(seasons))
    game = start(client)
    game_id = game["game_id"]
    response = client.post(f"/api/games/{game_id}/snap", json={"play": "1", "defense": "A"})
    assert response.status_code == 200
    pending = response.json()["view"]["pending"]
    assert pending is not None and pending["chooser"] == "Alpha Tech"
    assert response.json()["view"]["state"] == game["view"]["state"]
    assert (
        client.post(f"/api/games/{game_id}/snap", json={"play": "1", "defense": "A"}).status_code
        == 409
    )
    invalid = client.post(f"/api/games/{game_id}/decision", json={"choice": "invalid"})
    assert invalid.status_code == 422
    choice = next(c["id"] for c in pending["choices"] if c["id"].endswith(":previous"))
    accepted = client.post(f"/api/games/{game_id}/decision", json={"choice": choice})
    assert accepted.status_code == 200
    assert accepted.json()["view"]["state"]["spot"] == "own 43"
    assert accepted.json()["view"]["state"]["situation"] == "1st and 10"
    assert accepted.json()["view"]["pending"] is None
    assert client.post(f"/api/games/{game_id}/decision", json={"choice": choice}).status_code == 409


def test_punt_action_and_reception_decision_through_api(seasons: Path) -> None:
    from tests.test_special_teams import special_chart, yards

    write_team(seasons, special_chart("Alpha Tech", punt=yards(40)))
    client = TestClient(create_app(seasons))
    game = start(client)
    path = f"/api/games/{game['game_id']}"
    response = client.post(path + "/kick", json={"action": "punt"})
    assert response.status_code == 200
    data = response.json()
    assert data["view"]["state"] == game["view"]["state"]
    assert data["view"]["pending"]["chooser"] == "Beta State"
    assert client.post(path + "/kick", json={"action": "field_goal"}).status_code == 409
    assert client.post(path + "/snap", json={"play": "1", "defense": "A"}).status_code == 409
    result = client.post(path + "/decision", json={"choice": "kick:fair_catch"})
    assert result.status_code == 200
    assert result.json()["view"]["state"]["yards_to_goal"] == 75
    assert len(result.json()["report"]["trace"]) == 1
    assert len(result.json()["view"]["log"]) == 1


@pytest.mark.parametrize("body", [{}, {"action": "onside"}, {"action": "punt", "extra": True}])
def test_kick_input_is_validated_without_state_change(client: TestClient, body: dict) -> None:
    game = start(client)
    path = f"/api/games/{game['game_id']}"
    assert client.post(path + "/kick", json=body).status_code == 422
    assert client.get(path).json()["view"] == game["view"]


def test_unavailable_opening_kickoff_is_422_and_missing_game_is_404(client: TestClient) -> None:
    game = start(client)
    assert (
        client.post(f"/api/games/{game['game_id']}/kick", json={"action": "kickoff"}).status_code
        == 422
    )
    assert client.post("/api/games/missing/kick", json={"action": "punt"}).status_code == 404


def test_field_goal_score_and_finished_action_refusal_through_api(seasons: Path) -> None:
    from tests.test_special_teams import special_chart, yards

    write_team(seasons, special_chart("Alpha Tech", field_goal=yards(65)))
    client = TestClient(create_app(seasons))
    game = start(client)
    path = f"/api/games/{game['game_id']}"
    result = client.post(path + "/kick", json={"action": "field_goal"})
    assert result.status_code == 200
    assert result.json()["view"]["score"] == {"home": 3, "away": 0}
    assert result.json()["view"]["finished"] is True
    assert result.json()["view"]["actions"]["special"] == []
    assert client.post(path + "/kick", json={"action": "punt"}).status_code == 409


def test_opening_kickoff_end_zone_choice_through_api(seasons: Path) -> None:
    from dataclasses import replace

    from tests.test_special_teams import special_chart, yards

    write_team(seasons, replace(special_chart("Alpha Tech", kickoff=yards(70)), season=2002))
    client = TestClient(create_app(seasons))
    game = start(client, home="2002/alpha-tech")
    path = f"/api/games/{game['game_id']}"
    result = client.post(path + "/kick", json={"action": "kickoff"})
    assert result.status_code == 200
    assert [c["id"] for c in result.json()["view"]["pending"]["choices"]] == [
        "kick:touchback",
        "kick:return",
    ]
    assert result.json()["view"]["state"] == game["view"]["state"]
    final = client.post(path + "/decision", json={"choice": "kick:touchback"})
    assert final.json()["view"]["state"]["yards_to_goal"] == 80
    assert "kickoff" not in [a["key"] for a in final.json()["view"]["actions"]["special"]]
    assert len(final.json()["report"]["trace"]) == 1
