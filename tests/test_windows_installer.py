"""Installer file lists are generated from synthetic, verified package inventories."""

import json
from pathlib import Path

import pytest

from scripts import windows_installer as installer
from scripts.release_package import ReleaseError
from tests.test_release_package import put


def test_installer_lists_every_file_and_only_uninstalls_known_files(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    put(bundle, "BowlBound.exe", "synthetic executable")
    put(bundle, "_internal/example.dat", "synthetic resource")
    files = {"BowlBound.exe": "a" * 64, "_internal/example.dat": "b" * 64}
    put(bundle, "ARTIFACT-MANIFEST.json", json.dumps({"files": files}))
    work = tmp_path / "recipe"
    work.mkdir()
    installer.write_file_lists(bundle, work)
    install = (work / "install-files.nsh").read_text()
    uninstall = (work / "uninstall-files.nsh").read_text()
    assert 'File "/oname=BowlBound.exe"' in install
    assert 'File "/oname=example.dat"' in install
    assert 'Delete "$INSTDIR\\BowlBound.exe"' in uninstall
    assert 'Delete "$INSTDIR\\_internal\\example.dat"' in uninstall
    assert 'Delete "$INSTDIR\\ARTIFACT-MANIFEST.json"' in uninstall
    assert 'RMDir "$INSTDIR\\_internal"' in uninstall
    assert "/r" not in uninstall.lower() and "*" not in uninstall
    assert "$DOCUMENTS" not in uninstall


def test_unknown_file_not_silently_added_to_installer(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    put(bundle, "ARTIFACT-MANIFEST.json", '{"files":{}}')
    put(bundle, "private.txt", "DO NOT SHIP")
    with pytest.raises(ReleaseError, match="inventory"):
        installer.write_file_lists(bundle, tmp_path)


def test_nsis_requires_no_admin_and_preserves_personal_libraries() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "release/windows/installer.nsi").read_text()
    assert "RequestExecutionLevel user" in text
    assert "$LOCALAPPDATA\\Programs\\BowlBound" in text
    assert "SetShellVarContext current" in text and "HKCU" in text
    assert "BowlBound.exe" in text and "Uninstall.exe" in text
    assert "HKLM" not in text and "RMDir /r" not in text
    assert "CreateShortCut" in text and "UninstallString" in text


def test_workflow_requires_installer_compile_and_installed_app_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github/workflows/build.yml").read_text()
    assert "scripts.windows_installer" in text and "--smoke" in text
    assert "nsis --version=3.11" in text
    assert "*.exe" in text


@pytest.mark.parametrize("name", ["wild*", "wild?", "trailing.", "CON", 'quote"'])
def test_installer_rejects_windows_aliases_and_wildcards(tmp_path: Path, name: str) -> None:
    bundle = tmp_path / "bundle"
    put(bundle, name, "synthetic")
    put(bundle, "ARTIFACT-MANIFEST.json", json.dumps({"files": {name: "a" * 64}}))
    with pytest.raises(ReleaseError, match="path"):
        installer.write_file_lists(bundle, tmp_path)


@pytest.mark.parametrize(
    "name", ["BowlBound.exe", "file with spaces.dat", "sub dir/literal $name.dat"]
)
def test_output_name_is_one_quoted_nsis_option(tmp_path: Path, name: str) -> None:
    """NSIS requires quotes around the whole /oname= option, not its value."""
    bundle = tmp_path / "bundle with $literal spaces"
    put(bundle, name, "synthetic payload")
    put(bundle, "ARTIFACT-MANIFEST.json", json.dumps({"files": {name: "a" * 64}}))
    work = tmp_path / "recipe"
    work.mkdir()
    installer.write_file_lists(bundle, work)
    install = (work / "install-files.nsh").read_text()
    filename = Path(name).name.replace("$", "$$")
    source = str(bundle / name).replace("$", "$$")
    assert f'File "/oname={filename}" "{source}"' in install.splitlines()
    assert 'File /oname="' not in install
    assert len([line for line in install.splitlines() if line.startswith("File ")]) == 2
    uninstall = (work / "uninstall-files.nsh").read_text()
    escaped_name = name.replace("/", "\\").replace("$", "$$")
    assert f'Delete "$INSTDIR\\{escaped_name}"' in uninstall.splitlines()
    assert "*" not in uninstall and "RMDir /r" not in uninstall
