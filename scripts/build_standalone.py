"""Build inspected native onedir ZIPs from exact staged sources, never the worktree."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .release_package import (
    PUBLIC_FILES,
    ReleaseError,
    _destination,
    _plain,
    _write_json,
    archive_runtime,
    assemble_runtime,
    build_frontend,
    stage_sources,
)

TARGETS = {
    "macos-arm64": ("Darwin", "arm64", "Bowl-Bound"),
    "macos-x86_64": ("Darwin", "x86_64", "Bowl-Bound"),
    "windows-x64": ("Windows", "x86_64", "BowlBound.exe"),
}
RUNTIME_DISTS = (
    "PyYAML",
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic-core",
    "uvicorn",
    "h11",
    "click",
    "anyio",
    "idna",
    "typing-extensions",
    "annotated-types",
    "typing-inspection",
    "annotated-doc",
    "opentelemetry-api",
    "pyinstaller",
)


def check_target(target: str, system: str, machine: str) -> str:
    """Refuse cross-builds and 32-bit targets; return the exact executable filename."""
    if target not in TARGETS:
        raise ReleaseError("Unknown standalone target")
    expected_os, expected_arch, executable = TARGETS[target]
    architecture = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine.lower(), machine.lower())
    if (system, architecture) != (expected_os, expected_arch):
        raise ReleaseError("Standalone builds require a matching native OS and architecture")
    return executable


def _runtime_files(runtime: Path) -> dict[str, str]:
    with TemporaryDirectory(prefix="bb-native-verify-") as directory:
        archive_runtime(runtime, Path(directory).resolve() / "verified.zip")
    return json.loads((runtime / "MANIFEST.json").read_text(encoding="utf-8"))["files"]


def write_spec(runtime: Path, work: Path, target: str) -> Path:
    """Generate an explicit data recipe only after validating the assembled runtime."""
    hashes = _runtime_files(runtime)
    executable = TARGETS[target][2].removesuffix(".exe")
    data = [
        (str(runtime / name), str(Path(name).parent)) for name in hashes if not name.endswith(".py")
    ]
    if (work / "notices").is_dir():
        data.append((str(work / "notices"), "THIRD_PARTY"))
    entry = work / "entry.py"
    entry.write_text(
        "from backend.launcher import main\nraise SystemExit(main())\n", encoding="utf-8"
    )
    hidden = [
        "uvicorn.logging",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan.on",
    ]
    spec = work / "BowlBound.spec"
    spec.write_text(
        f"a = Analysis([{str(entry)!r}], pathex=[{str(runtime)!r}], datas={data!r}, "
        f"hiddenimports={hidden!r}, excludes=['tkinter', 'pytest', 'tools', 'tests'], optimize=0)\n"
        "pyz = PYZ(a.pure)\n"
        f"exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name={executable!r}, "
        "console=True, strip=False, upx=False)\n"
        f"app = COLLECT(exe, a.binaries, a.datas, name={executable!r}, strip=False, upx=False)\n",
        encoding="utf-8",
    )
    return spec


def materialize(source: Path, destination: Path) -> None:
    """Flatten only internal freezer symlinks so portable ZIP extraction is reliable."""
    source = source.resolve()
    for path in source.rglob("*"):
        if path.is_symlink():
            try:
                resolved = path.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise ReleaseError("Invalid freezer symlink") from error
            if source not in resolved.parents or resolved in path.parents:
                raise ReleaseError("Freezer symlink escapes output or forms a cycle")
    shutil.copytree(source, destination, symlinks=False)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_bundle(bundle: Path, runtime: Path, output: Path, target: str) -> Path:
    """Inspect resources and archive an exact inventory with a SHA256 sidecar."""
    hashes = _runtime_files(runtime)
    version = (runtime / "VERSION").read_text(encoding="utf-8").strip()
    archive = output / f"BowlBound-{version}-{target}.zip"
    if archive.exists() or archive.with_suffix(".zip.sha256").exists():
        raise ReleaseError("Standalone archive output already exists")
    actual: dict[str, str] = {}
    for path in sorted(bundle.rglob("*")):
        _plain(path)
        if path.is_dir():
            continue
        name = path.relative_to(bundle).as_posix()
        if re.search(
            r"(^|/)(private-data|dev-notes|opencode.json|roster.json|node_modules)(/|$)|[.]pdf$",
            name,
            re.I,
        ):
            raise ReleaseError("Forbidden private/development file in native output")
        if name.startswith("_internal/seasons/") and name.removeprefix("_internal/") not in hashes:
            raise ReleaseError("Unselected team resource in native output")
        actual[name] = _sha(path)
    for name, digest in hashes.items():
        if not name.endswith(".py") and actual.get("_internal/" + name) != digest:
            raise ReleaseError("Native resource missing or changed after assembly")
    if TARGETS[target][2] not in actual:
        raise ReleaseError("Native executable is missing or incorrectly named")
    inventory = {"version": version, "target": target, "files": actual}
    _write_json(bundle, "ARTIFACT-MANIFEST.json", inventory)
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as zipped:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                name = path.relative_to(bundle).as_posix()
                info = ZipInfo("BowlBound/" + name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (
                    0o100000 | (0o755 if os.access(path, os.X_OK) else 0o644)
                ) << 16
                info.compress_type = ZIP_DEFLATED
                zipped.writestr(info, path.read_bytes())
    with archive.with_suffix(".zip.sha256").open("x", encoding="utf-8") as stream:
        stream.write(f"{_sha(archive)}  {archive.name}\n")
    _write_json(output, archive.stem + ".manifest.json", inventory)
    return archive


def verify_environment(source: Path) -> None:
    """Require the complete pinned graph and no installed/editable source project."""
    from packaging.requirements import Requirement

    if sys.maxsize <= 2**32:
        raise ReleaseError("A 64-bit build interpreter is required")
    installed = metadata.distributions(
        path=list({sysconfig.get_path("purelib"), sysconfig.get_path("platlib")})
    )
    if any(
        re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower() == "bowl-bound" for dist in installed
    ):
        raise ReleaseError("Use a clean build environment without the installed source project")
    for line in (
        (source / "release/requirements-native.txt").read_text(encoding="utf-8").splitlines()
    ):
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        if metadata.version(requirement.name) not in requirement.specifier:
            raise ReleaseError("Native dependency version differs from the reviewed lock")


def write_notices(stage: Path, destination: Path) -> None:
    """Collect installed Python/package/frontend notices without private host paths."""
    destination.mkdir()
    inventory: dict[str, object] = {}
    for name in RUNTIME_DISTS:
        distribution = metadata.distribution(name)
        texts = [
            item
            for item in distribution.files or ()
            if re.match(r"(?i)^(license|copying|notice)([._-]|$)", item.name)
        ]
        if not texts:
            raise ReleaseError(f"No dependency license text found for {name}")
        copied = []
        for index, item in enumerate(texts):
            original = Path(distribution.locate_file(item))
            target = destination / name / f"{index}-{item.name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            copied.append(target.relative_to(destination).as_posix())
        inventory[name] = {"version": distribution.version, "notices": copied}
    python_license = next(
        (
            path
            for path in (
                Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
                Path(sys.base_prefix) / "LICENSE.txt",
                Path(sys.base_prefix) / "LICENSE",
            )
            if path.is_file()
        ),
        None,
    )
    if python_license is None:
        raise ReleaseError("Python runtime license text is missing")
    shutil.copyfile(python_license, destination / "PYTHON-LICENSE.txt")
    inventory["Python"] = {"version": platform.python_version(), "notices": ["PYTHON-LICENSE.txt"]}
    for name in ("react", "react-dom", "scheduler"):
        folder = stage / "frontend/node_modules" / name
        data = json.loads((folder / "package.json").read_text(encoding="utf-8"))
        target = destination / f"{name}-LICENSE.txt"
        shutil.copyfile(folder / "LICENSE", target)
        inventory[name] = {"version": data["version"], "notices": [target.name]}
    _write_json(destination, "DEPENDENCIES.json", inventory)


def inspect_modules(executable: Path, runtime: Path) -> None:
    """Reject unselected application modules accidentally captured during analysis."""
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(executable))
    pyz_name = next(name for name in archive.toc if name.endswith(".pyz"))
    pyz = archive.open_embedded_archive(pyz_name)
    allowed = {
        name.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
        for name in _runtime_files(runtime)
        if name.endswith(".py")
    }
    modules = set(pyz.toc)
    if not {"backend.launcher", "backend.app", "bowl_bound.session"} <= modules:
        raise ReleaseError("Frozen application modules are incomplete")
    for name in modules:
        if name.split(".")[0] in {"tools", "tests"}:
            raise ReleaseError("Development module captured in executable")
        if name.split(".")[0] in {"bowl_bound", "backend"} and name not in allowed:
            raise ReleaseError("Unselected application module captured in executable")


def build(source: Path, output: Path, target: str) -> None:
    """Stage, freeze, inspect and archive in fresh transactional external directories."""
    source = _plain(source)
    executable = check_target(target, platform.system(), platform.machine())
    verify_environment(source)
    with _destination(source, output) as artifacts:
        with TemporaryDirectory(prefix="bb-freezer-", dir=output.parent) as directory:
            work = Path(directory)
            stage, runtime = work / "stage", work / "runtime"
            stage_sources(source, stage)
            build_frontend(stage)
            assemble_runtime(stage, runtime)
            write_notices(stage, work / "notices")
            spec = write_spec(runtime, work, target)
            environment = {
                key: value
                for key, value in os.environ.items()
                if key not in {"PYTHONPATH", "PYTHONHOME"}
            }
            environment["PYTHONNOUSERSITE"] = "1"
            # Hook children inherit env, while -I makes the parent ignore it.
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-B",  # Keep the verified runtime pristine during analysis.
                    "-m",
                    "PyInstaller",
                    "--noconfirm",
                    "--clean",
                    "--distpath",
                    str(work / "dist"),
                    "--workpath",
                    str(work / "analysis"),
                    str(spec),
                ],
                cwd=work,
                env=environment,
                check=True,
            )
            frozen = work / "dist" / executable.removesuffix(".exe")
            inspect_modules(frozen / executable, runtime)
            bundle = work / "portable"
            materialize(frozen, bundle)
            for name in PUBLIC_FILES:
                if (runtime / name).is_file():
                    destination = bundle / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(runtime / name, destination)
                    if name.endswith(".sh"):
                        destination.chmod(0o755)
            shutil.copytree(work / "notices", bundle / "THIRD_PARTY")
            archive_bundle(bundle, runtime, artifacts, target)


def main() -> None:
    """Build one native target, without GitHub/Git/tag/release operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=TARGETS, required=True)
    args = parser.parse_args()
    try:
        build(args.source, args.output, args.target)
    except (
        ReleaseError,
        OSError,
        subprocess.CalledProcessError,
        metadata.PackageNotFoundError,
    ) as error:
        parser.exit(1, f"Standalone build failed: {error}\n")


if __name__ == "__main__":
    main()
