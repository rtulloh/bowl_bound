"""Local launcher lifecycle checks use synthetic assets and mocked Uvicorn."""

import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from backend import launcher


@pytest.fixture
def resources(tmp_path: Path) -> Path:
    (tmp_path / "seasons").mkdir()
    (tmp_path / "frontend/dist").mkdir(parents=True)
    (tmp_path / "frontend/dist/index.html").write_text("Synthetic UI")
    return tmp_path


def test_source_and_frozen_resource_paths_are_independent_of_cwd(tmp_path: Path) -> None:
    with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
        assert launcher.resource_root() == tmp_path
    assert launcher.resource_root() == Path(launcher.__file__).resolve().parents[1]


def test_version_exits_without_web_dependencies_or_resources(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as result:
        launcher.main(["--version"])
    assert result.value.code == 0
    assert capsys.readouterr().out.strip() == "Bowl Bound 0.1.0-alpha.2"


@pytest.mark.parametrize("args", [["--port", "0"], ["--port", "65536"], ["--host", "0.0.0.0"]])
def test_invalid_port_or_implicit_remote_binding_is_refused(args: list[str]) -> None:
    with pytest.raises(SystemExit) as result:
        launcher.main(args)
    assert result.value.code == 2


def test_missing_assets_are_actionable_without_private_path_leak(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch.object(launcher, "resource_root", return_value=tmp_path):
        assert launcher.main(["--no-browser"]) == 1
    message = capsys.readouterr().err
    assert "resources" in message
    assert str(tmp_path) not in message


def test_occupied_port_does_not_open_browser(
    resources: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with socket.create_server(("127.0.0.1", 0)) as occupied:
        port = occupied.getsockname()[1]
        with (
            patch.object(launcher, "resource_root", return_value=resources),
            patch("webbrowser.open") as browser,
        ):
            assert launcher.main(["--port", str(port)]) == 1
        browser.assert_not_called()
    assert "port" in capsys.readouterr().err.lower()


def test_server_receives_reserved_socket_and_shuts_down_without_reload(resources: Path) -> None:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    with (
        patch.object(launcher, "resource_root", return_value=resources),
        patch("uvicorn.Server") as server,
        patch("webbrowser.open") as browser,
    ):
        assert launcher.main(["--no-browser", "--port", str(port)]) == 0
    config = server.call_args.args[0]
    assert config.host == "127.0.0.1"
    assert config.reload is False
    assert config.workers == 1
    supplied = server.return_value.run.call_args.kwargs["sockets"][0]
    assert supplied.fileno() == -1  # Closed even when the server returns immediately.
    browser.assert_not_called()


def test_browser_waits_for_actual_server_start_and_stops_on_exit() -> None:
    from threading import Event, Thread
    from types import SimpleNamespace

    done = Event()
    server = SimpleNamespace(started=False)
    with patch("webbrowser.open") as browser:
        thread = Thread(
            target=launcher.open_when_ready, args=(server, done, "http://127.0.0.1:8000")
        )
        thread.start()
        browser.assert_not_called()
        done.set()
        thread.join(timeout=2)
        assert not thread.is_alive()
        browser.assert_not_called()
    done.clear()
    server.started = True
    with patch("webbrowser.open") as browser:
        thread = Thread(
            target=launcher.open_when_ready, args=(server, done, "http://127.0.0.1:8000")
        )
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        browser.assert_called_once_with("http://127.0.0.1:8000")


def test_start_sh_from_unrelated_directory_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "installed game"
    root.mkdir()
    script = Path(__file__).resolve().parents[1] / "start.sh"
    (root / "start.sh").write_bytes(script.read_bytes())
    executable = root / "Bowl-Bound"
    executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    executable.chmod(0o755)
    result = subprocess.run(
        ["bash", str(root / "start.sh"), "--version", "argument with spaces"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == ["--version", "argument with spaces"]


def test_failed_startup_returns_failure_and_does_not_open_browser(resources: Path) -> None:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    with (
        patch.object(launcher, "resource_root", return_value=resources),
        patch("uvicorn.Server") as server,
        patch("webbrowser.open") as browser,
    ):
        server.return_value.started = False
        assert launcher.main(["--port", str(port)]) == 1
    browser.assert_not_called()


def test_source_start_sh_selects_checkout_python_and_preserves_arguments(tmp_path: Path) -> None:
    root = tmp_path / "source checkout"
    python = root / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    script = Path(__file__).resolve().parents[1] / "start.sh"
    (root / "start.sh").write_bytes(script.read_bytes())
    python.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    python.chmod(0o755)
    result = subprocess.run(
        ["bash", str(root / "start.sh"), "--no-browser"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == ["-m", "backend.launcher", "--no-browser"]


def test_windows_starter_uses_owner_requested_executable_name() -> None:
    starter = (Path(__file__).resolve().parents[1] / "start.bat").read_text(encoding="utf-8")
    assert starter.count("BowlBound.exe") == 2
    assert "Bowl-Bound.exe" not in starter


@pytest.mark.parametrize("startup_failure", [False, True])
def test_windows_ctrl_break_is_clean_and_previous_handler_is_restored(
    resources: Path, monkeypatch: pytest.MonkeyPatch, startup_failure: bool
) -> None:
    import signal

    # Model Uvicorn replaying SIGBREAK after completing graceful shutdown.
    sigbreak = 21
    handlers = {sigbreak: signal.SIG_DFL}

    def set_handler(number: int, handler: object) -> object:
        previous = handlers[number]
        handlers[number] = handler
        return previous

    def run_server(**kwargs: object) -> None:
        if startup_failure:
            raise ValueError("synthetic startup failure")
        handler = handlers[sigbreak]
        if handler == signal.SIG_DFL:
            raise SystemExit("Windows default SIGBREAK terminates with failure")
        handler(sigbreak, None)

    monkeypatch.setattr(signal, "SIGBREAK", sigbreak, raising=False)
    monkeypatch.setattr(signal, "signal", set_handler)
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    with (
        patch.object(launcher, "resource_root", return_value=resources),
        patch("uvicorn.Server") as server,
    ):
        server.return_value.run.side_effect = run_server
        if startup_failure:
            with pytest.raises(ValueError, match="synthetic startup failure"):
                launcher.main(["--no-browser", "--port", str(port)])
        else:
            assert launcher.main(["--no-browser", "--port", str(port)]) == 0
    assert handlers[sigbreak] == signal.SIG_DFL
