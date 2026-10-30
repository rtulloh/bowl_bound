"""Release identity is separate from gameplay/save compatibility."""

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

import bowl_bound
from backend.app import create_app
from bowl_bound.save_game import ENGINE_PROFILE

ROOT = Path(__file__).resolve().parents[1]


def test_alpha_version_agrees_across_package_api_and_frontend(tmp_path: Path) -> None:
    python_version = "0.1.0a2"
    display_version = "0.1.0-alpha.2"
    assert bowl_bound.__version__ == python_version
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^version = "([^"]+)"$', metadata, re.MULTILINE)[1] == python_version
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))
    assert package["version"] == lock["version"] == display_version
    assert lock["packages"][""]["version"] == display_version
    app = create_app(tmp_path)
    assert app.version == python_version
    with TestClient(app) as client:
        response = client.get("/api/version")
        assert response.status_code == 200
        assert response.json() == {"version": display_version, "python_version": python_version}
    assert ENGINE_PROFILE == "bowl-bound-m21-v1"


def test_mit_license_retains_notice_and_excludes_third_party_material() -> None:
    license_file = ROOT / "LICENSE"
    assert license_file.is_file()
    text = license_file.read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Copyright (c) 2026 rtulloh" in text
    assert "Permission is hereby granted, free of charge" in text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in text
    attribution = (ROOT / "docs/ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "**undecided**" not in attribution
    assert "CC0-1.0" in attribution
    assert "not covered" in attribution
