"""Verify and smoke an extracted standalone without importing the source game."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import time
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile


def validate_relative_path(name: str) -> None:
    """Reject noncanonical paths and names Windows aliases or treats as wildcards."""
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or not path.parts
        or re.search(r'[\x00-\x1f<>:"\\|?*]', name)
        or any(
            part in {".", ".."}
            or part.endswith((".", " "))
            or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:[.].*)?", part)
            for part in path.parts
        )
    ):
        raise ValueError("Unsafe archive or installer path")


def extract_verified(archive: Path, destination: Path) -> dict:
    """Verify archive checksum, paths and every manifest entry before execution."""
    if destination.is_symlink() or (
        destination.exists() and (not destination.is_dir() or any(destination.iterdir()))
    ):
        raise ValueError("Extraction destination must be absent or empty")
    checksum = archive.with_suffix(".zip.sha256").read_text(encoding="utf-8").split()
    if checksum != [hashlib.sha256(archive.read_bytes()).hexdigest(), archive.name]:
        raise ValueError("Standalone archive checksum mismatch")
    with ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError("Duplicate archive path")
        for name in names:
            validate_relative_path(name)
            if not name.startswith("BowlBound/"):
                raise ValueError("Unsafe archive path")
            if (zipped.getinfo(name).external_attr >> 16) & 0o170000 != 0o100000:
                raise ValueError("Archive entry is not a regular file")
        manifest = json.loads(zipped.read("BowlBound/ARTIFACT-MANIFEST.json"))
        expected = {"BowlBound/" + name for name in manifest["files"]}
        if set(names) != expected | {"BowlBound/ARTIFACT-MANIFEST.json"}:
            raise ValueError("Standalone inventory mismatch")
        for name, digest in manifest["files"].items():
            if hashlib.sha256(zipped.read("BowlBound/" + name)).hexdigest() != digest:
                raise ValueError("Standalone file checksum mismatch")
        zipped.extractall(destination)
        for info in zipped.infolist():
            (destination / info.filename).chmod((info.external_attr >> 16) & 0o777)
    return manifest


def request(base: str, path: str, body: object = None) -> object:
    """Send local JSON only; no external service or source-game import is needed."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    with urlopen(
        Request(base + path, data=data, headers={"Content-Type": "application/json"}), timeout=5
    ) as response:
        return json.load(response)


def exercise(base: str, version: str) -> None:
    """Reconcile assets, exact samples, a real snap, and a save/load round trip."""
    assert request(base, "/api/health")["status"] == "healthy"
    assert request(base, "/api/version")["version"] == version
    catalog = request(base, "/api/teams")
    assert not catalog["problems"]
    assert {team["id"] for team in catalog["teams"]} == {
        "2007/cedar-valley",
        "2007/harbor-tech",
    }
    with urlopen(base + "/", timeout=5) as response:
        html = response.read().decode("utf-8")
    assets = re.findall(r'(?:src|href)="(/assets/[^" ]+)"', html)
    assert assets and any(name.endswith(".js") for name in assets)
    for name in assets:
        with urlopen(base + name, timeout=5) as response:
            assert response.status == 200 and response.read()
    game = request(
        base,
        "/api/games",
        {
            "home": "2007/cedar-valley",
            "away": "2007/harbor-tech",
            "seed": 7,
        },
    )
    path = "/api/games/" + game["game_id"]
    played = request(base, path + "/snap", {"play": "1", "defense": "A"})
    assert played["view"] != game["view"]
    saved = request(base, path + "/save")
    loaded = request(base, "/api/games/load", saved)
    assert loaded["view"] == played["view"] and loaded["game_id"] != game["game_id"]


def smoke_executable(executable: Path, version: str, work: Path) -> None:
    """Exercise an extracted or installed binary and require graceful shutdown."""
    actual = subprocess.check_output(
        [str(executable), "--version"], cwd=work, text=True, timeout=30
    )
    assert actual.strip() == "Bowl Bound " + version
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with (work / "server.log").open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(executable), "--no-browser", "--port", str(port)],
            cwd=work,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Standalone server exited before readiness")
                try:
                    if request(base, "/api/health")["status"] == "healthy":
                        break
                except (URLError, OSError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("Standalone server did not become ready")
                time.sleep(0.2)
            exercise(base, version)
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
            if process.wait(timeout=20) != 0:
                raise RuntimeError("Standalone shutdown returned failure")
        except BaseException:
            log.seek(0)
            print(log.read())
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def smoke(archive: Path) -> None:
    """Start only the extracted executable; source modules cannot satisfy imports."""
    with TemporaryDirectory(prefix="bb-native-smoke-") as directory:
        work = Path(directory)
        manifest = extract_verified(archive, work)
        executable = (
            work
            / "BowlBound"
            / ("BowlBound.exe" if manifest["target"] == "windows-x64" else "Bowl-Bound")
        )
        smoke_executable(executable, manifest["version"], work)
    print("Standalone smoke passed: version, UI/assets, two samples, snap, save/load, shutdown")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    archives = list(args.directory.glob("*.zip"))
    if len(archives) != 1:
        parser.error("expected exactly one standalone ZIP in the artifact directory")
    smoke(archives[0])


if __name__ == "__main__":
    main()
