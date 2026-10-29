"""Stage exact reviewed inputs, build fresh UI, and assemble private-data-free runtime.

This prepares build inputs, not a public release. No Git operations are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SAMPLES = frozenset(
    ["seasons/SAMPLE-LICENSE.md"]
    + [
        f"seasons/2007/{team}/{name}"
        for team in ("cedar-valley", "harbor-tech")
        for name in ("team.yaml", "offense.csv", "defense.csv", "special.csv")
    ]
    + [f"seasons/2007/provenance/{team}.csv" for team in ("cedar-valley", "harbor-tech")]
)
PUBLIC_FILES = frozenset(
    {
        "LICENSE",
        "README.md",
        "RELEASE_NOTES.md",
        "start.sh",
        "start.bat",
        "docs/README.md",
        "docs/installation.md",
        "docs/playing.md",
        "docs/startup.md",
        "docs/importing-teams.md",
        "docs/python-setup.md",
        "docs/troubleshooting.md",
        "docs/reporting-bugs.md",
        "docs/versioning.md",
        "docs/THIRD_PARTY_NOTICES.md",
    }
)
FRONTEND_CONFIG = frozenset(
    {
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/.npmrc",
        "frontend/index.html",
        "frontend/vite.config.js",
        "frontend/tailwind.config.js",
        "frontend/postcss.config.js",
    }
)


class ReleaseError(ValueError):
    """Release inputs are unsafe, inconsistent, incomplete or stale."""


def _plain(path: Path) -> Path:
    path = path.absolute()
    if ".." in path.parts:
        raise ReleaseError("Paths must not contain parent traversal")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ReleaseError("Release paths must not use symlinks")
    return path


def _name(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or path.as_posix() != name
        or any(part in {".", ".."} for part in path.parts)
        or any(c in name for c in "\\:*?[]\x00")
    ):
        raise ReleaseError("Manifest must contain exact safe relative file paths")
    return name


def _read(root: Path, name: str) -> bytes:
    path = _plain(root / _name(name))
    if not path.is_file():
        raise ReleaseError(f"Missing release input: {name}")
    return path.read_bytes()


def _json(root: Path, name: str) -> dict[str, Any]:
    try:
        data = json.loads(_read(root, name))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ReleaseError(f"Invalid JSON: {name}") from error
    if not isinstance(data, dict):
        raise ReleaseError(f"Expected JSON object: {name}")
    return data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(root: Path) -> dict[str, Any]:
    data = _json(root, "release/manifest.json")
    if set(data) != {"runtime", "frontend", "sample_sha256"}:
        raise ReleaseError("Unknown or missing manifest fields")
    seen: set[str] = set()
    for group in ("runtime", "frontend"):
        if not isinstance(data[group], list) or not data[group]:
            raise ReleaseError("Manifest file groups must be nonempty lists")
        for name in data[group]:
            if not isinstance(name, str):
                raise ReleaseError("Manifest paths must be strings")
            _name(name)
            if name in seen:
                raise ReleaseError("Duplicate manifest file")
            seen.add(name)
            path = PurePosixPath(name)
            if group == "runtime":
                allowed = (
                    name in PUBLIC_FILES
                    or name in SAMPLES
                    or (
                        len(path.parts) == 2
                        and path.parts[0] in {"bowl_bound", "backend"}
                        and path.suffix == ".py"
                    )
                )
            else:
                allowed = name in FRONTEND_CONFIG or (
                    path.parts[:2] == ("frontend", "src")
                    and "test" not in path.parts
                    and ".test." not in name
                    and ".spec." not in name
                    and path.suffix in {".js", ".jsx", ".css"}
                )
            if not allowed:
                raise ReleaseError(f"Not an approved release file category: {name}")
    hashes = data["sample_sha256"]
    if not isinstance(hashes, dict) or set(hashes) != set(data["runtime"]) & SAMPLES:
        raise ReleaseError("Every selected sample must have a pinned hash")
    for name, digest in hashes.items():
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ReleaseError("Invalid sample hash")
        if _sha(_read(root, name)) != digest:
            raise ReleaseError(f"Public sample hash mismatch: {name}")
    return data


def _version(root: Path) -> str:
    text = _read(root, "bowl_bound/__init__.py").decode("utf-8")
    display = re.search(r'^DISPLAY_VERSION = "([^"]+)"$', text, re.MULTILINE)
    python = re.search(r'^__version__ = "([^"]+)"$', text, re.MULTILINE)
    if not display or not python or not re.fullmatch(r"\d+\.\d+\.\d+-alpha\.\d+", display[1]):
        raise ReleaseError("Missing or invalid alpha version metadata")
    if python[1] != display[1].replace("-alpha.", "a"):
        raise ReleaseError("Python and public version mismatch")
    package = _json(root, "frontend/package.json")
    lock = _json(root, "frontend/package-lock.json")
    packages = lock.get("packages")
    root_package = packages.get("") if isinstance(packages, dict) else None
    if (
        package.get("version") != display[1]
        or lock.get("version") != display[1]
        or not isinstance(root_package, dict)
        or root_package.get("version") != display[1]
    ):
        raise ReleaseError("Frontend version mismatch")
    return display[1]


@contextmanager
def _destination(root: Path, destination: Path) -> Iterator[Path]:
    destination = _plain(destination)
    if destination == root or destination in root.parents or root in destination.parents:
        raise ReleaseError("Output must be outside its input tree")
    if destination.exists() or not destination.parent.is_dir():
        raise ReleaseError("Output must be absent and its parent directory must exist")
    with TemporaryDirectory(prefix="bb-release-", dir=destination.parent) as temp:
        working = Path(temp) / "contents"
        working.mkdir()
        yield working
        if destination.exists():
            raise ReleaseError("Output appeared during build; refusing to overwrite")
        working.rename(destination)


def _write(root: Path, name: str, content: bytes) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_json(root: Path, name: str, data: object) -> None:
    _write(root, name, (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def stage_sources(source: Path, destination: Path) -> None:
    """Copy only manifest files into a new transactional build tree."""
    source = _plain(source)
    manifest = _manifest(source)
    _version(source)
    names = [*manifest["runtime"], *manifest["frontend"], "release/manifest.json"]
    # Validate/read all selected inputs before creating any destination.
    contents = {name: _read(source, name) for name in names}
    with _destination(source, destination) as working:
        for name, content in contents.items():
            _write(working, name, content)
        _write_json(working, ".release-inputs.json", {n: _sha(b) for n, b in contents.items()})


def _verify_inputs(stage: Path) -> dict[str, Any]:
    manifest = _manifest(stage)
    expected = _json(stage, ".release-inputs.json")
    names = {*manifest["runtime"], *manifest["frontend"], "release/manifest.json"}
    if set(expected) != names or any(_sha(_read(stage, n)) != expected[n] for n in names):
        raise ReleaseError("Staged inputs changed; create a fresh build stage")
    _version(stage)
    return manifest


def _assets(stage: Path) -> dict[str, str]:
    base = _plain(stage / "frontend/dist")
    if not base.is_dir():
        raise ReleaseError("Built frontend dist is missing")
    files: dict[str, str] = {}
    for path in sorted(base.rglob("*")):
        _plain(path)
        if path.is_dir():
            continue
        name = path.relative_to(base).as_posix()
        if name != "index.html" and not re.fullmatch(r"assets/[\w-]+\.(?:js|css)", name):
            raise ReleaseError("Unexpected built frontend file")
        files[f"frontend/dist/{name}"] = _sha(_read(base, name))
    html = _read(base, "index.html").decode("utf-8")
    refs = re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html)
    if not refs or any(not re.fullmatch(r"/assets/[\w-]+\.(?:js|css)", ref) for ref in refs):
        raise ReleaseError("Frontend index must reference only local built assets")
    expected = {"frontend/dist/index.html", *(f"frontend/dist{ref}" for ref in refs)}
    if set(files) != expected:
        raise ReleaseError("Frontend contains missing or unreferenced assets")
    return files


def build_frontend(stage: Path) -> None:
    """Clean-install/build selected UI inputs using pinned Node/npm, without scripts."""
    stage = _plain(stage)
    _verify_inputs(stage)
    if (stage / "frontend/dist").exists() or (stage / "frontend-build.json").exists():
        raise ReleaseError("Frontend dist/build receipt already exists; use a fresh stage")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or "npm"
    for tool, version in (("node", "v24.22.1"), (npm, "11.19.1")):
        result = subprocess.run([tool, "--version"], check=True, capture_output=True, text=True)
        if result.stdout.strip() != version:
            raise ReleaseError(f"Release builds require {tool} {version}")
    subprocess.run([npm, "ci", "--ignore-scripts"], cwd=stage / "frontend", check=True)
    subprocess.run([npm, "run", "build"], cwd=stage / "frontend", check=True)
    _verify_inputs(stage)
    _write_json(stage, "frontend-build.json", _assets(stage))


def assemble_runtime(stage: Path, destination: Path) -> None:
    """Assemble only runtime/resources and fresh verified assets for a native builder."""
    stage = _plain(stage)
    manifest = _verify_inputs(stage)
    assets = _assets(stage)
    if _json(stage, "frontend-build.json") != assets:
        raise ReleaseError("Built frontend changed since its build receipt")
    names = [*manifest["runtime"], *assets]
    contents = {name: _read(stage, name) for name in names}
    contents["VERSION"] = (_version(stage) + "\n").encode("utf-8")
    with _destination(stage, destination) as working:
        for name, content in contents.items():
            _write(working, name, content)
        _write_json(
            working,
            "MANIFEST.json",
            {"version": _version(stage), "files": {n: _sha(b) for n, b in contents.items()}},
        )


def archive_runtime(runtime: Path, destination: Path) -> None:
    """Write a deterministic ZIP only after inspecting every runtime file/hash."""
    runtime, destination = _plain(runtime), _plain(destination)
    if runtime in destination.parents or destination.exists() or not destination.parent.is_dir():
        raise ReleaseError("Archive output must be absent and outside runtime inputs")
    manifest = _json(runtime, "MANIFEST.json")
    version, hashes = manifest.get("version"), manifest.get("files")
    if (
        not isinstance(version, str)
        or not re.fullmatch(r"\d+\.\d+\.\d+-alpha\.\d+", version)
        or not isinstance(hashes, dict)
    ):
        raise ReleaseError("Invalid runtime manifest")
    actual = set()
    for path in runtime.rglob("*"):
        _plain(path)
        if not path.is_dir():
            actual.add(path.relative_to(runtime).as_posix())
    expected = {*hashes, "MANIFEST.json"}
    if actual != expected:
        raise ReleaseError(
            "Unexpected or missing runtime files: "
            f"extra={sorted(actual - expected)!r}, missing={sorted(expected - actual)!r}"
        )
    contents = {name: _read(runtime, name) for name in sorted(actual)}
    if any(_sha(contents[name]) != digest for name, digest in hashes.items()):
        raise ReleaseError("Runtime file changed since assembly")
    if contents.get("VERSION") != (version + "\n").encode("utf-8"):
        raise ReleaseError("Runtime version mismatch")
    with TemporaryDirectory(prefix="bb-archive-", dir=destination.parent) as temp:
        archive_path = Path(temp) / "runtime.zip"
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in contents.items():
                info = ZipInfo(f"Bowl-Bound-{version}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.create_system = 3
                mode = 0o755 if name.endswith(".sh") else 0o644
                info.external_attr = (0o100000 | mode) << 16
                archive.writestr(info, content)
        # Atomic create-only publication of our own temporary file, never replace user work.
        os.link(archive_path, destination)


def main() -> None:
    """Prepare a build stage, its UI, or a verified runtime directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage")
    stage.add_argument("source", type=Path)
    stage.add_argument("destination", type=Path)
    frontend = commands.add_parser("frontend")
    frontend.add_argument("stage", type=Path)
    runtime = commands.add_parser("runtime")
    runtime.add_argument("stage", type=Path)
    runtime.add_argument("destination", type=Path)
    archive = commands.add_parser("archive")
    archive.add_argument("runtime", type=Path)
    archive.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "stage":
            stage_sources(args.source, args.destination)
        elif args.command == "frontend":
            build_frontend(args.stage)
        elif args.command == "runtime":
            assemble_runtime(args.stage, args.destination)
        else:
            archive_runtime(args.runtime, args.destination)
    except (ReleaseError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release preparation failed: {error}\n")


if __name__ == "__main__":
    main()
