"""The alpha payload uses the installed CSV loader and newly authored evidence."""

from copy import deepcopy
from dataclasses import asdict, replace
from functools import lru_cache
from typing import Any, cast

import pytest

from bowl_bound.models import Provenance
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.team_csv import TeamFileMetadata, load_team, team_folder_name, team_from_files
from tests.chartgen.test_typed_event_model import legacy_factory
from tools.chartgen.alpha_event_risks import apply_alpha_model
from tools.chartgen.alpha_export import encode_standard_alpha
from tools.chartgen.research_inputs import semantic_sha256

SOURCE = "a" * 64
TABLES = ("offense", "supplemental", "defense", "special_teams", "pat_outcomes")


def facts(chart):
    value = asdict(chart)
    for table in TABLES:
        for row in value[table]:
            if table == "pat_outcomes":
                del row["provenance"]
            else:
                del row["cell"]["provenance"]
        value[table] = sorted(value[table], key=lambda x: repr(x))
    return value


@lru_cache(maxsize=1)
def subject():
    old = legacy_factory()
    meta = TeamFileMetadata(
        5.5,
        ("XWC", "W"),
        "Fictional",
        cast(Provenance, old.offense[0].cell.provenance).source_sha256,
        (),
    )
    candidate, report = apply_alpha_model(
        old,
        known_depths=((-3, 1), (5, 1), (19, 1), (35, 1)),
        unknown_locations=2,
        source_identity=SOURCE,
    )
    assert report["status"] == "represented"
    return old, candidate, meta, cast(dict[str, Any], report)


def export(chart=None, metadata=None, report=None, **kwargs):
    old, candidate, meta, receipt = subject()
    return encode_standard_alpha(
        chart or candidate,
        metadata or meta,
        report or receipt,
        expected_baseline_sha256=semantic_sha256(old),
        source_sha256=SOURCE,
        **kwargs,
    )


def test_standard_roundtrip_preserves_all840_addressed_facts_and_gameplay_metadata():
    _, candidate, metadata, _ = subject()
    files, receipt = export()
    assert set(files) == {
        "team.yaml",
        "offense.csv",
        "defense.csv",
        "special.csv",
        "provenance.csv",
    }
    loaded, actual = team_from_files(
        {k: v for k, v in files.items() if k != "provenance.csv"}, files["provenance.csv"]
    )
    assert facts(loaded) == facts(candidate)
    assert (
        actual.power_rating,
        actual.defense_chart_markers,
        actual.defense_label,
        actual.power_rating_is_placeholder,
    ) == (
        metadata.power_rating,
        metadata.defense_chart_markers,
        metadata.defense_label,
        metadata.power_rating_is_placeholder,
    )
    assert receipt["loaded_chart_sha256"] == semantic_sha256(loaded)
    assert receipt["loaded_metadata_sha256"] == semantic_sha256(actual)
    assert receipt["coordinate_count"] == 840
    assert actual.source_sha256 == receipt["virtual_source_sha256"]
    assert actual.source_sha256 != metadata.source_sha256
    assert all(
        p.filename == "generated-bb-alpha-authored-v1.json"
        and p.source_sha256 == actual.source_sha256
        for table in TABLES
        for row in getattr(loaded, table)
        for p in [row.provenance if table == "pat_outcomes" else row.cell.provenance]
    )
    assert all(
        "private-data" not in text and "ancestry.json" not in text for text in files.values()
    )


def test_ordinary_disk_loader_and_actual_save_load_consume_new_objects(tmp_path):
    _, candidate, _, _ = subject()
    files, _ = export()
    season = tmp_path / str(candidate.season)
    slug = team_folder_name(candidate.name)
    folder = season / slug
    folder.mkdir(parents=True)
    (season / "provenance").mkdir()
    for name, text in files.items():
        (
            season / "provenance" / (slug + ".csv") if name == "provenance.csv" else folder / name
        ).write_text(text)
    chart, meta = load_team(season, slug)
    game = SavedGame.new(
        chart,
        chart,
        home_id=f"{candidate.season}/{slug}",
        away_id=f"{candidate.season}/away",
        seed=2,
        coach_seed=3,
        home_privileges=meta.defense_chart_markers,
        away_privileges=meta.defense_chart_markers,
    )
    game.snap("6", "D")
    restored = loads_game(dumps_game(game), lambda key: load_team(season, slug))
    assert restored.view() == game.view()


@pytest.mark.parametrize(
    "field", ["status", "model_identity", "output_sha256", "baseline_sha256", "source_identity"]
)
def test_mismatched_producer_claims_are_not_export_authority(field):
    report = deepcopy(subject()[3])
    report[field] = "wrong"
    with pytest.raises(ValueError, match="producer"):
        export(report=report)


def test_changed_football_facts_refuse_stale_output_claim():
    candidate = subject()[1]
    changed = replace(candidate, recovery_range=range(10, 11))
    with pytest.raises(ValueError, match="producer"):
        export(chart=changed)


def test_public_virtual_source_contains_only_explicit_derived_descriptor():
    files, receipt = export()
    descriptor = cast(dict[str, Any], receipt["virtual_source_descriptor"])
    assert descriptor["source_sha256"] == SOURCE
    assert descriptor["kind"] == "authored-logical-chart-cells"
    assert (
        cast(dict[str, Any], receipt["model_identity"])["origin"] == "authored-bb-budget-aware-v1"
    )
    assert "private" not in repr(descriptor).lower()
    assert files == export()[0]


def test_placeholder_and_metadata_marker_order_are_preserved():
    metadata = replace(subject()[2], power_rating=200.0, power_rating_is_placeholder=True)
    files, _ = export(metadata=metadata)
    _, loaded = team_from_files(
        {k: v for k, v in files.items() if k != "provenance.csv"}, files["provenance.csv"]
    )
    assert loaded.power_rating_is_placeholder and loaded.power_rating == 200.0
    assert loaded.defense_chart_markers == ("XWC", "W")


def test_private_metadata_evidence_is_replaced_by_explicit_authored_values():
    old = subject()[2]
    evidence = replace(
        cast(Provenance, subject()[1].offense[0].cell.provenance),
        filename="/private/source/reference.pdf",
        original_text="private source note",
    )
    metadata = replace(old, evidence=(("private", evidence),))
    files, _ = export(metadata=metadata)
    assert all(
        "reference.pdf" not in text and "private source note" not in text for text in files.values()
    )
    _, actual = team_from_files(
        {k: v for k, v in files.items() if k != "provenance.csv"}, files["provenance.csv"]
    )
    assert tuple(name for name, _ in actual.evidence) == (
        "rating",
        "markers",
        "label",
        "placeholder",
    )


def test_numeric_model_weight_cannot_be_replaced_by_boolean():
    report = deepcopy(subject()[3])
    report["model_identity"]["contract"]["prior_model"]["contract"]["parent_model"]["contract"][
        "weights"
    ][-1] = True
    with pytest.raises(ValueError, match="producer"):
        export(report=report)


@pytest.mark.parametrize("field", ["expected_baseline_sha256", "source_sha256"])
def test_external_source_and_baseline_pins_cannot_be_empty(field):
    old, chart, metadata, report = subject()
    pins = {"expected_baseline_sha256": semantic_sha256(old), "source_sha256": SOURCE}
    pins[field] = ""
    with pytest.raises(ValueError, match="producer"):
        encode_standard_alpha(chart, metadata, report, **pins)
