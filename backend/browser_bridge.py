"""Expose only registered game operations to the browser worker."""

import json
import re
from inspect import Parameter, signature
from pathlib import Path
from threading import RLock
from typing import get_type_hints
from urllib.parse import parse_qs, unquote, urlsplit

from pydantic import TypeAdapter, ValidationError

from .operations import Operation, OperationError, create_operations, operation_body_limit

_LOAD_PATH = "/api/games/load"
_JSON_RESPONSE = TypeAdapter(object)


class BrowserBridge:
    """Serve one in-memory registry using local API paths and text bodies."""

    def __init__(self, seasons_root: str | Path) -> None:
        self._routes = [
            (re.compile(re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", op.path)), op)
            for op in create_operations(Path(seasons_root))
        ]
        self._lock = RLock()

    def request(self, method: str, path: str, body: str | None = None) -> str:
        """Return a status and raw response text in a JSON envelope."""
        with self._lock:
            try:
                result = self._dispatch(method, path, body)
            except OperationError as error:
                return self._response(error.status_code, {"detail": error.detail})
            except ValidationError as error:
                return self._response(
                    422,
                    {"detail": json.loads(error.json(include_url=False, include_context=False))},
                )
            return self._response(200, result)

    def _dispatch(self, method: str, path: str, body: str | None) -> object:
        try:
            target = urlsplit(path)
        except ValueError as error:
            raise OperationError(400, "Expected a local operation path") from error
        if target.scheme or target.netloc or target.fragment or not target.path.startswith("/api/"):
            raise OperationError(400, "Expected a local operation path")

        route_path = unquote(target.path)
        method = method.upper()
        if method == "POST" and body is not None:
            limit = operation_body_limit(route_path)
            if len(body.encode("utf-8")) > limit:
                raise OperationError(413, "Request body exceeds the size limit.")

        query = parse_qs(target.query, keep_blank_values=True)
        for pattern, operation in self._routes:
            match = pattern.fullmatch(route_path)
            if operation.method == method and match is not None:
                return self._invoke(operation, match.groupdict(), query, body)
        raise OperationError(404, "Unknown operation")

    @staticmethod
    def _invoke(
        operation: Operation, path: dict[str, str], query: dict[str, list[str]], body: str | None
    ) -> object:
        handler = operation.handler
        hints = get_type_hints(handler)
        arguments: dict[str, object] = {}
        for name, parameter in signature(handler).parameters.items():
            annotation = hints[name]
            if name == "body":
                if operation.path == _LOAD_PATH:
                    arguments[name] = body or ""
                else:
                    arguments[name] = annotation.model_validate_json(body or "")
            elif name in path:
                arguments[name] = TypeAdapter(annotation).validate_python(path[name])
            elif name in query:
                arguments[name] = TypeAdapter(annotation).validate_python(query[name][-1])
            elif parameter.default is Parameter.empty:
                raise OperationError(422, f"Missing parameter: {name}")
        return handler(**arguments)

    @staticmethod
    def _response(status: int, value: object) -> str:
        text = value if isinstance(value, str) else _JSON_RESPONSE.dump_json(value).decode("utf-8")
        return json.dumps({"status": status, "body": text})
