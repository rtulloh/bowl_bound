"""Start the local production web game from source or a standalone bundle."""

from __future__ import annotations

import argparse
import socket
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING

from bowl_bound import DISPLAY_VERSION

if TYPE_CHECKING:
    from uvicorn import Server

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def resource_root() -> Path:
    """Locate read-only app resources independently of the current directory."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).resolve().parents[1]


def open_when_ready(server: Server, done: Event, url: str) -> None:
    """Open one browser only after our server starts; cancel when startup fails."""
    while not done.wait(0.05):
        if server.started:
            try:
                if not webbrowser.open(url):
                    print(f"Open {url} in your browser to play.", flush=True)
            except (OSError, webbrowser.Error):
                print(f"Open {url} in your browser to play.", flush=True)
            return


def main(argv: Sequence[str] | None = None) -> int:
    """Run one local server; no development reload, child servers or resource writes."""
    parser = argparse.ArgumentParser(description=__doc__, prog="Bowl-Bound")
    parser.add_argument("--version", action="version", version=f"Bowl Bound {DISPLAY_VERSION}")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--allow-remote", action="store_true", help="allow nonlocal binding (no authentication)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="do not open a browser automatically"
    )
    parser.add_argument("--seasons", type=Path, help="use a separately installed local team folder")
    parser.add_argument("--static", type=Path, help="use a separately built frontend")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if args.host not in LOCAL_HOSTS and not args.allow_remote:
        parser.error("nonlocal --host requires --allow-remote; there is no authentication")
    root = resource_root()
    seasons, static = args.seasons or root / "seasons", args.static or root / "frontend/dist"
    if not seasons.is_dir() or not (static / "index.html").is_file():
        print(
            "Game resources are missing. Re-extract the complete app, "
            "or build the source frontend.",
            file=sys.stderr,
        )
        return 1
    try:
        import uvicorn

        from .app import create_app
    except ImportError:
        print(
            "Web dependencies are missing. Source users: python -m pip install -e '.[web]'",
            file=sys.stderr,
        )
        return 1
    family = socket.AF_INET6 if ":" in args.host else socket.AF_INET
    try:
        listener = socket.create_server((args.host, args.port), family=family)
    except OSError:
        print(
            "Could not open the local server port. Stop another copy, or choose --port 8001.",
            file=sys.stderr,
        )
        return 1
    browser_host = args.host if args.host in LOCAL_HOSTS else "127.0.0.1"
    if ":" in browser_host:
        browser_host = f"[{browser_host}]"
    url = f"http://{browser_host}:{args.port}"
    done = Event()
    worker: Thread | None = None
    with listener:
        config = uvicorn.Config(
            create_app(seasons, static),
            host=args.host,
            port=args.port,
            reload=False,
            workers=1,
            access_log=False,
            loop="asyncio",
            http="h11",
            ws="none",
        )
        server = uvicorn.Server(config)
        print(
            f"Bowl Bound {DISPLAY_VERSION}\nOpen {url}\n"
            "Save your game before stopping. Press Ctrl+C to stop.",
            flush=True,
        )
        if args.allow_remote and args.host not in LOCAL_HOSTS:
            print("Warning: remote access is enabled without authentication.", file=sys.stderr)
        if not args.no_browser:
            worker = Thread(target=open_when_ready, args=(server, done, url), daemon=True)
            worker.start()
        try:
            server.run(sockets=[listener])
        except KeyboardInterrupt:
            return 0
        finally:
            done.set()
            if worker is not None:
                worker.join(timeout=1)
    return 0 if server.started else 1


if __name__ == "__main__":
    raise SystemExit(main())
