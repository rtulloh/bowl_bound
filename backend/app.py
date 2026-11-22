"""FastAPI adapter for the transport-independent Bowl Bound game operations."""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from bowl_bound import __version__

from .operations import MAX_GAMES, HumanSide, OperationError, create_operations
from .operations import NewGame as NewGame
from .request_limits import RequestBodyLimit

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def _download(handler: Callable[..., object]) -> Callable[[str], Response]:
    def save_game(game_id: str) -> Response:
        return Response(
            handler(game_id),
            media_type="application/json",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'attachment; filename="bowl-bound-save.json"',
            },
        )

    return save_game


def _upload(handler: Callable[..., object]) -> Callable[..., object]:
    async def load_game(request: Request, human_side: HumanSide | None = None) -> object:
        return await run_in_threadpool(handler, await request.body(), human_side)

    return load_game


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

    @app.exception_handler(OperationError)
    async def operation_error(request: Request, error: OperationError) -> JSONResponse:
        return JSONResponse({"detail": error.detail}, status_code=error.status_code)

    for operation in create_operations(seasons_root, max_games=MAX_GAMES):
        handler = operation.handler
        if operation.path == "/api/games/{game_id}/save":
            handler = _download(handler)
        elif operation.path == "/api/games/load":
            handler = _upload(handler)
        app.add_api_route(operation.path, handler, methods=[operation.method])

    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")
    return app
