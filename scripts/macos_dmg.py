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
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

from .release_package import ReleaseError
from .smoke_standalone import extract_verified, request, smoke_executable

DIRECT_EXECUTABLE = "Contents/MacOS/Bowl-Bound"
PORTABLE_PAYLOAD = "Contents/Resources/BowlBound"
FRAMEWORKS_LINK = "Contents/Frameworks"
FRAMEWORKS_TARGET = Path("Resources/BowlBound/_internal")


def _app_executable(app: Path) -> Path:
    """Locate the game executable in new images and immutable older releases."""
    direct = app / DIRECT_EXECUTABLE
    if direct.is_file():
        return direct
    return app / PORTABLE_PAYLOAD / "Bowl-Bound"


def _check_bundle_links(app: Path) -> None:
    """Allow only the relative link to the verified PyInstaller resources."""
    frameworks = app / FRAMEWORKS_LINK
    target = app / PORTABLE_PAYLOAD / "_internal"
    for path in app.rglob("*"):
        if path.is_symlink() and (
            path != frameworks or path.readlink() != FRAMEWORKS_TARGET or not target.is_dir()
        ):
            raise ReleaseError("Unexpected symlink in macOS app")
    if (app / DIRECT_EXECUTABLE).is_file() and not frameworks.is_symlink():
        raise ReleaseError("Direct macOS app has no PyInstaller Frameworks link")


def seal_app(app: Path) -> None:
    """Seal the completed bundle and reject any strict nested-code failure."""
    subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)


def assemble_app(payload: Path, destination: Path, version: str, *, target: str) -> Path:
    """Install the verified portable executable as the Finder entry point."""
    architectures = {"macos-arm64": "arm64", "macos-x86_64": "x86_64"}
    if target not in architectures:
        raise ReleaseError("App requires a supported macOS target")
    if destination.exists() or destination.is_symlink():
        raise ReleaseError("App destination already exists")
    if payload.is_symlink() or any(path.is_symlink() for path in payload.rglob("*")):
        raise ReleaseError("App payload must not contain symlinks")
    executable = payload / "Bowl-Bound"
    if not executable.is_file() or not (payload / "_internal").is_dir():
        raise ReleaseError("App requires a portable executable and its PyInstaller resources")
    packaged_payload = destination / PORTABLE_PAYLOAD
    shutil.copytree(payload, packaged_payload)
    direct = destination / DIRECT_EXECUTABLE
    direct.parent.mkdir()
    (packaged_payload / "Bowl-Bound").rename(direct)
    direct.chmod(0o755)
    # PyInstaller looks in Contents/Frameworks for executables in Contents/MacOS.
    (destination / FRAMEWORKS_LINK).symlink_to(FRAMEWORKS_TARGET, target_is_directory=True)
    info = {
        "CFBundleName": "Bowl Bound",
        "CFBundleDisplayName": "Bowl Bound",
        "CFBundleIdentifier": "org.bowlbound.game",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": "Bowl-Bound",
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "LSArchitecturePriority": [architectures[target]],
    }
    (destination / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    return destination


def smoke_finder_app(app: Path, version: str) -> None:
    """Launch through Launch Services, verify listener ownership, then stop only it."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 8001))
    executable = _app_executable(app)
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
                mapped_paths = {
                    Path(name[1:]).resolve() for name in mapped_files if name.startswith("n/")
                }
                if executable.resolve() not in mapped_paths:
                    raise ReleaseError("Finder smoke port belongs to another executable")
                pid = owner
                if request("http://127.0.0.1:8001", "/api/health")["status"] != "healthy":
                    raise ReleaseError("Finder application is not healthy")
                if request("http://127.0.0.1:8001", "/api/version")["version"] != version:
                    raise ReleaseError("Finder application version mismatch")
                return
            time.sleep(0.2)
        raise TimeoutError("Finder application did not start")
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
                raise TimeoutError("Finder application did not stop after SIGINT")


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
        assemble_app(
            work / "extracted/BowlBound",
            image / "Bowl Bound.app",
            manifest["version"],
            target=manifest["target"],
        )
        seal_app(image / "Bowl Bound.app")
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
                "finder_launch_smoke": smoke,
                "app_layout": "direct-pyinstaller-entrypoint",
                "browser_download_first_launch": "pending; local image has no browser quarantine",
                "signing": "ad-hoc sealed app; not Developer ID signed or notarized",
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
    work = Path(mkdtemp(prefix="bb-dmg-smoke-"))
    succeeded = False
    try:
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
            mounted_app = mounted / "Bowl Bound.app"
            _check_bundle_links(mounted_app)
            shutil.copytree(mounted_app, app, symlinks=True)
            payload = app / PORTABLE_PAYLOAD
            inventory = json.loads((payload / "ARTIFACT-MANIFEST.json").read_text())
            if inventory["version"] != version or inventory["target"] != target:
                raise ReleaseError("Mounted application version or target mismatch")
            smoke_finder_app(app, version)
            smoke_executable(
                _app_executable(app),
                version,
                work,
                expected_catalog=expected_catalog,
                check_ui=check_ui,
                log_path=log_path,
                payload_root=payload,
            )
        finally:
            subprocess.run(["hdiutil", "detach", str(mounted)], check=True)
        succeeded = True
    finally:
        if succeeded:
            shutil.rmtree(work)
        else:
            app = work / "installed/Bowl Bound.app"
            failure = {
                "passed": False,
                "image": str(image),
                "image_sha256": (
                    hashlib.sha256(image.read_bytes()).hexdigest() if image.is_file() else None
                ),
                "retained_app": str(app),
                "error": traceback.format_exc(),
                "instruction": "Stop any running game process before removing retained resources.",
            }
            (work / "failure.json").write_text(json.dumps(failure, indent=2) + "\n")
            print(f"Failed native smoke retained app and evidence: {app}", file=sys.stderr)


def main() -> None:
    """Build a disk image without modifying portable archives or publishing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    build_dmg(args.archive.resolve(), smoke=args.smoke)


if __name__ == "__main__":
    main()
