"""Compose a Finder-launchable macOS disk image from an inspected portable ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from .release_package import ReleaseError
from .smoke_standalone import extract_verified, request, smoke_executable


def assemble_app(payload: Path, destination: Path, version: str) -> Path:
    """Wrap exact portable resources with an explicit Terminal lifecycle launcher."""
    if destination.exists() or destination.is_symlink():
        raise ReleaseError("App destination already exists")
    if payload.is_symlink() or any(path.is_symlink() for path in payload.rglob("*")):
        raise ReleaseError("App payload must not contain symlinks")
    macos = destination / "Contents/MacOS"
    resources = destination / "Contents/Resources"
    macos.mkdir(parents=True)
    resources.mkdir()
    shutil.copytree(payload, macos / "BowlBound")
    info = {
        "CFBundleName": "Bowl Bound",
        "CFBundleDisplayName": "Bowl Bound",
        "CFBundleIdentifier": "org.bowlbound.game",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": "launch",
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "LSUIElement": True,
    }
    (destination / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    launch = macos / "launch"
    launch.write_text(
        "#!/bin/bash\nset -euo pipefail\n"
        'APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\n'
        'exec /usr/bin/open -a Terminal "$APP_DIR/../Resources/start.command"\n',
        encoding="utf-8",
    )
    command = resources / "start.command"
    command.write_text(
        "#!/bin/bash\nset -euo pipefail\n"
        'APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\n'
        'exec "$APP_DIR/../MacOS/BowlBound/start.sh" "$@"\n',
        encoding="utf-8",
    )
    launch.chmod(0o755)
    command.chmod(0o755)
    return destination


def smoke_finder_app(app: Path, version: str) -> None:
    """Launch through Finder/Terminal, verify listener ownership, then stop only it."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 8001))
    executable = app / "Contents/MacOS/BowlBound/Bowl-Bound"
    subprocess.run(["/usr/bin/open", "-n", str(app)], check=True, timeout=10)
    deadline = time.monotonic() + 60
    pid: int | None = None
    try:
        while time.monotonic() < deadline:
            result = subprocess.run(
                ["/usr/sbin/lsof", "-nP", "-t", "-iTCP:8001", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            ids = result.stdout.split()
            if ids:
                if len(set(ids)) != 1:
                    raise ReleaseError("Finder smoke found multiple listener processes")
                owner = int(ids[0])
                mapped_files = subprocess.check_output(
                    ["/usr/sbin/lsof", "-a", "-p", str(owner), "-d", "txt", "-Fn"],
                    text=True,
                    timeout=10,
                ).splitlines()
                if "n" + str(executable) not in mapped_files:
                    raise ReleaseError("Finder smoke port belongs to another executable")
                pid = owner
                if request("http://127.0.0.1:8001", "/api/health")["status"] != "healthy":
                    raise ReleaseError("Finder application is not healthy")
                if request("http://127.0.0.1:8001", "/api/version")["version"] != version:
                    raise ReleaseError("Finder application version mismatch")
                return
            time.sleep(0.2)
        raise TimeoutError("Finder/Terminal application did not start")
    finally:
        if pid is not None:
            os.kill(pid, signal.SIGINT)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("Finder application did not stop after Ctrl+C signal")


def build_dmg(archive: Path, *, smoke: bool = False) -> Path:
    """Verify input inventory, build read-only DMG, then test its mounted app copy."""
    output = archive.with_suffix(".dmg")
    if any(
        path.exists() or path.is_symlink() for path in (output, output.with_suffix(".dmg.sha256"))
    ):
        raise ReleaseError("DMG output already exists")
    receipt_path = output.with_suffix(".dmg.receipt.json")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ReleaseError("DMG receipt already exists")
    with TemporaryDirectory(prefix="bb-macos-") as directory:
        work = Path(directory)
        manifest = extract_verified(archive, work / "extracted")
        if manifest["target"] not in {"macos-arm64", "macos-x86_64"}:
            raise ReleaseError("DMG requires a macOS portable archive")
        candidate = work / output.name
        image = work / "image"
        image.mkdir()
        assemble_app(work / "extracted/BowlBound", image / "Bowl Bound.app", manifest["version"])
        (image / "Applications").symlink_to("/Applications")
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                "Bowl Bound",
                "-srcfolder",
                str(image),
                "-format",
                "UDZO",
                str(candidate),
            ],
            check=True,
        )
        subprocess.run(["hdiutil", "verify", str(candidate)], check=True)
        if smoke:
            smoke_dmg(candidate, manifest["version"], manifest["target"])
        shutil.move(candidate, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".dmg.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    output.with_suffix(".dmg.receipt.json").write_text(
        json.dumps(
            {
                "source_zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "dmg_sha256": digest,
                "mounted_payload_smoke": smoke,
                "finder_terminal_launch_smoke": smoke,
                "browser_download_first_launch": "pending; local image has no browser quarantine",
                "signing": "unsigned wrapper; not Developer ID signed or notarized",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def smoke_dmg(
    image: Path,
    version: str,
    target: str,
    *,
    expected_catalog: frozenset[str] | None = None,
    check_ui: Callable[[str], None] | None = None,
    log_path: Path | None = None,
) -> None:
    """Mount exact image bytes and exercise a copied app through Finder and its API."""
    with TemporaryDirectory(prefix="bb-dmg-smoke-") as directory:
        work = Path(directory)
        mounted = work / "mounted"
        mounted.mkdir()
        subprocess.run(
            [
                "hdiutil",
                "attach",
                "-readonly",
                "-nobrowse",
                "-mountpoint",
                str(mounted),
                str(image),
            ],
            check=True,
        )
        try:
            app = work / "installed/Bowl Bound.app"
            app.parent.mkdir()
            shutil.copytree(mounted / "Bowl Bound.app", app)
            payload = app / "Contents/MacOS/BowlBound"
            inventory = json.loads((payload / "ARTIFACT-MANIFEST.json").read_text())
            if inventory["version"] != version or inventory["target"] != target:
                raise ReleaseError("Mounted application version or target mismatch")
            smoke_finder_app(app, version)
            smoke_executable(
                payload / "Bowl-Bound",
                version,
                work,
                expected_catalog=expected_catalog,
                check_ui=check_ui,
                log_path=log_path,
            )
        finally:
            subprocess.run(["hdiutil", "detach", str(mounted)], check=True)


def main() -> None:
    """Build a disk image without modifying portable archives or publishing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    build_dmg(args.archive.resolve(), smoke=args.smoke)


if __name__ == "__main__":
    main()
