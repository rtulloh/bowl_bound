"""The launcher builds the real app from command-line options and never binds publicly."""

from pathlib import Path

import pytest

from backend.__main__ import build_app, parse_args
from tests.synthetic_teams import default_teams, write_team


def test_defaults_are_local_only() -> None:
    args = parse_args([])
    assert args.host == "127.0.0.1" and args.port == 8000
    assert args.seasons == Path("seasons")
    assert args.static == Path("frontend/dist")


def test_options_are_parsed() -> None:
    args = parse_args(["--seasons", "x", "--port", "9001", "--static", "y"])
    assert (args.seasons, args.port, args.static) == (Path("x"), 9001, Path("y"))


@pytest.mark.parametrize("bad", [["--port", "0"], ["--port", "70000"], ["--port", "abc"]])
def test_bad_ports_are_rejected(bad: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_args(bad)


def test_a_non_local_host_needs_an_explicit_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        parse_args(["--host", "0.0.0.0"])
    assert "--allow-remote" in capsys.readouterr().err
    assert parse_args(["--host", "0.0.0.0", "--allow-remote"]).host == "0.0.0.0"


def test_build_app_serves_the_teams(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    for chart in default_teams():
        write_team(tmp_path / "seasons", chart)
    app = build_app(parse_args(["--seasons", str(tmp_path / "seasons")]))
    assert len(TestClient(app).get("/api/teams").json()["teams"]) == 2
