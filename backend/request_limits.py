"""Bound request buffering before JSON validation, including chunked bodies."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bowl_bound.save_game import MAX_SAVE_BYTES

MAX_COMMAND_BYTES = 16 * 1024


class RequestBodyLimit:
    """Allow save imports up to 2 MiB and ordinary POST bodies up to 16 KiB."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        limit = MAX_SAVE_BYTES if scope["path"] == "/api/games/load" else MAX_COMMAND_BYTES
        buffered = bytearray()
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > limit:
                response = JSONResponse({"detail": "Request body exceeds the size limit."}, 413)
                await response(scope, receive, send)
                return
            buffered.extend(body)
            if not message.get("more_body", False):
                break
        body = bytes(buffered)
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)
