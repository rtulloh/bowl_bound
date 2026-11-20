"""Explicit, per-user assent for the reviewed frozen Windows runtime terms."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
from collections.abc import Callable
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

TERMS_FILENAME = "WINDOWS-RUNTIME-TERMS.txt"
TERMS_SHA256 = "7fb48ece6c4ef5203b050d60225c83ee7c1d9a10f4fb8519dc05472988b059b2"


def required() -> bool:
    """Source execution and non-Windows bundles do not use this agreement gate."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def reviewed_text(root: Path) -> str:
    """Read the exact reviewed terms; changed or missing resources fail closed."""
    data = (root / TERMS_FILENAME).read_bytes()
    if hashlib.sha256(data).hexdigest() != TERMS_SHA256:
        raise ValueError("Windows runtime terms are missing or changed; re-extract the app.")
    return data.decode("utf-8")


def _dialog_bounds(work: tuple[int, int, int, int], dpi: int) -> tuple[int, int, int, int]:
    """Center a bounded outer window inside the selected monitor work area."""
    left, top, right, bottom = work
    margin = max(8, 16 * dpi // 96)
    width = min(760 * dpi // 96, right - left - 2 * margin)
    height = min(640 * dpi // 96, bottom - top - 2 * margin)
    if width < 300 or height < 200:
        raise ValueError("Monitor work area is too small to display the Windows terms.")
    return left + (right - left - width) // 2, top + (bottom - top - height) // 2, width, height


def _control_bounds(width: int, height: int, dpi: int) -> dict[int, tuple[int, int, int, int]]:
    margin = max(8, 12 * dpi // 96)
    button_width, button_height = 90 * dpi // 96, 28 * dpi // 96
    button_y = height - margin - button_height
    return {
        1001: (margin, margin, width - 2 * margin, button_y - 2 * margin),
        6: (width - 2 * margin - 2 * button_width, button_y, button_width, button_height),
        7: (width - margin - button_width, button_y, button_width, button_height),
    }


def _dialog_template(message: str) -> bytes:
    """Build a standard Unicode DLGTEMPLATE with a scrollable read-only EDIT."""

    def string(value: str) -> bytes:
        return (value + "\0").encode("utf-16-le")

    # DS_MODALFRAME | DS_SETFONT | WS_POPUP | WS_CAPTION | WS_SYSMENU.
    data = bytearray(struct.pack("<IIHhhhh", 0x80C800C0, 0, 3, 0, 0, 400, 300))
    data += struct.pack("<HH", 0, 0) + string("Bowl Bound Windows terms")
    data += struct.pack("<H", 9) + string("Segoe UI")
    for control_id, style, window_class, text in (
        (1001, 0x50A10844, 0x81, message.replace("\r\n", "\n").replace("\n", "\r\n")),
        (6, 0x50010000, 0x80, "Yes"),
        (7, 0x50010001, 0x80, "No"),
    ):
        data += b"\0" * (-len(data) % 4)
        data += struct.pack("<IIhhhhH", style, 0, 0, 0, 10, 10, control_id)
        data += struct.pack("<HH", 0xFFFF, window_class) + string(text) + struct.pack("<H", 0)
    return bytes(data)


def _dialog_action(message_id: int, wparam: int) -> int | None:
    if message_id == 0x10:  # WM_CLOSE
        return 7
    if message_id == 0x111 and wparam & 0xFFFF in (2, 6, 7):  # WM_COMMAND
        return 6 if wparam & 0xFFFF == 6 else 7
    return None


def _show_scrollable_dialog(message: str) -> int:
    """Run an owned native modal dialog; native failures never imply assent."""
    import ctypes
    from ctypes import wintypes

    api: Any = ctypes
    user = api.WinDLL("user32", use_last_error=True)
    kernel = api.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    callback_type = api.WINFUNCTYPE(
        ctypes.c_ssize_t, pointer, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t
    )
    user.DialogBoxIndirectParamW.argtypes = [
        pointer,
        pointer,
        pointer,
        callback_type,
        ctypes.c_ssize_t,
    ]
    user.DialogBoxIndirectParamW.restype = ctypes.c_ssize_t
    user.GetDlgItem.argtypes = [pointer, ctypes.c_int]
    user.GetDlgItem.restype = pointer
    user.SetFocus.argtypes = [pointer]
    user.SetFocus.restype = pointer
    user.EndDialog.argtypes = [pointer, ctypes.c_ssize_t]
    user.SendMessageW.argtypes = [pointer, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    user.SendMessageW.restype = ctypes.c_ssize_t
    user.SetWindowPos.argtypes = [
        pointer,
        pointer,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user.GetClientRect.argtypes = [pointer, ctypes.POINTER(wintypes.RECT)]
    user.MonitorFromWindow.argtypes = [pointer, wintypes.DWORD]
    user.MonitorFromWindow.restype = pointer

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    user.GetMonitorInfoW.argtypes = [pointer, ctypes.POINTER(MonitorInfo)]
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype = pointer
    failed = False

    def callback(hwnd: Any, message_id: int, wparam: int, lparam: int) -> int:
        nonlocal failed
        try:
            if message_id == 0x110:  # WM_INITDIALOG
                info = MonitorInfo()
                info.cbSize = ctypes.sizeof(info)
                if not user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
                    raise OSError("Cannot inspect monitor work area")
                dpi = 96
                if hasattr(user, "GetDpiForWindow"):
                    user.GetDpiForWindow.argtypes = [pointer]
                    dpi = user.GetDpiForWindow(hwnd) or 96
                rect = info.rcWork
                bounds = _dialog_bounds((rect.left, rect.top, rect.right, rect.bottom), dpi)
                if not user.SetWindowPos(hwnd, None, *bounds, 0x14):  # NOZORDER | NOACTIVATE
                    raise OSError("Cannot position Windows terms dialog")
                client = wintypes.RECT()
                if not user.GetClientRect(hwnd, ctypes.byref(client)):
                    raise OSError("Cannot inspect Windows terms dialog")
                for control_id, box in _control_bounds(client.right, client.bottom, dpi).items():
                    if not user.SetWindowPos(user.GetDlgItem(hwnd, control_id), None, *box, 0x14):
                        raise OSError("Cannot position Windows terms control")
                user.SendMessageW(hwnd, 0x401, 7, 0)  # DM_SETDEFID: No
                user.SetFocus(user.GetDlgItem(hwnd, 7))
                return 0  # Focus was explicitly assigned.
            action = _dialog_action(message_id, wparam)
            if action is not None:
                user.EndDialog(hwnd, action)
                return 1
        except (OSError, ValueError):
            failed = True
            user.EndDialog(hwnd, -1)
            return 1
        return 0

    template = ctypes.create_string_buffer(_dialog_template(message))
    callback_pointer = callback_type(callback)
    result = user.DialogBoxIndirectParamW(
        kernel.GetModuleHandleW(None), template, None, callback_pointer, 0
    )
    return -1 if failed else int(result)


def _ask(text: str) -> bool | None:
    """Show scrollable Windows terms, with No as the default and close action."""
    try:
        answer = _show_scrollable_dialog(
            text + "\n\nChoose Yes to agree to these conditions and continue. Choose No to quit."
        )
        return None if answer == -1 else answer == 6
    except (AttributeError, OSError, ValueError):
        return None


def ensure_accepted(
    root: Path,
    explicit_hash: str | None,
    *,
    ask: Callable[[str], bool | None] | None = None,
) -> bool:
    """Require explicit current-hash assent and an atomic per-user receipt."""
    temporary: Path | None = None
    try:
        text = reviewed_text(root)
        if explicit_hash is not None and explicit_hash != TERMS_SHA256:
            raise ValueError("Acceptance hash does not match the reviewed Windows runtime terms.")
        appdata = os.environ.get("LOCALAPPDATA")
        if not appdata:
            raise ValueError(
                "LOCALAPPDATA is unavailable; Windows terms acceptance cannot be saved."
            )
        receipt = Path(appdata) / "BowlBound/accepted-windows-runtime-terms.json"
        expected = {"schema": 1, "sha256": TERMS_SHA256}
        try:
            if json.loads(receipt.read_text(encoding="utf-8")) == expected:
                return True
        except (OSError, ValueError):
            pass
        if explicit_hash is None and (ask or _ask)(text) is not True:
            print(
                "Windows runtime terms were not accepted; the game has not started.",
                file=sys.stderr,
            )
            return False
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=receipt.parent, prefix=".terms-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(expected, stream)
            stream.write("\n")
        temporary.replace(receipt)
        temporary = None
        return True
    except (OSError, ValueError) as error:
        print(f"Windows runtime terms: {error}", file=sys.stderr)
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                print("Could not remove the temporary Windows terms receipt.", file=sys.stderr)
