"""Review fixes: no leaked chart text, narrow exceptions, round-trip before write."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bowl_bound.models import BoundingBox, Provenance
from bowl_bound.normalization import ChartColor, NormalizationError, normalize_cell
from tools.pdf_import import cli
from tools.pdf_import.export import ImportValidationError, build_team
from tools.pdf_import.metadata import TeamMetadata

SECRET = "PRIVATE-CHART-TOKEN"


def _provenance(text: str) -> Provenance:
    return Provenance("a" * 64, "secret-team.pdf", 7, BoundingBox(0, 0, 1, 1), text, (1, 2, 3))


def test_normalization_error_does_not_echo_chart_text_or_filename() -> None:
    with pytest.raises(NormalizationError) as error:
        normalize_cell(_provenance(SECRET), ChartColor.WHITE)
    message = str(error.value)
    assert SECRET not in message
    assert "secret-team.pdf" not in message
    assert "page 7" in message


def test_normalization_error_keeps_location_for_local_triage() -> None:
    with pytest.raises(NormalizationError) as error:
        normalize_cell(_provenance("mystery"), ChartColor.WHITE)
    assert error.value.page == 7
    assert error.value.bounding_box == BoundingBox(0, 0, 1, 1)


def test_programming_errors_are_not_reported_as_invalid_documents() -> None:
    """A bad CellPosition is a bug, not a document problem."""
    broken = SimpleNamespace(section="offense", column="not-a-play", roll=10, defense=None)
    cell = SimpleNamespace(
        provenance=_provenance(""), rgb_color=(255, 255, 255), text="", rotation=0
    )
    with pytest.raises(Exception) as error:
        build_team("Synthetic", 2002, [(broken, cell)], TeamMetadata(200, range(10, 26), (), ()))
    assert not isinstance(error.value, ImportValidationError)


def test_bounding_box_rejects_huge_ints_with_a_normal_error() -> None:
    with pytest.raises((TypeError, ValueError)):
        BoundingBox(0, 0, 10**400, 1)


# --- CLI -----------------------------------------------------------------

GOOD_CHART = {
    "name": "Synthetic State",
    "season": 2002,
    "offense": [],
    "supplemental": [],
    "defense": [],
    "special_teams": [],
    "pat_outcomes": [],
}


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(b"placeholder")
    return path


def test_teams_are_round_tripped_before_anything_is_written(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A chart the CSV codec cannot represent must stop the run before any write."""
    from dataclasses import replace

    from tests.test_pdf_cli_export import _team

    team = _team("Synthetic State")
    bad_cell = replace(team.chart.offense[0].cell, variable=None)
    chart = replace(
        team.chart,
        offense=(replace(team.chart.offense[0], cell=bad_cell), *team.chart.offense[1:]),
    )
    monkeypatch.setattr(cli, "export_document", lambda path: [replace(team, chart=chart)])
    monkeypatch.setattr(cli, "_verify_teams", lambda teams: (_ for _ in ()).throw(ValueError("x")))
    root = tmp_path / "seasons"
    assert cli.main([str(source), "--export", "--output", str(root)]) == 1
    assert not root.exists()


def test_export_failure_message_names_the_right_operation(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def explode(path: Path) -> None:
        raise KeyError(SECRET)

    monkeypatch.setattr(cli, "export_document", explode)
    assert cli.main([str(source), "--export", "--output", str(tmp_path / "o.json")]) == 1
    err = capsys.readouterr().err
    assert SECRET not in err
    assert "exporting" in err


def test_documented_exit_codes() -> None:
    with pytest.raises(SystemExit) as error:
        cli.main([])
    assert error.value.code == 2


def test_default_summary_reports_counts_not_chart_text() -> None:
    from tests.test_pdf_cli_export import _team

    text = cli._summary([_team("Synthetic State")])
    assert "810 chart cells, 30 PAT outcomes" in text
    assert "yards" not in text and "Synths" not in text
