"""Explicit, per-user assent for the reviewed frozen Windows runtime terms."""

from __future__ import annotations

import hashlib
import json
import os
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


def _ask(text: str) -> bool | None:
    """Use Windows' native dialog, with No as the default; no browser is started."""
    import ctypes

    try:
        message = (
            text + "\n\nChoose Yes to agree to these conditions and continue. Choose No to quit."
        )
        # MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2. Only IDYES records assent.
        windows_api: Any = ctypes
        answer = windows_api.windll.user32.MessageBoxW(
            None, message, "Bowl Bound Windows terms", 0x124
        )
        return answer == 6
    except (AttributeError, OSError):
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
