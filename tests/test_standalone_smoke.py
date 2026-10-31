"""Standalone extraction rejects malicious or corrupt synthetic archives."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from scripts.smoke_standalone import extract_verified


def write_archive(
    tmp_path: Path, name: str, contents: bytes, *, mode: int = 0o100644, mirror_name: bool = False
) -> Path:
    archive = tmp_path / "app.zip"
    manifest = {
        "version": "0.1.0-alpha.3",
        "target": "macos-arm64",
        "files": {
            (name.removeprefix("BowlBound/") if mirror_name else "Bowl-Bound"): hashlib.sha256(
                b"synthetic"
            ).hexdigest()
        },
    }
    with ZipFile(archive, "w") as zipped:
        for path, data, permissions in [
            ("BowlBound/ARTIFACT-MANIFEST.json", json.dumps(manifest).encode(), 0o100644),
            (name, contents, mode),
        ]:
            info = ZipInfo(path)
            info.external_attr = permissions << 16
            zipped.writestr(info, data)
    archive.with_suffix(".zip.sha256").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name
    )
    return archive


def test_verified_extract_restores_executable_permission(tmp_path: Path) -> None:
    archive = write_archive(tmp_path, "BowlBound/Bowl-Bound", b"synthetic", mode=0o100755)
    destination = tmp_path / "extracted"
    manifest = extract_verified(archive, destination)
    assert manifest["version"] == "0.1.0-alpha.3"
    assert (destination / "BowlBound/Bowl-Bound").read_bytes() == b"synthetic"
    assert (destination / "BowlBound/Bowl-Bound").stat().st_mode & 0o111


@pytest.mark.parametrize(
    "path",
    [
        "BowlBound/../escape",
        "/absolute",
        "BowlBound/C:escape",
        "BowlBound\\escape",
        "BowlBound/./Bowl-Bound",
        "BowlBound//Bowl-Bound",
        "BowlBound/Bowl-Bound.",
        "BowlBound/CON",
        "BowlBound/file*",
        "BowlBound/file?",
    ],
)
def test_unsafe_archive_never_extracts(tmp_path: Path, path: str) -> None:
    archive = write_archive(tmp_path, path, b"synthetic", mirror_name=True)
    destination = tmp_path / "extracted"
    with pytest.raises(ValueError, match="path"):
        extract_verified(archive, destination)
    assert not destination.exists()


@pytest.mark.parametrize("mutation", ["checksum", "symlink", "content", "extra"])
def test_corrupt_or_unselected_entries_never_extract(tmp_path: Path, mutation: str) -> None:
    archive = write_archive(
        tmp_path,
        "BowlBound/extra" if mutation == "extra" else "BowlBound/Bowl-Bound",
        b"modified" if mutation == "content" else b"synthetic",
        mode=0o120777 if mutation == "symlink" else 0o100755,
    )
    if mutation == "checksum":
        archive.with_suffix(".zip.sha256").write_text("invalid")
    destination = tmp_path / "extracted"
    with pytest.raises(ValueError):
        extract_verified(archive, destination)
    assert not destination.exists()


def test_extraction_requires_fresh_destination(tmp_path: Path) -> None:
    archive = write_archive(tmp_path, "BowlBound/Bowl-Bound", b"synthetic")
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep.txt").write_text("keep")
    with pytest.raises(ValueError, match="destination"):
        extract_verified(archive, destination)
    assert (destination / "keep.txt").read_text() == "keep"
    assert not (destination / "BowlBound").exists()
