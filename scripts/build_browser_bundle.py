"""Stage Bowl Bound teams and the pinned Python runtime for static hosting."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .release_package import SAMPLES, ReleaseError, _json, _manifest, _plain, _read, _sha

PYODIDE_VERSION = "0.27.7"
PYODIDE_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
LICENSE_URLS = {
    "LICENSE-pyodide": f"https://cdn.jsdelivr.net/gh/pyodide/pyodide@{PYODIDE_VERSION}/LICENSE",
    "LICENSE-python": "https://cdn.jsdelivr.net/gh/python/cpython@v3.12.7/LICENSE",
}
# Core files, licenses, and the complete PyYAML and Pydantic package closure.
RUNTIME_HASHES = {
    "LICENSE-pyodide": "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5",
    "LICENSE-python": "3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf",
    "annotated_types-0.6.0-py3-none-any.whl": (
        "9733de5d59580defb40ad7bd8a5d53a0fac03de7a13028d95cacc4e81945c97c"
    ),
    "pydantic-2.10.5-py3-none-any.whl": (
        "dd344e353e3c3a2d972c1198744a4f4ba1e2ce586e903187cca9fdaafb46c63d"
    ),
    "pydantic_core-2.27.2-cp312-cp312-pyodide_2024_0_wasm32.whl": (
        "eefd735db79e36e3425e4a821fc9df6cb172d2845f0d4a2a1038eb5f4d5c1d0c"
    ),
    "pyodide-lock.json": "9c45b916001a750f4102fc287494f3eab215909c7535c626a20db80fd6333e2c",
    "pyodide.asm.js": "6b4c90de5b7172873f04f21884d0e9d2274e305fe32116558fe3e4fbe3618d51",
    "pyodide.asm.wasm": "a50dd1843f805a0b7c45b61037ee0d7b26dfe85efe0e18ef95a34ad24e401f5f",
    "pyodide.mjs": "04c052c815abb0bf2981fa38c2dfa58e3120ee5288c956df2b2a15e301782c5f",
    "python_stdlib.zip": "16611534726e5d8ac2bd8f926410b2dcb8d6f49aa24913463533b457a2115c16",
    "pyyaml-6.0.2-cp312-cp312-pyodide_2024_0_wasm32.whl": (
        "444d034ede13ca0a2961a1215838fb7d4cf6fa98ba7fe5e2a09e5063180af2bf"
    ),
    "typing_extensions-4.11.0-py3-none-any.whl": (
        "c3f00b6653202513b1f7813ad3c466510ceecc599a37d665a31dcfb5ac7049b9"
    ),
}
# Reviewed import closure of the browser bridge. No HTTP or CLI entry points.
PYTHON_FILES = frozenset(
    {
        "LICENSE",
        "backend/__init__.py",
        "backend/browser_bridge.py",
        "backend/operations.py",
        "bowl_bound/__init__.py",
        "bowl_bound/chart_coaching.py",
        "bowl_bound/chart_view.py",
        "bowl_bound/coaching.py",
        "bowl_bound/coaching_evaluation.py",
        "bowl_bound/coaching_probabilities.py",
        "bowl_bound/coaching_profiles.py",
        "bowl_bound/coaching_session.py",
        "bowl_bound/coaching_situations.py",
        "bowl_bound/commentary.py",
        "bowl_bound/decision_facts.py",
        "bowl_bound/dice.py",
        "bowl_bound/difficulty.py",
        "bowl_bound/game_state.py",
        "bowl_bound/models.py",
        "bowl_bound/normalization.py",
        "bowl_bound/overtime.py",
        "bowl_bound/penalties.py",
        "bowl_bound/penalty_yardage.py",
        "bowl_bound/player_coaching.py",
        "bowl_bound/regulation.py",
        "bowl_bound/resolution.py",
        "bowl_bound/return_recovery.py",
        "bowl_bound/roster.py",
        "bowl_bound/rules_summary.py",
        "bowl_bound/save_game.py",
        "bowl_bound/scoring.py",
        "bowl_bound/session.py",
        "bowl_bound/special_teams.py",
        "backend/played_season.py",
        "backend/season_templates.py",
        "backend/season_template_data.py",
        "bowl_bound/statistics.py",
        "bowl_bound/team_catalog.py",
        "bowl_bound/team_csv.py",
        "bowl_bound/timing.py",
        "bowl_bound/turnovers.py",
        "bowl_bound/variable_yardage.py",
    }
)


def _inventory(name: str, content: bytes) -> dict[str, str | int]:
    return {"path": name, "bytes": len(content), "sha256": _sha(content)}


def _python_archive(
    root: Path, *, include_release_teams: bool
) -> tuple[bytes, list[dict[str, str | int]], dict[str, list[str]]]:
    release = _manifest(root) if include_release_teams else _json(root, "release/manifest.json")
    hashes = release.get("sample_sha256")
    selected = release.get("runtime")
    if (
        not isinstance(hashes, dict)
        or set(hashes) != SAMPLES
        or not isinstance(selected, list)
        or not SAMPLES.issubset(selected)
    ):
        raise ReleaseError("The release manifest must pin all fictional sample assets")

    notices = set()
    if include_release_teams:
        hashes = {
            **hashes,
            **release.get("generated_sha256", {}),
            **release.get("roster_sha256", {}),
        }
        notices = {
            "seasons/GENERATED-LICENSE.md",
            "docs/generated-charts.md",
            "docs/generated-charts-1972.md",
            "docs/season-schedules.md",
        }
    seasons: dict[str, list[str]] = {}
    for name in sorted(hashes):
        if name.endswith("/team.yaml"):
            _, year, team, _ = name.split("/")
            seasons.setdefault(year, []).append(team)
    inventory = []
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name in sorted(PYTHON_FILES | hashes.keys() | notices):
            data = _read(root, name)
            entry = _inventory(name, data)
            if name in hashes and entry["sha256"] != hashes[name]:
                raise ReleaseError(f"Public team file hash mismatch: {name}")
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
            inventory.append(entry)
    return buffer.getvalue(), inventory, seasons


def _runtime_asset(name: str, runtime_dir: Path | None) -> bytes:
    if runtime_dir is not None:
        return _read(runtime_dir, name)
    with urlopen(LICENSE_URLS.get(name, f"{PYODIDE_URL}{name}"), timeout=30) as response:
        return response.read()


def build_bundle(
    source_root: Path,
    output: Path,
    *,
    runtime_dir: Path | None = None,
    include_release_teams: bool = False,
) -> dict[str, Any]:
    """Write a new browser staging directory using only reviewed assets."""
    source_root = _plain(source_root)
    output = _plain(output)
    if output.exists():
        raise ReleaseError(f"Browser staging directory already exists: {output}")

    archive, inventory, seasons = _python_archive(
        source_root, include_release_teams=include_release_teams
    )
    manifest = {
        "version": 1,
        "scope": "public-release-teams" if include_release_teams else "public-fictional-samples",
        "seasons": seasons,
        "files": [
            {"url": "python.zip", "mount": "/app", "bytes": len(archive), "sha256": _sha(archive)}
        ],
        "inventory": inventory,
        "pyodide": {"version": PYODIDE_VERSION, "files": []},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".browser-", dir=output.parent) as scratch:
        stage = Path(scratch) / "browser"
        runtime = stage / "pyodide"
        runtime.mkdir(parents=True)
        for name, expected in RUNTIME_HASHES.items():
            data = _runtime_asset(name, runtime_dir)
            entry = _inventory(name, data)
            if entry["sha256"] != expected:
                raise ReleaseError(f"Pyodide runtime hash mismatch: {name}")
            (runtime / name).write_bytes(data)
            manifest["pyodide"]["files"].append(entry)
        (stage / "python.zip").write_bytes(archive)
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        stage.rename(output)
    return manifest


def main() -> None:
    """Stage the game archive and self-hosted runtime."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True, help="New browser staging directory")
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        help="Read pinned runtime files from an existing local directory",
    )
    parser.add_argument(
        "--include-release-teams",
        action="store_true",
        help="Include only the generated teams and rosters pinned for release",
    )
    args = parser.parse_args()
    try:
        manifest = build_bundle(
            args.source_root,
            args.output,
            runtime_dir=args.runtime_dir,
            include_release_teams=args.include_release_teams,
        )
    except (OSError, ReleaseError) as error:
        parser.error(str(error))
    print(f"Staged {len(manifest['inventory'])} browser game assets in {args.output}")
    print(f"python.zip SHA-256: {manifest['files'][0]['sha256']}")


if __name__ == "__main__":
    main()
