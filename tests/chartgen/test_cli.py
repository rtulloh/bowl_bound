"""CLI failures do not expose historical data or write partial source conversions."""

from pathlib import Path

from tools.chartgen.cli import generate_main, normalize_main


def test_generate_missing_source_is_actionable(tmp_path: Path, capsys) -> None:
    status = generate_main(
        [
            "--source",
            str(tmp_path / "missing.json"),
            "--team",
            "1",
            "--name",
            "Cedar Valley",
            "--season",
            "2007",
            "--output",
            str(tmp_path / "private-data" / "candidate"),
        ]
    )
    assert status == 2
    assert "source file is unavailable" in capsys.readouterr().err
    assert not (tmp_path / "private-data").exists()


def test_normalizer_requires_explicit_source_url(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(SystemExit) as error:
        normalize_main(
            ["--input", str(tmp_path / "source.parquet"), "--output", str(tmp_path / "e.json")]
        )
    assert error.value.code == 2
