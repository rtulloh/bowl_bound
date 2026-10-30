"""Wheel contents: the importer ships, and private or historical data never does."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PREFIXES = ("seasons/", "private-data/", "docs/reference/")
TEAM_DATA_SUFFIXES = (".pdf", ".csv")
WEB_PREFIXES = ("backend/", "frontend/", "node_modules/")


@pytest.fixture(scope="module")
def wheel_package(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[str], str]:
    """Build a wheel from this checkout and return its members and metadata."""
    out = tmp_path_factory.mktemp("wheel")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--quiet", "-w", str(out), str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, "pip could not build a wheel from the checkout"
    wheels = list(out.glob("bowl_bound-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        return names, archive.read(metadata_name).decode("utf-8")


@pytest.fixture(scope="module")
def wheel_names(wheel_package: tuple[list[str], str]) -> list[str]:
    return wheel_package[0]


def test_importer_modules_are_packaged(wheel_names: list[str]) -> None:
    for module in ("tools/pdf_import/cli.py", "tools/pdf_import/export.py"):
        assert module in wheel_names
    assert "tools/pdf_import/metadata.py" in wheel_names


def test_team_codec_is_packaged(wheel_names: list[str]) -> None:
    assert "bowl_bound/team_csv.py" in wheel_names


def test_roster_loader_is_packaged_but_no_roster_data_is(wheel_names: list[str]) -> None:
    assert "bowl_bound/roster.py" in wheel_names
    assert [n for n in wheel_names if n.endswith(("roster.json", "roster-sources.md"))] == []
    assert [n for n in wheel_names if n.endswith(".json")] == []


def test_console_script_points_at_the_importer() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'bowl-bound-import = "tools.pdf_import.cli:main"' in text


def test_pdf_libraries_are_optional_wheel_extras(
    wheel_package: tuple[list[str], str],
) -> None:
    requirements = Parser().parsestr(wheel_package[1]).get_all("Requires-Dist", [])
    normalized = [requirement.lower().replace(" ", "") for requirement in requirements]

    for package in ("pdfplumber", "reportlab"):
        package_requirements = [item for item in normalized if item.startswith(package)]
        assert package_requirements
        assert all(';extra=="' in item for item in package_requirements)
    assert any(item.startswith("pdfplumber") and ';extra=="pdf"' in item for item in normalized)
    assert any(item.startswith("reportlab") and ';extra=="dev"' in item for item in normalized)


def test_no_private_or_team_data_is_packaged(wheel_names: list[str]) -> None:
    assert [n for n in wheel_names if n.startswith(PRIVATE_PREFIXES)] == []
    assert [n for n in wheel_names if n.endswith(TEAM_DATA_SUFFIXES)] == []


def test_web_demo_and_its_build_output_are_not_packaged(wheel_names: list[str]) -> None:
    """The engine ships; the browser demo, its node_modules and dist stay out of the wheel."""
    assert "bowl_bound/session.py" in wheel_names
    assert [n for n in wheel_names if n.startswith(WEB_PREFIXES)] == []
    assert [n for n in wheel_names if "node_modules" in n or n.endswith((".jsx", ".html"))] == []
