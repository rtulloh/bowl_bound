"""Thin FastAPI adapter for the Milestone 10 demonstration.

This module only validates input, finds teams on disk, holds in-memory sessions and
serializes the engine's own views. It never reads chart cells, never decides football
results and never builds wording: every label, number and sentence comes from
bowl_bound.session.
"""

import re
import secrets
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from starlette.concurrency import run_in_threadpool

from bowl_bound import DISPLAY_VERSION, __version__
from bowl_bound.regulation import RegulationView
from bowl_bound.roster import RosterFormatError
from bowl_bound.save_game import MAX_SAVE_BYTES, SavedGame, SaveFormatError, dumps_game, loads_game
from bowl_bound.session import (
    InvalidDecisionError,
    PendingDecisionError,
    PlayReport,
    SessionFinishedError,
    SessionView,
)
from bowl_bound.team_csv import TeamFormatError, load_team, team_folder_name

from .request_limits import RequestBodyLimit

MAX_GAMES = 50
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
_TEAM_ID = re.compile(r"^[1-9][0-9]{0,5}/[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEASON = re.compile(r"^[1-9][0-9]{0,5}$")

TeamId = Annotated[str, StringConstraints(max_length=120)]
HumanSide = Literal["home", "away"]


class NewGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home: TeamId
    away: TeamId
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)
    start_yards_to_goal: int = Field(default=65, ge=1, le=99)
    mode: Literal["drive", "regulation"] = "drive"
    game_type: Literal["regular", "postseason"] = "regular"
    difficulty: Literal["easy", "medium", "hard"] | None = None
    coach_policy: Literal["baseline", "chart-v1", "easy-v1", "medium-v1", "hard-v1"] | None = None

    @model_validator(mode="after")
    def unambiguous_policy(self) -> "NewGame":
        if self.difficulty is not None and self.coach_policy is not None:
            raise ValueError("choose difficulty or legacy coach_policy, not both")
        return self


class Snap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    play: str = Field(pattern=r"^[1-9]$")
    defense: str = Field(pattern=r"^[A-F]$")


class Kick(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["kickoff", "punt", "field_goal"]


class GameAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["kneel", "hail_mary", "timeout:home", "timeout:away"]


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: str = Field(min_length=1, max_length=100)


class CoachStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    human_side: HumanSide
    human_call: str | None = Field(default=None, pattern=r"^[1-9A-F]$")


def _report_data(session: SavedGame, report: PlayReport | None) -> dict[str, object] | None:
    return None if report is None else {**asdict(report), "commentary": session.commentary(report)}


def _view_data(session: SavedGame, view: SessionView | RegulationView) -> dict[str, object]:
    data = asdict(view)
    data["log"] = [_report_data(session, report) for report in view.log]
    return data


def create_app(seasons_root: Path, static_dir: Path | None = None) -> FastAPI:
    """Build the app for one seasons folder; sessions live in memory only."""
    app = FastAPI(title="Bowl Bound", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestBodyLimit)
    games: OrderedDict[str, SavedGame] = OrderedDict()
    registry_lock = RLock()

    def lookup(game_id: str) -> SavedGame:
        with registry_lock:
            session = _session(games, game_id)
            games.move_to_end(game_id)
            return session

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "healthy", "service": "bowl-bound"}

    @app.get("/api/version")
    def version() -> dict[str, str]:
        return {"version": DISPLAY_VERSION, "python_version": __version__}

    @app.get("/api/teams")
    def teams() -> dict[str, list[dict[str, object]]]:
        found: list[dict[str, object]] = []
        problems: list[dict[str, str]] = []
        for team_id, season_dir, slug in _team_folders(seasons_root):
            try:
                chart, _ = load_team(season_dir, slug)
            except (TeamFormatError, OSError):
                problems.append({"id": team_id, "reason": "could not be read"})
                continue
            found.append({"id": team_id, "name": chart.name, "season": chart.season})
        return {"teams": found, "problems": problems}

    @app.post("/api/games")
    def new_game(body: NewGame, human_side: HumanSide | None = None) -> dict[str, object]:
        home = _load(seasons_root, body.home)
        away = _load(seasons_root, body.away)
        seed = body.seed if body.seed is not None else secrets.randbits(32)
        try:
            session = SavedGame.new(
                home,
                away,
                home_id=body.home,
                away_id=body.away,
                seed=seed,
                mode=body.mode,
                game_type=body.game_type,
                start_yards_to_goal=body.start_yards_to_goal,
                coach_policy=body.coach_policy or f"{body.difficulty or 'medium'}-v1",
            )
            session.load_rosters(seasons_root)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return register(session, human_side)

    def register(session: SavedGame, human_side: HumanSide | None = None) -> dict[str, object]:
        game_id = secrets.token_urlsafe(9)
        with registry_lock:
            games[game_id] = session
            while len(games) > MAX_GAMES:
                games.popitem(last=False)
        return present(game_id, session, human_side)

    def present(
        game_id: str, session: SavedGame, human_side: HumanSide | None
    ) -> dict[str, object]:
        if human_side is None:
            return {
                "game_id": game_id,
                "seed": session.seed,
                "coach_policy": session.coach_policy,
                "view": _view_data(session, session.view()),
            }
        view, turn = session.coach_view(human_side)
        return {
            "game_id": game_id,
            "seed": session.seed,
            "coach_policy": session.coach_policy,
            "view": _view_data(session, view),
            "turn": asdict(turn),
        }

    def command(
        session: SavedGame, operation: str, value: str, human_side: HumanSide | None
    ) -> dict[str, object]:
        if human_side is None:
            report, view = session.execute_with_view(operation, [value])
            return {"report": _report_data(session, report), "view": _view_data(session, view)}
        report, view, turn = session.coach_execute(human_side, operation, value)
        return {
            "report": _report_data(session, report),
            "view": _view_data(session, view),
            "turn": asdict(turn),
        }

    @app.get("/api/games/{game_id}/save")
    def save_game(game_id: str) -> Response:
        session = lookup(game_id)
        try:
            text = dumps_game(session)
        except SaveFormatError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(
            text,
            media_type="application/json",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'attachment; filename="bowl-bound-save.json"',
            },
        )

    @app.post("/api/games/load")
    async def load_game(request: Request) -> dict[str, object]:
        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_SAVE_BYTES:
                raise HTTPException(status_code=413, detail="Save exceeds the 2 MiB limit.")
            chunks.append(chunk)
        try:
            text = b"".join(chunks).decode("utf-8")
            session = await run_in_threadpool(
                loads_game, text, lambda key: _load(seasons_root, key)
            )
            await run_in_threadpool(session.load_rosters, seasons_root)
        except (SaveFormatError, RosterFormatError, UnicodeError, HTTPException) as error:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Save is invalid, incompatible, or its local teams are unavailable; "
                    "current game unchanged."
                ),
            ) from error
        return register(session)

    @app.get("/api/games/{game_id}")
    def get_game(game_id: str, human_side: HumanSide | None = None) -> dict[str, object]:
        session = lookup(game_id)
        return present(game_id, session, human_side)

    @app.post("/api/games/{game_id}/coach")
    def coach_step(game_id: str, body: CoachStep) -> dict[str, object]:
        session = lookup(game_id)
        try:
            report, view, turn, _ = session.coach_step(body.human_side, body.human_call)
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "report": _report_data(session, report),
            "view": _view_data(session, view),
            "turn": asdict(turn),
        }

    @app.post("/api/games/{game_id}/snap")
    def snap(game_id: str, body: Snap) -> dict[str, object]:
        session = lookup(game_id)
        try:
            report, view = session.execute_with_view("snap", [body.play, body.defense])
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"report": _report_data(session, report), "view": _view_data(session, view)}

    @app.post("/api/games/{game_id}/kick")
    def kick(game_id: str, body: Kick, human_side: HumanSide | None = None) -> dict[str, object]:
        session = lookup(game_id)
        try:
            return command(session, "kick", body.action, human_side)
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/games/{game_id}/decision")
    def decide(
        game_id: str, body: Decision, human_side: HumanSide | None = None
    ) -> dict[str, object]:
        session = lookup(game_id)
        try:
            return command(session, "decide", body.choice, human_side)
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/games/{game_id}/action")
    def game_action(
        game_id: str, body: GameAction, human_side: HumanSide | None = None
    ) -> dict[str, object]:
        session = lookup(game_id)
        if session.mode != "regulation":
            raise HTTPException(status_code=422, detail="clock actions require regulation mode")
        try:
            return command(session, "action", body.action, human_side)
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")
    return app


def _session(games: OrderedDict[str, SavedGame], game_id: str) -> SavedGame:
    session = games.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such game")
    return session


def _team_folders(seasons_root: Path) -> list[tuple[str, Path, str]]:
    result: list[tuple[str, Path, str]] = []
    if not seasons_root.is_dir() or seasons_root.is_symlink():
        return result
    for season_dir in sorted(seasons_root.iterdir(), key=lambda p: p.name):
        if (
            not season_dir.is_dir()
            or season_dir.is_symlink()
            or not _SEASON.fullmatch(season_dir.name)
        ):
            continue
        for folder in sorted(season_dir.iterdir(), key=lambda p: p.name):
            if not folder.is_dir() or folder.is_symlink() or folder.name == "provenance":
                continue
            try:
                canonical = team_folder_name(folder.name) == folder.name
            except TeamFormatError:
                canonical = False
            if canonical and (folder / "team.yaml").is_file():
                result.append((season_dir.name + "/" + folder.name, season_dir, folder.name))
    return result


def _load(seasons_root: Path, team_id: str):  # noqa: ANN202 - returns a TeamChart
    if not _TEAM_ID.fullmatch(team_id):
        raise HTTPException(status_code=422, detail="team id must look like 2002/ohio-state")
    season, slug = team_id.split("/")
    season_dir = seasons_root / season
    if any(path.is_symlink() for path in (seasons_root, season_dir, season_dir / slug)):
        raise HTTPException(status_code=422, detail="team folders must not use symlinks")
    if not (season_dir / slug).is_dir():
        raise HTTPException(status_code=404, detail="no such team")
    try:
        chart, _ = load_team(season_dir, slug)
    except (TeamFormatError, OSError) as error:
        raise HTTPException(
            status_code=422, detail="that team's files could not be read"
        ) from error
    return chart
