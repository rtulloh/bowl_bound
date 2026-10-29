"""Run the Bowl Bound web demo: python -m backend --seasons seasons

Serves the API and, if present, the built frontend. It binds to this computer only
unless --allow-remote is given, because the game has no authentication.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from fastapi import FastAPI

from .app import create_app

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _port(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be a whole number") from error
    if not 1 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m backend", description=__doc__)
    parser.add_argument("--seasons", type=Path, default=Path("seasons"), help="seasons folder")
    parser.add_argument("--static", type=Path, default=Path("frontend/dist"), help="built frontend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=_port, default=8000)
    parser.add_argument(
        "--allow-remote", action="store_true", help="permit a non-local host (no authentication!)"
    )
    args = parser.parse_args(argv)
    if args.host not in LOCAL_HOSTS and not args.allow_remote:
        parser.error("a non-local --host needs --allow-remote; the demo has no authentication")
    return args


def build_app(args: argparse.Namespace) -> FastAPI:
    return create_app(args.seasons, args.static)


def main() -> None:
    args = parse_args()
    try:
        import uvicorn
    except ImportError:
        sys.exit("uvicorn is not installed; run: pip install -e '.[web]'")
    uvicorn.run(build_app(args), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
