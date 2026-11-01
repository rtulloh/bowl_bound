"""Thin FastAPI adapter for Bowl Bound games.

This module only validates input, finds teams on disk, holds in-memory sessions and
serializes the engine's own views. It never reads chart cells, never decides football
results and never builds wording: every label, number and sentence comes from
bowl_bound.session.
"""

import secrets
from collections import OrderedDict
from dataclasses import asdict, dataclass
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
from bowl_bound.save_game import (
    GameRevisionConflict,
    SavedGame,
    SaveFormatError,
    dumps_game,
    loads_game,
)
from bowl_bound.session import (
    InvalidDecisionError,
    PendingDecisionError,
    PlayReport,
    SessionFinishedError,
    SessionView,
)
from bowl_bound.team_catalog import (
    TEAM_ID_MAX_LENGTH,
    TEAM_ID_RE,
    TeamCatalog,
    TeamNotFoundError,
)

from .request_limits import RequestBodyLimit

MAX_GAMES = 50
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
TeamId = Annotated[str, StringConstraints(max_length=TEAM_ID_MAX_LENGTH)]
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
    coach_policy: (
        Literal[
            "baseline",
            "baseline-v2",
            "baseline-v8",
            "chart-v1",
            "chart-v2",
            "easy-v1",
            "medium-v1",
            "hard-v1",
            "easy-v2",
            "medium-v2",
            "hard-v2",
            "chart-v3",
            "easy-v3",
            "medium-v3",
            "hard-v3",
            "chart-v4",
            "easy-v4",
            "medium-v4",
            "hard-v4",
            "chart-v5",
            "easy-v5",
            "medium-v5",
            "hard-v5",
            "chart-v6",
            "easy-v6",
            "medium-v6",
            "hard-v6",
            "chart-v7",
            "chart-v8",
            "easy-v7",
            "medium-v7",
            "hard-v7",
            "easy-v8",
            "medium-v8",
            "hard-v8",
        ]
        | None
    ) = None

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
    action: Literal[
        "kneel",
        "hail_mary",
        "timeout:home",
        "timeout:away",
        "bounds:oob",
        "bounds:ib",
    ]


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: str = Field(min_length=1, max_length=100)


class CoachStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    human_side: HumanSide
    human_call: str | None = Field(default=None, pattern=r"^[1-9A-F]$")
    expected_revision: int = Field(ge=0, strict=True)


@dataclass(frozen=True)
class RegisteredGame:
    """In-memory game plus its immutable API control mode."""

    session: SavedGame
    human_side: HumanSide | None


def _report_data(session: SavedGame, report: PlayReport | None) -> dict[str, object] | None:
    if report is None:
        return None
    return {
        **asdict(report),
        "commentary": session.commentary(report),
        "highlights": list(report.highlight_tags),
    }


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
    games: OrderedDict[str, RegisteredGame] = OrderedDict()
    registry_lock = RLock()
    coordinator_error_detail = "Unable to prepare a legal coached turn for this game state."

    def coordinator_conflict() -> HTTPException:
        return HTTPException(status_code=409, detail=coordinator_error_detail)

    def lookup(game_id: str) -> RegisteredGame:
        with registry_lock:
            registered = _session(games, game_id)
            games.move_to_end(game_id)
            return registered

    def require_control(registered: RegisteredGame, human_side: HumanSide | None) -> None:
        if registered.human_side != human_side:
            raise HTTPException(
                status_code=409,
                detail="Game control mode or human side does not match this request.",
            )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "healthy", "service": "bowl-bound"}

    @app.get("/api/version")
    def version() -> dict[str, str]:
        return {"version": DISPLAY_VERSION, "python_version": __version__}

    @app.get("/api/teams")
    def teams() -> dict[str, list[dict[str, object]]]:
        catalog = TeamCatalog(seasons_root)
        try:
            entries = catalog.teams()
        except ValueError:
            return {"teams": [], "problems": []}
        found = [{"id": entry.key, "name": entry.name, "season": entry.season} for entry in entries]
        problems = [
            {"id": problem.partition(":")[0], "reason": "could not be read"}
            for problem in catalog.problems
        ]
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
                coach_policy=body.coach_policy or f"{body.difficulty or 'medium'}-v8",
            )
            session.load_rosters(seasons_root)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return register(session, human_side)

    def register(session: SavedGame, human_side: HumanSide | None = None) -> dict[str, object]:
        game_id = secrets.token_urlsafe(9)
        registered = RegisteredGame(session, human_side)
        with registry_lock:
            games[game_id] = registered
            while len(games) > MAX_GAMES:
                games.popitem(last=False)
        return present(game_id, registered)

    def present(game_id: str, registered: RegisteredGame) -> dict[str, object]:
        session = registered.session
        if registered.human_side is None:
            return {
                "game_id": game_id,
                "seed": session.seed,
                "coach_policy": session.coach_policy,
                "view": _view_data(session, session.view()),
                "revision": session.revision,
            }
        try:
            view, turn = session.coach_view(registered.human_side)
        except ValueError as error:
            raise coordinator_conflict() from error
        return {
            "game_id": game_id,
            "seed": session.seed,
            "coach_policy": session.coach_policy,
            "view": _view_data(session, view),
            "turn": asdict(turn),
            "revision": session.revision,
        }

    def command(
        session: SavedGame, operation: str, value: str, human_side: HumanSide | None
    ) -> dict[str, object]:
        if human_side is None:
            report, view = session.execute_with_view(operation, [value])
            return {
                "report": _report_data(session, report),
                "view": _view_data(session, view),
                "revision": session.revision,
            }
        try:
            report, view, turn = session.coach_execute(human_side, operation, value)
        except InvalidDecisionError:
            raise
        except ValueError as error:
            raise coordinator_conflict() from error
        return {
            "report": _report_data(session, report),
            "view": _view_data(session, view),
            "turn": asdict(turn),
            "revision": session.revision,
        }

    @app.get("/api/games/{game_id}/save")
    def save_game(game_id: str) -> Response:
        session = lookup(game_id).session
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
    async def load_game(request: Request, human_side: HumanSide | None = None) -> dict[str, object]:
        try:
            text = (await request.body()).decode("utf-8")
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
        return register(session, human_side)

    @app.get("/api/games/{game_id}")
    def get_game(game_id: str, human_side: HumanSide | None = None) -> dict[str, object]:
        registered = lookup(game_id)
        require_control(registered, human_side)
        return present(game_id, registered)

    @app.post("/api/games/{game_id}/coach")
    def coach_step(game_id: str, body: CoachStep) -> dict[str, object]:
        registered = lookup(game_id)
        require_control(registered, body.human_side)
        if registered.human_side is None:
            raise HTTPException(status_code=409, detail="This game uses manual controls.")
        session = registered.session
        try:
            report, view, turn = session.coach_step(
                body.human_side,
                body.human_call,
                expected_revision=body.expected_revision,
            )
        except GameRevisionConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except ValueError as error:
            raise coordinator_conflict() from error
        return {
            "report": _report_data(session, report),
            "view": _view_data(session, view),
            "turn": asdict(turn),
            "revision": session.revision,
        }

    @app.post("/api/games/{game_id}/snap")
    def snap(game_id: str, body: Snap) -> dict[str, object]:
        registered = lookup(game_id)
        if registered.human_side is not None:
            raise HTTPException(status_code=409, detail="This game uses coached controls.")
        session = registered.session
        try:
            report, view = session.execute_with_view("snap", [body.play, body.defense])
        except (SessionFinishedError, PendingDecisionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidDecisionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "report": _report_data(session, report),
            "view": _view_data(session, view),
            "revision": session.revision,
        }

    @app.post("/api/games/{game_id}/kick")
    def kick(game_id: str, body: Kick, human_side: HumanSide | None = None) -> dict[str, object]:
        registered = lookup(game_id)
        require_control(registered, human_side)
        session = registered.session
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
        registered = lookup(game_id)
        require_control(registered, human_side)
        session = registered.session
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
        registered = lookup(game_id)
        require_control(registered, human_side)
        session = registered.session
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


def _session(games: OrderedDict[str, RegisteredGame], game_id: str) -> RegisteredGame:
    registered = games.get(game_id)
    if registered is None:
        raise HTTPException(status_code=404, detail="no such game")
    return registered


def _load(seasons_root: Path, team_id: str):  # noqa: ANN202 - returns a TeamChart
    if len(team_id) > TEAM_ID_MAX_LENGTH or not TEAM_ID_RE.fullmatch(team_id):
        raise HTTPException(status_code=422, detail="team id must look like 2002/ohio-state")
    try:
        return TeamCatalog(seasons_root).load(team_id)
    except TeamNotFoundError as error:
        raise HTTPException(status_code=404, detail="no such team") from error
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="that team's files could not be read"
        ) from error
