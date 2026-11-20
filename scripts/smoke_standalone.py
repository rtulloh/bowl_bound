"""Verify and smoke an extracted standalone without importing the source game."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from tempfile import mkdtemp
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


def request(base: str, path: str, body: object = None, *, timeout: float = 5) -> object:
    """Send local JSON only; no external service or source-game import is needed."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    with urlopen(
        Request(base + path, data=data, headers={"Content-Type": "application/json"}),
        timeout=timeout,
    ) as response:
        return json.load(response)


def catalog_from_inventory(files: dict[str, str]) -> frozenset[str]:
    """Derive expected teams from the verified artifact's exact resource inventory."""
    resources = {name.removeprefix("_internal/") for name in files}
    teams = frozenset(
        name.removeprefix("seasons/").removesuffix("/team.yaml")
        for name in resources
        if re.fullmatch(r"seasons/\d{4}/[a-z0-9][a-z0-9-]*/team.yaml", name)
    )
    if (
        len(teams) < 2
        or any(
            f"seasons/{team}/{name}" not in resources
            for team in teams
            for name in ("team.yaml", "offense.csv", "defense.csv", "special.csv")
        )
        or any(
            f"seasons/{team.split('/')[0]}/provenance/{team.split('/')[1]}.csv" not in resources
            for team in teams
        )
    ):
        raise ValueError("Artifact inventory must contain at least two complete team bundles")
    return teams


def exercise(base: str, version: str, expected_teams: frozenset[str]) -> None:
    """Reconcile exact catalog/assets and a snap plus save/load for every packaged team."""
    assert request(base, "/api/health")["status"] == "healthy"
    assert request(base, "/api/version")["version"] == version
    # Discovery validates every chart and provenance bundle, unlike health or one action.
    started = time.monotonic()
    catalog = request(base, "/api/teams", timeout=30)
    assert not catalog["problems"]
    assert len(catalog["teams"]) == len(expected_teams)
    assert {team["id"] for team in catalog["teams"]} == expected_teams
    print(f"Verified {len(expected_teams)}-team catalog in {time.monotonic() - started:.2f}s")
    with urlopen(base + "/", timeout=5) as response:
        html = response.read().decode("utf-8")
    assets = re.findall(r'(?:src|href)="(/assets/[^" ]+)"', html)
    assert assets and any(name.endswith(".js") for name in assets)
    for name in assets:
        with urlopen(base + name, timeout=5) as response:
            assert response.status == 200 and response.read()
    teams = sorted(expected_teams)
    for index, home in enumerate(teams):
        game = request(
            base,
            "/api/games",
            {"home": home, "away": teams[(index + 1) % len(teams)], "seed": 7},
        )
        path = "/api/games/" + game["game_id"]
        played = request(base, path + "/snap", {"play": "1", "defense": "A"})
        assert played["view"] != game["view"]
        saved = request(base, path + "/save")
        loaded = request(base, "/api/games/load", saved)
        assert loaded["view"] == played["view"] and loaded["game_id"] != game["game_id"]


def clean_environment() -> dict[str, str]:
    """Prevent source checkout overrides from satisfying packaged imports."""
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        env.pop(key, None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def requires_windows_terms(version: str) -> bool:
    """New patches require explicit terms; immutable older releases remain testable."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-alpha\.\d+)?", version)
    if match is None:
        raise ValueError("Invalid Windows runtime terms release version")
    return tuple(map(int, match.groups())) >= (1, 1, 1)


def windows_terms_digest(bundle: Path, manifest: dict) -> str | None:
    """Verify both approved terms copies before explicit smoke-run agreement."""
    if manifest.get("target") != "windows-x64" or not requires_windows_terms(manifest["version"]):
        return None
    digests = []
    for name in ("WINDOWS-RUNTIME-TERMS.txt", "_internal/WINDOWS-RUNTIME-TERMS.txt"):
        path = bundle / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Windows runtime terms are missing or unsafe")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if manifest["files"].get(name) != digest:
            raise ValueError("Windows runtime terms differ from verified inventory")
        digests.append(digest)
    if len(set(digests)) != 1:
        raise ValueError("Windows runtime terms copies differ")
    return digests[0]


def smoke_executable(
    executable: Path,
    version: str,
    work: Path,
    *,
    expected_catalog: frozenset[str] | None = None,
    check_ui: Callable[[str], None] | None = None,
    log_path: Path | None = None,
    expected_terms_sha256: str | None = None,
) -> None:
    """Exercise an extracted or installed binary and require graceful shutdown."""
    inventory = json.loads((executable.parent / "ARTIFACT-MANIFEST.json").read_text("utf-8"))
    expected_teams = catalog_from_inventory(inventory["files"])
    if expected_catalog is not None and expected_teams != expected_catalog:
        raise ValueError("Installed artifact catalog differs from approved release catalog")
    terms_digest = windows_terms_digest(executable.parent, inventory)
    if expected_terms_sha256 is not None and terms_digest != expected_terms_sha256:
        raise ValueError("Windows runtime terms differ from approved release source")
    if terms_digest and os.name == "nt":
        from .smoke_windows_terms import smoke_windows_terms

        gui_work = log_path.parent if log_path else work
        gui_path = gui_work / "windows-runtime-terms-gui.json"
        if gui_path.exists() or gui_path.is_symlink():
            raise ValueError("Choose fresh Windows runtime terms GUI evidence paths")
        gui = smoke_windows_terms(executable, version, gui_work, terms_digest)
        if gui.get("status") != "passed" or gui.get("terms_sha256") != terms_digest:
            raise RuntimeError("Windows runtime terms GUI smoke did not qualify")
        with gui_path.open("x", encoding="utf-8") as stream:
            json.dump(gui, stream, indent=2)
            stream.write("\n")
    terms_arguments = ["--accept-windows-runtime-terms", terms_digest] if terms_digest else []
    env = clean_environment()
    if terms_digest:
        env["LOCALAPPDATA"] = str(work / "isolated-local-appdata")
    actual = subprocess.check_output(
        [str(executable), "--version"], cwd=work, text=True, timeout=30, env=env
    )
    assert actual.strip() == "Bowl Bound " + version
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with (log_path or work / "server.log").open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(executable), "--no-browser", "--port", str(port), *terms_arguments],
            cwd=work,
            env=env,
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
            exercise(base, version, expected_teams)
            if check_ui is not None:
                check_ui(base)
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
    """Smoke exact bytes, preserving failure resources and create-only receipts."""
    report = archive.with_suffix(".zip.receipt.json")
    if report.exists() or report.is_symlink():
        raise ValueError("Choose a fresh standalone smoke receipt path")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    work = Path(mkdtemp(prefix="bb-native-smoke-", dir=archive.parent)).resolve()
    receipt: dict[str, object] = {
        "passed": False,
        "artifact": archive.name,
        "sha256": digest,
    }
    try:
        manifest = extract_verified(archive, work)
        receipt["version"], receipt["target"] = manifest["version"], manifest["target"]
        executable = (
            work
            / "BowlBound"
            / ("BowlBound.exe" if manifest["target"] == "windows-x64" else "Bowl-Bound")
        )
        smoke_executable(executable, manifest["version"], work)
        receipt["passed"] = True
    except BaseException as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        gui = work / "windows-runtime-terms-gui.json"
        if gui.is_file():
            try:
                receipt["windows_runtime_terms_gui"] = json.loads(gui.read_text("utf-8"))
            except (OSError, ValueError) as error:
                receipt["passed"] = False
                receipt["gui_evidence_error"] = str(error)
        if receipt["passed"]:
            try:
                shutil.rmtree(work)
            except OSError as error:
                receipt["cleanup_warning"] = str(error)
                receipt["retained_work"] = str(work)
        else:
            receipt["retained_work"] = str(work)
            print(f"Standalone smoke failed; resources and logs retained at {work}")
        with report.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    if not receipt["passed"]:
        raise RuntimeError("Standalone GUI evidence did not qualify; inspect the retained receipt")
    print(
        "Standalone smoke passed: version, UI/assets, exact catalog, "
        "every-team snap/save/load, shutdown"
    )


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
