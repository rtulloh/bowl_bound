"""Native Windows assent smoke, restricted to windows owned by launched processes.

This checks the agreement dialog with --no-browser. It does not certify browser
first launch, fresh-machine behavior, or injected MessageBox API failures.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.error import URLError

from .smoke_standalone import clean_environment, request

PROMPT = "\n\nChoose Yes to agree to these conditions and continue. Choose No to quit."


@dataclass(frozen=True)
class Dialog:
    handle: int
    pid: int
    text: str
    yes: int
    no: int
    default_id: int
    within_work_area: bool
    text_fits: bool


def is_windows() -> bool:
    return os.name == "nt"


def owned_pids(root: int, parents: dict[int, int]) -> set[int]:
    """Return only the launched PID and descendants in a current process snapshot."""
    result = {root}
    while True:
        expanded = result | {pid for pid, parent in parents.items() if parent in result}
        if expanded == result:
            return result
        result = expanded


def contained(inner: tuple[int, ...], outer: tuple[int, ...]) -> bool:
    return (
        outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]
    )


def validate_dialog(dialog: Dialog, owners: set[int], terms: str) -> int:
    """Refuse partial text, offscreen controls, clipping or unsafe default actions."""
    if (
        dialog.pid not in owners
        or not dialog.handle
        or not dialog.yes
        or not dialog.no
        or dialog.default_id != 7
        or not dialog.within_work_area
        or not dialog.text_fits
        or dialog.text.replace("\r\n", "\n") != terms.replace("\r\n", "\n") + PROMPT
    ):
        raise RuntimeError(
            "Windows terms dialog ownership, full text, default or readability failed"
        )
    return dialog.handle


def click_choice(
    api: Any, dialog: Dialog, owners: set[int], choice: int, expected_image: Path
) -> None:
    """Post directly to the verified owned dialog; never send global keystrokes."""
    if choice not in {6, 7} or api.window_pid(dialog.handle) not in owners:
        raise RuntimeError("Windows terms dialog ownership changed before action")
    if api.image_matches(dialog.pid, expected_image) is not True:
        raise RuntimeError("Windows terms dialog owner image changed before action")
    api.post(dialog.handle, 0x111, choice, dialog.yes if choice == 6 else dialog.no)


def validate_decline_output(output: str) -> None:
    """Require the deliberate refusal path, not a crash with the same exit code."""
    if (
        "Windows runtime terms were not accepted; the game has not started." not in output
        or "Traceback" in output
        or "Fatal Python error" in output
    ):
        raise RuntimeError("Windows terms decline did not produce a clean refusal")


def read_terms(executable: Path, digest: str) -> str:
    copies = []
    for name in ("WINDOWS-RUNTIME-TERMS.txt", "_internal/WINDOWS-RUNTIME-TERMS.txt"):
        path = executable.parent / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Windows terms smoke requires both regular terms files")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Windows terms smoke source hash mismatch")
        copies.append(data)
    if copies[0] != copies[1]:
        raise ValueError("Windows terms smoke copies differ")
    return copies[0].decode("utf-8")


class _Windows:
    """Pointer-width-safe Win32 operations, loaded only on the required native host."""

    def __init__(self) -> None:
        from ctypes import wintypes as w

        self.w = w
        native: Any = ctypes
        self.u = native.WinDLL("user32", use_last_error=True)
        self.k = native.WinDLL("kernel32", use_last_error=True)
        self.g = native.WinDLL("gdi32", use_last_error=True)
        self.callback = native.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        signatures = {
            "GetWindowTextLengthW": ([w.HWND], ctypes.c_int),
            "GetWindowTextW": ([w.HWND, w.LPWSTR, ctypes.c_int], ctypes.c_int),
            "GetWindowThreadProcessId": ([w.HWND, ctypes.POINTER(w.DWORD)], w.DWORD),
            "EnumWindows": ([self.callback, w.LPARAM], w.BOOL),
            "EnumChildWindows": ([w.HWND, self.callback, w.LPARAM], w.BOOL),
            "GetDlgCtrlID": ([w.HWND], ctypes.c_int),
            "GetWindowLongW": ([w.HWND, ctypes.c_int], w.LONG),
            "GetWindowRect": ([w.HWND, ctypes.POINTER(w.RECT)], w.BOOL),
            "GetClientRect": ([w.HWND, ctypes.POINTER(w.RECT)], w.BOOL),
            "MonitorFromWindow": ([w.HWND, w.DWORD], w.HANDLE),
            "GetDC": ([w.HWND], w.HDC),
            "ReleaseDC": ([w.HWND, w.HDC], ctypes.c_int),
            "SendMessageW": ([w.HWND, w.UINT, w.WPARAM, w.LPARAM], ctypes.c_ssize_t),
            "PostMessageW": ([w.HWND, w.UINT, w.WPARAM, w.LPARAM], w.BOOL),
            "DrawTextW": (
                [w.HDC, w.LPCWSTR, ctypes.c_int, ctypes.POINTER(w.RECT), w.UINT],
                ctypes.c_int,
            ),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.u, name)
            function.argtypes, function.restype = args, result
        self.g.SelectObject.argtypes = [w.HDC, w.HANDLE]
        self.g.SelectObject.restype = w.HANDLE
        self.g.GetStockObject.argtypes = [ctypes.c_int]
        self.g.GetStockObject.restype = w.HANDLE

    def text(self, handle: int) -> str:
        buffer = ctypes.create_unicode_buffer(self.u.GetWindowTextLengthW(handle) + 1)
        self.u.GetWindowTextW(handle, buffer, len(buffer))
        return buffer.value

    def window_pid(self, handle: int) -> int:
        pid = self.w.DWORD()
        self.u.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        return pid.value

    def post(self, handle: int, message: int, wp: int, lp: int) -> None:
        if not self.u.PostMessageW(handle, message, wp, lp):
            raise OSError("Could not post Windows terms choice")

    def image_matches(self, pid: int, expected: Path) -> bool:
        w = self.w
        self.k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.k.OpenProcess.restype = w.HANDLE
        self.k.QueryFullProcessImageNameW.argtypes = [
            w.HANDLE,
            w.DWORD,
            w.LPWSTR,
            ctypes.POINTER(w.DWORD),
        ]
        self.k.QueryFullProcessImageNameW.restype = w.BOOL
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.k.CloseHandle.restype = w.BOOL
        handle = self.k.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            size = w.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not self.k.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return False
            return os.path.normcase(os.path.realpath(buffer.value)) == os.path.normcase(
                str(expected.resolve())
            )
        finally:
            self.k.CloseHandle(handle)

    def parents(self) -> dict[int, int]:
        w = self.w

        class Entry(ctypes.Structure):
            _fields_ = [
                ("size", w.DWORD),
                ("usage", w.DWORD),
                ("pid", w.DWORD),
                ("heap", ctypes.c_size_t),
                ("module", w.DWORD),
                ("threads", w.DWORD),
                ("parent", w.DWORD),
                ("priority", w.LONG),
                ("flags", w.DWORD),
                ("exe", w.WCHAR * 260),
            ]

        self.k.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
        self.k.CreateToolhelp32Snapshot.restype = w.HANDLE
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.k.CloseHandle.restype = w.BOOL
        for name in ("Process32FirstW", "Process32NextW"):
            getattr(self.k, name).argtypes = [w.HANDLE, ctypes.POINTER(Entry)]
            getattr(self.k, name).restype = w.BOOL
        snapshot = self.k.CreateToolhelp32Snapshot(2, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            raise OSError("Could not inspect owned Windows process ancestry")
        result = {}
        try:
            entry = Entry()
            entry.size = ctypes.sizeof(Entry)
            if not self.k.Process32FirstW(snapshot, ctypes.byref(entry)):
                raise OSError("Could not inspect Windows process snapshot")
            while True:
                result[entry.pid] = entry.parent
                if not self.k.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
        finally:
            self.k.CloseHandle(snapshot)
        return result

    def rect(self, handle: int, *, client: bool = False) -> tuple[int, ...]:
        rectangle = self.w.RECT()
        function = self.u.GetClientRect if client else self.u.GetWindowRect
        if not function(handle, ctypes.byref(rectangle)):
            raise OSError("Could not inspect Windows dialog geometry")
        return rectangle.left, rectangle.top, rectangle.right, rectangle.bottom

    def readable(self, handle: int) -> bool:
        rectangle = self.rect(handle, client=True)
        dc = self.u.GetDC(handle)
        if not dc:
            raise OSError("Could not measure Windows terms text")
        previous = None
        try:
            font = self.u.SendMessageW(handle, 0x31, 0, 0) or self.g.GetStockObject(17)
            previous = self.g.SelectObject(dc, font)
            measured = self.w.RECT(0, 0, rectangle[2], 0)
            text = self.text(handle)
            height = self.u.DrawTextW(dc, text, len(text), ctypes.byref(measured), 0xC50)
            return bool(
                height > 0 and measured.bottom <= rectangle[3] and measured.right <= rectangle[2]
            )
        finally:
            if previous:
                self.g.SelectObject(dc, previous)
            self.u.ReleaseDC(handle, dc)

    def dialogs(self, owners: set[int]) -> list[Dialog]:
        handles = []
        callback = self.callback(lambda hwnd, _: handles.append(hwnd) or True)
        if not self.u.EnumWindows(callback, 0):
            raise OSError("Could not enumerate Windows terms dialogs")
        result = []
        for hwnd in handles:
            pid = self.window_pid(hwnd)
            if pid not in owners or self.text(hwnd) != "Bowl Bound Windows terms":
                continue
            children = []
            child_callback = self.callback(
                lambda child, _, target=children: target.append(child) or True
            )
            self.u.EnumChildWindows(hwnd, child_callback, 0)
            buttons = {self.u.GetDlgCtrlID(child): child for child in children}
            text_controls = [
                child
                for child in children
                if self.text(child).replace("\r\n", "\n").endswith(PROMPT)
            ]
            if len(text_controls) != 1:
                raise RuntimeError("Full Windows terms static control not found")
            text_control = text_controls[0]

            class Monitor(ctypes.Structure):
                _fields_ = [
                    ("size", self.w.DWORD),
                    ("monitor", self.w.RECT),
                    ("work", self.w.RECT),
                    ("flags", self.w.DWORD),
                ]

            info = Monitor()
            info.size = ctypes.sizeof(Monitor)
            self.u.GetMonitorInfoW.argtypes = [self.w.HANDLE, ctypes.POINTER(Monitor)]
            self.u.GetMonitorInfoW.restype = self.w.BOOL
            monitor = self.u.MonitorFromWindow(hwnd, 2)
            if not self.u.GetMonitorInfoW(monitor, ctypes.byref(info)):
                raise OSError("Could not inspect Windows monitor work area")
            area = (info.work.left, info.work.top, info.work.right, info.work.bottom)
            yes, no = buttons.get(6, 0), buttons.get(7, 0)
            visible = contained(self.rect(hwnd), area) and all(
                control
                and contained(self.rect(control), area)
                and contained(self.rect(control), self.rect(hwnd))
                for control in (text_control, yes, no)
            )
            default = 7 if no and self.u.GetWindowLongW(no, -16) & 0xF == 1 else 0
            result.append(
                Dialog(
                    hwnd,
                    pid,
                    self.text(text_control),
                    yes,
                    no,
                    default,
                    bool(visible),
                    self.readable(text_control),
                )
            )
        return result


def _open_port(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.1)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def smoke_windows_terms(executable: Path, version: str, work: Path, terms_sha256: str) -> dict:
    """Exercise owned native No/Yes paths or raise; unsupported hosts never pass."""
    if not is_windows():
        raise RuntimeError("Native Windows terms smoke requires an interactive Windows host")
    terms = read_terms(executable, terms_sha256)
    api = _Windows()
    outcomes = []
    for choice, name in ((7, "decline"), (6, "accept")):
        with TemporaryDirectory(prefix=f"terms-{name}-", dir=work) as directory:
            appdata = Path(directory)
            env = clean_environment()
            env["LOCALAPPDATA"] = str(appdata)
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            with (work / f"windows-terms-{name}.log").open("w+", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [str(executable), "--no-browser", "--port", str(port)],
                    cwd=work,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=0x200,  # CREATE_NEW_PROCESS_GROUP,
                )
                try:
                    deadline = time.monotonic() + 30
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("Windows app exited before native terms dialog")
                        if _open_port(port):
                            raise RuntimeError("Windows app listened before terms agreement")
                        owners = owned_pids(process.pid, api.parents())
                        dialogs = api.dialogs(owners)
                        if len(dialogs) == 1:
                            dialog = dialogs[0]
                            validate_dialog(dialog, owners, terms)
                            break
                        if len(dialogs) > 1 or time.monotonic() >= deadline:
                            raise RuntimeError(
                                "Expected one owned interactive Windows terms dialog"
                            )
                        time.sleep(0.1)
                    if process.poll() is not None:
                        raise RuntimeError("Windows app exited before verified dialog action")
                    click_choice(
                        api, dialog, owned_pids(process.pid, api.parents()), choice, executable
                    )
                    receipt = appdata / "BowlBound/accepted-windows-runtime-terms.json"
                    if choice == 7:
                        while process.poll() is None:
                            if _open_port(port):
                                raise RuntimeError("Declined Windows app started a server")
                            if time.monotonic() >= deadline:
                                raise TimeoutError("Declined Windows app did not exit")
                            time.sleep(0.05)
                        if process.returncode != 1 or receipt.exists() or _open_port(port):
                            raise RuntimeError("Decline failed to block startup without a receipt")
                        log.seek(0)
                        validate_decline_output(log.read())
                        outcomes.append({"choice": name, "exit": 1, "receipt": False})
                    else:
                        base = f"http://127.0.0.1:{port}"
                        deadline = time.monotonic() + 60
                        while True:
                            if process.poll() is not None:
                                raise RuntimeError("Accepted Windows app exited before readiness")
                            try:
                                health = request(base, "/api/health", timeout=1)
                                if isinstance(health, dict) and health.get("status") == "healthy":
                                    break
                            except (URLError, OSError):
                                pass
                            if time.monotonic() >= deadline:
                                raise TimeoutError("Accepted Windows app did not become healthy")
                            time.sleep(0.1)
                        identity = request(base, "/api/version")
                        if not isinstance(identity, dict) or identity.get("version") != version:
                            raise RuntimeError("Windows terms smoke version mismatch")
                        value = json.loads(receipt.read_text("utf-8"))
                        if value != {"schema": 1, "sha256": terms_sha256}:
                            raise RuntimeError("Windows terms smoke acceptance receipt mismatch")
                        windows_signal: Any = signal
                        process.send_signal(windows_signal.CTRL_BREAK_EVENT)
                        if process.wait(timeout=20) != 0:
                            raise RuntimeError("Accepted Windows app shutdown failed")
                        outcomes.append({"choice": name, "exit": 0, "receipt": value})
                finally:
                    if process.poll() is None:
                        # Only our retained Popen handle; never image-name/global kills.
                        process.kill()
                        process.wait(timeout=10)
    return {
        "status": "passed",
        "scope": "owned native dialog, readable full terms, default No, No/Yes; --no-browser",
        "terms_sha256": terms_sha256,
        "outcomes": outcomes,
        "not_checked": [
            "default-browser first launch",
            "fresh-machine security",
            "injected MessageBox failure",
        ],
    }


def smoke_source_dialog(terms_path: Path) -> dict:
    """Probe this checkout's agreement dialog only; no packaged-engine claim."""
    if not is_windows():
        raise RuntimeError("Source dialog probe requires an interactive Windows host")
    from backend.windows_terms import TERMS_SHA256, reviewed_text

    terms_path = terms_path.resolve()
    terms = reviewed_text(terms_path.parent)
    if terms_path.name != "WINDOWS-RUNTIME-TERMS.txt":
        raise ValueError("Source probe requires the canonical Windows terms filename")
    api = _Windows()
    outcomes = []
    child = (
        "from pathlib import Path; import sys; "
        "from backend.windows_terms import ensure_accepted; "
        "raise SystemExit(0 if ensure_accepted(Path(sys.argv[1]), None) else 1)"
    )
    for choice, label in ((7, "decline"), (6, "accept")):
        with TemporaryDirectory(prefix=f"bb-source-terms-{label}-") as directory:
            env = clean_environment()
            env["LOCALAPPDATA"] = directory
            process = subprocess.Popen(
                [sys.executable, "-c", child, str(terms_path.parent)],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=0x200,
            )
            try:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Source probe exited before Windows dialog")
                    owners = owned_pids(process.pid, api.parents())
                    dialogs = api.dialogs(owners)
                    if len(dialogs) == 1:
                        dialog = dialogs[0]
                        validate_dialog(dialog, owners, terms)
                        break
                    if len(dialogs) > 1 or time.monotonic() >= deadline:
                        raise RuntimeError("Source probe requires one owned interactive dialog")
                    time.sleep(0.1)
                if process.poll() is not None:
                    raise RuntimeError("Source probe exited before verified action")
                click_choice(
                    api,
                    dialog,
                    owned_pids(process.pid, api.parents()),
                    choice,
                    Path(sys.executable),
                )
                output, _ = process.communicate(timeout=20)
                expected_exit = 1 if choice == 7 else 0
                if process.returncode != expected_exit:
                    raise RuntimeError(
                        "Source probe exit mismatch: " + output.decode("utf-8", errors="replace")
                    )
                if choice == 7:
                    validate_decline_output(output.decode("utf-8", errors="replace"))
                receipt = Path(directory) / "BowlBound/accepted-windows-runtime-terms.json"
                value = json.loads(receipt.read_text("utf-8")) if receipt.exists() else None
                expected_receipt = None if choice == 7 else {"schema": 1, "sha256": TERMS_SHA256}
                if value != expected_receipt:
                    raise RuntimeError("Source probe receipt mismatch")
                outcomes.append({"choice": label, "exit": expected_exit, "receipt": value})
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=10)
    return {
        "status": "passed",
        "scope": "source agreement dialog only; no packaged engine or browser",
        "terms_sha256": TERMS_SHA256,
        "outcomes": outcomes,
        "checks": [
            "owned PID/image",
            "complete terms",
            "default No",
            "monitor and text fit",
            "No/Yes receipts",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dialog", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink():
        parser.error(
            "Choose a fresh Windows source-dialog report path; existing evidence is preserved"
        )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = smoke_source_dialog(args.source_dialog)
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
        report = {"status": "failed", "scope": "source agreement dialog only", "error": str(error)}
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
