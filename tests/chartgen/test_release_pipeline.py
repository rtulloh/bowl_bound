"""Public generation uses fictional evidence and the current ordinary codec."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bowl_bound.models import Defense, Play, ResultKind
from bowl_bound.team_csv import load_team
from scripts import audit_generated_charts as audit
from tests.chartgen.test_generation import events as events
from tools.chartgen import release_pipeline as pipeline
from tools.chartgen.evidence import Event


def test_cohort_identity_requires_conditional_depth_qualification() -> None:
    from tools.chartgen.cohort_model import TOOL_VERSION, model_identity

    identity = {key: value for key, value in model_identity().items() if key != "contract"}
    identity.update(tool_version=TOOL_VERSION, source_sha256="a" * 64)
    audit._validate_identity(identity, 3)
    with pytest.raises(audit.ChartAuditError):
        audit._validate_identity(identity, 2)


def test_generated_2002_cohort_has_current_model_contrast_and_exact_pins(
    tmp_path: Path, events: list[Event]
) -> None:
    source = tuple(replace(e, season=2002) for e in events)
    output = tmp_path / "private-data" / "candidate"
    report = pipeline.generate_release_cohort(source, {"1": "Cedar Valley"}, 2002, output, seed=19)
    assert report["status"] == "complete"
    assert report["historical_fit"] == "UNVERIFIED"
    assert report["publication_authorized"] is False
    assert report["model_identity"]["origin"] == "authored-bb-cohort-v1"
    assert report["model_identity"]["sha256"] != audit.BUDGET_MODEL_SHA256
    audit._validate_identity(report["model_identity"], 3)
    pins, keys = audit._catalog(output)
    assert keys == {"2002/cedar-valley"}
    assert len(pins) == 5
    assert pins == report["output_pins"]
    chart, metadata = load_team(output / "seasons/2002", "cedar-valley")
    assert metadata.source_sha256
    assert all(r.cell.provenance for r in chart.defense)
    assert any(r.cell.kind is not ResultKind.NO_CHANGE for r in chart.defense)
    baseline = report["teams"]["2002/cedar-valley"]["baseline"]
    assert baseline["tactical_policy_sha256"] == audit.POLICY_SHA256
    assert report["teams"]["2002/cedar-valley"]["depth"]["status"] == "PASS-final-depth-files"
    for gain in (4, 10, 18):
        from bowl_bound.models import NormalizedCell

        cell = NormalizedCell(ResultKind.YARDS, None, yards=gain)
        for play, forms in (
            (Play.ONE, (Defense.B, Defense.A, Defense.E)),
            (Play.THREE, (Defense.C, Defense.A, Defense.B)),
            (Play.FOUR, (Defense.A, Defense.F)),
        ):
            values = [audit._primary(chart, play, f, cell)[0] for f in forms]
            assert all(a < b for a, b in zip(values[:-1], values[1:], strict=True))
    assert json.loads((output / "generation-receipt.json").read_text()) == report
    with pytest.raises(FileExistsError):
        pipeline.generate_release_cohort(source, {"1": "Cedar Valley"}, 2002, output)


def test_release_generation_is_deterministic(tmp_path: Path, events: list[Event]) -> None:
    reports = [
        pipeline.generate_release_cohort(
            events, {"1": "Cedar Valley"}, 2007, tmp_path / "private-data" / name, seed=19
        )
        for name in ("first", "second")
    ]
    assert reports[0]["output_pins"] == reports[1]["output_pins"]
    assert reports[0]["source_sha256"] == reports[1]["source_sha256"]


def test_unknown_primary_fumble_support_preserves_a_failed_receipt(
    tmp_path: Path, events: list[Event]
) -> None:
    unknown = [replace(event, fumble=None) for event in events]
    output = tmp_path / "private-data" / "unknown-fumbles"
    with pytest.raises(ValueError, match="primary fumble support is unknown"):
        pipeline.generate_release_cohort(unknown, {"1": "Cedar Valley"}, 2007, output)
    report = json.loads((output / "generation-receipt.json").read_text())
    assert report["status"] == "failed"
    assert report["output_pins"] == {}
    assert report["publication_authorized"] is False


@pytest.mark.parametrize(
    ("teams", "season", "error"),
    [
        ({"1": "Same Name", "2": "Same Name"}, 2007, "unique"),
        ({"1": "../outside"}, 2007, "name"),
        ({"missing": "Cedar Valley"}, 2007, "source"),
        ({"1": "Cedar Valley"}, 2002, "season"),
        ({"1": "Cedar Valley"}, 2024, "supported"),
        ({}, 2007, "team"),
    ],
)
def test_invalid_inputs_do_not_create_candidate(
    tmp_path: Path, events: list[Event], teams: dict[str, str], season: int, error: str
) -> None:
    output = tmp_path / "private-data" / "candidate"
    with pytest.raises(ValueError, match=error):
        pipeline.generate_release_cohort(events, teams, season, output)
    assert not output.exists()


def test_cli_has_public_generation_and_normalization_commands(
    capsys: pytest.CaptureFixture,
) -> None:
    from tools.chartgen.__main__ import main

    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    assert "generate" in capsys.readouterr().out


def test_cli_reports_missing_source_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    from tools.chartgen.__main__ import main

    teams = tmp_path / "teams.json"
    teams.write_text(json.dumps({"1": "Cedar Valley"}))
    result = main(
        [
            "generate",
            "--source",
            str(tmp_path / "missing.json"),
            "--teams",
            str(teams),
            "--season",
            "2002",
            "--output",
            str(tmp_path / "private-data" / "candidate"),
        ]
    )
    assert result == 2
    assert "source" in capsys.readouterr().err.lower()
