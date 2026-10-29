"""Compile and smoke a per-user NSIS installer from an inspected Windows ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from .release_package import ReleaseError
from .smoke_standalone import extract_verified, smoke_executable, validate_relative_path

UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\BowlBound"


def _quoted(text: str) -> str:
    if "\n" in text or "\r" in text:
        raise ReleaseError("Newlines are not allowed in installer paths")
    return text.replace("$", "$$").replace('"', '$\\"')


def write_file_lists(bundle: Path, work: Path) -> None:
    """Generate exact install/deletion lists; preserve any unrelated user files."""
    files = set(
        json.loads((bundle / "ARTIFACT-MANIFEST.json").read_text(encoding="utf-8"))["files"]
    )
    files.add("ARTIFACT-MANIFEST.json")
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if files != actual or any(p.is_symlink() for p in bundle.rglob("*")):
        raise ReleaseError("Installer inventory differs from verified bundle")
    install, uninstall = [], []
    folders = set()
    for name in sorted(files):
        relative = PurePosixPath(name)
        try:
            validate_relative_path(name)
        except ValueError as error:
            raise ReleaseError("Unsafe installer inventory path") from error
        windows_name = name.replace("/", "\\")
        parent = str(relative.parent).replace("/", "\\")
        install.append(
            'SetOutPath "$INSTDIR' + ("\\" + _quoted(parent) if parent != "." else "") + '"'
        )
        install.append(f'File "/oname={_quoted(relative.name)}" "{_quoted(str(bundle / name))}"')
        uninstall.append(f'Delete "$INSTDIR\\{_quoted(windows_name)}"')
        folders.update(str(p).replace("/", "\\") for p in relative.parents if str(p) != ".")
    uninstall.extend(
        f'RMDir "$INSTDIR\\{_quoted(folder)}"'
        for folder in sorted(folders, key=lambda p: (-p.count("\\"), p))
    )
    (work / "install-files.nsh").write_text("\n".join(install) + "\n", encoding="utf-8")
    (work / "uninstall-files.nsh").write_text("\n".join(uninstall) + "\n", encoding="utf-8")


def smoke_installer(installer: Path, version: str) -> None:
    """Test installed UI/save and uninstall while keeping an unrelated user file."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY):
            raise ReleaseError("Installer smoke must not replace an existing user installation")
    except FileNotFoundError:
        pass
    with TemporaryDirectory(prefix="bb-install-smoke-") as directory:
        work = Path(directory)
        installed = work / "installed"
        subprocess.run([str(installer), "/S", f"/D={installed}"], check=True, timeout=180)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
                assert winreg.QueryValueEx(key, "DisplayVersion")[0] == version
                assert Path(winreg.QueryValueEx(key, "InstallLocation")[0]) == installed
            smoke_executable(installed / "BowlBound.exe", version, work)
            (installed / "keep-personal.txt").write_text("keep", encoding="utf-8")
        finally:
            subprocess.run(
                [str(installed / "Uninstall.exe"), "/S", f"_?={installed}"], check=True, timeout=120
            )
        assert not (installed / "BowlBound.exe").exists()
        assert (installed / "keep-personal.txt").read_text() == "keep"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY):
                raise AssertionError("Uninstaller registration was not removed")
        except FileNotFoundError:
            pass
    print(
        "Windows installer smoke passed: install, registry, game/save, uninstall, "
        "preserved user file"
    )


def build(directory: Path, makensis: Path, source: Path, *, smoke: bool) -> None:
    """Create installer/checksum without replacing artifacts or publishing a release."""
    if os.name != "nt":
        raise ReleaseError("The Windows installer must be built on its native runner")
    if subprocess.check_output([str(makensis), "/VERSION"], text=True).strip() != "v3.11":
        raise ReleaseError("Expected the reviewed NSIS 3.11 compiler")
    archives = list(directory.glob("*.zip"))
    if len(archives) != 1:
        raise ReleaseError("Expected exactly one verified Windows ZIP")
    with TemporaryDirectory(prefix="bb-installer-", dir=directory.parent) as temporary:
        work = Path(temporary)
        manifest = extract_verified(archives[0], work)
        if manifest["target"] != "windows-x64":
            raise ReleaseError("Installer input is not the Windows x64 bundle")
        version = manifest["version"]
        if not re.fullmatch(r"\d+\.\d+\.\d+-alpha\.\d+", version):
            raise ReleaseError("Invalid installer version")
        bundle = work / "BowlBound"
        nsis_license = next(
            (
                makensis.parent / name
                for name in ("COPYING", "COPYING.txt", "LICENSE")
                if (makensis.parent / name).is_file()
            ),
            None,
        )
        if nsis_license is None:
            raise ReleaseError("NSIS license notice is missing")
        notice = "THIRD_PARTY/NSIS-COPYING.txt"
        (bundle / notice).write_bytes(nsis_license.read_bytes())
        manifest["files"][notice] = hashlib.sha256((bundle / notice).read_bytes()).hexdigest()
        (bundle / "ARTIFACT-MANIFEST.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        write_file_lists(bundle, work)
        name = f"BowlBoundSetup-{version}-windows-x64.exe"
        output = directory / name
        if output.exists() or output.with_suffix(".exe.sha256").exists():
            raise ReleaseError("Installer output already exists")
        arguments = {
            "DISPLAY_VERSION": version,
            "BUNDLE_DIR": str(bundle),
            "OUTPUT_FILE": str(work / name),
            "INSTALL_LIST": str(work / "install-files.nsh"),
            "UNINSTALL_LIST": str(work / "uninstall-files.nsh"),
        }
        subprocess.run(
            [
                str(makensis),
                *[f"/D{key}={value}" for key, value in arguments.items()],
                str(source / "release/windows/installer.nsi"),
            ],
            check=True,
            timeout=180,
        )
        if smoke:
            smoke_installer(work / name, version)
        digest = hashlib.sha256((work / name).read_bytes()).hexdigest()
        with output.open("xb") as stream:
            stream.write((work / name).read_bytes())
        with output.with_suffix(".exe.sha256").open("x", encoding="utf-8") as stream:
            stream.write(f"{digest}  {name}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--makensis", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    build(args.directory, args.makensis, args.source, smoke=args.smoke)


if __name__ == "__main__":
    main()
