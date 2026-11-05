"""Standalone extraction rejects malicious or corrupt synthetic archives."""

import hashlib
import io
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile, ZipInfo

import pytest

from scripts.smoke_standalone import extract_verified


def test_native_smoke_exercises_every_manifest_team_and_reconciles_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import smoke_standalone

    expected = frozenset({"2011/alpha", "2011/beta", "2011/gamma"})
    created: list[dict[str, Any]] = []
    catalog = {"teams": [{"id": team} for team in sorted(expected)], "problems": []}

    def request(base: str, path: str, body: Any = None, *, timeout: float = 5) -> Any:
        if path == "/api/health":
            return {"status": "healthy"}
        if path == "/api/version":
            return {"version": "0.1.0-alpha.6"}
        if path == "/api/teams":
            return catalog
        if path == "/api/games":
            created.append(body)
            return {"game_id": "original", "view": "before"}
        if path.endswith("/snap"):
            return {"view": "after"}
        if path.endswith("/save"):
            return {"saved": True}
        if path == "/api/games/load":
            assert body == {"saved": True}
            return {"view": "after", "game_id": "loaded"}
        raise AssertionError(path)

    monkeypatch.setattr(smoke_standalone, "request", request)

    class Response(io.BytesIO):
        status = 200

    monkeypatch.setattr(
        smoke_standalone,
        "urlopen",
        lambda url, timeout: Response(b'<script src="/assets/app.js"></script>'),
    )
    smoke_standalone.exercise("http://synthetic", "0.1.0-alpha.6", expected)
    assert {game["home"] for game in created} == expected
    assert all(game["away"] in expected and game["home"] != game["away"] for game in created)

    with pytest.raises(AssertionError):
        smoke_standalone.exercise("http://synthetic", "0.1.0-alpha.6", expected - {"2011/gamma"})
    with pytest.raises(AssertionError):
        smoke_standalone.exercise("http://synthetic", "0.1.0-alpha.6", expected | {"2011/delta"})
    catalog["teams"].append({"id": "2011/alpha"})
    with pytest.raises(AssertionError):
        smoke_standalone.exercise("http://synthetic", "0.1.0-alpha.6", expected)


def test_expected_catalog_comes_from_complete_verified_artifact_bundles() -> None:
    from scripts.smoke_standalone import catalog_from_inventory

    files = {
        f"_internal/seasons/2011/{team}/{name}": "synthetic-hash"
        for team in ("alpha", "beta", "gamma")
        for name in ("team.yaml", "offense.csv", "defense.csv", "special.csv")
    }
    files.update(
        {
            f"_internal/seasons/2011/provenance/{team}.csv": "synthetic-hash"
            for team in ("alpha", "beta", "gamma")
        }
    )
    files["_internal/docs/playing.md"] = "synthetic-doc-hash"
    assert catalog_from_inventory(files) == frozenset({"2011/alpha", "2011/beta", "2011/gamma"})
    provenance = files.pop("_internal/seasons/2011/provenance/gamma.csv")
    with pytest.raises(ValueError, match="complete team bundles"):
        catalog_from_inventory(files)
    files["_internal/seasons/2011/provenance/gamma.csv"] = provenance
    del files["_internal/seasons/2011/gamma/special.csv"]
    with pytest.raises(ValueError, match="complete team bundles"):
        catalog_from_inventory(files)
    with pytest.raises(ValueError, match="at least two"):
        catalog_from_inventory({})


def test_native_smoke_allows_bounded_full_catalog_discovery_after_fast_health() -> None:
    """Catalog validation may take longer than one ordinary action request."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from time import sleep

    from scripts.smoke_standalone import exercise

    expected = frozenset({"2011/alpha", "2011/beta"})

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def reply(self, value: object, *, html: bool = False) -> None:
            data = value if html else json.dumps(value).encode()
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The red regression deliberately closes its timed-out client.

        def do_GET(self) -> None:
            if self.path == "/api/health":
                self.reply({"status": "healthy"})
            elif self.path == "/api/version":
                self.reply({"version": "0.1.0-alpha.6"})
            elif self.path == "/api/teams":
                sleep(6)
                self.reply({"teams": [{"id": key} for key in expected], "problems": []})
            elif self.path.endswith("/save"):
                self.reply({"saved": True})
            elif self.path == "/":
                self.reply(b'<script src="/assets/app.js"></script>', html=True)
            elif self.path == "/assets/app.js":
                self.reply(b"synthetic", html=True)
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/api/games":
                self.reply({"game_id": "original", "view": "before"})
            elif self.path == "/api/games/load":
                self.reply({"game_id": "loaded", "view": "after"})
            elif self.path.endswith("/snap"):
                self.reply({"view": "after"})
            else:
                self.send_error(404)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            exercise(f"http://127.0.0.1:{server.server_port}", "0.1.0-alpha.6", expected)
        finally:
            server.shutdown()
            thread.join(timeout=2)


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
