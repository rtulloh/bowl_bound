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


def test_cohort_cli_rejects_missing_inputs_without_private_data_output(
    tmp_path: Path, capsys
) -> None:
    from tools.chartgen.cohort_cli import main

    status = main(
        [
            "--source",
            str(tmp_path / "missing.json"),
            "--membership",
            str(tmp_path / "member.csv"),
            "--schedule",
            str(tmp_path / "schedule.csv"),
            "--groups",
            str(tmp_path / "groups.csv"),
            "--season",
            "2007",
            "--output",
            str(tmp_path / "private-data" / "new"),
        ]
    )
    assert status == 2
    assert "input file is unavailable" in capsys.readouterr().err
    assert not (tmp_path / "private-data").exists()


def test_cohort_refinement_cli_requires_actual_existing_frozen_inputs(
    tmp_path: Path, capsys
) -> None:
    from tools.chartgen.cohort_refine_cli import main

    status = main(
        [
            "--source",
            str(tmp_path / "missing.json"),
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--targets",
            str(tmp_path / "targets.json"),
            "--reviewed-manifest-sha256",
            "reviewed-example-hash",
            "--output",
            str(tmp_path / "private-data" / "refinement"),
        ]
    )
    assert status == 2
    assert "input file is unavailable" in capsys.readouterr().err
    assert not (tmp_path / "private-data").exists()
